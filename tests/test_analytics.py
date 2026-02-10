"""
Unit tests for lightweight analytics tracking.
"""
import json

from src.utils.analytics import AnalyticsTracker


class TestAnalyticsTracker:
    """Tests for AnalyticsTracker."""

    def test_track_event_writes_jsonl_line(self, tmp_path):
        """Tracking should append one JSON event line to disk."""
        events_file = tmp_path / "events" / "analytics.jsonl"
        tracker = AnalyticsTracker(events_file=events_file)

        tracker.track_event("share_link_created", {"start": "2024-02-01T08:00"})

        assert events_file.exists()
        lines = events_file.read_text(encoding="utf-8").strip().splitlines()
        assert len(lines) == 1

        payload = json.loads(lines[0])
        assert payload["event_name"] == "share_link_created"
        assert payload["properties"]["start"] == "2024-02-01T08:00"
        assert "timestamp_utc" in payload
