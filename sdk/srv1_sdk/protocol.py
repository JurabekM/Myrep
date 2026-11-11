"""Yadro <-> bola jarayon protokoli: stdin/stdout orqali JSON qatorlar (har qatorda bitta xabar).

Yadro -> bola:
  {"type": "request", "id", "method", "path", "query", "headers", "body"}   # body: base64
  {"type": "event", "topic", "data"}
  {"type": "job", "id"}
  {"type": "stop"}

Bola -> yadro:
  {"type": "ready", "panel", "subscriptions": [naqsh], "jobs": [{"id", "interval_s", "cron"}]}
  {"type": "fatal", "error"}
  {"type": "response", "id", "status", "headers", "body"}                  # body: base64
  {"type": "publish", "topic", "data"}
  {"type": "audit", "action", "target", "ok", "detail"}
  {"type": "log", "level", "event", "fields"}
"""

import base64
import json
from typing import Any, cast

# asyncio.StreamReader qator chegarasi; eng katta javob (8 MiB) base64 da ~10,7 MiB.
LINE_LIMIT = 16 * 1024 * 1024
EXIT_OUT_OF_MEMORY = 70
EXIT_LOAD_FAILED = 71

Message = dict[str, Any]


def encode(message: Message) -> bytes:
    return json.dumps(message, ensure_ascii=False, separators=(",", ":")).encode("utf-8") + b"\n"


def decode(line: bytes) -> Message:
    parsed = json.loads(line)
    if not isinstance(parsed, dict) or not isinstance(cast(Message, parsed).get("type"), str):
        raise ValueError("xabar 'type' maydonli obyekt bo'lishi kerak")
    return cast(Message, parsed)


def pack_body(body: bytes) -> str:
    return base64.b64encode(body).decode("ascii")


def unpack_body(text: str) -> bytes:
    return base64.b64decode(text, validate=True)
