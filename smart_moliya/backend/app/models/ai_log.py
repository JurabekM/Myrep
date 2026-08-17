import uuid

from sqlalchemy import ForeignKey, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, TimestampMixin, UUIDPrimaryKeyMixin


class AiLog(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """AI Service chaqiruvlari audit logi (kategoriyalash, bashorat, chatbot, anomaliya)."""

    __tablename__ = "ai_logs"

    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"), index=True)
    model: Mapped[str] = mapped_column(String(100))  # classifier | forecast | chatbot | anomaly
    input_ref: Mapped[str] = mapped_column(String(500))
    output_ref: Mapped[str] = mapped_column(String(500))
