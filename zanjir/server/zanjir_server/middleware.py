"""ASGI middleware: so'rov hajmi cheklovi, rate limiting, kirish logi va metrikalar."""

from __future__ import annotations

import logging
import time
import uuid
from collections import defaultdict
from collections.abc import Callable

from starlette.types import ASGIApp, Message, Receive, Scope, Send

from zanjir_server.observability import ErrorReporter, Metrics

log = logging.getLogger("zanjir.access")


async def _json(send: Send, status: int, body: bytes, headers: list[tuple[bytes, bytes]] | None = None) -> None:
    await send(
        {
            "type": "http.response.start",
            "status": status,
            "headers": [(b"content-type", b"application/json"), *(headers or [])],
        }
    )
    await send({"type": "http.response.body", "body": body})


class BodyLimitMiddleware:
    """Chegaradan katta so'rov — 413. `Content-Length` bo'lsa darhol; bo'lmasa (chunked) tana oldindan o'qiladi."""

    def __init__(self, app: ASGIApp, max_bytes: int) -> None:
        self.app = app
        self.max_bytes = max_bytes

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return
        length = next((v for k, v in scope["headers"] if k == b"content-length"), None)
        if length is not None:
            if not length.isdigit() or int(length) > self.max_bytes:
                await _json(send, 413, b'{"detail":{"code":"body_too_large"}}')
                return
            await self.app(scope, receive, send)
            return
        messages: list[Message] = []
        size = 0
        while True:
            msg = await receive()
            messages.append(msg)
            if msg["type"] != "http.request":
                break
            size += len(msg.get("body", b""))
            if size > self.max_bytes:
                await _json(send, 413, b'{"detail":{"code":"body_too_large"}}')
                return
            if not msg.get("more_body", False):
                break

        async def replay() -> Message:
            return messages.pop(0) if messages else await receive()

        await self.app(scope, replay, send)


class RateLimiter:
    """Bir daqiqalik oyna, (guruh, IP) bo'yicha; bitta jarayon uchun (ko'p nusxada — Redis, ADR-0011)."""

    def __init__(self, clock: Callable[[], float] = time.monotonic) -> None:
        self._clock = clock
        self._hits: dict[tuple[str, str], tuple[int, int]] = defaultdict(lambda: (0, 0))

    def hit(self, bucket: str, key: str, limit: int) -> int | None:
        """Ruxsat bo'lsa None, aks holda keyingi oynagacha soniyalar."""
        now = self._clock()
        window = int(now // 60)
        w, n = self._hits[(bucket, key)]
        if w != window:
            w, n = window, 0
        n += 1
        self._hits[(bucket, key)] = (w, n)
        if len(self._hits) > 100_000:
            self._hits = defaultdict(lambda: (0, 0), {k: v for k, v in self._hits.items() if v[0] == window})
        return None if n <= limit else max(1, int((window + 1) * 60 - now))


class RateLimitMiddleware:
    def __init__(self, app: ASGIApp, limiter: RateLimiter, auth_limit: int, default_limit: int) -> None:
        self.app = app
        self.limiter = limiter
        self.auth_limit = auth_limit
        self.default_limit = default_limit

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        path: str = scope.get("path", "")
        if scope["type"] != "http" or path in ("/healthz", "/readyz", "/metrics"):
            await self.app(scope, receive, send)
            return
        auth = path.startswith("/auth/")
        client = scope.get("client")
        ip = client[0] if client else "-"
        retry = self.limiter.hit("auth" if auth else "default", ip, self.auth_limit if auth else self.default_limit)
        if retry is not None:
            await _json(send, 429, b'{"detail":{"code":"rate_limited"}}', [(b"retry-after", str(retry).encode())])
            return
        await self.app(scope, receive, send)


class AccessLogMiddleware:
    """JSON kirish logi va metrikalar; kutilmagan xato — adapterga va 500."""

    def __init__(self, app: ASGIApp, metrics: Metrics, reporter: ErrorReporter) -> None:
        self.app = app
        self.metrics = metrics
        self.reporter = reporter

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return
        start = time.perf_counter()
        status = 500
        started = False
        request_id = uuid.uuid4().hex[:16]

        async def wrapped(msg: Message) -> None:
            nonlocal status, started
            if msg["type"] == "http.response.start":
                status = msg["status"]
                started = True
                msg["headers"] = [*msg.get("headers", []), (b"x-request-id", request_id.encode())]
            await send(msg)

        try:
            await self.app(scope, receive, wrapped)
        except Exception as e:
            route = _route(scope)
            self.reporter.report(e, route=route)
            log.exception("unhandled", extra={"fields": {"route": route, "request_id": request_id}})
            status = 500
            if not started:
                await _json(send, 500, b'{"detail":{"code":"internal_error"}}')
        finally:
            route = _route(scope)
            elapsed = time.perf_counter() - start
            self.metrics.requests.labels(scope["method"], route, str(status)).inc()
            self.metrics.latency.labels(scope["method"], route).observe(elapsed)
            log.info(
                "request",
                extra={
                    "fields": {
                        "method": scope["method"],
                        "route": route,
                        "status": status,
                        "ms": round(elapsed * 1000, 1),
                        "request_id": request_id,
                    }
                },
            )


def _route(scope: Scope) -> str:
    """Marshrut shabloni (`/v/{qr_token}`) — haqiqiy yo'l (token, ID) logga yozilmaydi."""
    route = scope.get("route")
    path = getattr(route, "path", None)
    return path if isinstance(path, str) else "unmatched"
