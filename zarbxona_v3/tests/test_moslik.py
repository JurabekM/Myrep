"""A1 — Rust `aetherq_mint` bilan bayt-ma-bayt solishtirish (foydalanuvchi mashinasida).

AETHER-Q muhiti topilmasa — `skip`. Bulutda bu test ishlamaydi. `aetherq_mint.mint_batch`
chaqiruvi `tools/kat_yarat.py` dagi foydalanishdan olingan; imzo o'zgarsa moslang.

    ZARBXONA_AQ_YOL=C:\\...\\aetherq_bank  python -m pytest tests/test_moslik.py -v
"""

from __future__ import annotations

import os
import sys

import pytest

if os.environ.get("ZARBXONA_AQ_YOL"):
    sys.path.insert(0, os.environ["ZARBXONA_AQ_YOL"])

ref = pytest.importorskip("aetherq_mint", reason="AETHER-Q muhiti (aetherq_mint) topilmadi")

from core.cheklov import cheklov_json, cheklov_xeshi  # noqa: E402
from core.ibtido import kalit_urugdan  # noqa: E402
from core.konstanta import XAZINA  # noqa: E402
from core.partiya import ZarbKirishi, nominallarga_bol, zarb_qil  # noqa: E402


@pytest.mark.parametrize("nominallar,cheklov", [
    ([5000], ""),
    ([5000, 1000, 1], ""),
    (nominallarga_bol(1_234_567), cheklov_json(["SEED", "FUEL"], 1_800_000_000_000)),
    (nominallarga_bol(98_765_432)[:3000], cheklov_json([], None, 250, "AQ-TAX-01")),
])
def test_rust_bilan_bayt_mos(nominallar, cheklov):
    import secrets
    pid, bk, mk = secrets.token_bytes(16), secrets.token_bytes(32), secrets.token_bytes(32)
    sert_id, vaqt, qulf, seq = secrets.token_bytes(16), 1_750_000_000_000, "AQ-RES-A1", 101
    cx = cheklov_xeshi(cheklov)
    p = zarb_qil(ZarbKirishi(nominallar, sert_id, qulf, seq, cheklov),
                 kalit_urugdan(secrets.token_bytes(32)), partiya_id=pid, partiya_kaliti=bk,
                 master=mk, zarb_ms=vaqt)
    r = ref.mint_batch(nominallar, threads=1, duty=1.0, batch_id=pid, batch_key=bk, master=mk,
                       cert_id=sert_id, minted_ms=vaqt, reserve_lock=qulf, constraints_hash=cx,
                       first_seq=seq, owner=XAZINA)
    assert r.root == p.ildiz
    assert r.signing_message == p.imzo_xabari()
    for i, (q, k) in enumerate(zip(r.rows(), p.qatorlar)):
        assert q[0] == k.note_id, i
        assert q[6] == k.muhr, i
        assert q[7] == k.isbot, i
