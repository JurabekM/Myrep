"""Exporting company profile."""

from __future__ import annotations

from sqlalchemy import String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, IdMixin, TimestampMixin


class Company(IdMixin, TimestampMixin, Base):
    """Profile of the exporting company shown on catalogs and quotations."""

    __tablename__ = "companies"

    name: Mapped[str] = mapped_column(String(200), nullable=False)
    legal_name: Mapped[str | None] = mapped_column(String(200))
    logo_path: Mapped[str | None] = mapped_column(String(400))
    address: Mapped[str | None] = mapped_column(Text)
    country: Mapped[str] = mapped_column(String(80), default="Uzbekistan", nullable=False)
    city: Mapped[str | None] = mapped_column(String(80))
    tax_id: Mapped[str | None] = mapped_column(String(40))
    phone: Mapped[str | None] = mapped_column(String(80))
    email: Mapped[str | None] = mapped_column(String(160))
    website: Mapped[str | None] = mapped_column(String(160))
    export_contact_name: Mapped[str | None] = mapped_column(String(120))
    export_contact_phone: Mapped[str | None] = mapped_column(String(80))
    export_contact_email: Mapped[str | None] = mapped_column(String(160))
    bank_name: Mapped[str | None] = mapped_column(String(160))
    bank_account: Mapped[str | None] = mapped_column(String(80))
    bank_swift: Mapped[str | None] = mapped_column(String(40))
    bank_address: Mapped[str | None] = mapped_column(Text)
    correspondent_bank: Mapped[str | None] = mapped_column(String(200))
    default_currency: Mapped[str] = mapped_column(String(3), default="USD", nullable=False)
    timezone: Mapped[str] = mapped_column(String(60), default="Asia/Tashkent", nullable=False)
    languages: Mapped[str] = mapped_column(String(40), default="uz,ru,en", nullable=False)
    about_uz: Mapped[str | None] = mapped_column(Text)
    about_ru: Mapped[str | None] = mapped_column(Text)
    about_en: Mapped[str | None] = mapped_column(Text)

    def __repr__(self) -> str:  # pragma: no cover
        return f"<Company {self.name}>"
