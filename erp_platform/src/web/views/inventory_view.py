# -*- coding: utf-8 -*-
"""Ombor sahifalari: mahsulotlar, qoldiqlar, harakatlar, inventarizatsiya."""
from __future__ import annotations

from flask import abort, g, redirect, request

from src.core.errors import UzERPError
from src.core.security import escape_html as e
from src.web import helpers as h


def register(app, ctx) -> None:
    """Ombor marshrutlari."""
    from src.web.server import render
    S = ctx.services

    def _warehouse_options():
        return [(w["id"], w["name"])
                for w in S.get("inventory").warehouses()]

    def _category_options():
        return [(c["id"], c["name"])
                for c in S.get("products").categories()]

    def _product_options():
        rows = ctx.db.query("SELECT id, name FROM products "
                            "WHERE is_active = 1 ORDER BY name LIMIT 500")
        return [(r["id"], r["name"]) for r in rows]

    # ------------------------------------------------------------------ #
    #  Mahsulotlar
    # ------------------------------------------------------------------ #

    @app.get("/products")
    def products_list():
        if not h.can("inventory.view"):
            abort(403)
        products = S.get("products")
        args = request.args
        page = products.list_products(
            page=args.get("page", 1), search=args.get("q") or None,
            category_id=int(args["cat"]) if args.get("cat") else None)

        rows = [[
            e(r["sku"] or ""), e(r["name"]), e(r["barcode"] or ""),
            e(r["unit"]), h.m(r["cost_price"]), h.m(r["sale_price"]),
            e(r["min_stock"]),
            h.btn_link(f"/products/{r['id']}/edit", "Tahrirlash", "small")
            if h.can("inventory.edit") else "",
        ] for r in page.items]

        search_form = f"""
        <form method="get" action="/products" class="card"
              style="display:flex;gap:10px;flex-wrap:wrap;align-items:flex-end">
          {h.input_field("q", "Qidiruv", args.get("q", ""),
                         placeholder="nom, SKU, shtrix-kod")}
          {h.select_field("cat", "Kategoriya", _category_options(),
                          args.get("cat"), empty="Barchasi")}
          <button class="btn primary" type="submit">Qidirish</button>
        </form>"""

        content = (h.page_head(
            "Mahsulotlar",
            h.btn_link("/products/new", "+ Yangi mahsulot", "primary")
            if h.can("inventory.create") else "") + search_form +
            h.card("", h.data_table(
                ["SKU", "Nomi", "Shtrix-kod", "Birlik", "Tannarx",
                 "Sotish narxi", "Min.zaxira", ""], rows,
                num_cols=(4, 5, 6))) +
            h.pagination(page, "/products",
                         {k: v for k, v in args.items()
                          if k != "page" and v}))
        return render(ctx, "Mahsulotlar", content, "/products")

    def _product_form(action: str, product: dict | None = None) -> str:
        p = product or {}
        return h.form_page(
            action,
            h.input_field("name", "Nomi *", p.get("name", ""), required=True),
            h.select_field("category_id", "Kategoriya", _category_options(),
                           p.get("category_id"), empty="—"),
            h.input_field("sku", "SKU (bo'sh = avto)", p.get("sku", "")),
            h.input_field("barcode", "Shtrix-kod", p.get("barcode", "")),
            h.input_field("unit", "O'lchov birligi", p.get("unit", "dona")),
            h.input_field("vat_rate", "QQS stavkasi (%)",
                          p.get("vat_rate", 12), "number", step="0.01"),
            h.input_field("cost_price", "Tannarx",
                          p.get("cost_price", 0), "number", step="0.01"),
            h.input_field("sale_price", "Sotish narxi",
                          p.get("sale_price", 0), "number", step="0.01"),
            h.input_field("min_stock", "Minimal zaxira",
                          p.get("min_stock", 0), "number", step="0.01"),
            h.textarea_field("description", "Tavsif",
                             p.get("description", "")),
            cancel_url="/products")

    @app.get("/products/new")
    def product_new():
        if not h.can("inventory.create"):
            abort(403)
        content = (h.page_head("Yangi mahsulot") +
                   h.card("", _product_form("/products/new")))
        return render(ctx, "Yangi mahsulot", content, "/products")

    @app.post("/products/new")
    def product_new_submit():
        if not h.can("inventory.create"):
            abort(403)
        try:
            S.get("products").create(_product_payload(), g.user)
        except UzERPError as exc:
            return redirect(h.redirect_msg("/products/new", err=str(exc)))
        return redirect(h.redirect_msg("/products", msg="Mahsulot qo'shildi."))

    @app.get("/products/<int:product_id>/edit")
    def product_edit(product_id: int):
        if not h.can("inventory.edit"):
            abort(403)
        try:
            product = S.get("products").get(product_id)
        except UzERPError:
            abort(404)
        deactivate = (h.action_form(f"/products/{product_id}/deactivate",
                                    "Nofaol qilish", "danger")
                      if h.can("inventory.delete") else "")
        content = (h.page_head(f"Tahrirlash: {product['name']}", deactivate) +
                   h.card("", _product_form(
                       f"/products/{product_id}/edit", product)))
        return render(ctx, "Mahsulot", content, "/products")

    @app.post("/products/<int:product_id>/edit")
    def product_edit_submit(product_id: int):
        if not h.can("inventory.edit"):
            abort(403)
        try:
            S.get("products").update(product_id, _product_payload(), g.user)
        except UzERPError as exc:
            return redirect(h.redirect_msg(
                f"/products/{product_id}/edit", err=str(exc)))
        return redirect(h.redirect_msg("/products", msg="Saqlandi."))

    @app.post("/products/<int:product_id>/deactivate")
    def product_deactivate(product_id: int):
        if not h.can("inventory.delete"):
            abort(403)
        S.get("products").deactivate(product_id, g.user)
        return redirect(h.redirect_msg("/products",
                                       msg="Mahsulot nofaol qilindi."))

    def _product_payload() -> dict:
        f = request.form
        return {k: f.get(k, "") for k in
                ("name", "sku", "barcode", "unit", "cost_price", "sale_price",
                 "vat_rate", "min_stock", "description")} | (
            {"category_id": int(f["category_id"])}
            if f.get("category_id") else {})

    # ------------------------------------------------------------------ #
    #  Qoldiqlar + omborlar + transfer
    # ------------------------------------------------------------------ #

    @app.get("/stock")
    def stock_page():
        if not h.can("inventory.view"):
            abort(403)
        inventory = S.get("inventory")
        args = request.args
        page = inventory.stock_overview(
            page=args.get("page", 1), search=args.get("q") or None,
            warehouse_id=int(args["wh"]) if args.get("wh") else None)

        rows = []
        for r in page.items:
            low = (' <span class="badge red">KAM</span>'
                   if r.get("is_low") else "")
            rows.append([
                e(r["sku"] or ""), e(r["name"]) + low,
                f'{e(r["quantity"])} {e(r["unit"])}',
                h.m(r["cost_price"]), h.m(r["stock_value"]),
            ])

        filter_form = f"""
        <form method="get" action="/stock" class="card"
              style="display:flex;gap:10px;flex-wrap:wrap;align-items:flex-end">
          {h.select_field("wh", "Ombor", _warehouse_options(),
                          args.get("wh"), empty="Barcha omborlar")}
          {h.input_field("q", "Qidiruv", args.get("q", ""))}
          <button class="btn primary" type="submit">Ko'rsatish</button>
        </form>"""

        transfer_form = ""
        if h.can("inventory.transfer"):
            transfer_form = h.card("Ombordan omborga ko'chirish", h.form_page(
                "/stock/transfer",
                h.select_field("product_id", "Mahsulot", _product_options(),
                               empty="— tanlang —"),
                h.input_field("qty", "Miqdor", "", "number", step="0.01",
                              required=True),
                h.select_field("wh_from", "Qayerdan", _warehouse_options()),
                h.select_field("wh_to", "Qayerga", _warehouse_options()),
                submit="Ko'chirish"))

        wh_form = ""
        if h.can("inventory.create"):
            wh_list = "".join(
                f'<li>{e(w["name"])} <span class="muted">'
                f'{e(w["address"] or "")}</span></li>'
                for w in inventory.warehouses())
            wh_form = h.card("Omborlar", f"<ul>{wh_list}</ul><hr class='sep'>" +
                             h.form_page("/stock/warehouse",
                                         h.input_field("name", "Yangi ombor nomi",
                                                       required=True),
                                         h.input_field("address", "Manzil"),
                                         submit="Qo'shish"))

        content = (h.page_head("Ombor qoldiqlari") + filter_form +
                   h.card(f"Jami qiymat: {h.m(inventory.stock_value())} so'm",
                          h.data_table(
                              ["SKU", "Mahsulot", "Qoldiq", "Tannarx",
                               "Qiymat"], rows, num_cols=(2, 3, 4))) +
                   h.pagination(page, "/stock",
                                {k: v for k, v in args.items()
                                 if k != "page" and v}) +
                   f'<div class="grid cols-2 mt">{transfer_form}{wh_form}</div>')
        return render(ctx, "Qoldiqlar", content, "/stock")

    @app.post("/stock/transfer")
    def stock_transfer():
        if not h.can("inventory.transfer"):
            abort(403)
        f = request.form
        try:
            S.get("inventory").transfer(
                int(f["product_id"]), int(f["wh_from"]), int(f["wh_to"]),
                f.get("qty", 0), user=g.user)
        except (UzERPError, ValueError, KeyError) as exc:
            return redirect(h.redirect_msg("/stock", err=str(exc)))
        return redirect(h.redirect_msg("/stock", msg="Ko'chirildi."))

    @app.post("/stock/warehouse")
    def stock_warehouse_new():
        if not h.can("inventory.create"):
            abort(403)
        try:
            S.get("inventory").create_warehouse(
                request.form.get("name", ""),
                request.form.get("address", ""), g.user)
        except UzERPError as exc:
            return redirect(h.redirect_msg("/stock", err=str(exc)))
        return redirect(h.redirect_msg("/stock", msg="Ombor qo'shildi."))

    # ------------------------------------------------------------------ #
    #  Harakatlar jurnali
    # ------------------------------------------------------------------ #

    @app.get("/moves")
    def moves_page():
        if not h.can("inventory.view"):
            abort(403)
        args = request.args
        page = S.get("inventory").moves_history(
            page=args.get("page", 1),
            product_id=int(args["pid"]) if args.get("pid") else None)
        type_labels = {"in": ("Kirim", "green"), "out": ("Chiqim", "red"),
                       "transfer": ("Ko'chirish", "blue"),
                       "adjust": ("Tuzatish", "amber")}
        rows = []
        for r in page.items:
            label, kind = type_labels.get(r["move_type"],
                                          (r["move_type"], "gray"))
            rows.append([
                e(r["id"]),
                f'<span class="badge {kind}">{e(label)}</span>',
                e(r["product_name"]),
                f'{e(r["quantity"])} {e(r["unit"])}',
                e(r["ref_type"] or ""), e(r["note"] or ""),
                e(r["created_at"] or ""),
            ])
        content = (h.page_head("Ombor harakatlari") +
                   h.card("", h.data_table(
                       ["#", "Turi", "Mahsulot", "Miqdor", "Manba", "Izoh",
                        "Vaqt"], rows, num_cols=(3,))) +
                   h.pagination(page, "/moves", {}))
        return render(ctx, "Harakatlar", content, "/moves")

    # ------------------------------------------------------------------ #
    #  Inventarizatsiya
    # ------------------------------------------------------------------ #

    @app.get("/counts")
    def counts_page():
        if not h.can("inventory.adjust"):
            abort(403)
        page = S.get("inventory").list_counts(
            page=request.args.get("page", 1))
        rows = [[
            h.link(f"/counts/{r['id']}", r["number"]),
            e(r["warehouse_name"]), h.badge(r["status"]),
            e(r["created_at"] or ""), e(r["completed_at"] or "—"),
        ] for r in page.items]
        start_form = h.card("Yangi inventarizatsiya", h.form_page(
            "/counts/start",
            h.select_field("warehouse_id", "Ombor", _warehouse_options()),
            submit="Boshlash"))
        content = (h.page_head("Inventarizatsiya") +
                   f'<div class="grid cols-2">'
                   f'{h.card("Ro`yxat", h.data_table(["№", "Ombor", "Holat", "Boshlangan", "Yakunlangan"], rows))}'
                   f"{start_form}</div>" +
                   h.pagination(page, "/counts", {}))
        return render(ctx, "Inventarizatsiya", content, "/counts")

    @app.post("/counts/start")
    def counts_start():
        if not h.can("inventory.adjust"):
            abort(403)
        try:
            count_id = S.get("inventory").start_count(
                int(request.form["warehouse_id"]), g.user)
        except (UzERPError, ValueError, KeyError) as exc:
            return redirect(h.redirect_msg("/counts", err=str(exc)))
        return redirect(f"/counts/{count_id}")

    @app.get("/counts/<int:count_id>")
    def count_detail(count_id: int):
        if not h.can("inventory.adjust"):
            abort(403)
        try:
            data = S.get("inventory").count_details(count_id)
        except UzERPError:
            abort(404)
        count, items = data["count"], data["items"]
        is_draft = count["status"] == "draft"

        rows = []
        for item in items:
            if is_draft:
                actual = f"""
                <form class="inline" method="post"
                      action="/counts/{count_id}/item">{h.csrf_field()}
                  <input type="hidden" name="product_id"
                         value="{item['product_id']}">
                  <input name="actual" type="number" step="0.01" min="0"
                         value="{item['actual_qty']}" style="width:110px;
                         padding:5px;border-radius:6px;border:1px solid
                         var(--border);background:var(--bg);color:var(--text)">
                  <button class="btn small" type="submit">OK</button></form>"""
            else:
                actual = e(item["actual_qty"])
            diff = item["difference"]
            diff_html = (f'<span class="badge red">{e(diff)}</span>'
                         if float(diff or 0) < 0 else
                         (f'<span class="badge green">+{e(diff)}</span>'
                          if float(diff or 0) > 0 else '<span class="muted">0</span>'))
            rows.append([e(item["sku"] or ""), e(item["product_name"]),
                         e(item["expected_qty"]), actual, diff_html])

        actions = []
        if is_draft:
            actions.append(h.action_form(f"/counts/{count_id}/complete",
                                         "Yakunlash va tuzatish", "success"))
        content = (h.page_head(f"Inventarizatsiya {count['number']}",
                               h.btn_link("/counts", "← Ro'yxat"), *actions) +
                   h.card(f"Holat: {count['status']}", h.data_table(
                       ["SKU", "Mahsulot", "Kutilgan", "Haqiqiy", "Farq"],
                       rows, num_cols=(2,))))
        return render(ctx, count["number"], content, "/counts")

    @app.post("/counts/<int:count_id>/item")
    def count_item_update(count_id: int):
        if not h.can("inventory.adjust"):
            abort(403)
        try:
            S.get("inventory").set_count_item(
                count_id, int(request.form["product_id"]),
                request.form.get("actual", 0))
        except (UzERPError, ValueError, KeyError) as exc:
            return redirect(h.redirect_msg(f"/counts/{count_id}",
                                           err=str(exc)))
        return redirect(f"/counts/{count_id}")

    @app.post("/counts/<int:count_id>/complete")
    def count_complete(count_id: int):
        if not h.can("inventory.adjust"):
            abort(403)
        try:
            adjusted = S.get("inventory").complete_count(count_id, g.user)
        except UzERPError as exc:
            return redirect(h.redirect_msg(f"/counts/{count_id}",
                                           err=str(exc)))
        return redirect(h.redirect_msg(
            f"/counts/{count_id}",
            msg=f"Yakunlandi: {adjusted} ta pozitsiya tuzatildi."))
