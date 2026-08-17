# -*- coding: utf-8 -*-
"""
CRM servisi.

* Leadlar: yangi -> aloqa qilindi -> malakali -> yutildi/yo'qotildi
  (yutilgan lead avtomatik mijozga aylanadi)
* Faoliyatlar: qo'ng'iroq, email, uchrashuv, eslatma, vazifa
* Eslatmalar: muddati kelgan ochiq faoliyatlar ro'yxati
* Mijoz tarixi: faoliyatlar + savdo hujjatlari birlashgan lenta
"""
from __future__ import annotations

from src.core.errors import NotFoundError, StateError, ValidationError
from src.core.utils import clamp_page, now_str, Page
from src.database.repository import BaseRepository
from src.modules.base import BaseService

LEAD_STATUSES = ("new", "contacted", "qualified", "won", "lost")
ACTIVITY_TYPES = ("call", "email", "meeting", "reminder", "note", "task")


class LeadRepository(BaseRepository):
    """``leads`` jadvali repositoriysi."""

    table = "leads"
    searchable = ("name", "phone", "email", "source")
    soft_delete = False
    default_order = "id DESC"


class CrmService(BaseService):
    """Leadlar va mijoz faoliyatlarini boshqaruvchi servis."""

    def __init__(self, container) -> None:
        super().__init__(container)
        self.leads = LeadRepository(self.db)

    # ------------------------------------------------------------------ #
    #  Leadlar
    # ------------------------------------------------------------------ #

    def list_leads(self, page: int = 1, per_page: int = 25,
                   status: str | None = None,
                   search: str | None = None) -> Page:
        """Sahifalangan leadlar ro'yxati."""
        filters = {"status": status} if status else None
        return self.leads.list(page=page, per_page=per_page,
                               search=search, filters=filters)

    def get_lead(self, lead_id: int) -> dict:
        """Leadni qaytaradi; topilmasa xato."""
        lead = self.leads.get(lead_id)
        if not lead:
            raise NotFoundError(f"Lead topilmadi (id={lead_id}).")
        return lead

    def create_lead(self, data: dict, user: dict | None = None) -> int:
        """Yangi lead qo'shadi."""
        name = str(data.get("name") or "").strip()
        if not name:
            raise ValidationError("Lead nomi bo'sh bo'lishi mumkin emas.")
        lead_id = self.leads.create({
            "name": name,
            "phone": str(data.get("phone") or "").strip(),
            "email": str(data.get("email") or "").strip(),
            "source": str(data.get("source") or "").strip(),
            "status": "new",
            "assigned_to": data.get("assigned_to"),
            "note": str(data.get("note") or ""),
        })
        self.audit.log("lead.create", user=user, entity="lead",
                       entity_id=lead_id, details=name)
        return lead_id

    def update_lead(self, lead_id: int, data: dict,
                    user: dict | None = None) -> bool:
        """Lead ma'lumotlarini yangilaydi."""
        self.get_lead(lead_id)
        allowed = {"name", "phone", "email", "source", "assigned_to", "note"}
        payload = {k: v for k, v in data.items() if k in allowed}
        ok = self.leads.update(lead_id, payload)
        self.audit.log("lead.update", user=user, entity="lead", entity_id=lead_id)
        return ok

    def change_lead_status(self, lead_id: int, status: str,
                           user: dict | None = None) -> int | None:
        """
        Lead holatini o'zgartiradi. ``won`` holatida avtomatik mijoz
        yaratiladi va uning ``id`` si qaytariladi.
        """
        if status not in LEAD_STATUSES:
            raise ValidationError(f"Noma'lum lead holati: {status}")
        lead = self.get_lead(lead_id)
        if lead["status"] in ("won", "lost") and status not in ("won", "lost"):
            raise StateError("Yakunlangan leadni orqaga qaytarib bo'lmaydi.")

        customer_id: int | None = lead.get("customer_id")
        if status == "won" and not customer_id:
            customers = self.container.get("customers")
            customer_id = customers.create({
                "name": lead["name"], "phone": lead["phone"],
                "email": lead["email"],
                "note": f"Lead #{lead_id} dan konvertatsiya",
            }, user=user)

        self.leads.update(lead_id, {"status": status, "customer_id": customer_id})
        self.audit.log("lead.status", user=user, entity="lead",
                       entity_id=lead_id, details=f"{lead['status']} -> {status}")
        return customer_id

    # ------------------------------------------------------------------ #
    #  Faoliyatlar
    # ------------------------------------------------------------------ #

    def add_activity(self, subject: str, activity_type: str = "note",
                     customer_id: int | None = None,
                     lead_id: int | None = None, details: str = "",
                     due_at: str | None = None,
                     assigned_to: int | None = None,
                     user: dict | None = None) -> int:
        """Yangi faoliyat (qo'ng'iroq/uchrashuv/eslatma/vazifa) qo'shadi."""
        subject = (subject or "").strip()
        if not subject:
            raise ValidationError("Faoliyat mavzusi bo'sh bo'lishi mumkin emas.")
        if activity_type not in ACTIVITY_TYPES:
            raise ValidationError(f"Noma'lum faoliyat turi: {activity_type}")
        activity_id = self.db.insert("crm_activities", {
            "activity_type": activity_type,
            "customer_id": customer_id,
            "lead_id": lead_id,
            "subject": subject,
            "details": details,
            "due_at": due_at,
            "status": "open",
            "assigned_to": assigned_to or (user.get("id") if user else None),
            "created_by": user.get("id") if user else None,
            "created_at": now_str(),
        })
        self.audit.log("crm.activity_create", user=user, entity="activity",
                       entity_id=activity_id, details=subject)
        return activity_id

    def complete_activity(self, activity_id: int,
                          user: dict | None = None) -> bool:
        """Faoliyatni bajarilgan deb belgilaydi."""
        activity = self.db.query_one(
            "SELECT * FROM crm_activities WHERE id = ?", (activity_id,))
        if not activity:
            raise NotFoundError(f"Faoliyat topilmadi (id={activity_id}).")
        if activity["status"] != "open":
            raise StateError("Faoliyat allaqachon yakunlangan.")
        self.db.update("crm_activities", {
            "status": "done", "done_at": now_str(),
        }, "id = ?", (activity_id,))
        self.audit.log("crm.activity_done", user=user, entity="activity",
                       entity_id=activity_id)
        return True

    def list_activities(self, page: int = 1, per_page: int = 25,
                        status: str | None = None,
                        customer_id: int | None = None,
                        lead_id: int | None = None,
                        assigned_to: int | None = None) -> Page:
        """Faoliyatlar ro'yxati (filtrlar bilan)."""
        page, per_page = clamp_page(page, per_page)
        where, params = ["1=1"], []
        if status:
            where.append("a.status = ?")
            params.append(status)
        if customer_id:
            where.append("a.customer_id = ?")
            params.append(customer_id)
        if lead_id:
            where.append("a.lead_id = ?")
            params.append(lead_id)
        if assigned_to:
            where.append("a.assigned_to = ?")
            params.append(assigned_to)
        cond = " AND ".join(where)
        base = ("FROM crm_activities a "
                "LEFT JOIN customers c ON c.id = a.customer_id "
                "LEFT JOIN leads l ON l.id = a.lead_id WHERE " + cond)
        total = int(self.db.scalar(f"SELECT COUNT(*) {base}", tuple(params), 0) or 0)
        items = self.db.query(
            f"SELECT a.*, c.name AS customer_name, l.name AS lead_name {base} "
            f"ORDER BY a.id DESC LIMIT ? OFFSET ?",
            tuple(params) + (per_page, (page - 1) * per_page),
        )
        return Page(items=items, page=page, per_page=per_page, total=total)

    def due_reminders(self, assigned_to: int | None = None,
                      limit: int = 20) -> list[dict]:
        """Muddati kelgan (yoki o'tgan) ochiq faoliyatlar — eslatmalar paneli."""
        where, params = ["a.status = 'open'", "a.due_at IS NOT NULL",
                         "a.due_at <= ?"], [now_str()]
        if assigned_to:
            where.append("a.assigned_to = ?")
            params.append(assigned_to)
        return self.db.query(
            "SELECT a.*, c.name AS customer_name, l.name AS lead_name "
            "FROM crm_activities a "
            "LEFT JOIN customers c ON c.id = a.customer_id "
            "LEFT JOIN leads l ON l.id = a.lead_id "
            f"WHERE {' AND '.join(where)} ORDER BY a.due_at LIMIT ?",
            tuple(params) + (limit,),
        )

    # ------------------------------------------------------------------ #
    #  Mijoz tarixi
    # ------------------------------------------------------------------ #

    def customer_timeline(self, customer_id: int, limit: int = 30) -> dict:
        """Mijozning faoliyatlari va savdo hujjatlari (yagona lenta)."""
        activities = self.db.query(
            "SELECT * FROM crm_activities WHERE customer_id = ? "
            "ORDER BY id DESC LIMIT ?", (customer_id, limit),
        )
        sales = self.db.query(
            "SELECT id, number, doc_type, status, total, doc_date "
            "FROM sales_docs WHERE customer_id = ? "
            "ORDER BY id DESC LIMIT ?", (customer_id, limit),
        )
        return {"activities": activities, "sales": sales}
