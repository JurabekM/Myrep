# -*- coding: utf-8 -*-
"""
Asosiy vositalar servisi.

* Aktivlarni ro'yxatga olish (qiymat, foydali muddat, qoldiq qiymat)
* To'g'ri chiziqli (straight-line) amortizatsiya: oylik hisob-kitob
  ``(qiymat - qoldiq qiymat) / foydali muddat (oy)``
* Har oy uchun bitta jurnal o'tkazmasi: Dt 9410 / Kt 0200
  (davrni takror hisoblashdan himoya bor)
"""
from __future__ import annotations

from decimal import Decimal

from src.core.errors import NotFoundError, StateError, ValidationError
from src.core.utils import D, now_str, Page, clamp_page, today_str
from src.modules.base import BaseService


class AssetService(BaseService):
    """Asosiy vositalar va amortizatsiyani boshqaruvchi servis."""

    def create_asset(self, data: dict, user: dict | None = None) -> int:
        """Yangi asosiy vositani ro'yxatga oladi."""
        name = str(data.get("name") or "").strip()
        if not name:
            raise ValidationError("Aktiv nomi bo'sh bo'lishi mumkin emas.")
        cost = D(data.get("cost"))
        salvage = D(data.get("salvage_value", 0))
        life = int(data.get("useful_life_months") or 60)
        if cost <= 0:
            raise ValidationError("Aktiv qiymati musbat bo'lishi kerak.")
        if salvage < 0 or salvage >= cost:
            raise ValidationError(
                "Qoldiq qiymat 0 dan katta-teng va qiymatdan kichik bo'lsin.")
        if life <= 0:
            raise ValidationError("Foydali muddat musbat bo'lishi kerak.")

        asset_id = self.db.insert("assets", {
            "code": str(data.get("code") or "").strip(),
            "name": name,
            "purchase_date": data.get("purchase_date") or today_str(),
            "cost": cost,
            "salvage_value": salvage,
            "useful_life_months": life,
            "depreciation_method": "straight_line",
            "accumulated_depreciation": 0,
            "status": "active",
            "note": str(data.get("note") or ""),
            "created_at": now_str(),
        })
        if not data.get("code"):
            self.db.update("assets", {"code": f"AV{asset_id:05d}"},
                           "id = ?", (asset_id,))
        self.audit.log("asset.create", user=user, entity="asset",
                       entity_id=asset_id, details=f"{name} ({cost})")
        return asset_id

    def get(self, asset_id: int) -> dict:
        """Aktivni qaytaradi (qoldiq qiymat hisobi bilan)."""
        asset = self.db.query_one("SELECT * FROM assets WHERE id = ?", (asset_id,))
        if not asset:
            raise NotFoundError(f"Aktiv topilmadi (id={asset_id}).")
        asset["book_value"] = D(
            D(asset["cost"]) - D(asset["accumulated_depreciation"]))
        asset["monthly_depreciation"] = self._monthly_amount(asset)
        return asset

    def list_assets(self, page: int = 1, per_page: int = 25,
                    status: str | None = None) -> Page:
        """Aktivlar ro'yxati."""
        page, per_page = clamp_page(page, per_page)
        where, params = ["1=1"], []
        if status:
            where.append("status = ?")
            params.append(status)
        cond = " AND ".join(where)
        total = int(self.db.scalar(
            f"SELECT COUNT(*) FROM assets WHERE {cond}", tuple(params), 0) or 0)
        items = self.db.query(
            f"SELECT * FROM assets WHERE {cond} ORDER BY id DESC "
            f"LIMIT ? OFFSET ?",
            tuple(params) + (per_page, (page - 1) * per_page))
        for asset in items:
            asset["book_value"] = D(
                D(asset["cost"]) - D(asset["accumulated_depreciation"]))
        return Page(items=items, page=page, per_page=per_page, total=total)

    def dispose(self, asset_id: int, user: dict | None = None) -> None:
        """Aktivni hisobdan chiqaradi (holat: disposed)."""
        asset = self.get(asset_id)
        if asset["status"] != "active":
            raise StateError("Aktiv allaqachon hisobdan chiqarilgan.")
        self.db.update("assets", {"status": "disposed"}, "id = ?", (asset_id,))
        self.audit.log("asset.dispose", user=user, entity="asset",
                       entity_id=asset_id, details=asset["name"])

    # ------------------------------------------------------------------ #
    #  Amortizatsiya
    # ------------------------------------------------------------------ #

    def run_depreciation(self, period: str, user: dict | None = None) -> dict:
        """
        Berilgan davr (``YYYY-MM``) uchun amortizatsiya hisoblaydi.

        Barcha faol aktivlar bo'yicha bitta jurnal o'tkazmasi yaratiladi
        (Dt 9410 / Kt 0200). Davr takror hisoblansa xato beradi.

        :return: ``{"total": ..., "count": ..., "entry_id": ...}``
        """
        if len(period) != 7 or period[4] != "-":
            raise ValidationError("Davr formati YYYY-MM bo'lishi kerak.")
        existing = self.db.query_one(
            "SELECT id FROM journal_entries "
            "WHERE ref_type = 'depreciation' AND memo LIKE ?",
            (f"%{period}%",))
        if existing:
            raise StateError(
                f"{period} davri uchun amortizatsiya allaqachon hisoblangan.")

        assets = self.db.query(
            "SELECT * FROM assets WHERE status = 'active'")
        total = D(0)
        count = 0
        with self.db.transaction():
            for asset in assets:
                amount = self._monthly_amount(asset)
                remaining = D(
                    D(asset["cost"]) - D(asset["salvage_value"])
                    - D(asset["accumulated_depreciation"]))
                amount = min(amount, max(remaining, D(0)))
                if amount <= 0:
                    continue
                self.db.update("assets", {
                    "accumulated_depreciation":
                        D(D(asset["accumulated_depreciation"]) + amount),
                }, "id = ?", (asset["id"],))
                total += amount
                count += 1

            entry_id = None
            if total > 0:
                accounting = self.container.get("accounting")
                entry_id = accounting.create_entry(
                    f"Amortizatsiya {period}",
                    [{"account": "9410", "debit": total},
                     {"account": "0200", "credit": total}],
                    entry_date=f"{period}-28", ref_type="depreciation",
                    user=user)

        self.audit.log("asset.depreciation", user=user, entity="asset",
                       details=f"{period}: {count} ta aktiv, jami {total}")
        return {"total": D(total), "count": count, "entry_id": entry_id}

    @staticmethod
    def _monthly_amount(asset: dict) -> Decimal:
        """Oylik amortizatsiya summasi (to'g'ri chiziqli usul)."""
        life = int(asset["useful_life_months"] or 0)
        if life <= 0:
            return D(0)
        return D((D(asset["cost"]) - D(asset["salvage_value"])) / life)
