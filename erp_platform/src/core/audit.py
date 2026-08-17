# -*- coding: utf-8 -*-
"""
Audit Trail — kim, qachon, nima qilganini qayd etish.

Yozuvlar ikki joyga boradi:
  1. ``audit_log`` jadvali (UI da ko'rish, filtrlash uchun)
  2. ``logs/audit.log`` yoki ``logs/security.log`` fayli (o'zgarmas iz)
"""
from __future__ import annotations

from typing import Any

from src.core.logger import get_logger
from src.core.utils import clamp_page, now_str, Page


class AuditTrail:
    """Audit va xavfsizlik hodisalarini qayd etuvchi servis."""

    def __init__(self, db) -> None:
        self._db = db
        self._audit_log = get_logger("uzerp.audit")
        self._security_log = get_logger("uzerp.security")

    def log(
        self,
        action: str,
        *,
        user: dict | None = None,
        entity: str = "",
        entity_id: Any = "",
        details: str = "",
        ip: str = "",
        category: str = "audit",
    ) -> None:
        """
        Hodisani qayd etadi.

        :param action:   qisqa harakat nomi (masalan ``sale.create``, ``login.failed``)
        :param user:     harakatni bajargan foydalanuvchi (dict yoki None)
        :param entity:   obyekt turi (masalan ``invoice``)
        :param entity_id: obyekt identifikatori
        :param details:  qo'shimcha matn
        :param ip:       so'rov IP manzili
        :param category: ``audit`` | ``security`` | ``system``
        """
        user_id = user.get("id") if user else None
        username = (user.get("username") if user else "") or "system"
        try:
            self._db.insert(
                "audit_log",
                {
                    "user_id": user_id,
                    "username": username,
                    "action": action,
                    "entity": entity,
                    "entity_id": str(entity_id or ""),
                    "details": details[:2000],
                    "ip": ip,
                    "category": category,
                    "created_at": now_str(),
                },
            )
        except Exception:  # noqa: BLE001 - audit hech qachon asosiy oqimni buzmasin
            get_logger().exception("Audit yozuvida xato: %s", action)

        line = f"{username} | {action} | {entity}#{entity_id} | {details} | ip={ip}"
        if category == "security":
            self._security_log.info(line)
        else:
            self._audit_log.info(line)

    def security(self, action: str, **kwargs: Any) -> None:
        """Xavfsizlik hodisasi uchun qisqartma (category='security')."""
        kwargs["category"] = "security"
        self.log(action, **kwargs)

    def recent(
        self,
        page: int = 1,
        per_page: int = 50,
        category: str | None = None,
        username: str | None = None,
    ) -> Page:
        """Oxirgi audit yozuvlarini sahifalab qaytaradi (yangi -> eski)."""
        page, per_page = clamp_page(page, per_page)
        where, params = ["1=1"], []
        if category:
            where.append("category = ?")
            params.append(category)
        if username:
            where.append("username = ?")
            params.append(username)
        cond = " AND ".join(where)
        total_row = self._db.query_one(
            f"SELECT COUNT(*) AS c FROM audit_log WHERE {cond}", tuple(params)
        )
        items = self._db.query(
            f"SELECT * FROM audit_log WHERE {cond} ORDER BY id DESC LIMIT ? OFFSET ?",
            tuple(params) + (per_page, (page - 1) * per_page),
        )
        return Page(items=items, page=page, per_page=per_page,
                    total=int(total_row["c"]) if total_row else 0)
