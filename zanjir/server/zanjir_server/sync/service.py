"""`POST /sync/push` va `GET /sync/pull` mantig'i (ADR-0011).

Push — bitta tranzaksiya, "hammasi yoki hech narsa": birorta xato (audit zanjiri, imzo, qoida, cheklov) bo'lsa paket
to'liq rad etiladi. Takrorlangan `client_op_id` — o'tkazib yuboriladi (idempotent). Metadata — last-writer-wins
(`updated_at`, keyin `rev`); append-only jadvallar faqat qo'shiladi (bir xil qayta yuborish — takror, farqli — xato).
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Any

import yaml
from sqlalchemy import and_, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from zanjir_server.api.deps import Principal
from zanjir_server.crypto.canonical import canonical_json_bytes
from zanjir_server.crypto.hash_chain import AuditEvent as ChainEvent
from zanjir_server.crypto.hash_chain import payload_hash, verify_chain
from zanjir_server.crypto.hashing import sha256_hex
from zanjir_server.crypto.protocol import protocol_message, qr_token_from_signature, qr_token_message
from zanjir_server.crypto.signing import UnsupportedSigAlgError, verify_signature
from zanjir_server.db.models import (
    APPEND_ONLY,
    SYNC_MODELS,
    AppUser,
    AuditEvent,
    Base,
    Device,
    Instrument,
    IsolationPlan,
    Measurement,
    MeasurementSession,
    NormSet,
    Organization,
    Protocol,
    SyncOp,
)
from zanjir_server.security.roles import EDITORS, SIGNERS, Role
from zanjir_server.sync.protocol_rules import protocol_payload_violation
from zanjir_server.sync.wire import WireError, from_wire, iso, normalized, to_wire

# Qaysi jadvalni kim yuboradi (`app_user`, `device` — faqat API orqali).
PUSH_ROLES: dict[str, Role] = {
    "audit_event": Role.ENGINEER,
    "organization": Role.LEAD,
    "instrument": Role.ENGINEER,
    "site": Role.ENGINEER,
    "node": Role.ENGINEER,
    "edge": Role.ENGINEER,
    "measurement_session": Role.ENGINEER,
    "measurement": Role.ENGINEER,
    "protocol": Role.ENGINEER,
    "protocol_document": Role.ENGINEER,
    "isolation_plan": Role.ENGINEER,
    "norm_set": Role.LEAD,
    "org_setting": Role.LEAD,
}
# Muharrir rolini talab qiladigan audit hodisalari (ADR-0009, ADR-0010, ADR-0013).
EDITOR_EVENTS = {"PROTOCOL_REVOKED", "SETTINGS_CHANGED", "LAB_UPDATED", "PLAN_APPROVED"}
ORGANIZATION_FIELDS = ("name", "license_no", "license_valid_until")
SETTING_FIELDS = ("k_corr", "margin_pct", "active_norm_set_version")
# LWW'da mazmun emas — identifikator va versiya ustunlari.
META_FIELDS = ("id", "org_id", "created_at", "updated_at", "rev")
_PDF_ID = re.compile(rb"/ID\s*\[\s*<([0-9a-fA-F]{64})>\s*<([0-9a-fA-F]{64})>\s*\]")
# `YYYY-XXXXXX-NNN`: yil, qurilma ID sining oxirgi 6 belgisi, tartib raqami (ilovadagi `_nextNumber`).
_NUMBER = re.compile(r"[0-9]{4}-([0-9A-F]{6})-[0-9]{3,9}")  # faqat ASCII (`\d` Unicode raqamlarni ham oladi)

# Ajratish rejasi (ADR-0013, ADR-0014): ruxsat etilgan holat o'tishlari. EXECUTED, CANCELLED, STALE — yakuniy.
PLAN_TRANSITIONS: dict[str, set[str]] = {
    "DRAFT": {"DRAFT", "APPROVED", "EXECUTED", "CANCELLED", "STALE"},  # oflayn: tasdiq va bajarish bitta push'da
    "APPROVED": {"APPROVED", "EXECUTED", "CANCELLED", "STALE"},
}
# Reja yaratilgandan keyin o'zgarmaydigan ustunlar — tasdiq aynan shu qadamlarga beriladi.
PLAN_FROZEN = ("site_id", "target_node_ids", "solver_version", "graph_snapshot_hash", "steps", "warnings", "deleted")


class PushRejected(Exception):
    def __init__(self, reason: str, op_id: str | None = None) -> None:
        super().__init__(reason)
        self.reason = reason
        self.op_id = op_id


@dataclass
class Op:
    client_op_id: str
    table: str
    row: dict[str, Any]
    values: dict[str, Any] = field(default_factory=dict)
    status: str = "applied"


def measurement_audit_payload(v: dict[str, Any]) -> dict[str, Any]:
    """Ilovadagi `measurementAuditPayload` bilan bir xil (zanjir_data)."""
    keys = ("id", "session_id", "node_id", "type", "instrument_id", "values", "entered_via", "verdict", "norm_id")
    out = {k: v[k] for k in keys}
    out["norm_set_version"] = v["norm_set_version"]
    out["supersedes_id"] = v["supersedes_id"]
    return out


def protocol_audit_payload(v: dict[str, Any]) -> dict[str, Any]:
    keys = ("id", "session_id", "number", "payload_sha256", "pdf_sha256", "signature", "sig_alg", "qr_token")
    return {k: v[k] for k in keys}


class PushService:
    def __init__(
        self, s: AsyncSession, p: Principal, now: datetime, max_skew: timedelta = timedelta(minutes=10)
    ) -> None:
        self.s = s
        self.p = p
        self.now = now
        self.max_skew = max_skew

    async def run(self, raw_ops: list[dict[str, Any]]) -> list[Op]:
        ops = self._parse(raw_ops)
        seen = {
            r
            for (r,) in await self.s.execute(
                select(SyncOp.client_op_id).where(
                    SyncOp.org_id == self.p.org_id, SyncOp.client_op_id.in_([o.client_op_id for o in ops])
                )
            )
        }
        for o in ops:
            if o.client_op_id in seen:
                o.status = "duplicate"
        todo = [o for o in ops if o.status != "duplicate"]
        await self._audit([o for o in todo if o.table == "audit_event"])
        order = list(SYNC_MODELS)
        for o in sorted((o for o in todo if o.table != "audit_event"), key=lambda o: order.index(o.table)):
            if o.table in APPEND_ONLY:
                await self._append(o, todo)
            else:
                await self._upsert(o)
        await self.s.flush()
        for o in todo:
            self.s.add(SyncOp(org_id=self.p.org_id, client_op_id=o.client_op_id, received_at=self.now, status=o.status))
        return ops

    # --- tahlil ---

    def _parse(self, raw_ops: list[dict[str, Any]]) -> list[Op]:
        ops: list[Op] = []
        ids: set[str] = set()
        for raw in raw_ops:
            op_id, table, row = raw["client_op_id"], raw["table"], raw["row"]
            if op_id in ids:
                raise PushRejected("duplicate_op_id", op_id)
            ids.add(op_id)
            need = PUSH_ROLES.get(table)
            if need is None:
                raise PushRejected("table_not_pushable", op_id)
            if not self.p.role.at_least(need):
                raise PushRejected("forbidden_role", op_id)
            try:
                values = from_wire(table, row)
            except WireError as e:
                raise PushRejected(e.reason, op_id) from e
            org = values["id"] if table == "organization" else values["org_id"]
            if org != self.p.org_id:
                raise PushRejected("wrong_org", op_id)
            # Qurilma soati oldinda bo'lsa LWW'da "kelajak" vaqt abadiy yutib qolardi (ADR-0014). Append-only yozuvlar
            # LWW'da qatnashmaydi va imzolangan — ularni rad etish qurilmani abadiy to'xtatib qo'yardi.
            latest = self.now + self.max_skew
            if table not in APPEND_ONLY and (values["created_at"] > latest or values["updated_at"] > latest):
                raise PushRejected("clock_skew", op_id)
            ops.append(Op(op_id, table, row, values))
        return ops

    # --- audit zanjiri ---

    async def _audit(self, ops: list[Op]) -> None:
        by_device: dict[str, list[Op]] = {}
        for o in ops:
            by_device.setdefault(o.values["device_id"], []).append(o)
        for device_id, dev_ops in by_device.items():
            device = await self._device(device_id, dev_ops[0].client_op_id)
            if device.user_id != self.p.user_id:
                raise PushRejected("device_not_owned", dev_ops[0].client_op_id)
            dev_ops.sort(key=lambda o: o.values["seq"])
            stored = {
                e.seq: e
                for e in (
                    await self.s.execute(
                        select(AuditEvent).where(
                            AuditEvent.device_id == device_id, AuditEvent.seq.in_([o.values["seq"] for o in dev_ops])
                        )
                    )
                ).scalars()
            }
            fresh: list[Op] = []
            for o in dev_ops:
                old = stored.get(o.values["seq"])
                if old is None:
                    fresh.append(o)
                elif normalized("audit_event", o.values) == to_wire("audit_event", old):
                    o.status = "duplicate"
                else:
                    raise PushRejected("audit_conflict", o.client_op_id)
            if not fresh:
                continue
            for o in fresh:
                if o.values["actor_id"] != self.p.user_id:
                    raise PushRejected("actor_mismatch", o.client_op_id)
                if o.values["event_type"] in EDITOR_EVENTS and self.p.role not in EDITORS:
                    raise PushRejected("forbidden_role", o.client_op_id)
            anchor_row = (
                await self.s.execute(
                    select(AuditEvent)
                    .where(AuditEvent.device_id == device_id, AuditEvent.seq < fresh[0].values["seq"])
                    .order_by(AuditEvent.seq.desc())
                    .limit(1)
                )
            ).scalar_one_or_none()
            result = verify_chain(
                [_chain(o.values) for o in fresh],
                public_key_hex=device.public_key_ed25519,
                anchor=_chain(to_wire_values(anchor_row)) if anchor_row else None,
            )
            if not result.ok:
                bad = fresh[result.failed_index or 0]
                raise PushRejected(f"audit_chain:{result.reason}", bad.client_op_id)
            for o in fresh:
                self.s.add(AuditEvent(**o.values))
        await self.s.flush()

    async def _device(self, device_id: str, op_id: str) -> Device:
        d = (await self.s.execute(select(Device).where(Device.id == device_id))).scalar_one_or_none()
        if d is None:
            raise PushRejected("unknown_device", op_id)
        if d.revoked_at is not None or d.deleted:
            raise PushRejected("device_revoked", op_id)
        return d

    async def _has_event(
        self,
        event_type: str,
        entity_id: str,
        phash: str | None = None,
        *,
        actor_id: str | None = None,
        device_id: str | None = None,
    ) -> bool:
        q = select(AuditEvent.id).where(AuditEvent.event_type == event_type, AuditEvent.entity_id == entity_id)
        if phash is not None:
            q = q.where(AuditEvent.payload_hash == phash)
        if actor_id is not None:
            q = q.where(AuditEvent.actor_id == actor_id)
        if device_id is not None:
            q = q.where(AuditEvent.device_id == device_id)
        return (await self.s.execute(q.limit(1))).first() is not None

    # --- append-only ---

    async def _append(self, o: Op, batch: list[Op]) -> None:
        model = SYNC_MODELS[o.table]
        old = (await self.s.execute(select(model).where(model.id == o.values["id"]))).scalar_one_or_none()  # type: ignore[attr-defined]
        if old is not None:
            if normalized(o.table, o.values) != to_wire(o.table, old):
                raise PushRejected("append_only_conflict", o.client_op_id)
            o.status = "duplicate"
            return
        v = o.values
        if o.table == "measurement":
            if not await self._has_event("MEASUREMENT_ADDED", v["id"], payload_hash(measurement_audit_payload(v))):
                raise PushRejected("missing_audit_event", o.client_op_id)
        elif o.table == "protocol":
            await self._check_protocol(o, batch)
        elif o.table == "protocol_document":
            await self._check_document(o)
        self.s.add(model(**v))
        await self.s.flush()

    async def _check_protocol(self, o: Op, batch: list[Op]) -> None:
        v = o.values
        phash = payload_hash(protocol_audit_payload(v))
        if not await self._has_event(
            "PROTOCOL_SIGNED", v["id"], phash, actor_id=v["signed_by"], device_id=v["device_id"]
        ):
            raise PushRejected("missing_audit_event", o.client_op_id)
        # Raqam formati (PDF fayl nomi shundan) va qurilma belgisi — boshqa qurilma raqamini band qilib bo'lmaydi.
        m = _NUMBER.fullmatch(v["number"])
        if m is None or m[1] != v["device_id"].replace("-", "")[-6:].upper():
            raise PushRejected("protocol_number_invalid", o.client_op_id)
        device = await self._device(v["device_id"], o.client_op_id)
        if device.user_id != v["signed_by"]:
            raise PushRejected("signer_device_mismatch", o.client_op_id)
        signer = await self._user(v["signed_by"])
        if signer is None or Role(signer.role) not in SIGNERS:
            raise PushRejected("forbidden_signer_role", o.client_op_id)
        try:
            ok = verify_signature(
                sig_alg=v["sig_alg"],
                public_key_hex=device.public_key_ed25519,
                message=protocol_message(v["payload_sha256"], v["pdf_sha256"]),
                signature_hex=v["signature"],
            )
        except (UnsupportedSigAlgError, ValueError):
            ok = False
        if not ok:
            raise PushRejected("bad_protocol_signature", o.client_op_id)
        has_doc = any(b.table == "protocol_document" and b.values["protocol_id"] == v["id"] for b in batch)
        if not has_doc:
            raise PushRejected("protocol_document_required", o.client_op_id)

    async def _check_document(self, o: Op) -> None:
        v = o.values
        protocol = (await self.s.execute(select(Protocol).where(Protocol.id == v["protocol_id"]))).scalar_one_or_none()
        if protocol is None:
            raise PushRejected("unknown_protocol", o.client_op_id)
        try:
            payload = json.loads(v["payload_json"], parse_constant=_reject_constant)
            payload_sha = sha256_hex(canonical_json_bytes(payload))
        except ValueError as e:  # JSONDecodeError, NaN/Infinity, 2^53 dan katta son
            raise PushRejected("invalid_payload", o.client_op_id) from e
        if not isinstance(payload, dict):
            raise PushRejected("invalid_payload", o.client_op_id)
        if payload_sha != protocol.payload_sha256:
            raise PushRejected("payload_hash_mismatch", o.client_op_id)
        if sha256_hex(v["pdf"]) != protocol.pdf_sha256:
            raise PushRejected("pdf_hash_mismatch", o.client_op_id)
        ids = _PDF_ID.findall(v["pdf"])
        if len(ids) != 1 or {i.decode().lower() for i in ids[0]} != {protocol.payload_sha256}:
            raise PushRejected("pdf_id_mismatch", o.client_op_id)
        meta, signer, session = (_section(payload, k) for k in ("protocol", "signer", "session"))
        if (
            meta.get("number") != protocol.number
            or meta.get("qr_token") != protocol.qr_token
            or signer.get("id") != protocol.signed_by
            or session.get("id") != protocol.session_id
        ):
            raise PushRejected("payload_protocol_mismatch", o.client_op_id)
        await self._check_qr_token(protocol, meta.get("qr_sig"), o.client_op_id)
        signed_at = _datetime(payload.get("signed_at"))
        if signed_at is None or not -CLOCK_JITTER <= protocol.created_at - signed_at <= SIGN_WINDOW:
            raise PushRejected("protocol_rule:signed_at_mismatch", o.client_op_id)
        user = await self._user(protocol.signed_by)
        # Qoidalar serverdagi yozuvlar bo'yicha tekshiriladi (payload'ning o'z da'volari emas, ADR-0014).
        effective = await self._effective_payload(payload, protocol.session_id, o.client_op_id)
        violation = protocol_payload_violation(effective, user.role if user else "")
        if violation:
            raise PushRejected(f"protocol_rule:{violation}", o.client_op_id)

    async def _check_qr_token(self, protocol: Protocol, qr_sig: object, op_id: str) -> None:
        """`qr_token = sha256(qr_sig)[:32]`, `qr_sig` — imzolagan qurilma kaliti bilan (ADR-0014)."""
        device = await self._device(protocol.device_id, op_id)
        try:
            ok = isinstance(qr_sig, str) and verify_signature(
                sig_alg=protocol.sig_alg,
                public_key_hex=device.public_key_ed25519,
                message=qr_token_message(protocol.org_id, protocol.number),
                signature_hex=qr_sig,
            )
        except (UnsupportedSigAlgError, ValueError):
            ok = False
        if not ok or qr_token_from_signature(str(qr_sig)) != protocol.qr_token:
            raise PushRejected("qr_token_invalid", op_id)

    async def _effective_payload(self, payload: dict[str, Any], session_id: str, op_id: str) -> dict[str, Any]:
        """Payload'dagi o'lchovlar sessiyaning amaldagi (almashtirilmagan) o'lchovlari bilan aynan bir xil bo'lishi
        shart — PDF shu ma'lumotdan. Qoidalar uchun asbob guvohnomasi, litsenziya va norma tekshiruvi serverdagi
        yozuvlardan olinadi."""
        session = (
            await self.s.execute(select(MeasurementSession).where(MeasurementSession.id == session_id))
        ).scalar_one_or_none()
        if session is None or session.closed_at is None:
            raise PushRejected("protocol_rule:session_open", op_id)
        rows = list((await self.s.execute(select(Measurement).where(Measurement.session_id == session_id))).scalars())
        replaced = {m.supersedes_id for m in rows if m.supersedes_id}
        current = {m.id: m for m in rows if m.id not in replaced}
        items = payload.get("measurements")
        if not isinstance(items, list) or not all(isinstance(m, dict) and isinstance(m.get("id"), str) for m in items):
            raise PushRejected("invalid_payload", op_id)
        if sorted(m["id"] for m in items) != sorted(current):
            raise PushRejected("payload_measurement_mismatch", op_id)
        for m in items:
            row = current[m["id"]]
            if (m.get("verdict"), m.get("values"), m.get("instrument_id"), m.get("created_at")) != (
                row.verdict,
                row.values,
                row.instrument_id,
                iso(row.created_at),
            ):
                raise PushRejected("payload_measurement_mismatch", op_id)
        used = {m.instrument_id for m in current.values()}
        instruments = (await self.s.execute(select(Instrument).where(Instrument.id.in_(used)))).scalars()
        org = (await self.s.execute(select(Organization).where(Organization.id == self.p.org_id))).scalar_one()
        versions = {m.norm_set_version for m in current.values()}
        norm = None
        if len(versions) == 1:
            norm = (
                await self.s.execute(select(NormSet).where(NormSet.version == next(iter(versions))))
            ).scalar_one_or_none()
        claimed = _section(payload, "norm_set")
        if norm is None or (claimed.get("version"), claimed.get("sha256"), claimed.get("reviewed_by")) != (
            norm.version,
            norm.sha256,
            norm.reviewed_by,
        ):
            raise PushRejected("payload_norm_set_mismatch", op_id)
        lab = _section(payload, "lab")
        return {
            **payload,
            "lab": {**lab, "license_no": org.license_no, "license_valid_until": _iso_or_none(org.license_valid_until)},
            "norm_set": {"reviewed_by": norm.reviewed_by if norm else None},
            "instruments": [{"id": i.id, "verified_until": _iso_or_none(i.verified_until)} for i in instruments],
            "measurements": [
                {
                    "id": m.id,
                    "instrument_id": m.instrument_id,
                    "created_at": iso(m.created_at),
                    "verdict": m.verdict,
                    **{k: m.eval_detail[k] for k in ("instrument_verified_until",) if k in m.eval_detail},
                }
                for m in current.values()
            ],
        }

    async def _user(self, user_id: str) -> AppUser | None:
        return (await self.s.execute(select(AppUser).where(AppUser.id == user_id))).scalar_one_or_none()

    # --- metadata: last-writer-wins ---

    async def _upsert(self, o: Op) -> None:
        model = SYNC_MODELS[o.table]
        v = o.values
        old = (
            await self.s.execute(select(model).where(model.id == v["id"]).with_for_update())  # type: ignore[attr-defined]
        ).scalar_one_or_none()
        await self._check_mutable(o, old)
        if old is None:
            if o.table == "organization":
                raise PushRejected("wrong_org", o.client_op_id)  # o'z tashkiloti doim mavjud
            if o.table == "isolation_plan":
                await self._check_plan_status(o, None)
            await self._check_audited_change(o, None)
            self.s.add(model(**v))
            return
        fields = ORGANIZATION_FIELDS if o.table == "organization" else [k for k in v if k not in META_FIELDS]
        if (v["updated_at"], v["rev"]) <= (old.updated_at, old.rev):  # type: ignore[attr-defined]
            o.status = "stale"
            if any(normalized(o.table, v)[k] != to_wire(o.table, old)[k] for k in fields):
                # Qurilma yutqazdi (masalan, soati orqada), lekin o'z qiymatini ko'rsatib turibdi: server qatori qayta
                # yuboriladi (`server_rev` oshadi) — pull'da qurilma server versiyasini oladi va ajralib qolmaydi.
                await self.s.execute(update(model).where(model.id == v["id"]).values(rev=model.rev))  # type: ignore[attr-defined]
            return
        if o.table == "isolation_plan" and not await self._check_plan_status(o, old):  # type: ignore[arg-type]
            # Yakuniy holatdan chiqib bo'lmaydi: server versiyasi yutadi va pull'da qurilmaga qaytadi.
            old.updated_at = max(old.updated_at, v["updated_at"])  # type: ignore[attr-defined]
            old.rev = max(old.rev, v["rev"]) + 1  # type: ignore[attr-defined]
            o.status = "stale"
            return
        await self._check_audited_change(o, old)
        for k in (*fields, "updated_at", "rev"):
            setattr(old, k, v[k])

    async def _check_mutable(self, o: Op, old: Base | None) -> None:
        v = o.values
        if o.table == "measurement_session" and old is not None:
            if old.closed_at is not None and v["closed_at"] is None:  # type: ignore[attr-defined]
                raise PushRejected("session_reopen", o.client_op_id)
        elif o.table == "isolation_plan" and old is not None:
            frozen = [*PLAN_FROZEN, *(("approved_by",) if old.approved_by is not None else ())]  # type: ignore[attr-defined]
            if any(normalized(o.table, v)[k] != to_wire(o.table, old)[k] for k in frozen):
                raise PushRejected("plan_immutable", o.client_op_id)
        elif o.table == "norm_set":
            await self._check_norm_set(o, old)

    async def _check_plan_status(self, o: Op, old: IsolationPlan | None) -> bool:
        """Holat o'tishi ruxsat etilganmi (False — yakuniy holatdan chiqish: server versiyasi qoladi). APPROVED va
        EXECUTED — LEAD/ADMIN ning aynan shu qadamlarga imzolangan `PLAN_APPROVED` hodisasi bilan; EXECUTED — barcha
        qadamlar va `PLAN_EXECUTED` hodisasi bilan. Aks holda paket rad etiladi."""
        v = o.values
        new = v["status"]
        if old is not None and new not in PLAN_TRANSITIONS.get(old.status, {old.status}):
            return False
        if new in ("APPROVED", "EXECUTED") and (old is None or old.status == "DRAFT" or new == "EXECUTED"):
            approver = await self._user(v["approved_by"]) if v["approved_by"] else None
            if approver is None or Role(approver.role) not in EDITORS:
                raise PushRejected("approval_requires_lead", o.client_op_id)
            if not await self._has_event(
                "PLAN_APPROVED", v["id"], payload_hash(plan_approval_payload(v)), actor_id=v["approved_by"]
            ):
                raise PushRejected("missing_audit_event", o.client_op_id)
        if new == "EXECUTED" and (old is None or old.status != "EXECUTED"):
            orders = [st.get("order") if isinstance(st, dict) else None for st in v["steps"]]
            if not await self._has_event("PLAN_EXECUTED", v["id"]) or not await self._steps_done(v["id"], orders):
                raise PushRejected("plan_steps_incomplete", o.client_op_id)
        return True

    async def _steps_done(self, plan_id: str, orders: list[object]) -> bool:
        if not all(isinstance(n, int) and not isinstance(n, bool) for n in orders):
            return False
        want = {f"{plan_id}#{n}" for n in orders}
        done = {
            e
            for (e,) in await self.s.execute(
                select(AuditEvent.entity_id).where(
                    AuditEvent.event_type == "PLAN_STEP_DONE", AuditEvent.entity_id.in_(want)
                )
            )
        }
        return done == want

    async def _check_audited_change(self, o: Op, old: Base | None) -> None:
        """Laboratoriya rekvizitlari va sozlamalari o'zgarishi — imzolangan audit hodisasi bilan (ADR-0014)."""
        if o.table == "organization":
            event, fields = "LAB_UPDATED", ORGANIZATION_FIELDS
        elif o.table == "org_setting":
            event, fields = "SETTINGS_CHANGED", SETTING_FIELDS
        else:
            return
        v = o.values
        if old is not None and all(normalized(o.table, v)[k] == to_wire(o.table, old)[k] for k in fields):
            return
        if not await self._has_event(event, self.p.org_id, payload_hash({k: v[k] for k in fields})):
            raise PushRejected("missing_audit_event", o.client_op_id)

    async def _check_norm_set(self, o: Op, old: Base | None) -> None:
        v = o.values
        if sha256_hex(v["yaml"].encode()) != v["sha256"]:
            raise PushRejected("norm_set_hash_mismatch", o.client_op_id)
        try:
            doc = yaml.safe_load(v["yaml"])
        except yaml.YAMLError as e:
            raise PushRejected("norm_set_invalid", o.client_op_id) from e
        if not isinstance(doc, dict) or str(doc.get("version")) != v["version"]:
            raise PushRejected("norm_set_invalid", o.client_op_id)
        # `reviewed_by` faqat YAML ichidan (sha256 bilan himoyalangan) — alohida soxtalashtirib bo'lmaydi.
        for key in ("reviewed_by", "reviewed_at"):
            in_yaml = str(doc.get(key) or "").strip() or None
            if in_yaml != (v[key].strip() or None if isinstance(v[key], str) else None):
                raise PushRejected("norm_set_review_mismatch", o.client_op_id)
        if old is not None and old.sha256 != v["sha256"]:  # type: ignore[attr-defined]
            raise PushRejected("norm_set_conflict", o.client_op_id)


def plan_approval_payload(v: dict[str, Any]) -> dict[str, Any]:
    """Ilovadagi `planApprovalPayload` bilan bir xil (zanjir_data)."""
    return {
        "id": v["id"],
        "graph_snapshot_hash": v["graph_snapshot_hash"],
        "steps_sha256": sha256_hex(canonical_json_bytes(v["steps"])),
    }


# Ilovada qoralama 15 daqiqada eskiradi (`ProtocolRepository.draftTtl`); bir oz zaxira bilan.
SIGN_WINDOW = timedelta(minutes=16)
CLOCK_JITTER = timedelta(
    minutes=1
)  # tayyorlash va imzolash orasida qurilma soati biroz orqaga tuzatilishi mumkin (NTP)


def _datetime(v: object) -> datetime | None:
    if not isinstance(v, str):
        return None
    try:
        d = datetime.fromisoformat(v.replace("Z", "+00:00"))
    except ValueError:
        return None
    return d if d.tzinfo is not None else None


def _reject_constant(name: str) -> object:
    raise ValueError(name)


def _iso_or_none(t: datetime | None) -> str | None:
    return iso(t) if t is not None else None


def _section(payload: dict[str, Any], key: str) -> dict[str, Any]:
    v = payload.get(key)
    return v if isinstance(v, dict) else {}


def _chain(v: dict[str, Any]) -> ChainEvent:
    return ChainEvent(
        device_id=v["device_id"],
        seq=v["seq"],
        prev_hash=v["prev_hash"],
        event_hash=v["event_hash"],
        actor_id=v["actor_id"],
        event_type=v["event_type"],
        entity_id=v["entity_id"],
        payload_hash=v["payload_hash"],
        created_at=v["event_at"],
        device_sig=v["device_sig"],
        sig_alg=v["sig_alg"],
    )


def to_wire_values(row: AuditEvent) -> dict[str, Any]:
    return {c.key: getattr(row, c.key) for c in AuditEvent.__table__.columns}


async def pull(s: AsyncSession, org_id: str, since: int, limit: int) -> tuple[list[dict[str, Any]], bool]:
    """`server_rev > since` o'zgarishlar, `server_rev` bo'yicha tartiblangan; (o'zgarishlar, yana bormi)."""
    found: list[tuple[int, str, Base]] = []
    more = False
    for table, model in SYNC_MODELS.items():
        key = model.id if table == "organization" else model.org_id  # type: ignore[attr-defined]
        rows = (
            await s.execute(
                select(model)
                .where(and_(key == org_id, model.server_rev > since))  # type: ignore[attr-defined]
                .order_by(model.server_rev)  # type: ignore[attr-defined]
                .limit(limit + 1)
            )
        ).scalars()
        lst = list(rows)
        more |= len(lst) > limit
        found += [(r.server_rev, table, r) for r in lst[:limit]]  # type: ignore[attr-defined]
    found.sort(key=lambda x: x[0])
    more |= len(found) > limit
    return [{"table": t, "server_rev": rev, "row": to_wire(t, r)} for rev, t, r in found[:limit]], more
