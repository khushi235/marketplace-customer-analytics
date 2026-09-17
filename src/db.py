"""Database access.

Falls back to the committed sample extract when no connection string is configured, so
the repo runs for anyone who clones it.
"""

from pathlib import Path
import os

import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SAMPLE_DIR = PROJECT_ROOT / "data" / "sample"
DB_URL_VAR = "MARKETPLACE_DB_URL"


def _engine():
    from sqlalchemy import create_engine

    return create_engine(os.environ[DB_URL_VAR])


def query(sql: str) -> pd.DataFrame:
    with _engine().connect() as conn:
        return pd.read_sql(sql, conn)


def load_orders() -> pd.DataFrame:
    """Clean order lines - the input to every analysis in this project."""
    if os.getenv(DB_URL_VAR):
        return query("SELECT * FROM analytics.stg_orders")
    df = pd.read_csv(SAMPLE_DIR / "orders_sample.csv", parse_dates=["order_date"])
    return df


def load_customers() -> pd.DataFrame:
    if os.getenv(DB_URL_VAR):
        return query("SELECT * FROM analytics.customer_metrics")
    return pd.read_csv(SAMPLE_DIR / "customers_sample.csv", parse_dates=["signup_date"])
