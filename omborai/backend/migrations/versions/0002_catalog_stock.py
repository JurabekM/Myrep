"""Katalog, yetkazuvchilar, kirim va qoldiq ledger'i (RLS bilan)

Revision ID: 0002_catalog_stock
Revises: 0001_init
Create Date: 2026-10-10
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0002_catalog_stock"
down_revision: str | None = "0001_init"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

APP_ROLE = "omborai_app"
TENANT_TABLES = (
    "categories",
    "products",
    "product_barcodes",
    "suppliers",
    "purchases",
    "purchase_items",
    "stock_movements",
)
TENANT_OK = "tenant_id = nullif(current_setting('app.tenant_id', true), '')::uuid"


def _audit() -> list[sa.Column]:
    return [
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("version", sa.Integer(), server_default="1", nullable=False),
    ]


def _tenant_fk() -> sa.ForeignKeyConstraint:
    return sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"])


def upgrade() -> None:
    op.create_table(
        "categories",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("tenant_id", sa.Uuid(), nullable=False),
        sa.Column("name", sa.String(length=120), nullable=False),
        *_audit(),
        _tenant_fk(),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("tenant_id", "name", name="uq_category_name"),
    )
    op.create_index(op.f("ix_categories_tenant_id"), "categories", ["tenant_id"])

    op.create_table(
        "products",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("tenant_id", sa.Uuid(), nullable=False),
        sa.Column("category_id", sa.Uuid(), nullable=True),
        sa.Column("name", sa.String(length=200), nullable=False),
        sa.Column("unit", sa.String(length=10), server_default="dona", nullable=False),
        sa.Column("sale_price", sa.BigInteger(), server_default="0", nullable=False),
        sa.Column("cost_price", sa.BigInteger(), server_default="0", nullable=False),
        sa.Column("min_stock", sa.Numeric(14, 3), server_default="0", nullable=False),
        sa.Column("is_active", sa.Boolean(), server_default="true", nullable=False),
        *_audit(),
        _tenant_fk(),
        sa.ForeignKeyConstraint(["category_id"], ["categories.id"]),
        sa.CheckConstraint("sale_price >= 0", name="ck_product_sale_price"),
        sa.CheckConstraint("cost_price >= 0", name="ck_product_cost_price"),
        sa.CheckConstraint("min_stock >= 0", name="ck_product_min_stock"),
        sa.CheckConstraint("unit IN ('dona', 'kg', 'litr', 'metr', 'quti', 'paket')", name="ck_product_unit"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_products_tenant_id"), "products", ["tenant_id"])

    op.create_table(
        "product_barcodes",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("tenant_id", sa.Uuid(), nullable=False),
        sa.Column("product_id", sa.Uuid(), nullable=False),
        sa.Column("barcode", sa.String(length=64), nullable=False),
        *_audit(),
        _tenant_fk(),
        sa.ForeignKeyConstraint(["product_id"], ["products.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("tenant_id", "barcode", name="uq_barcode_per_tenant"),
    )
    op.create_index(op.f("ix_product_barcodes_tenant_id"), "product_barcodes", ["tenant_id"])
    op.create_index(op.f("ix_product_barcodes_product_id"), "product_barcodes", ["product_id"])

    op.create_table(
        "suppliers",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("tenant_id", sa.Uuid(), nullable=False),
        sa.Column("name", sa.String(length=200), nullable=False),
        sa.Column("phone", sa.String(length=32), nullable=True),
        *_audit(),
        _tenant_fk(),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_suppliers_tenant_id"), "suppliers", ["tenant_id"])

    op.create_table(
        "purchases",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("tenant_id", sa.Uuid(), nullable=False),
        sa.Column("store_id", sa.Uuid(), nullable=False),
        sa.Column("supplier_id", sa.Uuid(), nullable=True),
        sa.Column("created_by", sa.Uuid(), nullable=False),
        sa.Column("note", sa.String(length=300), nullable=True),
        sa.Column("total_cost", sa.BigInteger(), server_default="0", nullable=False),
        *_audit(),
        _tenant_fk(),
        sa.ForeignKeyConstraint(["store_id"], ["stores.id"]),
        sa.ForeignKeyConstraint(["supplier_id"], ["suppliers.id"]),
        sa.ForeignKeyConstraint(["created_by"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_purchases_tenant_id"), "purchases", ["tenant_id"])
    op.create_index(op.f("ix_purchases_store_id"), "purchases", ["store_id"])

    op.create_table(
        "purchase_items",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("tenant_id", sa.Uuid(), nullable=False),
        sa.Column("purchase_id", sa.Uuid(), nullable=False),
        sa.Column("product_id", sa.Uuid(), nullable=False),
        sa.Column("qty", sa.Numeric(14, 3), nullable=False),
        sa.Column("unit_cost", sa.BigInteger(), nullable=False),
        _tenant_fk(),
        sa.ForeignKeyConstraint(["purchase_id"], ["purchases.id"]),
        sa.ForeignKeyConstraint(["product_id"], ["products.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_purchase_items_tenant_id"), "purchase_items", ["tenant_id"])
    op.create_index(op.f("ix_purchase_items_purchase_id"), "purchase_items", ["purchase_id"])

    op.create_table(
        "stock_movements",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("tenant_id", sa.Uuid(), nullable=False),
        sa.Column("store_id", sa.Uuid(), nullable=False),
        sa.Column("product_id", sa.Uuid(), nullable=False),
        sa.Column("qty", sa.Numeric(14, 3), nullable=False),
        sa.Column("kind", sa.String(length=20), nullable=False),
        sa.Column("reference_type", sa.String(length=30), nullable=True),
        sa.Column("reference_id", sa.Uuid(), nullable=True),
        sa.Column("note", sa.String(length=300), nullable=True),
        sa.Column("created_by", sa.Uuid(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        _tenant_fk(),
        sa.ForeignKeyConstraint(["store_id"], ["stores.id"]),
        sa.ForeignKeyConstraint(["product_id"], ["products.id"]),
        sa.ForeignKeyConstraint(["created_by"], ["users.id"]),
        sa.CheckConstraint(
            "kind IN ('receipt', 'sale', 'sale_return', 'adjustment', 'writeoff')", name="ck_movement_kind"
        ),
        sa.CheckConstraint("qty <> 0", name="ck_movement_qty_nonzero"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_stock_movements_tenant_id"), "stock_movements", ["tenant_id"])
    op.create_index("ix_stock_movements_store_product", "stock_movements", ["store_id", "product_id"])

    # Har bir tenant jadvaliga RLS (ilova roli uchun har doim tenant filtri qo'llanadi)
    for table in TENANT_TABLES:
        op.execute(f"ALTER TABLE {table} ENABLE ROW LEVEL SECURITY")
        op.execute(f"CREATE POLICY tenant_isolation ON {table} USING ({TENANT_OK}) WITH CHECK ({TENANT_OK})")

    # Ledger o'zgarmas: ilova roli harakatni o'zgartira yoki o'chira olmaydi
    op.execute(f"REVOKE UPDATE, DELETE ON stock_movements FROM {APP_ROLE}")


def downgrade() -> None:
    for table in reversed(TENANT_TABLES):
        op.execute(f"DROP POLICY IF EXISTS tenant_isolation ON {table}")
    op.drop_table("stock_movements")
    op.drop_table("purchase_items")
    op.drop_table("purchases")
    op.drop_table("suppliers")
    op.drop_table("product_barcodes")
    op.drop_table("products")
    op.drop_table("categories")
