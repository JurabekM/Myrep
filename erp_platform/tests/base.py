# -*- coding: utf-8 -*-
"""
Testlar uchun umumiy asos: har bir test klassiga izolyatsiyalangan,
vaqtinchalik papkadagi toza ERP konteksti beriladi.
"""
from __future__ import annotations

import shutil
import tempfile
import unittest
from pathlib import Path

from src.core.bootstrap import initialize


class ERPTestCase(unittest.TestCase):
    """
    Har bir TEST uchun vaqtinchalik papkada toza, izolyatsiyalangan baza
    yaratadi (testlar bir-biriga ta'sir qilmaydi).

    ``self.ctx`` — to'liq ilova konteksti; ``self.user`` — admin dict;
    ``self.S`` — servis konteyner qisqartmasi.
    """

    def setUp(self) -> None:
        self._tmp = Path(tempfile.mkdtemp(prefix="uzerp_test_"))
        self.ctx = initialize(self._tmp)
        self.S = self.ctx.services
        admin = self.ctx.db.query_one(
            "SELECT id, username, role FROM users WHERE role='administrator'")
        self.user = dict(admin)

    def tearDown(self) -> None:
        try:
            self.ctx.close()
        finally:
            shutil.rmtree(self._tmp, ignore_errors=True)

    # -- qulay yordamchilar -------------------------------------------- #

    def make_product(self, name="Test mahsulot", **kwargs) -> int:
        data = {"name": name, "sale_price": 10000, "cost_price": 6000}
        data.update(kwargs)
        return self.S.get("products").create(data, self.user)

    def stock_up(self, product_id, qty=100, price=6000) -> None:
        wh = self.S.get("inventory").default_warehouse_id()
        self.S.get("inventory").move_in(product_id, wh, qty, unit_cost=price)
