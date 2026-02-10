"""
Pricing service layer.

This module provides a high-level interface for fetching and working with
ComEd pricing data. It wraps the API client and provides convenient methods
for common operations.
"""
from __future__ import annotations

import logging
from datetime import datetime, timedelta
from typing import Tuple

import pandas as pd

from src.api.comed_client import ComEdClient, ComEdAPIError
from src.models.pricing import PricePoint, PriceResponse

logger = logging.getLogger(__name__)


class PricingService:
    """
    High-level service for accessing ComEd pricing data.
    
    This service wraps the ComEdClient and provides:
    - DataFrame-ready outputs for visualization
    - Convenience methods for common time ranges
    - Error handling and logging
    
    Example:
        service = PricingService()
        
        # Get last 24 hours as DataFrame
        df = service.get_last_24_hours()
        
        # Get current price
        timestamp, price = service.get_current_price()
        print(f"Current price: {price}¢/kWh")
    """

    def __init__(self, client: ComEdClient | None = None) -> None:
        """
        Initialize the pricing service.
        
        Args:
            client: Optional ComEdClient instance. If not provided, a new
                   client will be created with default settings.
        """
        self.client = client or ComEdClient()

    def get_last_24_hours(self) -> pd.DataFrame:
        """
        Fetch 5-minute prices for the last 24 hours as a DataFrame.
        
        Returns:
            DataFrame with 'timestamp' and 'price' columns, sorted by timestamp.
            Returns empty DataFrame if fetch fails.
            
        Example:
            service = PricingService()
            df = service.get_last_24_hours()
            
            # Plot with plotly
            fig = px.line(df, x='timestamp', y='price')
        """
        try:
            response = self.client.get_five_minute_prices()
            return response.to_dataframe()
        except Exception as e:
            logger.error("Failed to fetch last 24 hours: %s", e)
            return pd.DataFrame(columns=["timestamp", "price"])

    def get_custom_range(
        self,
        start: datetime,
        end: datetime,
    ) -> pd.DataFrame:
        """
        Fetch 5-minute prices for a custom time range as a DataFrame.
        
        Args:
            start: Start datetime for the range.
            end: End datetime for the range.
            
        Returns:
            DataFrame with 'timestamp' and 'price' columns, sorted by timestamp.
            Returns empty DataFrame if fetch fails.
            
        Raises:
            ValueError: If start is after end.
            
        Example:
            service = PricingService()
            start = datetime(2024, 1, 15, 8, 0)
            end = datetime(2024, 1, 15, 17, 0)
            df = service.get_custom_range(start, end)
        """
        if start > end:
            raise ValueError(f"Start time ({start}) must be before end time ({end})")
        
        try:
            response = self.client.get_five_minute_prices_range(start, end)
            return response.to_dataframe()
        except Exception as e:
            logger.error("Failed to fetch custom range: %s", e)
            return pd.DataFrame(columns=["timestamp", "price"])

    def get_current_price(self) -> Tuple[datetime, float]:
        """
        Get the current hour's average price.
        
        Returns:
            Tuple of (timestamp, price_in_cents).
            
        Raises:
            ComEdAPIError: If the API request fails.
            
        Example:
            service = PricingService()
            timestamp, price = service.get_current_price()
            print(f"Current price at {timestamp}: {price}¢/kWh")
        """
        price_point = self.client.get_current_hour_average()
        return (price_point.timestamp, price_point.price)

    def get_price_statistics(
        self,
        start: datetime | None = None,
        end: datetime | None = None,
    ) -> dict:
        """
        Calculate price statistics for a time range.
        
        Args:
            start: Start datetime (defaults to 24 hours ago).
            end: End datetime (defaults to now).
            
        Returns:
            Dict with statistics: min, max, average, count, range_start, range_end.
            
        Example:
            service = PricingService()
            stats = service.get_price_statistics()
            print(f"Average price: {stats['average']:.2f}¢/kWh")
        """
        if start is None or end is None:
            response = self.client.get_five_minute_prices()
        else:
            response = self.client.get_five_minute_prices_range(start, end)
        
        return {
            "min": response.min_price,
            "max": response.max_price,
            "average": response.average_price,
            "count": len(response),
            "range_start": response.earliest.timestamp if response.earliest else None,
            "range_end": response.latest.timestamp if response.latest else None,
        }

    def get_hourly_averages(self) -> pd.DataFrame:
        """
        Get hourly average prices for the last 24 hours.
        
        Aggregates 5-minute data into hourly averages.
        
        Returns:
            DataFrame with 'hour' and 'avg_price' columns.
        """
        df = self.get_last_24_hours()
        
        if df.empty:
            return pd.DataFrame(columns=["hour", "avg_price"])
        
        df["hour"] = df["timestamp"].dt.floor("h")
        hourly = df.groupby("hour")["price"].mean().reset_index()
        hourly.columns = ["hour", "avg_price"]
        
        return hourly

    def is_api_available(self) -> bool:
        """
        Check if the ComEd API is available.
        
        Returns:
            True if the API is responding, False otherwise.
        """
        return self.client.health_check()
