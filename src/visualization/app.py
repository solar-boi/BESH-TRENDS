"""Native Streamlit dashboard for ComEd pricing."""
from __future__ import annotations

import sys
from datetime import date, datetime, timedelta
from pathlib import Path

import streamlit as st

# Adjust sys.path to allow absolute imports from src
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from src.config.settings import Config
from src.models.pricing import CustomRangeResult
from src.services.pricing_service import PricingService
from src.utils.helpers import configure_logging

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


@st.cache_data(ttl=300)
def fetch_statistics(_service: PricingService) -> dict:
    """Fetch backend-computed statistics."""
    return _service.get_price_statistics()


def render_sidebar(service: PricingService) -> None:
    """Render simple dashboard controls."""
    st.sidebar.title("Dashboard Controls")
    if fetch_api_status(service):
        st.sidebar.success("ComEd API Connected")
    else:
        st.sidebar.error("ComEd API Unavailable")

    if st.sidebar.button("Refresh Data", type="primary"):
        st.cache_data.clear()
        st.rerun()

    st.sidebar.caption(f"Data refreshes every {Config.AUTO_REFRESH_SECONDS // 60} minutes")
    st.sidebar.caption(
        f"Audit logging: {'enabled' if Config.PRICING_AUDIT_ENABLED else 'disabled'} "
        f"({Config.PRICING_AUDIT_FILE})"
    )


def render_current_price(service: PricingService) -> None:
    """Render current hour average price."""
    st.subheader("Current Price")
    timestamp, price = fetch_current_price(service)

    if price is None:
        st.warning("Unable to fetch current hour average.")
        return

    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("Current Hour Average", f"{price:.2f}¢/kWh")
    with col2:
        st.metric("Last Updated", timestamp.strftime("%I:%M %p") if timestamp else "N/A")
    with col3:
        st.metric("Date", timestamp.strftime("%Y-%m-%d") if timestamp else "N/A")


def render_last_24_hours(service: PricingService) -> None:
    """Render 24-hour raw data section."""
    st.subheader("Last 24 Hours (Raw 5-Minute Data)")
    df = fetch_last_24_hours(service)

    if df.empty:
        st.warning("No pricing data available.")
        return

    stats = fetch_statistics(service)
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("Average", f"{stats['average']:.2f}¢/kWh" if stats["average"] is not None else "N/A")
    with col2:
        st.metric("Maximum", f"{stats['max']:.2f}¢/kWh" if stats["max"] is not None else "N/A")
    with col3:
        st.metric("Minimum", f"{stats['min']:.2f}¢/kWh" if stats["min"] is not None else "N/A")
    with col4:
        st.metric("Data Points", str(stats["count"]))

    st.line_chart(df.set_index("timestamp")["price"], use_container_width=True)
    with st.expander("View raw 5-minute values"):
        st.dataframe(df.sort_values("timestamp", ascending=False), use_container_width=True, height=300)


def render_custom_range(service: PricingService) -> None:
    """Render custom date range analysis."""
    st.subheader("Custom Date Range (Backend Aggregation + Audit)")

    default_end = datetime.now().date()
    default_start = default_end - timedelta(days=7)

    with st.form("custom_range_form"):
        col1, col2 = st.columns(2)
        with col1:
            start_date = st.date_input(
                "Start Date",
                value=default_start,
                max_value=default_end,
            )
        with col2:
            end_date = st.date_input(
                "End Date",
                value=default_end,
                max_value=default_end,
            )
        submitted = st.form_submit_button("Fetch and Aggregate")

    if not submitted:
        return

    if start_date > end_date:
        st.error("Start date must be before or equal to end date.")
        return

    with st.spinner("Fetching raw values and computing hourly averages..."):
        result = fetch_custom_range_analysis(service, start_date, end_date)

    if result.raw_data.empty:
        st.warning("No data found for selected date range.")
        return

    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("Hourly Avg", f"{result.hourly_stats.average_price:.2f}¢/kWh")
    with col2:
        st.metric("Hourly Max", f"{result.hourly_stats.max_price:.2f}¢/kWh")
    with col3:
        st.metric("Hourly Min", f"{result.hourly_stats.min_price:.2f}¢/kWh")

    st.caption(
        f"Expanded fetch window: {result.expanded_start} to {result.expanded_end} "
        f"| Raw points: {result.raw_stats.count} | Hourly buckets: {result.hourly_stats.count}"
    )

    st.line_chart(
        result.hourly_data.set_index("hour")["avg_price"],
        use_container_width=True,
    )

    st.markdown("Hourly Averages")
    st.dataframe(result.hourly_data, use_container_width=True, height=250)

    with st.expander("Raw 5-minute values used by aggregation"):
        st.dataframe(result.raw_data, use_container_width=True, height=300)

    with st.expander("Hourly reconciliation context (raw counts and bounds)"):
        st.dataframe(result.hourly_with_context, use_container_width=True, height=250)

    hourly_csv = result.hourly_data.to_csv(index=False)
    raw_csv = result.raw_data.to_csv(index=False)
    c1, c2 = st.columns(2)
    with c1:
        st.download_button(
            label="Download hourly CSV",
            data=hourly_csv,
            file_name=f"comed_hourly_{start_date}_{end_date}.csv",
            mime="text/csv",
        )
    with c2:
        st.download_button(
            label="Download raw CSV",
            data=raw_csv,
            file_name=f"comed_raw_{start_date}_{end_date}.csv",
            mime="text/csv",
        )


def main() -> None:
    """Main dashboard entry point."""
    service = get_pricing_service()
    render_sidebar(service)

    st.title("ComEd Real-Time Pricing Dashboard")
    render_current_price(service)
    st.divider()
    render_last_24_hours(service)
    st.divider()
    render_custom_range(service)


if __name__ == "__main__":
    main()
