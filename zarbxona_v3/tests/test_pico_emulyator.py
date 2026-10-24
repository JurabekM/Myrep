"""4.x — HAQIQIY `.uf2` ni RP2040 emulyatorida (rp2040js) sinash.

Kompyuter varianti (`test_pico_ichki.py`) faqat yadroni sinaydi. Bu yerda esa Pico uchun
yig'ilgan aynan o'sha `.uf2` ishga tushiriladi va quyidagilar tekshiriladi:
- USB CDC ustidagi ikkilik protokol (CRLF tarjimasi o'chiqmi);
- alohida 32 KB stekka o'tish;
- ML-DSA-65 ning Cortex-M0+ kodi;
- GP14 tugmasi (qisqa/uzun bosish, tiqilib qolgan tugma);
- quvvat uzilishidan keyin flash'dagi yozuv.

Vaqtlar emulyatsiya qilingan 125 MHz bo'yicha hisoblanadi (taxminiy).

⚠ rp2040js flash'ga yozishni (SSI) emulyatsiya qilmaydi. Shuning uchun `flash_ish`
funksiyasi ushlanadi va sektor yozuvi JS tomonida bajariladi (`tools/pico_emulyator`).
`flash_safe_execute` va ROM'dagi flash funksiyalari bu yerda SINALMAYDI — ular faqat
haqiqiy Pico'da tekshiriladi.

Muhit o'zgaruvchilari:
- `AQ_PICO_EMU` — rp2040js papkasi (`npm ci` qilingan, runner `demo/` ga nusxalangan);
- `AQ_PICO_UF2` — `.uf2` fayl;
- `AQ_PICO_FLASH_ISH` — `flash_ish` manzili (hex).

Birortasi yo'q bo'lsa — testlar o'tkazib yuboriladi (CI'ning `pico` ishida yoqiladi).
"""

from __future__ import annotations

import os
import re
import subprocess
import threading
import time
from pathlib import Path

import pytest

from core.buyurtma import Zarbxona
from core.ibtido import imzo_togri, kalit_urugdan, ochiq_kalit
from core.partiya import imzo_xabari
from core.pico import protokol as P
from core.pico.qurilma import PicoImzolovchi
from core.surat import Surat
from core.tekshiruv import jurnalni_tekshir
from core.zanjir import bosh_xabari

EMU = os.environ.get("AQ_PICO_EMU")
UF2 = os.environ.get("AQ_PICO_UF2")
FLASH_ISH = os.environ.get("AQ_PICO_FLASH_ISH", "")
pytestmark = pytest.mark.skipif(
    not (EMU and UF2 and FLASH_ISH and Path(UF2).exists()),
    reason="AQ_PICO_EMU / AQ_PICO_UF2 / AQ_PICO_FLASH_ISH berilmagan")

PIN = "emu-pin-123"
URUG = bytes(range(1, 33))
HOZIR = 1_800_000_000_000
KUTISH = 1800            # emulyator haqiqiy Pico'dan ~5 marta sekin


class Emulyator:
    nomi = "emulyator"

    def __init__(self, flash: Path, tugma: str = ""):
        self.log = flash.with_suffix(".log")
        env = {**os.environ, "EMU_FLASH": str(flash), "EMU_TUGMA": tugma,
               "EMU_FLASH_ISH": FLASH_ISH}
        self._err = open(self.log, "ab")
        self.p = subprocess.Popen([str(Path(EMU) / "node_modules/.bin/tsx"),
                                   "demo/pico-hsm-run.ts", str(Path(UF2).resolve())],
                                  cwd=EMU, stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                                  stderr=self._err, env=env)
        self._b = bytearray()
        self._shart = threading.Condition()
        threading.Thread(target=self._oqi, daemon=True).start()

    def _oqi(self) -> None:
        while True:
            d = self.p.stdout.read1(65536)
            with self._shart:
                if not d:
                    self._shart.notify_all()
                    return
                self._b += d
                self._shart.notify_all()

    def yoz(self, b: bytes) -> None:
        self.p.stdin.write(b)
        self.p.stdin.flush()

    def oqi(self, kutish: float) -> bytes:
        oxiri = time.monotonic() + kutish
        with self._shart:
            while not self._b:
                q = oxiri - time.monotonic()
                if q <= 0 or self.p.poll() is not None:
                    return b""
                self._shart.wait(q)
            b = bytes(self._b)
            self._b.clear()
            return b

    def tozala(self) -> None:
        with self._shart:
            self._b.clear()

    def yop(self) -> None:
        if not self.p.stdin.closed:
            self.p.stdin.close()
        self.p.wait(120)
        self._err.close()

    def vaqtlar(self) -> list[tuple[float, str]]:
        """(emulyatsiya soniyasi, hodisa) — stderr jurnalidan."""
        return [(float(m[1]), m[2]) for m in
                re.finditer(r"\[([\d.]+) s\] (.+)", self.log.read_text(encoding="utf-8"))]


def test_uf2_toliq_hayot_sikli(tmp_path, kalitlar):
    flash = tmp_path / "flash.bin"
    xabarlar: list = []
    e = Emulyator(flash, tugma="ha,rad,ha")
    try:
        p = PicoImzolovchi(e, oddiy_kutish=KUTISH, kutish_xabari=xabarlar.append)
        s = p.salom()
        assert s.versiya == "zarbxona-pico 1.0" and not s.kalit_bor
        pk = p.kalit_import(PIN, URUG)
        assert pk == ochiq_kalit(kalit_urugdan(URUG))          # Cortex-M0+ dagi keygen
        assert xabarlar[:2] == ["Mavjud kalitni IMPORT qilish", None]
        with pytest.raises(P.PicoXatosi) as x:
            p.ruxsat("B-EMU", 1000)                             # 2,5 s bosib turildi
        assert x.value.kod == P.X_RAD
        p.ruxsat("B-EMU", 1000)                                 # rad'dan keyin qayta bosish
        a = (bytes(32), bytes(16), 3, 700, "AQ-RES-EMU", HOZIR)
        assert imzo_togri(pk, p.partiya_imzosi(*a), imzo_xabari(*a))
        x32 = b"\x07" * 32
        assert imzo_togri(pk, p.bosh_imzosi(1, x32), bosh_xabari(1, x32))
        h = p.holat()
        assert h.ruxsat_faol and h.byudjet == 300 and h.imzolar == 2
    finally:
        e.yop()
    vaqt = e.vaqtlar()
    assert sum(1 for _, h in vaqt if h == "flash yozildi") == 1

    e = Emulyator(flash)                                          # quvvat uzildi
    try:
        p = PicoImzolovchi(e, oddiy_kutish=KUTISH, kutilgan_pk=pk)
        s = p.salom()
        assert s.kalit_bor and not s.ochiq and s.import_qilingan
        with pytest.raises(P.PicoXatosi) as x:
            p.pin_och("xato-pin-00")
        assert x.value.kod == P.X_PIN and x.value.qoshimcha == [b"\x04"]
        assert p.pin_och(PIN) == pk
        assert p.salom().qolgan_urinish == P.MAX_URINISH
    finally:
        e.yop()
    for t, hodisa in e.vaqtlar():
        print(f"  {t:8.3f} s  {hodisa}")


def test_uf2_bilan_zarbxona_buyurtmasi(tmp_path, sertifikat):
    e = Emulyator(tmp_path / "flash.bin")
    try:
        p = PicoImzolovchi(e, oddiy_kutish=KUTISH)
        p.kalit_import(PIN, URUG)
        z = Zarbxona(tmp_path / "profil", p, soat_ms=lambda: HOZIR)
        try:
            sertifikat.yoz(tmp_path / "s.aqcert")
            z.sertifikat_import(tmp_path / "s.aqcert")
            b = z.buyurtma_yarat(5_000 * 3 + 7, "AQ-RES-EMU", "", Surat(rejim="cheklovsiz"),
                                 partiya_hajmi=3)
            r = z.buyurtmani_bajar(b.buyurtma_id)
            assert r.holat == "tugadi", r.xabar
            assert len(r.partiyalar) == 2
            assert jurnalni_tekshir(z.jurnal, z.partiya_papka, z.pk, z.sertifikat).ok
        finally:
            z.yop()
    finally:
        e.yop()
