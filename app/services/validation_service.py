from __future__ import annotations

from typing import Any

import pandas as pd

from app.config import Settings
from app.services.excel_service import build_column_profiles


def run_basic_validation(df: pd.DataFrame, settings: Settings) -> dict[str, Any]:
    """
    Lightweight validation suitable for the MVP pipeline.
    Swap this for Great Expectations suites when you need richer rules.
    """
    issues: list[str] = []
    row_count = len(df)
    columns = build_column_profiles(df)

    if row_count == 0:
        issues.append("The spreadsheet has no data rows.")

    if row_count > settings.import_max_rows:
        issues.append(f"Row count {row_count} exceeds limit {settings.import_max_rows}.")

    required = {c.upper() for c in settings.required_column_list}
    present = {str(c).upper() for c in df.columns}
    missing = sorted(required - present)
    if missing:
        issues.append(f"Missing required columns: {', '.join(missing)}")

    null_heavy = [c["name"] for c in columns if c["null_pct"] > 50]
    if null_heavy:
        issues.append(
            "Columns with more than 50% nulls: " + ", ".join(null_heavy[:20])
            + ("…" if len(null_heavy) > 20 else "")
        )

    completeness_scores = [max(0.0, 1.0 - (c["null_pct"] / 100.0)) for c in columns] or [1.0]
    overall_health = round(sum(completeness_scores) / len(completeness_scores) * 100, 2)

    passed = len(issues) == 0

    return {
        "passed": passed,
        "row_count": row_count,
        "columns": columns,
        "issues": issues,
        "scores": {"overall_health": overall_health, "column_count": float(len(columns))},
    }


def coerce_for_snowflake(df: pd.DataFrame) -> pd.DataFrame:
    """Best-effort dtype cleanup before write_pandas."""
    out = df.copy()
    for col in out.columns:
        s = out[col]
        if pd.api.types.is_object_dtype(s):
            # try datetime
            dt = pd.to_datetime(s, errors="coerce")
            if dt.notna().sum() > 0 and (dt.notna().sum() / max(len(s), 1)) > 0.85:
                out[col] = dt
                continue
            num = pd.to_numeric(s, errors="coerce")
            if num.notna().sum() > 0 and (num.notna().sum() / max(len(s), 1)) > 0.85:
                out[col] = num
                continue
    return out
