"""Native Streamlit dashboard for ComEd pricing."""
from __future__ import annotations

import sys
from datetime import date, datetime, timedelta
from pathlib import Path

import altair as alt
import pandas as pd
import streamlit as st
_repo_root = str(Path(__file__).resolve().parents[2])
if _repo_root not in sys.path:
    sys.path.insert(0, _repo_root)

from dart.config.settings import Config
from dart.models.pricing import CustomRangeResult
from dart.services.pricing_service import PricingService
from dart.utils.helpers import configure_logging
from dart.visualization.ui_helpers import (
    build_change_profile,
    build_daily_summary,
    build_hourly_profile,
    build_price_narrative,
    build_trend_chart_data,
    build_window_highlights,
)

configure_logging()

st.set_page_config(
    page_title=Config.DASHBOARD_TITLE,
    page_icon="⚡",
    layout="wide",
    initial_sidebar_state="expanded",
)


@st.cache_resource
def get_pricing_service() -> PricingService:
    """Get a cached pricing service."""
    return PricingService()


@st.cache_data(ttl=60)
def fetch_api_status(_service: PricingService) -> bool:
    """Fetch API health with short cache."""
    return _service.is_api_available()


@st.cache_data(ttl=60)
def fetch_current_price(_service: PricingService) -> tuple[datetime | None, float | None]:
    """Fetch current hour price."""
    try:
        return _service.get_current_price()
    except Exception:
        return None, None


@st.cache_data(ttl=300)
def fetch_last_24_hours(_service: PricingService):
    """Fetch last 24 hours of raw 5-minute prices."""
    return _service.get_last_24_hours()


@st.cache_data(ttl=300)
def fetch_custom_range_analysis(
    _service: PricingService,
    start_date: date,
    end_date: date,
) -> CustomRangeResult:
    """Fetch canonical custom-range backend result."""
    return _service.get_custom_range_analysis(start_date, end_date)


def _format_price(value: float | None) -> str:
    """Format a price for display."""
    if value is None:
        return "N/A"
    return f"{value:.2f}¢/kWh"


def _format_delta(value: float | None, suffix: str = "") -> str | None:
    """Format a metric delta for prices."""
    if value is None:
        return None
    suffix_text = f" {suffix}" if suffix else ""
    return f"{value:+.2f}¢{suffix_text}"


def _format_timestamp(value: datetime | None, include_date: bool = False) -> str:
    """Format timestamps for compact UI display."""
    if value is None:
        return "N/A"
    if include_date:
        return value.strftime("%b %d, %I:%M %p")
    return value.strftime("%I:%M %p")


def _render_narrative_message(title: str, level: str, description: str) -> None:
    """Render a narrative callout with matching Streamlit status styling."""
    message = f"**{title}**\n\n{description}"
    renderer = {
        "success": st.success,
        "info": st.info,
        "warning": st.warning,
        "error": st.error,
    }.get(level, st.info)
    renderer(message)


def _render_interactive_line_chart(
    df: pd.DataFrame, 
    x_col: str, 
    y_cols: list[str], 
    time_format: str = "%b %d, %I:%M %p",
) -> None:
    """Render an Altair line chart with shared hover tooltips."""
    hover = alt.selection_point(
        fields=[x_col],
        nearest=True,
        on="mouseover",
        empty=False,
    )

    base = alt.Chart(df).encode(x=alt.X(f"{x_col}:T", title=""))

    tooltips_list = [alt.Tooltip(f"{x_col}:T", title="Time", format=time_format)]
    for y_col in y_cols:
        tooltips_list.append(alt.Tooltip(f"{y_col}:Q", title=y_col, format=".2f"))

    rule = base.mark_rule(color="gray").encode(
        opacity=alt.condition(hover, alt.value(0.5), alt.value(0)),
        tooltip=tooltips_list,
    ).add_params(hover)

    melted = df.melt(id_vars=[x_col], value_vars=y_cols, var_name="Metric", value_name="Price")

    lines = alt.Chart(melted).mark_line().encode(
        x=alt.X(f"{x_col}:T", title=""),
        y=alt.Y("Price:Q", title="Price (¢/kWh)"),
        color=alt.Color("Metric:N", legend=alt.Legend(title="", orient="bottom")),
    )

    points = lines.mark_circle().encode(
        opacity=alt.condition(hover, alt.value(1), alt.value(0)),
    )

    chart = (lines + points + rule).interactive()
    st.altair_chart(chart, use_container_width=True)


def render_sidebar(service: PricingService) -> None:
    """Render sidebar controls and reading guidance."""
    st.sidebar.title("Dashboard controls")
    if fetch_api_status(service):
        st.sidebar.success("ComEd API connected")
    else:
        st.sidebar.error("ComEd API unavailable")

    if st.sidebar.button("Refresh data", type="primary", use_container_width=True):
        st.cache_data.clear()
        st.rerun()

    st.sidebar.caption(f"Data refreshes every {Config.AUTO_REFRESH_SECONDS // 60} minutes.")
    st.sidebar.caption(
        f"Audit logging is {'enabled' if Config.PRICING_AUDIT_ENABLED else 'disabled'} "
        f"({Config.PRICING_AUDIT_FILE})."
    )

    with st.sidebar.expander("How to read this dashboard"):
        st.markdown(
            "- **Live snapshot** compares the current ComEd hour against the latest 24-hour range.\n"
            "- **Trend charts** pair the raw signal with a rolling average so spikes are easier to read.\n"
            "- **Hourly pattern views** show which clock hours are typically cheaper or more volatile.\n"
            "- **Custom range** rolls 5-minute data into hour-ending averages for historical review."
        )

    with st.sidebar.expander("Data notes"):
        st.caption(
            "Recent charts use ComEd's 5-minute feed. Historical analysis aggregates those raw values"
            " into hourly averages so longer date ranges are easier to compare."
        )


def render_page_intro() -> None:
    """Render the top-of-page narrative content."""
    st.title("ComEd Real-Time Pricing Dashboard")
    st.caption(
        "A clearer view of live pricing, intraday shape, and historical behavior using only native"
        " Streamlit components."
    )

    with st.expander("What these visuals are designed to answer"):
        st.markdown(
            "- **Is the current hour cheap or expensive?** The live snapshot adds context against the recent 24-hour average.\n"
            "- **When did prices spike or dip?** Trend charts show the raw signal alongside a smoothed line.\n"
            "- **Which hours tend to move the most?** Pattern charts summarize average price levels and movement by clock hour.\n"
            "- **How does a historical period compare day by day?** The custom range view includes daily rollups and sparkline-style intraday profiles."
        )


def render_current_price(service: PricingService) -> None:
    """Render the live snapshot section."""
    st.subheader("Live market snapshot")

    timestamp, price = fetch_current_price(service)
    recent_df = fetch_last_24_hours(service)
    recent_highlights = build_window_highlights(recent_df)

    if price is None:
        st.warning("Unable to fetch the current hour average from ComEd.")
        return

    delta_to_average = None
    if recent_highlights.average_price is not None:
        delta_to_average = price - recent_highlights.average_price

    narrative = build_price_narrative(price, recent_highlights.average_price)
    col1, col2, col3 = st.columns([1.35, 1, 1], gap="large")

    with col1:
        with st.container(border=True):
            st.markdown("##### Current hour")
            st.metric(
                "Average price",
                _format_price(price),
                delta=_format_delta(delta_to_average, "vs 24h average"),
            )
            st.caption(
                f"Updated {_format_timestamp(timestamp, include_date=True)} from the current-hour endpoint."
            )

    with col2:
        with st.container(border=True):
            st.markdown("##### Recent range")
            st.metric("Average price", _format_price(recent_highlights.average_price))
            st.caption(
                f"Observed spread: {_format_price(recent_highlights.spread)} "
                f"from {_format_price(recent_highlights.min_price)} to "
                f"{_format_price(recent_highlights.max_price)}."
            )

    with col3:
        with st.container(border=True):
            st.markdown("##### Market behavior")
            st.metric("Negative intervals", str(recent_highlights.negative_intervals))
            st.caption(
                f"Tracking {recent_highlights.count} recent points ending "
                f"{_format_timestamp(recent_highlights.latest_timestamp, include_date=True)}."
            )

    _render_narrative_message(narrative.title, narrative.level, narrative.description)


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

    m1, m2, m3, m4 = st.columns(4)
    with m1:
        st.metric("24-hour average", _format_price(highlights.average_price))
    with m2:
        st.metric(
            "Highest 5-minute price",
            _format_price(highlights.max_price),
        )
        st.caption(f"At {_format_timestamp(highlights.max_timestamp)}")
    with m3:
        st.metric(
            "Lowest 5-minute price",
            _format_price(highlights.min_price),
        )
        st.caption(f"At {_format_timestamp(highlights.min_timestamp)}")
    with m4:
        st.metric(
            "Observed spread",
            _format_price(highlights.spread),
        )
        st.caption(f"{highlights.negative_intervals} negative intervals")

    trend_tab, pattern_tab, data_tab = st.tabs(["Trend view", "Hourly pattern", "Source data"])

    with trend_tab:
        st.caption(
            "The smoothed line helps you spot whether a spike is sustained or just a short-lived move."
        )
        _render_interactive_line_chart(
            trend_df.reset_index(),
            x_col="timestamp",
            y_cols=trend_df.columns.tolist(),
        )
        c1, c2 = st.columns(2)
        with c1:
            with st.container(border=True):
                st.markdown("##### Peak and trough")
                st.write(
                    f"High: {_format_price(highlights.max_price)} at "
                    f"{_format_timestamp(highlights.max_timestamp, include_date=True)}"
                )
                st.write(
                    f"Low: {_format_price(highlights.min_price)} at "
                    f"{_format_timestamp(highlights.min_timestamp, include_date=True)}"
                )
        with c2:
            with st.container(border=True):
                st.markdown("##### Interpretation")
                if highlights.negative_intervals > 0:
                    st.success(
                        f"The feed dipped below zero {highlights.negative_intervals} times in the last"
                        " 24 hours, which signals at least one unusually soft-demand window."
                    )
                else:
                    st.info(
                        "No negative 5-minute intervals appeared in the last 24 hours, so prices stayed"
                        " above zero throughout the observed window."
                    )

    with pattern_tab:
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

    with data_tab:
        st.caption("Inspect the raw observations or export the 24-hour feed for offline analysis.")
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
                "Start date",
                value=default_start,
                max_value=default_end,
            )
        with col2:
            end_date = st.date_input(
                "End date",
                value=default_end,
                max_value=default_end,
            )
        with col3:
            st.markdown("##### ")
            submitted = st.form_submit_button("Fetch and aggregate", use_container_width=True)

    if not submitted:
        st.info("Choose a start and end date to generate the historical comparison view.")
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
        result.hourly_data,
        price_column="avg_price",
        timestamp_column="hour",
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
            hourly_trend["Hourly average"].rolling(2, min_periods=1).mean()
        )
    clock_hour_profile = build_hourly_profile(
        result.hourly_data,
        price_column="avg_price",
        timestamp_column="hour",
        value_label="Average hourly price",
    )
    daily_summary = build_daily_summary(result.hourly_data)

    m1, m2, m3, m4 = st.columns(4)
    with m1:
        st.metric("Average hourly price", _format_price(result.hourly_stats.average_price))
    with m2:
        st.metric(
            "Highest hour",
            _format_price(result.hourly_stats.max_price),
        )
        st.caption(f"At {_format_timestamp(hourly_highlights.max_timestamp, include_date=True)}")
    with m3:
        st.metric(
            "Lowest hour",
            _format_price(result.hourly_stats.min_price),
        )
        st.caption(f"At {_format_timestamp(hourly_highlights.min_timestamp, include_date=True)}")
    with m4:
        st.metric(
            "Hourly buckets",
            str(result.hourly_stats.count),
        )
        st.caption(f"{result.raw_stats.count} raw points")

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
        with st.container(border=True):
            st.markdown("##### Hourly trend across the selected period")
            _render_interactive_line_chart(
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
                _render_interactive_line_chart(
                    daily_summary,
                    x_col="Date",
                    y_cols=["Average hourly price", "Peak hourly price", "Lowest hourly price"],
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
        _render_narrative_message(
            f"Latest hour in range: {narrative.title}",
            narrative.level,
            narrative.description,
        )

    with daily_tab:
        if daily_summary.empty:
            st.info("Daily summaries become available once at least one hourly bucket is returned.")
        else:
            if len(daily_summary) > 1:
                st.bar_chart(
                    daily_summary.set_index("Date")[["Average hourly price"]],
                    use_container_width=True,
                )
            chart_floor = (
                float(result.hourly_data["avg_price"].min()) if not result.hourly_data.empty else None
            )
            chart_ceiling = (
                float(result.hourly_data["avg_price"].max()) if not result.hourly_data.empty else None
            )
            
            # Use columns to position the localized instruction cleanly
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
                        "Average hourly price (¢/kWh)",
                        format="%.2f",
                    ),
                    "Peak hourly price": st.column_config.NumberColumn(
                        "Peak hourly price (¢/kWh)",
                        format="%.2f",
                    ),
                    "Lowest hourly price": st.column_config.NumberColumn(
                        "Lowest hourly price (¢/kWh)",
                        format="%.2f",
                    ),
                    "Daily spread": st.column_config.NumberColumn(
                        "Daily spread (¢/kWh)",
                        format="%.2f",
                    ),
                    "Hours sampled": st.column_config.NumberColumn("Hours sampled", format="%d"),
                    "Intraday profile": st.column_config.LineChartColumn(
                        "Intraday profile",
                        help="Sparkline of hourly averages across the day.",
                        y_min=chart_floor,
                        y_max=chart_ceiling,
                    ),
                },
            )
            
            # Identify if the user selected a specific daily summary row
            selected_date = None
            if len(event.selection.rows) > 0:
                selected_row = event.selection.rows[0]
                selected_date = daily_summary.iloc[selected_row]["Date"]

    with hourly_tab:
        
        # Filter the underlying result data to the selected day, or show all if none selected
        view_data = result.hourly_data.copy()
        view_profile = clock_hour_profile
        
        if selected_date:
            view_data = view_data[view_data["hour"].dt.strftime("%Y-%m-%d") == selected_date]
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
                 st.caption("This profile averages matching clock hours across the selected range.")
                 
        st.dataframe(
            view_data.rename(columns={"hour": "Hour ending", "avg_price": "Average price"}),
            use_container_width=True,
            hide_index=True,
            height=340,
            column_config={
                "Hour ending": st.column_config.DatetimeColumn("Hour ending"),
                "Average price": st.column_config.NumberColumn(
                    "Average price (¢/kWh)",
                    format="%.2f",
                ),
            },
        )

    with audit_tab:
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
                    "price": st.column_config.NumberColumn("Price (¢/kWh)", format="%.2f"),
                },
            )

        with st.expander("Hourly reconciliation context (raw counts and bounds)"):
            st.dataframe(
                result.hourly_with_context,
                use_container_width=True,
                hide_index=True,
                height=300,
            )


def main() -> None:
    """Main dashboard entry point."""
    service = get_pricing_service()
    render_sidebar(service)
    render_page_intro()
    render_current_price(service)
    st.divider()
    render_last_24_hours(service)
    st.divider()
    render_custom_range(service)


if __name__ == "__main__":
    main()
