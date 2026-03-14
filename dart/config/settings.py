"""
Configuration settings for the DART pricing system.
"""
import os
from pathlib import Path


class Config:
    """Centralized configuration with environment variable support."""

    # Base directories
    BASE_DIR = Path(__file__).resolve().parents[2]

    # ComEd Hourly Pricing API settings
    # Documentation: https://hourlypricing.comed.com/hp-api/
    COMED_API_BASE_URL = os.getenv(
        "COMED_API_BASE_URL",
        "https://hourlypricing.comed.com/api",
    )

    # Request settings
    REQUEST_TIMEOUT = int(os.getenv("COMED_REQUEST_TIMEOUT", 30))

    # Retry settings for API calls
    RETRY_ATTEMPTS = int(os.getenv("RETRY_ATTEMPTS", 3))
    RETRY_DELAY = int(os.getenv("RETRY_DELAY", 2))

    # Dashboard settings
    DASHBOARD_TITLE = os.getenv("DASHBOARD_TITLE", "ComEd Real-Time Pricing Dashboard")
    AUTO_REFRESH_SECONDS = int(os.getenv("AUTO_REFRESH_SECONDS", 300))  # 5 minutes
    DASHBOARD_SHARE_BASE_URL = os.getenv("DASHBOARD_SHARE_BASE_URL", "http://localhost:8501")

    # Lightweight event logging for dashboard analytics hooks
    ANALYTICS_EVENTS_FILE = Path(
        os.getenv(
            "ANALYTICS_EVENTS_FILE",
            str(BASE_DIR / ".dart" / "analytics_events.jsonl"),
        )
    )

    # Structured pricing audit logs for raw/hourly verification
    PRICING_AUDIT_ENABLED = os.getenv("PRICING_AUDIT_ENABLED", "true").lower() == "true"
    PRICING_AUDIT_FILE = Path(
        os.getenv(
            "PRICING_AUDIT_FILE",
            str(BASE_DIR / ".dart" / "pricing_audit.jsonl"),
        )
    )
    PRICING_AUDIT_SAMPLE_LIMIT = int(os.getenv("PRICING_AUDIT_SAMPLE_LIMIT", 500))

    # Day-ahead pricing CSV used by the DART comparison tab
    DAY_AHEAD_PRICING_FILE = Path(
        os.getenv(
            "DAY_AHEAD_PRICING_FILE",
            str(BASE_DIR / "DAY_AHEAD_PRICING.csv"),
        )
    )

    @classmethod
    def get_all_settings(cls) -> dict:
        """Get all configuration settings as a dictionary."""
        return {
            key: value for key, value in cls.__dict__.items()
            if not key.startswith('_') and not callable(value)
        }
