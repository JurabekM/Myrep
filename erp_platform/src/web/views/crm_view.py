# -*- coding: utf-8 -*-
"""CRM sahifalari: mijozlar, leadlar, faoliyatlar."""
from __future__ import annotations

from flask import abort, g, redirect, request

from src.core.errors import UzERPError
from src.core.security import escape_html as e
from src.web import helpers as h


def register(app, ctx) -> None:
    """CRM va mijozlar marshrutlari."""
    from src.web.server import render
    S = ctx.services

    # ------------------------------------------------------------------ #
    #  Mijozlar
    # ------------------------------------------------------------------ #

    @app.get("/customers")
    def customers_list():
        if not h.can("customers.view"):
            abort(403)
        customers = S.get("customers")
        page = customers.list_customers(
            page=request.args.get("page", 1),
            search=request.args.get("q") or None)
        rows = [[
            h.link(f"/customers/{r['id']}", r["name"]),
            e(r["phone"] or ""), e(r["tin"] or ""),
            e(r["discount_percent"]),
            h.m(customers.receivables(r["id"])),
        ] for r in page.items]

        new_form = ""
        if h.can("customers.create"):
            new_form = h.card("Yangi mijoz", h.form_page(
                "/customers/new",
                h.input_field("name", "Nomi *", required=True),
                h.input_field("phone", "Telefon"),
                h.input_field("tin", "STIR (INN)"),
                h.input_field("email", "Email"),
                h.input_field("discount_percent", "Chegirma (%)", "0",
                              "number", step="0.01"),
                h.input_field("address", "Manzil"),
                submit="Qo'shish"))

        content = (h.page_head("Mijozlar") +
                   f'<div class="grid cols-2">'
                   f'{h.card("Ro`yxat", h.data_table(["Nomi", "Telefon", "STIR", "Chegirma %", "Qarzi"], rows, num_cols=(3, 4)))}'
                   f"{new_form}</div>" +
                   h.pagination(page, "/customers",
                                {"q": request.args.get("q", "")}
                                if request.args.get("q") else {}))
        return render(ctx, "Mijozlar", content, "/customers")

    @app.post("/customers/new")
    def customer_new():
        if not h.can("customers.create"):
            abort(403)
        try:
            S.get("customers").create(
                {k: request.form.get(k, "") for k in
                 ("name", "phone", "tin", "email", "address",
                  "discount_percent")}, g.user)
        except UzERPError as exc:
            return redirect(h.redirect_msg("/customers", err=str(exc)))
        return redirect(h.redirect_msg("/customers", msg="Mijoz qo'shildi."))

    @app.get("/customers/<int:customer_id>")
    def customer_detail(customer_id: int):
        if not h.can("customers.view"):
            abort(403)
        customers = S.get("customers")
        try:
            customer = customers.get(customer_id)
        except UzERPError:
            abort(404)
        timeline = S.get("crm").customer_timeline(customer_id)

        info = h.kv_list([
            ("Nomi", e(customer["name"])),
            ("Telefon", e(customer["phone"] or "—")),
            ("STIR", e(customer["tin"] or "—")),
            ("Email", e(customer["email"] or "—")),
            ("Manzil", e(customer["address"] or "—")),
            ("Chegirma", f'{e(customer["discount_percent"])}%'),
            ("Qarzi (debitorlik)",
             f"<b>{h.m(customers.receivables(customer_id))}</b>"),
        ])
        sales_rows = [[
            h.link(f"/sales/{r['id']}", r["number"]),
            e(h.DOC_TYPE_LABELS.get(r["doc_type"], r["doc_type"])),
            h.badge(r["status"]), h.m(r["total"]), e(r["doc_date"]),
        ] for r in timeline["sales"]]
        activity_rows = [[
            e(r["activity_type"]), e(r["subject"]),
            h.badge(r["status"]), e(r["due_at"] or "—"),
        ] for r in timeline["activities"]]

        edit_form = ""
        if h.can("customers.edit"):
            edit_form = h.card("Tahrirlash", h.form_page(
                f"/customers/{customer_id}/edit",
                h.input_field("name", "Nomi *", customer["name"],
                              required=True),
                h.input_field("phone", "Telefon", customer["phone"] or ""),
                h.input_field("tin", "STIR", customer["tin"] or ""),
                h.input_field("email", "Email", customer["email"] or ""),
                h.input_field("discount_percent", "Chegirma (%)",
                              customer["discount_percent"], "number",
                              step="0.01"),
                h.input_field("address", "Manzil",
                              customer["address"] or "")))

        content = (h.page_head(customer["name"],
                               h.btn_link("/customers", "← Ro'yxat")) +
                   f'<div class="grid cols-2">{h.card("Ma`lumotlar", info)}'
                   f"{edit_form}</div>"
                   f'<div class="grid cols-2 mt">'
                   f'{h.card("Savdo tarixi", h.data_table(["№", "Turi", "Holat", "Summa", "Sana"], sales_rows, num_cols=(3,)))}'
                   f'{h.card("Faoliyatlar", h.data_table(["Turi", "Mavzu", "Holat", "Muddat"], activity_rows))}'
                   "</div>")
        return render(ctx, customer["name"], content, "/customers")

    @app.post("/customers/<int:customer_id>/edit")
    def customer_edit(customer_id: int):
        if not h.can("customers.edit"):
            abort(403)
        try:
            S.get("customers").update(
                customer_id,
                {k: request.form.get(k, "") for k in
                 ("name", "phone", "tin", "email", "address",
                  "discount_percent")}, g.user)
        except UzERPError as exc:
            return redirect(h.redirect_msg(f"/customers/{customer_id}",
                                           err=str(exc)))
        return redirect(h.redirect_msg(f"/customers/{customer_id}",
                                       msg="Saqlandi."))

    # ------------------------------------------------------------------ #
    #  Leadlar
    # ------------------------------------------------------------------ #

    @app.get("/crm")
    def crm_leads():
        if not h.can("crm.view"):
            abort(403)
        crm = S.get("crm")
        args = request.args
        page = crm.list_leads(page=args.get("page", 1),
                              status=args.get("status") or None,
                              search=args.get("q") or None)
        status_options = [("new", "Yangi"), ("contacted", "Aloqa qilindi"),
                          ("qualified", "Malakali"), ("won", "Yutildi"),
                          ("lost", "Yo'qotildi")]
        rows = []
        for r in page.items:
            status_form = ""
            if h.can("crm.edit") and r["status"] not in ("won", "lost"):
                opts = "".join(
                    f'<option value="{v}"{" selected" if v == r["status"] else ""}>'
                    f"{t}</option>" for v, t in status_options)
                status_form = f"""
                <form class="inline" method="post"
                      action="/crm/{r['id']}/status">{h.csrf_field()}
                  <select name="status" style="padding:4px;border-radius:6px;
                          border:1px solid var(--border);background:var(--bg);
                          color:var(--text)">{opts}</select>
                  <button class="btn small" type="submit">OK</button></form>"""
            rows.append([
                e(r["name"]), e(r["phone"] or ""), e(r["source"] or ""),
                h.badge(r["status"]), status_form,
            ])

        new_form = ""
        if h.can("crm.create"):
            new_form = h.card("Yangi lead", h.form_page(
                "/crm/new",
                h.input_field("name", "Nomi *", required=True),
                h.input_field("phone", "Telefon"),
                h.input_field("email", "Email"),
                h.input_field("source", "Manba",
                              placeholder="telegram, sayt, tavsiya..."),
                submit="Qo'shish"))

        content = (h.page_head("Leadlar (savdo voronkasi)") +
                   f'<div class="grid cols-2">'
                   f'{h.card("Ro`yxat", h.data_table(["Nomi", "Telefon", "Manba", "Holat", "O`zgartirish"], rows))}'
                   f"{new_form}</div>" +
                   h.pagination(page, "/crm", {}))
        return render(ctx, "Leadlar", content, "/crm")

    @app.post("/crm/new")
    def crm_lead_new():
        if not h.can("crm.create"):
            abort(403)
        try:
            S.get("crm").create_lead(
                {k: request.form.get(k, "") for k in
                 ("name", "phone", "email", "source")}, g.user)
        except UzERPError as exc:
            return redirect(h.redirect_msg("/crm", err=str(exc)))
        return redirect(h.redirect_msg("/crm", msg="Lead qo'shildi."))

    @app.post("/crm/<int:lead_id>/status")
    def crm_lead_status(lead_id: int):
        if not h.can("crm.edit"):
            abort(403)
        try:
            customer_id = S.get("crm").change_lead_status(
                lead_id, request.form.get("status", ""), g.user)
        except UzERPError as exc:
            return redirect(h.redirect_msg("/crm", err=str(exc)))
        msg = ("Lead yutildi — mijoz yaratildi!"
               if request.form.get("status") == "won" and customer_id
               else "Holat yangilandi.")
        return redirect(h.redirect_msg("/crm", msg=msg))

    # ------------------------------------------------------------------ #
    #  Faoliyatlar
    # ------------------------------------------------------------------ #

    @app.get("/activities")
    def activities_list():
        if not h.can("crm.view"):
            abort(403)
        crm = S.get("crm")
        page = crm.list_activities(page=request.args.get("page", 1),
                                   status=request.args.get("status") or None)
        reminders = crm.due_reminders()

        rows = []
        for r in page.items:
            done_btn = (h.action_form(f"/activities/{r['id']}/done",
                                      "Bajarildi", "success")
                        if r["status"] == "open" and h.can("crm.edit") else "")
            rows.append([
                e(r["activity_type"]), e(r["subject"]),
                e(r.get("customer_name") or r.get("lead_name") or "—"),
                e(r["due_at"] or "—"), h.badge(r["status"]), done_btn,
            ])

        reminder_html = ""
        if reminders:
            rem_rows = [[e(r["subject"]),
                         e(r.get("customer_name") or r.get("lead_name") or ""),
                         e(r["due_at"])] for r in reminders]
            reminder_html = h.card(
                f"⏰ Muddati kelgan eslatmalar ({len(reminders)})",
                h.data_table(["Mavzu", "Kim bilan", "Muddat"], rem_rows))

        new_form = ""
        if h.can("crm.create"):
            customers = [(r["id"], r["name"]) for r in ctx.db.query(
                "SELECT id, name FROM customers WHERE is_active = 1 "
                "ORDER BY name LIMIT 300")]
            new_form = h.card("Yangi faoliyat", h.form_page(
                "/activities/new",
                h.input_field("subject", "Mavzu *", required=True),
                h.select_field("activity_type", "Turi",
                               [("call", "Qo'ng'iroq"), ("email", "Email"),
                                ("meeting", "Uchrashuv"),
                                ("reminder", "Eslatma"), ("task", "Vazifa"),
                                ("note", "Izoh")]),
                h.select_field("customer_id", "Mijoz", customers,
                               empty="— yo'q —"),
                h.input_field("due_at", "Muddat", "", "datetime-local"),
                h.textarea_field("details", "Tafsilotlar"),
                submit="Qo'shish"))

        content = (h.page_head("Faoliyatlar") + reminder_html +
                   f'<div class="grid cols-2">'
                   f'{h.card("Ro`yxat", h.data_table(["Turi", "Mavzu", "Kim bilan", "Muddat", "Holat", ""], rows))}'
                   f"{new_form}</div>" +
                   h.pagination(page, "/activities", {}))
        return render(ctx, "Faoliyatlar", content, "/activities")

    @app.post("/activities/new")
    def activity_new():
        if not h.can("crm.create"):
            abort(403)
        f = request.form
        due = (f.get("due_at", "").replace("T", " ") + ":00"
               if f.get("due_at") else None)
        try:
            S.get("crm").add_activity(
                f.get("subject", ""), f.get("activity_type", "note"),
                customer_id=int(f["customer_id"])
                if f.get("customer_id") else None,
                details=f.get("details", ""), due_at=due, user=g.user)
        except UzERPError as exc:
            return redirect(h.redirect_msg("/activities", err=str(exc)))
        return redirect(h.redirect_msg("/activities", msg="Qo'shildi."))

    @app.post("/activities/<int:activity_id>/done")
    def activity_done(activity_id: int):
        if not h.can("crm.edit"):
            abort(403)
        try:
            S.get("crm").complete_activity(activity_id, g.user)
        except UzERPError as exc:
            return redirect(h.redirect_msg("/activities", err=str(exc)))
        return redirect(h.redirect_msg("/activities", msg="Bajarildi."))
