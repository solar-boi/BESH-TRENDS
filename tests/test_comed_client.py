"""
Unit tests for the ComEd API client.
"""
import pytest
import requests
from datetime import datetime
from unittest.mock import patch, Mock

from src.api.comed_client import ComEdClient, ComEdAPIError
from src.models.pricing import PricePoint, PriceResponse


# Sample API response data
SAMPLE_FIVE_MINUTE_RESPONSE = [
    {"millisUTC": "1706817600000", "price": "5.2"},  # 2024-02-01 12:00:00
    {"millisUTC": "1706817900000", "price": "5.5"},  # 2024-02-01 12:05:00
    {"millisUTC": "1706818200000", "price": "5.1"},  # 2024-02-01 12:10:00
]

SAMPLE_CURRENT_HOUR_RESPONSE = [
    {"millisUTC": "1706817600000", "price": "5.3"},
]


class TestComEdClient:
    """Tests for ComEdClient."""

    def test_init_default_settings(self):
        """Client initializes with default settings."""
        client = ComEdClient()
        assert client.base_url == "https://hourlypricing.comed.com/api"
        assert client.timeout == 30

    def test_init_custom_settings(self):
        """Client accepts custom settings."""
        client = ComEdClient(base_url="https://custom.url/api", timeout=60)
        assert client.base_url == "https://custom.url/api"
        assert client.timeout == 60

    @patch("src.api.comed_client.requests.get")
    def test_get_five_minute_prices_success(self, mock_get):
        """Fetching 5-minute prices returns PriceResponse."""
        mock_response = Mock()
        mock_response.json.return_value = SAMPLE_FIVE_MINUTE_RESPONSE
        mock_response.raise_for_status = Mock()
        mock_get.return_value = mock_response

        client = ComEdClient()
        response = client.get_five_minute_prices()

        assert isinstance(response, PriceResponse)
        assert len(response) == 3
        assert response.prices[0].price == 5.2
        
        mock_get.assert_called_once()
        call_args = mock_get.call_args
        assert call_args[1]["params"]["type"] == "5minutefeed"

    @patch("src.api.comed_client.requests.get")
    def test_get_five_minute_prices_range_success(self, mock_get):
        """Fetching 5-minute prices for range returns PriceResponse."""
        mock_response = Mock()
        mock_response.json.return_value = SAMPLE_FIVE_MINUTE_RESPONSE
        mock_response.raise_for_status = Mock()
        mock_get.return_value = mock_response

        client = ComEdClient()
        start = datetime(2024, 2, 1, 8, 0)
        end = datetime(2024, 2, 1, 17, 0)
        response = client.get_five_minute_prices_range(start, end)

        assert isinstance(response, PriceResponse)
        assert len(response) == 3
        
        call_args = mock_get.call_args
        assert call_args[1]["params"]["type"] == "5minutefeed"
        assert call_args[1]["params"]["datestart"] == "202402010800"
        assert call_args[1]["params"]["dateend"] == "202402011700"

    def test_get_five_minute_prices_range_invalid_dates(self):
        """Raises ValueError when start is after end."""
        client = ComEdClient()
        start = datetime(2024, 2, 1, 17, 0)
        end = datetime(2024, 2, 1, 8, 0)
        
        with pytest.raises(ValueError) as exc_info:
            client.get_five_minute_prices_range(start, end)
        
        assert "must be before" in str(exc_info.value)

    @patch("src.api.comed_client.requests.get")
    def test_get_current_hour_average_success(self, mock_get):
        """Fetching current hour average returns PricePoint."""
        mock_response = Mock()
        mock_response.json.return_value = SAMPLE_CURRENT_HOUR_RESPONSE
        mock_response.raise_for_status = Mock()
        mock_get.return_value = mock_response

        client = ComEdClient()
        price_point = client.get_current_hour_average()

        assert isinstance(price_point, PricePoint)
        assert price_point.price == 5.3
        
        call_args = mock_get.call_args
        assert call_args[1]["params"]["type"] == "currenthouraverage"

    @patch("src.api.comed_client.requests.get")
    def test_get_current_hour_average_empty_response(self, mock_get):
        """Raises ComEdAPIError when response is empty."""
        mock_response = Mock()
        mock_response.json.return_value = []
        mock_response.raise_for_status = Mock()
        mock_get.return_value = mock_response

        client = ComEdClient()
        
        with pytest.raises(ComEdAPIError) as exc_info:
            client.get_current_hour_average()
        
        assert "No data returned" in str(exc_info.value)

    @patch("src.api.comed_client.requests.get")
    def test_fetch_invalid_response_format(self, mock_get):
        """Raises ComEdAPIError when response is not a list."""
        mock_response = Mock()
        mock_response.json.return_value = {"error": "something went wrong"}
        mock_response.raise_for_status = Mock()
        mock_get.return_value = mock_response

        client = ComEdClient()
        
        with pytest.raises(ComEdAPIError) as exc_info:
            client.get_five_minute_prices()
        
        assert "Unexpected API response format" in str(exc_info.value)

    @patch("src.api.comed_client.requests.get")
    def test_health_check_success(self, mock_get):
        """Health check returns True when API is available."""
        mock_response = Mock()
        mock_response.json.return_value = SAMPLE_CURRENT_HOUR_RESPONSE
        mock_response.raise_for_status = Mock()
        mock_get.return_value = mock_response

        client = ComEdClient()
        assert client.health_check() is True

    @patch("src.api.comed_client.requests.get")
    def test_health_check_failure(self, mock_get):
        """Health check returns False when API is unavailable."""
        mock_get.side_effect = Exception("Connection failed")

        client = ComEdClient()
        assert client.health_check() is False


class TestRetryBehavior:
    """Tests for retry behavior."""

    @patch("src.utils.helpers.time.sleep")
    @patch("src.api.comed_client.requests.get")
    def test_retries_on_failure(self, mock_get, mock_sleep):
        """Client retries on transient failures."""
        # First two calls fail, third succeeds
        mock_response_success = Mock()
        mock_response_success.json.return_value = SAMPLE_CURRENT_HOUR_RESPONSE
        mock_response_success.raise_for_status = Mock()
        
        mock_get.side_effect = [
            requests.RequestException("Timeout"),
            requests.RequestException("Connection reset"),
            mock_response_success,
        ]

        client = ComEdClient()
        price_point = client.get_current_hour_average()

        assert price_point.price == 5.3
        assert mock_get.call_count == 3
        assert mock_sleep.call_count == 2
