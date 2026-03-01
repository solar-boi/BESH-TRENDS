"""
Structured audit logging for pricing calculations.
"""
from __future__ import annotations

import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Any

import pandas as pd

from src.models.pricing import CustomRangeResult

logger = logging.getLogger(__name__)


class PricingAuditLogger:
    """Write raw/hourly reconciliation records to JSONL."""

    def __init__(self, enabled: bool, file_path: Path, sample_limit: int = 500) -> None:
        self.enabled = enabled
        self.file_path = file_path
        self.sample_limit = sample_limit

    @staticmethod
    def _serialize_datetime(value: Any) -> Any:
        if isinstance(value, datetime):
            return value.isoformat()
        return value

    def _frame_to_records(self, df: pd.DataFrame, limit: int) -> list[dict[str, Any]]:
        if df.empty:
            return []

        limited = df.head(limit).copy()
        for col in limited.columns:
            if pd.api.types.is_datetime64_any_dtype(limited[col]):
                limited[col] = limited[col].dt.strftime("%Y-%m-%dT%H:%M:%S")

        records: list[dict[str, Any]] = limited.to_dict(orient="records")
        return records

    def log_custom_range_analysis(self, result: CustomRangeResult) -> None:
        """Persist a custom-range audit event."""
        if not self.enabled:
            return

        self.file_path.parent.mkdir(parents=True, exist_ok=True)
        raw_records = self._frame_to_records(result.raw_data, self.sample_limit)
        hourly_records = self._frame_to_records(result.hourly_data, self.sample_limit)
        context_records = self._frame_to_records(result.hourly_with_context, self.sample_limit)

        payload = {
            "event": "custom_range_analysis",
            "logged_at": datetime.now().isoformat(),
            "range": {
                "requested_start_date": str(result.requested_start_date),
                "requested_end_date": str(result.requested_end_date),
                "expanded_start": result.expanded_start.isoformat(),
                "expanded_end": result.expanded_end.isoformat(),
            },
            "stats": {
                "raw": {
                    "min": result.raw_stats.min_price,
                    "max": result.raw_stats.max_price,
                    "average": result.raw_stats.average_price,
                    "count": result.raw_stats.count,
                },
                "hourly": {
                    "min": result.hourly_stats.min_price,
                    "max": result.hourly_stats.max_price,
                    "average": result.hourly_stats.average_price,
                    "count": result.hourly_stats.count,
                },
            },
            "raw_values": {
                "total_count": len(result.raw_data),
                "sample_count": len(raw_records),
                "truncated": len(result.raw_data) > self.sample_limit,
                "records": raw_records,
            },
            "hourly_averages": {
                "total_count": len(result.hourly_data),
                "sample_count": len(hourly_records),
                "truncated": len(result.hourly_data) > self.sample_limit,
                "records": hourly_records,
            },
            "hourly_reconciliation": {
                "total_count": len(result.hourly_with_context),
                "sample_count": len(context_records),
                "truncated": len(result.hourly_with_context) > self.sample_limit,
                "records": context_records,
            },
        }

        with self.file_path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(payload, default=self._serialize_datetime) + "\n")

        logger.info(
            "Wrote pricing audit record for %s -> %s",
            result.requested_start_date,
            result.requested_end_date,
        )
