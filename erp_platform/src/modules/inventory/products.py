# -*- coding: utf-8 -*-
"""
Mahsulotlar katalogi servisi.

* CRUD + qidiruv (nom, SKU, shtrix-kod bo'yicha)
* SKU avtomatik generatsiyasi (``P000123``)
* Shtrix-kod orqali topish (POS uchun)
* Minimal zaxiradan kam qolgan mahsulotlar ro'yxati
* Kategoriyalar boshqaruvi
"""
from __future__ import annotations

from decimal import Decimal
from typing import Any

from src.core.errors import NotFoundError, ValidationError
from src.core.utils import D, Page
from src.database.repository import BaseRepository
from src.modules.base import BaseService


class ProductRepository(BaseRepository):
    """``products`` jadvali repositoriysi."""

    table = "products"
    searchable = ("name", "sku", "barcode")
    default_order = "name ASC"


class ProductService(BaseService):
    """Mahsulotlar va kategoriyalar bo'yicha biznes amallar."""

    def __init__(self, container) -> None:
        super().__init__(container)
        self.repo = ProductRepository(self.db)

    # ------------------------------------------------------------------ #
    #  Mahsulotlar
    # ------------------------------------------------------------------ #

    def list_products(self, page: int = 1, per_page: int = 25,
                      search: str | None = None,
                      category_id: int | None = None,
                      include_inactive: bool = False) -> Page:
        """Sahifalangan mahsulotlar ro'yxati (qidiruv va kategoriya filtri bilan)."""
        filters: dict[str, Any] = {}
        if category_id:
            filters["category_id"] = category_id
        return self.repo.list(page=page, per_page=per_page, search=search,
                              filters=filters, include_inactive=include_inactive)

    def get(self, product_id: int) -> dict:
        """Mahsulotni qaytaradi; topilmasa :class:`NotFoundError`."""
        product = self.repo.get(product_id)
        if not product:
            raise NotFoundError(f"Mahsulot topilmadi (id={product_id}).")
        return product

    def create(self, data: dict, user: dict | None = None) -> int:
        """
        Yangi mahsulot qo'shadi.

        SKU berilmasa avtomatik ``P{id:06d}`` ko'rinishida yaratiladi.
        """
        payload = self._validate(data)
        with self.db.transaction():
            product_id = self.repo.create(payload)
            if not payload.get("sku"):
                self.repo.update(product_id, {"sku": f"P{product_id:06d}"})
        self.audit.log("product.create", user=user, entity="product",
                       entity_id=product_id, details=payload["name"])
        self.cache.invalidate_prefix("products")
        return product_id

    def update(self, product_id: int, data: dict, user: dict | None = None) -> bool:
        """Mahsulot ma'lumotlarini yangilaydi."""
        self.get(product_id)  # mavjudligini tekshirish
        payload = self._validate(data, partial=True)
        ok = self.repo.update(product_id, payload)
        self.audit.log("product.update", user=user, entity="product",
                       entity_id=product_id, details=str(sorted(payload.keys())))
        self.cache.invalidate_prefix("products")
        return ok

    def deactivate(self, product_id: int, user: dict | None = None) -> bool:
        """Mahsulotni nofaol qiladi (tarixiy hujjatlar saqlanadi)."""
        ok = self.repo.delete(product_id)
        self.audit.log("product.deactivate", user=user, entity="product",
                       entity_id=product_id)
        self.cache.invalidate_prefix("products")
        return ok

    def find_by_barcode(self, barcode: str) -> dict | None:
        """Shtrix-kod bo'yicha faol mahsulotni topadi (POS skaneri uchun)."""
        code = (barcode or "").strip()
        if not code:
            return None
        return self.db.query_one(
            "SELECT * FROM products WHERE barcode = ? AND is_active = 1", (code,)
        )

    def low_stock(self, limit: int = 100) -> list[dict]:
        """
        Minimal zaxira chegarasidan kam qolgan mahsulotlar
        (``min_stock`` belgilanganlar orasida).
        """
        return self.db.query(
            "SELECT p.id, p.sku, p.name, p.unit, p.min_stock, "
            "       COALESCE(s.qty, 0) AS current_qty "
            "FROM products p "
            "LEFT JOIN (SELECT product_id, SUM(quantity) AS qty "
            "           FROM stock GROUP BY product_id) s ON s.product_id = p.id "
            "WHERE p.is_active = 1 AND p.min_stock > 0 "
            "  AND COALESCE(s.qty, 0) <= p.min_stock "
            "ORDER BY COALESCE(s.qty, 0) ASC LIMIT ?",
            (limit,),
        )

    def update_cost_price(self, product_id: int, new_cost: Decimal) -> None:
        """O'rtacha tannarxni yangilaydi (xarid qabulida chaqiriladi)."""
        self.repo.update(product_id, {"cost_price": D(new_cost)})
        self.cache.invalidate_prefix("products")

    # ------------------------------------------------------------------ #
    #  Kategoriyalar
    # ------------------------------------------------------------------ #

    def categories(self) -> list[dict]:
        """Faol kategoriyalar ro'yxati."""
        return self.db.query(
            "SELECT * FROM categories WHERE is_active = 1 ORDER BY name"
        )

    def create_category(self, name: str, parent_id: int | None = None,
                        user: dict | None = None) -> int:
        """Yangi kategoriya qo'shadi."""
        name = (name or "").strip()
        if not name:
            raise ValidationError("Kategoriya nomi bo'sh bo'lishi mumkin emas.")
        category_id = self.db.insert(
            "categories", {"name": name, "parent_id": parent_id, "is_active": 1}
        )
        self.audit.log("category.create", user=user, entity="category",
                       entity_id=category_id, details=name)
        return category_id

    # ------------------------------------------------------------------ #
    #  Ichki yordamchilar
    # ------------------------------------------------------------------ #

    def _validate(self, data: dict, partial: bool = False) -> dict:
        """Kiruvchi ma'lumotni tozalaydi va tekshiradi."""
        allowed = {"sku", "barcode", "name", "category_id", "unit", "cost_price",
                   "sale_price", "vat_rate", "min_stock", "description", "is_active"}
        payload = {k: v for k, v in data.items() if k in allowed}

        if not partial or "name" in payload:
            name = str(payload.get("name") or "").strip()
            if not name:
                raise ValidationError("Mahsulot nomi bo'sh bo'lishi mumkin emas.")
            payload["name"] = name

        for money_field in ("cost_price", "sale_price", "vat_rate", "min_stock"):
            if money_field in payload:
                value = D(payload[money_field])
                if value < 0:
                    raise ValidationError(
                        f"{money_field} manfiy bo'lishi mumkin emas."
                    )
                payload[money_field] = value

        if "sku" in payload and payload["sku"]:
            payload["sku"] = str(payload["sku"]).strip()
        if "barcode" in payload and payload["barcode"]:
            payload["barcode"] = str(payload["barcode"]).strip()
        if not partial:
            payload.setdefault("unit", "dona")
            payload.setdefault(
                "vat_rate", D(self.config.get("accounting.vat_rate", 12))
            )
        return payload
