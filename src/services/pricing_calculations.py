"""
Pure pricing calculation helpers.

These functions are intentionally side-effect free so they can be reused
across service methods and tested independently.
"""
from __future__ import annotations

from datetime import date, datetime, timedelta

import pandas as pd


def expand_date_range_to_bounds(start_date: date, end_date: date) -> tuple[datetime, datetime]:
    """Expand a date range to include both full endpoint days."""
    if start_date > end_date:
        raise ValueError(f"Start date ({start_date}) must be before end date ({end_date})")

    start_dt = datetime.combine(start_date, datetime.min.time())
    end_dt = datetime.combine(
        end_date,
        datetime.max.time().replace(second=0, microsecond=0),
    )
    return start_dt, end_dt


def compute_hourly_hour_ending(raw_df: pd.DataFrame) -> pd.DataFrame:
    """
    Convert 5-minute data into hour-ending averages.

    Example: prices from 12:00-12:55 are labeled as 13:00.
    """
    if raw_df.empty:
        return pd.DataFrame(columns=["hour", "avg_price"])

    df = raw_df.copy()
    df["hour"] = df["timestamp"].dt.floor("h") + timedelta(hours=1)
    hourly = df.groupby("hour", as_index=False)["price"].mean()
    hourly.columns = ["hour", "avg_price"]
    return hourly.sort_values("hour").reset_index(drop=True)


def compute_stats(df: pd.DataFrame, price_column: str) -> dict[str, float | int | None]:
    """Compute min/max/average/count statistics for a numeric price column."""
    if df.empty or price_column not in df.columns:
        return {"min": None, "max": None, "average": None, "count": 0}

    values = df[price_column]
    return {
        "min": float(values.min()),
        "max": float(values.max()),
        "average": float(values.mean()),
        "count": int(len(values)),
    }


def build_hourly_with_raw_context(raw_df: pd.DataFrame, hourly_df: pd.DataFrame) -> pd.DataFrame:
    """
    Add reconciliation context for each hourly bucket.

    Output columns:
    - hour
    - avg_price
    - raw_point_count
    - raw_bucket_start
    - raw_bucket_end
    """
    if raw_df.empty or hourly_df.empty:
        return pd.DataFrame(
            columns=["hour", "avg_price", "raw_point_count", "raw_bucket_start", "raw_bucket_end"]
        )

    df = raw_df.copy()
    df["hour"] = df["timestamp"].dt.floor("h") + timedelta(hours=1)
    grouped = (
        df.groupby("hour", as_index=False)
        .agg(
            raw_point_count=("price", "count"),
            raw_bucket_start=("timestamp", "min"),
            raw_bucket_end=("timestamp", "max"),
        )
        .sort_values("hour")
        .reset_index(drop=True)
    )

    merged = hourly_df.merge(grouped, on="hour", how="left")
    return merged
