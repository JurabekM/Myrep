# -*- coding: utf-8 -*-
"""
Flask web-server (localhost:8000).

Xavfsizlik qatlami:
* Sessiya — HttpOnly cookie (DB da saqlangan token, sirg'aluvchi timeout)
* CSRF — har bir POST formada majburiy token
* Rate limiting — IP bo'yicha sirg'aluvchi oyna
* Security headerlar — CSP, X-Frame-Options, nosniff
* XSS — barcha chiqishlar helpers.e() orqali ekranlanadi
* SQL injection — faqat parametrlangan so'rovlar (database qatlami)

JavaScript ISHLATILMAYDI — sof server-rendered HTML + CSS.
"""
from __future__ import annotations

from flask import Flask, abort, g, redirect, request, Response

from src import __app_name__, __version__
from src.auth.service import AuthError
from src.core.logger import get_logger
from src.core.security import escape_html as e
from src.web import helpers as h
from src.web.theme import CSS

SESSION_COOKIE = "uzerp_session"
#: Autentifikatsiyasiz ochiq yo'llar
_PUBLIC_PATHS = ("/login", "/static/", "/favicon.ico", "/health")

_FAVICON_SVG = (
    '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 64 64">'
    '<rect width="64" height="64" rx="14" fill="#4f8cff"/>'
    '<text x="32" y="42" font-size="28" font-weight="800" fill="#fff" '
    'text-anchor="middle" font-family="Segoe UI, sans-serif">Uz</text></svg>')


def create_app(ctx) -> Flask:
    """Flask ilovasini quradi (barcha marshrutlar bilan)."""
    app = Flask(__app_name__.lower())
    app.config["ctx"] = ctx
    log = get_logger("web")

    auth = ctx.services.get("auth")
    csrf = ctx.services.get("csrf")
    rate_limiter = ctx.services.get("rate_limiter")

    # ------------------------------------------------------------------ #
    #  Middleware
    # ------------------------------------------------------------------ #

    @app.before_request
    def _security_gate():
        # Rate limiting (IP bo'yicha)
        ip = request.remote_addr or "?"
        if not rate_limiter.allow(ip):
            ctx.audit.security("rate_limit.exceeded", ip=ip,
                               details=request.path)
            return Response("So'rovlar juda ko'p. Birozdan so'ng urinib "
                            "ko'ring.", status=429, mimetype="text/plain")

        # Ochiq yo'llar (login talab qilinmaydi)
        if (request.path in ("/login", "/health", "/favicon.ico",
                             "/api/docs")
                or request.path.startswith("/static/")):
            # /api/docs uchun: login qilingan bo'lsa layout ko'rsatish uchun
            # foydalanuvchini yuklab qo'yamiz (majburiy emas).
            token = request.cookies.get(SESSION_COOKIE, "")
            g.user = auth.validate_session(token) if token else None
            g.session_token = token
            g.csrf_token = csrf.issue(token or "login")
            if request.method == "POST":
                return _check_csrf()
            return None

        # REST API o'z Bearer-token autentifikatsiyasiga ega — sessiyani
        # chetlab o'tadi. /api/docs esa oddiy sahifa (sessiya bilan).
        if request.path.startswith("/api/v1/"):
            return None

        # Sessiya tekshiruvi
        token = request.cookies.get(SESSION_COOKIE, "")
        user = auth.validate_session(token) if token else None
        if not user:
            return redirect("/login?err=Sessiya+tugadi.+Qayta+kiring.")
        g.user = user
        g.session_token = token
        g.csrf_token = csrf.issue(token)

        if request.method == "POST":
            return _check_csrf()
        return None

    def _check_csrf():
        """POST so'rovlarda CSRF tokenni tekshiradi."""
        sent = request.form.get("_csrf", "")
        if sent != g.csrf_token:
            ctx.audit.security("csrf.blocked", user=getattr(g, "user", None),
                               ip=request.remote_addr or "",
                               details=request.path)
            abort(400, "CSRF token yaroqsiz.")
        return None

    @app.after_request
    def _security_headers(response: Response) -> Response:
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "SAMEORIGIN"
        response.headers["Referrer-Policy"] = "same-origin"
        response.headers["Content-Security-Policy"] = (
            "default-src 'self'; img-src 'self' data:; "
            "style-src 'self' 'unsafe-inline'; script-src 'none'; "
            "form-action 'self'; frame-ancestors 'self'")
        return response

    # ------------------------------------------------------------------ #
    #  Statik va texnik marshrutlar
    # ------------------------------------------------------------------ #

    @app.get("/static/style.css")
    def style_css():
        return Response(CSS, mimetype="text/css",
                        headers={"Cache-Control": "public, max-age=3600"})

    @app.get("/favicon.ico")
    def favicon():
        return Response(_FAVICON_SVG, mimetype="image/svg+xml",
                        headers={"Cache-Control": "public, max-age=86400"})

    @app.get("/health")
    def health():
        return {"status": "ok", "app": __app_name__, "version": __version__}

    # ------------------------------------------------------------------ #
    #  Login / Logout / Profil
    # ------------------------------------------------------------------ #

    @app.get("/login")
    def login_page():
        err = request.args.get("err", "")
        err_html = f'<div class="alert err">{e(err)}</div>' if err else ""
        body = (
            '<div class="login-wrap"><div class="login-card">'
            '<div class="logo-row"><div class="logo" style="width:42px;'
            'height:42px;border-radius:11px;display:grid;place-items:center;'
            'font-weight:800;color:#fff;background:linear-gradient(135deg,'
            f'#4f8cff,#a78bfa)">Uz</div><div><h1>{e(__app_name__)}</h1>'
            '<div class="sub">Enterprise Resource Planning</div></div></div>'
            f"{err_html}"
            f'<form method="post" action="/login">{h.csrf_field()}'
            '<div class="field"><label>Login</label>'
            '<input name="username" required autofocus autocomplete="username">'
            "</div>"
            '<div class="field"><label>Parol</label>'
            '<input type="password" name="password" required '
            'autocomplete="current-password"></div>'
            '<button class="btn primary" type="submit" '
            'style="width:100%;justify-content:center">Kirish</button>'
            "</form>"
            '<p class="sub" style="margin-top:14px">Birinchi kirish: '
            "login <b>admin</b>, parol data/admin_credentials.txt faylida."
            "</p></div></div>")
        return _bare_page("Kirish", body)

    @app.post("/login")
    def login_submit():
        try:
            result = auth.login(
                request.form.get("username", ""),
                request.form.get("password", ""),
                ip=request.remote_addr or "",
                user_agent=request.headers.get("User-Agent", ""))
        except AuthError as exc:
            return redirect(h.redirect_msg("/login", err=str(exc)))
        response = redirect("/")
        response.set_cookie(
            SESSION_COOKIE, result["token"], httponly=True,
            samesite="Lax", max_age=12 * 3600)
        return response

    @app.post("/logout")
    def logout():
        token = request.cookies.get(SESSION_COOKIE, "")
        if token:
            auth.logout(token)
        response = redirect("/login?msg=Tizimdan+chiqdingiz.")
        response.delete_cookie(SESSION_COOKIE)
        return response

    @app.get("/profile")
    def profile():
        user = g.user
        content = h.page_head("Profil") + h.card(
            "Hisob ma'lumotlari",
            h.kv_list([
                ("Login", e(user["username"])),
                ("F.I.Sh.", e(user["full_name"])),
                ("Rol", h.badge(user["role"]) if user["role"] in
                 h.STATUS_BADGES else e(user["role"])),
                ("Email", e(user["email"])),
            ])) + h.card(
            "Parolni almashtirish",
            h.form_page("/profile/password",
                        h.input_field("old_password", "Joriy parol",
                                      type_="password", required=True),
                        h.input_field("new_password", "Yangi parol",
                                      type_="password", required=True),
                        submit="Parolni yangilash"))
        return render(ctx, "Profil", content, "/profile")

    @app.post("/profile/password")
    def profile_password():
        try:
            auth.change_password(g.user["id"],
                                 request.form.get("old_password", ""),
                                 request.form.get("new_password", ""))
        except AuthError as exc:
            return redirect(h.redirect_msg("/profile", err=str(exc)))
        return redirect(h.redirect_msg("/profile", msg="Parol yangilandi."))

    # ------------------------------------------------------------------ #
    #  Xato sahifalari
    # ------------------------------------------------------------------ #

    @app.errorhandler(403)
    def forbidden(_err):
        return _error_page(ctx, 403, "Ruxsat yo'q",
                           "Sizning rolingizda bu sahifa uchun ruxsat yo'q.")

    @app.errorhandler(404)
    def not_found(_err):
        return _error_page(ctx, 404, "Topilmadi",
                           "So'ralgan sahifa mavjud emas.")

    @app.errorhandler(500)
    def server_error(err):
        log.exception("Ichki xato: %s", err)
        return _error_page(ctx, 500, "Ichki xato",
                           "Kutilmagan xato yuz berdi. Loglarni tekshiring.")

    # ------------------------------------------------------------------ #
    #  Modul sahifalari
    # ------------------------------------------------------------------ #

    from src.web.views import register_all
    register_all(app, ctx)

    # REST API (token-auth) + OpenAPI/Swagger docs
    _register_api(app, ctx)

    return app


def _register_api(app, ctx) -> None:
    """REST API blueprint va hujjatlar marshrutlarini ulaydi."""
    from flask import jsonify, request

    from src.web.api.openapi import build_openapi_spec, render_api_docs
    from src.web.api.rest import create_api_blueprint

    app.register_blueprint(create_api_blueprint(ctx))

    def _base_url() -> str:
        return request.host_url.rstrip("/")

    @app.get("/api/v1/openapi.json")
    def openapi_json():
        return jsonify(build_openapi_spec(_base_url()))

    @app.get("/api/docs")
    def api_docs():
        # Docs sahifasi login qilingan foydalanuvchiga layout ichida,
        # aks holda bare sahifa sifatida ko'rsatiladi.
        docs_html = render_api_docs(_base_url())
        intro = (
            '<div class="card"><h3>Autentifikatsiya</h3>'
            '<p class="muted">1. <code>POST /api/v1/auth/login</code> orqali '
            "token oling. 2. Keyingi so'rovlarda "
            "<code>Authorization: Bearer &lt;token&gt;</code> sarlavhasini "
            "yuboring. Token 1 soat amal qiladi.</p>"
            '<p style="margin-top:8px">'
            '<a class="btn small" href="/api/v1/openapi.json">'
            "openapi.json (OpenAPI 3.0 spec)</a> "
            '<a class="btn small" href="/api/v1/ping">/ping (sinov)</a></p>'
            "</div>")
        content = (h.page_head("REST API hujjatlari") + intro + docs_html)
        if getattr(g, "user", None):
            return render(ctx, "API hujjatlari", content, "/api/docs")
        return _bare_page("API hujjatlari",
                          f'<div class="content" style="max-width:1000px;'
                          f'margin:auto;padding:24px">{content}</div>')


# ---------------------------------------------------------------------- #
#  Render yordamchilari
# ---------------------------------------------------------------------- #

def render(ctx, title: str, content: str, active_path: str = "/") -> str:
    """Sahifani umumiy layout ichida qaytaradi (plugin menyusi bilan)."""
    plugin_items = []
    if ctx.services.has("plugins"):
        try:
            plugin_items = ctx.services.get("plugins").menu_items()
        except Exception:  # noqa: BLE001
            plugin_items = []
    return h.layout(title, content, active_path, plugin_items)


def _bare_page(title: str, body: str) -> str:
    """Layout'siz sahifa (login va xatolar uchun)."""
    return ("<!DOCTYPE html>"
            '<html lang="uz"><head><meta charset="utf-8">'
            '<meta name="viewport" content="width=device-width, '
            'initial-scale=1">'
            f"<title>{e(title)} — {e(__app_name__)}</title>"
            '<link rel="stylesheet" href="/static/style.css"></head>'
            f"<body>{body}</body></html>")


def _error_page(ctx, code: int, title: str, message: str):
    """Xato sahifasi (login qilingan bo'lsa layout ichida)."""
    if getattr(g, "user", None):
        content = h.page_head(f"{code} — {title}") + h.card(
            title, f'<p class="muted">{e(message)}</p>'
                   f'<div class="mt">{h.btn_link("/", "Bosh sahifa")}</div>')
        return render(ctx, title, content), code
    body = (f'<div class="login-wrap"><div class="login-card">'
            f"<h1>{code} — {e(title)}</h1>"
            f'<p class="sub mt">{e(message)}</p>'
            f'<div class="mt"><a class="btn primary" href="/login">'
            f"Kirish sahifasi</a></div></div></div>")
    return _bare_page(title, body), code


def run_server(ctx) -> None:
    """Web-serverni ishga tushiradi (bloklaydi)."""
    app = create_app(ctx)
    host = str(ctx.config.get("server.host", "127.0.0.1"))
    port = int(ctx.config.get("server.port", 8000))
    get_logger("web").info("Web-server: http://%s:%s", host, port)
    app.run(host=host, port=port, debug=False, use_reloader=False,
            threaded=True)
