"""FastAPI middleware for request context."""

from __future__ import annotations

import logging
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

from opentelemetry import trace
from homelab.observability.request_context import (
    ensure_request_id,
    reset_request_id,
    set_request_id,
)


class RequestContextMiddleware(BaseHTTPMiddleware):
    """Attach a request_id to each request and response."""

    async def dispatch(self, request: Request, call_next) -> Response:
        header_request_id = request.headers.get("X-Request-ID") or request.headers.get("X-Request-Id")
        request_id = ensure_request_id(header_request_id)
        token = set_request_id(request_id)
        request.state.request_id = request_id
        try:
            span = trace.get_current_span()
            if span:
                span.set_attribute("request.id", request_id)
            logger.info("[Request] %s %s", request.method, request.url.path)
            response = await call_next(request)
        finally:
            reset_request_id(token)
        response.headers["X-Request-ID"] = request_id
        return response


logger = logging.getLogger(__name__)
