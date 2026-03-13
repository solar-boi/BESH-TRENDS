"""Tests for visualization formatting helpers."""
from __future__ import annotations

from datetime import datetime

from dart.visualization.formatting import format_delta, format_price, format_timestamp


class TestFormatPrice:
    def test_formats_positive_price(self):
        assert format_price(5.23) == "5.23¢/kWh"

    def test_formats_negative_price(self):
        assert format_price(-1.5) == "-1.50¢/kWh"

    def test_formats_none(self):
        assert format_price(None) == "N/A"

    def test_formats_zero(self):
        assert format_price(0.0) == "0.00¢/kWh"


class TestFormatDelta:
    def test_positive_delta(self):
        assert format_delta(2.5) == "+2.50¢"

    def test_negative_delta(self):
        assert format_delta(-1.3) == "-1.30¢"

    def test_with_suffix(self):
        assert format_delta(1.0, "vs avg") == "+1.00¢ vs avg"

    def test_none_returns_none(self):
        assert format_delta(None) is None


class TestFormatTimestamp:
    def test_time_only(self):
        dt = datetime(2024, 2, 1, 14, 30)
        assert format_timestamp(dt) == "02:30 PM"

    def test_with_date(self):
        dt = datetime(2024, 2, 1, 14, 30)
        result = format_timestamp(dt, include_date=True)
        assert "Feb 01" in result
        assert "02:30 PM" in result

    def test_none_returns_na(self):
        assert format_timestamp(None) == "N/A"
