"""In-memory sliding-window rate limiter for sensitive endpoints (login, register, refresh).

Limits are per client IP per endpoint. State lives in the API process, so each worker
counts separately; put a shared limiter (e.g. Redis or the reverse proxy) in front when
running many instances.
"""

from __future__ import annotations

import time
from collections import defaultdict, deque
from collections.abc import Awaitable, Callable

import structlog
from fastapi import Request

from chitbook_api.core.config import get_settings
from chitbook_api.core.errors import AppError, ErrorCode

log = structlog.get_logger("chitbook.rate_limit")

WINDOW_SECONDS = 60.0


class SlidingWindowLimiter:
    def __init__(self) -> None:
        self._hits: dict[str, deque[float]] = defaultdict(deque)

    def hit(self, key: str, limit: int) -> bool:
        """Records a hit; returns False when the key is over the limit."""
        moment = time.monotonic()
        window = self._hits[key]
        while window and moment - window[0] > WINDOW_SECONDS:
            window.popleft()
        if len(window) >= limit:
            return False
        window.append(moment)
        return True

    def reset(self) -> None:
        self._hits.clear()


limiter = SlidingWindowLimiter()


def auth_rate_limit(name: str) -> Callable[[Request], Awaitable[None]]:
    """FastAPI dependency limiting an auth endpoint per client IP."""

    async def dependency(request: Request) -> None:
        ip = request.client.host if request.client else "unknown"
        if not limiter.hit(f"{name}:{ip}", get_settings().rate_limit_auth_per_minute):
            log.warning("rate_limit.exceeded", endpoint=name, client_ip=ip)
            raise AppError(ErrorCode.RATE_LIMITED)

    return dependency
