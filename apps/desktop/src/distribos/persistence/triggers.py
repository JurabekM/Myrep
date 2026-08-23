"""Baza darajasidagi o'zgarmaslik qulflari (SQLite TRIGGER).

Nega ORM qoidasi yetmaydi: ORM'ni chetlab o'tish oson — xom SQL, boshqa
dastur, yoki DB Browser bilan faylni ochish. Audit jurnali va hodisa
jurnali «append-only» deyilsa, buni **baza** majburlashi kerak, kod emas.

Bu trigger'lar `RAISE(ABORT, ...)` bilan ishlaydi: UPDATE/DELETE urinishi
tranzaksiyani butunlay bekor qiladi.
"""

from __future__ import annotations

from sqlalchemy import Engine, text

#: Har biri (nom, SQL). Nom `DROP TRIGGER IF EXISTS` uchun kerak.
IMMUTABILITY_TRIGGERS: tuple[tuple[str, str], ...] = (
    (
        "trg_audit_log_no_update",
        """
        CREATE TRIGGER trg_audit_log_no_update
        BEFORE UPDATE ON audit_log
        BEGIN
            SELECT RAISE(ABORT, 'audit_log append-only: UPDATE taqiqlanadi');
        END
        """,
    ),
    (
        "trg_audit_log_no_delete",
        """
        CREATE TRIGGER trg_audit_log_no_delete
        BEFORE DELETE ON audit_log
        BEGIN
            SELECT RAISE(ABORT, 'audit_log append-only: DELETE taqiqlanadi');
        END
        """,
    ),
    (
        "trg_event_log_no_delete",
        """
        CREATE TRIGGER trg_event_log_no_delete
        BEFORE DELETE ON event_log
        BEGIN
            SELECT RAISE(ABORT, 'event_log append-only: DELETE taqiqlanadi');
        END
        """,
    ),
    (
        # Hodisaning O'ZI o'zgarmas. Faqat `applied_at` (proyektor belgisi)
        # yangilanishi mumkin — qolgan har qanday maydon o'zgarsa, bu
        # tarixni qayta yozish demakdir.
        "trg_event_log_immutable_fields",
        """
        CREATE TRIGGER trg_event_log_immutable_fields
        BEFORE UPDATE ON event_log
        WHEN OLD.event_id       IS NOT NEW.event_id
          OR OLD.event_type     IS NOT NEW.event_type
          OR OLD.payload        IS NOT NEW.payload
          OR OLD.device_id      IS NOT NEW.device_id
          OR OLD.device_sequence IS NOT NEW.device_sequence
          OR OLD.occurred_at    IS NOT NEW.occurred_at
          OR OLD.aggregate_id   IS NOT NEW.aggregate_id
          OR OLD.tenant_id      IS NOT NEW.tenant_id
        BEGIN
            SELECT RAISE(ABORT, 'event_log o''zgarmas: faqat applied_at yangilanadi');
        END
        """,
    ),
    (
        # Ombor harakati append-only — qoldiq shundan hisoblanadi (§13).
        "trg_inv_movement_no_update",
        """
        CREATE TRIGGER trg_inv_movement_no_update
        BEFORE UPDATE ON inv_movement
        BEGIN
            SELECT RAISE(ABORT, 'inv_movement append-only: tuzatish uchun yangi harakat yarating');
        END
        """,
    ),
    (
        "trg_inv_movement_no_delete",
        """
        CREATE TRIGGER trg_inv_movement_no_delete
        BEFORE DELETE ON inv_movement
        BEGIN
            SELECT RAISE(ABORT, 'inv_movement append-only: DELETE taqiqlanadi');
        END
        """,
    ),
    (
        # To'lov o'chirilmaydi va summasi o'zgarmaydi — faqat reversal (§13).
        # `is_reversed` bayrog'ini qo'yishga ruxsat beriladi.
        "trg_payment_immutable_amount",
        """
        CREATE TRIGGER trg_payment_immutable_amount
        BEFORE UPDATE ON fin_payment
        WHEN OLD.amount      IS NOT NEW.amount
          OR OLD.direction   IS NOT NEW.direction
          OR OLD.customer_id IS NOT NEW.customer_id
          OR OLD.occurred_at IS NOT NEW.occurred_at
        BEGIN
            SELECT RAISE(ABORT, 'to''lov o''zgarmas: bekor qilish uchun reversal yozuvi yarating');
        END
        """,
    ),
    (
        "trg_payment_no_delete",
        """
        CREATE TRIGGER trg_payment_no_delete
        BEFORE DELETE ON fin_payment
        BEGIN
            SELECT RAISE(ABORT, 'to''lov o''chirilmaydi: reversal yozuvi yarating');
        END
        """,
    ),
)


def install_triggers(engine: Engine) -> None:
    """Trigger'larni o'rnatadi (idempotent)."""
    with engine.begin() as connection:
        for name, ddl in IMMUTABILITY_TRIGGERS:
            connection.execute(text(f"DROP TRIGGER IF EXISTS {name}"))
            connection.execute(text(ddl.strip()))


def installed_triggers(engine: Engine) -> set[str]:
    """Bazada haqiqatan mavjud trigger nomlari (diagnostika va test uchun)."""
    with engine.connect() as connection:
        rows = connection.execute(
            text("SELECT name FROM sqlite_master WHERE type = 'trigger'")
        ).scalars()
        return set(rows)
