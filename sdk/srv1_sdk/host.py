"""Bola jarayon: `python -m srv1_sdk.host --dir <plagin> --data-dir <papka>`.

Bitta plaginni yuklaydi va yadro bilan stdin/stdout orqali gaplashadi
(`srv1_sdk.protocol`). Plaginning `print()` chiqishi stderr'ga yo'naltiriladi.
"""

import argparse
import asyncio
import os
import sys
import threading
from collections.abc import Mapping
from contextlib import suppress
from fnmatch import fnmatchcase
from pathlib import Path
from typing import Any, BinaryIO

from srv1_sdk.context import LogLevel, PluginContext
from srv1_sdk.manifest import load_manifest
from srv1_sdk.protocol import (
    EXIT_LOAD_FAILED,
    EXIT_OUT_OF_MEMORY,
    Message,
    decode,
    encode,
    pack_body,
    unpack_body,
)
from srv1_sdk.runtime import LoadedPlugin


class _Channel:
    """Yadroga xabar yuboradi; `PluginContext` uchun `Backend` vazifasini ham bajaradi."""

    def __init__(self, out: BinaryIO) -> None:
        self._out = out
        self._lock = threading.Lock()

    def send(self, message: Message) -> None:
        data = encode(message)
        with self._lock:
            self._out.write(data)
            self._out.flush()

    def publish(self, topic: str, data: Mapping[str, Any]) -> None:
        self.send({"type": "publish", "topic": topic, "data": dict(data)})

    async def audit(self, action: str, target: str, ok: bool, detail: Mapping[str, Any]) -> None:
        self.send(
            {"type": "audit", "action": action, "target": target, "ok": ok, "detail": dict(detail)}
        )

    def log(self, level: LogLevel, event: str, fields: Mapping[str, Any]) -> None:
        self.send({"type": "log", "level": level, "event": event, "fields": dict(fields)})


def _start_reader(
    stdin: BinaryIO, loop: asyncio.AbstractEventLoop, queue: asyncio.Queue[Message | None]
) -> None:
    """stdin'ni alohida oqimda o'qiydi: bola tomondagi quvur overlapped emas."""

    def pump() -> None:
        try:
            for line in stdin:
                loop.call_soon_threadsafe(queue.put_nowait, decode(line))
        except (ValueError, OSError, RuntimeError):
            pass
        finally:
            with suppress(RuntimeError):  # loop allaqachon yopilgan bo'lishi mumkin
                loop.call_soon_threadsafe(queue.put_nowait, None)

    threading.Thread(target=pump, name="srv1-stdin", daemon=True).start()


class _Host:
    def __init__(self, plugin: LoadedPlugin, channel: _Channel) -> None:
        self._plugin = plugin
        self._channel = channel
        self._tasks: set[asyncio.Task[None]] = set()

    def announce_ready(self) -> None:
        plugin = self._plugin
        self._channel.send(
            {
                "type": "ready",
                "panel": None if plugin.panel is None else plugin.panel.model_dump(mode="json"),
                "subscriptions": [handler.pattern for handler in plugin.subscriptions],
                "jobs": [
                    {"id": job.id, "interval_s": job.interval_s, "cron": job.cron}
                    for job in plugin.jobs
                ],
            }
        )

    async def serve(self, queue: asyncio.Queue[Message | None]) -> None:
        while True:
            message = await queue.get()
            if message is None or message["type"] == "stop":
                break
            task = asyncio.create_task(self._guarded(message))
            self._tasks.add(task)
            task.add_done_callback(self._tasks.discard)
        for task in list(self._tasks):
            task.cancel()
        await asyncio.gather(*self._tasks, return_exceptions=True)

    async def _guarded(self, message: Message) -> None:
        try:
            await self._dispatch(message)
        except MemoryError:
            os._exit(EXIT_OUT_OF_MEMORY)
        except Exception as exc:
            self._channel.log(
                "error",
                "host_handler_failed",
                {"message_type": message.get("type"), "error": f"{type(exc).__name__}: {exc}"},
            )

    async def _dispatch(self, message: Message) -> None:
        kind = message["type"]
        if kind == "request":
            await self._request(message)
        elif kind == "event":
            topic: str = message["topic"]
            for handler in self._plugin.subscriptions:
                if fnmatchcase(topic, handler.pattern):
                    await handler.handler(topic, message["data"])
        elif kind == "job":
            for job in self._plugin.jobs:
                if job.id == message["id"]:
                    await job.func()

    async def _request(self, message: Message) -> None:
        response = await self._plugin.handle_request(
            method=message["method"],
            path=message["path"],
            query=str(message.get("query", "")).encode("latin-1"),
            headers=[(str(k), str(v)) for k, v in message.get("headers", [])],
            body=unpack_body(message.get("body", "")),
        )
        self._channel.send(
            {
                "type": "response",
                "id": message["id"],
                "status": response.status,
                "headers": [list(pair) for pair in response.headers],
                "body": pack_body(response.body),
            }
        )


async def _run(
    plugin_dir: Path,
    data_dir: Path,
    projects_dir: Path | None,
    stdin: BinaryIO,
    channel: _Channel,
) -> int:
    try:
        manifest = load_manifest(plugin_dir)
        ctx = PluginContext(manifest, data_dir, channel, projects_dir)
        plugin = LoadedPlugin(plugin_dir, manifest, ctx)
        plugin.load()
        await plugin.start()
    except MemoryError:
        return EXIT_OUT_OF_MEMORY
    except Exception as exc:
        channel.send({"type": "fatal", "error": f"{type(exc).__name__}: {exc}"})
        return EXIT_LOAD_FAILED
    host = _Host(plugin, channel)
    host.announce_ready()
    queue: asyncio.Queue[Message | None] = asyncio.Queue()
    _start_reader(stdin, asyncio.get_running_loop(), queue)
    await host.serve(queue)
    await plugin.stop()
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="srv1_sdk.host")
    parser.add_argument("--dir", type=Path, required=True)
    parser.add_argument("--data-dir", type=Path, required=True)
    parser.add_argument("--projects-dir", type=Path, default=None)
    args = parser.parse_args(argv)
    args.data_dir.mkdir(parents=True, exist_ok=True)
    stdin, protocol_out = sys.stdin.buffer, sys.stdout.buffer
    sys.stdout = sys.stderr  # plagin print() protokolni buzmasin
    try:
        channel = _Channel(protocol_out)
        return asyncio.run(_run(args.dir, args.data_dir, args.projects_dir, stdin, channel))
    except MemoryError:
        return EXIT_OUT_OF_MEMORY


if __name__ == "__main__":
    # Daemon oqim stdin'da bloklangan bo'lishi mumkin: interpretator yakunini kutmaymiz.
    os._exit(main())
