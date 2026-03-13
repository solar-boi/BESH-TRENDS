"""Last-24-hours section with trend, pattern, and source-data tabs."""
from __future__ import annotations

import streamlit as st

from dart.services.pricing_service import PricingService
from dart.visualization.charts import render_interactive_line_chart
from dart.visualization.data_layer import fetch_last_24_hours
from dart.visualization.formatting import format_price, format_timestamp
from dart.visualization.ui_helpers import (
    build_change_profile,
    build_hourly_profile,
    build_trend_chart_data,
    build_window_highlights,
)


def render_last_24_hours(service: PricingService) -> None:
    """Render the enhanced 24-hour raw data section."""
    st.subheader("Last 24 hours")
    df = fetch_last_24_hours(service)

    if df.empty:
        st.warning("No 24-hour pricing data is currently available.")
        return

    highlights = build_window_highlights(df)
    trend_df = build_trend_chart_data(
        df,
        rolling_window=12,
        base_label="5-minute price",
        rolling_label="1-hour rolling average",
    )
    hourly_profile = build_hourly_profile(df, value_label="Average 5-minute price")
    change_profile = build_change_profile(df)

    _render_metrics_row(highlights)

    trend_tab, pattern_tab, data_tab = st.tabs(
        ["Trend view", "Hourly pattern", "Source data"]
    )

    with trend_tab:
        _render_trend_tab(trend_df, highlights)

    with pattern_tab:
        _render_pattern_tab(hourly_profile, change_profile)

    with data_tab:
        _render_data_tab(df)


def _render_metrics_row(highlights) -> None:
    m1, m2, m3, m4 = st.columns(4)
    with m1:
        st.metric("24-hour average", format_price(highlights.average_price))
    with m2:
        st.metric("Highest 5-minute price", format_price(highlights.max_price))
        st.caption(f"At {format_timestamp(highlights.max_timestamp)}")
    with m3:
        st.metric("Lowest 5-minute price", format_price(highlights.min_price))
        st.caption(f"At {format_timestamp(highlights.min_timestamp)}")
    with m4:
        st.metric("Observed spread", format_price(highlights.spread))
        st.caption(f"{highlights.negative_intervals} negative intervals")


def _render_trend_tab(trend_df, highlights) -> None:
    st.caption(
        "The smoothed line helps you spot whether a spike is sustained or just a short-lived move."
    )
    render_interactive_line_chart(
        trend_df.reset_index(),
        x_col="timestamp",
        y_cols=trend_df.columns.tolist(),
    )
    c1, c2 = st.columns(2)
    with c1:
        with st.container(border=True):
            st.markdown("##### Peak and trough")
            st.write(
                f"High: {format_price(highlights.max_price)} at "
                f"{format_timestamp(highlights.max_timestamp, include_date=True)}"
            )
            st.write(
                f"Low: {format_price(highlights.min_price)} at "
                f"{format_timestamp(highlights.min_timestamp, include_date=True)}"
            )
    with c2:
        with st.container(border=True):
            st.markdown("##### Trend summary")
            if highlights.spread is not None:
                st.write(
                    f"The 24-hour spread is {format_price(highlights.spread)}, "
                    f"across {highlights.count} data points."
                )


def _render_pattern_tab(hourly_profile, change_profile) -> None:
    c1, c2 = st.columns(2, gap="large")
    with c1:
        with st.container(border=True):
            st.markdown("##### Average price by clock hour")
            st.bar_chart(hourly_profile, use_container_width=True)
            st.caption(
                "This view makes it easier to compare whether mornings, afternoons, or evenings"
                " carried the highest prices over the latest day."
            )
    with c2:
        with st.container(border=True):
            st.markdown("##### Average movement by clock hour")
            st.bar_chart(change_profile, use_container_width=True)
            st.caption(
                "Bigger bars indicate clock hours where the 5-minute feed moved more abruptly."
            )


def _render_data_tab(df) -> None:
    st.caption(
        "Inspect the raw observations or export the 24-hour feed for offline analysis."
    )
    st.dataframe(
        df.sort_values("timestamp", ascending=False),
        use_container_width=True,
        hide_index=True,
        height=320,
        column_config={
            "timestamp": st.column_config.DatetimeColumn("Timestamp"),
            "price": st.column_config.NumberColumn("Price (¢/kWh)", format="%.2f"),
        },
    )
    st.download_button(
        label="Download last 24-hour CSV",
        data=df.to_csv(index=False),
        file_name="comed_last_24_hours.csv",
        mime="text/csv",
    )
