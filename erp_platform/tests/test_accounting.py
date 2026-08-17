# -*- coding: utf-8 -*-
"""Buxgalteriya testlari: dvoyna zapis, balans, avto-o'tkazmalar, payroll."""
from __future__ import annotations

import unittest
from decimal import Decimal

from src.core.errors import StateError, ValidationError
from src.core.utils import today_str
from tests.base import ERPTestCase


class TestAccounting(ERPTestCase):
    def test_double_entry_requires_balance(self):
        acc = self.S.get("accounting")
        with self.assertRaises(ValidationError):
            acc.create_entry("Nomutanosib",
                             [{"account": "5010", "debit": 100},
                              {"account": "9010", "credit": 99}],
                             user=self.user)

    def test_manual_entry_and_balance(self):
        acc = self.S.get("accounting")
        acc.create_entry("Ustav kapitali",
                         [{"account": "5110", "debit": 5000000},
                          {"account": "8330", "credit": 5000000}],
                         user=self.user)
        self.assertEqual(acc.account_balance("5110"), Decimal("5000000.00"))
        self.assertEqual(acc.account_balance("8330"), Decimal("5000000.00"))

    def test_sale_auto_journal(self):
        pid = self.make_product("Buxgalteriya mahsuloti", sale_price=11200,
                                cost_price=8000)
        self.stock_up(pid, 100, 8000)
        sales = self.S.get("sales")
        doc_id = sales.create_doc("invoice", None, None,
                                  [{"product_id": pid, "quantity": 10}],
                                  user=self.user)
        sales.confirm(doc_id, user=self.user)
        acc = self.S.get("accounting")
        # Dt 4010 = 112000, Kt 9010 = 100000, Kt 6520 = 12000
        self.assertEqual(acc.account_balance("4010"), Decimal("112000.00"))
        self.assertEqual(acc.account_balance("9010"), Decimal("100000.00"))
        self.assertEqual(acc.account_balance("6520"), Decimal("12000.00"))
        # Tannarx: Dt 9110 = 80000, Kt 2900 = 80000
        self.assertEqual(acc.account_balance("9110"), Decimal("80000.00"))

    def test_balance_sheet_balances(self):
        acc = self.S.get("accounting")
        acc.create_entry("Kapital",
                         [{"account": "5110", "debit": 10000000},
                          {"account": "8330", "credit": 10000000}],
                         user=self.user)
        pid = self.make_product("BS mahsulot", sale_price=15000,
                                cost_price=10000)
        self.stock_up(pid, 50, 10000)
        sales = self.S.get("sales")
        doc = sales.create_doc("invoice", None, None,
                               [{"product_id": pid, "quantity": 10}],
                               user=self.user)
        sales.confirm(doc, user=self.user)
        bs = acc.balance_sheet(today_str())
        self.assertTrue(bs["balanced"],
                        f"Aktiv={bs['total_assets']} != "
                        f"Passiv={bs['total_liabilities'] + bs['total_equity']}")

    def test_trial_balance_equal(self):
        acc = self.S.get("accounting")
        acc.create_entry("Test",
                         [{"account": "5010", "debit": 1000},
                          {"account": "9010", "credit": 1000}],
                         user=self.user)
        tb = acc.trial_balance(today_str())
        total_debit = sum(r["total_debit"] for r in tb)
        total_credit = sum(r["total_credit"] for r in tb)
        self.assertEqual(total_debit, total_credit)

    def test_payment_updates_cash(self):
        payments = self.S.get("payments")
        payments.other_income(500000, "Test kirim", method="cash",
                              user=self.user)
        self.assertEqual(payments.cash_balance(), Decimal("500000.00"))
        payments.expense(200000, "Test xarajat", method="cash",
                         user=self.user)
        self.assertEqual(payments.cash_balance(), Decimal("300000.00"))

    def test_vat_report(self):
        pid = self.make_product("QQS mahsulot", sale_price=11200,
                                cost_price=8000)
        self.stock_up(pid, 100, 8000)
        sales = self.S.get("sales")
        doc = sales.create_doc("invoice", None, None,
                               [{"product_id": pid, "quantity": 10}],
                               user=self.user)
        sales.confirm(doc, user=self.user)
        vat = self.S.get("accounting").vat_report(f"{today_str()[:7]}-01",
                                                  f"{today_str()[:7]}-31")
        self.assertEqual(vat["output_vat"], Decimal("12000.00"))


class TestAssets(ERPTestCase):
    def test_depreciation(self):
        assets = self.S.get("assets")
        assets.create_asset({"name": "Kompyuter", "cost": 12000000,
                             "useful_life_months": 24}, self.user)
        result = assets.run_depreciation(today_str()[:7], self.user)
        # 12 000 000 / 24 = 500 000
        self.assertEqual(result["total"], Decimal("500000.00"))
        # Takror hisoblash bloklanadi
        with self.assertRaises(StateError):
            assets.run_depreciation(today_str()[:7], self.user)


class TestPayroll(ERPTestCase):
    def test_payroll_calculation(self):
        hr = self.S.get("hr")
        hr.create_employee({"full_name": "Test Xodim", "salary": 5000000},
                           self.user)
        payroll = self.S.get("payroll")
        run_id = payroll.create_run(today_str()[:7], self.user)
        run = payroll.get_run(run_id)["run"]
        # 5 000 000; soliq 12% = 600 000; INPS 0.1% = 5 000; net = 4 395 000
        self.assertEqual(run["total_gross"], Decimal("5000000.00"))
        self.assertEqual(run["total_tax"], Decimal("605000.00"))
        self.assertEqual(run["total_net"], Decimal("4395000.00"))

    def test_payroll_approve_journal(self):
        hr = self.S.get("hr")
        hr.create_employee({"full_name": "Xodim 2", "salary": 3000000},
                           self.user)
        payroll = self.S.get("payroll")
        run_id = payroll.create_run(today_str()[:7], self.user)
        payroll.approve(run_id, self.user)
        acc = self.S.get("accounting")
        # Kt 6710 (net + ushlanma) va Kt 6410 (soliq)
        self.assertGreater(acc.account_balance("6710"), Decimal("0"))
        self.assertGreater(acc.account_balance("6410"), Decimal("0"))


if __name__ == "__main__":
    unittest.main()
