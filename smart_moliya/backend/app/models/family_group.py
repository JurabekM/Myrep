import uuid

from sqlalchemy import ForeignKey, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin, UUIDPrimaryKeyMixin


class FamilyGroup(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "family_groups"

    name: Mapped[str] = mapped_column(String(255))
    owner_user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"))

    members: Mapped[list["User"]] = relationship(back_populates="family_group", foreign_keys="User.family_group_id")
