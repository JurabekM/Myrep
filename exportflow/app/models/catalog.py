"""Multilingual catalog builder models."""

from __future__ import annotations

from sqlalchemy import ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import ArchiveMixin, Base, IdMixin, TimestampMixin


class Catalog(IdMixin, TimestampMixin, ArchiveMixin, Base):
    """A versioned product catalog that can be exported to PDF/HTML/ZIP."""

    __tablename__ = "catalogs"

    title: Mapped[str] = mapped_column(String(200), nullable=False)
    language: Mapped[str] = mapped_column(String(5), default="en", nullable=False)
    version: Mapped[str] = mapped_column(String(20), default="1.0", nullable=False)
    subtitle: Mapped[str | None] = mapped_column(String(240))
    cover_note: Mapped[str | None] = mapped_column(Text)
    about_text: Mapped[str | None] = mapped_column(Text)
    contact_text: Mapped[str | None] = mapped_column(Text)
    include_certificates: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    include_prices: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    template: Mapped[str] = mapped_column(String(40), default="modern", nullable=False)
    last_export_path: Mapped[str | None] = mapped_column(String(500))

    items: Mapped[list[CatalogItem]] = relationship(
        back_populates="catalog", cascade="all, delete-orphan", order_by="CatalogItem.sort_order"
    )

    def __repr__(self) -> str:  # pragma: no cover
        return f"<Catalog {self.title} v{self.version}>"


class CatalogItem(IdMixin, Base):
    """A product included in a catalog, with optional per-catalog overrides."""

    __tablename__ = "catalog_items"

    catalog_id: Mapped[int] = mapped_column(ForeignKey("catalogs.id", ondelete="CASCADE"))
    product_id: Mapped[int] = mapped_column(ForeignKey("products.id", ondelete="CASCADE"))
    sort_order: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    highlight: Mapped[str | None] = mapped_column(String(240))

    catalog: Mapped[Catalog] = relationship(back_populates="items")
