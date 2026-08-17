# -*- coding: utf-8 -*-
"""
Global qidiruv servisi (Ctrl+K).

Bitta so'rov bilan barcha asosiy obyektlar bo'ylab qidiradi:
mahsulotlar, mijozlar, ta'minotchilar, savdo/xarid hujjatlari,
xodimlar, leadlar, hisoblar. Natijalar guruhlangan holda,
web-интерфейс havolalari bilan qaytadi.
"""
from __future__ import annotations

from src.modules.base import BaseService

#: (guruh nomi, SQL, url shabloni) — {id} o'rniga yozuv id si qo'yiladi
_SOURCES: list[tuple[str, str, str]] = [
    ("Mahsulotlar",
     "SELECT id, name AS title, COALESCE(sku, '') || ' ' || barcode AS subtitle "
     "FROM products WHERE is_active = 1 AND "
     "(name LIKE ? OR sku LIKE ? OR barcode LIKE ?) LIMIT ?",
     "/products?highlight={id}"),
    ("Mijozlar",
     "SELECT id, name AS title, phone AS subtitle FROM customers "
     "WHERE is_active = 1 AND (name LIKE ? OR phone LIKE ? OR tin LIKE ?) LIMIT ?",
     "/customers/{id}"),
    ("Ta'minotchilar",
     "SELECT id, name AS title, phone AS subtitle FROM suppliers "
     "WHERE is_active = 1 AND (name LIKE ? OR phone LIKE ? OR tin LIKE ?) LIMIT ?",
     "/suppliers?highlight={id}"),
    ("Savdo hujjatlari",
     "SELECT id, number AS title, doc_type || ' | ' || status AS subtitle "
     "FROM sales_docs WHERE number LIKE ? OR note LIKE ? OR CAST(id AS TEXT) = ? "
     "ORDER BY id DESC LIMIT ?",
     "/sales/{id}"),
    ("Xaridlar",
     "SELECT id, number AS title, status AS subtitle FROM purchases "
     "WHERE number LIKE ? OR note LIKE ? OR CAST(id AS TEXT) = ? "
     "ORDER BY id DESC LIMIT ?",
     "/purchases/{id}"),
    ("Xodimlar",
     "SELECT id, full_name AS title, position AS subtitle FROM employees "
     "WHERE full_name LIKE ? OR code LIKE ? OR phone LIKE ? LIMIT ?",
     "/hr?highlight={id}"),
    ("Leadlar",
     "SELECT id, name AS title, status AS subtitle FROM leads "
     "WHERE name LIKE ? OR phone LIKE ? OR email LIKE ? LIMIT ?",
     "/crm?highlight={id}"),
    ("Hisoblar rejasi",
     "SELECT id, code || ' ' || name AS title, type AS subtitle FROM accounts "
     "WHERE is_active = 1 AND (code LIKE ? OR name LIKE ? OR name LIKE ?) LIMIT ?",
     "/accounting/accounts?highlight={id}"),
]


class SearchService(BaseService):
    """Barcha modullar bo'ylab yagona qidiruv."""

    def global_search(self, query: str, limit_per_group: int = 5) -> list[dict]:
        """
        Qidiruv natijalarini guruhlangan holda qaytaradi::

            [{"group": "Mahsulotlar",
              "items": [{"id": 1, "title": ..., "subtitle": ..., "url": ...}]}]
        """
        query = (query or "").strip()
        if len(query) < 2:
            return []
        like = f"%{query}%"
        results = []
        for group, sql, url_template in _SOURCES:
            params = self._build_params(sql, like, query, limit_per_group)
            try:
                rows = self.db.query(sql, params)
            except Exception:  # noqa: BLE001 - bitta manba xatosi qolganini buzmasin
                self.log.exception("Qidiruv xatosi: %s", group)
                continue
            if rows:
                results.append({
                    "group": group,
                    "items": [{
                        "id": row["id"],
                        "title": str(row.get("title") or ""),
                        "subtitle": str(row.get("subtitle") or "").strip(" |"),
                        "url": url_template.format(id=row["id"]),
                    } for row in rows],
                })
        return results

    @staticmethod
    def _build_params(sql: str, like: str, raw: str, limit: int) -> tuple:
        """SQL dagi placeholderlar soniga mos parametrlar tuzadi."""
        placeholders = sql.count("?") - 1  # oxirgisi LIMIT
        params: list = []
        for _ in range(placeholders):
            # CAST(id AS TEXT) = ? bo'lgan joyga xom qiymat ketadi
            params.append(raw if "CAST(id AS TEXT) = ?" in sql
                          and len(params) == placeholders - 1 else like)
        params.append(limit)
        return tuple(params)
