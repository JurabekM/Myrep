"""Unumdorlik byudjetlari (10-faza, ADR-0014): to'liq tekshiruvli push (audit zanjiri, imzo) va pull.

Byudjetlar CI uchun zaxira bilan; raqamlar `-s` bilan chop etiladi.
"""

from __future__ import annotations

import time

from tests.support.field import rows
from tests.test_sync import Env, env, graph  # noqa: F401 — fixture


async def test_push_and_pull_budget(env: Env) -> None:  # noqa: F811
    g = await graph(env)
    f = env.field
    ops = []
    for i in range(240):  # 240 o'lchov + 240 audit hodisasi = 480 op (bitta paket)
        ops += f.measurement(g["ses"]["id"], g["node"]["id"], g["inst"]["id"], zs=0.3 + i / 1000)
    t0 = time.perf_counter()
    await env.ok(ops)
    push = time.perf_counter() - t0
    t1 = time.perf_counter()
    total = len(await env.all_rows("measurement"))
    pull = time.perf_counter() - t1
    print(f"push {len(ops)} op: {push * 1000:.0f} ms; pull (barcha sahifalar): {pull * 1000:.0f} ms")
    assert total == 240
    assert len(rows(ops, "audit_event")) == 240
    assert push < 10
    assert pull < 5
