"""Server jadvallari. Ustun nomlari ilovadagi Drift sxemasi bilan bir xil (sinxronlash formati, ADR-0011).

- Har bir tashkilot jadvalida `org_id` + Postgres RLS (migratsiyada); bog'liqliklar `(org_id, id)` kompozit
  kalit orqali — boshqa tashkilot yozuviga havola qilib bo'lmaydi.
- `server_rev` — tashkilot ichidagi o'zgarish tartibi (trigger beradi, `GET /sync/pull?since=`).
- `measurement`, `protocol`, `protocol_document`, `audit_event` — append-only
  (trigger: UPDATE/DELETE/TRUNCATE taqiqlangan).
"""

from __future__ import annotations

from datetime import datetime
from typing import Any, ClassVar

from sqlalchemy import (
    BigInteger,
    Boolean,
    CheckConstraint,
    DateTime,
    Float,
    ForeignKeyConstraint,
    Index,
    Integer,
    LargeBinary,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

ID = String(36)
ROLES = ("ADMIN", "LEAD", "ENGINEER", "VIEWER")


def _in(column: str, values: tuple[str, ...]) -> str:
    return f"{column} IN ({', '.join(repr(v) for v in values)})"


class Base(DeclarativeBase):
    type_annotation_map: ClassVar[dict[Any, Any]] = {
        dict[str, Any]: JSONB,
        list[Any]: JSONB,
        datetime: DateTime(timezone=True),
    }


class _Row:
    id: Mapped[str] = mapped_column(ID, primary_key=True)
    created_at: Mapped[datetime]
    updated_at: Mapped[datetime]
    rev: Mapped[int] = mapped_column(Integer, default=1)
    server_rev: Mapped[int] = mapped_column(BigInteger, default=0)


class _Org(_Row):
    org_id: Mapped[str] = mapped_column(ID)


class _SoftDelete:
    deleted: Mapped[bool] = mapped_column(Boolean, default=False)


def _org_fk(cols: list[str], table: str, ref: str = "id") -> ForeignKeyConstraint:
    """Bir tashkilot ichidagi havola: `(org_id, col) → table(org_id, id)`; DEFERRED — partiyadagi tartib muhim emas."""
    return ForeignKeyConstraint(
        ["org_id", *cols], [f"{table}.org_id", f"{table}.{ref}"], deferrable=True, initially="DEFERRED"
    )


def _org_unique() -> UniqueConstraint:
    return UniqueConstraint("org_id", "id")


class Organization(_Row, _SoftDelete, Base):
    __tablename__ = "organization"
    name: Mapped[str] = mapped_column(Text)
    license_no: Mapped[str | None] = mapped_column(Text)
    license_valid_until: Mapped[datetime | None]


class AppUser(_Org, _SoftDelete, Base):
    __tablename__ = "app_user"
    full_name: Mapped[str] = mapped_column(Text)
    phone: Mapped[str] = mapped_column(String(20), unique=True)
    password_hash: Mapped[str] = mapped_column(Text)
    role: Mapped[str] = mapped_column(String(16))
    safety_group: Mapped[str | None] = mapped_column(String(3))
    __table_args__ = (
        _org_unique(),
        ForeignKeyConstraint(["org_id"], ["organization.id"]),
        CheckConstraint(_in("role", ROLES), name="app_user_role"),
        CheckConstraint("safety_group IS NULL OR " + _in("safety_group", ("I", "II", "III", "IV", "V")), name="sg"),
    )


class Device(_Org, _SoftDelete, Base):
    __tablename__ = "device"
    user_id: Mapped[str] = mapped_column(ID)
    public_key_ed25519: Mapped[str] = mapped_column(String(64))
    sig_alg: Mapped[str] = mapped_column(String(32))
    registered_at: Mapped[datetime]
    revoked_at: Mapped[datetime | None]
    __table_args__ = (_org_unique(), _org_fk(["user_id"], "app_user"))


class Instrument(_Org, _SoftDelete, Base):
    __tablename__ = "instrument"
    kind: Mapped[str] = mapped_column(Text)
    model: Mapped[str] = mapped_column(Text)
    serial_no: Mapped[str] = mapped_column(Text)
    verification_cert_no: Mapped[str | None] = mapped_column(Text)
    verified_until: Mapped[datetime | None]
    __table_args__ = (_org_unique(), ForeignKeyConstraint(["org_id"], ["organization.id"]))


class Site(_Org, _SoftDelete, Base):
    __tablename__ = "site"
    name: Mapped[str] = mapped_column(Text)
    address: Mapped[str | None] = mapped_column(Text)
    customer: Mapped[str | None] = mapped_column(Text)
    earthing_system: Mapped[str | None] = mapped_column(String(8))
    u0_volts: Mapped[float | None] = mapped_column(Float)
    __table_args__ = (
        _org_unique(),
        ForeignKeyConstraint(["org_id"], ["organization.id"]),
        CheckConstraint(
            "earthing_system IS NULL OR " + _in("earthing_system", ("TN-C", "TN-S", "TN-C-S", "TT", "IT")), name="es"
        ),
    )


class Node(_Org, _SoftDelete, Base):
    __tablename__ = "node"
    site_id: Mapped[str] = mapped_column(ID)
    kind: Mapped[str] = mapped_column(String(32))
    label: Mapped[str] = mapped_column(Text)
    panel_id: Mapped[str | None] = mapped_column(ID)
    state: Mapped[str | None] = mapped_column(String(8))
    attrs: Mapped[dict[str, Any]] = mapped_column(default=dict)
    verified: Mapped[bool] = mapped_column(Boolean, default=False)
    x: Mapped[float | None] = mapped_column(Float)
    y: Mapped[float | None] = mapped_column(Float)
    __table_args__ = (
        _org_unique(),
        _org_fk(["site_id"], "site"),
        _org_fk(["panel_id"], "node"),
        CheckConstraint("state IS NULL OR " + _in("state", ("CLOSED", "OPEN")), name="node_state"),
    )


class Edge(_Org, _SoftDelete, Base):
    __tablename__ = "edge"
    site_id: Mapped[str] = mapped_column(ID)
    a_node_id: Mapped[str] = mapped_column(ID)
    b_node_id: Mapped[str] = mapped_column(ID)
    conductors: Mapped[str] = mapped_column(Text)
    __table_args__ = (
        _org_unique(),
        _org_fk(["site_id"], "site"),
        _org_fk(["a_node_id"], "node"),
        _org_fk(["b_node_id"], "node"),
    )


class MeasurementSession(_Org, _SoftDelete, Base):
    __tablename__ = "measurement_session"
    site_id: Mapped[str] = mapped_column(ID)
    kind: Mapped[str] = mapped_column(String(24))
    engineer_id: Mapped[str] = mapped_column(ID)
    ambient_temp_c: Mapped[float | None] = mapped_column(Float)
    humidity_pct: Mapped[float | None] = mapped_column(Float)
    started_at: Mapped[datetime]
    closed_at: Mapped[datetime | None]
    __table_args__ = (
        _org_unique(),
        _org_fk(["site_id"], "site"),
        _org_fk(["engineer_id"], "app_user"),
        CheckConstraint(_in("kind", ("QABUL_TOPSHIRISH", "DAVRIY", "NAVBATDAN_TASHQARI")), name="session_kind"),
    )


class Measurement(_Org, Base):
    __tablename__ = "measurement"
    session_id: Mapped[str] = mapped_column(ID)
    node_id: Mapped[str] = mapped_column(ID)
    type: Mapped[str] = mapped_column(String(24))
    instrument_id: Mapped[str] = mapped_column(ID)
    values: Mapped[dict[str, Any]]
    entered_via: Mapped[str] = mapped_column(String(8))
    verdict: Mapped[str] = mapped_column(String(16))
    norm_id: Mapped[str | None] = mapped_column(Text)
    norm_set_version: Mapped[str] = mapped_column(Text)
    eval_detail: Mapped[dict[str, Any]]
    supersedes_id: Mapped[str | None] = mapped_column(ID, unique=True)
    __table_args__ = (
        _org_unique(),
        _org_fk(["session_id"], "measurement_session"),
        _org_fk(["node_id"], "node"),
        _org_fk(["instrument_id"], "instrument"),
        _org_fk(["supersedes_id"], "measurement"),
        CheckConstraint(_in("verdict", ("PASS", "FAIL", "NEEDS_REVIEW", "NOT_APPLICABLE")), name="verdict"),
        CheckConstraint(_in("entered_via", ("MANUAL", "OCR", "BT")), name="entered_via"),
    )


class Protocol(_Org, Base):
    __tablename__ = "protocol"
    session_id: Mapped[str] = mapped_column(ID)
    number: Mapped[str] = mapped_column(Text)
    payload_sha256: Mapped[str] = mapped_column(String(64))
    pdf_sha256: Mapped[str] = mapped_column(String(64))
    signed_by: Mapped[str] = mapped_column(ID)
    device_id: Mapped[str] = mapped_column(ID)
    signature: Mapped[str] = mapped_column(Text)
    sig_alg: Mapped[str] = mapped_column(String(32))
    qr_token: Mapped[str] = mapped_column(String(64), unique=True)
    __table_args__ = (
        _org_unique(),
        UniqueConstraint("org_id", "number"),
        _org_fk(["session_id"], "measurement_session"),
        _org_fk(["signed_by"], "app_user"),
        _org_fk(["device_id"], "device"),
    )


class ProtocolDocument(_Org, Base):
    __tablename__ = "protocol_document"
    protocol_id: Mapped[str] = mapped_column(ID, unique=True)
    payload_json: Mapped[str] = mapped_column(Text)
    pdf: Mapped[bytes] = mapped_column(LargeBinary)
    __table_args__ = (_org_unique(), _org_fk(["protocol_id"], "protocol"))


class AuditEvent(_Org, Base):
    __tablename__ = "audit_event"
    device_id: Mapped[str] = mapped_column(ID)
    seq: Mapped[int] = mapped_column(BigInteger)
    prev_hash: Mapped[str] = mapped_column(String(64))
    event_hash: Mapped[str] = mapped_column(String(64), unique=True)
    actor_id: Mapped[str] = mapped_column(ID)
    event_type: Mapped[str] = mapped_column(String(64))
    entity_id: Mapped[str | None] = mapped_column(Text)
    payload_hash: Mapped[str] = mapped_column(String(64))
    device_sig: Mapped[str] = mapped_column(Text)
    sig_alg: Mapped[str] = mapped_column(String(32))
    event_at: Mapped[str] = mapped_column(String(24))
    __table_args__ = (
        _org_unique(),
        UniqueConstraint("device_id", "seq"),
        _org_fk(["device_id"], "device"),
        _org_fk(["actor_id"], "app_user"),
    )


class IsolationPlan(_Org, _SoftDelete, Base):
    __tablename__ = "isolation_plan"
    site_id: Mapped[str] = mapped_column(ID)
    target_node_ids: Mapped[list[Any]]
    solver_version: Mapped[str] = mapped_column(Text)
    graph_snapshot_hash: Mapped[str] = mapped_column(String(64))
    steps: Mapped[list[Any]]
    warnings: Mapped[list[Any]]
    status: Mapped[str] = mapped_column(String(16))
    approved_by: Mapped[str | None] = mapped_column(ID)
    __table_args__ = (
        _org_unique(),
        _org_fk(["site_id"], "site"),
        _org_fk(["approved_by"], "app_user"),
        CheckConstraint(_in("status", ("DRAFT", "APPROVED", "EXECUTED", "CANCELLED", "STALE")), name="plan_status"),
    )


class NormSet(_Org, _SoftDelete, Base):
    __tablename__ = "norm_set"
    version: Mapped[str] = mapped_column(Text)
    sha256: Mapped[str] = mapped_column(String(64))
    yaml: Mapped[str] = mapped_column(Text)
    reviewed_by: Mapped[str | None] = mapped_column(Text)
    reviewed_at: Mapped[str | None] = mapped_column(Text)
    __table_args__ = (
        _org_unique(),
        UniqueConstraint("org_id", "version"),
        ForeignKeyConstraint(["org_id"], ["organization.id"]),
    )


class OrgSetting(_Org, Base):
    __tablename__ = "org_setting"
    k_corr: Mapped[float] = mapped_column(Float, default=1.0)
    margin_pct: Mapped[float] = mapped_column(Float, default=0.0)
    active_norm_set_version: Mapped[str | None] = mapped_column(Text)
    __table_args__ = (
        UniqueConstraint("org_id"),
        ForeignKeyConstraint(["org_id"], ["organization.id"]),
        CheckConstraint("k_corr > 0 AND k_corr <= 1", name="k_corr"),
        CheckConstraint("margin_pct >= 0 AND margin_pct <= 50", name="margin"),
    )


# --- Faqat serverda ---


class RefreshToken(Base):
    """Refresh token (faqat SHA-256 hash'i). Rotatsiya: har safar yangisi; eskisi qayta kelsa — oila bekor."""

    __tablename__ = "refresh_token"
    id: Mapped[str] = mapped_column(ID, primary_key=True)
    org_id: Mapped[str] = mapped_column(ID)
    user_id: Mapped[str] = mapped_column(ID)
    family_id: Mapped[str] = mapped_column(ID, index=True)
    token_hash: Mapped[str] = mapped_column(String(64), unique=True)
    issued_at: Mapped[datetime]
    expires_at: Mapped[datetime]
    used_at: Mapped[datetime | None]
    revoked_at: Mapped[datetime | None]
    __table_args__ = (_org_fk(["user_id"], "app_user"),)


class Invite(Base):
    """Taklif kodi (faqat hash'i saqlanadi), bir martalik, muddatli."""

    __tablename__ = "invite"
    id: Mapped[str] = mapped_column(ID, primary_key=True)
    org_id: Mapped[str] = mapped_column(ID)
    code_hash: Mapped[str] = mapped_column(String(64), unique=True)
    role: Mapped[str] = mapped_column(String(16))
    created_by: Mapped[str] = mapped_column(ID)
    created_at: Mapped[datetime]
    expires_at: Mapped[datetime]
    used_at: Mapped[datetime | None]
    used_by: Mapped[str | None] = mapped_column(ID)
    __table_args__ = (
        _org_fk(["created_by"], "app_user"),
        CheckConstraint(_in("role", ROLES), name="invite_role"),
    )


class SyncOp(Base):
    """`POST /sync/push` idempotentligi: qabul qilingan `client_op_id` lar."""

    __tablename__ = "sync_op"
    org_id: Mapped[str] = mapped_column(ID, primary_key=True)
    client_op_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    received_at: Mapped[datetime]
    status: Mapped[str] = mapped_column(String(16))


class OrgSyncRev(Base):
    """Tashkilot bo'yicha `server_rev` hisoblagichi (faqat trigger funksiyasi yozadi)."""

    __tablename__ = "org_sync_rev"
    org_id: Mapped[str] = mapped_column(ID, primary_key=True)
    rev: Mapped[int] = mapped_column(BigInteger, default=0)


# Sinxronlanadigan jadvallar (pull tartibi — ota jadvallar birinchi).
SYNC_MODELS: dict[str, type[Base]] = {
    m.__tablename__: m
    for m in (
        Organization,
        AppUser,
        Device,
        Instrument,
        Site,
        Node,
        Edge,
        MeasurementSession,
        Measurement,
        Protocol,
        ProtocolDocument,
        AuditEvent,
        IsolationPlan,
        NormSet,
        OrgSetting,
    )
}
for _name, _model in SYNC_MODELS.items():
    Index(
        f"{_name}_org_rev_idx",
        _model.__table__.c["id" if _name == "organization" else "org_id"],
        _model.__table__.c.server_rev,
    )

APPEND_ONLY = ("measurement", "protocol", "protocol_document", "audit_event")
ORG_SCOPED = (*(t for t in SYNC_MODELS if t != "organization"), "refresh_token", "invite", "sync_op")
