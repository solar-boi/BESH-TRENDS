"""
ComEd Real-Time Pricing Dashboard

A Streamlit dashboard for viewing real-time ComEd electricity pricing data
using the ComEd Hourly Pricing API.
"""
import sys
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any

import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

# Adjust sys.path to allow absolute imports from src
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from src.config.settings import Config
from src.services.pricing_service import PricingService
from src.utils.analytics import AnalyticsTracker
from src.utils.share_links import (
    SHARE_REF,
    build_share_message,
    build_shared_range_url,
    build_x_share_url,
    format_share_datetime,
    parse_share_datetime,
)

# Page configuration
st.set_page_config(
    page_title=Config.DASHBOARD_TITLE,
    page_icon="⚡",
    layout="wide",
    initial_sidebar_state="expanded",
)

# Initialize service
@st.cache_resource
def get_pricing_service():
    """Get a cached instance of the pricing service."""
    return PricingService()


@st.cache_resource
def get_analytics_tracker():
    """Get a cached analytics tracker instance."""
    return AnalyticsTracker()


def _get_query_param_value(value: Any) -> str | None:
    """Normalize query param values from Streamlit into a single string."""
    if isinstance(value, list):
        return value[0] if value else None
    if isinstance(value, str):
        return value
    return None


def get_shared_range_from_query_params() -> tuple[datetime | None, datetime | None, str | None]:
    """Parse incoming share link query params."""
    start_raw = _get_query_param_value(st.query_params.get("start"))
    end_raw = _get_query_param_value(st.query_params.get("end"))
    ref_raw = _get_query_param_value(st.query_params.get("ref"))

    start = parse_share_datetime(start_raw)
    end = parse_share_datetime(end_raw)

    if start and end and start < end:
        return start, end, ref_raw
    return None, None, ref_raw


def track_shared_link_open(
    analytics: AnalyticsTracker,
    shared_start: datetime | None,
    shared_end: datetime | None,
    shared_ref: str | None,
) -> None:
    """Track when a recipient opens a shared range link."""
    if not (shared_start and shared_end and shared_ref == SHARE_REF):
        return

    if st.session_state.get("share_link_open_tracked"):
        return

    analytics.track_event(
        "share_link_opened",
        {
            "start": format_share_datetime(shared_start),
            "end": format_share_datetime(shared_end),
            "ref": shared_ref,
        },
    )
    st.session_state["share_link_open_tracked"] = True


def main():
    """Main dashboard entry point."""
    service = get_pricing_service()
    analytics = get_analytics_tracker()
    shared_start, shared_end, shared_ref = get_shared_range_from_query_params()
    track_shared_link_open(analytics, shared_start, shared_end, shared_ref)
    
    # Sidebar controls
    st.sidebar.title("Dashboard Controls")
    
    # API status indicator
    api_status = service.is_api_available()
    if api_status:
        st.sidebar.success("✓ ComEd API Connected")
    else:
        st.sidebar.error("✗ ComEd API Unavailable")
    
    # Refresh button
    if st.sidebar.button("🔄 Refresh Data", type="primary"):
        st.cache_data.clear()
        st.rerun()
    
    # Auto-refresh info
    st.sidebar.caption(
        f"Data refreshes every {Config.AUTO_REFRESH_SECONDS // 60} minutes"
    )
    
    # Main content
    st.title("⚡ ComEd Real-Time Pricing Dashboard")
    
    # Current price section
    render_current_price(service)
    
    st.divider()
    
    # 5-minute prices section
    render_five_minute_prices(service)
    
    st.divider()
    
    # Custom date range section
    render_custom_range(service, analytics, shared_start, shared_end, shared_ref)
    
    st.divider()
    
    # Statistics section
    render_statistics(service)


@st.cache_data(ttl=60)  # Cache for 1 minute
def fetch_current_price(_service: PricingService):
    """Fetch current price with caching."""
    try:
        return _service.get_current_price()
    except Exception as e:
        st.error(f"Failed to fetch current price: {e}")
        return None, None


@st.cache_data(ttl=300)  # Cache for 5 minutes
def fetch_last_24_hours(_service: PricingService):
    """Fetch last 24 hours of data with caching."""
    return _service.get_last_24_hours()


@st.cache_data(ttl=300)
def fetch_custom_range(_service: PricingService, start: datetime, end: datetime):
    """Fetch custom range data with caching."""
    return _service.get_custom_range(start, end)


@st.cache_data(ttl=300)
def fetch_statistics(_service: PricingService):
    """Fetch statistics with caching."""
    return _service.get_price_statistics()


def render_current_price(service: PricingService):
    """Render the current price section."""
    st.subheader("💰 Current Price")
    
    timestamp, price = fetch_current_price(service)
    
    if price is not None:
        col1, col2, col3 = st.columns(3)
        
        with col1:
            st.metric(
                label="Current Hour Average",
                value=f"{price:.2f}¢/kWh",
            )
        
        with col2:
            st.metric(
                label="Last Updated",
                value=timestamp.strftime("%I:%M %p") if timestamp else "N/A",
            )
        
        with col3:
            st.metric(
                label="Date",
                value=timestamp.strftime("%b %d, %Y") if timestamp else "N/A",
            )
    else:
        st.warning("Unable to fetch current price. Please try refreshing.")


def render_five_minute_prices(service: PricingService):
    """Render the 5-minute prices section."""
    st.subheader("📈 Last 24 Hours (5-Minute Intervals)")
    
    df = fetch_last_24_hours(service)
    
    if df.empty:
        st.warning("No pricing data available. Please try refreshing.")
        return
    
    # Calculate statistics for display
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric("Average", f"{df['price'].mean():.2f}¢/kWh")
    with col2:
        st.metric("Maximum", f"{df['price'].max():.2f}¢/kWh")
    with col3:
        st.metric("Minimum", f"{df['price'].min():.2f}¢/kWh")
    with col4:
        st.metric("Data Points", f"{len(df)}")
    
    # Create interactive chart
    fig = go.Figure()
    
    fig.add_trace(go.Scatter(
        x=df["timestamp"],
        y=df["price"],
        mode="lines",
        name="Price",
        line=dict(color="#1E88E5", width=2),
        hovertemplate="Time: %{x}<br>Price: %{y:.2f}¢/kWh<extra></extra>",
    ))
    
    # Add average line
    avg_price = df["price"].mean()
    fig.add_hline(
        y=avg_price,
        line_dash="dash",
        line_color="gray",
        annotation_text=f"Avg: {avg_price:.2f}¢",
        annotation_position="right",
    )
    
    fig.update_layout(
        title="5-Minute Real-Time Prices",
        xaxis_title="Time",
        yaxis_title="Price (¢/kWh)",
        hovermode="x unified",
        template="plotly_white",
        height=500,
    )
    
    st.plotly_chart(fig, use_container_width=True)
    
    # Expandable data table
    with st.expander("📋 View Raw Data"):
        # Show most recent first
        display_df = df.sort_values("timestamp", ascending=False).copy()
        display_df["timestamp"] = display_df["timestamp"].dt.strftime("%Y-%m-%d %H:%M")
        display_df["price"] = display_df["price"].apply(lambda x: f"{x:.2f}¢")
        display_df.columns = ["Time", "Price"]
        st.dataframe(display_df, use_container_width=True, height=300)


def render_custom_range(
    service: PricingService,
    analytics: AnalyticsTracker,
    shared_start: datetime | None,
    shared_end: datetime | None,
    shared_ref: str | None,
):
    """Render the custom date range section."""
    st.subheader("📅 Custom Date Range")
    
    col1, col2 = st.columns(2)
    
    # Default to last 7 days
    default_end = datetime.now()
    default_start = default_end - timedelta(days=7)
    if shared_start and shared_end:
        default_start = shared_start
        default_end = shared_end
        if shared_ref == SHARE_REF:
            st.info("Opened from a shared link. This range is preloaded for you.")
    
    with col1:
        start_date = st.date_input(
            "Start Date",
            value=default_start.date(),
            max_value=datetime.now().date(),
            key="custom_start_date",
        )
        start_time = st.time_input(
            "Start Time",
            value=default_start.time().replace(second=0, microsecond=0),
            key="custom_start_time",
        )
    
    with col2:
        end_date = st.date_input(
            "End Date",
            value=default_end.date(),
            max_value=datetime.now().date(),
            key="custom_end_date",
        )
        end_time = st.time_input(
            "End Time",
            value=default_end.time().replace(second=0, microsecond=0),
            key="custom_end_time",
        )
    
    start_datetime = datetime.combine(start_date, start_time)
    end_datetime = datetime.combine(end_date, end_time)
    
    should_fetch = st.button("🔍 Fetch Data", key="fetch_custom")
    if shared_start and shared_end and not st.session_state.get("shared_range_auto_loaded"):
        should_fetch = True
        st.session_state["shared_range_auto_loaded"] = True

    if should_fetch:
        if start_datetime >= end_datetime:
            st.error("Start time must be before end time.")
            return
        
        with st.spinner("Fetching data..."):
            df = fetch_custom_range(service, start_datetime, end_datetime)
        
        if df.empty:
            st.warning("No data found for the selected range.")
            return
        
        # Display stats
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("Average", f"{df['price'].mean():.2f}¢/kWh")
        with col2:
            st.metric("Max", f"{df['price'].max():.2f}¢/kWh")
        with col3:
            st.metric("Min", f"{df['price'].min():.2f}¢/kWh")
        
        # Chart
        fig = px.line(
            df,
            x="timestamp",
            y="price",
            title=f"Prices from {start_datetime.strftime('%Y-%m-%d %H:%M')} to {end_datetime.strftime('%Y-%m-%d %H:%M')}",
        )
        fig.update_layout(
            xaxis_title="Time",
            yaxis_title="Price (¢/kWh)",
            template="plotly_white",
            height=400,
        )
        st.plotly_chart(fig, use_container_width=True)
        
        # Download button
        download_df = df.copy()
        download_df["timestamp"] = download_df["timestamp"].dt.strftime("%Y-%m-%d %H:%M:%S")
        download_df.columns = ["DateTime", "Price (¢/kWh)"]
        csv_data = download_df.to_csv(index=False)
        
        st.download_button(
            label="📥 Download CSV",
            data=csv_data,
            file_name=f"comed_prices_{start_datetime.strftime('%Y%m%d')}_{end_datetime.strftime('%Y%m%d')}.csv",
            mime="text/csv",
        )

        render_share_range_actions(analytics, start_datetime, end_datetime, df)


def render_share_range_actions(
    analytics: AnalyticsTracker,
    start_datetime: datetime,
    end_datetime: datetime,
    df,
):
    """Render one-click sharing actions for a fetched custom range."""
    st.markdown("#### 🔗 Share This Price Snapshot")
    share_url = build_shared_range_url(
        Config.DASHBOARD_SHARE_BASE_URL,
        start_datetime,
        end_datetime,
    )
    share_message = build_share_message(
        start_datetime,
        end_datetime,
        float(df["price"].mean()),
        float(df["price"].min()),
        float(df["price"].max()),
        share_url,
    )

    if st.button("Create Share Link", key="create_share_link"):
        st.session_state["custom_range_share"] = {
            "start": format_share_datetime(start_datetime),
            "end": format_share_datetime(end_datetime),
            "url": share_url,
            "message": share_message,
        }
        analytics.track_event(
            "share_link_created",
            {
                "start": format_share_datetime(start_datetime),
                "end": format_share_datetime(end_datetime),
                "avg_price": round(float(df["price"].mean()), 2),
            },
        )

    share_payload = st.session_state.get("custom_range_share")
    if not share_payload:
        return

    if (
        share_payload.get("start") != format_share_datetime(start_datetime)
        or share_payload.get("end") != format_share_datetime(end_datetime)
    ):
        return

    st.success("Share link ready. Copy and send it.")
    st.code(share_payload["url"])
    st.code(share_payload["message"])
    st.link_button("Post on X", build_x_share_url(share_payload["message"]))


def render_statistics(service: PricingService):
    """Render the statistics section."""
    st.subheader("📊 24-Hour Statistics")
    
    stats = fetch_statistics(service)
    
    if not stats or stats.get("count", 0) == 0:
        st.warning("No statistics available.")
        return
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.metric(
            "Average Price",
            f"{stats['average']:.2f}¢/kWh" if stats['average'] else "N/A",
        )
    
    with col2:
        st.metric(
            "Price Range",
            f"{stats['min']:.2f}¢ - {stats['max']:.2f}¢" if stats['min'] and stats['max'] else "N/A",
        )
    
    with col3:
        st.metric(
            "Data Points",
            f"{stats['count']}",
        )
    
    # Price distribution
    df = fetch_last_24_hours(service)
    
    if not df.empty:
        fig = px.histogram(
            df,
            x="price",
            nbins=30,
            title="Price Distribution (Last 24 Hours)",
            labels={"price": "Price (¢/kWh)", "count": "Frequency"},
        )
        fig.update_layout(
            template="plotly_white",
            height=300,
        )
        st.plotly_chart(fig, use_container_width=True)


# Run the dashboard
if __name__ == "__main__":
    main()
