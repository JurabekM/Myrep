import uuid

from sqlalchemy import Enum, ForeignKey, Numeric
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin, UUIDPrimaryKeyMixin
from app.models.enums import InvestmentAssetType


class Investment(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "investments"

    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"), index=True)
    asset_type: Mapped[InvestmentAssetType] = mapped_column(Enum(InvestmentAssetType, name="investment_asset_type"))
    quantity: Mapped[float] = mapped_column(Numeric(18, 6))
    avg_price: Mapped[float] = mapped_column(Numeric(18, 2))

    owner: Mapped["User"] = relationship(back_populates="investments")
