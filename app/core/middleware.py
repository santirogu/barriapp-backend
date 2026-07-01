"""Request-context middleware.

Assigns/propagates a request id and binds request-scoped fields to the structlog
contextvars so all logs within a request are correlated. The request id is
echoed back in the ``X-Request-ID`` response header and will later feed the audit
trail (see docs/AUDIT_LOG.md).
"""

import uuid

import structlog
from starlette.requests import Request
from starlette.types import ASGIApp

from app.core.config import get_settings

REQUEST_ID_HEADER = "X-Request-ID"


class RequestContextMiddleware:
    """Pure-ASGI middleware for request id + log context binding."""

    def __init__(self, app: ASGIApp) -> None:
        self.app = app

    async def __call__(self, scope, receive, send):  # type: ignore[no-untyped-def]
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        request = Request(scope)
        request_id = request.headers.get(REQUEST_ID_HEADER) or uuid.uuid4().hex

        structlog.contextvars.clear_contextvars()
        structlog.contextvars.bind_contextvars(
            request_id=request_id,
            method=request.method,
            path=request.url.path,
            client_ip=request.client.host if request.client else None,
            user_agent=request.headers.get("user-agent"),
        )

        async def send_with_header(message):  # type: ignore[no-untyped-def]
            if message["type"] == "http.response.start":
                headers = message.setdefault("headers", [])
                headers.append((REQUEST_ID_HEADER.lower().encode(), request_id.encode()))
            await send(message)

        try:
            await self.app(scope, receive, send_with_header)
        finally:
            structlog.contextvars.clear_contextvars()


def build_security_headers(*, enable_hsts: bool, hsts_max_age: int) -> list[tuple[bytes, bytes]]:
    """Baseline security headers; HSTS is added only when enabled (HTTPS/prod)."""
    headers: list[tuple[bytes, bytes]] = [
        (b"x-content-type-options", b"nosniff"),
        (b"x-frame-options", b"DENY"),
        (b"referrer-policy", b"no-referrer"),
        (b"x-xss-protection", b"0"),
    ]
    if enable_hsts:
        value = f"max-age={hsts_max_age}; includeSubDomains".encode()
        headers.append((b"strict-transport-security", value))
    return headers


class SecurityHeadersMiddleware:
    """Adds baseline security headers to every HTTP response."""

    def __init__(self, app: ASGIApp) -> None:
        self.app = app
        settings = get_settings()
        self._headers = build_security_headers(
            enable_hsts=settings.enable_hsts, hsts_max_age=settings.hsts_max_age
        )

    async def __call__(self, scope, receive, send):  # type: ignore[no-untyped-def]
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        async def send_with_headers(message):  # type: ignore[no-untyped-def]
            if message["type"] == "http.response.start":
                headers = message.setdefault("headers", [])
                headers.extend(self._headers)
            await send(message)

        await self.app(scope, receive, send_with_headers)
