from datetime import date

from pydantic import BaseModel, Field


class StatusCount(BaseModel):
    status: str
    count: int


class DailySeriesPoint(BaseModel):
    day: date
    total_imports: int
    successful_imports: int
    failed_imports: int
    success_rate: float
    rows_loaded: int


class DashboardOverview(BaseModel):
    total_imports: int
    successful_imports: int
    failed_imports: int
    in_progress_imports: int
    success_rate: float
    total_rows_loaded: int
    avg_rows_per_import: float
    by_status: list[StatusCount] = Field(default_factory=list)
    activity_by_day: list[DailySeriesPoint] = Field(default_factory=list)
