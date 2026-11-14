"""Ushlash ishchisi: `python -m netcap.worker <sozlama.json>`.

`monitor` plagini tomonidan `ctx.spawn` bilan (xotira limiti ostida) ishga tushiriladi.

- stdout: har satr — bitta JSON xabar (`ready`, `tick`, `error`);
- stdin: har satr — bitta JSON buyruq (`pause`, `resume`, `exclude`, `stop`). stdin
  yopilsa (plagin to'xtadi yoki o'ldi), ishchi ham yopiladi.

Uch oqim: ushlash (scapy), buyruqlar (stdin), asosiy (har soniyada `tick` yuboradi).
"""

import json
import os
import sys
import threading
import time
from pathlib import Path
from typing import Any

from .engine import Engine, Options
from .geo import GeoResolver

TICK_S = 1.0
EXIT_BAD_ARGS = 2
EXIT_CAPTURE_FAILED = 3

_out_lock = threading.Lock()


def emit(message: dict[str, Any]) -> None:
    line = json.dumps(message, ensure_ascii=True, separators=(",", ":"))
    with _out_lock:
        sys.stdout.write(line + "\n")
        sys.stdout.flush()


def _read_commands(engine: Engine, stop: threading.Event) -> None:
    for line in sys.stdin:
        try:
            message = json.loads(line)
        except ValueError:
            continue
        if isinstance(message, dict) and not engine.command(message):  # pyright: ignore[reportUnknownArgumentType]
            break
    stop.set()


def _capture(engine: Engine, stop: threading.Event, failure: list[str]) -> None:
    """scapy shu yerda yuklanadi: import xatosi ham (Npcap yo'q) `error` xabari bo'lib chiqadi."""
    try:
        from scapy.config import conf

        conf.verb = 0
        from scapy.sendrecv import sniff

        from .parse import parse
    except Exception as exc:
        failure.append(f"scapy yuklanmadi: {type(exc).__name__}: {exc}")
        stop.set()
        return

    def on_packet(packet: Any) -> None:  # noqa: ANN401 — scapy paketi
        # Bitta buzuq paket ushlashni to'xtatmasligi kerak.
        try:
            engine.handle(parse(packet))
        except Exception as exc:
            engine.failed(exc)

    options = engine.options
    try:
        sniff(  # pyright: ignore[reportUnknownVariableType]
            iface=options.interface,
            prn=on_packet,
            store=False,
            filter=options.bpf_filter or None,
            started_callback=lambda: emit({"t": "ready", "interface": options.interface}),
        )
        failure.append("ushlash kutilmaganda tugadi")
    except Exception as exc:
        failure.append(f"{type(exc).__name__}: {exc}"[:300])
    stop.set()


def main(argv: list[str]) -> int:
    if len(argv) != 2:
        emit({"t": "error", "error": "foydalanish: python -m netcap.worker <sozlama.json>"})
        return EXIT_BAD_ARGS
    try:
        options = Options.from_json(json.loads(Path(argv[1]).read_text(encoding="utf-8")))
    except (OSError, ValueError, KeyError, TypeError) as exc:
        emit({"t": "error", "error": f"sozlama o'qilmadi: {exc}"})
        return EXIT_BAD_ARGS

    geo: GeoResolver | None = None
    if options.geo:
        geo = GeoResolver()
        geo.start()
    engine = Engine(options, geo.lookup if geo is not None else None)
    stop = threading.Event()
    failure: list[str] = []
    threading.Thread(target=_read_commands, args=(engine, stop), daemon=True).start()
    threading.Thread(target=_capture, args=(engine, stop, failure), daemon=True).start()

    last = time.monotonic()
    while not stop.wait(TICK_S):
        now = time.monotonic()
        emit(engine.tick(time.time(), now - last))
        last = now
    if failure:
        emit({"t": "error", "error": failure[0]})
        return EXIT_CAPTURE_FAILED
    emit(engine.tick(time.time(), time.monotonic() - last))
    return 0


if __name__ == "__main__":
    # Ushlash oqimi drayver chaqiruvida kutib turgan bo'lishi mumkin: uni kutmasdan chiqiladi.
    code = main(sys.argv)
    sys.stdout.flush()
    os._exit(code)
