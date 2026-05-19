from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.demo_constants import DEMO_ADMIN_USER_ID, DEMO_REGULAR_USER_ID
from app.models.user import User
from app.schemas.dashboard import DashboardOverview
from app.services.dashboard_service import build_dashboard_overview

router = APIRouter(prefix="/dashboard", tags=["dashboard"])


@router.get("/overview", response_model=DashboardOverview)
def get_dashboard_overview_admin(
    days: int = Query(default=30, ge=1, le=365),
    db: Session = Depends(get_db),
) -> DashboardOverview:
    """Platform-wide metrics (admin dashboard)."""
    return build_dashboard_overview(db, days=days, user_id=None)


@router.get("/users/{user_id}/overview", response_model=DashboardOverview)
def get_dashboard_overview_for_user(
    user_id: UUID,
    days: int = Query(default=30, ge=1, le=365),
    db: Session = Depends(get_db),
) -> DashboardOverview:
    """Metrics scoped to one user (user dashboard). Replace path param with JWT user later."""
    if db.get(User, user_id) is None:
        raise HTTPException(status_code=404, detail="User not found.")
    return build_dashboard_overview(db, days=days, user_id=user_id)


@router.get("/demo/info")
def get_demo_dashboard_info() -> dict:
    """Stable demo user IDs and example URLs for local testing (no auth yet)."""
    return {
        "admin_user_id": str(DEMO_ADMIN_USER_ID),
        "regular_user_id": str(DEMO_REGULAR_USER_ID),
        "examples": {
            "platform_overview": "/api/v1/dashboard/overview?days=30",
            "admin_personal": f"/api/v1/dashboard/users/{DEMO_ADMIN_USER_ID}/overview?days=30",
            "user_personal": f"/api/v1/dashboard/users/{DEMO_REGULAR_USER_ID}/overview?days=30",
        },
        "note": "Run scripts/seed_demo_dashboard.py after migrations to populate sample data.",
    }
