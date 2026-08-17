# -*- coding: utf-8 -*-
"""Savdo va ombor integratsion testlari."""
from __future__ import annotations

import unittest
from decimal import Decimal

from src.core.errors import (
    InsufficientStockError, StateError, ValidationError,
)
from tests.base import ERPTestCase


class TestInventory(ERPTestCase):
    def test_stock_in_out(self):
        pid = self.make_product("Ombor test")
        wh = self.S.get("inventory").default_warehouse_id()
        self.S.get("inventory").move_in(pid, wh, 50)
        self.assertEqual(self.S.get("inventory").stock_level(pid, wh),
                         Decimal("50.00"))
        self.S.get("inventory").move_out(pid, wh, 20)
        self.assertEqual(self.S.get("inventory").stock_level(pid, wh),
                         Decimal("30.00"))

    def test_negative_stock_blocked(self):
        pid = self.make_product("Kam qoldiq")
        wh = self.S.get("inventory").default_warehouse_id()
        self.S.get("inventory").move_in(pid, wh, 5)
        with self.assertRaises(InsufficientStockError):
            self.S.get("inventory").move_out(pid, wh, 10)

    def test_transfer(self):
        pid = self.make_product("Transfer test")
        inv = self.S.get("inventory")
        wh1 = inv.default_warehouse_id()
        wh2 = inv.create_warehouse("Filial", user=self.user)
        inv.move_in(pid, wh1, 40)
        inv.transfer(pid, wh1, wh2, 15, user=self.user)
        self.assertEqual(inv.stock_level(pid, wh1), Decimal("25.00"))
        self.assertEqual(inv.stock_level(pid, wh2), Decimal("15.00"))

    def test_inventory_count(self):
        pid = self.make_product("Sanoq test")
        inv = self.S.get("inventory")
        wh = inv.default_warehouse_id()
        inv.move_in(pid, wh, 100)
        count_id = inv.start_count(wh, self.user)
        inv.set_count_item(count_id, pid, 95)  # 5 kamomad
        adjusted = inv.complete_count(count_id, self.user)
        self.assertEqual(adjusted, 1)
        self.assertEqual(inv.stock_level(pid, wh), Decimal("95.00"))

    def test_barcode_lookup(self):
        pid = self.make_product("Shtrix test", barcode="TEST12345")
        found = self.S.get("products").find_by_barcode("TEST12345")
        self.assertEqual(found["id"], pid)
        self.assertIsNone(self.S.get("products").find_by_barcode("yo'q"))


class TestSales(ERPTestCase):
    def _setup_product(self, qty=100, price=15000, cost=10000):
        pid = self.make_product("Savdo mahsuloti", sale_price=price,
                                cost_price=cost)
        self.stock_up(pid, qty, cost)
        return pid

    def test_invoice_flow(self):
        pid = self._setup_product()
        sales = self.S.get("sales")
        wh = self.S.get("inventory").default_warehouse_id()
        doc_id = sales.create_doc("invoice", None, wh,
                                  [{"product_id": pid, "quantity": 10}],
                                  user=self.user)
        doc = sales.get_doc(doc_id)["doc"]
        self.assertEqual(doc["total"], Decimal("150000.00"))
        self.assertEqual(doc["status"], "draft")
        sales.confirm(doc_id, user=self.user)
        # Ombordan chiqim
        self.assertEqual(self.S.get("inventory").stock_level(pid, wh),
                         Decimal("90.00"))

    def test_vat_calculation(self):
        pid = self._setup_product(price=11200)
        sales = self.S.get("sales")
        doc_id = sales.create_doc("invoice", None, None,
                                  [{"product_id": pid, "quantity": 1}],
                                  user=self.user)
        doc = sales.get_doc(doc_id)["doc"]
        # 11200 dan 12% QQS = 1200
        self.assertEqual(doc["vat_amount"], Decimal("1200.00"))

    def test_customer_discount(self):
        pid = self._setup_product(price=10000)
        cust = self.S.get("customers").create(
            {"name": "Chegirmali", "discount_percent": 10}, self.user)
        sales = self.S.get("sales")
        doc_id = sales.create_doc("invoice", cust, None,
                                  [{"product_id": pid, "quantity": 10}],
                                  user=self.user)
        doc = sales.get_doc(doc_id)["doc"]
        # 100000 - 10% = 90000
        self.assertEqual(doc["total"], Decimal("90000.00"))

    def test_payment_status(self):
        pid = self._setup_product()
        sales = self.S.get("sales")
        doc_id = sales.create_doc("invoice", None, None,
                                  [{"product_id": pid, "quantity": 10}],
                                  user=self.user)
        sales.confirm(doc_id, user=self.user)
        sales.register_payment(doc_id, 50000, user=self.user)
        self.assertEqual(sales.get_doc(doc_id)["doc"]["status"], "partial")
        # Qoldiqdan ortiq to'lov rad etiladi (qoldiq 100000)
        with self.assertRaises(ValidationError):
            sales.register_payment(doc_id, 200000, user=self.user)
        # To'liq to'lash -> paid
        sales.register_payment(doc_id, 100000, user=self.user)
        self.assertEqual(sales.get_doc(doc_id)["doc"]["status"], "paid")
        # To'langan hujjatga qayta to'lov -> StateError
        with self.assertRaises(StateError):
            sales.register_payment(doc_id, 1, user=self.user)

    def test_return_flow(self):
        pid = self._setup_product()
        sales = self.S.get("sales")
        wh = self.S.get("inventory").default_warehouse_id()
        doc_id = sales.create_doc("invoice", None, wh,
                                  [{"product_id": pid, "quantity": 10}],
                                  user=self.user)
        sales.confirm(doc_id, user=self.user)
        ret_id = sales.create_return(doc_id, [{"product_id": pid,
                                               "quantity": 3}],
                                     user=self.user)
        self.assertEqual(self.S.get("inventory").stock_level(pid, wh),
                         Decimal("93.00"))
        with self.assertRaises(ValidationError):
            sales.create_return(doc_id, [{"product_id": pid, "quantity": 100}],
                                user=self.user)

    def test_pos_sale(self):
        pid = self._setup_product(price=5000)
        result = self.S.get("sales").pos_sale(
            [{"product_id": pid, "quantity": 3}], user=self.user)
        self.assertEqual(result["doc"]["status"], "paid")
        self.assertEqual(result["doc"]["total"], Decimal("15000.00"))

    def test_conversion_chain(self):
        pid = self._setup_product()
        sales = self.S.get("sales")
        quo = sales.create_doc("quotation", None, None,
                               [{"product_id": pid, "quantity": 2}],
                               user=self.user)
        order = sales.convert(quo, user=self.user)
        self.assertEqual(sales.get_doc(order)["doc"]["doc_type"], "order")
        invoice = sales.convert(order, user=self.user)
        self.assertEqual(sales.get_doc(invoice)["doc"]["doc_type"], "invoice")

    def test_weighted_average_cost(self):
        pid = self.make_product("O'rtacha tannarx", cost_price=0)
        purchases = self.S.get("purchases")
        wh = self.S.get("inventory").default_warehouse_id()
        p1 = purchases.create(None, wh,
                              [{"product_id": pid, "quantity": 100,
                                "price": 10000}], user=self.user)
        purchases.receive(p1, self.user)
        p2 = purchases.create(None, wh,
                              [{"product_id": pid, "quantity": 100,
                                "price": 12000}], user=self.user)
        purchases.receive(p2, self.user)
        # (100*10000 + 100*12000) / 200 = 11000
        self.assertEqual(self.S.get("products").get(pid)["cost_price"],
                         Decimal("11000.00"))


if __name__ == "__main__":
    unittest.main()
