"""§7 — cheklov (dasturlanadigan pul): kanonik JSON va uning xeshi."""

from __future__ import annotations

import json
from collections.abc import Iterable

from .ibtido import tagged_hash
from .konstanta import L_CONSTRAINTS


class CheklovXatosi(ValueError):
    pass


def cheklov_json(toifalar: Iterable[str] = (), muddat_ms: int | None = None,
                 soliq_bps: int = 0, soliq_hisobi: str = "") -> str:
    t = sorted({x.strip().upper() for x in toifalar if x.strip()})
    if len(t) > 8:
        raise CheklovXatosi("toifalar 8 tadan ko'p bo'lmasin")
    for x in t:
        if len(x) > 32 or not x.replace("_", "").isalnum():
            raise CheklovXatosi(f"toifa noto'g'ri: {x!r} (harf, raqam, _; ≤ 32 belgi)")
    if not 0 <= int(soliq_bps) < 10_000:
        raise CheklovXatosi("soliq 0 dan 9999 bps gacha")
    soliq_hisobi = (soliq_hisobi or "").strip()
    if bool(soliq_bps) != bool(soliq_hisobi):
        raise CheklovXatosi("soliq foizi va soliq hisobi birga beriladi")
    if muddat_ms is not None and int(muddat_ms) <= 0:
        raise CheklovXatosi("muddat musbat bo'lishi kerak")
    d: dict = {}
    if t:
        d["categories"] = t
    if muddat_ms:
        d["expires_ms"] = int(muddat_ms)
    if soliq_bps:
        d["tax_bps"] = int(soliq_bps)
        d["tax_account"] = soliq_hisobi
    if not d:
        return ""
    return json.dumps(d, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def cheklov_xeshi(json_satr: str) -> bytes:
    if json_satr == "":
        return bytes(32)
    return tagged_hash(L_CONSTRAINTS, json_satr.encode("utf-8"))


def cheklov_tavsif(json_satr: str) -> str:
    """Odam o'qiydigan qisqa tavsif."""
    if not json_satr:
        return "cheklovsiz"
    try:
        d = json.loads(json_satr)
    except ValueError:
        return "noto'g'ri cheklov"
    q = []
    if d.get("categories"):
        q.append("toifalar: " + ", ".join(d["categories"]))
    if d.get("expires_ms"):
        import datetime as _dt
        t = _dt.datetime.fromtimestamp(d["expires_ms"] / 1000)
        q.append("muddat: " + t.strftime("%Y-%m-%d %H:%M"))
    if d.get("tax_bps"):
        q.append(f"soliq: {d['tax_bps'] / 100:.2f}% → {d.get('tax_account', '')}")
    return "; ".join(q)
