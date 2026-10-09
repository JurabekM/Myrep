"""Kupyura isboti paketi — bitta kupyuraning partiyaga tegishliligini OFLAYN tekshirish.

Ikki ko'rinish:
- **siqiq** (QR uchun): ochiq sarlavha + Merkle isboti + ildiz. Kupyura shu ildizli
  partiyaga tegishliligini isbotlaydi.
- **to'liq** (JSON fayl): qo'shimcha ravishda partiya imzosi va imzo xabari maydonlari —
  zarbxona ochiq kaliti bilan ildizning haqiqiyligini ham tekshirish mumkin.

Maxfiy narsa YO'Q: nazorat kaliti va muhr paketga kirmaydi.
Bu zarbxonaning ichki formati (bank protokoliga kirmaydi).
"""

from __future__ import annotations

import base64
import json

from .ibtido import imzo_togri
from .kupyura import barg, sarlavha_kodi
from .merkle import isbot_ajrat, isbot_togri
from .partiya import Partiya, imzo_xabari

FORMAT = "AQ-ISBOT-1"


def _b(x: bytes) -> str:
    return base64.urlsafe_b64encode(x).decode().rstrip("=")


def _ub(s: str) -> bytes:
    return base64.urlsafe_b64decode(s + "=" * (-len(s) % 4))


def isbot_paketi(p: Partiya, i: int, toliq: bool = False) -> dict:
    if not 0 <= i < p.soni:
        raise IndexError(f"partiyada {p.soni} ta kupyura bor")
    q = p.qatorlar[i]
    d = {"v": FORMAT, "b": _b(p.partiya_id), "r": _b(p.ildiz), "n": p.soni, "i": i,
         "id": _b(q.note_id), "d": q.nominal, "o": q.egasi, "s": q.seq, "c": _b(q.cheklov_xeshi),
         "p": _b(q.isbot)}
    if toliq:
        d.update({"jami": p.jami, "qulf": p.zaxira_qulfi, "ms": p.zarb_ms,
                  "imzo": _b(p.imzo), "cheklov": p.cheklov})
    return d


def isbot_matni(d: dict) -> str:
    return json.dumps(d, separators=(",", ":"), ensure_ascii=False)


def isbot_tekshir(d: dict | str, zarbxona_pk: bytes | None = None) -> tuple[bool, str]:
    """(natija, izoh). `zarbxona_pk` berilsa va paket to'liq bo'lsa — imzo ham."""
    try:
        if isinstance(d, str):
            d = json.loads(d)
        if d.get("v") != FORMAT:
            return False, "format noma'lum"
        bid, ildiz, n, i = _ub(d["b"]), _ub(d["r"]), int(d["n"]), int(d["i"])
        kod = sarlavha_kodi(_ub(d["id"]), int(d["d"]), str(d["o"]), int(d["s"]), bid,
                            _ub(d["c"]))
        yol = isbot_ajrat(_ub(d["p"]))
    except (ValueError, KeyError, TypeError) as e:
        return False, f"paket buzilgan: {e}"
    if yol is None or not isbot_togri(barg(kod), yol, i, n, ildiz):
        return False, "Merkle isboti ildizga olib bormaydi — kupyura bu partiyaga tegishli emas"
    if zarbxona_pk is None or "imzo" not in d:
        return True, (f"kupyura #{i} (seq {d['s']}, {d['d']} so'm) ildizi {ildiz.hex()[:12]}… "
                      "bo'lgan partiyaga tegishli (imzo tekshirilmadi)")
    try:
        msg = imzo_xabari(ildiz, bid, n, int(d["jami"]), str(d["qulf"]), int(d["ms"]))
        ok = imzo_togri(zarbxona_pk, _ub(d["imzo"]), msg)
    except (ValueError, KeyError, TypeError) as e:
        return False, f"imzo maydonlari buzilgan: {e}"
    if not ok:
        return False, "partiya imzosi zarbxona kaliti bilan mos emas"
    return True, f"kupyura #{i} partiyaga tegishli VA partiya imzosi to'g'ri"


def qr_png(d: dict, yol, masshtab: int = 4) -> None:
    """Siqiq paketni QR PNG sifatida saqlaydi. `segno` kerak."""
    import segno
    segno.make(isbot_matni(d), error="l", micro=False).save(str(yol), scale=masshtab,
                                                             border=4)
