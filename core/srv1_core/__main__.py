"""Yadroni ishga tushirish: `python -m srv1_core`."""

import asyncio
import sys

import uvicorn
from pydantic import ValidationError

from srv1_core.app import build_settings, create_app
from srv1_core.paths import DataPaths, resolve_data_dir

WS_MAX_MESSAGE_BYTES = 64 * 1024


def main() -> int:
    paths = DataPaths(resolve_data_dir())
    try:
        settings = build_settings(paths)
    except (ValidationError, OSError) as exc:
        print(f"SRV_1: sozlamalarni o'qib bo'lmadi ({paths.config_file}):\n{exc}", file=sys.stderr)
        return 2
    config = uvicorn.Config(
        create_app(paths, settings, console_log=True),
        host=settings.server.host,
        port=settings.server.port,
        workers=1,
        log_config=None,
        access_log=False,
        server_header=False,
        ws_max_size=WS_MAX_MESSAGE_BYTES,
    )
    server = uvicorn.Server(config)
    # Proactor: asyncio.subprocess Windows'da faqat shu loop bilan ishlaydi.
    asyncio.run(server.serve(), loop_factory=asyncio.ProactorEventLoop)
    return 0


if __name__ == "__main__":
    sys.exit(main())
