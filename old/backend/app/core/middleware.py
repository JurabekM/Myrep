"""HTTP middleware: request-id, structured access log, rate limiting, security headers."""

import time
import uuid

from fastapi import FastAPI, Request, Response
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint

from app.core.config import Settings
from app.core.exceptions import RateLimitExceededError
from app.core.logging import bind_request_id, clear_request_context, get_logger
from app.infrastructure.cache.redis import RedisManager

logger = get_logger("access")

_SECURITY_HEADERS = {
    "X-Content-Type-Options": "nosniff",
    "X-Frame-Options": "DENY",
    "Referrer-Policy": "strict-origin-when-cross-origin",
    "Permissions-Policy": "camera=(), geolocation=()",
}


class RequestContextMiddleware(BaseHTTPMiddleware):
    """Request-id propagation + access logging + security headers."""

    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        request_id = request.headers.get("x-request-id") or uuid.uuid4().hex
        bind_request_id(request_id)
        start = time.perf_counter()
        try:
            response = await call_next(request)
        finally:
            clear_request_context()
        response.headers["x-request-id"] = request_id
        for header, value in _SECURITY_HEADERS.items():
            response.headers.setdefault(header, value)
        logger.info(
            "http_request",
            method=request.method,
            path=request.url.path,
            status=response.status_code,
            duration_ms=round((time.perf_counter() - start) * 1000, 1),
        )
        return response


class RateLimitMiddleware(BaseHTTPMiddleware):
    """Coarse per-IP limit for unauthenticated traffic. Fine-grained per-user
    plan limits are enforced in the service layer (QuotaService)."""

    def __init__(self, app: FastAPI, redis: RedisManager, settings: Settings):
        super().__init__(app)
        self._redis = redis
        self._settings = settings

    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        client_ip = request.headers.get("x-forwarded-for", "").split(",")[0].strip() or (
            request.client.host if request.client else "unknown"
        )
        is_auth_endpoint = request.url.path.startswith(
            f"{self._settings.api_v1_prefix}/auth"
        )
        limit = (
            self._settings.rate_limit_auth if is_auth_endpoint else self._settings.rate_limit_default
        )
        exceeded = await self._redis.hit_rate_limit(
            f"rl:ip:{client_ip}:{'auth' if is_auth_endpoint else 'api'}", limit
        )
        if exceeded:
            error = RateLimitExceededError("So'rovlar soni cheklovdan oshdi")
            return Response(
                content=str(error.to_payload()),
                status_code=error.status_code,
                media_type="application/json",
                headers={"Retry-After": "60"},
            )
        return await call_next(request)
