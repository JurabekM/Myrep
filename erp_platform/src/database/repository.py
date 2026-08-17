# -*- coding: utf-8 -*-
"""
Repository pattern — jadval ustidagi standart CRUD amallar.

Har bir modul o'z repositoriysini ``BaseRepository`` dan meros oladi va
faqat o'ziga xos so'rovlarni qo'shadi. Bu SQL kodini bir joyga jamlaydi
va xizmat (service) qatlamini toza saqlaydi.
"""
from __future__ import annotations

import re
from typing import Any

from src.core.utils import clamp_page, now_str, Page

_IDENTIFIER_RE = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")
_ORDER_RE = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*(\s+(ASC|DESC))?$", re.IGNORECASE)


class BaseRepository:
    """
    Umumiy CRUD repository.

    Meros oluvchi klass quyidagilarni belgilaydi:

    * ``table``       — jadval nomi (majburiy)
    * ``searchable``  — matnli qidiruv ustunlari
    * ``timestamps``  — True bo'lsa created_at/updated_at avtomatik yoziladi
    * ``soft_delete`` — True bo'lsa o'chirish o'rniga ``is_active = 0``
    """

    table: str = ""
    searchable: tuple[str, ...] = ()
    default_order: str = "id DESC"
    timestamps: bool = True
    soft_delete: bool = True

    def __init__(self, db) -> None:
        if not self.table or not _IDENTIFIER_RE.match(self.table):
            raise ValueError(f"Yaroqsiz jadval nomi: {self.table!r}")
        self.db = db

    # ------------------------------------------------------------------ #
    #  O'qish
    # ------------------------------------------------------------------ #

    def get(self, item_id: int) -> dict | None:
        """Bitta yozuvni id bo'yicha qaytaradi."""
        return self.db.query_one(
            f"SELECT * FROM {self.table} WHERE id = ?", (item_id,)
        )

    def list(
        self,
        page: int = 1,
        per_page: int = 25,
        search: str | None = None,
        filters: dict[str, Any] | None = None,
        order_by: str | None = None,
        include_inactive: bool = False,
    ) -> Page:
        """
        Sahifalangan ro'yxat: filtrlash + matnli qidiruv + tartiblash.

        ``filters`` — {ustun: qiymat} ko'rinishida aniq tenglik sharti.
        """
        page, per_page = clamp_page(page, per_page)
        where, params = self._build_where(search, filters, include_inactive)

        total = int(self.db.scalar(
            f"SELECT COUNT(*) FROM {self.table} WHERE {where}", params, 0
        ) or 0)

        order = self._safe_order(order_by)
        items = self.db.query(
            f"SELECT * FROM {self.table} WHERE {where} "
            f"ORDER BY {order} LIMIT ? OFFSET ?",
            params + (per_page, (page - 1) * per_page),
        )
        return Page(items=items, page=page, per_page=per_page, total=total)

    def all(self, filters: dict[str, Any] | None = None,
            include_inactive: bool = False) -> list[dict]:
        """Barcha yozuvlar (kichik lug'at jadvallari uchun)."""
        where, params = self._build_where(None, filters, include_inactive)
        return self.db.query(
            f"SELECT * FROM {self.table} WHERE {where} ORDER BY {self.default_order}",
            params,
        )

    def count(self, filters: dict[str, Any] | None = None) -> int:
        """Shartlarga mos yozuvlar soni."""
        where, params = self._build_where(None, filters, True)
        return int(self.db.scalar(
            f"SELECT COUNT(*) FROM {self.table} WHERE {where}", params, 0
        ) or 0)

    # ------------------------------------------------------------------ #
    #  Yozish
    # ------------------------------------------------------------------ #

    def create(self, data: dict[str, Any]) -> int:
        """Yangi yozuv qo'shadi; ``id`` qaytaradi."""
        payload = dict(data)
        if self.timestamps:
            payload.setdefault("created_at", now_str())
            payload.setdefault("updated_at", now_str())
        return self.db.insert(self.table, payload)

    def update(self, item_id: int, data: dict[str, Any]) -> bool:
        """Yozuvni yangilaydi; muvaffaqiyat holatini qaytaradi."""
        payload = dict(data)
        payload.pop("id", None)
        if self.timestamps:
            payload["updated_at"] = now_str()
        affected = self.db.update(self.table, payload, "id = ?", (item_id,))
        return affected > 0

    def delete(self, item_id: int) -> bool:
        """
        Yozuvni o'chiradi. ``soft_delete=True`` bo'lsa faqat nofaol qiladi —
        tarixiy hujjatlar butunligi buzilmaydi.
        """
        if self.soft_delete:
            affected = self.db.update(
                self.table, {"is_active": 0}, "id = ?", (item_id,)
            )
        else:
            affected = self.db.delete(self.table, "id = ?", (item_id,))
        return affected > 0

    # ------------------------------------------------------------------ #
    #  Ichki yordamchilar
    # ------------------------------------------------------------------ #

    def _build_where(
        self,
        search: str | None,
        filters: dict[str, Any] | None,
        include_inactive: bool,
    ) -> tuple[str, tuple]:
        """WHERE shartini xavfsiz quradi (faqat parametrlangan qiymatlar)."""
        conditions: list[str] = ["1=1"]
        params: list[Any] = []

        if self.soft_delete and not include_inactive:
            conditions.append("is_active = 1")

        for column, value in (filters or {}).items():
            if not _IDENTIFIER_RE.match(column):
                raise ValueError(f"Yaroqsiz ustun nomi: {column!r}")
            if value is None:
                conditions.append(f"{column} IS NULL")
            else:
                conditions.append(f"{column} = ?")
                params.append(value)

        if search and self.searchable:
            like = f"%{search.strip()}%"
            sub = " OR ".join(f"{col} LIKE ?" for col in self.searchable)
            conditions.append(f"({sub})")
            params.extend([like] * len(self.searchable))

        return " AND ".join(conditions), tuple(params)

    def _safe_order(self, order_by: str | None) -> str:
        """ORDER BY ifodasini oq ro'yxat bilan tekshiradi (injection himoya)."""
        candidate = (order_by or self.default_order).strip()
        for part in candidate.split(","):
            if not _ORDER_RE.match(part.strip()):
                return self.default_order
        return candidate
