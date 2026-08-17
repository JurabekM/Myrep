import uuid
from typing import Optional

from sqlalchemy import Enum, ForeignKey, Numeric, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin, UUIDPrimaryKeyMixin
from app.models.enums import PaymentProviderCode, PaymentStatus


class Payment(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """Click/Payme/UzumBank orqali hamyonni to'ldirish (top-up) tranzaksiyasi."""

    __tablename__ = "payments"

    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"), index=True)
    wallet_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("wallets.id"))
    provider: Mapped[PaymentProviderCode] = mapped_column(Enum(PaymentProviderCode, name="payment_provider"))
    amount: Mapped[float] = mapped_column(Numeric(18, 2))
    currency: Mapped[str] = mapped_column(String(3), default="UZS")
    status: Mapped[PaymentStatus] = mapped_column(
        Enum(PaymentStatus, name="payment_status"), default=PaymentStatus.PENDING
    )
    external_id: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    checkout_url: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    transaction_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), ForeignKey("transactions.id"), nullable=True
    )

    user: Mapped["User"] = relationship()
    wallet: Mapped["Wallet"] = relationship()
