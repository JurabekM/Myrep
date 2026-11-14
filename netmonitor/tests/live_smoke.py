"""Jonli sinov: dasturni haqiqiy interfeysda ishga tushirib, o'zi yuborgan paketlarni ko'radimi — tekshiradi.

Ushlash drayveri (Windows'da Npcap) va huquq (Linux'da root) kerak, shuning uchun pytest to'plamiga kirmaydi.

    python tests/live_smoke.py python netmonitor.py
    python tests\\live_smoke.py release\\NetMonitor.exe

`NETMONITOR_SMOKE_NO_FILTER=1` — ushlash filtrisiz (libpcap o'rnatilmagan Linux uchun).
"""

from __future__ import annotations

import json
import os
import socket
import subprocess
import sys
import tempfile
import threading
import time
from pathlib import Path

# Hujjatlar uchun ajratilgan tarmoqlar: hech kimga yetib bormaydi, lekin paket interfeysdan chiqadi.
TARGET = ("203.0.113.9", 9)
MARKER = b"netmonitor-smoke login=sinov&password=JonliSinov77"
EXCLUDED = "198.51.100.9"
CAPTURE_FILTER = "udp and (net 203.0.113.0/24 or net 198.51.100.0/24)"


def local_address() -> str:
    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as probe:
        probe.connect(TARGET)
        return str(probe.getsockname()[0])


def send(count: int, target: tuple[str, int]) -> None:
    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sender:
        for _ in range(count):
            sender.sendto(MARKER, target)
            time.sleep(0.05)


def main() -> int:
    command = sys.argv[1:]
    if not command:
        print(__doc__)
        return 2
    address = local_address()
    problems: list[str] = []
    with tempfile.TemporaryDirectory(prefix="netmonitor-live-") as folder_name:
        folder = Path(folder_name)
        config = folder / "config.json"
        settings = {"log_folder": str(folder / "logs"), "capture_filter": CAPTURE_FILTER}
        if os.environ.get("NETMONITOR_SMOKE_NO_FILTER"):  # libpcap yo'q tizim: filtr kompilyatsiya qilinmaydi
            del settings["capture_filter"]
        config.write_text(json.dumps(settings), encoding="utf-8")
        process = subprocess.Popen(
            [*command, "--config", str(config), "--iface", address],
            stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
            text=True, encoding="utf-8", errors="replace",
        )
        lines: list[str] = []
        reader = threading.Thread(target=lambda: lines.extend(process.stdout), daemon=True)  # type: ignore[arg-type]
        reader.start()

        def say(text: str) -> None:
            assert process.stdin is not None
            process.stdin.write(text + "\n")
            process.stdin.flush()

        try:
            time.sleep(6.0)  # interfeys ochilishini kutish
            if process.poll() is not None:
                problems.append(f"dastur erta tugadi (kod {process.returncode})")
            else:
                send(5, TARGET)
                time.sleep(1.5)
                say(f"exclude {EXCLUDED}")
                time.sleep(0.5)
                send(5, (EXCLUDED, 9))
                time.sleep(1.5)
                say("pause")
                time.sleep(0.5)
                send(5, TARGET)
                time.sleep(1.5)
                say("status")
                say("exit")
                try:
                    process.wait(20)
                except subprocess.TimeoutExpired:
                    problems.append("`exit` buyrug'idan keyin dastur 20 s ichida tugamadi")
        finally:
            if process.poll() is None:
                process.kill()
            reader.join(5)
        output = "".join(lines)
        print(output)
        if process.returncode != 0:
            problems.append(f"chiqish kodi {process.returncode}")
        records = []
        for path in sorted((folder / "logs").glob("captured_packets*.json")):
            records += [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines()]
        seen = [r for r in records if r["ip"]["dst_ip"] == TARGET[0] and r.get("transport", {}).get("dst_port") == 9]
        if len(seen) != 5:
            problems.append(f"jurnalda {TARGET[0]} ga {len(seen)} paket, kutilgan 5 (pauzadagilar tushmasligi kerak)")
        if any(r["ip"]["dst_ip"] == EXCLUDED for r in records):
            problems.append("chiqarilgan manzil jurnalga tushdi")
        if "JonliSinov77" in output or any("JonliSinov77" in json.dumps(r) for r in records):
            problems.append("parol qiymati yashirilmadi")
        for expected in ("XAVFLI PAYLOAD", "Ochiq matnda maxfiy maydon (login, password)", "CHIQARILDI", "PAUZA"):
            if expected not in output:
                problems.append(f"chiqishda yo'q: {expected}")
    if problems:
        print("JONLI SINOV MUVAFFAQIYATSIZ:")
        for problem in problems:
            print(f"  - {problem}")
        return 1
    print(f"JONLI SINOV MUVAFFAQIYATLI: interfeys {address}, 5 paket ushlandi, pauza va exclude ishladi")
    return 0


if __name__ == "__main__":
    sys.exit(main())
