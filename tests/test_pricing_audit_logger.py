"""Unit tests for structured pricing audit logging."""
import json
from datetime import date, datetime
from pathlib import Path

import pandas as pd

from dart.models.pricing import CustomRangeResult, PriceStats
from dart.utils.pricing_audit_logger import PricingAuditLogger


def _sample_result() -> CustomRangeResult:
    raw_df = pd.DataFrame(
        {
            "timestamp": [datetime(2024, 2, 1, 12, 0), datetime(2024, 2, 1, 12, 5)],
            "price": [5.2, 5.4],
        }
    )
    hourly_df = pd.DataFrame({"hour": [datetime(2024, 2, 1, 13, 0)], "avg_price": [5.3]})
    context_df = pd.DataFrame(
        {
            "hour": [datetime(2024, 2, 1, 13, 0)],
            "avg_price": [5.3],
            "raw_point_count": [2],
            "raw_bucket_start": [datetime(2024, 2, 1, 12, 0)],
            "raw_bucket_end": [datetime(2024, 2, 1, 12, 5)],
        }
    )
    return CustomRangeResult(
        requested_start_date=date(2024, 2, 1),
        requested_end_date=date(2024, 2, 1),
        expanded_start=datetime(2024, 2, 1, 0, 0),
        expanded_end=datetime(2024, 2, 1, 23, 59),
        raw_data=raw_df,
        hourly_data=hourly_df,
        raw_stats=PriceStats(min_price=5.2, max_price=5.4, average_price=5.3, count=2),
        hourly_stats=PriceStats(min_price=5.3, max_price=5.3, average_price=5.3, count=1),
        hourly_with_context=context_df,
    )


def test_audit_logger_writes_jsonl(tmp_path: Path):
    audit_file = tmp_path / "pricing_audit.jsonl"
    logger = PricingAuditLogger(enabled=True, file_path=audit_file, sample_limit=50)
    logger.log_custom_range_analysis(_sample_result())

    assert audit_file.exists()
    lines = audit_file.read_text(encoding="utf-8").strip().splitlines()
    assert len(lines) == 1
    payload = json.loads(lines[0])
    assert payload["event"] == "custom_range_analysis"
    assert payload["raw_values"]["total_count"] == 2
    assert payload["hourly_averages"]["total_count"] == 1


def test_audit_logger_noop_when_disabled(tmp_path: Path):
    audit_file = tmp_path / "pricing_audit.jsonl"
    logger = PricingAuditLogger(enabled=False, file_path=audit_file, sample_limit=50)
    logger.log_custom_range_analysis(_sample_result())
    assert not audit_file.exists()
