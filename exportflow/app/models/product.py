"""Product information management models."""

from __future__ import annotations

import datetime as dt

from sqlalchemy import Boolean, Date, Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import ArchiveMixin, Base, IdMixin, TimestampMixin


class ProductCategory(IdMixin, TimestampMixin, ArchiveMixin, Base):
    """Hierarchical product category (category / subcategory)."""

    __tablename__ = "product_categories"

    code: Mapped[str] = mapped_column(String(40), nullable=False, index=True)
    name_uz: Mapped[str] = mapped_column(String(120), nullable=False)
    name_ru: Mapped[str] = mapped_column(String(120), nullable=False, default="")
    name_en: Mapped[str] = mapped_column(String(120), nullable=False, default="")
    parent_id: Mapped[int | None] = mapped_column(ForeignKey("product_categories.id"))

    parent: Mapped[ProductCategory | None] = relationship(remote_side="ProductCategory.id")
    products: Mapped[list[Product]] = relationship(back_populates="category")

    def display_name(self, lang: str = "en") -> str:
        """Localized category name with graceful fallback."""
        return getattr(self, f"name_{lang}", None) or self.name_en or self.name_uz


class Product(IdMixin, TimestampMixin, ArchiveMixin, Base):
    """A manufactured product offered for export."""

    __tablename__ = "products"

    sku: Mapped[str] = mapped_column(String(60), unique=True, nullable=False, index=True)
    status: Mapped[str] = mapped_column(String(20), default="draft", nullable=False, index=True)

    name_uz: Mapped[str] = mapped_column(String(200), nullable=False, default="")
    name_ru: Mapped[str] = mapped_column(String(200), nullable=False, default="")
    name_en: Mapped[str] = mapped_column(String(200), nullable=False, default="")
    short_desc_uz: Mapped[str | None] = mapped_column(Text)
    short_desc_ru: Mapped[str | None] = mapped_column(Text)
    short_desc_en: Mapped[str | None] = mapped_column(Text)
    full_desc_uz: Mapped[str | None] = mapped_column(Text)
    full_desc_ru: Mapped[str | None] = mapped_column(Text)
    full_desc_en: Mapped[str | None] = mapped_column(Text)

    brand: Mapped[str | None] = mapped_column(String(120))
    manufacturer: Mapped[str | None] = mapped_column(String(200))
    hs_code: Mapped[str | None] = mapped_column(String(20), index=True)
    origin_country: Mapped[str] = mapped_column(String(80), default="Uzbekistan", nullable=False)

    moq: Mapped[float | None] = mapped_column(Float)
    unit: Mapped[str] = mapped_column(String(20), default="pcs", nullable=False)
    capacity_month: Mapped[float | None] = mapped_column(Float)
    capacity_year: Mapped[float | None] = mapped_column(Float)
    lead_time_days: Mapped[int | None] = mapped_column(Integer)

    net_weight: Mapped[float | None] = mapped_column(Float)
    gross_weight: Mapped[float | None] = mapped_column(Float)
    length_cm: Mapped[float | None] = mapped_column(Float)
    width_cm: Mapped[float | None] = mapped_column(Float)
    height_cm: Mapped[float | None] = mapped_column(Float)

    packaging_type: Mapped[str | None] = mapped_column(String(120))
    units_per_carton: Mapped[float | None] = mapped_column(Float)
    cartons_per_pallet: Mapped[float | None] = mapped_column(Float)
    carton_dimensions: Mapped[str | None] = mapped_column(String(120))
    pallet_dimensions: Mapped[str | None] = mapped_column(String(120))
    shelf_life: Mapped[str | None] = mapped_column(String(120))
    storage_condition: Mapped[str | None] = mapped_column(Text)

    tags: Mapped[str | None] = mapped_column(String(400))
    internal_notes: Mapped[str | None] = mapped_column(Text)
    export_ready: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    category_id: Mapped[int | None] = mapped_column(ForeignKey("product_categories.id"))
    category: Mapped[ProductCategory | None] = relationship(
        back_populates="products", lazy="joined"
    )

    variants: Mapped[list[ProductVariant]] = relationship(
        back_populates="product", cascade="all, delete-orphan"
    )
    media: Mapped[list[ProductMedia]] = relationship(
        back_populates="product", cascade="all, delete-orphan"
    )
    specifications: Mapped[list[ProductSpecification]] = relationship(
        back_populates="product", cascade="all, delete-orphan"
    )
    prices: Mapped[list[ProductPrice]] = relationship(
        back_populates="product", cascade="all, delete-orphan"
    )

    def display_name(self, lang: str = "en") -> str:
        """Localized product name with fallback to English then Uzbek."""
        return getattr(self, f"name_{lang}", None) or self.name_en or self.name_uz or self.sku

    def __repr__(self) -> str:  # pragma: no cover
        return f"<Product {self.sku}>"


class ProductVariant(IdMixin, TimestampMixin, ArchiveMixin, Base):
    """A colour/size/packaging variant of a product."""

    __tablename__ = "product_variants"

    product_id: Mapped[int] = mapped_column(ForeignKey("products.id", ondelete="CASCADE"))
    sku_suffix: Mapped[str] = mapped_column(String(40), default="", nullable=False)
    name: Mapped[str] = mapped_column(String(160), nullable=False)
    attribute: Mapped[str | None] = mapped_column(String(80))
    value: Mapped[str | None] = mapped_column(String(160))
    extra_price: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    moq: Mapped[float | None] = mapped_column(Float)

    product: Mapped[Product] = relationship(back_populates="variants")


class ProductMedia(IdMixin, TimestampMixin, Base):
    """Photo / video / file attached to a product."""

    __tablename__ = "product_media"

    product_id: Mapped[int] = mapped_column(ForeignKey("products.id", ondelete="CASCADE"))
    kind: Mapped[str] = mapped_column(String(20), default="image", nullable=False)
    file_path: Mapped[str] = mapped_column(String(500), nullable=False)
    title: Mapped[str | None] = mapped_column(String(160))
    is_primary: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    sort_order: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    product: Mapped[Product] = relationship(back_populates="media")


class ProductSpecification(IdMixin, TimestampMixin, Base):
    """Key/value technical attribute displayed in catalogs."""

    __tablename__ = "product_specifications"

    product_id: Mapped[int] = mapped_column(ForeignKey("products.id", ondelete="CASCADE"))
    name_en: Mapped[str] = mapped_column(String(120), nullable=False)
    name_ru: Mapped[str | None] = mapped_column(String(120))
    name_uz: Mapped[str | None] = mapped_column(String(120))
    value_en: Mapped[str] = mapped_column(String(240), nullable=False, default="")
    value_ru: Mapped[str | None] = mapped_column(String(240))
    value_uz: Mapped[str | None] = mapped_column(String(240))
    sort_order: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    product: Mapped[Product] = relationship(back_populates="specifications")


class ProductPrice(IdMixin, TimestampMixin, ArchiveMixin, Base):
    """An Incoterm-specific price line with its own validity window."""

    __tablename__ = "product_prices"

    product_id: Mapped[int] = mapped_column(ForeignKey("products.id", ondelete="CASCADE"))
    incoterm: Mapped[str] = mapped_column(String(20), default="FOB", nullable=False, index=True)
    custom_incoterm: Mapped[str | None] = mapped_column(String(40))
    currency: Mapped[str] = mapped_column(String(3), default="USD", nullable=False)
    origin_point: Mapped[str | None] = mapped_column(String(160))
    unit_price: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    moq: Mapped[float | None] = mapped_column(Float)
    valid_from: Mapped[dt.date | None] = mapped_column(Date)
    valid_to: Mapped[dt.date | None] = mapped_column(Date)
    payment_terms: Mapped[str | None] = mapped_column(String(200))
    lead_time_days: Mapped[int | None] = mapped_column(Integer)
    status: Mapped[str] = mapped_column(String(20), default="draft", nullable=False, index=True)
    notes: Mapped[str | None] = mapped_column(Text)

    product: Mapped[Product] = relationship(back_populates="prices")

    def __repr__(self) -> str:  # pragma: no cover
        return f"<ProductPrice {self.incoterm} {self.unit_price}{self.currency}>"
