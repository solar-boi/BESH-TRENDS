"""Live market snapshot section."""
from __future__ import annotations

import streamlit as st

from dart.services.pricing_service import PricingService
from dart.visualization.data_layer import fetch_current_price, fetch_last_24_hours
from dart.visualization.formatting import format_delta, format_price, format_timestamp
from dart.visualization.ui_helpers import build_price_narrative, build_window_highlights


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

    col1, col2, col3 = st.columns([1, 1, 1], gap="large")

    with col1:
        with st.container(border=True):
            st.markdown("##### Current hour")
            st.metric(
                "Average price",
                format_price(price),
                delta=format_delta(delta_to_average, "vs 24h average"),
            )
            st.caption(
                f" {format_timestamp(timestamp, include_date=True)} via current endpoint."
            )

    with col2:
        with st.container(border=True):
            st.markdown("##### Recent range")
            st.metric("Average price", format_price(recent_highlights.average_price))
            st.caption(
                f"Observed spread: {format_price(recent_highlights.spread)} "
                f"from {format_price(recent_highlights.min_price)} to "
                f"{format_price(recent_highlights.max_price)}."
            )

    with col3:
        with st.container(border=True):
            st.markdown("##### Market behavior")
            st.metric("Negative intervals", str(recent_highlights.negative_intervals))
            st.caption(
                f" {recent_highlights.count} recent points ending "
                f"{format_timestamp(recent_highlights.latest_timestamp, include_date=True)}."
            )

    narrative = build_price_narrative(price, recent_highlights.average_price)
    from dart.visualization.charts import render_narrative_message

    render_narrative_message(
        f"Current hour: {narrative.title}",
        narrative.level,
        narrative.description,
    )
