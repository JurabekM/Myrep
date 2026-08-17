"""notification_type enum'iga ADMIN_MESSAGE qo'shish (admin panel xabarlari uchun)

Revision ID: 0004
Revises: 0003
Create Date: 2026-07-15

"""
from typing import Sequence, Union

from alembic import op

revision: str = "0004"
down_revision: Union[str, None] = "0003"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ADD VALUE tranzaksiyadan tashqarida bajarilishi kerak (PG cheklovi),
    # alembic'da autocommit_block shu maqsadga xizmat qiladi.
    with op.get_context().autocommit_block():
        op.execute("ALTER TYPE notification_type ADD VALUE IF NOT EXISTS 'ADMIN_MESSAGE'")


def downgrade() -> None:
    # PostgreSQL enum'dan qiymatni olib tashlashni qo'llab-quvvatlamaydi -
    # downgrade'da qiymat qoladi (zararsiz).
    pass
