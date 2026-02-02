"""FastAPI middleware for request context."""

from __future__ import annotations

import logging
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

import time
import asyncio
from opentelemetry import trace
from homelab.observability.request_context import (
    ensure_request_id,
    reset_request_id,
    set_request_id,
)
from homelab.storage.database import async_session_maker
from homelab.storage.models import AccessLog


class RequestContextMiddleware(BaseHTTPMiddleware):
    """Attach a request_id to each request and response."""

    async def dispatch(self, request: Request, call_next) -> Response:
        header_request_id = request.headers.get("X-Request-ID") or request.headers.get("X-Request-Id")
        request_id = ensure_request_id(header_request_id)
        token = set_request_id(request_id)
        request.state.request_id = request_id
        
        start_time = time.time()
        status_code = 500
        
        try:
            span = trace.get_current_span()
            if span:
                span.set_attribute("request.id", request_id)
            logger.info("[Request] %s %s", request.method, request.url.path)
            
            response = await call_next(request)
            status_code = response.status_code
            return response
        finally:
            duration = (time.time() - start_time) * 1000
            
            # Fire and forget log persistence
            asyncio.create_task(
                self._persist_log(
                    method=request.method,
                    path=request.url.path,
                    status_code=status_code,
                    client_ip=request.client.host if request.client else None,
                    user_agent=request.headers.get("user-agent"),
                    duration_ms=duration
                )
            )
            
            reset_request_id(token)

    async def _persist_log(self, method, path, status_code, client_ip, user_agent, duration_ms):
        """Persist access log to database."""
        try:
            async with async_session_maker() as db:
                log = AccessLog(
                    method=method,
                    path=path,
                    status_code=status_code,
                    client_ip=client_ip,
                    user_agent=user_agent,
                    duration_ms=duration_ms
                )
                db.add(log)
                await db.commit()
        except Exception as e:
            logger.error(f"Failed to persist access log: {e}")


logger = logging.getLogger(__name__)
