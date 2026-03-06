"""
Unit tests for pricing data models.
"""
import pytest
import pandas as pd
from datetime import datetime

from dart.models.pricing import CustomRangeResult, PricePoint, PriceResponse, PriceStats


class TestPricePoint:
    """Tests for PricePoint dataclass."""

    def test_create_price_point(self):
        """Can create a valid PricePoint."""
        timestamp = datetime(2024, 2, 1, 12, 0)
        point = PricePoint(timestamp=timestamp, price=5.5)
        
        assert point.timestamp == timestamp
        assert point.price == 5.5

    def test_negative_price_is_valid(self):
        """Negative price is allowed (can occur during oversupply)."""
        point = PricePoint(timestamp=datetime.now(), price=-1.0)
        assert point.price == -1.0

    def test_zero_price_is_valid(self):
        """Zero price is allowed."""
        point = PricePoint(timestamp=datetime.now(), price=0.0)
        assert point.price == 0.0

    def test_from_api_response(self):
        """Can create from API response dict."""
        data = {"millisUTC": "1706817600000", "price": "5.2"}
        point = PricePoint.from_api_response(data)
        
        assert point.price == 5.2
        assert point.timestamp.year == 2024

    def test_from_api_response_missing_key(self):
        """Raises KeyError when required key is missing."""
        data = {"price": "5.2"}  # Missing millisUTC
        
        with pytest.raises(KeyError):
            PricePoint.from_api_response(data)

    def test_immutable(self):
        """PricePoint is immutable (frozen)."""
        point = PricePoint(timestamp=datetime.now(), price=5.0)
        
        with pytest.raises(AttributeError):
            point.price = 6.0


class TestPriceResponse:
    """Tests for PriceResponse dataclass."""

    def test_empty_response(self):
        """Empty response is valid."""
        response = PriceResponse()
        
        assert len(response) == 0
        assert not response  # Falsy
        assert response.latest is None
        assert response.earliest is None
        assert response.average_price is None

    def test_with_prices(self):
        """Response with prices calculates statistics."""
        prices = [
            PricePoint(timestamp=datetime(2024, 2, 1, 12, 0), price=5.0),
            PricePoint(timestamp=datetime(2024, 2, 1, 12, 5), price=6.0),
            PricePoint(timestamp=datetime(2024, 2, 1, 12, 10), price=7.0),
        ]
        response = PriceResponse(prices=prices)
        
        assert len(response) == 3
        assert response  # Truthy
        assert response.average_price == 6.0
        assert response.min_price == 5.0
        assert response.max_price == 7.0

    def test_latest_and_earliest(self):
        """Correctly identifies latest and earliest prices."""
        prices = [
            PricePoint(timestamp=datetime(2024, 2, 1, 12, 5), price=5.5),
            PricePoint(timestamp=datetime(2024, 2, 1, 12, 0), price=5.0),
            PricePoint(timestamp=datetime(2024, 2, 1, 12, 10), price=6.0),
        ]
        response = PriceResponse(prices=prices)
        
        assert response.earliest.timestamp == datetime(2024, 2, 1, 12, 0)
        assert response.latest.timestamp == datetime(2024, 2, 1, 12, 10)

    def test_to_dataframe(self):
        """Converts to sorted DataFrame."""
        prices = [
            PricePoint(timestamp=datetime(2024, 2, 1, 12, 10), price=6.0),
            PricePoint(timestamp=datetime(2024, 2, 1, 12, 0), price=5.0),
            PricePoint(timestamp=datetime(2024, 2, 1, 12, 5), price=5.5),
        ]
        response = PriceResponse(prices=prices)
        df = response.to_dataframe()
        
        assert isinstance(df, pd.DataFrame)
        assert len(df) == 3
        assert list(df.columns) == ["timestamp", "price"]
        # Should be sorted by timestamp
        assert df.iloc[0]["price"] == 5.0
        assert df.iloc[2]["price"] == 6.0

    def test_to_dataframe_empty(self):
        """Empty response returns empty DataFrame with columns."""
        response = PriceResponse()
        df = response.to_dataframe()
        
        assert isinstance(df, pd.DataFrame)
        assert df.empty
        assert list(df.columns) == ["timestamp", "price"]

    def test_from_api_response(self):
        """Creates from list of API response dicts."""
        data = [
            {"millisUTC": "1706817600000", "price": "5.0"},
            {"millisUTC": "1706817900000", "price": "5.5"},
        ]
        response = PriceResponse.from_api_response(data)
        
        assert len(response) == 2
        assert response.prices[0].price == 5.0
        assert response.prices[1].price == 5.5


class TestResultModels:
    """Tests for typed result models."""

    def test_price_stats(self):
        stats = PriceStats(min_price=1.0, max_price=3.0, average_price=2.0, count=2)
        assert stats.min_price == 1.0
        assert stats.max_price == 3.0
        assert stats.average_price == 2.0
        assert stats.count == 2

    def test_custom_range_result(self):
        raw_df = pd.DataFrame({"timestamp": [datetime(2024, 2, 1, 12, 0)], "price": [5.2]})
        hourly_df = pd.DataFrame({"hour": [datetime(2024, 2, 1, 13, 0)], "avg_price": [5.2]})
        result = CustomRangeResult(
            requested_start_date=datetime(2024, 2, 1).date(),
            requested_end_date=datetime(2024, 2, 1).date(),
            expanded_start=datetime(2024, 2, 1, 0, 0),
            expanded_end=datetime(2024, 2, 1, 23, 59),
            raw_data=raw_df,
            hourly_data=hourly_df,
            raw_stats=PriceStats(min_price=5.2, max_price=5.2, average_price=5.2, count=1),
            hourly_stats=PriceStats(min_price=5.2, max_price=5.2, average_price=5.2, count=1),
            hourly_with_context=hourly_df,
        )
        assert result.raw_stats.count == 1
        assert result.hourly_stats.average_price == 5.2
