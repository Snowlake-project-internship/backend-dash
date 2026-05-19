"""
Populate Postgres with demo users, import jobs, feedback, notifications, and audit rows
so dashboard endpoints return non-empty charts.

Run from `backend/` after migrations:

  set PYTHONPATH=%CD%
  python scripts/seed_demo_dashboard.py
"""

from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone

import bcrypt
from sqlalchemy import delete

from app.db.session import SessionLocal
from app.demo_constants import DEMO_ADMIN_USER_ID, DEMO_REGULAR_USER_ID
from app.models.audit_log import AuditLog
from app.models.feedback import Feedback
from app.models.import_job import ImportJob, ImportJobStatus
from app.models.notification import Notification
from app.models.user import User, UserRole


def _dt(days_ago: int, hour: int = 12) -> datetime:
    d = datetime.now(timezone.utc).replace(hour=hour, minute=0, second=0, microsecond=0) - timedelta(days=days_ago)
    return d


def main() -> None:
    db = SessionLocal()
    try:
        db.execute(delete(ImportJob).where(ImportJob.user_id.in_([DEMO_ADMIN_USER_ID, DEMO_REGULAR_USER_ID])))
        db.execute(delete(Notification).where(Notification.user_id.in_([DEMO_ADMIN_USER_ID, DEMO_REGULAR_USER_ID])))
        db.execute(delete(Feedback).where(Feedback.user_id.in_([DEMO_ADMIN_USER_ID, DEMO_REGULAR_USER_ID])))
        db.execute(delete(AuditLog).where(AuditLog.actor_user_id.in_([DEMO_ADMIN_USER_ID, DEMO_REGULAR_USER_ID])))
        db.execute(delete(User).where(User.id.in_([DEMO_ADMIN_USER_ID, DEMO_REGULAR_USER_ID])))
        db.commit()

        demo_hash = bcrypt.hashpw(b"demo123", bcrypt.gensalt()).decode("ascii")

        admin = User(
            id=DEMO_ADMIN_USER_ID,
            email="admin.demo@example.com",
            hashed_password=demo_hash,
            full_name="Demo Admin",
            role=UserRole.admin.value,
            is_active=True,
            last_login_at=datetime.now(timezone.utc),
        )
        user = User(
            id=DEMO_REGULAR_USER_ID,
            email="user.demo@example.com",
            hashed_password=demo_hash,
            full_name="Demo User",
            role=UserRole.user.value,
            is_active=True,
            last_login_at=datetime.now(timezone.utc) - timedelta(hours=2),
        )
        db.add_all([admin, user])
        db.flush()

        def job(
            uid: uuid.UUID,
            *,
            status: str,
            days_ago: int,
            rows: int | None,
            sf_rows: int | None,
            fname: str,
        ) -> ImportJob:
            return ImportJob(
                id=uuid.uuid4(),
                user_id=uid,
                original_filename=fname,
                stored_path="/demo/placeholder.xlsx",
                normalized_parquet_path=None,
                status=status,
                row_count=rows,
                validation_report=None if status != ImportJobStatus.validation_failed.value else {"passed": False},
                error_message=None if status != ImportJobStatus.load_failed.value else "Snowflake connection refused (demo).",
                snowflake_rows_written=sf_rows,
                created_at=_dt(days_ago),
                updated_at=_dt(days_ago),
            )

        jobs: list[ImportJob] = [
            job(DEMO_ADMIN_USER_ID, status=ImportJobStatus.load_success.value, days_ago=0, rows=120, sf_rows=120, fname="sales_q1.xlsx"),
            job(DEMO_ADMIN_USER_ID, status=ImportJobStatus.load_success.value, days_ago=1, rows=80, sf_rows=80, fname="inventory.xlsx"),
            job(DEMO_ADMIN_USER_ID, status=ImportJobStatus.validation_failed.value, days_ago=2, rows=0, sf_rows=None, fname="bad_headers.xlsx"),
            job(DEMO_ADMIN_USER_ID, status=ImportJobStatus.load_failed.value, days_ago=3, rows=200, sf_rows=None, fname="warehouse_load.xlsx"),
            job(DEMO_ADMIN_USER_ID, status=ImportJobStatus.validated.value, days_ago=4, rows=50, sf_rows=None, fname="pending_confirm.xlsx"),
            job(DEMO_REGULAR_USER_ID, status=ImportJobStatus.load_success.value, days_ago=0, rows=300, sf_rows=300, fname="monthly_report.xlsx"),
            job(DEMO_REGULAR_USER_ID, status=ImportJobStatus.load_success.value, days_ago=1, rows=150, sf_rows=150, fname="customers.xlsx"),
            job(DEMO_REGULAR_USER_ID, status=ImportJobStatus.load_success.value, days_ago=2, rows=90, sf_rows=90, fname="orders.xlsx"),
            job(DEMO_REGULAR_USER_ID, status=ImportJobStatus.validation_failed.value, days_ago=5, rows=0, sf_rows=None, fname="empty.xlsx"),
            job(DEMO_REGULAR_USER_ID, status=ImportJobStatus.pending.value, days_ago=0, rows=None, sf_rows=None, fname="queued.xlsx"),
            job(DEMO_REGULAR_USER_ID, status=ImportJobStatus.load_success.value, days_ago=10, rows=400, sf_rows=400, fname="archive_may.xlsx"),
            job(DEMO_REGULAR_USER_ID, status=ImportJobStatus.load_success.value, days_ago=12, rows=220, sf_rows=220, fname="archive_apr.xlsx"),
        ]
        db.add_all(jobs)

        db.add(
            Feedback(
                user_id=DEMO_REGULAR_USER_ID,
                subject="Column mapping",
                body="Can we rename columns automatically?",
                status="open",
            )
        )
        db.add(
            Notification(
                user_id=DEMO_REGULAR_USER_ID,
                title="Import succeeded",
                body="Your file monthly_report.xlsx finished loading.",
            )
        )
        db.add(
            AuditLog(
                actor_user_id=DEMO_ADMIN_USER_ID,
                action="demo.seed",
                resource_type="system",
                resource_id="seed_demo_dashboard",
                extra_data={"message": "Demo data inserted"},
            )
        )

        db.commit()
        print("Demo data inserted.")
        print("  Admin user id:", DEMO_ADMIN_USER_ID)
        print("  User id:      ", DEMO_REGULAR_USER_ID)
        print("Try:")
        print("  GET /api/v1/dashboard/overview?days=30")
        print(f"  GET /api/v1/dashboard/users/{DEMO_REGULAR_USER_ID}/overview?days=30")
    finally:
        db.close()


if __name__ == "__main__":
    main()
