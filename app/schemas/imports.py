import uuid
from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field


class ColumnProfile(BaseModel):
    name: str
    inferred_type: str
    non_null_count: int
    null_count: int
    null_pct: float
    sample_values: list[Any] = Field(default_factory=list)


class ValidationReport(BaseModel):
    passed: bool
    row_count: int
    columns: list[ColumnProfile]
    issues: list[str] = Field(default_factory=list)
    scores: dict[str, float] = Field(default_factory=dict)


class ImportJobRead(BaseModel):
    id: uuid.UUID
    user_id: uuid.UUID | None = None
    original_filename: str
    status: str
    row_count: int | None
    validation_report: dict[str, Any] | None
    error_message: str | None
    snowflake_rows_written: int | None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class UploadResponse(BaseModel):
    job_id: uuid.UUID
    status: str
