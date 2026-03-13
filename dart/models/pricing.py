"""
Pricing data models for ComEd API responses.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, datetime

import pandas as pd


@dataclass(frozen=True)
class PricePoint:
    """
    Represents a single price point from the ComEd API.

    Attributes:
        timestamp: The datetime of the price reading (UTC converted to local).
        price: The price in cents per kWh. Can be negative during periods of
               electricity oversupply (negative pricing is a real market phenomenon).
    """
    timestamp: datetime
    price: float  # cents per kWh (can be negative during oversupply)

    @classmethod
    def from_api_response(cls, data: dict) -> "PricePoint":
        """
        Create a PricePoint from a ComEd API response dict.

        Args:
            data: Dict with 'millisUTC' and 'price' keys.

        Returns:
            PricePoint instance.

        Raises:
            KeyError: If required keys are missing.
            ValueError: If data cannot be parsed.
        """
        millis = int(data["millisUTC"])
        timestamp = datetime.fromtimestamp(millis / 1000)
        price = float(data["price"])
        return cls(timestamp=timestamp, price=price)


@dataclass
class PriceResponse:
    """
    Container for a collection of price points with metadata.

    Attributes:
        prices: List of PricePoint objects.
        fetched_at: When the data was fetched from the API.
    """
    prices: list[PricePoint] = field(default_factory=list)
    fetched_at: datetime = field(default_factory=datetime.now)

    def __len__(self) -> int:
        return len(self.prices)

    def __bool__(self) -> bool:
        return len(self.prices) > 0

    @property
    def latest(self) -> PricePoint | None:
        """Get the most recent price point."""
        if not self.prices:
            return None
        return max(self.prices, key=lambda p: p.timestamp)

    @property
    def earliest(self) -> PricePoint | None:
        """Get the earliest price point."""
        if not self.prices:
            return None
        return min(self.prices, key=lambda p: p.timestamp)

    @property
    def average_price(self) -> float | None:
        """Calculate the average price across all points."""
        if not self.prices:
            return None
        return sum(p.price for p in self.prices) / len(self.prices)

    @property
    def min_price(self) -> float | None:
        """Get the minimum price."""
        if not self.prices:
            return None
        return min(p.price for p in self.prices)

    @property
    def max_price(self) -> float | None:
        """Get the maximum price."""
        if not self.prices:
            return None
        return max(p.price for p in self.prices)

    def to_dataframe(self) -> pd.DataFrame:
        """
        Convert price points to a pandas DataFrame.

        Returns:
            DataFrame with 'timestamp' and 'price' columns, sorted by timestamp.
        """
        if not self.prices:
            return pd.DataFrame(columns=["timestamp", "price"])

        data = [
            {"timestamp": p.timestamp, "price": p.price}
            for p in self.prices
        ]
        df = pd.DataFrame(data)
        df = df.sort_values("timestamp").reset_index(drop=True)
        return df

    @classmethod
    def from_api_response(cls, data: list[dict]) -> "PriceResponse":
        """
        Create a PriceResponse from a list of API response dicts.

        Args:
            data: List of dicts with 'millisUTC' and 'price' keys.

        Returns:
            PriceResponse instance.
        """
        prices = [PricePoint.from_api_response(item) for item in data]
        return cls(prices=prices, fetched_at=datetime.now())


@dataclass(frozen=True)
class PriceStats:
    """Typed statistics container for a price series."""

    min_price: float | None
    max_price: float | None
    average_price: float | None
    count: int


@dataclass
class CustomRangeResult:
    """
    Canonical backend result for custom-range analysis.

    Includes raw points, hourly averages, stats for both levels, and metadata
    about requested/expanded ranges.
    """

    requested_start_date: date
    requested_end_date: date
    expanded_start: datetime
    expanded_end: datetime
    raw_data: pd.DataFrame
    hourly_data: pd.DataFrame
    raw_stats: PriceStats
    hourly_stats: PriceStats
    hourly_with_context: pd.DataFrame = field(default_factory=pd.DataFrame)
