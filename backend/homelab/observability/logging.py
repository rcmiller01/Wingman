"""Logging configuration with request context."""

from __future__ import annotations

import logging
from logging.handlers import SysLogHandler

import httpx

from opentelemetry import trace

from homelab.config import get_settings
from homelab.observability.request_context import get_request_id


class RequestIdFilter(logging.Filter):
    """Attach request_id to log records."""

    def filter(self, record: logging.LogRecord) -> bool:
        span = trace.get_current_span()
        span_context = span.get_span_context()
        if span_context and span_context.is_valid:
            record.trace_id = format(span_context.trace_id, "032x")
            record.span_id = format(span_context.span_id, "016x")
        else:
            record.trace_id = "-"
            record.span_id = "-"
        record.request_id = get_request_id() or "-"
        return True


class NtfyHandler(logging.Handler):
    """Send log notifications to ntfy."""

    def __init__(self, url: str, topic: str):
        super().__init__(level=logging.ERROR)
        self.url = url.rstrip("/")
        self.topic = topic
        self.client = httpx.Client(timeout=5.0)

    def emit(self, record: logging.LogRecord) -> None:
        message = self.format(record)
        try:
            self.client.post(
                f"{self.url}/{self.topic}",
                content=message,
                headers={"Title": "Wingman alert"},
            )
        except Exception:
            pass


class GotifyHandler(logging.Handler):
    """Send log notifications to Gotify."""

    def __init__(self, url: str, token: str):
        super().__init__(level=logging.ERROR)
        self.url = url.rstrip("/")
        self.token = token
        self.client = httpx.Client(timeout=5.0)

    def emit(self, record: logging.LogRecord) -> None:
        message = self.format(record)
        try:
            self.client.post(
                f"{self.url}/message",
                params={"token": self.token},
                json={
                    "title": "Wingman alert",
                    "message": message,
                    "priority": 7,
                },
            )
        except Exception:
            pass


def configure_logging() -> None:
    """Configure base logging to include request context."""
    settings = get_settings()
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s request_id=%(request_id)s trace_id=%(trace_id)s span_id=%(span_id)s %(message)s",
    )
    root_logger = logging.getLogger()
    root_logger.addFilter(RequestIdFilter())

    if settings.syslog_host:
        syslog_handler = SysLogHandler(address=(settings.syslog_host, settings.syslog_port))
        syslog_handler.setLevel(logging.INFO)
        syslog_handler.setFormatter(logging.Formatter("%(name)s %(levelname)s %(message)s"))
        root_logger.addHandler(syslog_handler)

    if settings.ntfy_url and settings.ntfy_topic:
        ntfy_handler = NtfyHandler(settings.ntfy_url, settings.ntfy_topic)
        ntfy_handler.setFormatter(logging.Formatter("%(levelname)s %(name)s %(message)s"))
        root_logger.addHandler(ntfy_handler)

    if settings.gotify_url and settings.gotify_token:
        gotify_handler = GotifyHandler(settings.gotify_url, settings.gotify_token)
        gotify_handler.setFormatter(logging.Formatter("%(levelname)s %(name)s %(message)s"))
        root_logger.addHandler(gotify_handler)
