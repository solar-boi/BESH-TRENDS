"""
Lightweight analytics event tracking for dashboard interactions.
"""
from __future__ import annotations

import json
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from dart.config.settings import Config

logger = logging.getLogger(__name__)


class AnalyticsTracker:
    """Append analytics events to a local JSONL file."""

    def __init__(self, events_file: Path | None = None) -> None:
        self.events_file = events_file or Config.ANALYTICS_EVENTS_FILE

    def track_event(self, event_name: str, properties: dict[str, Any] | None = None) -> None:
        """Persist one analytics event for simple dashboard measurement."""
        payload = {
            "event_name": event_name,
            "timestamp_utc": datetime.now(timezone.utc).isoformat(),
            "properties": properties or {},
        }

        try:
            self.events_file.parent.mkdir(parents=True, exist_ok=True)
            with self.events_file.open("a", encoding="utf-8") as file:
                file.write(json.dumps(payload, default=str))
                file.write("\n")
        except Exception as exc:
            logger.warning("Failed to write analytics event '%s': %s", event_name, exc)
