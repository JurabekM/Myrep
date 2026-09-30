"""GUI'siz (headless) rejim — server yoki Raspberry Pi'da ekransiz, soatlab zarb uchun.
Qt import qilinmaydi.

    python run.py holat      [--papka P]
    python run.py zarb       --summa 1234567 --qulf AQ-RES-1 [--surat davomiylik:30] ...
    python run.py davom      --buyurtma ID
    python run.py tasdiqla   --buyurtma ID
    python run.py buyurtmalar
    python run.py tekshir

Parol: `ZARBXONA_PAROL` muhit o'zgaruvchisi yoki so'raladi (getpass). Tasdiqchi paroli:
`ZARBXONA_TASDIQCHI_PAROL` yoki so'raladi. Ctrl+C — TO'XTATISH: joriy partiya
yozilmaydi, buyurtma keyin `davom` bilan davom etadi.

Chiqish kodlari: 0 — muvaffaqiyat/toza; 1 — xato yoki tekshiruvda muammo;
2 — noto'g'ri buyruq; 3 — to'xtatildi yoki ikkinchi tasdiq kutilmoqda.
"""

from __future__ import annotations

import argparse
import getpass
import os
import signal
import sys
import threading
import time
from pathlib import Path

from app.yollar import dastur_papkasi
from core.buyurtma import BandXatosi, BuyurtmaXatosi, Zarbxona
from core.cheklov import CheklovXatosi, cheklov_json
from core.ombor import OmborXatosi, ombor_och
from core.surat import Surat, tezlik_matni, vaqt_matni
from core.tasdiq import TasdiqXatosi
from core.tekshiruv import jurnalni_tekshir

BUYRUQLAR = ("holat", "zarb", "davom", "tasdiqla", "buyurtmalar", "tekshir")
ILDIZ = dastur_papkasi()


def _chiq(s: str = "") -> None:
    print(s, flush=True)


def surat_tahlil(s: str, byudjet: float, sovutish: str) -> Surat:
    """`tezlik:8` · `davomiylik:30` (daqiqa) · `cheklovsiz`; sovutish `N:X`."""
    rejim, _, qiymat = s.partition(":")
    sur = Surat(rejim=rejim, byudjet=byudjet)
    if rejim == "tezlik":
        sur.tezlik = float(qiymat or 8)
    elif rejim == "davomiylik":
        sur.davomiylik = float(qiymat or 10)
    elif rejim != "cheklovsiz":
        raise ValueError(f"noma'lum sur'at: {s}")
    n, _, x = sovutish.partition(":")
    sur.N, sur.X = int(n or 0), float(x or 0)
    sur.tekshir()
    return sur


def interaktiv() -> bool:
    """Haqiqiy terminalmi. stdin YOLG'IZ yetmaydi: Windows'da NUL qurilmasi (masalan
    subprocess DEVNULL) isatty() da True beradi va getpass konsolni kutib osilib qoladi.
    Chiqish ushlangan (pipe/fayl) bo'lsa — bu interaktiv sessiya emas."""
    try:
        return sys.stdin.isatty() and sys.stdout.isatty()
    except (AttributeError, ValueError):
        return False


def _parol(env: str, savol: str) -> str | None:
    p = os.environ.get(env)
    if p:
        return p
    if not interaktiv():
        return None
    return getpass.getpass(savol)


def _och(papka: Path) -> Zarbxona:
    kalit = papka / "kalit.json"
    if not kalit.exists():
        raise OmborXatosi(f"kalit yo'q: {kalit} — avval GUI bilan kalit yarating")
    parol = _parol("ZARBXONA_PAROL", "zarbxona paroli: ")
    if parol is None:
        raise OmborXatosi("parol berilmadi (ZARBXONA_PAROL yoki interaktiv terminal)")
    z = Zarbxona(papka, ombor_och(kalit, parol))
    t = z.tiklash()
    if not t.bosh:
        _chiq("tiklash: " + t.matn().replace("\n", "\n         "))
    for o in z.ogohlantirishlar():
        _chiq(f"⚠ {o}")
    return z


# --- buyruqlar ---------------------------------------------------------------------------


def holat(z: Zarbxona, _a) -> int:
    s = z.sertifikat
    if s is None:
        _chiq("sertifikat: YO'Q")
    else:
        m = s.muammo(z.pk, z.soat_ms())
        _chiq(f"sertifikat: {s.label} · {m or 'yaroqli'}")
        _chiq(f"limit {s.limit_amount:,} · chiqarilgan {z.chiqarilgan():,} · "
              f"qolgan {z.qolgan_limit():,}".replace(",", " "))
    st = z.jurnal.jami_statistika()
    _chiq(f"partiyalar {st['partiya']} · kupyuralar {st['kupyura']} · "
          f"topshirilmagan {st['topshirilmagan']}")
    ch = z.tasdiq.chegara()
    _chiq("ikki kishilik tasdiq: " + ("o'chiq" if ch is None else f"chegara {ch:,}"
                                      .replace(",", " ")))
    return 0


def buyurtmalar(z: Zarbxona, _a) -> int:
    for b in z.jurnal.buyurtmalar():
        _chiq(f"{b.buyurtma_id}  {b.holat:<7} {b.summa:>14,}  {b.bajarilgan_kupyura}/"
              f"{b.kupyura_soni}  tasdiq: {z.tasdiq.holat(b)}".replace(",", " "))
    return 0


def tekshir(z: Zarbxona, _a) -> int:
    h = jurnalni_tekshir(z.jurnal, z.partiya_papka, z.pk, z.sertifikat)
    _chiq(h.matn())
    return 0 if h.ok else 1


def tasdiqla(z: Zarbxona, a) -> int:
    p = _parol("ZARBXONA_TASDIQCHI_PAROL", "TASDIQCHI paroli (ikkinchi operator): ")
    if p is None:
        _chiq("tasdiqchi paroli berilmadi")
        return 3
    try:
        _chiq(f"tasdiqlandi · tasdiqchi {z.tasdiq.tasdiqla(a.buyurtma, p)}")
    except TasdiqXatosi as e:
        _chiq(f"XATO: {e}")
        return 1
    return 0


class _Monitor:
    """Konsol monitori: har ~2 s da bitta holat satri (tez rejimda ham toshqin yo'q)."""

    def __init__(self):
        self.t0 = time.monotonic()
        self.oxirgi = 0.0
        self.n = 0
        self.asos = 0
        self.jami = 0

    def kuzatuv(self, q, i, soni) -> None:
        self.n += 1
        hozir = time.monotonic()
        if hozir - self.oxirgi >= 2 or i + 1 == soni:
            self.oxirgi = hozir
            tz = self.n / max(1e-9, hozir - self.t0)
            qolgan = (self.jami - self.asos - i - 1) / tz if tz else 0
            _chiq(f"  #{q.seq} · {self.asos + i + 1}/{self.jami} · {tezlik_matni(tz)} · "
                  f"qolgan ~{vaqt_matni(qolgan)}")

    def hodisa(self, tur, d) -> None:
        if tur == "partiya_boshlandi":
            self.asos, self.jami = d["bajarilgan"], d["jami_kupyura"]
        elif tur == "partiya_yopildi":
            p = d["partiya"]
            _chiq(f"partiya yopildi · {d['fayl']} · ildiz {p.ildiz.hex()[:12]}… · "
                  f"{p.soni} kupyura · {p.jami:,} so'm".replace(",", " "))
        elif tur == "tanaffus":
            _chiq(f"  — sovutish ({d} s) —")


def _bajar(z: Zarbxona, bid: str, surat: Surat | None) -> int:
    b = z.jurnal.buyurtma(bid)
    if z.tasdiq.holat(b) == "kutilmoqda":
        _chiq("ikkinchi operator tasdig'i kerak")
        if tasdiqla(z, argparse.Namespace(buyurtma=bid)) != 0:
            _chiq(f"buyurtma saqlandi: {bid} — `tasdiqla --buyurtma {bid}`, keyin `davom`")
            return 3
    toxta = threading.Event()

    def sigint(_s, _f):
        _chiq("\nTO'XTATILMOQDA… joriy partiya yozilmaydi")
        toxta.set()
    eski = signal.signal(signal.SIGINT, sigint)
    m = _Monitor()
    try:
        r = z.buyurtmani_bajar(bid, surat=surat, kuzatuv=m.kuzatuv, hodisa=m.hodisa,
                               bekormi=toxta.is_set,
                               tanaffus=lambda x: m.hodisa("tanaffus", x))
    finally:
        signal.signal(signal.SIGINT, eski)
    _chiq(f"{r.holat.upper()}: {r.xabar} · {len(r.partiyalar)} partiya yozildi")
    if r.holat == "tugadi":
        return 0
    if r.hisobot is not None:
        _chiq(r.hisobot.matn())
        return 1
    return 3 if r.holat in ("toxtatildi", "pauza") else 1


def zarb(z: Zarbxona, a) -> int:
    try:
        sur = surat_tahlil(a.surat, a.byudjet, a.sovutish)
        cj = cheklov_json([x for x in a.toifalar.split(",") if x], a.muddat_ms, a.soliq_bps,
                          a.soliq_hisobi)
        b = z.buyurtma_yarat(a.summa, a.qulf, cj, sur, a.hajm)
    except (ValueError, CheklovXatosi, BuyurtmaXatosi) as e:
        _chiq(f"XATO: {e}")
        return 1
    _chiq(f"buyurtma {b.buyurtma_id}: {b.summa:,} so'm → {b.kupyura_soni} kupyura · sur'at "
          f"{sur.rejim}".replace(",", " "))
    return _bajar(z, b.buyurtma_id, sur)


def davom(z: Zarbxona, a) -> int:
    b = z.jurnal.buyurtma(a.buyurtma)
    if b is None:
        _chiq("buyurtma topilmadi")
        return 1
    sur = surat_tahlil(a.surat, a.byudjet, a.sovutish) if a.surat else None
    return _bajar(z, b.buyurtma_id, sur)


def argumentlar(argv) -> argparse.Namespace:
    a = argparse.ArgumentParser(prog="zarbxona", description="Zarbxona v3 — GUI'siz rejim")
    sub = a.add_subparsers(dest="buyruq", required=True)
    umumiy = argparse.ArgumentParser(add_help=False)
    umumiy.add_argument("--papka", type=Path, default=ILDIZ / "data")
    surat = argparse.ArgumentParser(add_help=False)
    surat.add_argument("--surat", default="tezlik:8",
                       help="tezlik:K (kupyura/s) · davomiylik:D (daqiqa) · cheklovsiz")
    surat.add_argument("--byudjet", type=float, default=0.25, help="CPU ulushi, 0 < b ≤ 1")
    surat.add_argument("--sovutish", default="25:2", help="N:X — har N kupyurada X s")
    for nom in ("holat", "buyurtmalar", "tekshir"):
        sub.add_parser(nom, parents=[umumiy])
    z = sub.add_parser("zarb", parents=[umumiy, surat])
    z.add_argument("--summa", type=int, required=True)
    z.add_argument("--qulf", required=True, help="bank bergan zaxira qulfi")
    z.add_argument("--hajm", type=int, default=500, help="partiya hajmi")
    z.add_argument("--toifalar", default="")
    z.add_argument("--muddat-ms", dest="muddat_ms", type=int, default=None)
    z.add_argument("--soliq-bps", dest="soliq_bps", type=int, default=0)
    z.add_argument("--soliq-hisobi", dest="soliq_hisobi", default="")
    d = sub.add_parser("davom", parents=[umumiy, surat])
    d.add_argument("--buyurtma", required=True)
    d.set_defaults(surat=None)
    t = sub.add_parser("tasdiqla", parents=[umumiy])
    t.add_argument("--buyurtma", required=True)
    return a.parse_args(argv)


def main(argv) -> int:
    a = argumentlar(argv)
    try:
        z = _och(a.papka)
    except (OmborXatosi, BandXatosi) as e:
        _chiq(f"XATO: {e}")
        return 1
    try:
        return {"holat": holat, "zarb": zarb, "davom": davom, "tasdiqla": tasdiqla,
                "buyurtmalar": buyurtmalar, "tekshir": tekshir}[a.buyruq](z, a)
    finally:
        z.yop()
