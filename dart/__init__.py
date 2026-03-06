"""
DART - Data Acquisition and Real-time Tracking

A real-time ComEd electricity pricing dashboard using the ComEd Hourly Pricing API.
"""

__version__ = "2.0.0"
__author__ = "DART Team"

from dart.api.comed_client import ComEdClient
from dart.models.pricing import PricePoint, PriceResponse
from dart.services.pricing_service import PricingService

__all__ = [
    "ComEdClient",
    "PricePoint",
    "PriceResponse",
    "PricingService",
]
