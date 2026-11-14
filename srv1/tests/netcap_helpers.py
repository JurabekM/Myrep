"""Tarmoq kuzatuvi sinovlari uchun: soxta ushlash ishchisi va plagin modullarini yuklash."""

import importlib
import sys
from pathlib import Path
from types import ModuleType

from srv1_core.plugins.registry import BUILTIN_DIR

# Haqiqiy ishchi o'rniga ishlaydigan skript: Npcap va tarmoqsiz, oldindan ma'lum natija bilan.
# Sozlama faylini o'qiydi, `ready` yuboradi, so'ng har 0,1 s da `tick`. Birinchi tick'da
# ikkita paket va bitta signal bor. Buyruqlarni stdin'dan oladi va holatini tick'da qaytaradi.
# `bpf_filter` `crash` bo'lsa — boshlanmay xato bilan chiqadi; `die` bo'lsa — bitta
# tick'dan so'ng o'ladi.
FAKE_WORKER = r"""
import json, sys, threading, time

options = json.load(open(sys.argv[1], encoding="utf-8"))
state = {"paused": False, "excluded": list(options.get("excluded", [])), "stop": False}


def emit(message):
    sys.stdout.write(json.dumps(message) + "\n")
    sys.stdout.flush()


def commands():
    for line in sys.stdin:
        message = json.loads(line)
        if message["c"] == "stop":
            break
        if message["c"] == "pause":
            state["paused"] = True
        elif message["c"] == "resume":
            state["paused"] = False
        elif message["c"] == "exclude":
            state["excluded"] = message["ips"]
    state["stop"] = True


if options.get("bpf_filter") == "crash":
    print("Traceback: soxta ishchi yiqildi")
    emit({"t": "error", "error": "soxta xato: interfeys ochilmadi"})
    sys.exit(3)

threading.Thread(target=commands, daemon=True).start()
emit({"t": "ready", "interface": options["interface"]})
total = 0
first = True
while not state["stop"]:
    packets, alerts = [], []
    if first:
        first = False
        now = time.time()
        packets = [
            {"ts": now, "proto": "TCP", "src": "10.0.0.5", "sport": 50000, "dst": "10.0.0.9",
             "dport": 80, "len": 120, "info": "[PA]", "mark": "password",
             **({"payload": "password=..."} if options.get("store_payload") else {})},
            {"ts": now, "proto": "UDP", "src": "10.0.0.5", "sport": 5353, "dst": "8.8.8.8",
             "dport": 53, "len": 70, "info": "DNS? example.com", "mark": ""},
        ]
        alerts = [{"ts": now, "kind": "secret", "src": "10.0.0.5", "dst": "10.0.0.9",
                   "note": "password -> :80"}]
        total = 2
    emit({"t": "tick", "ts": time.time(), "paused": state["paused"], "total": total,
          "ignored": len(state["excluded"]), "skipped": 0, "errors": 0, "last_error": "",
          "suppressed": 0, "bytes": 190, "pps": 2.0 if packets else 0.0,
          "packets": packets, "alerts": alerts,
          "hosts": [{"ip": "10.0.0.5", "packets": 2, "bytes": 190, "where": ""}]})
    if options.get("bpf_filter") == "die":
        sys.exit(7)
    time.sleep(0.1)
emit({"t": "tick", "ts": time.time(), "paused": state["paused"], "total": total, "packets": [],
      "alerts": [], "hosts": []})
"""


def netcap_module(name: str) -> ModuleType:
    """`plugins.monitor.netcap.<name>` — repozitoriydagi koddan."""
    sys.path.insert(0, str(BUILTIN_DIR.parent))
    try:
        return importlib.import_module(f"plugins.monitor.netcap.{name}")
    finally:
        sys.path.pop(0)


def write_fake_worker(directory: Path) -> Path:
    script = directory / "fake_netcap_worker.py"
    script.write_text(FAKE_WORKER, encoding="utf-8")
    return script
