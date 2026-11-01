"""ASGI middleware: request id, access log line, security headers."""

from __future__ import annotations

import json
import re
import time
import uuid

import structlog
from starlette.types import ASGIApp, Message, Receive, Scope, Send

log = structlog.get_logger("chitbook.http")

_SAFE_REQUEST_ID = re.compile(r"^[A-Za-z0-9._-]{8,64}$")

SECURITY_HEADERS = [
    (b"x-content-type-options", b"nosniff"),
    (b"x-frame-options", b"DENY"),
    (b"referrer-policy", b"no-referrer"),
    (b"permissions-policy", b"camera=(), microphone=(), geolocation=()"),
    (b"cache-control", b"no-store"),
]


class RequestContextMiddleware:
    """Gives every HTTP request a request id, logs one access line, adds security headers."""

    def __init__(self, app: ASGIApp) -> None:
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        incoming = dict(scope["headers"]).get(b"x-request-id", b"").decode("latin-1")
        request_id = incoming if _SAFE_REQUEST_ID.match(incoming) else uuid.uuid4().hex
        scope.setdefault("state", {})["request_id"] = request_id

        structlog.contextvars.clear_contextvars()
        structlog.contextvars.bind_contextvars(request_id=request_id)

        start = time.perf_counter()
        status_code = 500
        response_started = False

        async def send_wrapper(message: Message) -> None:
            nonlocal status_code, response_started
            if message["type"] == "http.response.start":
                response_started = True
                status_code = message["status"]
                headers = list(message.get("headers", []))
                headers.append((b"x-request-id", request_id.encode()))
                headers.extend(SECURITY_HEADERS)
                message["headers"] = headers
            await send(message)

        try:
            await self.app(scope, receive, send_wrapper)
        except Exception as exc:
            log.error("request.unhandled_exception", code="INTERNAL_ERROR", error=repr(exc), exc_info=exc)
            if not response_started:
                await _send_internal_error(send_wrapper, request_id)
        finally:
            duration_ms = round((time.perf_counter() - start) * 1000, 1)
            client = scope.get("client")
            line = log.info if status_code < 500 else log.error
            line(
                "http.request",
                method=scope["method"],
                path=scope["path"],
                status=status_code,
                duration_ms=duration_ms,
                client_ip=client[0] if client else None,
            )
            structlog.contextvars.clear_contextvars()


async def _send_internal_error(send: Send, request_id: str) -> None:
    body = json.dumps(
        {
            "error": {
                "code": "INTERNAL_ERROR",
                "message": "An unexpected internal error occurred",
                "details": None,
                "requestId": request_id,
            }
        }
    ).encode()
    await send(
        {
            "type": "http.response.start",
            "status": 500,
            "headers": [(b"content-type", b"application/json"), (b"content-length", str(len(body)).encode())],
        }
    )
    await send({"type": "http.response.body", "body": body})
