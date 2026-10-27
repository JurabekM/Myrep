"""`/sync/push` va `/sync/pull`: idempotentlik, LWW, append-only, audit zanjiri, protokol, tashkilot ajratilishi."""

from __future__ import annotations

import copy
import json
from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

import pytest

from tests.support.api import Api, User
from tests.support.field import NORMS, Field, fake_pdf, rows
from zanjir_server.crypto.hash_chain import payload_hash


@dataclass
class Env:
    api: Api
    users: dict[str, User]
    field: Field

    async def push(self, ops: list[dict[str, Any]], user: User | None = None) -> Any:
        r = await self.api.c.post("/sync/push", json={"ops": ops}, headers=(user or self.users["LEAD"]).headers)
        return r

    async def ok(self, ops: list[dict[str, Any]], user: User | None = None) -> dict[str, str]:
        r = await self.push(ops, user)
        assert r.status_code == 200, r.text
        return {x["client_op_id"]: x["status"] for x in r.json()["results"]}

    async def rejected(self, ops: list[dict[str, Any]], reason: str, user: User | None = None) -> None:
        r = await self.push(ops, user)
        assert r.status_code == 422, r.text
        assert r.json()["detail"]["reason"] == reason, r.text

    async def pull(self, since: int = 0, user: User | None = None, limit: int | None = None) -> Any:
        q = f"/sync/pull?since={since}" + (f"&limit={limit}" if limit else "")
        r = await self.api.c.get(q, headers=(user or self.users["VIEWER"]).headers)
        assert r.status_code == 200, r.text
        return r.json()

    async def all_rows(self, table: str) -> list[dict[str, Any]]:
        out: list[dict[str, Any]] = []
        since = 0
        while True:
            page = await self.pull(since)
            out += [c["row"] for c in page["changes"] if c["table"] == table]
            since = page["server_rev"]
            if not page["has_more"]:
                return out


@pytest.fixture
async def env(api: Api) -> Env:
    users = await api.org()
    lead = users["LEAD"]
    field = Field(lead.org_id, lead.id, device_id="00000000-0000-7000-8000-" + lead.id[-12:])
    await api.device(lead, field.public_key, field.device_id)
    return Env(api, users, field)


async def graph(e: Env, reviewed: bool = True, verified_until: str | None = None) -> dict[str, Any]:
    """Normalar to'plami, obyekt, tugun, asbob, yopilgan sessiya — push qilingan."""
    f = e.field
    site = f.site()
    node = f.node(site["row"]["id"])
    inst = f.instrument(verified_until) if verified_until else f.instrument()
    ses = f.session(site["row"]["id"])
    await e.ok([f.norm_set(reviewed), site, node, inst, ses])
    return {"site": site["row"], "node": node["row"], "inst": inst["row"], "ses": ses["row"]}


async def test_push_pull_roundtrip_and_idempotency(env: Env) -> None:
    g = await graph(env)
    f = env.field
    m_ops = f.measurement(g["ses"]["id"], g["node"]["id"], g["inst"]["id"])
    statuses = await env.ok(m_ops)
    assert set(statuses.values()) == {"applied"}
    # Xuddi shu paket qayta — takror (client_op_id).
    assert set((await env.ok(m_ops)).values()) == {"duplicate"}
    # Yangi op ID, bir xil qatorlar — append-only takror.
    again = [{**o, "client_op_id": o["client_op_id"] + "-r"} for o in m_ops]
    assert set((await env.ok(again)).values()) == {"duplicate"}

    page = await env.pull()
    tables = [c["table"] for c in page["changes"]]
    assert {
        "organization",
        "app_user",
        "device",
        "site",
        "node",
        "instrument",
        "measurement_session",
        "measurement",
        "audit_event",
    } <= set(tables)
    revs = [c["server_rev"] for c in page["changes"]]
    assert revs == sorted(revs) and len(set(revs)) == len(revs)
    users = [c["row"] for c in page["changes"] if c["table"] == "app_user"]
    assert users and all("password_hash" not in u and "phone" not in u for u in users)
    m = next(c["row"] for c in page["changes"] if c["table"] == "measurement")
    assert m == rows(m_ops, "measurement")[0]
    assert (await env.pull(since=page["server_rev"]))["changes"] == []


async def test_pull_pagination(env: Env) -> None:
    await graph(env)
    seen: list[int] = []
    since = 0
    while True:
        page = await env.pull(since, limit=3)
        assert len(page["changes"]) <= 3
        seen += [c["server_rev"] for c in page["changes"]]
        since = page["server_rev"]
        if not page["has_more"]:
            break
    assert seen == sorted(seen) and len(seen) == len(set(seen)) and len(seen) >= 8


async def test_last_writer_wins(env: Env) -> None:
    f = env.field
    site = f.site()
    await env.ok([site])
    newer = copy.deepcopy(site)
    newer["client_op_id"] += "-2"
    newer["row"].update(name="Yangi nom", updated_at="2026-10-27T08:05:00.000Z", rev=2)
    older = copy.deepcopy(site)
    older["client_op_id"] += "-3"
    older["row"].update(name="Eski nom", updated_at="2026-10-26T00:00:00.000Z", rev=5)
    st = await env.ok([newer])
    assert set(st.values()) == {"applied"}
    st = await env.ok([older])
    assert set(st.values()) == {"stale"}
    assert (await env.all_rows("site"))[0]["name"] == "Yangi nom"


async def test_measurement_requires_signed_audit_event(env: Env) -> None:
    g = await graph(env)
    f = env.field
    ev, m = f.measurement(g["ses"]["id"], g["node"]["id"], g["inst"]["id"])
    await env.rejected([m], "missing_audit_event")
    forged = copy.deepcopy(m)
    forged["row"]["verdict"] = "FAIL"  # hodisadagi hash boshqa natijaga tegishli
    await env.rejected([ev, forged], "missing_audit_event")
    # Hech narsa saqlanmadi (paket to'liq rad etildi) — hodisa ham.
    assert await env.all_rows("audit_event") == []
    await env.ok([ev, m])
    changed = copy.deepcopy(m)
    changed["client_op_id"] += "-x"
    changed["row"]["values"] = {"pair": "L1-PE", "zs_ohm": 0.1}
    await env.rejected([changed], "append_only_conflict")


@pytest.mark.parametrize(
    ("mutate", "reason"),
    [
        (lambda e: e["row"].update(seq=e["row"]["seq"] + 1), "audit_chain:seq_gap"),
        (lambda e: e["row"].update(prev_hash="f" * 64), "audit_chain:prev_hash_mismatch"),
        (lambda e: e["row"].update(payload_hash="e" * 64), "audit_chain:event_hash_mismatch"),
        (lambda e: e["row"].update(device_sig="00" * 64), "audit_chain:bad_signature"),
        (lambda e: e["row"].update(event_at="2026-10-27 08:00"), "audit_chain:invalid_format"),
    ],
)
async def test_broken_audit_chain_rejects_whole_batch(
    env: Env, mutate: Callable[[dict[str, Any]], None], reason: str
) -> None:
    f = env.field
    first = f.event("SITE_CREATED", "s", {"a": 1})
    second = f.event("SITE_CREATED", "s", {"a": 2})
    site = f.site()
    mutate(second)
    await env.rejected([first, second, site], reason)
    assert await env.all_rows("audit_event") == []
    assert await env.all_rows("site") == []


async def test_audit_chain_continues_across_pushes(env: Env) -> None:
    f = env.field
    e1, e2, e3 = (f.event("X", None, {"i": i}) for i in range(3))
    await env.ok([e1])
    await env.ok([e3, e2])  # tartib muhim emas — seq bo'yicha saralanadi
    await env.ok([e1, e2])  # takror
    conflict = copy.deepcopy(e2)
    conflict["client_op_id"] += "-c"
    conflict["row"]["id"] = "11111111-1111-4111-8111-111111111111"
    conflict["row"]["event_hash"] = "a" * 64
    await env.rejected([conflict], "audit_conflict")
    assert [r["seq"] for r in await env.all_rows("audit_event")] == [1, 2, 3]


async def test_device_rules(env: Env) -> None:
    f = env.field
    eng = env.users["ENGINEER"]
    # Boshqa foydalanuvchining qurilmasi hodisalarini yuborib bo'lmaydi.
    await env.rejected([f.event("X", None, {})], "device_not_owned", user=eng)
    # Noma'lum qurilma.
    stranger = Field(f.org_id, f.user_id, "22222222-2222-4222-8222-222222222222", seed=9)
    await env.rejected([stranger.event("X", None, {})], "unknown_device")
    # Hodisa boshqa aktor nomidan.
    ev = f.event("X", None, {})
    ev["row"]["actor_id"] = eng.id
    await env.rejected([ev], "actor_mismatch")
    # Bekor qilingan qurilma.
    r = await env.api.c.post(f"/devices/{f.device_id}/revoke", headers=env.users["ADMIN"].headers)
    assert r.status_code == 200
    f.seq, f.prev = 0, "0" * 64
    await env.rejected([f.event("X", None, {})], "device_revoked")


async def test_editor_only_events_and_tables(env: Env, api: Api) -> None:
    eng = env.users["ENGINEER"]
    ef = Field(eng.org_id, eng.id, "33333333-3333-4333-8333-333333333333", seed=11)
    await api.device(eng, ef.public_key, ef.device_id)
    await env.rejected([ef.event("PROTOCOL_REVOKED", "p", {"reason": "x"})], "forbidden_role", user=eng)
    ef.restore((0, "0" * 64))
    await env.rejected([ef.event("PLAN_APPROVED", "p", {"id": "p"})], "forbidden_role", user=eng)
    ef.restore((0, "0" * 64))
    setting = ef.op("org_setting", ef.base(k_corr=0.8, margin_pct=5.0, active_norm_set_version=None))
    await env.rejected([setting], "forbidden_role", user=eng)
    r = await env.push([ef.site()], user=env.users["VIEWER"])
    assert r.status_code == 403
    user_row = ef.op("app_user", ef.base(full_name="x", role="ADMIN", safety_group=None, deleted=False))
    await env.rejected([user_row], "table_not_pushable")


async def test_wire_validation_and_org_boundary(env: Env, api: Api) -> None:
    f = env.field
    bad = f.site()
    bad["row"]["u0_volts"] = "220"
    await env.rejected([bad], "type:site.u0_volts")
    extra = f.site()
    extra["row"]["secret"] = 1
    await env.rejected([extra], "unknown_column:site.secret")
    missing = f.site()
    del missing["row"]["name"]
    await env.rejected([missing], "missing:site.name")
    other = await api.register("LEAD")
    foreign = f.site()
    foreign["row"]["org_id"] = other.org_id
    await env.rejected([foreign], "wrong_org")
    dup = f.site()
    await env.rejected([dup, {**dup}], "duplicate_op_id")
    # Boshqa tashkilotdagi mavjud ID — RLS ko'rsatmaydi, PK to'qnashuvi — cheklov xatosi.
    site = f.site()
    await env.ok([site])
    of = Field(other.org_id, other.id, "44444444-4444-4444-8444-444444444444")
    clash = of.site()
    clash["row"]["id"] = site["row"]["id"]
    r = await api.c.post("/sync/push", json={"ops": [clash]}, headers=other.headers)
    assert r.json()["detail"]["reason"] == "constraint_violation"
    # Boshqa tashkilot pull'da ko'rmaydi.
    page = (await api.c.get("/sync/pull", headers=other.headers)).json()
    assert all(c["row"].get("org_id", c["row"]["id"]) == other.org_id for c in page["changes"])
    # Mavjud bo'lmagan ota yozuv (kechiktirilgan FK) — paket rad.
    orphan = f.node("55555555-5555-4555-8555-555555555555")
    await env.rejected([orphan], "constraint_violation")


async def test_organization_and_settings_by_lead(env: Env) -> None:
    f = env.field
    org = (await env.all_rows("organization"))[0]
    upd = {
        **org,
        "license_no": "EL-42",
        "license_valid_until": "2027-12-31T00:00:00.000Z",
        "updated_at": "2026-10-27T08:05:00.000Z",
        "rev": org["rev"] + 1,
        "name": "Lab 2",
    }
    lab = {"name": "Lab 2", "license_no": "EL-42", "license_valid_until": "2027-12-31T00:00:00.000Z"}
    # Rekvizitlar o'zgarishi imzolangan LAB_UPDATED hodisasisiz yoki boshqa qiymatli hodisa bilan — rad (ADR-0014).
    await env.rejected([f.op("organization", upd)], "missing_audit_event")
    state = f.snapshot()
    await env.rejected(
        [f.event("LAB_UPDATED", org["id"], {**lab, "name": "Boshqa"}), f.op("organization", upd)],
        "missing_audit_event",
    )
    f.restore(state)
    await env.ok([f.event("LAB_UPDATED", org["id"], lab), f.op("organization", upd)])
    after = (await env.all_rows("organization"))[0]
    assert (after["license_no"], after["name"]) == ("EL-42", "Lab 2")
    setting = f.op("org_setting", f.base(k_corr=0.8, margin_pct=5.0, active_norm_set_version="0.1.1"))
    await env.rejected([setting], "missing_audit_event")
    changed = {"k_corr": 0.8, "margin_pct": 5.0, "active_norm_set_version": "0.1.1"}
    await env.ok([f.event("SETTINGS_CHANGED", org["id"], changed), setting])
    bad = f.op("org_setting", f.base(k_corr=1.5, margin_pct=5.0, active_norm_set_version=None))
    ev = f.event("SETTINGS_CHANGED", org["id"], {"k_corr": 1.5, "margin_pct": 5.0, "active_norm_set_version": None})
    await env.rejected([ev, bad], "constraint_violation")


async def test_session_cannot_reopen(env: Env) -> None:
    g = await graph(env)
    f = env.field
    reopen = f.op(
        "measurement_session", {**g["ses"], "closed_at": None, "updated_at": "2026-10-27T08:05:00.000Z", "rev": 2}
    )
    await env.rejected([reopen], "session_reopen")


STEPS = [{"order": 1, "kind": "SWITCH_OFF"}, {"order": 2, "kind": "VERIFY_NO_VOLTAGE"}]


def plan_row(f: Field, g: dict[str, Any], **kw: Any) -> dict[str, Any]:
    return (
        f.base(
            site_id=g["site"]["id"],
            target_node_ids=[g["node"]["id"]],
            solver_version="1",
            graph_snapshot_hash="a" * 64,
            steps=STEPS,
            warnings=[],
            status="DRAFT",
            approved_by=None,
            deleted=False,
        )
        | kw
    )


def bump(row: dict[str, Any], **kw: Any) -> dict[str, Any]:
    """Keyingi LWW versiya (yangiroq `updated_at`, `rev` + 1)."""
    minute = 1 + row["rev"]
    return {**row, "updated_at": f"2026-10-27T08:0{minute}:00.000Z", "rev": row["rev"] + 1, **kw}


async def engineer_field(env: Env) -> tuple[User, Field]:
    eng = env.users["ENGINEER"]
    ef = Field(eng.org_id, eng.id, "66666666-6666-4666-8666-" + eng.id[-12:], seed=13)
    await env.api.device(eng, ef.public_key, ef.device_id)
    return eng, ef


async def test_plan_approval_cannot_be_forged_by_engineer(env: Env) -> None:
    """H1 (ADR-0014): tasdiq — faqat LEAD/ADMIN ning aynan shu qadamlarga imzolangan PLAN_APPROVED hodisasi bilan."""
    from zanjir_server.sync.service import plan_approval_payload

    g = await graph(env)
    eng, ef = await engineer_field(env)
    lead = env.users["LEAD"]
    draft = plan_row(ef, g)
    await env.ok([ef.op("isolation_plan", draft)], user=eng)
    # O'zini tasdiqlovchi deb ko'rsatish, LEAD nomidan tasdiq (hodisasiz), o'zi PLAN_APPROVED yozish — rad.
    await env.rejected(
        [ef.op("isolation_plan", bump(draft, status="APPROVED", approved_by=eng.id))], "approval_requires_lead", eng
    )
    forged = bump(draft, status="APPROVED", approved_by=lead.id)
    await env.rejected([ef.op("isolation_plan", forged)], "missing_audit_event", eng)
    state = ef.snapshot()
    await env.rejected(
        [ef.event("PLAN_APPROVED", draft["id"], plan_approval_payload(forged)), ef.op("isolation_plan", forged)],
        "forbidden_role",
        eng,
    )
    ef.restore(state)
    # Yangi qator darhol APPROVED/EXECUTED holatida ham xuddi shunday.
    fresh = plan_row(ef, g, status="EXECUTED", approved_by=lead.id)
    await env.rejected([ef.op("isolation_plan", fresh)], "missing_audit_event", eng)

    # LEAD boshqa qadamlarga tasdiq bergan bo'lsa — mos emas.
    f = env.field
    other = plan_approval_payload({**forged, "steps": STEPS[:1]})
    state = f.snapshot()
    await env.rejected(
        [f.event("PLAN_APPROVED", draft["id"], other), f.op("isolation_plan", forged)], "missing_audit_event"
    )
    f.restore(state)
    st = await env.ok(
        [f.event("PLAN_APPROVED", draft["id"], plan_approval_payload(forged)), f.op("isolation_plan", forged)]
    )
    assert set(st.values()) == {"applied"}


async def test_plan_content_frozen_and_terminal_states_win(env: Env) -> None:
    from zanjir_server.sync.service import plan_approval_payload

    g = await graph(env)
    eng, ef = await engineer_field(env)
    f = env.field
    lead = env.users["LEAD"]
    approved = plan_row(f, g, status="APPROVED", approved_by=lead.id)
    await env.ok(
        [f.event("PLAN_APPROVED", approved["id"], plan_approval_payload(approved)), f.op("isolation_plan", approved)]
    )
    # Tasdiqdan keyin qadamlar, maqsad yoki tasdiqlovchi almashtirilmaydi.
    changes: list[dict[str, Any]] = [{"steps": STEPS[:1]}, {"target_node_ids": []}, {"approved_by": eng.id}]
    for change in [*changes, {"deleted": True}]:
        await env.rejected([ef.op("isolation_plan", bump(approved, **change))], "plan_immutable", eng)
    # Bajarish — barcha qadamlar va PLAN_EXECUTED hodisasi bilan.
    executed = bump(approved, status="EXECUTED")
    state = ef.snapshot()
    await env.rejected(
        [
            ef.event("PLAN_STEP_DONE", f"{approved['id']}#1", {}),
            ef.event("PLAN_EXECUTED", approved["id"], {}),
            ef.op("isolation_plan", executed),
        ],
        "plan_steps_incomplete",
        eng,
    )
    ef.restore(state)
    events = [ef.event("PLAN_STEP_DONE", f"{approved['id']}#{n}", {"order": n}) for n in (1, 2)]
    await env.ok(
        [*events, ef.event("PLAN_EXECUTED", approved["id"], {"id": approved["id"]}), ef.op("isolation_plan", executed)],
        eng,
    )
    # Yakuniy holatdan chiqish (masalan, boshqa qurilmadagi eskirgan CANCELLED) — server versiyasi yutadi.
    cancelled = bump(executed, status="CANCELLED")
    st = await env.ok([ef.op("isolation_plan", cancelled)], eng)
    assert set(st.values()) == {"stale"}
    row = next(r for r in await env.all_rows("isolation_plan") if r["id"] == approved["id"])
    assert row["status"] == "EXECUTED"
    assert (row["updated_at"], row["rev"]) > (cancelled["updated_at"], cancelled["rev"])  # pull'da qurilmaga qaytadi


async def test_cancelled_plan_cannot_be_resurrected(env: Env) -> None:
    g = await graph(env)
    eng, ef = await engineer_field(env)
    draft = plan_row(ef, g)
    cancelled = bump(draft, status="CANCELLED")
    await env.ok([ef.op("isolation_plan", draft), ef.op("isolation_plan", cancelled)], eng)
    st = await env.ok([ef.op("isolation_plan", bump(cancelled, status="DRAFT"))], eng)
    assert set(st.values()) == {"stale"}
    assert next(r for r in await env.all_rows("isolation_plan") if r["id"] == draft["id"])["status"] == "CANCELLED"


async def test_norm_set_review_is_bound_to_yaml(env: Env) -> None:
    from zanjir_server.crypto.hashing import sha256_hex

    f = env.field

    def norm(yaml: str, reviewed_by: str | None, reviewed_at: str | None = None) -> dict[str, Any]:
        return f.op(
            "norm_set",
            f.base(
                version="0.1.1",
                sha256=sha256_hex(yaml.encode()),
                yaml=yaml,
                reviewed_by=reviewed_by,
                reviewed_at=reviewed_at,
                deleted=False,
            ),
        )

    unreviewed = NORMS.format(rb="", ra="")
    # YAML'da bo'sh, qatorda "tekshirilgan" — soxtalashtirish.
    await env.rejected([norm(unreviewed, "Muhandis")], "norm_set_review_mismatch")
    bad_hash = norm(unreviewed, None)
    bad_hash["row"]["sha256"] = "0" * 64
    await env.rejected([bad_hash], "norm_set_hash_mismatch")
    await env.rejected([norm("[1, 2", None)], "norm_set_invalid")
    first = norm(unreviewed, None)
    await env.ok([first])
    other_content = NORMS.format(rb="X", ra="2026-10-01")
    changed = norm(other_content, "X", "2026-10-01")
    changed["row"]["id"] = first["row"]["id"]
    changed["row"].update(updated_at="2026-10-27T08:05:00.000Z", rev=2)
    await env.rejected([changed], "norm_set_conflict")
    await env.rejected([norm(unreviewed, None) | {"client_op_id": "v"}], "constraint_violation")


# --- protokol ---


async def signable(
    env: Env, verdicts: tuple[str, ...] = ("PASS",), **graph_kwargs: Any
) -> tuple[dict[str, Any], list[dict[str, Any]], dict[str, Any]]:
    g = await graph(env, **graph_kwargs)
    f = env.field
    ops: list[dict[str, Any]] = []
    for i, v in enumerate(verdicts):
        ops += f.measurement(g["ses"]["id"], g["node"]["id"], g["inst"]["id"], verdict=v, zs=0.5 + i / 10)
    await env.ok(ops)
    return g, rows(ops, "measurement"), g["inst"]


async def test_protocol_full_verification(env: Env) -> None:
    g, ms, inst = await signable(env)
    f = env.field
    payload = f.protocol_payload(g["ses"], ms, [inst])
    ops = f.protocol(g["ses"]["id"], payload)
    assert set((await env.ok(ops)).values()) == {"applied"}
    docs = await env.all_rows("protocol_document")
    assert docs[0]["protocol_id"] == rows(ops, "protocol")[0]["id"]
    assert set((await env.ok(ops)).values()) == {"duplicate"}


async def test_protocol_requires_document_event_and_valid_signature(env: Env) -> None:
    g, ms, inst = await signable(env)
    f = env.field
    payload = f.protocol_payload(g["ses"], ms, [inst])
    ev, proto, doc = f.protocol(g["ses"]["id"], payload)
    await env.rejected([ev, proto], "protocol_document_required")
    await env.rejected([proto, doc], "missing_audit_event")
    bad_sig = copy.deepcopy(proto)
    bad_sig["row"]["signature"] = "00" * 64
    # Hodisa payload'i imzoni ham qamraydi — avval hodisa mos kelmaydi.
    await env.rejected([ev, bad_sig, doc], "missing_audit_event")


async def test_protocol_signature_checked(env: Env) -> None:
    from zanjir_server.sync.service import protocol_audit_payload

    g, ms, inst = await signable(env)
    f = env.field
    payload = f.protocol_payload(g["ses"], ms, [inst])
    state = f.snapshot()
    _, proto, doc = f.protocol(g["ses"]["id"], payload)
    proto["row"]["signature"] = "11" * 64
    f.restore(state)  # hodisa soxta imzoli qator uchun qayta yaratiladi
    ev = f.event("PROTOCOL_SIGNED", proto["row"]["id"], protocol_audit_payload(proto["row"]))
    await env.rejected([ev, proto, doc], "bad_protocol_signature")


@pytest.mark.parametrize(
    ("verdicts", "kwargs", "reason"),
    [
        (("PASS",), {"reviewed": False}, "protocol_rule:norms_not_reviewed"),
        (("PASS", "NEEDS_REVIEW"), {"signer_role": "LEAD"}, "protocol_rule:lead_comment_required"),
    ],
)
async def test_protocol_rules(env: Env, verdicts: tuple[str, ...], kwargs: dict[str, Any], reason: str) -> None:
    g, ms, inst = await signable(env, verdicts, reviewed=kwargs.get("reviewed", True))
    f = env.field
    payload = f.protocol_payload(g["ses"], ms, [inst], **kwargs)
    await env.rejected(f.protocol(g["ses"]["id"], payload), reason)


async def test_protocol_needs_review_signed_by_engineer_rejected(env: Env, api: Api) -> None:
    eng = env.users["ENGINEER"]
    ef = Field(eng.org_id, eng.id, "66666666-6666-4666-8666-666666666666", seed=13)
    await api.device(eng, ef.public_key, ef.device_id)
    g = await graph(env)
    ops = ef.measurement(g["ses"]["id"], g["node"]["id"], g["inst"]["id"], verdict="NEEDS_REVIEW")
    await env.ok(ops, user=eng)
    payload = ef.protocol_payload(
        g["ses"], rows(ops, "measurement"), [g["inst"]], signer_role="ENGINEER", lead_comment="izoh"
    )
    await env.rejected(ef.protocol(g["ses"]["id"], payload), "protocol_rule:needs_review_requires_lead", user=eng)


async def test_protocol_expired_instrument_and_tampered_payload(env: Env) -> None:
    g, ms, inst = await signable(env, verified_until="2026-01-01T00:00:00.000Z")
    f = env.field
    state = f.snapshot()
    await env.rejected(
        f.protocol(g["ses"]["id"], f.protocol_payload(g["ses"], ms, [inst])), "protocol_rule:instrument_expired"
    )
    f.restore(state)
    # Payload asbobni "amalda" deb ko'rsatadi — qoida serverdagi asbob yozuvi bo'yicha (ADR-0014, M1).
    valid = {**inst, "verified_until": "2027-12-31T00:00:00.000Z"}
    await env.rejected(
        f.protocol(g["ses"]["id"], f.protocol_payload(g["ses"], ms, [valid])), "protocol_rule:instrument_expired"
    )
    f.restore(state)
    # Payload'dagi natija serverdagidan farq qiladi (FAIL ni PASS qilib ko'rsatish urinishi).
    lie = f.protocol_payload(g["ses"], [{**ms[0], "values": {"pair": "L1-PE", "zs_ohm": 0.01}}], [inst])
    await env.rejected(f.protocol(g["ses"]["id"], lie), "payload_measurement_mismatch")


async def test_protocol_payload_must_cover_current_measurements(env: Env) -> None:
    """M1 (ADR-0014): o'lchovni tushirib qoldirib (masalan, NEEDS_REVIEW) qoidani chetlab o'tib bo'lmaydi."""
    g, ms, inst = await signable(env, ("PASS", "NEEDS_REVIEW"))
    f = env.field
    state = f.snapshot()
    only_pass = f.protocol_payload(g["ses"], [m for m in ms if m["verdict"] == "PASS"], [inst])
    await env.rejected(f.protocol(g["ses"]["id"], only_pass), "payload_measurement_mismatch")
    f.restore(state)
    moved = f.protocol_payload(g["ses"], [{**ms[0], "created_at": "2026-10-20T00:00:00.000Z"}, ms[1]], [inst])
    await env.rejected(f.protocol(g["ses"]["id"], moved), "payload_measurement_mismatch")
    f.restore(state)
    full = f.protocol_payload(g["ses"], ms, [inst], lead_comment="Tekshirildi")
    await env.ok(f.protocol(g["ses"]["id"], full))


async def test_protocol_superseded_measurement_excluded(env: Env) -> None:
    g, ms, inst = await signable(env)
    f = env.field
    old = ms[0]
    redo = f.measurement(g["ses"]["id"], g["node"]["id"], g["inst"]["id"], zs=0.7, supersedes_id=old["id"])
    new = rows(redo, "measurement")[0]
    await env.ok(redo)
    state = f.snapshot()
    stale = f.protocol_payload(g["ses"], [old, new], [inst])
    await env.rejected(f.protocol(g["ses"]["id"], stale), "payload_measurement_mismatch")
    f.restore(state)
    await env.ok(f.protocol(g["ses"]["id"], f.protocol_payload(g["ses"], [new], [inst])))


async def test_protocol_norm_set_and_signed_at_from_server(env: Env) -> None:
    g, ms, inst = await signable(env, reviewed=False)
    f = env.field
    state = f.snapshot()
    # Payload normalarni "tekshirilgan" deb ko'rsatadi, serverdagi to'plam esa tekshirilmagan.
    await env.rejected(
        f.protocol(g["ses"]["id"], f.protocol_payload(g["ses"], ms, [inst])), "payload_norm_set_mismatch"
    )
    f.restore(state)
    old_sig = f.protocol_payload(g["ses"], ms, [inst], reviewed=False) | {"signed_at": "2026-10-01T00:00:00.000Z"}
    await env.rejected(f.protocol(g["ses"]["id"], old_sig), "protocol_rule:signed_at_mismatch")


async def test_protocol_qr_token_and_number_bound_to_device(env: Env) -> None:
    """M2/L3 (ADR-0014): QR token qurilma imzosidan; raqam — shu qurilma belgisi bilan va qat'iy formatda."""
    g, ms, inst = await signable(env)
    f = env.field
    state = f.snapshot()
    chosen = f.protocol_payload(g["ses"], ms, [inst], qr_token="0" * 32)
    await env.rejected(f.protocol(g["ses"]["id"], chosen), "qr_token_invalid")
    f.restore(state)
    foreign = f.protocol_payload(g["ses"], ms, [inst])
    foreign["protocol"]["qr_sig"] = Field(f.org_id, f.user_id, f.device_id, seed=99).signer.sign(b"x").hex()
    await env.rejected(f.protocol(g["ses"]["id"], foreign), "qr_token_invalid")
    for number in (
        "2026-ABCDEF-001",
        f'2026-{f.device_tag}-001"\r\nX: y',
        f"26-{f.device_tag}-001",
        f"٢٠٢٦-{f.device_tag}-001",
    ):
        f.restore(state)
        bad = f.protocol_payload(g["ses"], ms, [inst], number=number)
        await env.rejected(f.protocol(g["ses"]["id"], bad), "protocol_number_invalid")


async def test_protocol_event_bound_to_signer_and_device(env: Env) -> None:
    """L1: PROTOCOL_SIGNED hodisasi imzolovchi va uning qurilmasidan bo'lishi shart."""
    from zanjir_server.sync.service import protocol_audit_payload

    g, ms, inst = await signable(env)
    eng, ef = await engineer_field(env)
    f = env.field
    _, proto, doc = f.protocol(g["ses"]["id"], f.protocol_payload(g["ses"], ms, [inst]))
    ev = ef.event("PROTOCOL_SIGNED", proto["row"]["id"], protocol_audit_payload(proto["row"]))
    await env.rejected([ev, proto, doc], "missing_audit_event", eng)


async def test_protocol_pdf_checks(env: Env) -> None:
    from zanjir_server.crypto.canonical import canonical_json_bytes
    from zanjir_server.crypto.hashing import sha256_hex

    g, ms, inst = await signable(env)
    f = env.field
    payload = f.protocol_payload(g["ses"], ms, [inst])
    wrong_id = fake_pdf("b" * 64)
    state = f.snapshot()
    await env.rejected(f.protocol(g["ses"]["id"], payload, pdf=wrong_id), "pdf_id_mismatch")
    f.restore(state)
    sha = sha256_hex(canonical_json_bytes(payload))
    ops = f.protocol(g["ses"]["id"], payload, pdf=fake_pdf(sha))
    doc = ops[2]
    good_payload = doc["row"]["payload_json"]
    doc["row"]["payload_json"] = '{"x": NaN}'
    await env.rejected(ops, "invalid_payload")
    doc["row"]["payload_json"] = good_payload
    doc["row"]["pdf"] = "AAAA"  # boshqa bayt — hash mos emas
    await env.rejected(ops, "pdf_hash_mismatch")


async def test_audit_payload_helpers_match_app() -> None:
    """Ilova `measurementAuditPayload` bilan bir xil kalitlar (tartib kanonik JSON'da ahamiyatsiz)."""
    from zanjir_server.sync.service import measurement_audit_payload

    row = {
        k: k
        for k in (
            "id",
            "session_id",
            "node_id",
            "type",
            "instrument_id",
            "values",
            "entered_via",
            "verdict",
            "norm_id",
            "norm_set_version",
            "supersedes_id",
            "created_at",
            "eval_detail",
        )
    }
    p = measurement_audit_payload(row)
    assert set(p) == {
        "id",
        "session_id",
        "node_id",
        "type",
        "instrument_id",
        "values",
        "entered_via",
        "verdict",
        "norm_id",
        "norm_set_version",
        "supersedes_id",
    }
    assert payload_hash(p) == payload_hash(dict(reversed(list(p.items()))))


async def test_future_timestamps_rejected(env: Env) -> None:
    """Soati oldinda qurilma LWW'ni "kelajak" vaqt bilan egallab ololmaydi (ADR-0014)."""
    f = env.field
    site = f.site()
    site["row"]["updated_at"] = "2026-10-27T08:30:00.000Z"  # server soati 08:00, chegara +10 daqiqa
    await env.rejected([site], "clock_skew")
    ok = f.site()
    ok["row"]["updated_at"] = "2026-10-27T08:09:00.000Z"
    await env.ok([ok])


async def test_future_append_only_rows_accepted(env: Env) -> None:
    """M3: append-only (imzolangan) yozuvlar LWW'da qatnashmaydi — soat oldinda bo'lsa ham qurilma to'xtab qolmaydi."""
    from datetime import UTC, datetime

    g = await graph(env)
    f = env.field
    f.t = datetime(2026, 10, 27, 9, 0, tzinfo=UTC)  # server soati 08:00
    st = await env.ok(f.measurement(g["ses"]["id"], g["node"]["id"], g["inst"]["id"]))
    assert set(st.values()) == {"applied"}


@pytest.mark.parametrize("bad", [float("nan"), float("inf"), 2**60])
async def test_unhashable_json_rejected(env: Env, bad: object) -> None:
    """L4: NaN/Infinity va 2^53 dan katta son — 500 emas, aniq rad etish."""
    f = env.field
    site = f.site()
    node = f.node(site["row"]["id"])
    node["row"]["attrs"] = {"x": bad}
    r = await env.api.c.post(
        "/sync/push",
        content=json.dumps({"ops": [site, node]}),  # NaN/Infinity — Python json'da ruxsat etilgan kengaytma
        headers={**env.users["LEAD"].headers, "content-type": "application/json"},
    )
    assert r.status_code == 422, r.text
    assert r.json()["detail"]["reason"] == "type:node.attrs"
