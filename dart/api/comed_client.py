"""
ComEd Hourly Pricing API client.

This module provides a clean interface to the ComEd Hourly Pricing API.
Documentation: https://hourlypricing.comed.com/hp-api/
"""
from __future__ import annotations

import logging
from datetime import datetime
from typing import Any

import requests

from dart.config.settings import Config
from dart.models.pricing import PricePoint, PriceResponse
from dart.utils.helpers import retry_operation

logger = logging.getLogger(__name__)


class ComEdAPIError(Exception):
    """Exception raised for ComEd API errors."""
    pass


class ComEdClient:
    """
    Client for the ComEd Hourly Pricing API.

    Provides methods for fetching:
    - 5-minute prices for the last 24 hours
    - 5-minute prices for a custom time range
    - Current hour average price

    Example:
        client = ComEdClient()

        # Get last 24 hours of 5-minute prices
        response = client.get_five_minute_prices()
        df = response.to_dataframe()

        # Get current hour average
        current = client.get_current_hour_average()
        print(f"Current price: {current.price}¢/kWh")
    """

    DATE_FORMAT = "%Y%m%d%H%M"

    def __init__(
        self,
        base_url: str | None = None,
        timeout: int | None = None,
    ) -> None:
        """Initialize the ComEd API client.

        Args:
            base_url: Override the default API base URL.
            timeout: Request timeout in seconds.
        """
        self.base_url = base_url or Config.COMED_API_BASE_URL
        self.timeout = timeout or Config.REQUEST_TIMEOUT

    @retry_operation(
        max_attempts=Config.RETRY_ATTEMPTS,
        delay=Config.RETRY_DELAY,
        exceptions=(requests.RequestException, ComEdAPIError),
    )
    def _fetch(self, params: dict[str, Any]) -> list[dict[str, Any]]:
        """
        Make a request to the ComEd API.

        Args:
            params: Query parameters for the request.

        Returns:
            List of response dictionaries.

        Raises:
            ComEdAPIError: If the API returns an error or unexpected response.
            requests.RequestException: If the HTTP request fails.
        """
        logger.debug("Fetching from ComEd API with params: %s", params)

        response = requests.get(
            self.base_url,
            params=params,
            timeout=self.timeout,
        )
        response.raise_for_status()

        data = response.json()

        if not isinstance(data, list):
            raise ComEdAPIError(
                f"Unexpected API response format. Expected list, got: {type(data).__name__}"
            )

        logger.debug("Received %d records from ComEd API", len(data))
        return data

    def get_five_minute_prices(self) -> PriceResponse:
        """
        Fetch 5-minute prices for the last 24 hours.

        Returns:
            PriceResponse containing all price points from the last 24 hours.

        Raises:
            ComEdAPIError: If the API returns an error.
            requests.RequestException: If the HTTP request fails.

        Example:
            client = ComEdClient()
            response = client.get_five_minute_prices()
            print(f"Got {len(response)} price points")
            print(f"Average price: {response.average_price:.2f}¢/kWh")
        """
        logger.info("Fetching 5-minute prices for last 24 hours")

        data = self._fetch({"type": "5minutefeed"})
        response = PriceResponse.from_api_response(data)

        logger.info(
            "Fetched %d price points, range: %s to %s",
            len(response),
            response.earliest.timestamp if response.earliest else "N/A",
            response.latest.timestamp if response.latest else "N/A",
        )

        return response

    def get_five_minute_prices_range(
        self,
        start: datetime,
        end: datetime,
    ) -> PriceResponse:
        """
        Fetch 5-minute prices for a custom time range.

        Args:
            start: Start datetime for the range (inclusive).
            end: End datetime for the range (inclusive).

        Returns:
            PriceResponse containing price points within the specified range.

        Raises:
            ValueError: If start is after end.
            ComEdAPIError: If the API returns an error.
            requests.RequestException: If the HTTP request fails.

        Example:
            client = ComEdClient()
            start = datetime(2024, 1, 15, 8, 0)
            end = datetime(2024, 1, 15, 17, 0)
            response = client.get_five_minute_prices_range(start, end)
        """
        if start > end:
            raise ValueError(f"Start time ({start}) must be before end time ({end})")

        logger.info("Fetching 5-minute prices from %s to %s", start, end)

        params = {
            "type": "5minutefeed",
            "datestart": start.strftime(self.DATE_FORMAT),
            "dateend": end.strftime(self.DATE_FORMAT),
        }

        data = self._fetch(params)
        response = PriceResponse.from_api_response(data)

        logger.info("Fetched %d price points for custom range", len(response))

        return response

    def get_current_hour_average(self) -> PricePoint:
        """
        Fetch the current hour's average price.

        This returns the average of all 5-minute prices within the current hour.

        Returns:
            PricePoint with the current hour's average price.

        Raises:
            ComEdAPIError: If the API returns an error or no data.
            requests.RequestException: If the HTTP request fails.

        Example:
            client = ComEdClient()
            current = client.get_current_hour_average()
            print(f"Current price: {current.price:.2f}¢/kWh at {current.timestamp}")
        """
        logger.info("Fetching current hour average price")

        data = self._fetch({"type": "currenthouraverage"})

        if not data:
            raise ComEdAPIError("No data returned for current hour average")

        # API returns a list with a single item
        price_point = PricePoint.from_api_response(data[0])

        logger.info(
            "Current hour average: %.2f¢/kWh at %s",
            price_point.price,
            price_point.timestamp,
        )

        return price_point

    def health_check(self) -> bool:
        """
        Verify the API is reachable and responding.

        Returns:
            True if the API is healthy, False otherwise.
        """
        try:
            self.get_current_hour_average()
            return True
        except Exception as e:
            logger.warning("Health check failed: %s", e)
            return False
