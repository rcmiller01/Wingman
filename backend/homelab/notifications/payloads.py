"""Notification payload helpers."""

from __future__ import annotations

from datetime import datetime
from typing import Any


def build_webhook_payload(event_type: str, data: dict[str, Any]) -> dict[str, Any]:
    """Build a normalized webhook payload envelope."""
    return {
        "version": "1.0",
        "event_type": event_type,
        "timestamp": datetime.utcnow().isoformat(),
        "data": data,
    }
