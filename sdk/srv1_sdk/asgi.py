"""ASGI ilovasini tarmoqsiz chaqirish: bitta so'rov -> bitta to'liq javob."""

import asyncio
from collections.abc import Awaitable, Callable, MutableMapping, Sequence
from dataclasses import dataclass
from typing import Any

Message = MutableMapping[str, Any]
AsgiApp = Callable[
    [
        MutableMapping[str, Any],
        Callable[[], Awaitable[Message]],
        Callable[[Message], Awaitable[None]],
    ],
    Awaitable[None],
]

MAX_RESPONSE_BYTES = 8 * 1024 * 1024
JSON_HEADERS = (("content-type", "application/json"),)


@dataclass(frozen=True, slots=True)
class AsgiResponse:
    status: int
    headers: tuple[tuple[str, str], ...]
    body: bytes

    @property
    def content_type(self) -> str | None:
        return next((value for key, value in self.headers if key == "content-type"), None)


def json_error(status: int, detail: str) -> AsgiResponse:
    safe = detail.replace("\\", "\\\\").replace('"', '\\"')
    return AsgiResponse(status, JSON_HEADERS, f'{{"detail":"{safe}"}}'.encode())


def _scope(
    method: str, path: str, query: bytes, headers: Sequence[tuple[str, str]]
) -> dict[str, Any]:
    return {
        "type": "http",
        "asgi": {"version": "3.0", "spec_version": "2.3"},
        "http_version": "1.1",
        "method": method.upper(),
        "scheme": "http",
        "path": path,
        "raw_path": path.encode("utf-8"),
        "query_string": query,
        "root_path": "",
        "headers": [(k.lower().encode("latin-1"), v.encode("latin-1")) for k, v in headers],
        "client": ("127.0.0.1", 0),
        "server": ("127.0.0.1", 0),
    }


class _Collector:
    def __init__(self) -> None:
        self.status = 500
        self.headers: tuple[tuple[str, str], ...] = ()
        self.started = False
        self.chunks: list[bytes] = []
        self.size = 0

    async def send(self, message: Message) -> None:
        if message["type"] == "http.response.start":
            self.status = int(message["status"])
            raw: Sequence[tuple[bytes, bytes]] = message.get("headers", [])
            self.headers = tuple((k.decode("latin-1").lower(), v.decode("latin-1")) for k, v in raw)
            self.started = True
        elif message["type"] == "http.response.body":
            chunk: bytes = message.get("body", b"")
            self.size += len(chunk)
            if self.size > MAX_RESPONSE_BYTES:
                raise OverflowError("javob juda katta")
            self.chunks.append(chunk)

    def response(self) -> AsgiResponse:
        return AsgiResponse(self.status, self.headers, b"".join(self.chunks))


async def call_asgi(
    app: AsgiApp,
    *,
    method: str,
    path: str,
    query: bytes = b"",
    headers: Sequence[tuple[str, str]] = (),
    body: bytes = b"",
) -> AsgiResponse:
    """`app` ni bitta HTTP so'rov bilan chaqiradi. Oqimli javoblar to'liq yig'iladi."""
    delivered = False

    async def receive() -> Message:
        nonlocal delivered
        if not delivered:
            delivered = True
            return {"type": "http.request", "body": body, "more_body": False}
        await asyncio.Event().wait()  # klient uzilmaydi: javob tugaguncha kutadi
        raise AssertionError("unreachable")

    collector = _Collector()
    try:
        await app(_scope(method, path, query, headers), receive, collector.send)
    except MemoryError:
        raise
    except OverflowError:
        return json_error(502, "plagin javobi juda katta")
    except Exception as exc:
        if not collector.started:
            return json_error(500, f"plagin xatosi: {type(exc).__name__}")
    return collector.response()
