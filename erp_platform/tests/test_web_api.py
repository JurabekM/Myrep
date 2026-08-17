# -*- coding: utf-8 -*-
"""Web interfeys va REST API testlari (Flask test client orqali)."""
from __future__ import annotations

import re
import unittest

from src.web.server import create_app, SESSION_COOKIE
from tests.base import ERPTestCase


class WebTestBase(ERPTestCase):
    def setUp(self):
        super().setUp()
        self.app = create_app(self.ctx)
        self.client = self.app.test_client()
        creds = (self.ctx.base_dir / "data" / "admin_credentials.txt").read_text(
            encoding="utf-8")
        self.password = [l for l in creds.splitlines()
                         if l.startswith("Parol")][0].split(":", 1)[1].strip()

    def _csrf(self, path):
        html = self.client.get(path).get_data(as_text=True)
        m = re.search(r'name="_csrf" value="([^"]+)"', html)
        return m.group(1) if m else ""

    def _login(self):
        csrf = self._csrf("/login")
        return self.client.post("/login", data={
            "username": "admin", "password": self.password, "_csrf": csrf},
            follow_redirects=False)


class TestWeb(WebTestBase):
    def test_requires_login(self):
        resp = self.client.get("/", follow_redirects=False)
        self.assertEqual(resp.status_code, 302)
        self.assertIn("/login", resp.headers["Location"])

    def test_csrf_required(self):
        resp = self.client.post("/login", data={"username": "admin",
                                                "password": self.password})
        self.assertEqual(resp.status_code, 400)

    def test_login_logout(self):
        resp = self._login()
        self.assertEqual(resp.headers["Location"], "/")
        # Dashboard endi ochiladi
        self.assertEqual(self.client.get("/").status_code, 200)

    def test_no_javascript(self):
        self._login()
        html = self.client.get("/").get_data(as_text=True)
        self.assertNotIn("<script", html.lower())

    def test_security_headers(self):
        resp = self.client.get("/login")
        self.assertIn("script-src 'none'",
                      resp.headers.get("Content-Security-Policy", ""))
        self.assertEqual(resp.headers.get("X-Frame-Options"), "SAMEORIGIN")

    def test_key_pages_render(self):
        self._login()
        for path in ("/", "/sales", "/products", "/stock", "/customers",
                     "/cash", "/journal", "/accounts", "/hr", "/payroll",
                     "/reports/balance", "/analytics", "/users", "/audit"):
            self.assertEqual(self.client.get(path).status_code, 200,
                             f"{path} 200 qaytarmadi")

    def test_health(self):
        data = self.client.get("/health").get_json()
        self.assertEqual(data["status"], "ok")


class TestAPI(WebTestBase):
    def _token(self, username="admin", password=None):
        resp = self.client.post("/api/v1/auth/login", json={
            "username": username, "password": password or self.password})
        return resp.get_json().get("token")

    def _auth(self, token):
        return {"Authorization": f"Bearer {token}"}

    def test_ping_public(self):
        self.assertTrue(self.client.get("/api/v1/ping").get_json()["ok"])

    def test_unauthorized(self):
        resp = self.client.get("/api/v1/products")
        self.assertEqual(resp.status_code, 401)

    def test_login_and_me(self):
        token = self._token()
        self.assertIsNotNone(token)
        resp = self.client.get("/api/v1/auth/me", headers=self._auth(token))
        self.assertEqual(resp.get_json()["data"]["username"], "admin")

    def test_invalid_token(self):
        resp = self.client.get("/api/v1/products",
                               headers=self._auth("soxta.token"))
        self.assertEqual(resp.status_code, 401)

    def test_product_crud(self):
        token = self._token()
        resp = self.client.post("/api/v1/products", headers=self._auth(token),
                                json={"name": "API mahsulot",
                                      "sale_price": 5000})
        self.assertEqual(resp.status_code, 201)
        pid = resp.get_json()["data"]["id"]
        resp = self.client.get(f"/api/v1/products/{pid}",
                               headers=self._auth(token))
        self.assertEqual(resp.get_json()["data"]["name"], "API mahsulot")

    def test_decimal_serialization(self):
        token = self._token()
        resp = self.client.get("/api/v1/reports/balance",
                               headers=self._auth(token))
        # Balans qiymatlari matn sifatida (Decimal serializatsiya)
        self.assertIsInstance(resp.get_json()["data"]["total_assets"], str)

    def test_openapi_spec(self):
        spec = self.client.get("/api/v1/openapi.json").get_json()
        self.assertTrue(spec["openapi"].startswith("3."))
        self.assertGreaterEqual(len(spec["paths"]), 15)
        self.assertIn("bearerAuth", spec["components"]["securitySchemes"])

    def test_docs_page(self):
        html = self.client.get("/api/docs").get_data(as_text=True)
        self.assertIn("REST API", html)
        self.assertNotIn("<script", html.lower())

    def test_rbac_enforcement(self):
        self.S.get("auth").create_user(self.user, "apicashier", "Kassir123",
                                       role="cashier")
        token = self._token("apicashier", "Kassir123")
        # kassir 'api.access' yo'q -> 403
        resp = self.client.get("/api/v1/products", headers=self._auth(token))
        self.assertEqual(resp.status_code, 403)


if __name__ == "__main__":
    unittest.main()
