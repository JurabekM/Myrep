"""Offline sinxronizatsiya: sales.updated_at, sync_ops va pull uchun indekslar (RLS bilan)

Revision ID: 0004_sync
Revises: 0003_sales
Create Date: 2026-10-10
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0004_sync"
down_revision: str | None = "0003_sales"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

TENANT_OK = "tenant_id = nullif(current_setting('app.tenant_id', true), '')::uuid"


def upgrade() -> None:
    op.add_column(
        "sales",
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_sales_store_updated", "sales", ["store_id", "updated_at", "id"])
    op.create_index("ix_products_tenant_updated", "products", ["tenant_id", "updated_at", "id"])
    op.create_index("ix_stock_movements_store_created", "stock_movements", ["store_id", "created_at", "id"])

    op.create_table(
        "sync_ops",
        sa.Column("op_id", sa.Uuid(), nullable=False),
        sa.Column("tenant_id", sa.Uuid(), nullable=False),
        sa.Column("op_type", sa.String(length=20), nullable=False),
        sa.Column("status", sa.String(length=20), nullable=False),
        sa.Column("error_title", sa.String(length=200), nullable=True),
        sa.Column("error_detail", sa.String(length=500), nullable=True),
        sa.Column("processed_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"]),
        sa.PrimaryKeyConstraint("op_id"),
    )
    op.create_index(op.f("ix_sync_ops_tenant_id"), "sync_ops", ["tenant_id"])
    op.execute("ALTER TABLE sync_ops ENABLE ROW LEVEL SECURITY")
    op.execute(f"CREATE POLICY tenant_isolation ON sync_ops USING ({TENANT_OK}) WITH CHECK ({TENANT_OK})")


def downgrade() -> None:
    op.execute("DROP POLICY IF EXISTS tenant_isolation ON sync_ops")
    op.drop_table("sync_ops")
    op.drop_index("ix_stock_movements_store_created", table_name="stock_movements")
    op.drop_index("ix_products_tenant_updated", table_name="products")
    op.drop_index("ix_sales_store_updated", table_name="sales")
    op.drop_column("sales", "updated_at")
