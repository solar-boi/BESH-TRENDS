"""Helpers for building Streamlit-friendly pricing views."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

import pandas as pd


@dataclass(frozen=True)
class PriceNarrative:
    """Narrative copy that explains the current pricing regime."""

    title: str
    level: str
    description: str


@dataclass(frozen=True)
class WindowHighlights:
    """Key facts pulled from a pricing time window."""

    latest_price: float | None
    latest_timestamp: datetime | None
    average_price: float | None
    max_price: float | None
    max_timestamp: datetime | None
    min_price: float | None
    min_timestamp: datetime | None
    spread: float | None
    negative_intervals: int
    count: int

    @classmethod
    def empty(cls) -> "WindowHighlights":
        return cls(
            latest_price=None,
            latest_timestamp=None,
            average_price=None,
            max_price=None,
            max_timestamp=None,
            min_price=None,
            min_timestamp=None,
            spread=None,
            negative_intervals=0,
            count=0,
        )


def _format_hour_label(value: datetime) -> str:
    """Format an hour label without a leading zero."""
    return value.strftime("%I %p").lstrip("0")


def _hour_label_order() -> list[str]:
    """Return canonical clock-hour label order from midnight through 11 PM."""
    return [_format_hour_label(datetime(2000, 1, 1, hour)) for hour in range(24)]


def build_window_highlights(
    df: pd.DataFrame,
    *,
    price_column: str = "price",
    timestamp_column: str = "timestamp",
) -> WindowHighlights:
    """Extract headline metrics from a price series."""
    if df.empty or price_column not in df.columns or timestamp_column not in df.columns:
        return WindowHighlights.empty()

    valid = df[[timestamp_column, price_column]].dropna().sort_values(timestamp_column)
    if valid.empty:
        return WindowHighlights.empty()

    latest_row = valid.iloc[-1]
    max_row = valid.loc[valid[price_column].idxmax()]
    min_row = valid.loc[valid[price_column].idxmin()]

    max_price = float(max_row[price_column])
    min_price = float(min_row[price_column])

    return WindowHighlights(
        latest_price=float(latest_row[price_column]),
        latest_timestamp=pd.to_datetime(latest_row[timestamp_column]).to_pydatetime(),
        average_price=float(valid[price_column].mean()),
        max_price=max_price,
        max_timestamp=pd.to_datetime(max_row[timestamp_column]).to_pydatetime(),
        min_price=min_price,
        min_timestamp=pd.to_datetime(min_row[timestamp_column]).to_pydatetime(),
        spread=max_price - min_price,
        negative_intervals=int((valid[price_column] < 0).sum()),
        count=int(len(valid)),
    )


def build_price_narrative(
    current_price: float | None,
    baseline_price: float | None = None,
) -> PriceNarrative:
    """Turn a price into short user-facing guidance."""
    if current_price is None:
        return PriceNarrative(
            title="Pricing signal unavailable",
            level="warning",
            description="The current-hour average could not be retrieved from ComEd.",
        )

    comparison = ""
    if baseline_price is not None:
        delta = current_price - baseline_price
        if abs(delta) < 0.01:
            comparison = " It is almost identical to the recent 24-hour average."
        elif delta > 0:
            comparison = f" It is {delta:.2f} cents above the recent 24-hour average."
        else:
            comparison = f" It is {abs(delta):.2f} cents below the recent 24-hour average."

    if current_price < 0:
        return PriceNarrative(
            title="Negative pricing window",
            level="success",
            description=(
                "Prices are below zero, which usually signals very soft demand or strong supply."
                " This is often the most favorable window for flexible usage."
                f"{comparison}"
            ),
        )
    if current_price < 3:
        return PriceNarrative(
            title="Low-cost period",
            level="success",
            description=(
                "The current hour is landing in the lower-cost part of the recent range,"
                " making it a favorable time for discretionary consumption."
                f"{comparison}"
            ),
        )
    if current_price < 7:
        return PriceNarrative(
            title="Typical daytime pricing",
            level="info",
            description=(
                "Pricing looks fairly normal relative to recent activity, without a strong"
                " low-cost or peak-demand signal."
                f"{comparison}"
            ),
        )
    if current_price < 10:
        return PriceNarrative(
            title="Elevated pricing",
            level="warning",
            description=(
                "The current hour is trending above a normal comfort range, which may justify"
                " delaying optional usage if you are load-shifting."
                f"{comparison}"
            ),
        )
    return PriceNarrative(
        title="Peak-demand pricing",
        level="error",
        description=(
            "Prices are at the expensive end of the recent range, suggesting a stronger"
            " demand period or tighter supply conditions."
            f"{comparison}"
        ),
    )


def build_trend_chart_data(
    df: pd.DataFrame,
    *,
    price_column: str = "price",
    timestamp_column: str = "timestamp",
    rolling_window: int = 12,
    base_label: str = "Observed price",
    rolling_label: str = "Rolling average",
) -> pd.DataFrame:
    """Build a chart-ready DataFrame with a smoothed comparison line."""
    if df.empty or price_column not in df.columns or timestamp_column not in df.columns:
        return pd.DataFrame(columns=[base_label, rolling_label])

    trend_df = (
        df[[timestamp_column, price_column]]
        .dropna()
        .sort_values(timestamp_column)
        .rename(columns={timestamp_column: "timestamp", price_column: base_label})
    )
    trend_df[rolling_label] = trend_df[base_label].rolling(rolling_window, min_periods=1).mean()
    return trend_df.set_index("timestamp")[[base_label, rolling_label]]


def build_hourly_profile(
    df: pd.DataFrame,
    *,
    price_column: str = "price",
    timestamp_column: str = "timestamp",
    value_label: str = "Average price",
) -> pd.DataFrame:
    """Average prices by hour of day for a compact profile chart."""
    if df.empty or price_column not in df.columns or timestamp_column not in df.columns:
        return pd.DataFrame(columns=[value_label])

    profile = (
        df[[timestamp_column, price_column]]
        .dropna()
        .assign(hour_of_day=lambda frame: pd.to_datetime(frame[timestamp_column]).dt.hour)
        .groupby("hour_of_day", as_index=False)[price_column]
        .mean()
    )
    profile["Hour"] = profile["hour_of_day"].apply(
        lambda hour: _format_hour_label(datetime(2000, 1, 1, int(hour)))
    )
    profile["Hour"] = pd.Categorical(
        profile["Hour"],
        categories=_hour_label_order(),
        ordered=True,
    )
    profile = profile.sort_values("Hour")
    return profile.set_index("Hour").rename(columns={price_column: value_label})[[value_label]]


def build_change_profile(
    df: pd.DataFrame,
    *,
    price_column: str = "price",
    timestamp_column: str = "timestamp",
) -> pd.DataFrame:
    """Summarize average movement size by hour of day."""
    if df.empty or price_column not in df.columns or timestamp_column not in df.columns:
        return pd.DataFrame(columns=["Average 5-minute change"])

    working = (
        df[[timestamp_column, price_column]]
        .dropna()
        .sort_values(timestamp_column)
        .assign(
            hour_of_day=lambda frame: pd.to_datetime(frame[timestamp_column]).dt.hour,
            absolute_change=lambda frame: frame[price_column].diff().abs().fillna(0.0),
        )
    )
    profile = working.groupby("hour_of_day", as_index=False)["absolute_change"].mean()
    profile["Hour"] = profile["hour_of_day"].apply(
        lambda hour: _format_hour_label(datetime(2000, 1, 1, int(hour)))
    )
    profile["Hour"] = pd.Categorical(
        profile["Hour"],
        categories=_hour_label_order(),
        ordered=True,
    )
    profile = profile.sort_values("Hour")
    return profile.set_index("Hour").rename(
        columns={"absolute_change": "Average 5-minute change"}
    )[["Average 5-minute change"]]


def build_daily_summary(hourly_df: pd.DataFrame) -> pd.DataFrame:
    """Create a daily rollup with sparkline-ready values."""
    expected_columns = {"hour", "avg_price"}
    if hourly_df.empty or not expected_columns.issubset(hourly_df.columns):
        return pd.DataFrame(
            columns=[
                "Date",
                "Average hourly price",
                "Peak hourly price",
                "Lowest hourly price",
                "Daily spread",
                "Peak hour",
                "Low hour",
                "Hours sampled",
                "Intraday profile",
            ]
        )

    summary_rows: list[dict] = []
    working = hourly_df[["hour", "avg_price"]].dropna().sort_values("hour").copy()
    working["service_date"] = pd.to_datetime(working["hour"]).dt.date

    for service_date, group in working.groupby("service_date", sort=True):
        ordered = group.sort_values("hour").reset_index(drop=True)
        peak_row = ordered.loc[ordered["avg_price"].idxmax()]
        low_row = ordered.loc[ordered["avg_price"].idxmin()]

        summary_rows.append(
            {
                "Date": service_date.isoformat(),
                "Average hourly price": round(float(ordered["avg_price"].mean()), 2),
                "Peak hourly price": round(float(ordered["avg_price"].max()), 2),
                "Lowest hourly price": round(float(ordered["avg_price"].min()), 2),
                "Daily spread": round(
                    float(ordered["avg_price"].max() - ordered["avg_price"].min()),
                    2,
                ),
                "Peak hour": _format_hour_label(pd.to_datetime(peak_row["hour"]).to_pydatetime()),
                "Low hour": _format_hour_label(pd.to_datetime(low_row["hour"]).to_pydatetime()),
                "Hours sampled": int(len(ordered)),
                "Intraday profile": [round(float(value), 2) for value in ordered["avg_price"]],
            }
        )

    return pd.DataFrame(summary_rows)
