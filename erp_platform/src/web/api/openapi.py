# -*- coding: utf-8 -*-
"""
OpenAPI 3.0 spetsifikatsiyasi generatori va Python-rendered API docs.

``/api/v1/openapi.json`` — mashina o'qiy oladigan spec (mobil ilova,
Postman, kod generatorlar uchun).
``/api/docs`` — inson o'qiy oladigan, JavaScript'siz HTML hujjatlar.
"""
from __future__ import annotations

from src import __app_name__, __version__
from src.core.security import escape_html as e

#: Endpointlar katalogi: (metod, yo'l, tag, xulosa, ruxsat, body namunasi)
ENDPOINTS = [
    ("POST", "/auth/login", "Auth", "Tizimga kirish va token olish", None,
     {"username": "admin", "password": "***"}),
    ("GET", "/auth/me", "Auth", "Joriy foydalanuvchi ma'lumoti",
     "api.access", None),
    ("GET", "/ping", "Meta", "Xizmat holati (auth talab qilinmaydi)",
     None, None),
    ("GET", "/products", "Mahsulotlar",
     "Mahsulotlar ro'yxati (sahifalangan, ?q= qidiruv)",
     "inventory.view", None),
    ("GET", "/products/{id}", "Mahsulotlar", "Bitta mahsulot",
     "inventory.view", None),
    ("POST", "/products", "Mahsulotlar", "Yangi mahsulot yaratish",
     "inventory.create",
     {"name": "Mahsulot nomi", "sale_price": 15000, "cost_price": 10000,
      "barcode": "4780000000001", "unit": "dona", "min_stock": 5}),
    ("GET", "/products/barcode/{barcode}", "Mahsulotlar",
     "Shtrix-kod bo'yicha topish", "inventory.view", None),
    ("GET", "/stock", "Ombor", "Ombor qoldiqlari", "inventory.view", None),
    ("GET", "/customers", "Mijozlar", "Mijozlar ro'yxati",
     "customers.view", None),
    ("POST", "/customers", "Mijozlar", "Yangi mijoz",
     "customers.create",
     {"name": "Mijoz nomi", "phone": "+998901234567",
      "discount_percent": 5}),
    ("GET", "/sales", "Savdo",
     "Savdo hujjatlari (?type=&status=)", "sales.view", None),
    ("GET", "/sales/{id}", "Savdo", "Hujjat tafsiloti", "sales.view", None),
    ("POST", "/sales", "Savdo", "Yangi savdo hujjati (confirm: true bilan)",
     "sales.create",
     {"doc_type": "invoice", "customer_id": 1, "confirm": True,
      "items": [{"product_id": 1, "quantity": 2, "price": 15000}]}),
    ("POST", "/sales/{id}/confirm", "Savdo", "Hujjatni tasdiqlash",
     "sales.approve", None),
    ("POST", "/pos", "Savdo", "POS savdo (bir qadamda: sotish+to'lov)",
     "pos.operate",
     {"method": "cash", "items": [{"product_id": 1, "quantity": 1}]}),
    ("GET", "/reports/dashboard", "Hisobotlar", "Dashboard ko'rsatkichlari",
     "dashboard.view", None),
    ("GET", "/reports/pl", "Hisobotlar",
     "Foyda-zarar (?from=&to=)", "reports.view", None),
    ("GET", "/reports/balance", "Hisobotlar", "Balans (?to=)",
     "reports.view", None),
    ("GET", "/reports/vat", "Hisobotlar", "QQS hisoboti (?from=&to=)",
     "reports.view", None),
    ("GET", "/analytics/kpi", "Analitika", "KPI ko'rsatkichlari",
     "analytics.view", None),
    ("GET", "/analytics/top-products", "Analitika",
     "TOP mahsulotlar (?limit=)", "analytics.view", None),
]

API_PREFIX = "/api/v1"


def build_openapi_spec(base_url: str = "") -> dict:
    """OpenAPI 3.0 JSON spetsifikatsiyasini quradi."""
    paths: dict = {}
    tags_seen: dict[str, None] = {}

    for method, path, tag, summary, permission, body in ENDPOINTS:
        tags_seen[tag] = None
        full_path = API_PREFIX + path.replace("{id}", "{id}")
        operation = {
            "tags": [tag],
            "summary": summary,
            "responses": {
                "200": {"description": "Muvaffaqiyatli"},
                "401": {"description": "Autentifikatsiya kerak"},
                "403": {"description": "Ruxsat yo'q"},
                "422": {"description": "Validatsiya xatosi"},
            },
        }
        if permission:
            operation["security"] = [{"bearerAuth": []}]
            operation["description"] = f"Kerakli ruxsat: `{permission}`"
        # Path parametrlari
        params = []
        if "{id}" in path:
            params.append({"name": "id", "in": "path", "required": True,
                           "schema": {"type": "integer"}})
        if "{barcode}" in path:
            params.append({"name": "barcode", "in": "path", "required": True,
                           "schema": {"type": "string"}})
        if method == "GET" and path in ("/products", "/customers", "/sales",
                                        "/stock"):
            params += [
                {"name": "page", "in": "query",
                 "schema": {"type": "integer", "default": 1}},
                {"name": "per_page", "in": "query",
                 "schema": {"type": "integer", "default": 25}},
            ]
        if params:
            operation["parameters"] = params
        # Request body
        if body is not None:
            operation["requestBody"] = {
                "required": True,
                "content": {"application/json": {"example": body}},
            }
        paths.setdefault(full_path, {})[method.lower()] = operation

    return {
        "openapi": "3.0.3",
        "info": {
            "title": f"{__app_name__} REST API",
            "version": __version__,
            "description": "Enterprise ERP REST API — 100% Python. "
                           "Barcha endpointlar Bearer token bilan "
                           "himoyalangan (/auth/login orqali oling).",
        },
        "servers": [{"url": base_url or "http://127.0.0.1:8000"}],
        "components": {
            "securitySchemes": {
                "bearerAuth": {"type": "http", "scheme": "bearer",
                               "bearerFormat": "HMAC-JWT"},
            },
        },
        "tags": [{"name": t} for t in tags_seen],
        "paths": paths,
    }


def render_api_docs(base_url: str = "") -> str:
    """
    JavaScript'siz, Python-rendered API hujjatlari sahifasi.

    Har bir endpoint: metod, yo'l, tavsif, ruxsat, so'rov namunasi va
    tayyor ``curl`` misoli bilan.
    """
    import json

    groups: dict[str, list] = {}
    for endpoint in ENDPOINTS:
        groups.setdefault(endpoint[2], []).append(endpoint)

    method_colors = {"GET": "green", "POST": "blue", "PUT": "amber",
                     "DELETE": "red"}
    sections = []
    for tag, items in groups.items():
        rows = []
        for method, path, _tag, summary, permission, body in items:
            color = method_colors.get(method, "gray")
            perm_badge = (f'<span class="badge violet">{e(permission)}</span>'
                          if permission else
                          '<span class="badge gray">ochiq</span>')
            curl = _curl_example(base_url, method, path, body)
            body_html = ""
            if body is not None:
                body_html = (
                    '<div class="muted" style="margin-top:6px">So\'rov tanasi:'
                    f'</div><pre style="background:var(--bg);padding:10px;'
                    f'border-radius:8px;overflow-x:auto;font-size:.8rem">'
                    f'{e(json.dumps(body, ensure_ascii=False, indent=2))}</pre>')
            rows.append(f"""
            <div class="card" style="margin-bottom:12px">
              <div style="display:flex;gap:10px;align-items:center;
                   flex-wrap:wrap">
                <span class="badge {color}">{method}</span>
                <code style="font-size:.92rem;color:var(--accent-h)">
                {e(API_PREFIX + path)}</code>
                {perm_badge}
              </div>
              <p style="margin-top:8px">{e(summary)}</p>
              {body_html}
              <details style="margin-top:8px">
                <summary class="muted" style="cursor:pointer">curl misoli
                </summary>
                <pre style="background:var(--bg);padding:10px;
                     border-radius:8px;overflow-x:auto;font-size:.78rem;
                     margin-top:6px">{e(curl)}</pre>
              </details>
            </div>""")
        sections.append(f'<h2 style="margin:20px 0 12px">{e(tag)}</h2>'
                        + "".join(rows))

    return "".join(sections)


def _curl_example(base_url: str, method: str, path: str, body) -> str:
    """Endpoint uchun tayyor curl buyrug'ini quradi."""
    import json

    url = (base_url or "http://127.0.0.1:8000") + API_PREFIX + \
        path.replace("{id}", "1").replace("{barcode}", "4780000000001")
    parts = [f"curl -X {method} '{url}'"]
    if path != "/auth/login" and path != "/ping":
        parts.append("  -H 'Authorization: Bearer <TOKEN>'")
    if body is not None:
        parts.append("  -H 'Content-Type: application/json'")
        parts.append(f"  -d '{json.dumps(body, ensure_ascii=False)}'")
    return " \\\n".join(parts)
