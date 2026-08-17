# -*- coding: utf-8 -*-
"""Mijozlar servisi: CRUD + debitorlik qarzi (receivables) + chegirma foizi."""
from __future__ import annotations

from decimal import Decimal

from src.core.errors import NotFoundError, ValidationError
from src.core.utils import D, Page
from src.database.repository import BaseRepository
from src.modules.base import BaseService


class CustomerRepository(BaseRepository):
    """``customers`` jadvali repositoriysi."""

    table = "customers"
    searchable = ("name", "tin", "phone", "code")
    default_order = "name ASC"


class CustomerService(BaseService):
    """Mijozlar bo'yicha biznes amallar."""

    def __init__(self, container) -> None:
        super().__init__(container)
        self.repo = CustomerRepository(self.db)

    def list_customers(self, page: int = 1, per_page: int = 25,
                       search: str | None = None,
                       include_inactive: bool = False) -> Page:
        """Sahifalangan mijozlar ro'yxati."""
        return self.repo.list(page=page, per_page=per_page, search=search,
                              include_inactive=include_inactive)

    def get(self, customer_id: int) -> dict:
        """Mijozni qaytaradi; topilmasa xato."""
        customer = self.repo.get(customer_id)
        if not customer:
            raise NotFoundError(f"Mijoz topilmadi (id={customer_id}).")
        return customer

    def create(self, data: dict, user: dict | None = None) -> int:
        """Yangi mijoz qo'shadi."""
        payload = self._validate(data)
        customer_id = self.repo.create(payload)
        self.audit.log("customer.create", user=user, entity="customer",
                       entity_id=customer_id, details=payload["name"])
        return customer_id

    def update(self, customer_id: int, data: dict,
               user: dict | None = None) -> bool:
        """Mijoz ma'lumotlarini yangilaydi."""
        self.get(customer_id)
        payload = self._validate(data, partial=True)
        ok = self.repo.update(customer_id, payload)
        self.audit.log("customer.update", user=user, entity="customer",
                       entity_id=customer_id)
        return ok

    def deactivate(self, customer_id: int, user: dict | None = None) -> bool:
        """Mijozni nofaol qiladi."""
        ok = self.repo.delete(customer_id)
        self.audit.log("customer.deactivate", user=user, entity="customer",
                       entity_id=customer_id)
        return ok

    def receivables(self, customer_id: int) -> Decimal:
        """Mijozdan undirilmagan qarz (tasdiqlangan savdolar bo'yicha)."""
        value = self.db.scalar(
            "SELECT SUM(total - paid_amount) FROM sales_docs "
            "WHERE customer_id = ? AND doc_type IN ('invoice', 'pos') "
            "AND status IN ('confirmed', 'partial')",
            (customer_id,), 0,
        )
        return D(value)

    @staticmethod
    def _validate(data: dict, partial: bool = False) -> dict:
        allowed = {"code", "name", "tin", "phone", "email", "address",
                   "credit_limit", "discount_percent", "note", "is_active"}
        payload = {k: v for k, v in data.items() if k in allowed}
        if not partial or "name" in payload:
            name = str(payload.get("name") or "").strip()
            if not name:
                raise ValidationError("Mijoz nomi bo'sh bo'lishi mumkin emas.")
            payload["name"] = name
        for money_field in ("credit_limit", "discount_percent"):
            if money_field in payload:
                value = D(payload[money_field])
                if value < 0:
                    raise ValidationError(
                        f"{money_field} manfiy bo'lishi mumkin emas.")
                payload[money_field] = value
        if "discount_percent" in payload and payload["discount_percent"] > 100:
            raise ValidationError("Chegirma 100% dan oshishi mumkin emas.")
        return payload
