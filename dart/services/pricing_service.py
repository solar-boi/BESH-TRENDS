"""
Pricing service layer.

This module provides a high-level interface for fetching and working with
ComEd pricing data. It wraps the API client and provides convenient methods
for common operations.
"""
from __future__ import annotations

import logging
from datetime import date, datetime
from typing import Tuple

import pandas as pd

from dart.api.comed_client import ComEdClient
from dart.config.settings import Config
from dart.models.pricing import CustomRangeResult, PriceStats
from dart.services.pricing_calculations import (
    build_hourly_with_raw_context,
    compute_hourly_hour_ending,
    compute_stats,
    expand_date_range_to_bounds,
)
from dart.utils.pricing_audit_logger import PricingAuditLogger

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

    def __init__(
        self,
        client: ComEdClient | None = None,
        audit_logger: PricingAuditLogger | None = None,
    ) -> None:
        """
        Initialize the pricing service.

        Args:
            client: Optional ComEdClient instance. If not provided, a new
                   client will be created with default settings.
        """
        self.client = client or ComEdClient()
        self.audit_logger = audit_logger or PricingAuditLogger(
            enabled=Config.PRICING_AUDIT_ENABLED,
            file_path=Config.PRICING_AUDIT_FILE,
            sample_limit=Config.PRICING_AUDIT_SAMPLE_LIMIT,
        )

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
            df = self.get_last_24_hours()
        else:
            df = self.get_custom_range(start, end)

        stats = compute_stats(df, "price")
        return {
            "min": stats["min"],
            "max": stats["max"],
            "average": stats["average"],
            "count": stats["count"],
            "range_start": df["timestamp"].min() if not df.empty else None,
            "range_end": df["timestamp"].max() if not df.empty else None,
        }

    @staticmethod
    def _build_price_stats(df: pd.DataFrame, price_column: str) -> PriceStats:
        """Convert dict stats output into a typed PriceStats object."""
        stats = compute_stats(df, price_column)
        return PriceStats(
            min_price=stats["min"],
            max_price=stats["max"],
            average_price=stats["average"],
            count=stats["count"],
        )

    def get_custom_range_analysis(
        self,
        start_date: date,
        end_date: date,
    ) -> CustomRangeResult:
        """
        Return canonical raw+hourly outputs for a date range.

        This is the backend source of truth used by the UI.
        """
        start_dt, end_dt = expand_date_range_to_bounds(start_date, end_date)
        raw_df = self.get_custom_range(start_dt, end_dt)
        hourly_df = compute_hourly_hour_ending(raw_df)
        hourly_context_df = build_hourly_with_raw_context(raw_df, hourly_df)

        result = CustomRangeResult(
            requested_start_date=start_date,
            requested_end_date=end_date,
            expanded_start=start_dt,
            expanded_end=end_dt,
            raw_data=raw_df,
            hourly_data=hourly_df,
            raw_stats=self._build_price_stats(raw_df, "price"),
            hourly_stats=self._build_price_stats(hourly_df, "avg_price"),
            hourly_with_context=hourly_context_df,
        )
        self.audit_logger.log_custom_range_analysis(result)
        return result

    def get_hourly_custom_range(
        self,
        start_date: date,
        end_date: date,
    ) -> pd.DataFrame:
        """
        Fetch and aggregate prices to hourly averages for a date range.

        Uses "hour-ending" logic: 12:00-12:55 average is labeled as 1:00 PM.
        Ensures full day coverage for the selected dates.

        Args:
            start_date: Starting date.
            end_date: Ending date.

        Returns:
            DataFrame with 'hour' and 'avg_price' columns.
        """
        return self.get_custom_range_analysis(start_date, end_date).hourly_data

    def get_hourly_averages(self) -> pd.DataFrame:
        """
        Get hourly average prices for the last 24 hours.

        Aggregates 5-minute data into hourly averages using hour-ending logic.

        Returns:
            DataFrame with 'hour' and 'avg_price' columns.
        """
        df = self.get_last_24_hours()
        return compute_hourly_hour_ending(df)

    def is_api_available(self) -> bool:
        """
        Check if the ComEd API is available.

        Returns:
            True if the API is responding, False otherwise.
        """
        return self.client.health_check()
