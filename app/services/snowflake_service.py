from __future__ import annotations

import snowflake.connector
from pandas import DataFrame
from snowflake.connector.connection import SnowflakeConnection
from snowflake.connector.pandas_tools import write_pandas

from app.config import Settings


def _connect(settings: Settings) -> SnowflakeConnection:
    if not settings.snowflake_account or not settings.snowflake_user:
        raise RuntimeError("Snowflake credentials are not configured (SNOWFLAKE_ACCOUNT / SNOWFLAKE_USER).")
    if not settings.snowflake_password:
        raise RuntimeError("Snowflake password is not configured (SNOWFLAKE_PASSWORD).")
    conn = snowflake.connector.connect(
        account=settings.snowflake_account,
        user=settings.snowflake_user,
        password=settings.snowflake_password or None,
        role=settings.snowflake_role,
        warehouse=settings.snowflake_warehouse,
        database=settings.snowflake_database,
        schema=settings.snowflake_schema,
    )
    return conn


def write_dataframe_to_table(df: DataFrame, settings: Settings) -> int:
    """
    Load a pandas DataFrame into Snowflake using the connector's chunked upload.
    Returns number of rows reported by write_pandas.
    """
    conn = _connect(settings)
    try:
        ok, num_chunks, num_rows, output = write_pandas(
            conn,
            df,
            settings.snowflake_table,
            database=settings.snowflake_database,
            schema=settings.snowflake_schema,
            auto_create_table=settings.auto_create_snowflake_table,
            quote_identifiers=False,
        )
        if not ok:
            raise RuntimeError(f"write_pandas failed: {output}")
        return int(num_rows)
    finally:
        conn.close()
