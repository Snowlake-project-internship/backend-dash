from __future__ import annotations

from datetime import date, datetime, time, timedelta, timezone
from uuid import UUID

from sqlalchemy import case, func
from sqlalchemy.orm import Session

from app.models.import_job import ImportJob
from app.schemas.dashboard import DailySeriesPoint, DashboardOverview, StatusCount

SUCCESS_STATUSES = {"load_success"}
FAILED_STATUSES = {"validation_failed", "load_failed"}
IN_PROGRESS_STATUSES = {"pending", "validating", "validated", "loading"}


def period_start(days: int) -> datetime:
    today = datetime.now(timezone.utc).date()
    start_day = today - timedelta(days=max(days - 1, 0))
    return datetime.combine(start_day, time.min, tzinfo=timezone.utc)


def _import_jobs_query(db: Session, *, start_at: datetime, user_id: UUID | None):
    q = db.query(ImportJob).filter(ImportJob.created_at >= start_at)
    if user_id is not None:
        q = q.filter(ImportJob.user_id == user_id)
    return q


def build_dashboard_overview(db: Session, *, days: int, user_id: UUID | None = None) -> DashboardOverview:
    start_at = period_start(days)

    total_imports = _import_jobs_query(db, start_at=start_at, user_id=user_id).count()

    successful_imports = (
        _import_jobs_query(db, start_at=start_at, user_id=user_id)
        .filter(ImportJob.status.in_(SUCCESS_STATUSES))
        .count()
    )

    failed_imports = (
        _import_jobs_query(db, start_at=start_at, user_id=user_id)
        .filter(ImportJob.status.in_(FAILED_STATUSES))
        .count()
    )

    in_progress_imports = (
        _import_jobs_query(db, start_at=start_at, user_id=user_id)
        .filter(ImportJob.status.in_(IN_PROGRESS_STATUSES))
        .count()
    )

    total_rows_loaded = (
        _import_jobs_query(db, start_at=start_at, user_id=user_id)
        .with_entities(func.coalesce(func.sum(ImportJob.snowflake_rows_written), 0))
        .scalar()
        or 0
    )

    grouped = (
        _import_jobs_query(db, start_at=start_at, user_id=user_id)
        .with_entities(ImportJob.status, func.count(ImportJob.id))
        .group_by(ImportJob.status)
        .all()
    )
    by_status = [StatusCount(status=status, count=count) for status, count in grouped]

    daily_rows = (
        _import_jobs_query(db, start_at=start_at, user_id=user_id)
        .with_entities(
            func.date(ImportJob.created_at).label("day"),
            func.count(ImportJob.id).label("total_imports"),
            func.sum(case((ImportJob.status.in_(SUCCESS_STATUSES), 1), else_=0)).label("successful_imports"),
            func.sum(case((ImportJob.status.in_(FAILED_STATUSES), 1), else_=0)).label("failed_imports"),
            func.coalesce(func.sum(ImportJob.snowflake_rows_written), 0).label("rows_loaded"),
        )
        .group_by(func.date(ImportJob.created_at))
        .order_by(func.date(ImportJob.created_at))
        .all()
    )

    activity_by_day: list[DailySeriesPoint] = []
    for row in daily_rows:
        total = int(row.total_imports or 0)
        success = int(row.successful_imports or 0)
        failed = int(row.failed_imports or 0)
        activity_by_day.append(
            DailySeriesPoint(
                day=row.day if isinstance(row.day, date) else date.fromisoformat(str(row.day)),
                total_imports=total,
                successful_imports=success,
                failed_imports=failed,
                success_rate=round((success / total) * 100, 2) if total else 0.0,
                rows_loaded=int(row.rows_loaded or 0),
            )
        )

    success_rate = round((successful_imports / total_imports) * 100, 2) if total_imports else 0.0
    avg_rows = round(total_rows_loaded / successful_imports, 2) if successful_imports else 0.0

    return DashboardOverview(
        total_imports=int(total_imports),
        successful_imports=int(successful_imports),
        failed_imports=int(failed_imports),
        in_progress_imports=int(in_progress_imports),
        success_rate=success_rate,
        total_rows_loaded=int(total_rows_loaded),
        avg_rows_per_import=avg_rows,
        by_status=by_status,
        activity_by_day=activity_by_day,
    )
