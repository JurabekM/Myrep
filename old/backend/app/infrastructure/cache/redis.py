"""Redis connection + small typed helpers used across the app.

Responsibilities: session/refresh-token storage, rate-limit counters,
response cache, WebSocket pub/sub.
"""

import json
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from typing import Any

from redis.asyncio import Redis, from_url

from app.core.config import Settings
from app.core.logging import get_logger

logger = get_logger(__name__)


class RedisManager:
    def __init__(self, settings: Settings):
        self._settings = settings
        self._client: Redis | None = None

    async def connect(self) -> None:
        self._client = from_url(
            str(self._settings.redis_dsn),
            encoding="utf-8",
            decode_responses=True,
            max_connections=50,
        )
        await self._client.ping()
        logger.info("redis_connected")

    async def disconnect(self) -> None:
        if self._client is not None:
            await self._client.aclose()
            self._client = None
            logger.info("redis_disconnected")

    @property
    def client(self) -> Redis:
        if self._client is None:
            raise RuntimeError("RedisManager.connect() has not been called")
        return self._client

    # --- JSON cache helpers ---

    async def get_json(self, key: str) -> Any | None:
        raw = await self.client.get(key)
        return json.loads(raw) if raw is not None else None

    async def set_json(self, key: str, value: Any, ttl_seconds: int) -> None:
        await self.client.set(key, json.dumps(value, ensure_ascii=False), ex=ttl_seconds)

    async def delete(self, *keys: str) -> None:
        if keys:
            await self.client.delete(*keys)

    # --- Sliding-window rate limiting ---

    async def hit_rate_limit(self, key: str, limit: int, window_seconds: int = 60) -> bool:
        """Increment counter for `key`; return True when the limit is exceeded."""
        pipe = self.client.pipeline()
        pipe.incr(key)
        pipe.expire(key, window_seconds, nx=True)
        count, _ = await pipe.execute()
        return int(count) > limit

    # --- Pub/Sub (WebSocket fan-out) ---

    async def publish(self, channel: str, message: dict[str, Any]) -> None:
        await self.client.publish(channel, json.dumps(message, ensure_ascii=False))

    @asynccontextmanager
    async def subscribe(self, channel: str) -> AsyncIterator[Any]:
        pubsub = self.client.pubsub()
        await pubsub.subscribe(channel)
        try:
            yield pubsub
        finally:
            await pubsub.unsubscribe(channel)
            await pubsub.aclose()
