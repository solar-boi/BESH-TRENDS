"""Sidebar controls and reading guidance."""
from __future__ import annotations

import streamlit as st

from dart.config.settings import Config
from dart.services.pricing_service import PricingService
from dart.visualization.data_layer import fetch_api_status


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

    st.sidebar.caption(
        f"Data refreshes every {Config.AUTO_REFRESH_SECONDS // 60} minutes."
    )
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
