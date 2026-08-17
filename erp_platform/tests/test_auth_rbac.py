# -*- coding: utf-8 -*-
"""Auth va RBAC testlari."""
from __future__ import annotations

import unittest

from src.auth.rbac import (
    ALL_PERMISSIONS, has_permission, role_permissions, valid_roles,
)
from src.auth.service import AuthError
from tests.base import ERPTestCase


class TestRBAC(unittest.TestCase):
    def test_administrator_has_all(self):
        for perm in list(ALL_PERMISSIONS)[:20]:
            self.assertTrue(has_permission("administrator", perm))

    def test_role_boundaries(self):
        cases = [
            ("cashier", "pos.operate", True),
            ("cashier", "accounting.post", False),
            ("accountant", "accounting.post", True),
            ("accountant", "sales.delete", False),
            ("warehouse", "inventory.transfer", True),
            ("warehouse", "payroll.approve", False),
            ("auditor", "sales.view", True),
            ("auditor", "sales.create", False),
            ("hr", "hr.create", True),
            ("hr", "accounting.view", False),
            ("guest", "dashboard.view", True),
            ("guest", "sales.view", False),
            ("owner", "users.manage", False),
        ]
        for role, perm, expected in cases:
            self.assertEqual(has_permission(role, perm), expected,
                             f"{role}.{perm} kutilgan {expected}")

    def test_unknown_role(self):
        self.assertFalse(has_permission("mavjud_emas", "sales.view"))

    def test_valid_roles(self):
        roles = valid_roles()
        self.assertIn("administrator", roles)
        self.assertEqual(len(roles), 9)

    def test_auditor_view_only(self):
        perms = role_permissions("auditor")
        self.assertTrue(all(p.endswith((".view", ".export")) or p == "audit.view"
                            for p in perms))


class TestAuthService(ERPTestCase):
    def _password(self):
        creds = (self.ctx.base_dir / "data" / "admin_credentials.txt").read_text(
            encoding="utf-8")
        return [l for l in creds.splitlines()
                if l.startswith("Parol")][0].split(":", 1)[1].strip()

    def test_admin_created(self):
        self.assertIsNotNone(self.ctx.db.query_one(
            "SELECT id FROM users WHERE username='admin'"))

    def test_login_success_and_session(self):
        result = self.S.get("auth").login("admin", self._password())
        self.assertIn("token", result)
        user = self.S.get("auth").validate_session(result["token"])
        self.assertEqual(user["username"], "admin")

    def test_login_wrong_password(self):
        with self.assertRaises(AuthError):
            self.S.get("auth").login("admin", "noto'g'ri")

    def test_account_lockout(self):
        auth = self.S.get("auth")
        auth.create_user(self.user, "lockme", "Parol123", role="guest")
        for _ in range(5):
            with self.assertRaises(AuthError):
                auth.login("lockme", "xato")
        # To'g'ri parol bilan ham bloklangan bo'lishi kerak
        with self.assertRaises(AuthError):
            auth.login("lockme", "Parol123")

    def test_create_user_validation(self):
        auth = self.S.get("auth")
        with self.assertRaises(AuthError):
            auth.create_user(self.user, "ab", "Parol123")  # login qisqa
        with self.assertRaises(AuthError):
            auth.create_user(self.user, "yaxshi", "qisqa")  # parol siyosati
        auth.create_user(self.user, "yangi1", "Parol123", role="cashier")
        with self.assertRaises(AuthError):
            auth.create_user(self.user, "yangi1", "Parol123")  # takror login

    def test_logout(self):
        auth = self.S.get("auth")
        result = auth.login("admin", self._password())
        auth.logout(result["token"])
        self.assertIsNone(auth.validate_session(result["token"]))


if __name__ == "__main__":
    unittest.main()
