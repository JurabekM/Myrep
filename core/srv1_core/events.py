"""Ichki asyncio pub/sub. Sekin obunachi nashrni to'xtatmaydi: eng eski hodisa tashlanadi."""

import asyncio
import itertools
import time
from collections.abc import Mapping
from dataclasses import dataclass, field
from fnmatch import fnmatchcase
from typing import Any, Self


@dataclass(frozen=True, slots=True)
class Event:
    topic: str
    data: Mapping[str, Any]
    ts: float
    seq: int

    def as_dict(self) -> dict[str, Any]:
        return {"topic": self.topic, "data": dict(self.data), "ts": self.ts, "seq": self.seq}


@dataclass(eq=False, slots=True)
class Subscription:
    """Hodisalar navbati. `async for` bilan o'qiladi; shina yopilganda tugaydi."""

    patterns: tuple[str, ...]
    _queue: asyncio.Queue[Event | None]
    dropped: int = 0
    _closed: bool = field(default=False)

    def matches(self, topic: str) -> bool:
        return any(fnmatchcase(topic, pattern) for pattern in self.patterns)

    def take_dropped(self) -> int:
        """Oxirgi chaqiruvdan beri tashlangan hodisalar sonini qaytaradi va nolga tushiradi."""
        count, self.dropped = self.dropped, 0
        return count

    def _offer(self, item: Event | None) -> None:
        if self._closed:
            return
        if self._queue.full():
            self._queue.get_nowait()
            self.dropped += 1
        self._queue.put_nowait(item)
        if item is None:
            self._closed = True

    def __aiter__(self) -> Self:
        return self

    async def __anext__(self) -> Event:
        item = await self._queue.get()
        if item is None:
            raise StopAsyncIteration
        return item


class EventBus:
    """Mavzu bo'yicha nashr/obuna. Faqat event loop oqimidan chaqiriladi."""

    def __init__(self, queue_size: int = 256) -> None:
        self._queue_size = queue_size
        self._subscriptions: set[Subscription] = set()
        self._seq = itertools.count(1)
        self._closed = False

    def subscribe(self, *patterns: str) -> Subscription:
        """Naqshlar `fnmatch` uslubida: `system.*`, `audit`, `*`."""
        if self._closed:
            raise RuntimeError("hodisalar shinasi yopilgan")
        subscription = Subscription(patterns or ("*",), asyncio.Queue(self._queue_size))
        self._subscriptions.add(subscription)
        return subscription

    def unsubscribe(self, subscription: Subscription) -> None:
        self._subscriptions.discard(subscription)
        subscription._offer(None)  # pyright: ignore[reportPrivateUsage]

    def publish(self, topic: str, data: Mapping[str, Any] | None = None) -> Event:
        event = Event(topic=topic, data=data or {}, ts=time.time(), seq=next(self._seq))
        for subscription in self._subscriptions:
            if subscription.matches(topic):
                subscription._offer(event)  # pyright: ignore[reportPrivateUsage]
        return event

    def has_subscribers(self, topic: str) -> bool:
        return any(subscription.matches(topic) for subscription in self._subscriptions)

    @property
    def subscriber_count(self) -> int:
        return len(self._subscriptions)

    def close(self) -> None:
        """Barcha obunachilarni tugatadi; keyingi `subscribe` xato beradi."""
        self._closed = True
        for subscription in list(self._subscriptions):
            self.unsubscribe(subscription)
