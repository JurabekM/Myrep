# -*- coding: utf-8 -*-
"""Core qatlam testlari: xavfsizlik, utils, kesh, konfiguratsiya."""
from __future__ import annotations

import unittest
from decimal import Decimal

from src.core.cache import TTLCache
from src.core.security import (
    CSRFProtect, RateLimiter, SignedTokenFactory, check_password_policy,
    hash_password, verify_password,
)
from src.core.utils import D, money, next_document_number


class TestSecurity(unittest.TestCase):
    def test_password_hash_roundtrip(self):
        h = hash_password("Parol123")
        self.assertTrue(verify_password("Parol123", h))
        self.assertFalse(verify_password("noto'g'ri", h))

    def test_password_hash_unique_salt(self):
        # Bir xil parol har safar boshqa xesh berishi kerak (tuz tasodifiy)
        self.assertNotEqual(hash_password("Parol123"), hash_password("Parol123"))

    def test_password_policy(self):
        self.assertIsNone(check_password_policy("Parol123"))
        self.assertIsNotNone(check_password_policy("qisqa"))
        self.assertIsNotNone(check_password_policy("faqatharflar"))
        self.assertIsNotNone(check_password_policy("12345678"))

    def test_signed_token(self):
        factory = SignedTokenFactory("maxfiy-kalit")
        token = factory.sign({"uid": 7}, ttl_seconds=60)
        payload = factory.verify(token)
        self.assertEqual(payload["uid"], 7)
        # Buzilgan token
        self.assertIsNone(factory.verify(token + "x"))
        # Boshqa kalit bilan tekshirish
        self.assertIsNone(SignedTokenFactory("boshqa").verify(token))

    def test_expired_token(self):
        factory = SignedTokenFactory("k")
        token = factory.sign({"uid": 1}, ttl_seconds=-1)
        self.assertIsNone(factory.verify(token))

    def test_rate_limiter(self):
        limiter = RateLimiter(max_requests=3, window_seconds=60)
        self.assertTrue(all(limiter.allow("ip1") for _ in range(3)))
        self.assertFalse(limiter.allow("ip1"))
        self.assertTrue(limiter.allow("ip2"))  # boshqa kalit alohida

    def test_csrf(self):
        csrf = CSRFProtect("kalit")
        token = csrf.issue("sessiya-abc")
        self.assertTrue(csrf.validate("sessiya-abc", token))
        self.assertFalse(csrf.validate("boshqa-sessiya", token))
        self.assertFalse(csrf.validate("sessiya-abc", "soxta"))


class TestUtils(unittest.TestCase):
    def test_decimal_conversion(self):
        self.assertEqual(D("12.5"), Decimal("12.50"))
        self.assertEqual(D(None), Decimal("0.00"))
        self.assertEqual(D("noto'g'ri"), Decimal("0.00"))
        self.assertEqual(D(0.1 + 0.2), Decimal("0.30"))  # float xatosisiz

    def test_money_format(self):
        self.assertEqual(money(1234567), "1 234 567")
        self.assertEqual(money(Decimal("1234.50")), "1 234.50")
        self.assertEqual(money(-500), "-500")

    def test_vat_extraction(self):
        # 112 000 dan 12% QQS ni ajratish
        total = D(112000)
        vat = D(total * 12 / 112)
        self.assertEqual(vat, Decimal("12000.00"))


class TestCache(unittest.TestCase):
    def test_get_set(self):
        cache = TTLCache(maxsize=10, ttl=60)
        cache.set("a", 1)
        self.assertEqual(cache.get("a"), 1)
        self.assertIsNone(cache.get("yo'q"))

    def test_get_or_set(self):
        cache = TTLCache()
        calls = []

        def factory():
            calls.append(1)
            return 42

        self.assertEqual(cache.get_or_set("k", factory), 42)
        self.assertEqual(cache.get_or_set("k", factory), 42)
        self.assertEqual(len(calls), 1)  # faqat bir marta hisoblangan

    def test_lru_eviction(self):
        cache = TTLCache(maxsize=2, ttl=60)
        cache.set("a", 1)
        cache.set("b", 2)
        cache.set("c", 3)  # 'a' chiqarib yuboriladi
        self.assertIsNone(cache.get("a"))
        self.assertEqual(cache.get("c"), 3)

    def test_invalidate_prefix(self):
        cache = TTLCache()
        cache.set("products:1", "a")
        cache.set("products:2", "b")
        cache.set("sales:1", "c")
        cache.invalidate_prefix("products")
        self.assertIsNone(cache.get("products:1"))
        self.assertEqual(cache.get("sales:1"), "c")


if __name__ == "__main__":
    unittest.main()
