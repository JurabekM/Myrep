"""`WS /ws/events` — hodisalar oqimi. Token faqat `Authorization` sarlavhasida qabul qilinadi."""

import asyncio
import re
from contextlib import suppress
from typing import Annotated

from fastapi import APIRouter, Query, WebSocket, WebSocketDisconnect, status

from srv1_core.events import Subscription
from srv1_core.state import get_core

router = APIRouter()

MAX_PATTERNS = 16
DROPPED_TOPIC = "bus.dropped"
_PATTERN_RE = re.compile(r"[a-z0-9_.*-]{1,64}")


def parse_topics(raw: str) -> tuple[str, ...] | None:
    """`system.*,audit` -> naqshlar; yaroqsiz bo'lsa `None`."""
    patterns = tuple(part.strip() for part in raw.split(",") if part.strip())
    if not patterns or len(patterns) > MAX_PATTERNS:
        return None
    if not all(_PATTERN_RE.fullmatch(pattern) for pattern in patterns):
        return None
    return patterns


async def _pump(ws: WebSocket, subscription: Subscription) -> None:
    """Hodisalarni klientga uzatadi; shina yopilganda tugaydi."""
    async for event in subscription:
        dropped = subscription.take_dropped()
        if dropped:
            await ws.send_json({"topic": DROPPED_TOPIC, "data": {"count": dropped}})
        await ws.send_json(event.as_dict())


async def _drain(ws: WebSocket) -> None:
    """Klient xabarlari e'tiborsiz; vazifasi — uzilishni payqash."""
    with suppress(WebSocketDisconnect):
        while True:
            await ws.receive_text()


@router.websocket("/ws/events")
async def events(ws: WebSocket, topics: Annotated[str, Query(max_length=512)] = "*") -> None:
    core = get_core(ws)
    patterns = parse_topics(topics)
    if patterns is None or not core.auth.verify_header(ws.headers.get("authorization")):
        await ws.close(code=status.WS_1008_POLICY_VIOLATION)
        return
    await ws.accept()
    subscription = core.bus.subscribe(*patterns)
    pump = asyncio.create_task(_pump(ws, subscription))
    drain = asyncio.create_task(_drain(ws))
    try:
        await asyncio.wait({pump, drain}, return_when=asyncio.FIRST_COMPLETED)
    finally:
        core.bus.unsubscribe(subscription)
        bus_closed = pump.done() and not pump.cancelled() and pump.exception() is None
        for task in (pump, drain):
            task.cancel()
        await asyncio.gather(pump, drain, return_exceptions=True)
        if bus_closed:
            with suppress(RuntimeError, WebSocketDisconnect):
                await ws.close(code=status.WS_1001_GOING_AWAY)
