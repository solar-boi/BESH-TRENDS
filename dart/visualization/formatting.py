"""Display formatting helpers used across dashboard sections."""
from __future__ import annotations

from datetime import datetime


def format_price(value: float | None) -> str:
    """Format a price in cents/kWh for display."""
    if value is None:
        return "N/A"
    return f"{value:.2f}¢/kWh"


def format_delta(value: float | None, suffix: str = "") -> str | None:
    """Format a metric delta for prices."""
    if value is None:
        return None
    suffix_text = f" {suffix}" if suffix else ""
    return f"{value:+.2f}¢{suffix_text}"


def format_timestamp(value: datetime | None, include_date: bool = False) -> str:
    """Format timestamps for compact UI display."""
    if value is None:
        return "N/A"
    if include_date:
        return value.strftime("%b %d, %I:%M %p")
    return value.strftime("%I:%M %p")
