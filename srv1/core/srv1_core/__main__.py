"""Yadroni ishga tushirish: `python -m srv1_core [--no-console]`."""

import argparse
import asyncio
import sys
from contextlib import suppress

import uvicorn
from pydantic import ValidationError

from srv1_core.app import build_settings, create_app
from srv1_core.lifecycle import port_in_use, set_exit_hook
from srv1_core.paths import DataPaths, resolve_data_dir

WS_MAX_MESSAGE_BYTES = 64 * 1024
# To'xtashda ochiq ulanishlar (shell WebSocket'i) shuncha kutiladi, keyin uziladi.
GRACEFUL_SHUTDOWN_S = 10
EXIT_BAD_CONFIG = 2
EXIT_PORT_BUSY = 3


def _arguments(argv: list[str] | None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(prog="python -m srv1_core", description="SRV_1 yadrosi")
    # Shell yadroni oynasiz ishga tushirganda: jurnal faqat faylga (logs/), konsolga emas.
    parser.add_argument("--no-console", action="store_true", help="jurnalni konsolga chiqarmaslik")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    options = _arguments(argv)
    paths = DataPaths(resolve_data_dir())
    try:
        settings = build_settings(paths)
    except (ValidationError, OSError) as exc:
        print(f"SRV_1: sozlamalarni o'qib bo'lmadi ({paths.config_file}):\n{exc}", file=sys.stderr)
        return EXIT_BAD_CONFIG
    host, port = settings.server.host, settings.server.port
    # Plaginlar (Caddy, Mosquitto, loyihalar) port ochilishidan oldin ishga tushadi: ikkinchi
    # yadro ularni ko'tarib, birinchisiga xalaqit bermasligi uchun avval tekshiramiz.
    if port_in_use(host, port):
        print(f"SRV_1: {host}:{port} band - yadro allaqachon ishlayapti.", file=sys.stderr)
        return EXIT_PORT_BUSY
    app = create_app(paths, settings, console_log=not options.no_console)
    config = uvicorn.Config(
        app,
        host=host,
        port=port,
        workers=1,
        log_config=None,
        access_log=False,
        server_header=False,
        ws_max_size=WS_MAX_MESSAGE_BYTES,
        timeout_graceful_shutdown=GRACEFUL_SHUTDOWN_S,
    )
    server = uvicorn.Server(config)

    def request_exit() -> None:
        server.should_exit = True

    set_exit_hook(app, request_exit)
    # Proactor: asyncio.subprocess Windows'da faqat shu loop bilan ishlaydi.
    # Ctrl+C (yoki xizmat to'xtashi): uvicorn tartibli yopilgach signalni qayta ko'taradi.
    with suppress(KeyboardInterrupt):
        asyncio.run(server.serve(), loop_factory=asyncio.ProactorEventLoop)
    return 0


if __name__ == "__main__":
    sys.exit(main())
