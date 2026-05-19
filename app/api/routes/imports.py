from pathlib import Path
from uuid import UUID

from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile
from sqlalchemy.orm import Session

from app.config import get_settings
from app.db.session import get_db
from app.models.import_job import ImportJob, ImportJobStatus
from app.models.user import User
from app.schemas.imports import ImportJobRead, UploadResponse
from app.workers.tasks import load_import_task, validate_import_task

router = APIRouter(prefix="/imports", tags=["imports"])


@router.post("/upload", response_model=UploadResponse)
def upload_excel(
    file: UploadFile = File(...),
    user_id: UUID | None = Query(default=None, description="Optional owner; required once JWT auth exists."),
    db: Session = Depends(get_db),
) -> UploadResponse:
    if not file.filename:
        raise HTTPException(status_code=400, detail="Missing filename.")

    suffix = Path(file.filename).suffix.lower()
    if suffix not in {".xlsx", ".xls"}:
        raise HTTPException(status_code=400, detail="Only .xlsx (recommended) or .xls Excel files are supported.")

    settings = get_settings()
    content = file.file.read()
    max_bytes = settings.import_max_file_mb * 1024 * 1024
    if len(content) > max_bytes:
        raise HTTPException(
            status_code=413,
            detail=f"File exceeds maximum size of {settings.import_max_file_mb} MB.",
        )

    if user_id is not None and db.get(User, user_id) is None:
        raise HTTPException(status_code=400, detail="user_id does not exist.")

    job = ImportJob(
        user_id=user_id,
        original_filename=file.filename,
        stored_path="",
        status=ImportJobStatus.pending.value,
    )
    db.add(job)
    db.flush()

    upload_root = settings.upload_path
    upload_root.mkdir(parents=True, exist_ok=True)
    dest = upload_root / f"{job.id}{suffix}"
    dest.write_bytes(content)
    job.stored_path = str(dest.resolve())
    db.commit()
    db.refresh(job)

    validate_import_task.delay(str(job.id))
    return UploadResponse(job_id=job.id, status=job.status)


@router.get("/{job_id}", response_model=ImportJobRead)
def get_import_job(job_id: UUID, db: Session = Depends(get_db)) -> ImportJob:
    job = db.get(ImportJob, job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Import job not found.")
    return job


@router.post("/{job_id}/load", response_model=ImportJobRead)
def confirm_load(job_id: UUID, db: Session = Depends(get_db)) -> ImportJob:
    job = db.get(ImportJob, job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Import job not found.")
    if job.status != ImportJobStatus.validated.value:
        raise HTTPException(
            status_code=409,
            detail=f"Job must be in 'validated' state before load (current: {job.status}).",
        )
    load_import_task.delay(str(job.id))
    return job
