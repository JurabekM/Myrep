# -*- coding: utf-8 -*-
"""
REST API — ``/api/v1/*``.

Autentifikatsiya: HMAC bilan imzolangan Bearer token (stateless).

    POST /api/v1/auth/login  {"username": ..., "password": ...}
      -> {"token": "...", "expires_in": 3600, "user": {...}}

Keyingi so'rovlarda sarlavha:  ``Authorization: Bearer <token>``

Barcha javoblar JSON. Ruxsatlar web bilan bir xil RBAC matritsasidan
tekshiriladi (``api.access`` + har endpoint uchun modul ruxsati).
Barcha yozuvlar (POST/DELETE) audit-trailga tushadi.
"""
from __future__ import annotations

import functools
from decimal import Decimal

from flask import Blueprint, g, jsonify, request

from src.auth.rbac import has_permission
from src.auth.service import AuthError
from src.core.errors import (
    NotFoundError, PermissionDeniedError, UzERPError, ValidationError,
)

API_PREFIX = "/api/v1"


def _json_default(value):
    """Decimal va boshqa turlarni JSON uchun matnga aylantiradi."""
    if isinstance(value, Decimal):
        return str(value)
    return str(value)


def _serialize(obj):
    """Ichma-ich Decimal'larni matnga aylantirib, JSON-mos struktura qaytaradi."""
    if isinstance(obj, Decimal):
        return str(obj)
    if isinstance(obj, dict):
        return {k: _serialize(v) for k, v in obj.items()}
    if isinstance(obj, (list, tuple)):
        return [_serialize(v) for v in obj]
    return obj


def ok(data=None, status: int = 200, **extra):
    """Muvaffaqiyatli JSON javob."""
    payload = {"ok": True}
    if data is not None:
        payload["data"] = _serialize(data)
    payload.update({k: _serialize(v) for k, v in extra.items()})
    return jsonify(payload), status


def error(message: str, status: int = 400, code: str = "error"):
    """Xato JSON javob."""
    return jsonify({"ok": False, "error": message, "code": code}), status


def create_api_blueprint(ctx) -> Blueprint:
    """REST API Blueprint'ini quradi."""
    bp = Blueprint("api_v1", __name__, url_prefix=API_PREFIX)
    S = ctx.services
    auth = S.get("auth")
    tokens = S.get("tokens")

    # ------------------------------------------------------------------ #
    #  Auth dekoratori
    # ------------------------------------------------------------------ #

    def require_auth(permission: str | None = None):
        """
        Endpoint uchun Bearer token va (ixtiyoriy) modul ruxsatini talab
        qiladi. Foydalanuvchi ``g.api_user`` da bo'ladi.
        """
        def decorator(fn):
            @functools.wraps(fn)
            def wrapper(*args, **kwargs):
                header = request.headers.get("Authorization", "")
                if not header.startswith("Bearer "):
                    return error("Authorization: Bearer <token> kerak.",
                                 401, "unauthorized")
                payload = tokens.verify(header[7:].strip())
                if not payload:
                    return error("Token yaroqsiz yoki muddati o'tgan.",
                                 401, "invalid_token")
                user = ctx.db.query_one(
                    "SELECT id, username, full_name, role, email "
                    "FROM users WHERE id = ? AND is_active = 1",
                    (payload.get("uid"),))
                if not user:
                    return error("Foydalanuvchi topilmadi yoki nofaol.",
                                 401, "user_inactive")
                if not has_permission(user["role"], "api.access"):
                    return error("API ga kirish uchun ruxsat yo'q.",
                                 403, "forbidden")
                if permission and not has_permission(user["role"], permission):
                    return error(f"Ruxsat yetarli emas: {permission}",
                                 403, "forbidden")
                g.api_user = dict(user)
                return fn(*args, **kwargs)
            return wrapper
        return decorator

    def _paginate_args():
        """So'rovdan sahifa parametrlarini oladi."""
        return (request.args.get("page", 1), request.args.get("per_page", 25))

    def _page_response(page):
        """Page obyektini standart JSON javobga aylantiradi."""
        return ok(page.items, total=page.total, page=page.page,
                  per_page=page.per_page, pages=page.pages)

    # ------------------------------------------------------------------ #
    #  Xatolarni JSON'ga aylantirish
    # ------------------------------------------------------------------ #

    @bp.errorhandler(NotFoundError)
    def _not_found(exc):
        return error(str(exc), 404, "not_found")

    @bp.errorhandler(ValidationError)
    def _validation(exc):
        return error(str(exc), 422, "validation")

    @bp.errorhandler(PermissionDeniedError)
    def _permission(exc):
        return error(str(exc), 403, "forbidden")

    @bp.errorhandler(UzERPError)
    def _uzerp(exc):
        return error(str(exc), 400, "business_error")

    @bp.errorhandler(404)
    def _http_404(_exc):
        return error("Endpoint topilmadi.", 404, "not_found")

    @bp.errorhandler(405)
    def _http_405(_exc):
        return error("Metod ruxsat etilmagan.", 405, "method_not_allowed")

    # ------------------------------------------------------------------ #
    #  Auth
    # ------------------------------------------------------------------ #

    @bp.post("/auth/login")
    def api_login():
        body = request.get_json(silent=True) or {}
        try:
            result = auth.login(body.get("username", ""),
                                body.get("password", ""),
                                ip=request.remote_addr or "", user_agent="api")
        except AuthError as exc:
            return error(str(exc), 401, "auth_failed")
        user = result["user"]
        ttl = 3600
        token = tokens.sign({"uid": user["id"], "role": user["role"]}, ttl)
        return ok(user=user, token=token, token_type="Bearer",
                  expires_in=ttl)

    @bp.get("/auth/me")
    @require_auth()
    def api_me():
        return ok(g.api_user)

    # ------------------------------------------------------------------ #
    #  Mahsulotlar
    # ------------------------------------------------------------------ #

    @bp.get("/products")
    @require_auth("inventory.view")
    def api_products():
        page, per_page = _paginate_args()
        result = S.get("products").list_products(
            page=page, per_page=per_page, search=request.args.get("q"))
        return _page_response(result)

    @bp.get("/products/<int:product_id>")
    @require_auth("inventory.view")
    def api_product(product_id):
        return ok(S.get("products").get(product_id))

    @bp.post("/products")
    @require_auth("inventory.create")
    def api_product_create():
        body = request.get_json(silent=True) or {}
        product_id = S.get("products").create(body, g.api_user)
        return ok(S.get("products").get(product_id), 201)

    @bp.get("/products/barcode/<barcode>")
    @require_auth("inventory.view")
    def api_product_barcode(barcode):
        product = S.get("products").find_by_barcode(barcode)
        if not product:
            return error("Mahsulot topilmadi.", 404, "not_found")
        return ok(product)

    # ------------------------------------------------------------------ #
    #  Ombor
    # ------------------------------------------------------------------ #

    @bp.get("/stock")
    @require_auth("inventory.view")
    def api_stock():
        page, per_page = _paginate_args()
        result = S.get("inventory").stock_overview(
            page=page, per_page=per_page, search=request.args.get("q"))
        return _page_response(result)

    # ------------------------------------------------------------------ #
    #  Mijozlar
    # ------------------------------------------------------------------ #

    @bp.get("/customers")
    @require_auth("customers.view")
    def api_customers():
        page, per_page = _paginate_args()
        result = S.get("customers").list_customers(
            page=page, per_page=per_page, search=request.args.get("q"))
        return _page_response(result)

    @bp.post("/customers")
    @require_auth("customers.create")
    def api_customer_create():
        body = request.get_json(silent=True) or {}
        cid = S.get("customers").create(body, g.api_user)
        return ok(S.get("customers").get(cid), 201)

    # ------------------------------------------------------------------ #
    #  Savdo
    # ------------------------------------------------------------------ #

    @bp.get("/sales")
    @require_auth("sales.view")
    def api_sales():
        page, per_page = _paginate_args()
        result = S.get("sales").list_docs(
            page=page, per_page=per_page,
            doc_type=request.args.get("type"),
            status=request.args.get("status"))
        return _page_response(result)

    @bp.get("/sales/<int:doc_id>")
    @require_auth("sales.view")
    def api_sale(doc_id):
        return ok(S.get("sales").get_doc(doc_id))

    @bp.post("/sales")
    @require_auth("sales.create")
    def api_sale_create():
        body = request.get_json(silent=True) or {}
        doc_id = S.get("sales").create_doc(
            body.get("doc_type", "invoice"), body.get("customer_id"),
            body.get("warehouse_id"), body.get("items", []),
            user=g.api_user, note=body.get("note", ""),
            discount=body.get("discount", 0))
        if body.get("confirm"):
            S.get("sales").confirm(doc_id, user=g.api_user)
        return ok(S.get("sales").get_doc(doc_id), 201)

    @bp.post("/sales/<int:doc_id>/confirm")
    @require_auth("sales.approve")
    def api_sale_confirm(doc_id):
        S.get("sales").confirm(doc_id, user=g.api_user)
        return ok(S.get("sales").get_doc(doc_id))

    @bp.post("/pos")
    @require_auth("pos.operate")
    def api_pos():
        body = request.get_json(silent=True) or {}
        result = S.get("sales").pos_sale(
            body.get("items", []), user=g.api_user,
            customer_id=body.get("customer_id"),
            method=body.get("method", "cash"))
        return ok(result, 201)

    # ------------------------------------------------------------------ #
    #  Hisobotlar / analitika
    # ------------------------------------------------------------------ #

    @bp.get("/reports/dashboard")
    @require_auth("dashboard.view")
    def api_dashboard():
        return ok(S.get("reports").dashboard())

    @bp.get("/reports/pl")
    @require_auth("reports.view")
    def api_pl():
        date_from = request.args.get("from", "")
        date_to = request.args.get("to", "")
        if not date_from or not date_to:
            return error("from va to parametrlari kerak (YYYY-MM-DD).",
                         422, "validation")
        return ok(S.get("accounting").profit_loss(date_from, date_to))

    @bp.get("/reports/balance")
    @require_auth("reports.view")
    def api_balance():
        return ok(S.get("accounting").balance_sheet(request.args.get("to")))

    @bp.get("/reports/vat")
    @require_auth("reports.view")
    def api_vat():
        date_from = request.args.get("from", "")
        date_to = request.args.get("to", "")
        if not date_from or not date_to:
            return error("from va to parametrlari kerak.", 422, "validation")
        return ok(S.get("accounting").vat_report(date_from, date_to))

    @bp.get("/analytics/kpi")
    @require_auth("analytics.view")
    def api_kpi():
        return ok(S.get("analytics").kpi())

    @bp.get("/analytics/top-products")
    @require_auth("analytics.view")
    def api_top_products():
        limit = int(request.args.get("limit", 10))
        return ok(S.get("analytics").top_products(limit))

    # ------------------------------------------------------------------ #
    #  Meta
    # ------------------------------------------------------------------ #

    @bp.get("/ping")
    def api_ping():
        from src import __version__
        return ok(version=__version__, service="UzERP API")

    return bp
