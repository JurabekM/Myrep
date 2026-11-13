"""Kassa: smena, savdo, savdo qatorlari va to'lovlar (RLS bilan)

Revision ID: 0003_sales
Revises: 0002_catalog_stock
Create Date: 2026-10-10
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0003_sales"
down_revision: str | None = "0002_catalog_stock"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

TENANT_OK = "tenant_id = nullif(current_setting('app.tenant_id', true), '')::uuid"
TENANT_TABLES = ("shifts", "sales", "sale_items", "payments")


def upgrade() -> None:
    op.execute("CREATE SEQUENCE IF NOT EXISTS sale_number_seq START 1000")
    # Ilova roli chek raqamini olish uchun ketma-ketlikdan foydalanishi kerak
    op.execute("GRANT USAGE, SELECT ON SEQUENCE sale_number_seq TO omborai_app")

    op.create_table(
        "shifts",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("tenant_id", sa.Uuid(), nullable=False),
        sa.Column("store_id", sa.Uuid(), nullable=False),
        sa.Column("opened_by", sa.Uuid(), nullable=False),
        sa.Column("closed_by", sa.Uuid(), nullable=True),
        sa.Column("opened_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("closed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("opening_cash", sa.BigInteger(), server_default="0", nullable=False),
        sa.Column("closing_cash", sa.BigInteger(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("version", sa.Integer(), server_default="1", nullable=False),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"]),
        sa.ForeignKeyConstraint(["store_id"], ["stores.id"]),
        sa.ForeignKeyConstraint(["opened_by"], ["users.id"]),
        sa.ForeignKeyConstraint(["closed_by"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_shifts_tenant_id"), "shifts", ["tenant_id"])
    op.create_index(
        "uq_open_shift_per_store",
        "shifts",
        ["store_id"],
        unique=True,
        postgresql_where=sa.text("closed_at IS NULL"),
    )

    op.create_table(
        "sales",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("tenant_id", sa.Uuid(), nullable=False),
        sa.Column("store_id", sa.Uuid(), nullable=False),
        sa.Column("shift_id", sa.Uuid(), nullable=False),
        sa.Column(
            "number", sa.BigInteger(), server_default=sa.text("nextval('sale_number_seq')"), nullable=False
        ),
        sa.Column("status", sa.String(length=20), server_default="completed", nullable=False),
        sa.Column("subtotal", sa.BigInteger(), nullable=False),
        sa.Column("discount", sa.BigInteger(), server_default="0", nullable=False),
        sa.Column("total", sa.BigInteger(), nullable=False),
        sa.Column("created_by", sa.Uuid(), nullable=False),
        sa.Column("client_created_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"]),
        sa.ForeignKeyConstraint(["store_id"], ["stores.id"]),
        sa.ForeignKeyConstraint(["shift_id"], ["shifts.id"]),
        sa.ForeignKeyConstraint(["created_by"], ["users.id"]),
        sa.CheckConstraint("status IN ('completed', 'refunded')", name="ck_sale_status"),
        sa.CheckConstraint("total >= 0", name="ck_sale_total"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_sales_tenant_id"), "sales", ["tenant_id"])
    op.create_index(op.f("ix_sales_store_id"), "sales", ["store_id"])
    op.create_index(op.f("ix_sales_shift_id"), "sales", ["shift_id"])

    op.create_table(
        "sale_items",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("tenant_id", sa.Uuid(), nullable=False),
        sa.Column("sale_id", sa.Uuid(), nullable=False),
        sa.Column("product_id", sa.Uuid(), nullable=False),
        sa.Column("product_name", sa.String(length=200), nullable=False),
        sa.Column("unit", sa.String(length=10), nullable=False),
        sa.Column("qty", sa.Numeric(14, 3), nullable=False),
        sa.Column("unit_price", sa.BigInteger(), nullable=False),
        sa.Column("line_total", sa.BigInteger(), nullable=False),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"]),
        sa.ForeignKeyConstraint(["sale_id"], ["sales.id"]),
        sa.ForeignKeyConstraint(["product_id"], ["products.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_sale_items_tenant_id"), "sale_items", ["tenant_id"])
    op.create_index(op.f("ix_sale_items_sale_id"), "sale_items", ["sale_id"])

    op.create_table(
        "payments",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("tenant_id", sa.Uuid(), nullable=False),
        sa.Column("sale_id", sa.Uuid(), nullable=False),
        sa.Column("method", sa.String(length=20), nullable=False),
        sa.Column("amount", sa.BigInteger(), nullable=False),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"]),
        sa.ForeignKeyConstraint(["sale_id"], ["sales.id"]),
        sa.CheckConstraint("method IN ('cash', 'card', 'click', 'payme')", name="ck_payment_method"),
        sa.CheckConstraint("amount > 0", name="ck_payment_amount"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_payments_tenant_id"), "payments", ["tenant_id"])
    op.create_index(op.f("ix_payments_sale_id"), "payments", ["sale_id"])

    for table in TENANT_TABLES:
        op.execute(f"ALTER TABLE {table} ENABLE ROW LEVEL SECURITY")
        op.execute(f"CREATE POLICY tenant_isolation ON {table} USING ({TENANT_OK}) WITH CHECK ({TENANT_OK})")


def downgrade() -> None:
    for table in reversed(TENANT_TABLES):
        op.execute(f"DROP POLICY IF EXISTS tenant_isolation ON {table}")
    op.drop_table("payments")
    op.drop_table("sale_items")
    op.drop_table("sales")
    op.drop_table("shifts")
    op.execute("DROP SEQUENCE IF EXISTS sale_number_seq")
