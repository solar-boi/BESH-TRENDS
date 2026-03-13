"""Streamlit dashboard entry point.

This module configures the page and orchestrates the section renderers.
All data fetching, formatting, chart building, and section rendering
live in dedicated modules under ``dart.visualization``.
"""
from __future__ import annotations

import streamlit as st

from dart.config.settings import Config
from dart.utils.helpers import configure_logging
from dart.visualization.data_layer import get_pricing_service
from dart.visualization.sections.custom_range import render_custom_range
from dart.visualization.sections.header import render_page_intro
from dart.visualization.sections.live_snapshot import render_current_price
from dart.visualization.sections.recent_prices import render_last_24_hours
from dart.visualization.sections.sidebar import render_sidebar

configure_logging()

st.set_page_config(
    page_title=Config.DASHBOARD_TITLE,
    page_icon="⚡",
    layout="wide",
    initial_sidebar_state="expanded",
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
