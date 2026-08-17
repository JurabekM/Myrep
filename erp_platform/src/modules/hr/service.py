# -*- coding: utf-8 -*-
"""
HR servisi: bo'limlar, xodimlar, davomat va ta'tillar.

* Xodim kodi avtomatik: ``E00001``
* Davomat: kun kesimida upsert (kelish/ketish vaqti, soat, holat)
* Ta'til: so'rov -> tasdiqlash/rad etish, kunlar avtomatik hisoblanadi
"""
from __future__ import annotations

from datetime import date

from src.core.errors import NotFoundError, StateError, ValidationError
from src.core.utils import (
    clamp_page, D, now_str, Page, parse_date, today_str,
)
from src.database.repository import BaseRepository
from src.modules.base import BaseService

ATTENDANCE_STATUSES = ("present", "absent", "late", "leave", "holiday")
LEAVE_TYPES = ("annual", "sick", "unpaid", "maternity", "other")


class EmployeeRepository(BaseRepository):
    """``employees`` jadvali repositoriysi (soft delete o'rniga status)."""

    table = "employees"
    searchable = ("full_name", "code", "phone", "position")
    soft_delete = False
    default_order = "full_name ASC"


class HrService(BaseService):
    """Xodimlar va davomatni boshqaruvchi servis."""

    def __init__(self, container) -> None:
        super().__init__(container)
        self.repo = EmployeeRepository(self.db)

    # ------------------------------------------------------------------ #
    #  Bo'limlar
    # ------------------------------------------------------------------ #

    def departments(self) -> list[dict]:
        """Faol bo'limlar (xodimlar soni bilan)."""
        return self.db.query(
            "SELECT d.*, (SELECT COUNT(*) FROM employees e "
            "WHERE e.department_id = d.id AND e.status = 'active') AS employee_count "
            "FROM departments d WHERE d.is_active = 1 ORDER BY d.name")

    def create_department(self, name: str, parent_id: int | None = None,
                          user: dict | None = None) -> int:
        """Yangi bo'lim qo'shadi."""
        name = (name or "").strip()
        if not name:
            raise ValidationError("Bo'lim nomi bo'sh bo'lishi mumkin emas.")
        department_id = self.db.insert(
            "departments", {"name": name, "parent_id": parent_id, "is_active": 1})
        self.audit.log("department.create", user=user, entity="department",
                       entity_id=department_id, details=name)
        return department_id

    # ------------------------------------------------------------------ #
    #  Xodimlar
    # ------------------------------------------------------------------ #

    def list_employees(self, page: int = 1, per_page: int = 25,
                       search: str | None = None,
                       department_id: int | None = None,
                       status: str | None = "active") -> Page:
        """Sahifalangan xodimlar ro'yxati."""
        filters: dict = {}
        if department_id:
            filters["department_id"] = department_id
        if status:
            filters["status"] = status
        return self.repo.list(page=page, per_page=per_page, search=search,
                              filters=filters or None)

    def get_employee(self, employee_id: int) -> dict:
        """Xodimni qaytaradi; topilmasa xato."""
        employee = self.repo.get(employee_id)
        if not employee:
            raise NotFoundError(f"Xodim topilmadi (id={employee_id}).")
        return employee

    def create_employee(self, data: dict, user: dict | None = None) -> int:
        """Yangi xodim qo'shadi (kod avtomatik)."""
        full_name = str(data.get("full_name") or "").strip()
        if not full_name:
            raise ValidationError("Xodim F.I.Sh. bo'sh bo'lishi mumkin emas.")
        salary = D(data.get("salary", 0))
        if salary < 0:
            raise ValidationError("Maosh manfiy bo'lishi mumkin emas.")
        with self.db.transaction():
            employee_id = self.repo.create({
                "full_name": full_name,
                "department_id": data.get("department_id"),
                "position": str(data.get("position") or "").strip(),
                "phone": str(data.get("phone") or "").strip(),
                "email": str(data.get("email") or "").strip(),
                "hire_date": data.get("hire_date") or today_str(),
                "birth_date": data.get("birth_date"),
                "salary": salary,
                "status": "active",
                "tin": str(data.get("tin") or "").strip(),
                "address": str(data.get("address") or "").strip(),
                "user_id": data.get("user_id"),
            })
            if not data.get("code"):
                self.repo.update(employee_id, {"code": f"E{employee_id:05d}"})
        self.audit.log("employee.create", user=user, entity="employee",
                       entity_id=employee_id, details=full_name)
        return employee_id

    def update_employee(self, employee_id: int, data: dict,
                        user: dict | None = None) -> bool:
        """Xodim ma'lumotlarini yangilaydi."""
        self.get_employee(employee_id)
        allowed = {"full_name", "department_id", "position", "phone", "email",
                   "hire_date", "birth_date", "salary", "status", "tin",
                   "address", "user_id", "code"}
        payload = {k: v for k, v in data.items() if k in allowed}
        if "salary" in payload:
            payload["salary"] = D(payload["salary"])
            if payload["salary"] < 0:
                raise ValidationError("Maosh manfiy bo'lishi mumkin emas.")
        if "status" in payload and payload["status"] not in (
                "active", "leave", "terminated"):
            raise ValidationError(f"Noma'lum holat: {payload['status']}")
        ok = self.repo.update(employee_id, payload)
        self.audit.log("employee.update", user=user, entity="employee",
                       entity_id=employee_id)
        return ok

    def terminate(self, employee_id: int, user: dict | None = None) -> bool:
        """Xodimni ishdan bo'shatadi (tarixiy yozuvlar saqlanadi)."""
        ok = self.update_employee(employee_id, {"status": "terminated"}, user)
        self.audit.log("employee.terminate", user=user, entity="employee",
                       entity_id=employee_id)
        return ok

    # ------------------------------------------------------------------ #
    #  Davomat
    # ------------------------------------------------------------------ #

    def mark_attendance(self, employee_id: int, work_date: str | None = None,
                        status: str = "present", check_in: str = "",
                        check_out: str = "", note: str = "",
                        user: dict | None = None) -> None:
        """Davomat belgisi (kun bo'yicha upsert)."""
        if status not in ATTENDANCE_STATUSES:
            raise ValidationError(f"Noma'lum davomat holati: {status}")
        self.get_employee(employee_id)
        work_date = work_date or today_str()
        hours = self._calc_hours(check_in, check_out)
        existing = self.db.query_one(
            "SELECT id FROM attendance WHERE employee_id = ? AND work_date = ?",
            (employee_id, work_date))
        payload = {"status": status, "check_in": check_in,
                   "check_out": check_out, "hours": hours, "note": note}
        if existing:
            self.db.update("attendance", payload, "id = ?", (existing["id"],))
        else:
            payload.update({"employee_id": employee_id, "work_date": work_date})
            self.db.insert("attendance", payload)

    def bulk_mark(self, work_date: str | None = None,
                  status: str = "present", user: dict | None = None) -> int:
        """Barcha faol xodimlarga bir kunlik davomat qo'yadi (belgilanmaganlarga)."""
        work_date = work_date or today_str()
        employees = self.db.query(
            "SELECT id FROM employees WHERE status = 'active'")
        marked = 0
        for employee in employees:
            existing = self.db.query_one(
                "SELECT id FROM attendance "
                "WHERE employee_id = ? AND work_date = ?",
                (employee["id"], work_date))
            if not existing:
                self.mark_attendance(employee["id"], work_date, status,
                                     user=user)
                marked += 1
        self.audit.log("attendance.bulk", user=user,
                       details=f"{work_date}: {marked} ta xodim ({status})")
        return marked

    def attendance_sheet(self, year: int, month: int) -> list[dict]:
        """Oylik davomat jadvali: xodim kesimida kunlar soni (holat bo'yicha)."""
        prefix = f"{year:04d}-{month:02d}-%"
        return self.db.query(
            "SELECT e.id, e.code, e.full_name, "
            "  SUM(CASE WHEN a.status = 'present' THEN 1 ELSE 0 END) AS days_present, "
            "  SUM(CASE WHEN a.status = 'late' THEN 1 ELSE 0 END) AS days_late, "
            "  SUM(CASE WHEN a.status = 'absent' THEN 1 ELSE 0 END) AS days_absent, "
            "  SUM(CASE WHEN a.status = 'leave' THEN 1 ELSE 0 END) AS days_leave, "
            "  COALESCE(SUM(a.hours), 0) AS total_hours "
            "FROM employees e "
            "LEFT JOIN attendance a ON a.employee_id = e.id "
            "  AND a.work_date LIKE ? "
            "WHERE e.status = 'active' "
            "GROUP BY e.id, e.code, e.full_name ORDER BY e.full_name",
            (prefix,))

    # ------------------------------------------------------------------ #
    #  Ta'tillar
    # ------------------------------------------------------------------ #

    def request_leave(self, employee_id: int, leave_type: str,
                      date_from: str, date_to: str, note: str = "",
                      user: dict | None = None) -> int:
        """Ta'til so'rovi yaratadi (kunlar soni avtomatik)."""
        if leave_type not in LEAVE_TYPES:
            raise ValidationError(f"Noma'lum ta'til turi: {leave_type}")
        self.get_employee(employee_id)
        start = parse_date(date_from)
        end = parse_date(date_to)
        if not start or not end or end < start:
            raise ValidationError("Ta'til sanalari noto'g'ri.")
        days = (end - start).days + 1
        leave_id = self.db.insert("leaves", {
            "employee_id": employee_id, "leave_type": leave_type,
            "date_from": start.isoformat(), "date_to": end.isoformat(),
            "days": days, "status": "pending", "note": note,
            "created_at": now_str(),
        })
        self.audit.log("leave.request", user=user, entity="leave",
                       entity_id=leave_id,
                       details=f"xodim #{employee_id}, {days} kun")
        return leave_id

    def decide_leave(self, leave_id: int, approve: bool,
                     user: dict | None = None) -> None:
        """Ta'tilni tasdiqlaydi yoki rad etadi."""
        leave = self.db.query_one("SELECT * FROM leaves WHERE id = ?", (leave_id,))
        if not leave:
            raise NotFoundError(f"Ta'til so'rovi topilmadi (id={leave_id}).")
        if leave["status"] != "pending":
            raise StateError("Bu so'rov allaqachon ko'rib chiqilgan.")
        status = "approved" if approve else "rejected"
        self.db.update("leaves", {
            "status": status,
            "approved_by": user.get("id") if user else None,
        }, "id = ?", (leave_id,))
        self.audit.log(f"leave.{status}", user=user, entity="leave",
                       entity_id=leave_id)

    def list_leaves(self, page: int = 1, per_page: int = 25,
                    status: str | None = None,
                    employee_id: int | None = None) -> Page:
        """Ta'til so'rovlari ro'yxati."""
        page, per_page = clamp_page(page, per_page)
        where, params = ["1=1"], []
        if status:
            where.append("lv.status = ?")
            params.append(status)
        if employee_id:
            where.append("lv.employee_id = ?")
            params.append(employee_id)
        cond = " AND ".join(where)
        total = int(self.db.scalar(
            f"SELECT COUNT(*) FROM leaves lv WHERE {cond}",
            tuple(params), 0) or 0)
        items = self.db.query(
            f"SELECT lv.*, e.full_name, e.code FROM leaves lv "
            f"JOIN employees e ON e.id = lv.employee_id "
            f"WHERE {cond} ORDER BY lv.id DESC LIMIT ? OFFSET ?",
            tuple(params) + (per_page, (page - 1) * per_page))
        return Page(items=items, page=page, per_page=per_page, total=total)

    # ------------------------------------------------------------------ #
    #  Ichki yordamchilar
    # ------------------------------------------------------------------ #

    @staticmethod
    def _calc_hours(check_in: str, check_out: str):
        """``HH:MM`` juftligidan ish soatini hisoblaydi (xato bo'lsa 0)."""
        try:
            h1, m1 = map(int, check_in.strip().split(":"))
            h2, m2 = map(int, check_out.strip().split(":"))
            minutes = (h2 * 60 + m2) - (h1 * 60 + m1)
            return D(D(max(minutes, 0)) / 60) if minutes > 0 else D(0)
        except (ValueError, AttributeError):
            return D(0)
