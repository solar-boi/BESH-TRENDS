"""Cached data access layer for the Streamlit dashboard.

Streamlit's caching decorators live here so that section modules only
deal with rendering, not cache configuration.
"""
from __future__ import annotations

from datetime import date, datetime

import streamlit as st

from dart.models.pricing import CustomRangeResult
from dart.services.pricing_service import PricingService


@st.cache_resource
def get_pricing_service() -> PricingService:
    """Return a singleton PricingService across reruns."""
    return PricingService()


@st.cache_data(ttl=60)
def fetch_api_status(_service: PricingService) -> bool:
    """Fetch API health with a short cache."""
    return _service.is_api_available()


@st.cache_data(ttl=60)
def fetch_current_price(
    _service: PricingService,
) -> tuple[datetime | None, float | None]:
    """Fetch the current-hour average price."""
    try:
        return _service.get_current_price()
    except Exception:
        return None, None


@st.cache_data(ttl=300)
def fetch_last_24_hours(_service: PricingService):
    """Fetch the last 24 hours of raw 5-minute prices."""
    return _service.get_last_24_hours()


@st.cache_data(ttl=300)
def fetch_custom_range_analysis(
    _service: PricingService,
    start_date: date,
    end_date: date,
) -> CustomRangeResult:
    """Fetch canonical custom-range backend result."""
    return _service.get_custom_range_analysis(start_date, end_date)
