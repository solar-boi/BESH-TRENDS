"""
Unit tests for the PricingService.
"""
import pytest
import pandas as pd
from datetime import date, datetime
from unittest.mock import Mock

from dart.services.pricing_service import PricingService
from dart.models.pricing import PricePoint, PriceResponse


# Sample data for testing
def create_sample_response():
    """Create a sample PriceResponse for testing."""
    prices = [
        PricePoint(timestamp=datetime(2024, 2, 1, 12, 0), price=5.2),
        PricePoint(timestamp=datetime(2024, 2, 1, 12, 5), price=5.5),
        PricePoint(timestamp=datetime(2024, 2, 1, 12, 10), price=5.1),
        PricePoint(timestamp=datetime(2024, 2, 1, 13, 0), price=6.0),
        PricePoint(timestamp=datetime(2024, 2, 1, 13, 5), price=6.2),
    ]
    return PriceResponse(prices=prices)


class TestPricingService:
    """Tests for PricingService."""

    def test_init_default_client(self):
        """Service creates default client if none provided."""
        service = PricingService()
        assert service.client is not None

    def test_init_custom_client(self):
        """Service accepts custom client."""
        mock_client = Mock()
        service = PricingService(client=mock_client)
        assert service.client is mock_client

    def test_get_last_24_hours_success(self):
        """Returns DataFrame from 5-minute prices."""
        mock_client = Mock()
        mock_client.get_five_minute_prices.return_value = create_sample_response()
        
        service = PricingService(client=mock_client)
        df = service.get_last_24_hours()

        assert isinstance(df, pd.DataFrame)
        assert len(df) == 5
        assert "timestamp" in df.columns
        assert "price" in df.columns
        mock_client.get_five_minute_prices.assert_called_once()

    def test_get_last_24_hours_error_returns_empty_df(self):
        """Returns empty DataFrame on error."""
        mock_client = Mock()
        mock_client.get_five_minute_prices.side_effect = Exception("API error")
        
        service = PricingService(client=mock_client)
        df = service.get_last_24_hours()

        assert isinstance(df, pd.DataFrame)
        assert df.empty
        assert list(df.columns) == ["timestamp", "price"]

    def test_get_custom_range_success(self):
        """Returns DataFrame for custom date range."""
        mock_client = Mock()
        mock_client.get_five_minute_prices_range.return_value = create_sample_response()
        
        service = PricingService(client=mock_client)
        start = datetime(2024, 2, 1, 8, 0)
        end = datetime(2024, 2, 1, 17, 0)
        df = service.get_custom_range(start, end)

        assert isinstance(df, pd.DataFrame)
        assert len(df) == 5
        mock_client.get_five_minute_prices_range.assert_called_once_with(start, end)

    def test_get_custom_range_invalid_dates(self):
        """Raises ValueError when start is after end."""
        service = PricingService()
        start = datetime(2024, 2, 1, 17, 0)
        end = datetime(2024, 2, 1, 8, 0)
        
        with pytest.raises(ValueError) as exc_info:
            service.get_custom_range(start, end)
        
        assert "must be before" in str(exc_info.value)

    def test_get_custom_range_error_returns_empty_df(self):
        """Returns empty DataFrame on error."""
        mock_client = Mock()
        mock_client.get_five_minute_prices_range.side_effect = Exception("API error")
        
        service = PricingService(client=mock_client)
        start = datetime(2024, 2, 1, 8, 0)
        end = datetime(2024, 2, 1, 17, 0)
        df = service.get_custom_range(start, end)

        assert isinstance(df, pd.DataFrame)
        assert df.empty

    def test_get_current_price_success(self):
        """Returns tuple of timestamp and price."""
        mock_client = Mock()
        expected_time = datetime(2024, 2, 1, 12, 0)
        expected_price = 5.3
        mock_client.get_current_hour_average.return_value = PricePoint(
            timestamp=expected_time,
            price=expected_price,
        )
        
        service = PricingService(client=mock_client)
        timestamp, price = service.get_current_price()

        assert timestamp == expected_time
        assert price == expected_price

    def test_get_price_statistics(self):
        """Returns statistics dict."""
        mock_client = Mock()
        mock_client.get_five_minute_prices.return_value = create_sample_response()
        
        service = PricingService(client=mock_client)
        stats = service.get_price_statistics()

        assert stats["min"] == 5.1
        assert stats["max"] == 6.2
        assert stats["count"] == 5
        assert stats["average"] == pytest.approx(5.6, rel=0.01)

    def test_get_hourly_averages(self):
        """Returns hourly aggregated DataFrame."""
        mock_client = Mock()
        mock_client.get_five_minute_prices.return_value = create_sample_response()
        
        service = PricingService(client=mock_client)
        df = service.get_hourly_averages()

        assert isinstance(df, pd.DataFrame)
        assert "hour" in df.columns
        assert "avg_price" in df.columns
        # Should have 2 hours: 12:00 and 13:00
        assert len(df) == 2

    def test_get_hourly_averages_empty(self):
        """Returns empty DataFrame when no data."""
        mock_client = Mock()
        mock_client.get_five_minute_prices.return_value = PriceResponse(prices=[])
        
        service = PricingService(client=mock_client)
        df = service.get_hourly_averages()

        assert isinstance(df, pd.DataFrame)
        assert df.empty

    def test_get_custom_range_analysis(self):
        """Returns canonical custom-range backend result."""
        mock_client = Mock()
        mock_client.get_five_minute_prices_range.return_value = create_sample_response()
        mock_audit_logger = Mock()

        service = PricingService(client=mock_client, audit_logger=mock_audit_logger)
        result = service.get_custom_range_analysis(date(2024, 2, 1), date(2024, 2, 1))

        assert result.requested_start_date == date(2024, 2, 1)
        assert result.requested_end_date == date(2024, 2, 1)
        assert isinstance(result.raw_data, pd.DataFrame)
        assert isinstance(result.hourly_data, pd.DataFrame)
        assert isinstance(result.hourly_with_context, pd.DataFrame)
        assert result.raw_stats.count == 5
        assert result.hourly_stats.count == 2
        assert int(result.hourly_with_context["raw_point_count"].sum()) == 5
        mock_audit_logger.log_custom_range_analysis.assert_called_once()

    def test_get_custom_range_analysis_invalid_dates(self):
        """Raises ValueError when start date is after end date."""
        service = PricingService(client=Mock(), audit_logger=Mock())
        with pytest.raises(ValueError):
            service.get_custom_range_analysis(date(2024, 2, 2), date(2024, 2, 1))

    def test_is_api_available_true(self):
        """Returns True when API is healthy."""
        mock_client = Mock()
        mock_client.health_check.return_value = True
        
        service = PricingService(client=mock_client)
        assert service.is_api_available() is True

    def test_is_api_available_false(self):
        """Returns False when API is unhealthy."""
        mock_client = Mock()
        mock_client.health_check.return_value = False
        
        service = PricingService(client=mock_client)
        assert service.is_api_available() is False
