from __future__ import annotations

import re
from pathlib import Path
from typing import Any

import pandas as pd


def json_friendly_value(val: Any) -> Any:
    if val is None or isinstance(val, (str, int, float, bool)):
        return val
    if hasattr(val, "item"):
        try:
            return json_friendly_value(val.item())
        except Exception:
            pass
    if hasattr(val, "isoformat"):
        try:
            return val.isoformat()
        except Exception:
            pass
    return str(val)


def normalize_column_name(raw: str) -> str:
    s = str(raw).strip().replace(" ", "_").replace("-", "_")
    s = re.sub(r"[^0-9A-Za-z_]", "_", s)
    s = re.sub(r"_+", "_", s).strip("_")
    if not s:
        s = "COLUMN"
    if s[0].isdigit():
        s = f"COL_{s}"
    return s.upper()


def dedupe_column_names(names: list[str]) -> list[str]:
    seen: dict[str, int] = {}
    out: list[str] = []
    for name in names:
        count = seen.get(name, 0) + 1
        seen[name] = count
        out.append(name if count == 1 else f"{name}_{count}")
    return out


def read_excel_to_dataframe(path: Path) -> pd.DataFrame:
    suffix = path.suffix.lower()
    engine = "openpyxl" if suffix == ".xlsx" else "xlrd"
    return pd.read_excel(path, engine=engine, dtype=object)


def normalize_dataframe(df: pd.DataFrame) -> pd.DataFrame:
    raw_names = [normalize_column_name(c) for c in df.columns.astype(str).tolist()]
    df = df.copy()
    df.columns = dedupe_column_names(raw_names)
    return df


def infer_column_type(series: pd.Series) -> str:
    non_null = series.dropna()
    if non_null.empty:
        return "unknown"
    if pd.api.types.is_bool_dtype(series):
        return "boolean"
    if pd.api.types.is_integer_dtype(series):
        return "integer"
    if pd.api.types.is_float_dtype(series):
        return "float"
    # try numeric coercion
    coerced = pd.to_numeric(non_null, errors="coerce")
    if coerced.notna().all():
        return "integer" if (coerced % 1 == 0).all() else "float"
    # datetime
    dt = pd.to_datetime(non_null, errors="coerce")
    if dt.notna().sum() / len(non_null) > 0.9:
        return "datetime"
    return "string"


def column_samples(series: pd.Series, k: int = 3) -> list[Any]:
    out: list[Any] = []
    for val in series.dropna().head(k).tolist():
        if hasattr(val, "isoformat"):
            try:
                out.append(val.isoformat())  # type: ignore[union-attr]
                continue
            except Exception:
                pass
        if isinstance(val, bytes):
            out.append(val.decode("utf-8", errors="replace"))
        else:
            out.append(json_friendly_value(val))
    return out


def build_column_profiles(df: pd.DataFrame) -> list[dict[str, Any]]:
    profiles: list[dict[str, Any]] = []
    n = len(df)
    for col in df.columns:
        s = df[col]
        null_count = int(s.isna().sum())
        profiles.append(
            {
                "name": str(col),
                "inferred_type": infer_column_type(s),
                "non_null_count": int(n - null_count),
                "null_count": null_count,
                "null_pct": round((null_count / n) * 100, 2) if n else 0.0,
                "sample_values": list(column_samples(s)),
            }
        )
    return profiles


def dataframe_to_parquet(df: pd.DataFrame, dest: Path) -> None:
    dest.parent.mkdir(parents=True, exist_ok=True)
    df.to_parquet(dest, index=False, engine="pyarrow")
