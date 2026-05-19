from functools import lru_cache
from pathlib import Path

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

_BACKEND_DIR = Path(__file__).resolve().parent.parent


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=_BACKEND_DIR / ".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    api_prefix: str = "/api/v1"
    cors_origins: str = "http://localhost:5173"

    database_url: str = Field(
        default="postgresql+psycopg2://postgres:postgres@localhost:5432/snowflake_loader",
        alias="DATABASE_URL",
    )
    redis_url: str = Field(default="redis://localhost:6379/0", alias="REDIS_URL")
    celery_task_always_eager: bool = Field(default=False, alias="CELERY_TASK_ALWAYS_EAGER")

    upload_dir: str = Field(default="./data/uploads", alias="UPLOAD_DIR")

    import_max_rows: int = Field(default=500_000, alias="IMPORT_MAX_ROWS")
    import_max_file_mb: int = Field(default=50, alias="IMPORT_MAX_FILE_MB")
    required_columns: str = Field(default="", alias="REQUIRED_COLUMNS")

    snowflake_account: str = Field(default="", alias="SNOWFLAKE_ACCOUNT")
    snowflake_user: str = Field(default="", alias="SNOWFLAKE_USER")
    snowflake_password: str = Field(default="", alias="SNOWFLAKE_PASSWORD")
    snowflake_role: str | None = Field(default=None, alias="SNOWFLAKE_ROLE")
    snowflake_warehouse: str | None = Field(default=None, alias="SNOWFLAKE_WAREHOUSE")
    snowflake_database: str = Field(default="", alias="SNOWFLAKE_DATABASE")
    snowflake_schema: str = Field(default="", alias="SNOWFLAKE_SCHEMA")
    snowflake_table: str = Field(default="EXCEL_IMPORTS_RAW", alias="SNOWFLAKE_TABLE")
    auto_create_snowflake_table: bool = Field(default=True, alias="AUTO_CREATE_SNOWFLAKE_TABLE")

    @field_validator("required_columns", mode="before")
    @classmethod
    def strip_required(cls, v: str) -> str:
        if v is None:
            return ""
        return str(v).strip()

    @property
    def required_column_list(self) -> list[str]:
        if not self.required_columns:
            return []
        return [c.strip() for c in self.required_columns.split(",") if c.strip()]

    @property
    def cors_origin_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]

    @property
    def upload_path(self) -> Path:
        p = Path(self.upload_dir)
        return p.resolve() if p.is_absolute() else (_BACKEND_DIR / p).resolve()


@lru_cache
def get_settings() -> Settings:
    return Settings()
