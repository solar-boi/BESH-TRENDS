"""
Helpers for building and parsing shareable dashboard links.
"""
from __future__ import annotations

from datetime import datetime
from urllib.parse import parse_qs, quote_plus, urlencode, urlparse, urlunparse

SHARE_DATETIME_FORMAT = "%Y-%m-%dT%H:%M"
SHARE_REF = "range_share"


def format_share_datetime(value: datetime) -> str:
    """Format a datetime for URL query params."""
    return value.strftime(SHARE_DATETIME_FORMAT)


def parse_share_datetime(value: str | None) -> datetime | None:
    """Parse a query param datetime used in share links."""
    if not value:
        return None

    try:
        return datetime.strptime(value, SHARE_DATETIME_FORMAT)
    except ValueError:
        return None


def build_shared_range_url(base_url: str, start: datetime, end: datetime) -> str:
    """Build a sharable URL that opens the dashboard to the same date range."""
    parsed = urlparse(base_url if "://" in base_url else f"http://{base_url}")
    query = parse_qs(parsed.query)

    query["start"] = [format_share_datetime(start)]
    query["end"] = [format_share_datetime(end)]
    query["ref"] = [SHARE_REF]

    encoded_query = urlencode(query, doseq=True)
    return urlunparse(parsed._replace(query=encoded_query))


def build_share_message(
    start: datetime,
    end: datetime,
    avg_price: float,
    min_price: float,
    max_price: float,
    share_url: str,
) -> str:
    """Create copy-ready message text for social or chat sharing."""
    range_text = f"{start.strftime('%b %d %I:%M%p')} - {end.strftime('%b %d %I:%M%p')}"
    return (
        f"ComEd price snapshot: avg {avg_price:.2f}c/kWh "
        f"(low {min_price:.2f}, high {max_price:.2f}) for {range_text}. "
        f"Track live prices here: {share_url}"
    )


def build_x_share_url(message: str) -> str:
    """Build an X intent URL for posting prefilled share copy."""
    return f"https://twitter.com/intent/tweet?text={quote_plus(message)}"
