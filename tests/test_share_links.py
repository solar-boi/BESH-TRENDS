"""
Unit tests for share link utility helpers.
"""
from datetime import datetime

from dart.utils.share_links import (
    SHARE_REF,
    build_share_message,
    build_shared_range_url,
    build_x_share_url,
    parse_share_datetime,
)


class TestShareLinks:
    """Tests for share link helpers."""

    def test_build_shared_range_url_includes_expected_query_params(self):
        """Share URL should include start/end/ref params."""
        start = datetime(2024, 2, 1, 8, 15)
        end = datetime(2024, 2, 1, 10, 45)

        url = build_shared_range_url("https://dart.example.com", start, end)

        assert "start=2024-02-01T08%3A15" in url
        assert "end=2024-02-01T10%3A45" in url
        assert f"ref={SHARE_REF}" in url

    def test_parse_share_datetime_valid_and_invalid_values(self):
        """Parses valid datetimes and rejects invalid strings."""
        parsed = parse_share_datetime("2024-02-01T08:15")
        invalid = parse_share_datetime("2024/02/01 08:15")

        assert parsed == datetime(2024, 2, 1, 8, 15)
        assert invalid is None

    def test_build_share_message_contains_range_and_prices(self):
        """Generated message should include key snapshot values."""
        start = datetime(2024, 2, 1, 8, 0)
        end = datetime(2024, 2, 1, 9, 0)
        message = build_share_message(
            start=start,
            end=end,
            avg_price=4.23,
            min_price=3.10,
            max_price=6.05,
            share_url="https://dart.example.com?start=2024-02-01T08%3A00",
        )

        assert "avg 4.23c/kWh" in message
        assert "low 3.10, high 6.05" in message
        assert "Track live prices here:" in message

    def test_build_x_share_url_encodes_spaces(self):
        """X share URL should URL-encode text payload."""
        url = build_x_share_url("price alert now")

        assert url.startswith("https://twitter.com/intent/tweet?text=")
        assert "price+alert+now" in url
