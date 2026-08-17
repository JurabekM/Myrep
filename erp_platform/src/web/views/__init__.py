# -*- coding: utf-8 -*-
"""Web sahifalar (view'lar) — har bir modul o'z marshrutlarini ro'yxatlaydi."""
from __future__ import annotations


def register_all(app, ctx) -> None:
    """Barcha view modullarini Flask ilovasiga ulaydi."""
    from src.web.views import (
        admin, analytics_view, crm_view, dashboard, finance, hr_view,
        inventory_view, purchases_view, sales_view,
    )

    for module in (dashboard, sales_view, inventory_view, purchases_view,
                   crm_view, finance, hr_view, analytics_view, admin):
        module.register(app, ctx)
