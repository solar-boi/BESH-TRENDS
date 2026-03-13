"""Page introduction / header section."""
from __future__ import annotations

import streamlit as st


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
