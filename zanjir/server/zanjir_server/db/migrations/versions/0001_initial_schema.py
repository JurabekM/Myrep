"""Boshlang'ich sxema: jadvallar, RLS, append-only va `server_rev` triggerlari, `zanjir_app` roli (ADR-0011).

Revision ID: 0001
Revises:
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "0001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "org_sync_rev",
        sa.Column("org_id", sa.String(length=36), nullable=False),
        sa.Column("rev", sa.BigInteger(), nullable=False),
        sa.PrimaryKeyConstraint("org_id"),
    )
    op.create_table(
        "organization",
        sa.Column("name", sa.Text(), nullable=False),
        sa.Column("license_no", sa.Text(), nullable=True),
        sa.Column("license_valid_until", sa.DateTime(timezone=True), nullable=True),
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("rev", sa.Integer(), nullable=False),
        sa.Column("server_rev", sa.BigInteger(), nullable=False),
        sa.Column("deleted", sa.Boolean(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_table(
        "sync_op",
        sa.Column("org_id", sa.String(length=36), nullable=False),
        sa.Column("client_op_id", sa.String(length=64), nullable=False),
        sa.Column("received_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("status", sa.String(length=16), nullable=False),
        sa.PrimaryKeyConstraint("org_id", "client_op_id"),
    )
    op.create_table(
        "app_user",
        sa.Column("full_name", sa.Text(), nullable=False),
        sa.Column("phone", sa.String(length=20), nullable=False),
        sa.Column("password_hash", sa.Text(), nullable=False),
        sa.Column("role", sa.String(length=16), nullable=False),
        sa.Column("safety_group", sa.String(length=3), nullable=True),
        sa.Column("org_id", sa.String(length=36), nullable=False),
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("rev", sa.Integer(), nullable=False),
        sa.Column("server_rev", sa.BigInteger(), nullable=False),
        sa.Column("deleted", sa.Boolean(), nullable=False),
        sa.CheckConstraint("role IN ('ADMIN', 'LEAD', 'ENGINEER', 'VIEWER')", name="app_user_role"),
        sa.CheckConstraint("safety_group IS NULL OR safety_group IN ('I', 'II', 'III', 'IV', 'V')", name="sg"),
        sa.ForeignKeyConstraint(
            ["org_id"],
            ["organization.id"],
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("org_id", "id"),
        sa.UniqueConstraint("phone"),
    )
    op.create_table(
        "instrument",
        sa.Column("kind", sa.Text(), nullable=False),
        sa.Column("model", sa.Text(), nullable=False),
        sa.Column("serial_no", sa.Text(), nullable=False),
        sa.Column("verification_cert_no", sa.Text(), nullable=True),
        sa.Column("verified_until", sa.DateTime(timezone=True), nullable=True),
        sa.Column("org_id", sa.String(length=36), nullable=False),
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("rev", sa.Integer(), nullable=False),
        sa.Column("server_rev", sa.BigInteger(), nullable=False),
        sa.Column("deleted", sa.Boolean(), nullable=False),
        sa.ForeignKeyConstraint(
            ["org_id"],
            ["organization.id"],
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("org_id", "id"),
    )
    op.create_table(
        "norm_set",
        sa.Column("version", sa.Text(), nullable=False),
        sa.Column("sha256", sa.String(length=64), nullable=False),
        sa.Column("yaml", sa.Text(), nullable=False),
        sa.Column("reviewed_by", sa.Text(), nullable=True),
        sa.Column("reviewed_at", sa.Text(), nullable=True),
        sa.Column("org_id", sa.String(length=36), nullable=False),
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("rev", sa.Integer(), nullable=False),
        sa.Column("server_rev", sa.BigInteger(), nullable=False),
        sa.Column("deleted", sa.Boolean(), nullable=False),
        sa.ForeignKeyConstraint(
            ["org_id"],
            ["organization.id"],
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("org_id", "id"),
        sa.UniqueConstraint("org_id", "version"),
    )
    op.create_table(
        "org_setting",
        sa.Column("k_corr", sa.Float(), nullable=False),
        sa.Column("margin_pct", sa.Float(), nullable=False),
        sa.Column("active_norm_set_version", sa.Text(), nullable=True),
        sa.Column("org_id", sa.String(length=36), nullable=False),
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("rev", sa.Integer(), nullable=False),
        sa.Column("server_rev", sa.BigInteger(), nullable=False),
        sa.CheckConstraint("k_corr > 0 AND k_corr <= 1", name="k_corr"),
        sa.CheckConstraint("margin_pct >= 0 AND margin_pct <= 50", name="margin"),
        sa.ForeignKeyConstraint(
            ["org_id"],
            ["organization.id"],
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("org_id"),
    )
    op.create_table(
        "site",
        sa.Column("name", sa.Text(), nullable=False),
        sa.Column("address", sa.Text(), nullable=True),
        sa.Column("customer", sa.Text(), nullable=True),
        sa.Column("earthing_system", sa.String(length=8), nullable=True),
        sa.Column("u0_volts", sa.Float(), nullable=True),
        sa.Column("org_id", sa.String(length=36), nullable=False),
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("rev", sa.Integer(), nullable=False),
        sa.Column("server_rev", sa.BigInteger(), nullable=False),
        sa.Column("deleted", sa.Boolean(), nullable=False),
        sa.CheckConstraint(
            "earthing_system IS NULL OR earthing_system IN ('TN-C', 'TN-S', 'TN-C-S', 'TT', 'IT')", name="es"
        ),
        sa.ForeignKeyConstraint(
            ["org_id"],
            ["organization.id"],
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("org_id", "id"),
    )
    op.create_table(
        "device",
        sa.Column("user_id", sa.String(length=36), nullable=False),
        sa.Column("public_key_ed25519", sa.String(length=64), nullable=False),
        sa.Column("sig_alg", sa.String(length=32), nullable=False),
        sa.Column("registered_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("revoked_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("org_id", sa.String(length=36), nullable=False),
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("rev", sa.Integer(), nullable=False),
        sa.Column("server_rev", sa.BigInteger(), nullable=False),
        sa.Column("deleted", sa.Boolean(), nullable=False),
        sa.ForeignKeyConstraint(
            ["org_id", "user_id"], ["app_user.org_id", "app_user.id"], initially="DEFERRED", deferrable=True
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("org_id", "id"),
    )
    op.create_table(
        "invite",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("org_id", sa.String(length=36), nullable=False),
        sa.Column("code_hash", sa.String(length=64), nullable=False),
        sa.Column("role", sa.String(length=16), nullable=False),
        sa.Column("created_by", sa.String(length=36), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("used_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("used_by", sa.String(length=36), nullable=True),
        sa.CheckConstraint("role IN ('ADMIN', 'LEAD', 'ENGINEER', 'VIEWER')", name="invite_role"),
        sa.ForeignKeyConstraint(
            ["org_id", "created_by"], ["app_user.org_id", "app_user.id"], initially="DEFERRED", deferrable=True
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("code_hash"),
    )
    op.create_table(
        "isolation_plan",
        sa.Column("site_id", sa.String(length=36), nullable=False),
        sa.Column("target_node_ids", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("solver_version", sa.Text(), nullable=False),
        sa.Column("graph_snapshot_hash", sa.String(length=64), nullable=False),
        sa.Column("steps", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("warnings", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("status", sa.String(length=16), nullable=False),
        sa.Column("approved_by", sa.String(length=36), nullable=True),
        sa.Column("org_id", sa.String(length=36), nullable=False),
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("rev", sa.Integer(), nullable=False),
        sa.Column("server_rev", sa.BigInteger(), nullable=False),
        sa.Column("deleted", sa.Boolean(), nullable=False),
        sa.CheckConstraint("status IN ('DRAFT', 'APPROVED', 'EXECUTED', 'CANCELLED', 'STALE')", name="plan_status"),
        sa.ForeignKeyConstraint(
            ["org_id", "approved_by"], ["app_user.org_id", "app_user.id"], initially="DEFERRED", deferrable=True
        ),
        sa.ForeignKeyConstraint(
            ["org_id", "site_id"], ["site.org_id", "site.id"], initially="DEFERRED", deferrable=True
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("org_id", "id"),
    )
    op.create_table(
        "measurement_session",
        sa.Column("site_id", sa.String(length=36), nullable=False),
        sa.Column("kind", sa.String(length=24), nullable=False),
        sa.Column("engineer_id", sa.String(length=36), nullable=False),
        sa.Column("ambient_temp_c", sa.Float(), nullable=True),
        sa.Column("humidity_pct", sa.Float(), nullable=True),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("closed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("org_id", sa.String(length=36), nullable=False),
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("rev", sa.Integer(), nullable=False),
        sa.Column("server_rev", sa.BigInteger(), nullable=False),
        sa.Column("deleted", sa.Boolean(), nullable=False),
        sa.CheckConstraint("kind IN ('QABUL_TOPSHIRISH', 'DAVRIY', 'NAVBATDAN_TASHQARI')", name="session_kind"),
        sa.ForeignKeyConstraint(
            ["org_id", "engineer_id"], ["app_user.org_id", "app_user.id"], initially="DEFERRED", deferrable=True
        ),
        sa.ForeignKeyConstraint(
            ["org_id", "site_id"], ["site.org_id", "site.id"], initially="DEFERRED", deferrable=True
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("org_id", "id"),
    )
    op.create_table(
        "node",
        sa.Column("site_id", sa.String(length=36), nullable=False),
        sa.Column("kind", sa.String(length=32), nullable=False),
        sa.Column("label", sa.Text(), nullable=False),
        sa.Column("panel_id", sa.String(length=36), nullable=True),
        sa.Column("state", sa.String(length=8), nullable=True),
        sa.Column("attrs", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("verified", sa.Boolean(), nullable=False),
        sa.Column("x", sa.Float(), nullable=True),
        sa.Column("y", sa.Float(), nullable=True),
        sa.Column("org_id", sa.String(length=36), nullable=False),
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("rev", sa.Integer(), nullable=False),
        sa.Column("server_rev", sa.BigInteger(), nullable=False),
        sa.Column("deleted", sa.Boolean(), nullable=False),
        sa.CheckConstraint("state IS NULL OR state IN ('CLOSED', 'OPEN')", name="node_state"),
        sa.ForeignKeyConstraint(
            ["org_id", "panel_id"], ["node.org_id", "node.id"], initially="DEFERRED", deferrable=True
        ),
        sa.ForeignKeyConstraint(
            ["org_id", "site_id"], ["site.org_id", "site.id"], initially="DEFERRED", deferrable=True
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("org_id", "id"),
    )
    op.create_table(
        "refresh_token",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("org_id", sa.String(length=36), nullable=False),
        sa.Column("user_id", sa.String(length=36), nullable=False),
        sa.Column("family_id", sa.String(length=36), nullable=False),
        sa.Column("token_hash", sa.String(length=64), nullable=False),
        sa.Column("issued_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("used_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("revoked_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(
            ["org_id", "user_id"], ["app_user.org_id", "app_user.id"], initially="DEFERRED", deferrable=True
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("token_hash"),
    )
    op.create_index(op.f("ix_refresh_token_family_id"), "refresh_token", ["family_id"], unique=False)
    op.create_table(
        "audit_event",
        sa.Column("device_id", sa.String(length=36), nullable=False),
        sa.Column("seq", sa.BigInteger(), nullable=False),
        sa.Column("prev_hash", sa.String(length=64), nullable=False),
        sa.Column("event_hash", sa.String(length=64), nullable=False),
        sa.Column("actor_id", sa.String(length=36), nullable=False),
        sa.Column("event_type", sa.String(length=64), nullable=False),
        sa.Column("entity_id", sa.Text(), nullable=True),
        sa.Column("payload_hash", sa.String(length=64), nullable=False),
        sa.Column("device_sig", sa.Text(), nullable=False),
        sa.Column("sig_alg", sa.String(length=32), nullable=False),
        sa.Column("event_at", sa.String(length=24), nullable=False),
        sa.Column("org_id", sa.String(length=36), nullable=False),
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("rev", sa.Integer(), nullable=False),
        sa.Column("server_rev", sa.BigInteger(), nullable=False),
        sa.ForeignKeyConstraint(
            ["org_id", "actor_id"], ["app_user.org_id", "app_user.id"], initially="DEFERRED", deferrable=True
        ),
        sa.ForeignKeyConstraint(
            ["org_id", "device_id"], ["device.org_id", "device.id"], initially="DEFERRED", deferrable=True
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("device_id", "seq"),
        sa.UniqueConstraint("event_hash"),
        sa.UniqueConstraint("org_id", "id"),
    )
    op.create_table(
        "edge",
        sa.Column("site_id", sa.String(length=36), nullable=False),
        sa.Column("a_node_id", sa.String(length=36), nullable=False),
        sa.Column("b_node_id", sa.String(length=36), nullable=False),
        sa.Column("conductors", sa.Text(), nullable=False),
        sa.Column("org_id", sa.String(length=36), nullable=False),
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("rev", sa.Integer(), nullable=False),
        sa.Column("server_rev", sa.BigInteger(), nullable=False),
        sa.Column("deleted", sa.Boolean(), nullable=False),
        sa.ForeignKeyConstraint(
            ["org_id", "a_node_id"], ["node.org_id", "node.id"], initially="DEFERRED", deferrable=True
        ),
        sa.ForeignKeyConstraint(
            ["org_id", "b_node_id"], ["node.org_id", "node.id"], initially="DEFERRED", deferrable=True
        ),
        sa.ForeignKeyConstraint(
            ["org_id", "site_id"], ["site.org_id", "site.id"], initially="DEFERRED", deferrable=True
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("org_id", "id"),
    )
    op.create_table(
        "measurement",
        sa.Column("session_id", sa.String(length=36), nullable=False),
        sa.Column("node_id", sa.String(length=36), nullable=False),
        sa.Column("type", sa.String(length=24), nullable=False),
        sa.Column("instrument_id", sa.String(length=36), nullable=False),
        sa.Column("values", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("entered_via", sa.String(length=8), nullable=False),
        sa.Column("verdict", sa.String(length=16), nullable=False),
        sa.Column("norm_id", sa.Text(), nullable=True),
        sa.Column("norm_set_version", sa.Text(), nullable=False),
        sa.Column("eval_detail", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("supersedes_id", sa.String(length=36), nullable=True),
        sa.Column("org_id", sa.String(length=36), nullable=False),
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("rev", sa.Integer(), nullable=False),
        sa.Column("server_rev", sa.BigInteger(), nullable=False),
        sa.CheckConstraint("entered_via IN ('MANUAL', 'OCR', 'BT')", name="entered_via"),
        sa.CheckConstraint("verdict IN ('PASS', 'FAIL', 'NEEDS_REVIEW', 'NOT_APPLICABLE')", name="verdict"),
        sa.ForeignKeyConstraint(
            ["org_id", "instrument_id"], ["instrument.org_id", "instrument.id"], initially="DEFERRED", deferrable=True
        ),
        sa.ForeignKeyConstraint(
            ["org_id", "node_id"], ["node.org_id", "node.id"], initially="DEFERRED", deferrable=True
        ),
        sa.ForeignKeyConstraint(
            ["org_id", "session_id"],
            ["measurement_session.org_id", "measurement_session.id"],
            initially="DEFERRED",
            deferrable=True,
        ),
        sa.ForeignKeyConstraint(
            ["org_id", "supersedes_id"], ["measurement.org_id", "measurement.id"], initially="DEFERRED", deferrable=True
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("org_id", "id"),
        sa.UniqueConstraint("supersedes_id"),
    )
    op.create_table(
        "protocol",
        sa.Column("session_id", sa.String(length=36), nullable=False),
        sa.Column("number", sa.Text(), nullable=False),
        sa.Column("payload_sha256", sa.String(length=64), nullable=False),
        sa.Column("pdf_sha256", sa.String(length=64), nullable=False),
        sa.Column("signed_by", sa.String(length=36), nullable=False),
        sa.Column("device_id", sa.String(length=36), nullable=False),
        sa.Column("signature", sa.Text(), nullable=False),
        sa.Column("sig_alg", sa.String(length=32), nullable=False),
        sa.Column("qr_token", sa.String(length=64), nullable=False),
        sa.Column("org_id", sa.String(length=36), nullable=False),
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("rev", sa.Integer(), nullable=False),
        sa.Column("server_rev", sa.BigInteger(), nullable=False),
        sa.ForeignKeyConstraint(
            ["org_id", "device_id"], ["device.org_id", "device.id"], initially="DEFERRED", deferrable=True
        ),
        sa.ForeignKeyConstraint(
            ["org_id", "session_id"],
            ["measurement_session.org_id", "measurement_session.id"],
            initially="DEFERRED",
            deferrable=True,
        ),
        sa.ForeignKeyConstraint(
            ["org_id", "signed_by"], ["app_user.org_id", "app_user.id"], initially="DEFERRED", deferrable=True
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("org_id", "id"),
        sa.UniqueConstraint("org_id", "number"),
        sa.UniqueConstraint("qr_token"),
    )
    op.create_table(
        "protocol_document",
        sa.Column("protocol_id", sa.String(length=36), nullable=False),
        sa.Column("payload_json", sa.Text(), nullable=False),
        sa.Column("pdf", sa.LargeBinary(), nullable=False),
        sa.Column("org_id", sa.String(length=36), nullable=False),
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("rev", sa.Integer(), nullable=False),
        sa.Column("server_rev", sa.BigInteger(), nullable=False),
        sa.ForeignKeyConstraint(
            ["org_id", "protocol_id"], ["protocol.org_id", "protocol.id"], initially="DEFERRED", deferrable=True
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("org_id", "id"),
        sa.UniqueConstraint("protocol_id"),
    )
    _security()


# Migratsiya o'zgarmas bo'lishi uchun ro'yxatlar shu yerda (modeldan import qilinmaydi).
SYNC_TABLES = (
    "organization",
    "app_user",
    "device",
    "instrument",
    "site",
    "node",
    "edge",
    "measurement_session",
    "measurement",
    "protocol",
    "protocol_document",
    "audit_event",
    "isolation_plan",
    "norm_set",
    "org_setting",
)
APPEND_ONLY = ("measurement", "protocol", "protocol_document", "audit_event")
SERVER_ONLY = ("refresh_token", "invite", "sync_op")
LOOKUPS = (
    ("zanjir_org_of_phone", "app_user", "phone", "AND NOT deleted"),
    ("zanjir_org_of_refresh", "refresh_token", "token_hash", ""),
    ("zanjir_org_of_invite", "invite", "code_hash", ""),
    ("zanjir_org_of_qr", "protocol", "qr_token", ""),
)


def _security() -> None:
    # Ilova roli: RLS majburiy (NOSUPERUSER, NOBYPASSRLS). Har so'rov tranzaksiyasida `SET LOCAL ROLE zanjir_app`.
    op.execute(
        """
        DO $$ BEGIN
          IF NOT EXISTS (SELECT FROM pg_roles WHERE rolname = 'zanjir_app') THEN
            CREATE ROLE zanjir_app NOLOGIN NOSUPERUSER NOBYPASSRLS;
          END IF;
        END $$;
        """
    )
    op.execute("GRANT USAGE ON SCHEMA public TO zanjir_app")
    op.execute("GRANT zanjir_app TO CURRENT_USER")

    # server_rev: tashkilot hisoblagichi qatori yozish oxirigacha qulflanadi — bir tashkilot o'zgarishlari
    # commit tartibida raqamlanadi (pull hech narsani o'tkazib yubormaydi).
    op.execute(
        """
        CREATE FUNCTION zanjir_next_rev() RETURNS trigger LANGUAGE plpgsql
        SECURITY DEFINER SET search_path = public AS $$
        DECLARE org text;
        BEGIN
          IF TG_TABLE_NAME = 'organization' THEN org := NEW.id; ELSE org := NEW.org_id; END IF;
          INSERT INTO org_sync_rev (org_id, rev) VALUES (org, 1)
            ON CONFLICT (org_id) DO UPDATE SET rev = org_sync_rev.rev + 1
            RETURNING rev INTO NEW.server_rev;
          RETURN NEW;
        END $$;
        """
    )
    # Joriy tashkilot hisoblagichi (ilova roli `org_sync_rev` jadvalini to'g'ridan-to'g'ri o'qiy olmaydi).
    op.execute(
        """
        CREATE FUNCTION zanjir_org_rev() RETURNS bigint LANGUAGE sql STABLE
        SECURITY DEFINER SET search_path = public AS $$
          SELECT coalesce((SELECT rev FROM org_sync_rev WHERE org_id = current_setting('app.org_id', true)), 0)
        $$;
        """
    )
    # Tashkilot hali noma'lum bo'lgan yo'llar (kirish, refresh, taklif, ochiq tekshirish) uchun: aniq kalit bo'yicha
    # faqat `org_id` qaytaradi, keyingi hamma narsa RLS ostida (`org_session`). Ilova roli RLS'ni chetlab o'tmaydi.
    for fn, table, column, extra in LOOKUPS:
        op.execute(
            f"""
            CREATE FUNCTION {fn}(key text) RETURNS text LANGUAGE sql STABLE
            SECURITY DEFINER SET search_path = public AS $$
              SELECT org_id FROM {table} WHERE {column} = key {extra} LIMIT 1
            $$;
            """  # noqa: S608 — jadval/ustun nomlari shu fayldagi konstantalar
        )
        op.execute(f"REVOKE ALL ON FUNCTION {fn}(text) FROM PUBLIC")
        op.execute(f"GRANT EXECUTE ON FUNCTION {fn}(text) TO zanjir_app")
    op.execute("REVOKE ALL ON FUNCTION zanjir_org_rev() FROM PUBLIC")
    op.execute("GRANT EXECUTE ON FUNCTION zanjir_org_rev() TO zanjir_app")
    op.execute(
        """
        CREATE FUNCTION zanjir_append_only() RETURNS trigger LANGUAGE plpgsql AS $$
        BEGIN
          RAISE EXCEPTION 'append_only: %', TG_TABLE_NAME USING ERRCODE = 'restrict_violation';
        END $$;
        """
    )
    for t in SYNC_TABLES:
        op.execute(
            f"CREATE TRIGGER {t}_server_rev BEFORE INSERT OR UPDATE ON {t} FOR EACH ROW "
            "EXECUTE FUNCTION zanjir_next_rev()"
        )
        key = "id" if t == "organization" else "org_id"
        op.execute(f"CREATE INDEX {t}_org_rev_idx ON {t} ({key}, server_rev)")
    for t in APPEND_ONLY:
        # Nomi `_server_rev` dan oldin: UPDATE da avval shu trigger ishlaydi.
        op.execute(
            f"CREATE TRIGGER {t}_append_only BEFORE UPDATE OR DELETE ON {t} FOR EACH ROW "
            "EXECUTE FUNCTION zanjir_append_only()"
        )
        op.execute(
            f"CREATE TRIGGER {t}_append_only_truncate BEFORE TRUNCATE ON {t} FOR EACH STATEMENT "
            "EXECUTE FUNCTION zanjir_append_only()"
        )

    # RLS: faqat `app.org_id` tashkiloti. Jadval egasi (migratsiya roli) chetlab o'tadi — u faqat tizim yo'llarida
    # (kirish, refresh, ochiq tekshirish sahifasi) ishlatiladi.
    for t in (*SYNC_TABLES, *SERVER_ONLY):
        key = "id" if t == "organization" else "org_id"
        cond = f"{key} = current_setting('app.org_id', true)"
        op.execute(f"ALTER TABLE {t} ENABLE ROW LEVEL SECURITY")
        op.execute(f"CREATE POLICY {t}_org_isolation ON {t} USING ({cond}) WITH CHECK ({cond})")
        privileges = "SELECT, INSERT" if t in APPEND_ONLY else "SELECT, INSERT, UPDATE"
        op.execute(f"GRANT {privileges} ON {t} TO zanjir_app")


def downgrade() -> None:
    for fn in ("zanjir_append_only", "zanjir_next_rev", "zanjir_org_rev"):
        op.execute(f"DROP FUNCTION IF EXISTS {fn}() CASCADE")
    for fn, *_ in LOOKUPS:
        op.execute(f"DROP FUNCTION IF EXISTS {fn}(text)")
    op.drop_table("protocol_document")
    op.drop_table("protocol")
    op.drop_table("measurement")
    op.drop_table("edge")
    op.drop_table("audit_event")
    op.drop_index(op.f("ix_refresh_token_family_id"), table_name="refresh_token")
    op.drop_table("refresh_token")
    op.drop_table("node")
    op.drop_table("measurement_session")
    op.drop_table("isolation_plan")
    op.drop_table("invite")
    op.drop_table("device")
    op.drop_table("site")
    op.drop_table("org_setting")
    op.drop_table("norm_set")
    op.drop_table("instrument")
    op.drop_table("app_user")
    op.drop_table("sync_op")
    op.drop_table("organization")
    op.drop_table("org_sync_rev")
