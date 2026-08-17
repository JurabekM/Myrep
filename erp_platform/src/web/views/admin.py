# -*- coding: utf-8 -*-
"""Boshqaruv sahifalari: foydalanuvchilar, sozlamalar, integratsiyalar,
import, backup, pluginlar, audit, global qidiruv."""
from __future__ import annotations

from pathlib import Path

from flask import abort, g, redirect, request

from src.auth.rbac import ROLE_LABELS, role_permissions
from src.auth.service import AuthError
from src.core.errors import UzERPError
from src.core.security import escape_html as e
from src.core.utils import now_str
from src.web import helpers as h


def register(app, ctx) -> None:
    """Boshqaruv marshrutlari."""
    from src.web.server import render
    S = ctx.services

    # ------------------------------------------------------------------ #
    #  Foydalanuvchilar
    # ------------------------------------------------------------------ #

    @app.get("/users")
    def users_page():
        if not h.can("users.manage"):
            abort(403)
        auth = S.get("auth")
        role_options = list(ROLE_LABELS.items())
        rows = []
        for u in auth.list_users():
            role_opts = "".join(
                f'<option value="{v}"{" selected" if v == u["role"] else ""}>'
                f"{t}</option>" for v, t in role_options)
            controls = f"""
            <form class="inline" method="post" action="/users/{u['id']}/update">
              {h.csrf_field()}
              <select name="role" style="padding:4px;border-radius:6px;
                      border:1px solid var(--border);background:var(--bg);
                      color:var(--text)">{role_opts}</select>
              <select name="is_active" style="padding:4px;border-radius:6px;
                      border:1px solid var(--border);background:var(--bg);
                      color:var(--text)">
                <option value="1"{" selected" if u["is_active"] else ""}>Faol</option>
                <option value="0"{" selected" if not u["is_active"] else ""}>Nofaol</option>
              </select>
              <input name="new_password" type="password"
                     placeholder="yangi parol (ixtiyoriy)"
                     style="width:150px;padding:4px;border-radius:6px;
                     border:1px solid var(--border);background:var(--bg);
                     color:var(--text)">
              <button class="btn small" type="submit">Saqlash</button>
            </form>"""
            rows.append([
                e(u["username"]), e(u["full_name"] or ""),
                e(ROLE_LABELS.get(u["role"], u["role"])),
                h.badge("active") if u["is_active"] else h.badge("cancelled"),
                e(u["last_login"] or "—"), controls,
            ])

        new_form = h.card("Yangi foydalanuvchi", h.form_page(
            "/users/new",
            h.input_field("username", "Login *", required=True),
            h.input_field("password", "Parol *", type_="password",
                          required=True),
            h.input_field("full_name", "F.I.Sh."),
            h.select_field("role", "Rol", role_options, "guest"),
            h.input_field("email", "Email"),
            h.input_field("phone", "Telefon"),
            submit="Yaratish"))

        perms_rows = []
        for role, label in ROLE_LABELS.items():
            perms = role_permissions(role)
            perms_rows.append([
                e(label),
                f'<span class="muted">{len(perms)} ta ruxsat</span>',
                e(", ".join(sorted(perms)[:8]) +
                  (" ..." if len(perms) > 8 else "")),
            ])

        content = (h.page_head("Foydalanuvchilar") +
                   h.card("Ro'yxat", h.data_table(
                       ["Login", "F.I.Sh.", "Rol", "Holat", "Oxirgi kirish",
                        "Boshqarish"], rows)) +
                   f'<div class="grid cols-2 mt">{new_form}'
                   f'{h.card("Permission Matrix", h.data_table(["Rol", "Soni", "Ruxsatlar (qisqa)"], perms_rows))}'
                   "</div>")
        return render(ctx, "Foydalanuvchilar", content, "/users")

    @app.post("/users/new")
    def user_new():
        if not h.can("users.manage"):
            abort(403)
        f = request.form
        try:
            S.get("auth").create_user(
                g.user, f.get("username", ""), f.get("password", ""),
                full_name=f.get("full_name", ""), role=f.get("role", "guest"),
                email=f.get("email", ""), phone=f.get("phone", ""))
        except AuthError as exc:
            return redirect(h.redirect_msg("/users", err=str(exc)))
        return redirect(h.redirect_msg("/users", msg="Foydalanuvchi yaratildi."))

    @app.post("/users/<int:user_id>/update")
    def user_update(user_id: int):
        if not h.can("users.manage"):
            abort(403)
        f = request.form
        try:
            S.get("auth").update_user(
                g.user, user_id, role=f.get("role"),
                is_active=int(f.get("is_active", 1)))
            if f.get("new_password"):
                S.get("auth").reset_password(g.user, user_id,
                                             f["new_password"])
        except AuthError as exc:
            return redirect(h.redirect_msg("/users", err=str(exc)))
        return redirect(h.redirect_msg("/users", msg="Yangilandi."))

    # ------------------------------------------------------------------ #
    #  Sozlamalar
    # ------------------------------------------------------------------ #

    @app.get("/settings")
    def settings_page():
        if not h.can("settings.manage"):
            abort(403)
        settings = {r["key"]: r["value"] for r in
                    ctx.db.query("SELECT key, value FROM settings")}
        company_form = h.card("Kompaniya ma'lumotlari", h.form_page(
            "/settings/company",
            h.input_field("company_name", "Kompaniya nomi",
                          settings.get("company_name", "")),
            h.input_field("company_tin", "STIR (INN)",
                          settings.get("company_tin", "")),
            h.input_field("company_phone", "Telefon",
                          settings.get("company_phone", "")),
            h.input_field("company_address", "Manzil",
                          settings.get("company_address", "")),
            h.input_field("receipt_footer", "Chek pastki matni",
                          settings.get("receipt_footer", ""), full=True)))

        cfg = ctx.config
        sys_info = h.card("Tizim konfiguratsiyasi (config.yaml)", h.kv_list([
            ("Database", e(ctx.db.engine)),
            ("Server", f"{e(cfg.get('server.host'))}:"
                       f"{e(cfg.get('server.port'))}"),
            ("QQS stavkasi", f"{e(cfg.get('accounting.vat_rate'))}%"),
            ("Daromad solig'i", f"{e(cfg.get('accounting.income_tax_rate'))}%"),
            ("Sessiya timeout",
             f"{e(cfg.get('security.session_timeout_minutes'))} daqiqa"),
            ("Auto-backup", "Yoqilgan"
             if cfg.get("backup.auto_backup") else "O'chirilgan"),
            ("Valyuta", e(cfg.get("app.currency"))),
        ]) + '<p class="muted mt">To\'liq sozlamalar: config.yaml faylida.</p>')

        content = (h.page_head("Sozlamalar") +
                   f'<div class="grid cols-2">{company_form}{sys_info}</div>')
        return render(ctx, "Sozlamalar", content, "/settings")

    @app.post("/settings/company")
    def settings_company():
        if not h.can("settings.manage"):
            abort(403)
        for key in ("company_name", "company_tin", "company_phone",
                    "company_address", "receipt_footer"):
            value = request.form.get(key, "")
            existing = ctx.db.query_one(
                "SELECT key FROM settings WHERE key = ?", (key,))
            if existing:
                ctx.db.update("settings", {"value": value,
                                           "updated_at": now_str()},
                              "key = ?", (key,))
            else:
                ctx.db.insert_no_id("settings", {
                    "key": key, "value": value, "updated_at": now_str()})
        ctx.audit.log("settings.update", user=g.user)
        return redirect(h.redirect_msg("/settings", msg="Saqlandi."))

    # ------------------------------------------------------------------ #
    #  Integratsiyalar
    # ------------------------------------------------------------------ #

    @app.get("/integrations")
    def integrations_page():
        if not h.can("settings.manage"):
            abort(403)
        adapters = S.get("integrations").list_all()
        rows = [[
            e(a["title"]), e(a["name"]),
            (h.badge("active") if a["configured"]
             else '<span class="badge gray">Sozlanmagan</span>'),
        ] for a in adapters]
        content = (h.page_head("Integratsiyalar") +
                   h.card("Adapterlar", h.data_table(
                       ["Nomi", "Kod", "Holat"], rows) +
                       '<p class="muted mt">Integratsiyani yoqish uchun '
                       "config.yaml dagi <b>integrations</b> bo'limiga "
                       "API kalitlarini kiriting va dasturni qayta ishga "
                       "tushiring. Kalitsiz ham tizim to'liq ishlaydi — "
                       "adapterlar so'rovlarni tayyorlaydi, lekin "
                       "yubormaydi.</p>"))
        return render(ctx, "Integratsiyalar", content, "/integrations")

    # ------------------------------------------------------------------ #
    #  Import
    # ------------------------------------------------------------------ #

    @app.get("/import")
    def import_page():
        if not h.can("settings.manage"):
            abort(403)
        form = f"""
        <form method="post" action="/import" enctype="multipart/form-data">
          {h.csrf_field()}
          <div class="form-grid">
            {h.select_field("target", "Nimani import qilish",
                            [("products", "Mahsulotlar"),
                             ("customers", "Mijozlar"),
                             ("suppliers", "Ta'minotchilar")])}
            <div class="field"><label>Fayl (CSV / XLSX / JSON)</label>
              <input type="file" name="file" required
                     accept=".csv,.xlsx,.json"></div>
          </div>
          <div class="form-actions">
            <button class="btn primary" type="submit">Import qilish</button>
          </div></form>
        <hr class="sep">
        <p class="muted">Ustun nomlari avtomatik taniladi:
        <b>nomi/name</b>, <b>sku/kod</b>, <b>narx/sale_price</b>,
        <b>tannarx/cost_price</b>, <b>shtrix/barcode</b>,
        <b>inn/stir/tin</b>, <b>telefon/phone</b>...
        Mavjud yozuvlar yangilanadi (upsert).</p>"""
        content = h.page_head("Ma'lumot import qilish") + h.card("", form)
        return render(ctx, "Import", content, "/import")

    @app.post("/import")
    def import_submit():
        if not h.can("settings.manage"):
            abort(403)
        file = request.files.get("file")
        if not file or not file.filename:
            return redirect(h.redirect_msg("/import", err="Fayl tanlanmadi."))
        suffix = Path(file.filename).suffix.lower()
        if suffix not in (".csv", ".xlsx", ".json"):
            return redirect(h.redirect_msg("/import",
                                           err=f"Format qo'llanmaydi: {suffix}"))
        temp_path = ctx.base_dir / "data" / f"upload_tmp{suffix}"
        file.save(temp_path)
        importer = S.get("importer")
        target = request.form.get("target", "products")
        try:
            fn = {"products": importer.import_products,
                  "customers": importer.import_customers,
                  "suppliers": importer.import_suppliers}[target]
            result = fn(temp_path, g.user)
        except UzERPError as exc:
            return redirect(h.redirect_msg("/import", err=str(exc)))
        finally:
            temp_path.unlink(missing_ok=True)
        msg = (f"Import yakunlandi: yangi {result['created']}, "
               f"yangilangan {result['updated']}, "
               f"xato {len(result['errors'])}")
        if result["errors"]:
            msg += " — " + "; ".join(result["errors"][:3])
        return redirect(h.redirect_msg("/import", msg=msg))

    # ------------------------------------------------------------------ #
    #  Backup
    # ------------------------------------------------------------------ #

    @app.get("/backup")
    def backup_page():
        if not h.can("backup.manage"):
            abort(403)
        backup = S.get("backup")
        rows = [[
            e(b["name"]), f'{e(b["size_mb"])} MB', e(b["created_at"]),
            h.action_form("/backup/restore", "Tiklash", "danger",
                          hidden={"name": b["name"]}),
        ] for b in backup.list_backups()]
        content = (h.page_head(
            "Backup",
            h.action_form("/backup/create", "Yangi backup olish",
                          "primary")) +
            h.card("Zaxira nusxalari", h.data_table(
                ["Fayl", "Hajm", "Yaratilgan", ""], rows,
                "Backup nusxalari yo'q")) +
            h.card("Avtomatik backup", h.kv_list([
                ("Holat", "Yoqilgan"
                 if ctx.config.get("backup.auto_backup") else "O'chirilgan"),
                ("Interval",
                 f"{e(ctx.config.get('backup.interval_hours'))} soat"),
                ("Saqlanadigan nusxalar",
                 e(ctx.config.get("backup.keep_last"))),
            ])))
        return render(ctx, "Backup", content, "/backup")

    @app.post("/backup/create")
    def backup_create():
        if not h.can("backup.manage"):
            abort(403)
        try:
            path = S.get("backup").create_backup(g.user)
        except UzERPError as exc:
            return redirect(h.redirect_msg("/backup", err=str(exc)))
        return redirect(h.redirect_msg("/backup",
                                       msg=f"Backup yaratildi: {path.name}"))

    @app.post("/backup/restore")
    def backup_restore():
        if not h.can("backup.manage"):
            abort(403)
        name = request.form.get("name", "")
        backup = S.get("backup")
        # faqat backups/ ichidagi haqiqiy fayl nomlariga ruxsat
        valid = {b["name"]: b["path"] for b in backup.list_backups()}
        if name not in valid:
            return redirect(h.redirect_msg("/backup", err="Fayl topilmadi."))
        try:
            backup.restore_backup(valid[name], g.user)
        except UzERPError as exc:
            return redirect(h.redirect_msg("/backup", err=str(exc)))
        return redirect(h.redirect_msg("/backup",
                                       msg=f"Tiklandi: {name}"))

    # ------------------------------------------------------------------ #
    #  Pluginlar
    # ------------------------------------------------------------------ #

    @app.get("/plugins")
    def plugins_page():
        if not h.can("settings.manage"):
            abort(403)
        plugins = S.get("plugins")
        rows = [[
            e(p["name"]), e(p["file"]), e(p["version"]),
            e(p["description"]),
            (h.badge("active") if p["status"] == "loaded"
             else f'<span class="badge red">{e(p["error"])}</span>'),
        ] for p in plugins.loaded]
        content = (h.page_head("Pluginlar") +
                   h.card("Yuklangan pluginlar", h.data_table(
                       ["Nomi", "Fayl", "Versiya", "Tavsif", "Holat"], rows,
                       "plugins/ papkasida plugin yo'q") +
                       '<p class="muted mt">Yangi plugin qo\'shish: '
                       "<b>plugins/</b> papkasiga .py fayl joylashtiring "
                       "(namuna: sample_plugin.py) va dasturni qayta "
                       "ishga tushiring.</p>"))
        return render(ctx, "Pluginlar", content, "/plugins")

    # ------------------------------------------------------------------ #
    #  Audit
    # ------------------------------------------------------------------ #

    @app.get("/audit")
    def audit_page():
        if not h.can("audit.view"):
            abort(403)
        args = request.args
        page = ctx.audit.recent(page=int(args.get("page", 1)),
                                category=args.get("cat") or None,
                                username=args.get("user") or None)
        rows = [[
            e(r["id"]), e(r["created_at"] or ""), e(r["username"]),
            e(r["action"]),
            e(f'{r["entity"]}#{r["entity_id"]}' if r["entity"] else ""),
            e(r["details"] or ""), e(r["ip"] or ""),
            ('<span class="badge red">security</span>'
             if r["category"] == "security" else
             f'<span class="badge gray">{e(r["category"])}</span>'),
        ] for r in page.items]
        filter_form = f"""
        <form method="get" action="/audit" class="card"
              style="display:flex;gap:10px;flex-wrap:wrap;align-items:flex-end">
          {h.select_field("cat", "Kategoriya",
                          [("audit", "Audit"), ("security", "Xavfsizlik"),
                           ("system", "Tizim")], args.get("cat"),
                          empty="Barchasi")}
          {h.input_field("user", "Foydalanuvchi", args.get("user", ""))}
          <button class="btn primary" type="submit">Filtrlash</button>
        </form>"""
        content = (h.page_head("Audit jurnali") + filter_form +
                   h.card("", h.data_table(
                       ["#", "Vaqt", "Kim", "Harakat", "Obyekt", "Tafsilot",
                        "IP", "Tur"], rows)) +
                   h.pagination(page, "/audit",
                                {k: v for k, v in args.items()
                                 if k != "page" and v}))
        return render(ctx, "Audit", content, "/audit")

    # ------------------------------------------------------------------ #
    #  Global qidiruv
    # ------------------------------------------------------------------ #

    @app.get("/search")
    def search_page():
        query = request.args.get("q", "").strip()
        results = S.get("search").global_search(query) if query else []
        sections = []
        for group in results:
            rows = [[h.link(item["url"], item["title"]),
                     e(item["subtitle"])] for item in group["items"]]
            sections.append(h.card(group["group"],
                                   h.data_table(["Nomi", "Ma'lumot"], rows)))
        if query and not results:
            sections.append(h.card("Natija",
                                   f'<p class="muted">"{e(query)}" bo\'yicha '
                                   "hech narsa topilmadi.</p>"))
        if not query:
            sections.append(h.card("Qidiruv",
                                   '<p class="muted">Yuqoridagi qidiruv '
                                   "maydoniga so'z kiriting (Alt+K).</p>"))
        content = (h.page_head(f"Qidiruv: {query}" if query else "Qidiruv") +
                   f'<div class="grid cols-2">{"".join(sections)}</div>')
        return render(ctx, "Qidiruv", content, "/search")
