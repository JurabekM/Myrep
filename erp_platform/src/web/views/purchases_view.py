# -*- coding: utf-8 -*-
"""Xarid sahifalari: xaridlar ro'yxati/yangi/tafsilot, ta'minotchilar."""
from __future__ import annotations

from flask import abort, g, redirect, request

from src.core.errors import UzERPError
from src.core.security import escape_html as e
from src.core.utils import D
from src.web import helpers as h

_ITEM_ROWS = 8


def register(app, ctx) -> None:
    """Xarid marshrutlari."""
    from src.web.server import render
    S = ctx.services

    def _supplier_options():
        rows = ctx.db.query("SELECT id, name FROM suppliers "
                            "WHERE is_active = 1 ORDER BY name")
        return [(r["id"], r["name"]) for r in rows]

    def _product_options():
        rows = ctx.db.query("SELECT id, name, cost_price FROM products "
                            "WHERE is_active = 1 ORDER BY name LIMIT 500")
        return [(r["id"], f"{r['name']} — {r['cost_price']}") for r in rows]

    def _warehouse_options():
        return [(w["id"], w["name"]) for w in S.get("inventory").warehouses()]

    # ------------------------------------------------------------------ #
    #  Xaridlar
    # ------------------------------------------------------------------ #

    @app.get("/purchases")
    def purchases_list():
        if not h.can("purchases.view"):
            abort(403)
        args = request.args
        page = S.get("purchases").list_purchases(
            page=args.get("page", 1), status=args.get("status") or None,
            search=args.get("q") or None)
        rows = [[
            h.link(f"/purchases/{r['id']}", r["number"]),
            e(r.get("supplier_name") or "—"), h.badge(r["status"]),
            h.m(r["total"]), h.m(r["paid_amount"]), e(r["doc_date"]),
        ] for r in page.items]
        content = (h.page_head(
            "Xaridlar",
            h.btn_link("/purchases/new", "+ Yangi xarid", "primary")
            if h.can("purchases.create") else "") +
            h.card("", h.data_table(
                ["№", "Ta'minotchi", "Holat", "Jami", "To'langan", "Sana"],
                rows, num_cols=(3, 4))) +
            h.pagination(page, "/purchases", {}))
        return render(ctx, "Xaridlar", content, "/purchases")

    @app.get("/purchases/new")
    def purchase_new():
        if not h.can("purchases.create"):
            abort(403)
        products = _product_options()
        item_rows = []
        for i in range(_ITEM_ROWS):
            item_rows.append(f"""
            <tr><td>{h.select_field(f"product_{i}", "", products,
                                    empty="— mahsulot —").replace(
                                    '<div class="field">', '<div>')}</td>
            <td><input name="qty_{i}" type="number" step="0.01" min="0"
                       placeholder="0"></td>
            <td><input name="price_{i}" type="number" step="0.01" min="0"
                       placeholder="narx"></td></tr>""")
        content = h.page_head("Yangi xarid") + h.card("", f"""
        <form method="post" action="/purchases/new">{h.csrf_field()}
          <div class="form-grid">
            {h.select_field("supplier_id", "Ta'minotchi",
                            _supplier_options(), empty="— tanlang —")}
            {h.select_field("warehouse_id", "Ombor", _warehouse_options())}
            {h.input_field("doc_date", "Sana", "", "date")}
          </div>
          <div class="table-wrap mt"><table class="data">
            <thead><tr><th style="width:50%">Mahsulot</th><th>Miqdor</th>
            <th>Narx (QQS bilan)</th></tr></thead>
            <tbody>{''.join(item_rows)}</tbody></table></div>
          {h.textarea_field("note", "Izoh")}
          <div class="form-actions">
            <button class="btn primary" type="submit">Saqlash</button>
            <button class="btn success" type="submit" name="receive"
                    value="1">Saqlash va qabul qilish</button>
            <a class="btn" href="/purchases">Bekor</a></div></form>""")
        return render(ctx, "Yangi xarid", content, "/purchases")

    @app.post("/purchases/new")
    def purchase_new_submit():
        if not h.can("purchases.create"):
            abort(403)
        f = request.form
        items = []
        for i in range(_ITEM_ROWS):
            if f.get(f"product_{i}") and f.get(f"qty_{i}"):
                items.append({"product_id": int(f[f"product_{i}"]),
                              "quantity": f[f"qty_{i}"],
                              "price": f.get(f"price_{i}") or 0})
        try:
            purchases = S.get("purchases")
            purchase_id = purchases.create(
                int(f["supplier_id"]) if f.get("supplier_id") else None,
                int(f["warehouse_id"]), items, user=g.user,
                note=f.get("note", ""), doc_date=f.get("doc_date") or None)
            if f.get("receive"):
                purchases.receive(purchase_id, g.user)
        except (UzERPError, ValueError, KeyError) as exc:
            return redirect(h.redirect_msg("/purchases/new", err=str(exc)))
        return redirect(h.redirect_msg(f"/purchases/{purchase_id}",
                                       msg="Xarid yaratildi."))

    @app.get("/purchases/<int:purchase_id>")
    def purchase_detail(purchase_id: int):
        if not h.can("purchases.view"):
            abort(403)
        try:
            data = S.get("purchases").get(purchase_id)
        except UzERPError:
            abort(404)
        doc, items = data["doc"], data["items"]
        rows = [[e(i["product_name"]), f'{e(i["quantity"])} {e(i["unit"])}',
                 h.m(i["price"]), h.m(i["vat_amount"]), h.m(i["total"])]
                for i in items]

        actions = []
        if doc["status"] == "draft" and h.can("purchases.receive"):
            actions.append(h.action_form(f"/purchases/{purchase_id}/receive",
                                         "Qabul qilish", "success"))
        if (doc["status"] in ("received", "partial")
                and h.can("cash.operate")):
            remaining = D(doc["total"]) - D(doc["paid_amount"])
            actions.append(f"""
            <form class="inline" method="post"
                  action="/purchases/{purchase_id}/pay">{h.csrf_field()}
              <input type="number" name="amount" step="0.01" min="0.01"
                     max="{remaining}" value="{remaining}"
                     style="width:140px;padding:6px;border-radius:7px;
                     border:1px solid var(--border);background:var(--bg);
                     color:var(--text)">
              <select name="method" style="padding:6px;border-radius:7px;
                      border:1px solid var(--border);background:var(--bg);
                      color:var(--text)">
                <option value="bank">Bank</option>
                <option value="cash">Naqd</option></select>
              <button class="btn small success" type="submit">To'lash
              </button></form>""")
        if (doc["status"] != "cancelled" and D(doc["paid_amount"]) == 0
                and h.can("purchases.delete")):
            actions.append(h.action_form(f"/purchases/{purchase_id}/cancel",
                                         "Bekor qilish", "danger"))

        info = h.kv_list([
            ("Raqam", e(doc["number"])),
            ("Ta'minotchi", e(doc.get("supplier_name") or "—")),
            ("Holat", h.badge(doc["status"])),
            ("Sana", e(doc["doc_date"])),
            ("QQS (ichida)", h.m(doc["vat_amount"])),
            ("JAMI", f"<b>{h.m(doc['total'])}</b>"),
            ("To'langan", h.m(doc["paid_amount"])),
            ("Izoh", e(doc.get("note") or "—")),
        ])
        content = (h.page_head(f"Xarid {doc['number']}",
                               h.btn_link("/purchases", "← Ro'yxat"),
                               *actions) +
                   f'<div class="grid cols-2">{h.card("Ma`lumotlar", info)}'
                   + h.card("Pozitsiyalar", h.data_table(
                       ["Mahsulot", "Miqdor", "Narx", "QQS", "Jami"], rows,
                       num_cols=(2, 3, 4))) + "</div>")
        return render(ctx, doc["number"], content, "/purchases")

    @app.post("/purchases/<int:purchase_id>/receive")
    def purchase_receive(purchase_id: int):
        if not h.can("purchases.receive"):
            abort(403)
        try:
            S.get("purchases").receive(purchase_id, g.user)
        except UzERPError as exc:
            return redirect(h.redirect_msg(f"/purchases/{purchase_id}",
                                           err=str(exc)))
        return redirect(h.redirect_msg(f"/purchases/{purchase_id}",
                                       msg="Xarid qabul qilindi."))

    @app.post("/purchases/<int:purchase_id>/pay")
    def purchase_pay(purchase_id: int):
        if not h.can("cash.operate"):
            abort(403)
        try:
            S.get("payments").pay_for_purchase(
                purchase_id, request.form.get("amount", 0),
                method=request.form.get("method", "bank"), user=g.user)
        except UzERPError as exc:
            return redirect(h.redirect_msg(f"/purchases/{purchase_id}",
                                           err=str(exc)))
        return redirect(h.redirect_msg(f"/purchases/{purchase_id}",
                                       msg="To'lov amalga oshirildi."))

    @app.post("/purchases/<int:purchase_id>/cancel")
    def purchase_cancel(purchase_id: int):
        if not h.can("purchases.delete"):
            abort(403)
        try:
            S.get("purchases").cancel(purchase_id, g.user)
        except UzERPError as exc:
            return redirect(h.redirect_msg(f"/purchases/{purchase_id}",
                                           err=str(exc)))
        return redirect(h.redirect_msg(f"/purchases/{purchase_id}",
                                       msg="Xarid bekor qilindi."))

    # ------------------------------------------------------------------ #
    #  Ta'minotchilar
    # ------------------------------------------------------------------ #

    @app.get("/suppliers")
    def suppliers_list():
        if not h.can("suppliers.view"):
            abort(403)
        suppliers = S.get("suppliers")
        page = suppliers.list_suppliers(
            page=request.args.get("page", 1),
            search=request.args.get("q") or None)
        rows = [[
            e(r["name"]), e(r["tin"] or ""), e(r["phone"] or ""),
            h.m(suppliers.payables(r["id"])),
            h.btn_link(f"/suppliers/{r['id']}/edit", "Tahrirlash", "small")
            if h.can("suppliers.edit") else "",
        ] for r in page.items]

        new_form = ""
        if h.can("suppliers.create"):
            new_form = h.card("Yangi ta'minotchi", h.form_page(
                "/suppliers/new",
                h.input_field("name", "Nomi *", required=True),
                h.input_field("tin", "STIR (INN)"),
                h.input_field("phone", "Telefon"),
                h.input_field("email", "Email"),
                h.input_field("address", "Manzil", full=True),
                submit="Qo'shish"))

        content = (h.page_head("Ta'minotchilar") +
                   f'<div class="grid cols-2">'
                   f'{h.card("Ro`yxat", h.data_table(["Nomi", "STIR", "Telefon", "Qarzimiz", ""], rows, num_cols=(3,)))}'
                   f"{new_form}</div>" +
                   h.pagination(page, "/suppliers", {}))
        return render(ctx, "Ta'minotchilar", content, "/suppliers")

    @app.post("/suppliers/new")
    def supplier_new():
        if not h.can("suppliers.create"):
            abort(403)
        try:
            S.get("suppliers").create(
                {k: request.form.get(k, "") for k in
                 ("name", "tin", "phone", "email", "address")}, g.user)
        except UzERPError as exc:
            return redirect(h.redirect_msg("/suppliers", err=str(exc)))
        return redirect(h.redirect_msg("/suppliers", msg="Qo'shildi."))

    @app.get("/suppliers/<int:supplier_id>/edit")
    def supplier_edit(supplier_id: int):
        if not h.can("suppliers.edit"):
            abort(403)
        try:
            s = S.get("suppliers").get(supplier_id)
        except UzERPError:
            abort(404)
        content = (h.page_head(f"Tahrirlash: {s['name']}") +
                   h.card("", h.form_page(
                       f"/suppliers/{supplier_id}/edit",
                       h.input_field("name", "Nomi *", s["name"],
                                     required=True),
                       h.input_field("tin", "STIR", s["tin"] or ""),
                       h.input_field("phone", "Telefon", s["phone"] or ""),
                       h.input_field("email", "Email", s["email"] or ""),
                       h.input_field("address", "Manzil", s["address"] or "",
                                     full=True),
                       cancel_url="/suppliers")))
        return render(ctx, "Ta'minotchi", content, "/suppliers")

    @app.post("/suppliers/<int:supplier_id>/edit")
    def supplier_edit_submit(supplier_id: int):
        if not h.can("suppliers.edit"):
            abort(403)
        try:
            S.get("suppliers").update(
                supplier_id,
                {k: request.form.get(k, "") for k in
                 ("name", "tin", "phone", "email", "address")}, g.user)
        except UzERPError as exc:
            return redirect(h.redirect_msg(
                f"/suppliers/{supplier_id}/edit", err=str(exc)))
        return redirect(h.redirect_msg("/suppliers", msg="Saqlandi."))
