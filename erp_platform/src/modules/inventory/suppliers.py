# -*- coding: utf-8 -*-
"""Ta'minotchilar servisi: CRUD + kreditorlik qarzi (payables)."""
from __future__ import annotations

from decimal import Decimal

from src.core.errors import NotFoundError, ValidationError
from src.core.utils import D, Page
from src.database.repository import BaseRepository
from src.modules.base import BaseService


class SupplierRepository(BaseRepository):
    """``suppliers`` jadvali repositoriysi."""

    table = "suppliers"
    searchable = ("name", "tin", "phone", "code")
    default_order = "name ASC"


class SupplierService(BaseService):
    """Ta'minotchilar bo'yicha biznes amallar."""

    def __init__(self, container) -> None:
        super().__init__(container)
        self.repo = SupplierRepository(self.db)

    def list_suppliers(self, page: int = 1, per_page: int = 25,
                       search: str | None = None,
                       include_inactive: bool = False) -> Page:
        """Sahifalangan ta'minotchilar ro'yxati."""
        return self.repo.list(page=page, per_page=per_page, search=search,
                              include_inactive=include_inactive)

    def get(self, supplier_id: int) -> dict:
        """Ta'minotchini qaytaradi; topilmasa xato."""
        supplier = self.repo.get(supplier_id)
        if not supplier:
            raise NotFoundError(f"Ta'minotchi topilmadi (id={supplier_id}).")
        return supplier

    def create(self, data: dict, user: dict | None = None) -> int:
        """Yangi ta'minotchi qo'shadi."""
        payload = self._validate(data)
        supplier_id = self.repo.create(payload)
        self.audit.log("supplier.create", user=user, entity="supplier",
                       entity_id=supplier_id, details=payload["name"])
        return supplier_id

    def update(self, supplier_id: int, data: dict,
               user: dict | None = None) -> bool:
        """Ta'minotchi ma'lumotlarini yangilaydi."""
        self.get(supplier_id)
        payload = self._validate(data, partial=True)
        ok = self.repo.update(supplier_id, payload)
        self.audit.log("supplier.update", user=user, entity="supplier",
                       entity_id=supplier_id)
        return ok

    def deactivate(self, supplier_id: int, user: dict | None = None) -> bool:
        """Ta'minotchini nofaol qiladi."""
        ok = self.repo.delete(supplier_id)
        self.audit.log("supplier.deactivate", user=user, entity="supplier",
                       entity_id=supplier_id)
        return ok

    def payables(self, supplier_id: int) -> Decimal:
        """Ta'minotchiga to'lanmagan qarz (qabul qilingan xaridlar bo'yicha)."""
        value = self.db.scalar(
            "SELECT SUM(total - paid_amount) FROM purchases "
            "WHERE supplier_id = ? AND status IN ('received', 'partial')",
            (supplier_id,), 0,
        )
        return D(value)

    @staticmethod
    def _validate(data: dict, partial: bool = False) -> dict:
        allowed = {"code", "name", "tin", "phone", "email", "address",
                   "note", "is_active"}
        payload = {k: v for k, v in data.items() if k in allowed}
        if not partial or "name" in payload:
            name = str(payload.get("name") or "").strip()
            if not name:
                raise ValidationError("Ta'minotchi nomi bo'sh bo'lishi mumkin emas.")
            payload["name"] = name
        return payload
