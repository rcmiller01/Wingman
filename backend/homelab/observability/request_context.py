"""Request-scoped context utilities."""

from __future__ import annotations

from contextvars import ContextVar
from uuid import uuid4

_request_id: ContextVar[str | None] = ContextVar("request_id", default=None)


def get_request_id() -> str | None:
    """Return the current request id if available."""
    return _request_id.get()


def set_request_id(request_id: str | None):
    """Set the request id for the current context and return the token."""
    return _request_id.set(request_id)


def reset_request_id(token) -> None:
    """Reset the request id to a previous context token."""
    _request_id.reset(token)


def ensure_request_id(request_id: str | None = None) -> str:
    """Return a request id, generating a new one if needed."""
    return request_id or uuid4().hex
