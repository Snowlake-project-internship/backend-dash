from __future__ import annotations

import uuid
from pathlib import Path

import pandas as pd

from app.config import get_settings
from app.db.session import SessionLocal
from app.models.import_job import ImportJob, ImportJobStatus
from app.services.excel_service import dataframe_to_parquet, normalize_dataframe, read_excel_to_dataframe
from app.services.snowflake_service import write_dataframe_to_table
from app.services.validation_service import coerce_for_snowflake, run_basic_validation
from app.workers.celery_app import celery_app


@celery_app.task(bind=True, name="imports.validate")
def validate_import_task(_self, job_id: str) -> None:
    settings = get_settings()
    jid = uuid.UUID(job_id)
    db = SessionLocal()
    try:
        job = db.get(ImportJob, jid)
        if not job:
            return
        job.status = ImportJobStatus.validating.value
        db.commit()

        path = Path(job.stored_path)
        df_raw = read_excel_to_dataframe(path)
        df = normalize_dataframe(df_raw)
        report = run_basic_validation(df, settings)
        job.validation_report = report
        job.row_count = report["row_count"]

        if not report["passed"]:
            job.status = ImportJobStatus.validation_failed.value
            job.error_message = "; ".join(report["issues"])
        else:
            parquet_path = path.with_suffix(".parquet")
            dataframe_to_parquet(df, parquet_path)
            job.normalized_parquet_path = str(parquet_path)
            job.status = ImportJobStatus.validated.value
            job.error_message = None
        db.commit()
    except Exception as exc:
        db.rollback()
        job = db.get(ImportJob, jid)
        if job:
            job.status = ImportJobStatus.validation_failed.value
            job.error_message = str(exc)
            db.commit()
        raise
    finally:
        db.close()


@celery_app.task(bind=True, name="imports.load")
def load_import_task(_self, job_id: str) -> None:
    settings = get_settings()
    jid = uuid.UUID(job_id)
    db = SessionLocal()
    try:
        job = db.get(ImportJob, jid)
        if not job:
            return
        if job.status != ImportJobStatus.validated.value:
            raise RuntimeError("Job is not ready to load (status must be 'validated').")

        job.status = ImportJobStatus.loading.value
        db.commit()

        pq = job.normalized_parquet_path
        if not pq:
            raise RuntimeError("Missing normalized Parquet artifact for this job.")

        df = pd.read_parquet(pq)
        df = coerce_for_snowflake(df)
        rows_written = write_dataframe_to_table(df, settings)

        job.status = ImportJobStatus.load_success.value
        job.snowflake_rows_written = rows_written
        job.error_message = None
        db.commit()
    except Exception as exc:
        db.rollback()
        job = db.get(ImportJob, jid)
        if job:
            job.status = ImportJobStatus.load_failed.value
            job.error_message = str(exc)
            db.commit()
        raise
    finally:
        db.close()
