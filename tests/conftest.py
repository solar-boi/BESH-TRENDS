"""Shared test fixtures for the DART test suite."""
from __future__ import annotations

from datetime import datetime

import pandas as pd
import pytest

from dart.models.pricing import PricePoint, PriceResponse


@pytest.fixture()
def sample_price_points() -> list[PricePoint]:
    """Five 5-minute price points spanning two clock hours."""
    return [
        PricePoint(timestamp=datetime(2024, 2, 1, 12, 0), price=5.2),
        PricePoint(timestamp=datetime(2024, 2, 1, 12, 5), price=5.5),
        PricePoint(timestamp=datetime(2024, 2, 1, 12, 10), price=5.1),
        PricePoint(timestamp=datetime(2024, 2, 1, 13, 0), price=6.0),
        PricePoint(timestamp=datetime(2024, 2, 1, 13, 5), price=6.2),
    ]


@pytest.fixture()
def sample_price_response(sample_price_points) -> PriceResponse:
    """A PriceResponse wrapping the sample price points."""
    return PriceResponse(prices=sample_price_points)


@pytest.fixture()
def sample_raw_df() -> pd.DataFrame:
    """Raw 5-minute price DataFrame matching the sample price points."""
    return pd.DataFrame(
        {
            "timestamp": [
                datetime(2024, 2, 1, 12, 0),
                datetime(2024, 2, 1, 12, 5),
                datetime(2024, 2, 1, 12, 10),
                datetime(2024, 2, 1, 13, 0),
                datetime(2024, 2, 1, 13, 5),
            ],
            "price": [5.2, 5.5, 5.1, 6.0, 6.2],
        }
    )


@pytest.fixture()
def sample_hourly_two_days() -> pd.DataFrame:
    """Hourly data spanning two days for daily-summary tests."""
    return pd.DataFrame(
        {
            "hour": [
                datetime(2024, 2, 1, 1, 0),
                datetime(2024, 2, 1, 2, 0),
                datetime(2024, 2, 2, 1, 0),
                datetime(2024, 2, 2, 2, 0),
            ],
            "avg_price": [2.0, 6.0, 4.0, 8.0],
        }
    )
