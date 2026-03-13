"""Tests for visualization helper functions."""
from __future__ import annotations

from datetime import datetime

import pandas as pd
import pytest

from dart.visualization.ui_helpers import (
    WindowHighlights,
    build_change_profile,
    build_daily_summary,
    build_hourly_profile,
    build_price_narrative,
    build_trend_chart_data,
    build_window_highlights,
)


@pytest.fixture()
def raw_prices_with_negative() -> pd.DataFrame:
    """Raw prices that include a negative value for narrative/highlight tests."""
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


def test_build_window_highlights_extracts_key_metrics(raw_prices_with_negative):
    highlights = build_window_highlights(raw_prices_with_negative)

    assert highlights.latest_price == 9.0
    assert highlights.average_price == 5.0
    assert highlights.max_price == 9.0
    assert highlights.min_price == -1.0
    assert highlights.spread == 10.0
    assert highlights.negative_intervals == 1
    assert highlights.count == 4


def test_window_highlights_empty_factory():
    empty = WindowHighlights.empty()
    assert empty.count == 0
    assert empty.latest_price is None


def test_build_price_narrative_classifies_peak_period():
    narrative = build_price_narrative(11.0, 6.0)

    assert narrative.level == "error"
    assert "Peak-demand pricing" in narrative.title
    assert "5.00 cents above" in narrative.description


def test_build_trend_chart_data_adds_rolling_series(raw_prices_with_negative):
    df = raw_prices_with_negative.iloc[[2, 0, 3, 1]]
    trend = build_trend_chart_data(
        df,
        rolling_window=2,
        base_label="Observed",
        rolling_label="Smoothed",
    )

    assert list(trend.columns) == ["Observed", "Smoothed"]
    assert trend.index[0] == datetime(2024, 2, 1, 12, 0)
    assert trend.iloc[1]["Smoothed"] == 2.0


def test_build_hourly_and_change_profiles_group_by_clock_hour(raw_prices_with_negative):
    hourly_profile = build_hourly_profile(raw_prices_with_negative)
    change_profile = build_change_profile(raw_prices_with_negative)

    assert list(hourly_profile.index) == ["12 PM", "1 PM"]
    assert hourly_profile.loc["12 PM", "Average price"] == 2.0
    assert change_profile.loc["1 PM", "Average 5-minute change"] == 5.0


def test_build_daily_summary_returns_sparkline_ready_rows(sample_hourly_two_days):
    summary = build_daily_summary(sample_hourly_two_days)

    assert list(summary["Date"]) == ["2024-02-01", "2024-02-02"]
    assert summary.loc[0, "Average hourly price"] == 4.0
    assert summary.loc[1, "Peak hour"] == "2 AM"
    assert summary.loc[0, "Intraday profile"] == [2.0, 6.0]
