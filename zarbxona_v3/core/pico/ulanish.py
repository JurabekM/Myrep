"""Pico'ni topish va ulash; profildagi `imzolovchi.json`.

Port yozuvi:
  * `auto`            — Raspberry Pi USB qurilmalari orasidan topadi (VID 0x2E8A);
  * `COM5`, `/dev/ttyACM0` — aniq port;
  * `soxta:<fayl>`    — apparatsiz SOXTA Pico (demo/test); tugma avtomatik bosiladi.
"""

from __future__ import annotations

import json
import os
import time
from dataclasses import dataclass
from pathlib import Path

from . import protokol as P
from .qurilma import DEFAULT_RUXSAT_S, PicoImzolovchi

RPI_VID = 0x2E8A
MAHSULOT = "AETHER-Q Pico HSM"      # ichki dastur USB mahsulot nomi
SOZLAMA_FAYLI = "imzolovchi.json"
SOXTA = "soxta:"


class SerialTashuvchi:
    nomi = "pico"

    def __init__(self, port: str):
        try:
            import serial
        except ImportError as e:            # pragma: no cover — requirements'da bor
            raise P.PicoXatosi(P.X_ALOQA, "pyserial o'rnatilmagan (pip install pyserial)") from e
        self._serial = serial
        self.port = port
        try:
            self.s = serial.Serial(port, 115200, timeout=0.05, write_timeout=5)
        except (serial.SerialException, OSError) as e:
            raise P.PicoXatosi(P.X_ALOQA, f"{port} ochilmadi: {e}") from e

    def yoz(self, b: bytes) -> None:
        try:
            self.s.write(b)
            self.s.flush()
        except self._serial.SerialException as e:
            raise OSError(str(e)) from e

    def oqi(self, kutish: float) -> bytes:
        oxiri = time.monotonic() + kutish
        try:
            while True:
                n = self.s.in_waiting
                if n:
                    return self.s.read(n)
                b = self.s.read(1)          # timeout=0.05 bilan bloklanadi
                if b:
                    return b + self.s.read(self.s.in_waiting)
                if time.monotonic() >= oxiri:
                    return b""
        except self._serial.SerialException as e:
            raise OSError(str(e)) from e

    def tozala(self) -> None:
        try:
            self.s.reset_input_buffer()
        except self._serial.SerialException as e:
            raise OSError(str(e)) from e

    def yop(self) -> None:
        self.s.close()


def portlar() -> list[tuple[str, str]]:
    """(port, tavsif) — Raspberry Pi USB qurilmalari; bizning ichki dastur birinchi."""
    try:
        from serial.tools import list_ports
    except ImportError:
        return []
    topildi = [(p.device, f"{p.product or p.description or ''} {p.serial_number or ''}".strip())
               for p in list_ports.comports() if p.vid == RPI_VID]
    return sorted(topildi, key=lambda x: MAHSULOT not in x[1])


def tashuvchi_och(port: str = "auto"):
    if port.startswith(SOXTA):
        from .soxta import SoxtaPico, SoxtaTashuvchi
        return SoxtaTashuvchi(SoxtaPico(Path(port[len(SOXTA):])))
    if port == "auto":
        p = portlar()
        if not p:
            raise P.PicoXatosi(P.X_ALOQA, "Pico topilmadi — USB kabelni tekshiring (faqat "
                                          "zaryad beradigan kabel ishlamaydi)")
        port = p[0][0]
    return SerialTashuvchi(port)


@dataclass
class PicoSozlama:
    port: str = "auto"
    public_key: bytes | None = None
    seriya: bytes | None = None
    ruxsat_muddati_s: int = DEFAULT_RUXSAT_S

    def lugat(self) -> dict:
        return {"tur": "pico", "port": self.port,
                "public_key": self.public_key.hex() if self.public_key else None,
                "seriya": self.seriya.hex() if self.seriya else None,
                "ruxsat_muddati_s": self.ruxsat_muddati_s}


def sozlama_oqi(papka: Path) -> PicoSozlama | None:
    """Profil Pico rejimidami. Yo'q bo'lsa — `None` (fayl kaliti)."""
    f = Path(papka) / SOZLAMA_FAYLI
    if not f.exists():
        return None
    try:
        d = json.loads(f.read_text(encoding="utf-8"))
        if d.get("tur") != "pico":
            return None
        return PicoSozlama(d.get("port") or "auto",
                           bytes.fromhex(d["public_key"]) if d.get("public_key") else None,
                           bytes.fromhex(d["seriya"]) if d.get("seriya") else None,
                           int(d.get("ruxsat_muddati_s") or DEFAULT_RUXSAT_S))
    except (OSError, ValueError, TypeError, KeyError) as e:
        raise P.PicoXatosi(P.X_ALOQA, f"{SOZLAMA_FAYLI} buzilgan: {e}") from e


def sozlama_yoz(papka: Path, s: PicoSozlama) -> None:
    f = Path(papka) / SOZLAMA_FAYLI
    tmp = f.with_name(f.name + ".tmp")
    tmp.write_text(json.dumps(s.lugat(), indent=2), encoding="utf-8")
    os.replace(tmp, f)


def sozlama_ochir(papka: Path) -> None:
    (Path(papka) / SOZLAMA_FAYLI).unlink(missing_ok=True)


def ulan(s: PicoSozlama, **kw) -> PicoImzolovchi:
    """Portni ochadi va SALOM qiladi. Sozlamada kalit bo'lsa — qurilma kaliti mos
    kelishi shart (boshqa Pico ulangan bo'lsa xato)."""
    pico = PicoImzolovchi(tashuvchi_och(s.port), kutilgan_pk=s.public_key,
                          ruxsat_muddati_s=s.ruxsat_muddati_s, **kw)
    try:
        sal = pico.salom()
        if s.public_key is not None and not sal.kalit_bor:
            raise P.PicoXatosi(P.X_KALIT_YOQ, "bu Pico'da kalit yo'q — profil boshqa Pico "
                                              "bilan sozlangan")
        if s.seriya is not None and sal.seriya != s.seriya:
            raise P.PicoXatosi(P.X_ALOQA, f"bu BOSHQA Pico (seriya {sal.seriya.hex()}, "
                                          f"kutilgan {s.seriya.hex()})")
    except BaseException:
        pico.yop()
        raise
    return pico
