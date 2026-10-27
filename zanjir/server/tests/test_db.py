"""Migratsiya, RLS, append-only triggerlar va `server_rev` — to'g'ridan-to'g'ri baza darajasida."""

from __future__ import annotations

import uuid
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from datetime import UTC, datetime

import pytest
from alembic.autogenerate import compare_metadata
from alembic.migration import MigrationContext
from sqlalchemy import Connection, text
from sqlalchemy.exc import DBAPIError
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine

from tests.conftest import migrate
from zanjir_server.db.models import APPEND_ONLY, ORG_SCOPED, SYNC_MODELS, Base
from zanjir_server.db.session import Database

NOW = datetime(2026, 10, 27, tzinfo=UTC)


@asynccontextmanager
async def owner_session(db: Database) -> AsyncIterator[AsyncSession]:
    """Jadval egasi sifatida (faqat test ma'lumotini tayyorlash va trigger tekshiruvi uchun)."""
    async with AsyncSession(db.engine) as s, s.begin():
        yield s


@pytest.fixture
async def db(pg_url: str) -> AsyncIterator[Database]:
    d = Database(pg_url)
    yield d
    await d.dispose()


async def seed_org(db: Database) -> tuple[str, str]:
    """Tashkilot + foydalanuvchi + obyekt (tizim sessiyasi orqali)."""
    org, user = str(uuid.uuid4()), str(uuid.uuid4())
    async with owner_session(db) as s:
        p = {"org": org, "user": user, "now": NOW, "phone": "+998" + str(uuid.uuid4().int)[:9]}
        await s.execute(
            text(
                "INSERT INTO organization (id, name, created_at, updated_at, rev, server_rev, deleted) "
                "VALUES (:org, 'Lab', :now, :now, 1, 0, false)"
            ),
            p,
        )
        await s.execute(
            text(
                "INSERT INTO app_user (id, org_id, full_name, phone, password_hash, role, created_at, updated_at, rev, "
                "server_rev, deleted) VALUES (:user, :org, 'F', :phone, 'x', 'LEAD', :now, :now, 1, 0, false)"
            ),
            p,
        )
        await s.execute(
            text(
                "INSERT INTO site (id, org_id, name, created_at, updated_at, rev, server_rev, deleted) "
                "VALUES (gen_random_uuid()::text, :org, 'Obyekt', :now, :now, 1, 0, false)"
            ),
            p,
        )
    return org, user


def test_models_match_migrations(pg_url: str) -> None:
    import asyncio

    async def diff() -> list[object]:
        engine = create_async_engine(pg_url)

        def cmp(conn: Connection) -> list[object]:
            return list(compare_metadata(MigrationContext.configure(conn), Base.metadata))

        async with engine.connect() as c:
            out = await c.run_sync(cmp)
        await engine.dispose()
        return out

    assert asyncio.run(diff()) == []


def test_downgrade_and_upgrade_again(pg_url: str) -> None:
    """Toza bazada: head → base → head."""
    import asyncio

    name = "mig_" + uuid.uuid4().hex[:8]

    async def admin(sql: str) -> None:
        engine = create_async_engine(pg_url, isolation_level="AUTOCOMMIT")
        async with engine.connect() as c:
            await c.execute(text(sql))
        await engine.dispose()

    asyncio.run(admin(f"CREATE DATABASE {name}"))
    url = pg_url.rsplit("/", 1)[0] + "/" + name
    try:
        migrate(url)
        migrate(url, "base", down=True)
        migrate(url)
    finally:
        asyncio.run(admin(f"DROP DATABASE {name} WITH (FORCE)"))


async def test_lookup_functions_return_only_org(db: Database, app_url: str) -> None:
    """Ilova roli jadvallarni RLS'siz o'qiy olmaydi; tashkilotni faqat aniq kalit bo'yicha topadi."""
    org, _ = await seed_org(db)
    async with owner_session(db) as s:
        phone = str((await s.execute(text("SELECT phone FROM app_user WHERE org_id = :o"), {"o": org})).scalar())
    app_db = Database(app_url)
    try:
        assert await app_db.lookup_org("zanjir_org_of_phone", phone) == org
        assert await app_db.lookup_org("zanjir_org_of_phone", "+998000000000") is None
        assert await app_db.lookup_org("zanjir_org_of_qr", "%") is None
        # `app.org_id` siz: RLS hech narsa ko'rsatmaydi; hisoblagich jadvaliga huquq yo'q.
        async with AsyncSession(app_db.engine) as s, s.begin():
            assert (await s.execute(text("SELECT count(*) FROM app_user"))).scalar() == 0
        with pytest.raises(DBAPIError):
            async with AsyncSession(app_db.engine) as s, s.begin():
                await s.execute(text("SELECT count(*) FROM org_sync_rev"))
        async with app_db.org_session(org) as s:
            assert (await s.execute(text("SELECT count(*) FROM app_user"))).scalar() == 1
    finally:
        await app_db.dispose()


async def test_rls_enabled_and_app_role(db: Database) -> None:
    org, _ = await seed_org(db)
    async with db.org_session(org) as s:
        assert (await s.execute(text("SELECT current_user"))).scalar() == "zanjir_app"
        assert (
            await s.execute(text("SELECT rolbypassrls OR rolsuper FROM pg_roles WHERE rolname = current_user"))
        ).scalar() is False
    async with owner_session(db) as s:
        rows = (
            await s.execute(
                text("SELECT relname, relrowsecurity FROM pg_class WHERE relname = ANY(:t)"),
                {"t": [*ORG_SCOPED, "organization"]},
            )
        ).all()
    assert {r[0] for r in rows} == {*ORG_SCOPED, "organization"}
    assert all(r[1] for r in rows)


async def test_rls_isolates_every_table(db: Database) -> None:
    a, _ = await seed_org(db)
    b, _ = await seed_org(db)
    async with db.org_session(a) as s:
        # WHERE yo'q — faqat RLS: boshqa tashkilot qatorlari ko'rinmaydi.
        for table in [*SYNC_MODELS, "refresh_token", "invite", "sync_op"]:
            key = "id" if table == "organization" else "org_id"
            seen = (await s.execute(text(f"SELECT DISTINCT {key} FROM {table}"))).scalars().all()
            assert set(seen) <= {a}, table
        assert (await s.execute(text("SELECT count(*) FROM site"))).scalar() == 1
    with pytest.raises(DBAPIError):
        async with db.org_session(a) as s:
            await s.execute(
                text(
                    "INSERT INTO site (id, org_id, name, created_at, updated_at, rev, server_rev, deleted) "
                    "VALUES (gen_random_uuid()::text, :b, 'X', now(), now(), 1, 0, false)"
                ),
                {"b": b},
            )
    with pytest.raises(DBAPIError):
        async with db.org_session(a) as s:
            await s.execute(text("UPDATE site SET org_id = :b"), {"b": b})
    async with db.org_session(a) as s:
        assert (await s.execute(text("UPDATE site SET name = 'Y' WHERE org_id = :b"), {"b": b})).rowcount == 0  # type: ignore[attr-defined]
    # Ilova roli o'chira olmaydi (soft delete), hisoblagich jadvaliga kira olmaydi.
    for sql in ("DELETE FROM site", "SELECT * FROM org_sync_rev"):
        with pytest.raises(DBAPIError):
            async with db.org_session(a) as s:
                await s.execute(text(sql))


async def test_cross_org_reference_rejected(db: Database) -> None:
    """Kompozit FK: A tashkilotining tuguni B obyektiga havola qila olmaydi (hatto egasi sifatida ham)."""
    a, _ = await seed_org(db)
    b, _ = await seed_org(db)
    async with owner_session(db) as s:
        site_b = (await s.execute(text("SELECT id FROM site WHERE org_id = :b"), {"b": b})).scalar()
    with pytest.raises(DBAPIError):
        async with owner_session(db) as s:
            await s.execute(
                text(
                    "INSERT INTO node (id, org_id, site_id, kind, label, attrs, verified, created_at, "
                    "updated_at, rev, server_rev, deleted) VALUES (gen_random_uuid()::text, :a, :site, "
                    "'CABLE', 'W1', '{}', false, now(), now(), 1, 0, false)"
                ),
                {"a": a, "site": site_b},
            )


async def seed_append_only(db: Database) -> None:
    """Har bir append-only jadvalda kamida bitta qator (qator triggerlari bo'sh jadvalda ishlamaydi)."""
    org, user = await seed_org(db)
    c = "created_at, updated_at, rev, server_rev"
    v = ":now, :now, 1, 0"
    ids = {k: str(uuid.uuid4()) for k in ("dev", "ins", "node", "ses", "m", "p", "num", "qr", "doc", "ev")}
    p = {"org": org, "user": user, "now": NOW, **ids}
    async with owner_session(db) as s:
        site = (await s.execute(text("SELECT id FROM site WHERE org_id = :org"), p)).scalar()
        p["site"] = site
        for sql in (
            f"INSERT INTO device (id, org_id, user_id, public_key_ed25519, sig_alg, registered_at, deleted, {c}) "
            f"VALUES (:dev, :org, :user, repeat('a', 64), 'Ed25519', :now, false, {v})",
            f"INSERT INTO instrument (id, org_id, kind, model, serial_no, deleted, {c}) "
            f"VALUES (:ins, :org, 'K', 'M', 'S', false, {v})",
            f"INSERT INTO node (id, org_id, site_id, kind, label, attrs, verified, deleted, {c}) "
            f"VALUES (:node, :org, :site, 'CABLE', 'W1', '{{}}', false, false, {v})",
            f"INSERT INTO measurement_session (id, org_id, site_id, kind, engineer_id, started_at, deleted, {c}) "
            f"VALUES (:ses, :org, :site, 'DAVRIY', :user, :now, false, {v})",
            f"INSERT INTO measurement (id, org_id, session_id, node_id, type, instrument_id, values, entered_via, "
            f"verdict, norm_set_version, eval_detail, {c}) "
            f"VALUES (:m, :org, :ses, :node, 'CONTINUITY_BONDING', :ins, '{{}}', 'MANUAL', 'PASS', '0.1.1', '{{}}', "
            f"{v})",
            f"INSERT INTO protocol (id, org_id, session_id, number, payload_sha256, pdf_sha256, signed_by, device_id, "
            f"signature, sig_alg, qr_token, {c}) "
            f"VALUES (:p, :org, :ses, :num, 'a', 'b', :user, :dev, 's', 'Ed25519', :qr, {v})",
            f"INSERT INTO protocol_document (id, org_id, protocol_id, payload_json, pdf, {c}) "
            f"VALUES (:doc, :org, :p, '{{}}', '\\x00', {v})",
            f"INSERT INTO audit_event (id, org_id, device_id, seq, prev_hash, event_hash, actor_id, event_type, "
            f"payload_hash, device_sig, sig_alg, event_at, {c}) "
            f"VALUES (:ev, :org, :dev, 1, 'p', :qr, :user, 'X', 'h', 's', 'Ed25519', '2026', {v})",
        ):
            await s.execute(text(sql), p)


@pytest.mark.parametrize("table", APPEND_ONLY)
async def test_append_only_even_for_owner(db: Database, table: str) -> None:
    await seed_append_only(db)
    for sql in (f"UPDATE {table} SET rev = rev", f"DELETE FROM {table}", f"TRUNCATE {table} CASCADE"):
        with pytest.raises(DBAPIError, match="append_only"):
            async with owner_session(db) as s:
                await s.execute(text(sql))


async def test_server_rev_monotonic_per_org(db: Database) -> None:
    org, _ = await seed_org(db)
    async with db.org_session(org) as s:
        revs = (
            (
                await s.execute(
                    text(
                        "SELECT server_rev FROM organization UNION ALL SELECT server_rev FROM app_user "
                        "UNION ALL SELECT server_rev FROM site ORDER BY 1"
                    )
                )
            )
            .scalars()
            .all()
        )
        assert revs == [1, 2, 3]
        await s.execute(text("UPDATE site SET name = 'Z'"))
        assert (await s.execute(text("SELECT server_rev FROM site"))).scalar() == 4
