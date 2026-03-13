"""Custom date-range analysis section."""
from __future__ import annotations

from datetime import datetime, timedelta

import streamlit as st

from dart.services.pricing_service import PricingService
from dart.visualization.charts import (
    render_interactive_line_chart,
    render_narrative_message,
)
from dart.visualization.data_layer import fetch_custom_range_analysis
from dart.visualization.formatting import format_price, format_timestamp
from dart.visualization.ui_helpers import (
    build_daily_summary,
    build_hourly_profile,
    build_price_narrative,
    build_trend_chart_data,
    build_window_highlights,
)


def render_custom_range(service: PricingService) -> None:
    """Render custom date range analysis."""
    st.subheader("Custom date range analysis")
    st.caption(
        "Historical comparisons aggregate the raw 5-minute feed into hour-ending averages to keep"
        " longer windows readable."
    )

    default_end = datetime.now().date()
    default_start = default_end - timedelta(days=7)

    with st.form("custom_range_form"):
        col1, col2, col3 = st.columns([1, 1, 0.8])
        with col1:
            start_date = st.date_input(
                "Start date", value=default_start, max_value=default_end
            )
        with col2:
            end_date = st.date_input(
                "End date", value=default_end, max_value=default_end
            )
        with col3:
            st.markdown("##### ")
            submitted = st.form_submit_button(
                "Fetch and aggregate", use_container_width=True
            )

    if not submitted:
        st.info(
            "Choose a start and end date to generate the historical comparison view."
        )
        return

    if start_date > end_date:
        st.error("Start date must be before or equal to end date.")
        return

    with st.spinner("Fetching raw values and computing hourly averages..."):
        result = fetch_custom_range_analysis(service, start_date, end_date)

    if result.raw_data.empty:
        st.warning("No data found for the selected date range.")
        return

    hourly_highlights = build_window_highlights(
        result.hourly_data, price_column="avg_price", timestamp_column="hour"
    )
    hourly_trend = build_trend_chart_data(
        result.hourly_data,
        price_column="avg_price",
        timestamp_column="hour",
        rolling_window=4,
        base_label="Hourly average",
        rolling_label="4-hour rolling average",
    )
    if not hourly_trend.empty:
        hourly_trend.insert(
            1,
            "2-hour rolling average",
            hourly_trend["Hourly average"].rolling(2, min_periods=1).mean(),
        )
    clock_hour_profile = build_hourly_profile(
        result.hourly_data,
        price_column="avg_price",
        timestamp_column="hour",
        value_label="Average hourly price",
    )
    daily_summary = build_daily_summary(result.hourly_data)

    _render_metrics_row(result, hourly_highlights)

    st.info(
        "Hour-ending logic is used here: values from 12:00 through 12:55 are labeled as the 1:00 PM"
        " hour, which matches how utility customers usually review hourly pricing."
    )
    st.caption(
        f"Expanded fetch window: {result.expanded_start} to {result.expanded_end} | "
        f"Requested dates: {result.requested_start_date} to {result.requested_end_date}"
    )

    overview_tab, daily_tab, hourly_tab, audit_tab = st.tabs(
        ["Overview", "Daily summary", "Hourly detail", "Raw & audit"]
    )

    with overview_tab:
        _render_overview_tab(
            hourly_trend,
            daily_summary,
            clock_hour_profile,
            hourly_highlights,
            result,
        )

    selected_date = None
    with daily_tab:
        selected_date = _render_daily_tab(daily_summary, result)

    with hourly_tab:
        _render_hourly_tab(result, clock_hour_profile, selected_date)

    with audit_tab:
        _render_audit_tab(result, start_date, end_date)


def _render_metrics_row(result, hourly_highlights) -> None:
    m1, m2, m3, m4 = st.columns(4)
    with m1:
        st.metric(
            "Average hourly price",
            format_price(result.hourly_stats.average_price),
        )
    with m2:
        st.metric("Highest hour", format_price(result.hourly_stats.max_price))
        st.caption(
            f"At {format_timestamp(hourly_highlights.max_timestamp, include_date=True)}"
        )
    with m3:
        st.metric("Lowest hour", format_price(result.hourly_stats.min_price))
        st.caption(
            f"At {format_timestamp(hourly_highlights.min_timestamp, include_date=True)}"
        )
    with m4:
        st.metric("Hourly buckets", str(result.hourly_stats.count))
        st.caption(f"{result.raw_stats.count} raw points")


def _render_overview_tab(
    hourly_trend, daily_summary, clock_hour_profile, hourly_highlights, result
) -> None:
    with st.container(border=True):
        st.markdown("##### Hourly trend across the selected period")
        render_interactive_line_chart(
            hourly_trend.reset_index(),
            x_col="timestamp",
            y_cols=hourly_trend.columns.tolist(),
        )
        st.caption(
            "The rolling comparison line smooths short-term noise and highlights broader"
            " shifts across the chosen historical window."
        )

    with st.container(border=True):
        if len(daily_summary) > 1:
            st.markdown("##### Daily envelope")
            render_interactive_line_chart(
                daily_summary,
                x_col="Date",
                y_cols=[
                    "Average hourly price",
                    "Peak hourly price",
                    "Lowest hourly price",
                ],
                time_format="%b %d, %Y",
            )
            st.caption(
                "This makes it easier to compare how each day opened, peaked, and settled"
                " within the selected range."
            )
        else:
            st.markdown("##### Average price by clock hour")
            st.bar_chart(clock_hour_profile, use_container_width=True)
            st.caption(
                "A single-day selection uses a clock-hour profile instead of a daily summary."
            )

    narrative = build_price_narrative(
        hourly_highlights.latest_price,
        result.hourly_stats.average_price,
    )
    render_narrative_message(
        f"Latest hour in range: {narrative.title}",
        narrative.level,
        narrative.description,
    )


def _render_daily_tab(daily_summary, result):
    """Render the daily summary tab. Returns the selected date (if any)."""
    selected_date = None

    if daily_summary.empty:
        st.info(
            "Daily summaries become available once at least one hourly bucket is returned."
        )
        return selected_date

    if len(daily_summary) > 1:
        st.bar_chart(
            daily_summary.set_index("Date")[["Average hourly price"]],
            use_container_width=True,
        )

    chart_floor = (
        float(result.hourly_data["avg_price"].min())
        if not result.hourly_data.empty
        else None
    )
    chart_ceiling = (
        float(result.hourly_data["avg_price"].max())
        if not result.hourly_data.empty
        else None
    )

    st.caption("Click any row below to filter the Hourly Detail tab to only that day.")

    event = st.dataframe(
        daily_summary,
        use_container_width=True,
        hide_index=True,
        height=360,
        on_select="rerun",
        selection_mode="single-row",
        column_config={
            "Date": st.column_config.TextColumn("Date"),
            "Average hourly price": st.column_config.NumberColumn(
                "Average hourly price (¢/kWh)", format="%.2f"
            ),
            "Peak hourly price": st.column_config.NumberColumn(
                "Peak hourly price (¢/kWh)", format="%.2f"
            ),
            "Lowest hourly price": st.column_config.NumberColumn(
                "Lowest hourly price (¢/kWh)", format="%.2f"
            ),
            "Daily spread": st.column_config.NumberColumn(
                "Daily spread (¢/kWh)", format="%.2f"
            ),
            "Hours sampled": st.column_config.NumberColumn(
                "Hours sampled", format="%d"
            ),
            "Intraday profile": st.column_config.LineChartColumn(
                "Intraday profile",
                help="Sparkline of hourly averages across the day.",
                y_min=chart_floor,
                y_max=chart_ceiling,
            ),
        },
    )

    if len(event.selection.rows) > 0:
        selected_row = event.selection.rows[0]
        selected_date = daily_summary.iloc[selected_row]["Date"]

    return selected_date


def _render_hourly_tab(result, clock_hour_profile, selected_date) -> None:
    view_data = result.hourly_data.copy()
    view_profile = clock_hour_profile

    if selected_date:
        view_data = view_data[
            view_data["hour"].dt.strftime("%Y-%m-%d") == selected_date
        ]
        view_profile = build_hourly_profile(
            view_data,
            price_column="avg_price",
            timestamp_column="hour",
            value_label="Average hourly price",
        )
        st.info(f"Viewing localized detail for **{selected_date}**.")

    with st.container(border=True):
        st.markdown("##### Average price by clock hour")
        st.bar_chart(view_profile, use_container_width=True)
        if selected_date:
            st.caption(f"Clock hour averages for {selected_date}.")
        else:
            st.caption(
                "This profile averages matching clock hours across the selected range."
            )

    st.dataframe(
        view_data.rename(columns={"hour": "Hour ending", "avg_price": "Average price"}),
        use_container_width=True,
        hide_index=True,
        height=340,
        column_config={
            "Hour ending": st.column_config.DatetimeColumn("Hour ending"),
            "Average price": st.column_config.NumberColumn(
                "Average price (¢/kWh)", format="%.2f"
            ),
        },
    )


def _render_audit_tab(result, start_date, end_date) -> None:
    hourly_csv = result.hourly_data.to_csv(index=False)
    raw_csv = result.raw_data.to_csv(index=False)

    d1, d2 = st.columns(2)
    with d1:
        st.download_button(
            label="Download hourly CSV",
            data=hourly_csv,
            file_name=f"comed_hourly_{start_date}_{end_date}.csv",
            mime="text/csv",
            use_container_width=True,
        )
    with d2:
        st.download_button(
            label="Download raw CSV",
            data=raw_csv,
            file_name=f"comed_raw_{start_date}_{end_date}.csv",
            mime="text/csv",
            use_container_width=True,
        )

    with st.expander("Raw 5-minute values used by aggregation"):
        st.dataframe(
            result.raw_data,
            use_container_width=True,
            hide_index=True,
            height=320,
            column_config={
                "timestamp": st.column_config.DatetimeColumn("Timestamp"),
                "price": st.column_config.NumberColumn(
                    "Price (¢/kWh)", format="%.2f"
                ),
            },
        )

    with st.expander("Hourly reconciliation context (raw counts and bounds)"):
        st.dataframe(
            result.hourly_with_context,
            use_container_width=True,
            hide_index=True,
            height=300,
        )
