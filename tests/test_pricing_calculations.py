"""Unit tests for pure pricing calculation helpers."""
from datetime import date, datetime

import pytest

from dart.services.pricing_calculations import (
    build_hourly_with_raw_context,
    compute_hourly_hour_ending,
    compute_stats,
    expand_date_range_to_bounds,
)


def test_expand_date_range_to_bounds():
    start_dt, end_dt = expand_date_range_to_bounds(date(2024, 2, 1), date(2024, 2, 2))
    assert start_dt == datetime(2024, 2, 1, 0, 0)
    assert end_dt == datetime(2024, 2, 2, 23, 59)


def test_expand_date_range_to_bounds_invalid():
    with pytest.raises(ValueError):
        expand_date_range_to_bounds(date(2024, 2, 2), date(2024, 2, 1))


def test_compute_hourly_hour_ending(sample_raw_df):
    hourly = compute_hourly_hour_ending(sample_raw_df)
    assert len(hourly) == 2
    assert list(hourly.columns) == ["hour", "avg_price"]
    assert hourly.iloc[0]["hour"] == datetime(2024, 2, 1, 13, 0)
    assert hourly.iloc[0]["avg_price"] == pytest.approx((5.2 + 5.5 + 5.1) / 3, rel=0.01)
    assert hourly.iloc[1]["hour"] == datetime(2024, 2, 1, 14, 0)


def test_compute_stats(sample_raw_df):
    stats = compute_stats(sample_raw_df, "price")
    assert stats["count"] == 5
    assert stats["min"] == 5.1
    assert stats["max"] == 6.2
    assert stats["average"] == pytest.approx(5.6, rel=0.01)


def test_build_hourly_with_raw_context(sample_raw_df):
    hourly_df = compute_hourly_hour_ending(sample_raw_df)
    context_df = build_hourly_with_raw_context(sample_raw_df, hourly_df)

    assert list(context_df.columns) == [
        "hour",
        "avg_price",
        "raw_point_count",
        "raw_bucket_start",
        "raw_bucket_end",
    ]
    assert int(context_df["raw_point_count"].sum()) == 5
    assert context_df.iloc[0]["raw_bucket_start"] == datetime(2024, 2, 1, 12, 0)
