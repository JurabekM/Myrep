# -*- coding: utf-8 -*-
"""Savdo sahifalari: hujjatlar ro'yxati, yangi hujjat, tafsilot, POS kassa."""
from __future__ import annotations

from flask import abort, g, redirect, request

from src.core.errors import UzERPError
from src.core.security import escape_html as e
from src.core.utils import D
from src.web import helpers as h

#: POS savatlari: sessiya tokeni -> [{product_id, name, qty, price}]
_CARTS: dict[str, list[dict]] = {}
_ITEM_ROWS = 8  # yangi hujjat formasidagi qator soni


def register(app, ctx) -> None:
    """Savdo marshrutlari."""
    from src.web.server import render
    S = ctx.services

    def _products_options():
        rows = ctx.db.query(
            "SELECT id, name, sale_price, unit FROM products "
            "WHERE is_active = 1 ORDER BY name LIMIT 500")
        return [(r["id"], f"{r['name']} — {r['sale_price']} so'm")
                for r in rows]

    def _customers_options():
        rows = ctx.db.query(
            "SELECT id, name FROM customers WHERE is_active = 1 "
            "ORDER BY name LIMIT 500")
        return [(r["id"], r["name"]) for r in rows]

    def _parse_items(form) -> list[dict]:
        """Formadagi qatorlarni (bo'shlarini tashlab) items ro'yxatiga yig'adi."""
        items = []
        for i in range(_ITEM_ROWS):
            pid = form.get(f"product_{i}", "")
            qty = form.get(f"qty_{i}", "")
            if not pid or not qty:
                continue
            item = {"product_id": int(pid), "quantity": qty}
            price = form.get(f"price_{i}", "").strip()
            if price:
                item["price"] = price
            disc = form.get(f"disc_{i}", "").strip()
            if disc:
                item["discount"] = disc
            items.append(item)
        return items

    # ------------------------------------------------------------------ #
    #  Ro'yxat
    # ------------------------------------------------------------------ #

    @app.get("/sales")
    def sales_list():
        if not h.can("sales.view"):
            abort(403)
        sales = S.get("sales")
        args = request.args
        page = sales.list_docs(
            page=args.get("page", 1), per_page=25,
            doc_type=args.get("type") or None,
            status=args.get("status") or None,
            search=args.get("q") or None,
            date_from=args.get("from") or None,
            date_to=args.get("to") or None)

        filter_form = f"""
        <form method="get" action="/sales" class="card"
              style="display:flex;gap:10px;flex-wrap:wrap;align-items:flex-end">
          {h.select_field("type", "Turi",
                          list(h.DOC_TYPE_LABELS.items()),
                          args.get("type"), empty="Barchasi")}
          {h.select_field("status", "Holat",
                          [(k, v[0]) for k, v in h.STATUS_BADGES.items()
                           if k in ('draft', 'confirmed', 'partial', 'paid',
                                    'cancelled')],
                          args.get("status"), empty="Barchasi")}
          {h.input_field("from", "Sanadan", args.get("from", ""), "date")}
          {h.input_field("to", "Sanagacha", args.get("to", ""), "date")}
          {h.input_field("q", "Qidiruv", args.get("q", ""),
                         placeholder="raqam yoki mijoz")}
          <button class="btn primary" type="submit">Filtrlash</button>
        </form>"""

        rows = [[
            h.link(f"/sales/{r['id']}", r["number"]),
            e(h.DOC_TYPE_LABELS.get(r["doc_type"], r["doc_type"])),
            e(r.get("customer_name") or "—"),
            h.badge(r["status"]),
            h.m(r["total"]),
            h.m(r["paid_amount"]),
            e(r["doc_date"]),
        ] for r in page.items]

        actions = []
        if h.can("sales.create"):
            actions.append(h.btn_link("/sales/new", "+ Yangi hujjat",
                                      "primary"))
        if h.can("pos.operate"):
            actions.append(h.btn_link("/pos", "POS kassa"))

        content = (h.page_head("Savdo hujjatlari", *actions) + filter_form +
                   h.card("", h.data_table(
                       ["№", "Turi", "Mijoz", "Holat", "Jami", "To'langan",
                        "Sana"], rows, num_cols=(4, 5))) +
                   h.pagination(page, "/sales",
                                {k: v for k, v in args.items()
                                 if k != "page" and v}))
        return render(ctx, "Savdo", content, "/sales")

    # ------------------------------------------------------------------ #
    #  Yangi hujjat
    # ------------------------------------------------------------------ #

    @app.get("/sales/new")
    def sales_new():
        if not h.can("sales.create"):
            abort(403)
        products = _products_options()
        item_rows = []
        for i in range(_ITEM_ROWS):
            item_rows.append(f"""
            <tr>
              <td>{h.select_field(f"product_{i}", "", products,
                                  empty="— mahsulot —").replace(
                                  '<div class="field">', '<div>')}</td>
              <td><input name="qty_{i}" type="number" step="0.01" min="0"
                         placeholder="0"></td>
              <td><input name="price_{i}" type="number" step="0.01" min="0"
                         placeholder="avto"></td>
              <td><input name="disc_{i}" type="number" step="0.01" min="0"
                         placeholder="0"></td>
            </tr>""")

        content = h.page_head("Yangi savdo hujjati") + h.card("", f"""
        <form method="post" action="/sales/new">{h.csrf_field()}
          <div class="form-grid">
            {h.select_field("doc_type", "Hujjat turi",
                            [("quotation", "Taklif (Quotation)"),
                             ("order", "Buyurtma (Order)"),
                             ("invoice", "Hisob-faktura (Invoice)")],
                            "invoice")}
            {h.select_field("customer_id", "Mijoz", _customers_options(),
                            empty="— tanlanmagan —")}
            {h.input_field("doc_date", "Sana", "", "date")}
            {h.input_field("discount", "Hujjat chegirmasi (so'm)", "0",
                           "number", step="0.01")}
          </div>
          <div class="table-wrap mt"><table class="data">
            <thead><tr><th style="width:45%">Mahsulot</th><th>Miqdor</th>
            <th>Narx (bo'sh = avto)</th><th>Chegirma</th></tr></thead>
            <tbody>{''.join(item_rows)}</tbody></table></div>
          {h.textarea_field("note", "Izoh")}
          <div class="form-actions">
            <button class="btn primary" type="submit">Saqlash (qoralama)</button>
            <button class="btn success" type="submit" name="confirm"
                    value="1">Saqlash va tasdiqlash</button>
            <a class="btn" href="/sales">Bekor qilish</a>
          </div>
        </form>""")
        return render(ctx, "Yangi hujjat", content, "/sales")

    @app.post("/sales/new")
    def sales_new_submit():
        if not h.can("sales.create"):
            abort(403)
        sales = S.get("sales")
        try:
            items = _parse_items(request.form)
            doc_id = sales.create_doc(
                request.form.get("doc_type", "invoice"),
                int(request.form["customer_id"])
                if request.form.get("customer_id") else None,
                None, items, user=g.user,
                note=request.form.get("note", ""),
                discount=request.form.get("discount", 0) or 0,
                doc_date=request.form.get("doc_date") or None)
            if request.form.get("confirm"):
                sales.confirm(doc_id, user=g.user)
        except (UzERPError, ValueError, KeyError) as exc:
            return redirect(h.redirect_msg("/sales/new", err=str(exc)))
        return redirect(h.redirect_msg(f"/sales/{doc_id}",
                                       msg="Hujjat yaratildi."))

    # ------------------------------------------------------------------ #
    #  Tafsilot va amallar
    # ------------------------------------------------------------------ #

    @app.get("/sales/<int:doc_id>")
    def sales_detail(doc_id: int):
        if not h.can("sales.view"):
            abort(403)
        sales = S.get("sales")
        try:
            data = sales.get_doc(doc_id)
        except UzERPError:
            abort(404)
        doc, items = data["doc"], data["items"]

        item_rows = [[
            e(i["product_name"]), e(i["sku"] or ""),
            f'{e(i["quantity"])} {e(i["unit"])}',
            h.m(i["price"]), h.m(i["discount"]), h.m(i["vat_amount"]),
            h.m(i["total"]),
        ] for i in items]

        actions = []
        if doc["status"] == "draft" and h.can("sales.approve"):
            actions.append(h.action_form(f"/sales/{doc_id}/confirm",
                                         "Tasdiqlash", "success"))
        if (doc["status"] in ("confirmed", "partial")
                and doc["doc_type"] in ("invoice", "pos", "order")
                and h.can("cash.operate")):
            remaining = D(doc["total"]) - D(doc["paid_amount"])
            actions.append(f"""
            <form class="inline" method="post"
                  action="/sales/{doc_id}/payment">{h.csrf_field()}
              <input type="number" name="amount" step="0.01" min="0.01"
                     max="{remaining}" value="{remaining}"
                     style="width:140px;padding:6px;border-radius:7px;
                     border:1px solid var(--border);background:var(--bg);
                     color:var(--text)">
              <select name="method" style="padding:6px;border-radius:7px;
                      border:1px solid var(--border);background:var(--bg);
                      color:var(--text)">
                <option value="cash">Naqd</option>
                <option value="bank">Bank</option>
                <option value="card">Karta</option>
              </select>
              <button class="btn small success" type="submit">To'lov
              </button></form>""")
        if (doc["doc_type"] in ("quotation", "order")
                and doc["status"] != "cancelled" and h.can("sales.create")):
            actions.append(h.action_form(f"/sales/{doc_id}/convert",
                                         "Keyingi bosqichga o'tkazish"))
        if (doc["doc_type"] in ("invoice", "pos")
                and doc["status"] in ("confirmed", "partial", "paid")
                and h.can("sales.create")):
            actions.append(h.btn_link(f"/sales/{doc_id}/return",
                                      "Qaytarish", "small"))
        if (doc["status"] not in ("cancelled",)
                and D(doc["paid_amount"]) == 0 and h.can("sales.delete")):
            actions.append(h.action_form(f"/sales/{doc_id}/cancel",
                                         "Bekor qilish", "danger"))

        info = h.kv_list([
            ("Raqam", e(doc["number"])),
            ("Turi", e(h.DOC_TYPE_LABELS.get(doc["doc_type"],
                                             doc["doc_type"]))),
            ("Mijoz", e(doc.get("customer_name") or "—")),
            ("Holat", h.badge(doc["status"])),
            ("Sana", e(doc["doc_date"])),
            ("Oraliq jami", h.m(doc["subtotal"])),
            ("Chegirma", h.m(doc["discount"])),
            ("QQS (ichida)", h.m(doc["vat_amount"])),
            ("JAMI", f"<b>{h.m(doc['total'])}</b>"),
            ("To'langan", h.m(doc["paid_amount"])),
            ("Izoh", e(doc.get("note") or "—")),
        ])

        content = (h.page_head(f"Hujjat {doc['number']}",
                               h.btn_link("/sales", "← Ro'yxat"), *actions) +
                   f'<div class="grid cols-2">{h.card("Ma`lumotlar", info)}'
                   + h.card("Pozitsiyalar", h.data_table(
                       ["Mahsulot", "SKU", "Miqdor", "Narx", "Chegirma",
                        "QQS", "Jami"], item_rows,
                       num_cols=(3, 4, 5, 6))) + "</div>")
        return render(ctx, doc["number"], content, "/sales")

    @app.post("/sales/<int:doc_id>/confirm")
    def sales_confirm(doc_id: int):
        if not h.can("sales.approve"):
            abort(403)
        try:
            S.get("sales").confirm(doc_id, user=g.user)
        except UzERPError as exc:
            return redirect(h.redirect_msg(f"/sales/{doc_id}", err=str(exc)))
        return redirect(h.redirect_msg(f"/sales/{doc_id}",
                                       msg="Hujjat tasdiqlandi."))

    @app.post("/sales/<int:doc_id>/cancel")
    def sales_cancel(doc_id: int):
        if not h.can("sales.delete"):
            abort(403)
        try:
            S.get("sales").cancel(doc_id, user=g.user)
        except UzERPError as exc:
            return redirect(h.redirect_msg(f"/sales/{doc_id}", err=str(exc)))
        return redirect(h.redirect_msg(f"/sales/{doc_id}",
                                       msg="Hujjat bekor qilindi."))

    @app.post("/sales/<int:doc_id>/convert")
    def sales_convert(doc_id: int):
        if not h.can("sales.create"):
            abort(403)
        try:
            new_id = S.get("sales").convert(doc_id, user=g.user)
        except UzERPError as exc:
            return redirect(h.redirect_msg(f"/sales/{doc_id}", err=str(exc)))
        return redirect(h.redirect_msg(f"/sales/{new_id}",
                                       msg="Hujjat konvertatsiya qilindi."))

    @app.post("/sales/<int:doc_id>/payment")
    def sales_payment(doc_id: int):
        if not h.can("cash.operate"):
            abort(403)
        payments = S.get("payments")
        try:
            payments.receive_for_sale(
                doc_id, request.form.get("amount", 0),
                method=request.form.get("method", "cash"), user=g.user)
        except UzERPError as exc:
            return redirect(h.redirect_msg(f"/sales/{doc_id}", err=str(exc)))
        return redirect(h.redirect_msg(f"/sales/{doc_id}",
                                       msg="To'lov qabul qilindi."))

    # ------------------------------------------------------------------ #
    #  Qaytarish
    # ------------------------------------------------------------------ #

    @app.get("/sales/<int:doc_id>/return")
    def sales_return_form(doc_id: int):
        if not h.can("sales.create"):
            abort(403)
        data = S.get("sales").get_doc(doc_id)
        doc, items = data["doc"], data["items"]
        rows = []
        for i, item in enumerate(items):
            rows.append(f"""
            <tr><td>{e(item['product_name'])}</td>
            <td class="num">{e(item['quantity'])} {e(item['unit'])}</td>
            <td><input type="hidden" name="pid_{i}"
                       value="{item['product_id']}">
                <input name="rqty_{i}" type="number" step="0.01" min="0"
                       max="{item['quantity']}" placeholder="0"></td></tr>""")
        content = h.page_head(f"Qaytarish — {doc['number']}") + h.card("", f"""
        <form method="post" action="/sales/{doc_id}/return">{h.csrf_field()}
          <div class="table-wrap"><table class="data">
          <thead><tr><th>Mahsulot</th><th class="num">Sotilgan</th>
          <th>Qaytarish miqdori</th></tr></thead>
          <tbody>{''.join(rows)}</tbody></table></div>
          {h.textarea_field("note", "Sabab / izoh")}
          <div class="form-actions">
            <button class="btn danger" type="submit">Qaytarishni
            rasmiylashtirish</button>
            <a class="btn" href="/sales/{doc_id}">Bekor qilish</a>
          </div></form>""")
        return render(ctx, "Qaytarish", content, "/sales")

    @app.post("/sales/<int:doc_id>/return")
    def sales_return_submit(doc_id: int):
        if not h.can("sales.create"):
            abort(403)
        items = []
        for i in range(50):
            pid = request.form.get(f"pid_{i}")
            qty = request.form.get(f"rqty_{i}", "").strip()
            if pid and qty and D(qty) > 0:
                items.append({"product_id": int(pid), "quantity": qty})
        if not items:
            return redirect(h.redirect_msg(f"/sales/{doc_id}/return",
                                           err="Miqdor kiritilmadi."))
        try:
            ret_id = S.get("sales").create_return(
                doc_id, items, user=g.user,
                note=request.form.get("note", ""))
        except UzERPError as exc:
            return redirect(h.redirect_msg(f"/sales/{doc_id}/return",
                                           err=str(exc)))
        return redirect(h.redirect_msg(f"/sales/{ret_id}",
                                       msg="Qaytarish rasmiylashtirildi."))

    # ------------------------------------------------------------------ #
    #  POS kassa
    # ------------------------------------------------------------------ #

    @app.get("/pos")
    def pos_page():
        if not h.can("pos.operate"):
            abort(403)
        cart = _CARTS.get(g.session_token, [])
        total = sum(D(i["qty"]) * D(i["price"]) for i in cart)

        cart_rows = []
        for idx, item in enumerate(cart):
            cart_rows.append([
                e(item["name"]), e(item["qty"]), h.m(item["price"]),
                h.m(D(item["qty"]) * D(item["price"])),
                h.action_form(f"/pos/remove/{idx}", "✕", "danger")])

        add_form = f"""
        <form method="post" action="/pos/add">{h.csrf_field()}
          <div class="form-grid">
            {h.input_field("barcode", "Shtrix-kod (skaner)", "",
                           placeholder="skanerlang yoki kiriting")}
            {h.select_field("product_id", "Yoki mahsulot",
                            _products_options(), empty="— tanlang —")}
            {h.input_field("qty", "Miqdor", "1", "number", step="0.01")}
          </div>
          <div class="form-actions">
            <button class="btn primary" type="submit">Savatga qo'shish
            </button></div></form>"""

        checkout = f"""
        <div class="pos-total">{h.m(total)} so'm</div><hr class="sep">
        <form method="post" action="/pos/checkout">{h.csrf_field()}
          <div class="form-grid">
            {h.select_field("method", "To'lov usuli",
                            [("cash", "Naqd"), ("card", "Karta"),
                             ("click", "Click"), ("payme", "Payme")])}
            {h.select_field("customer_id", "Mijoz (ixtiyoriy)",
                            _customers_options(), empty="— umumiy xaridor —")}
          </div>
          <div class="form-actions">
            <button class="btn success" type="submit"
                    {'' if cart else 'disabled'}>SOTISH</button>
            {h.action_form("/pos/clear", "Savatni tozalash", "danger")
             if cart else ''}
          </div></form>"""

        content = (h.page_head("POS kassa") +
                   f'<div class="pos-grid">'
                   f'{h.card("Savat", h.data_table(["Mahsulot", "Miqdor", "Narx", "Jami", ""], cart_rows, "Savat bo`sh", num_cols=(1, 2, 3)))}'
                   f'<div>{h.card("Mahsulot qo`shish", add_form)}'
                   f'{h.card("To`lov", checkout)}</div></div>')
        return render(ctx, "POS", content, "/pos")

    @app.post("/pos/add")
    def pos_add():
        if not h.can("pos.operate"):
            abort(403)
        products = S.get("products")
        barcode = request.form.get("barcode", "").strip()
        product = None
        if barcode:
            product = products.find_by_barcode(barcode)
            if not product:
                return redirect(h.redirect_msg(
                    "/pos", err=f"Shtrix-kod topilmadi: {barcode}"))
        elif request.form.get("product_id"):
            try:
                product = products.get(int(request.form["product_id"]))
            except UzERPError:
                product = None
        if not product:
            return redirect(h.redirect_msg("/pos", err="Mahsulot tanlanmadi."))

        qty = request.form.get("qty", "1") or "1"
        cart = _CARTS.setdefault(g.session_token, [])
        for item in cart:
            if item["product_id"] == product["id"]:
                item["qty"] = str(D(item["qty"]) + D(qty))
                break
        else:
            cart.append({"product_id": product["id"], "name": product["name"],
                         "qty": qty, "price": str(product["sale_price"])})
        return redirect("/pos")

    @app.post("/pos/remove/<int:index>")
    def pos_remove(index: int):
        if not h.can("pos.operate"):
            abort(403)
        cart = _CARTS.get(g.session_token, [])
        if 0 <= index < len(cart):
            cart.pop(index)
        return redirect("/pos")

    @app.post("/pos/clear")
    def pos_clear():
        if not h.can("pos.operate"):
            abort(403)
        _CARTS.pop(g.session_token, None)
        return redirect("/pos")

    @app.post("/pos/checkout")
    def pos_checkout():
        if not h.can("pos.operate"):
            abort(403)
        cart = _CARTS.get(g.session_token, [])
        if not cart:
            return redirect(h.redirect_msg("/pos", err="Savat bo'sh."))
        items = [{"product_id": i["product_id"], "quantity": i["qty"],
                  "price": i["price"]} for i in cart]
        try:
            result = S.get("sales").pos_sale(
                items, user=g.user,
                customer_id=int(request.form["customer_id"])
                if request.form.get("customer_id") else None,
                method=request.form.get("method", "cash"))
        except UzERPError as exc:
            return redirect(h.redirect_msg("/pos", err=str(exc)))
        _CARTS.pop(g.session_token, None)
        doc = result["doc"]
        return redirect(h.redirect_msg(
            f"/sales/{doc['id']}",
            msg=f"Savdo yakunlandi: {doc['number']}, {doc['total']} so'm."))
