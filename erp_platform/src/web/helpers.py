# -*- coding: utf-8 -*-
"""
HTML render yordamchilari — shablon dvigatelisiz, sof Python funksiyalar.

Barcha foydalanuvchi ma'lumotlari :func:`e` (escape) orqali chiqariladi —
XSS himoyasi shu qatlamda markazlashgan.
"""
from __future__ import annotations

from decimal import Decimal
from typing import Any, Sequence
from urllib.parse import quote, urlencode

from flask import g, request

from src import __app_name__, __version__
from src.auth.rbac import has_permission, ROLE_LABELS
from src.core.security import escape_html as e
from src.core.utils import money, Page

# ---------------------------------------------------------------------- #
#  Menyu strukturasi: (bo'lim, [(nom, url, ruxsat, belgi)])
# ---------------------------------------------------------------------- #

MENU: list[tuple[str, list[tuple[str, str, str, str]]]] = [
    ("", [("Dashboard", "/", "dashboard.view", "◧")]),
    ("Savdo", [
        ("Hujjatlar", "/sales", "sales.view", "▤"),
        ("POS kassa", "/pos", "pos.operate", "▣"),
        ("Mijozlar", "/customers", "customers.view", "◉"),
    ]),
    ("Ombor", [
        ("Mahsulotlar", "/products", "inventory.view", "◫"),
        ("Qoldiqlar", "/stock", "inventory.view", "≡"),
        ("Harakatlar", "/moves", "inventory.view", "⇄"),
        ("Inventarizatsiya", "/counts", "inventory.adjust", "☰"),
    ]),
    ("Xarid", [
        ("Xaridlar", "/purchases", "purchases.view", "▥"),
        ("Ta'minotchilar", "/suppliers", "suppliers.view", "◎"),
    ]),
    ("CRM", [
        ("Leadlar", "/crm", "crm.view", "◭"),
        ("Faoliyatlar", "/activities", "crm.view", "✓"),
    ]),
    ("Moliya", [
        ("Kassa / Bank", "/cash", "cash.view", "▦"),
        ("Jurnal", "/journal", "accounting.view", "☷"),
        ("Hisoblar rejasi", "/accounts", "accounting.view", "#"),
        ("Asosiy vositalar", "/assets", "accounting.view", "◨"),
        ("Hisobotlar", "/reports", "reports.view", "◪"),
    ]),
    ("HR", [
        ("Xodimlar", "/hr", "hr.view", "◔"),
        ("Davomat", "/attendance", "hr.view", "◷"),
        ("Ta'tillar", "/leaves", "hr.view", "☀"),
        ("Ish haqi", "/payroll", "payroll.view", "₮"),
    ]),
    ("Analitika", [("Analitika", "/analytics", "analytics.view", "◮")]),
    ("Boshqaruv", [
        ("Foydalanuvchilar", "/users", "users.manage", "◉"),
        ("REST API", "/api/docs", "api.access", "⧉"),
        ("Sozlamalar", "/settings", "settings.manage", "⚙"),
        ("Integratsiyalar", "/integrations", "settings.manage", "⇌"),
        ("Import", "/import", "settings.manage", "⇥"),
        ("Backup", "/backup", "backup.manage", "▽"),
        ("Pluginlar", "/plugins", "settings.manage", "✚"),
        ("Audit", "/audit", "audit.view", "☲"),
    ]),
]

STATUS_BADGES = {
    "draft": ("Qoralama", "gray"),
    "confirmed": ("Tasdiqlangan", "blue"),
    "partial": ("Qisman to'langan", "amber"),
    "paid": ("To'langan", "green"),
    "received": ("Qabul qilingan", "blue"),
    "cancelled": ("Bekor qilingan", "red"),
    "returned": ("Qaytarilgan", "violet"),
    "done": ("Yakunlangan", "green"),
    "open": ("Ochiq", "blue"),
    "pending": ("Kutilmoqda", "amber"),
    "approved": ("Tasdiqlangan", "green"),
    "rejected": ("Rad etilgan", "red"),
    "active": ("Faol", "green"),
    "new": ("Yangi", "blue"),
    "contacted": ("Aloqa qilindi", "amber"),
    "qualified": ("Malakali", "violet"),
    "won": ("Yutildi", "green"),
    "lost": ("Yo'qotildi", "red"),
    "terminated": ("Bo'shatilgan", "red"),
    "leave": ("Ta'tilda", "amber"),
    "in": ("Kirim", "green"),
    "out": ("Chiqim", "red"),
}

DOC_TYPE_LABELS = {
    "quotation": "Taklif", "order": "Buyurtma", "invoice": "Hisob-faktura",
    "pos": "POS savdo", "return": "Qaytarish",
}


# ---------------------------------------------------------------------- #
#  Kichik komponentlar
# ---------------------------------------------------------------------- #

def can(perm: str) -> bool:
    """Joriy foydalanuvchi ruxsatini tekshiradi."""
    user = getattr(g, "user", None)
    return bool(user) and has_permission(user["role"], perm)


def badge(status: str) -> str:
    """Holat belgisi (rangli)."""
    label, kind = STATUS_BADGES.get(str(status), (str(status), "gray"))
    return f'<span class="badge {kind}">{e(label)}</span>'


def m(value) -> str:
    """Pul formatlash (jadval katagi uchun)."""
    return e(money(value))


def link(href: str, text: str, cls: str = "") -> str:
    """Oddiy havola."""
    return f'<a href="{e(href)}" class="{e(cls)}">{e(text)}</a>'


def btn_link(href: str, text: str, kind: str = "") -> str:
    """Tugma ko'rinishidagi havola."""
    return f'<a class="btn {e(kind)}" href="{e(href)}">{e(text)}</a>'


def action_form(action: str, label: str, kind: str = "",
                hidden: dict | None = None) -> str:
    """Bir tugmali POST forma (tasdiqlash/bekor qilish kabi amallar)."""
    fields = [csrf_field()]
    for name, value in (hidden or {}).items():
        fields.append(f'<input type="hidden" name="{e(name)}" '
                      f'value="{e(value)}">')
    return (f'<form class="inline" method="post" action="{e(action)}">'
            f'{"".join(fields)}'
            f'<button class="btn small {e(kind)}" type="submit">'
            f'{e(label)}</button></form>')


def csrf_field() -> str:
    """CSRF hidden maydoni (joriy sessiyaga bog'langan)."""
    token = getattr(g, "csrf_token", "")
    return f'<input type="hidden" name="_csrf" value="{e(token)}">'


def flash_html() -> str:
    """Query paramlardan xabar/xato bannerlari (?msg= / ?err=)."""
    parts = []
    msg = request.args.get("msg")
    err = request.args.get("err")
    if msg:
        parts.append(f'<div class="alert ok">{e(msg)}</div>')
    if err:
        parts.append(f'<div class="alert err">{e(err)}</div>')
    return "".join(parts)


def redirect_msg(url: str, msg: str = "", err: str = "") -> str:
    """Xabar bilan redirect URL quradi."""
    params = {}
    if msg:
        params["msg"] = msg
    if err:
        params["err"] = err
    if not params:
        return url
    sep = "&" if "?" in url else "?"
    return url + sep + urlencode(params)


# ---------------------------------------------------------------------- #
#  Forma maydonlari
# ---------------------------------------------------------------------- #

def input_field(name: str, label: str, value: Any = "", type_: str = "text",
                required: bool = False, step: str | None = None,
                placeholder: str = "", full: bool = False) -> str:
    """Matn/son/sana kiritish maydoni."""
    attrs = f' type="{e(type_)}" name="{e(name)}" value="{e(value)}"'
    if required:
        attrs += " required"
    if step:
        attrs += f' step="{e(step)}"'
    if placeholder:
        attrs += f' placeholder="{e(placeholder)}"'
    cls = "field full" if full else "field"
    return (f'<div class="{cls}"><label>{e(label)}</label>'
            f'<input{attrs}></div>')


def select_field(name: str, label: str,
                 options: Sequence[tuple[Any, str]],
                 selected: Any = None, full: bool = False,
                 empty: str | None = None) -> str:
    """Tanlov maydoni. ``options``: (qiymat, ko'rinish) juftliklari."""
    opts = []
    if empty is not None:
        opts.append(f'<option value="">{e(empty)}</option>')
    for value, text in options:
        sel = " selected" if str(value) == str(selected or "") else ""
        opts.append(f'<option value="{e(value)}"{sel}>{e(text)}</option>')
    cls = "field full" if full else "field"
    return (f'<div class="{cls}"><label>{e(label)}</label>'
            f'<select name="{e(name)}">{"".join(opts)}</select></div>')


def textarea_field(name: str, label: str, value: Any = "",
                   full: bool = True, rows: int = 3) -> str:
    """Ko'p qatorli matn maydoni."""
    cls = "field full" if full else "field"
    return (f'<div class="{cls}"><label>{e(label)}</label>'
            f'<textarea name="{e(name)}" rows="{rows}">{e(value)}</textarea>'
            f'</div>')


def form_page(action: str, *fields: str, submit: str = "Saqlash",
              cancel_url: str | None = None) -> str:
    """Standart forma (grid joylashuvida, CSRF bilan)."""
    cancel = (f'<a class="btn" href="{e(cancel_url)}">Bekor qilish</a>'
              if cancel_url else "")
    return (f'<form method="post" action="{e(action)}">{csrf_field()}'
            f'<div class="form-grid">{"".join(fields)}</div>'
            f'<div class="form-actions">'
            f'<button class="btn primary" type="submit">{e(submit)}</button>'
            f'{cancel}</div></form>')


# ---------------------------------------------------------------------- #
#  Jadval va sahifalash
# ---------------------------------------------------------------------- #

def data_table(headers: Sequence[str], rows: Sequence[Sequence[str]],
               empty_text: str = "Ma'lumot yo'q",
               num_cols: Sequence[int] = ()) -> str:
    """
    Ma'lumotlar jadvali. Katak qiymatlari OLDINDAN xavfsiz HTML bo'lishi
    kerak (``e()``, ``m()``, ``badge()`` yordamchilaridan foydalaning).
    """
    head = "".join(
        f'<th class="num">{h}</th>' if i in num_cols else f"<th>{h}</th>"
        for i, h in enumerate(headers))
    if not rows:
        body = (f'<tr><td colspan="{len(headers)}" class="muted" '
                f'style="text-align:center;padding:26px">{e(empty_text)}'
                f'</td></tr>')
    else:
        body_rows = []
        for row in rows:
            cells = "".join(
                f'<td class="num">{c}</td>' if i in num_cols else f"<td>{c}</td>"
                for i, c in enumerate(row))
            body_rows.append(f"<tr>{cells}</tr>")
        body = "".join(body_rows)
    return (f'<div class="table-wrap"><table class="data">'
            f"<thead><tr>{head}</tr></thead><tbody>{body}</tbody>"
            f"</table></div>")


def pagination(page: Page, base_url: str, params: dict | None = None) -> str:
    """Sahifalash paneli (oldingi/keyingi + raqamlar)."""
    if page.pages <= 1:
        return (f'<div class="pagination"><span class="info">'
                f'Jami: {page.total} ta</span></div>')

    def url_for_page(p: int) -> str:
        merged = dict(params or {})
        merged["page"] = p
        return f"{base_url}?{urlencode(merged)}"

    parts = ['<div class="pagination">']
    if page.has_prev:
        parts.append(f'<a href="{e(url_for_page(page.page - 1))}">‹</a>')
    start = max(1, page.page - 3)
    end = min(page.pages, page.page + 3)
    for p in range(start, end + 1):
        if p == page.page:
            parts.append(f'<span class="cur">{p}</span>')
        else:
            parts.append(f'<a href="{e(url_for_page(p))}">{p}</a>')
    if page.has_next:
        parts.append(f'<a href="{e(url_for_page(page.page + 1))}">›</a>')
    parts.append(f'<span class="info">Jami: {page.total} ta</span></div>')
    return "".join(parts)


def stat_card(label: str, value: str, sub: str = "",
              accent: str = "") -> str:
    """KPI kartochkasi."""
    sub_html = f'<div class="sub">{sub}</div>' if sub else ""
    return (f'<div class="card"><div class="stat {e(accent)}">'
            f'<div class="label">{e(label)}</div>'
            f'<div class="value">{value}</div>{sub_html}</div></div>')


def card(title: str, body: str, action_html: str = "") -> str:
    """Sarlavhali kartochka."""
    return (f'<div class="card"><h3>{e(title)}<span>{action_html}</span></h3>'
            f"{body}</div>")


def page_head(title: str, *actions: str) -> str:
    """Sahifa sarlavhasi + amallar paneli."""
    actions_html = f'<div class="actions">{"".join(actions)}</div>' if actions else ""
    return f'<div class="page-head"><h1>{e(title)}</h1>{actions_html}</div>'


def tabs(items: Sequence[tuple[str, str]], active: str) -> str:
    """Yorliqlar paneli. ``items``: (url, nom)."""
    parts = ['<div class="tabs">']
    for url, name in items:
        cls = ' class="active"' if url == active else ""
        parts.append(f'<a href="{e(url)}"{cls}>{e(name)}</a>')
    parts.append("</div>")
    return "".join(parts)


def kv_list(pairs: Sequence[tuple[str, str]]) -> str:
    """Kalit-qiymat ro'yxati (hujjat tafsilotlari)."""
    rows = "".join(f"<dt>{e(k)}</dt><dd>{v}</dd>" for k, v in pairs)
    return f'<dl class="kv">{rows}</dl>'


# ---------------------------------------------------------------------- #
#  Asosiy layout
# ---------------------------------------------------------------------- #

def _sidebar(active_path: str, plugin_items: list[dict]) -> str:
    """Ruxsatlarga qarab filtrlangan yon panel."""
    groups = []
    for section, items in MENU:
        visible = [item for item in items if can(item[2])]
        if not visible:
            continue
        links = []
        for name, url, _perm, icon in visible:
            is_active = (active_path == url or
                         (url != "/" and active_path.startswith(url)))
            cls = "nav-item active" if is_active else "nav-item"
            links.append(f'<a class="{cls}" href="{e(url)}">'
                         f'<span class="ico">{icon}</span>{e(name)}</a>')
        title = f'<div class="nav-title">{e(section)}</div>' if section else ""
        groups.append(f'<div class="nav-group">{title}{"".join(links)}</div>')

    if plugin_items:
        links = "".join(
            f'<a class="nav-item" href="{e(p["url"])}">'
            f'<span class="ico">✚</span>{e(p["title"])}</a>'
            for p in plugin_items)
        groups.append(f'<div class="nav-group">'
                      f'<div class="nav-title">Pluginlar</div>{links}</div>')

    return (f'<aside class="sidebar"><div class="brand">'
            f'<div class="logo">Uz</div><div><div class="name">'
            f"{e(__app_name__)}</div>"
            f'<div class="ver">v{e(__version__)} · ERP</div></div></div>'
            f'{"".join(groups)}</aside>')


def layout(title: str, content: str, active_path: str = "/",
           plugin_items: list[dict] | None = None) -> str:
    """To'liq sahifa: sidebar + topbar + kontent."""
    user = getattr(g, "user", None) or {}
    role_label = ROLE_LABELS.get(user.get("role", ""), user.get("role", ""))
    initial = (user.get("full_name") or user.get("username") or "?")[:1].upper()

    topbar = (
        '<header class="topbar">'
        '<form class="search" method="get" action="/search">'
        '<input type="search" name="q" placeholder="Qidiruv... (Alt+K)" '
        f'accesskey="k" value="{e(request.args.get("q", ""))}"></form>'
        '<span class="spacer"></span>'
        f'<div class="userbox"><div class="avatar">{e(initial)}</div>'
        f'<div><div class="uname">{e(user.get("full_name") or user.get("username", ""))}</div>'
        f'<div class="urole">{e(role_label)}</div></div>'
        f'{btn_link("/profile", "Profil", "small")}'
        f'{action_form("/logout", "Chiqish", "small danger")}'
        "</div></header>")

    return (
        "<!DOCTYPE html>"
        '<html lang="uz"><head><meta charset="utf-8">'
        '<meta name="viewport" content="width=device-width, initial-scale=1">'
        f"<title>{e(title)} — {e(__app_name__)}</title>"
        '<link rel="stylesheet" href="/static/style.css">'
        "</head><body>"
        f'<div class="app">{_sidebar(active_path, plugin_items or [])}'
        f'<div class="main">{topbar}'
        f'<div class="content">{flash_html()}{content}</div>'
        f'<div class="footer">{e(__app_name__)} v{e(__version__)} — '
        f"Enterprise ERP · 100% Python</div>"
        "</div></div></body></html>")
