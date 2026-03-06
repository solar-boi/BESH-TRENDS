"""Tests for visualization helper functions."""

from datetime import datetime

import pandas as pd

from dart.visualization.ui_helpers import (
    build_change_profile,
    build_daily_summary,
    build_hourly_profile,
    build_price_narrative,
    build_trend_chart_data,
    build_window_highlights,
)


def create_raw_prices() -> pd.DataFrame:
    """Create a small raw price sample for view-model tests."""
    return pd.DataFrame(
        {
            "timestamp": [
                datetime(2024, 2, 1, 12, 0),
                datetime(2024, 2, 1, 12, 5),
                datetime(2024, 2, 1, 13, 0),
                datetime(2024, 2, 1, 13, 5),
            ],
            "price": [5.0, -1.0, 7.0, 9.0],
        }
    )


def create_hourly_prices() -> pd.DataFrame:
    """Create hourly data spanning two days."""
    return pd.DataFrame(
        {
            "hour": [
                datetime(2024, 2, 1, 1, 0),
                datetime(2024, 2, 1, 2, 0),
                datetime(2024, 2, 2, 1, 0),
                datetime(2024, 2, 2, 2, 0),
            ],
            "avg_price": [2.0, 6.0, 4.0, 8.0],
        }
    )


def test_build_window_highlights_extracts_key_metrics():
    """Highlights include extrema, latest point, and negative interval count."""
    highlights = build_window_highlights(create_raw_prices())

    assert highlights.latest_price == 9.0
    assert highlights.average_price == 5.0
    assert highlights.max_price == 9.0
    assert highlights.min_price == -1.0
    assert highlights.spread == 10.0
    assert highlights.negative_intervals == 1
    assert highlights.count == 4


def test_build_price_narrative_classifies_peak_period():
    """High prices produce a peak-pricing narrative."""
    narrative = build_price_narrative(11.0, 6.0)

    assert narrative.level == "error"
    assert "Peak-demand pricing" in narrative.title
    assert "5.00 cents above" in narrative.description


def test_build_trend_chart_data_adds_rolling_series():
    """Trend chart data is sorted and includes a rolling average."""
    df = create_raw_prices().iloc[[2, 0, 3, 1]]
    trend = build_trend_chart_data(
        df,
        rolling_window=2,
        base_label="Observed",
        rolling_label="Smoothed",
    )

    assert list(trend.columns) == ["Observed", "Smoothed"]
    assert trend.index[0] == datetime(2024, 2, 1, 12, 0)
    assert trend.iloc[1]["Smoothed"] == 2.0


def test_build_hourly_and_change_profiles_group_by_clock_hour():
    """Clock-hour summaries expose average levels and movement."""
    raw_df = create_raw_prices()

    hourly_profile = build_hourly_profile(raw_df)
    change_profile = build_change_profile(raw_df)

    assert list(hourly_profile.index) == ["12 PM", "1 PM"]
    assert hourly_profile.loc["12 PM", "Average price"] == 2.0
    assert change_profile.loc["1 PM", "Average 5-minute change"] == 5.0


def test_build_daily_summary_returns_sparkline_ready_rows():
    """Daily summary includes one row per day and intraday list values."""
    summary = build_daily_summary(create_hourly_prices())

    assert list(summary["Date"]) == ["2024-02-01", "2024-02-02"]
    assert summary.loc[0, "Average hourly price"] == 4.0
    assert summary.loc[1, "Peak hour"] == "2 AM"
    assert summary.loc[0, "Intraday profile"] == [2.0, 6.0]
