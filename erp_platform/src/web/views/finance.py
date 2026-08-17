# -*- coding: utf-8 -*-
"""Moliya sahifalari: kassa/bank, jurnal, hisoblar rejasi, aktivlar, hisobotlar."""
from __future__ import annotations

from datetime import date

from flask import abort, g, redirect, request, send_file

from src.core.errors import UzERPError
from src.core.security import escape_html as e
from src.core.utils import money, today_str
from src.web import helpers as h

_JOURNAL_ROWS = 6


def register(app, ctx) -> None:
    """Moliya marshrutlari."""
    from src.web.server import render
    S = ctx.services

    def _month_range():
        today = today_str()
        return (request.args.get("from") or f"{today[:7]}-01",
                request.args.get("to") or today)

    def _period_form(action: str) -> str:
        date_from, date_to = _month_range()
        return f"""
        <form method="get" action="{action}" class="card"
              style="display:flex;gap:10px;flex-wrap:wrap;align-items:flex-end">
          {h.input_field("from", "Sanadan", date_from, "date")}
          {h.input_field("to", "Sanagacha", date_to, "date")}
          <button class="btn primary" type="submit">Ko'rsatish</button>
        </form>"""

    def _export_buttons(report: str) -> str:
        date_from, date_to = _month_range()
        if not h.can("reports.export"):
            return ""
        return "".join(
            h.btn_link(f"/reports/{report}/export/{fmt}?from={date_from}"
                       f"&to={date_to}", fmt.upper(), "small")
            for fmt in ("xlsx", "pdf", "csv", "docx", "json"))

    # ------------------------------------------------------------------ #
    #  Kassa / Bank
    # ------------------------------------------------------------------ #

    @app.get("/cash")
    def cash_page():
        if not h.can("cash.view"):
            abort(403)
        payments = S.get("payments")
        args = request.args
        page = payments.cashbook(
            page=args.get("page", 1), method=args.get("m") or None,
            payment_type=args.get("t") or None)

        rows = [[
            e(r["number"]), h.badge(r["payment_type"]),
            e(r["method"]), h.m(r["amount"]),
            e((r.get("corr_code") or "") + " " + (r.get("corr_name") or "")),
            e(r["note"] or ""), e(r["payment_date"]),
        ] for r in page.items]

        ops_form = ""
        if h.can("cash.operate"):
            accounts = S.get("accounting").accounts()
            expense_opts = [(a["code"], f"{a['code']} {a['name']}")
                            for a in accounts if a["type"] == "expense"]
            income_opts = [(a["code"], f"{a['code']} {a['name']}")
                           for a in accounts if a["type"] == "income"]
            ops_form = f"""
            <div class="grid cols-2">
            {h.card("Xarajat (chiqim)", h.form_page(
                "/cash/expense",
                h.input_field("amount", "Summa *", "", "number",
                              step="0.01", required=True),
                h.select_field("method", "Usul",
                               [("cash", "Naqd (kassa)"), ("bank", "Bank")]),
                h.select_field("account", "Xarajat hisobi", expense_opts,
                               "9410"),
                h.input_field("note", "Izoh *", required=True),
                submit="Chiqim qilish"))}
            {h.card("Boshqa kirim", h.form_page(
                "/cash/income",
                h.input_field("amount", "Summa *", "", "number",
                              step="0.01", required=True),
                h.select_field("method", "Usul",
                               [("cash", "Naqd (kassa)"), ("bank", "Bank")]),
                h.select_field("account", "Daromad hisobi", income_opts,
                               "9010"),
                h.input_field("note", "Izoh *", required=True),
                submit="Kirim qilish"))}
            </div>"""

        stats = f"""
        <div class="grid cols-2">
          {h.stat_card("Kassa qoldig'i (5010)",
                       h.m(payments.cash_balance()), "so'm", "green")}
          {h.stat_card("Bank qoldig'i (5110)",
                       h.m(payments.bank_balance()), "so'm", "accent")}
        </div>"""

        content = (h.page_head("Kassa / Bank") + stats +
                   h.card("Kassa kitobi", h.data_table(
                       ["№", "Turi", "Usul", "Summa", "Korr. hisob", "Izoh",
                        "Sana"], rows, num_cols=(3,))) +
                   h.pagination(page, "/cash", {}) +
                   f'<div class="mt">{ops_form}</div>')
        return render(ctx, "Kassa", content, "/cash")

    @app.post("/cash/expense")
    def cash_expense():
        if not h.can("cash.operate"):
            abort(403)
        try:
            S.get("payments").expense(
                request.form.get("amount", 0),
                request.form.get("note", ""),
                method=request.form.get("method", "cash"),
                expense_account=request.form.get("account", "9410"),
                user=g.user)
        except UzERPError as exc:
            return redirect(h.redirect_msg("/cash", err=str(exc)))
        return redirect(h.redirect_msg("/cash", msg="Xarajat qayd etildi."))

    @app.post("/cash/income")
    def cash_income():
        if not h.can("cash.operate"):
            abort(403)
        try:
            S.get("payments").other_income(
                request.form.get("amount", 0),
                request.form.get("note", ""),
                method=request.form.get("method", "cash"),
                income_account=request.form.get("account", "9010"),
                user=g.user)
        except UzERPError as exc:
            return redirect(h.redirect_msg("/cash", err=str(exc)))
        return redirect(h.redirect_msg("/cash", msg="Kirim qayd etildi."))

    # ------------------------------------------------------------------ #
    #  Jurnal
    # ------------------------------------------------------------------ #

    @app.get("/journal")
    def journal_list():
        if not h.can("accounting.view"):
            abort(403)
        args = request.args
        page = S.get("accounting").list_entries(
            page=args.get("page", 1), search=args.get("q") or None,
            date_from=args.get("from") or None,
            date_to=args.get("to") or None)
        rows = [[
            h.link(f"/journal/{r['id']}", r["number"]),
            e(r["entry_date"]), e(r["memo"]), e(r["ref_type"] or "qo'lda"),
            h.m(r["amount"] or 0),
        ] for r in page.items]
        content = (h.page_head(
            "Buxgalteriya jurnali",
            h.btn_link("/journal/new", "+ Qo'lda o'tkazma", "primary")
            if h.can("accounting.post") else "") +
            h.card("", h.data_table(
                ["№", "Sana", "Mazmuni", "Manba", "Summa"], rows,
                num_cols=(4,))) +
            h.pagination(page, "/journal", {}))
        return render(ctx, "Jurnal", content, "/journal")

    @app.get("/journal/new")
    def journal_new():
        if not h.can("accounting.post"):
            abort(403)
        accounts = [(a["code"], f"{a['code']} — {a['name']}")
                    for a in S.get("accounting").accounts()]
        line_rows = []
        for i in range(_JOURNAL_ROWS):
            line_rows.append(f"""
            <tr><td>{h.select_field(f"acc_{i}", "", accounts,
                                    empty="— hisob —").replace(
                                    '<div class="field">', '<div>')}</td>
            <td><input name="debit_{i}" type="number" step="0.01" min="0"
                       placeholder="0"></td>
            <td><input name="credit_{i}" type="number" step="0.01" min="0"
                       placeholder="0"></td></tr>""")
        content = h.page_head("Qo'lda o'tkazma") + h.card("", f"""
        <form method="post" action="/journal/new">{h.csrf_field()}
          <div class="form-grid">
            {h.input_field("memo", "Mazmuni *", required=True)}
            {h.input_field("entry_date", "Sana", today_str(), "date")}
          </div>
          <div class="table-wrap mt"><table class="data">
          <thead><tr><th style="width:55%">Hisob</th><th>Debet</th>
          <th>Kredit</th></tr></thead>
          <tbody>{''.join(line_rows)}</tbody></table></div>
          <p class="muted mt">Debet va kredit jami teng bo'lishi shart
          (dvoyna zapis).</p>
          <div class="form-actions">
            <button class="btn primary" type="submit">O'tkazish</button>
            <a class="btn" href="/journal">Bekor</a></div></form>""")
        return render(ctx, "Yangi o'tkazma", content, "/journal")

    @app.post("/journal/new")
    def journal_new_submit():
        if not h.can("accounting.post"):
            abort(403)
        f = request.form
        lines = []
        for i in range(_JOURNAL_ROWS):
            acc = f.get(f"acc_{i}")
            debit = f.get(f"debit_{i}", "").strip()
            credit = f.get(f"credit_{i}", "").strip()
            if acc and (debit or credit):
                line = {"account": acc}
                if debit and float(debit or 0) > 0:
                    line["debit"] = debit
                if credit and float(credit or 0) > 0:
                    line["credit"] = credit
                lines.append(line)
        try:
            entry_id = S.get("accounting").create_entry(
                f.get("memo", ""), lines,
                entry_date=f.get("entry_date") or None, ref_type="manual",
                user=g.user)
        except UzERPError as exc:
            return redirect(h.redirect_msg("/journal/new", err=str(exc)))
        return redirect(h.redirect_msg(f"/journal/{entry_id}",
                                       msg="O'tkazma yozildi."))

    @app.get("/journal/<int:entry_id>")
    def journal_detail(entry_id: int):
        if not h.can("accounting.view"):
            abort(403)
        try:
            data = S.get("accounting").get_entry(entry_id)
        except UzERPError:
            abort(404)
        entry, lines = data["entry"], data["lines"]
        rows = [[e(l["account_code"]), e(l["account_name"]),
                 h.m(l["debit"]) if float(l["debit"] or 0) else "",
                 h.m(l["credit"]) if float(l["credit"] or 0) else ""]
                for l in lines]
        info = h.kv_list([
            ("Raqam", e(entry["number"])), ("Sana", e(entry["entry_date"])),
            ("Mazmuni", e(entry["memo"])),
            ("Manba", e(entry["ref_type"] or "qo'lda")),
        ])
        content = (h.page_head(f"O'tkazma {entry['number']}",
                               h.btn_link("/journal", "← Jurnal")) +
                   f'<div class="grid cols-2">{h.card("Ma`lumot", info)}'
                   f'{h.card("Satrlar", h.data_table(["Kod", "Hisob", "Debet", "Kredit"], rows, num_cols=(2, 3)))}'
                   "</div>")
        return render(ctx, entry["number"], content, "/journal")

    # ------------------------------------------------------------------ #
    #  Hisoblar rejasi
    # ------------------------------------------------------------------ #

    @app.get("/accounts")
    def accounts_page():
        if not h.can("accounting.view"):
            abort(403)
        accounting = S.get("accounting")
        type_labels = {"asset": "Aktiv", "contra_asset": "Kontr-aktiv",
                       "liability": "Majburiyat", "equity": "Kapital",
                       "income": "Daromad", "expense": "Xarajat"}
        rows = [[
            e(a["code"]), e(a["name"]),
            e(type_labels.get(a["type"], a["type"])),
            h.m(accounting.account_balance(a["code"])),
        ] for a in accounting.accounts()]

        new_form = ""
        if h.can("accounting.edit"):
            new_form = h.card("Yangi hisob", h.form_page(
                "/accounts/new",
                h.input_field("code", "Kod *", required=True),
                h.input_field("name", "Nomi *", required=True),
                h.select_field("type", "Turi",
                               list(type_labels.items())),
                submit="Qo'shish"))

        content = (h.page_head("Hisoblar rejasi (NAS-21)") +
                   f'<div class="grid cols-2">'
                   f'{h.card("Hisoblar", h.data_table(["Kod", "Nomi", "Turi", "Qoldiq"], rows, num_cols=(3,)))}'
                   f"{new_form}</div>")
        return render(ctx, "Hisoblar rejasi", content, "/accounts")

    @app.post("/accounts/new")
    def account_new():
        if not h.can("accounting.edit"):
            abort(403)
        try:
            S.get("accounting").create_account(
                request.form.get("code", ""), request.form.get("name", ""),
                request.form.get("type", "expense"), g.user)
        except UzERPError as exc:
            return redirect(h.redirect_msg("/accounts", err=str(exc)))
        return redirect(h.redirect_msg("/accounts", msg="Hisob qo'shildi."))

    # ------------------------------------------------------------------ #
    #  Asosiy vositalar
    # ------------------------------------------------------------------ #

    @app.get("/assets")
    def assets_page():
        if not h.can("accounting.view"):
            abort(403)
        assets = S.get("assets")
        page = assets.list_assets(page=request.args.get("page", 1))
        rows = [[
            e(r["code"]), e(r["name"]), e(r["purchase_date"] or ""),
            h.m(r["cost"]), h.m(r["accumulated_depreciation"]),
            h.m(r["book_value"]), h.badge(r["status"]),
        ] for r in page.items]

        forms = ""
        if h.can("accounting.post"):
            current_period = today_str()[:7]
            forms = f"""
            <div class="grid cols-2">
            {h.card("Yangi asosiy vosita", h.form_page(
                "/assets/new",
                h.input_field("name", "Nomi *", required=True),
                h.input_field("cost", "Qiymati *", "", "number",
                              step="0.01", required=True),
                h.input_field("useful_life_months", "Foydali muddat (oy)",
                              "60", "number"),
                h.input_field("salvage_value", "Qoldiq qiymat", "0",
                              "number", step="0.01"),
                h.input_field("purchase_date", "Xarid sanasi",
                              today_str(), "date"),
                submit="Qo'shish"))}
            {h.card("Amortizatsiya hisoblash", h.form_page(
                "/assets/depreciation",
                h.input_field("period", "Davr (YYYY-MM)", current_period,
                              required=True),
                submit="Hisoblash (Dt 9410 / Kt 0200)"))}
            </div>"""

        content = (h.page_head("Asosiy vositalar") +
                   h.card("", h.data_table(
                       ["Kod", "Nomi", "Xarid sanasi", "Qiymat",
                        "Amortizatsiya", "Qoldiq qiymat", "Holat"], rows,
                       num_cols=(3, 4, 5))) +
                   h.pagination(page, "/assets", {}) +
                   f'<div class="mt">{forms}</div>')
        return render(ctx, "Asosiy vositalar", content, "/assets")

    @app.post("/assets/new")
    def asset_new():
        if not h.can("accounting.post"):
            abort(403)
        try:
            S.get("assets").create_asset(
                {k: request.form.get(k, "") for k in
                 ("name", "cost", "useful_life_months", "salvage_value",
                  "purchase_date")}, g.user)
        except UzERPError as exc:
            return redirect(h.redirect_msg("/assets", err=str(exc)))
        return redirect(h.redirect_msg("/assets", msg="Aktiv qo'shildi."))

    @app.post("/assets/depreciation")
    def asset_depreciation():
        if not h.can("accounting.post"):
            abort(403)
        try:
            result = S.get("assets").run_depreciation(
                request.form.get("period", ""), g.user)
        except UzERPError as exc:
            return redirect(h.redirect_msg("/assets", err=str(exc)))
        return redirect(h.redirect_msg(
            "/assets", msg=f"Amortizatsiya: {result['count']} ta aktiv, "
                           f"jami {money(result['total'])} so'm."))

    # ------------------------------------------------------------------ #
    #  Hisobotlar
    # ------------------------------------------------------------------ #

    _REPORT_TABS = [
        ("/reports", "Umumiy"),
        ("/reports/pl", "Foyda-zarar"),
        ("/reports/balance", "Balans"),
        ("/reports/trial", "Aylanma"),
        ("/reports/vat", "QQS"),
        ("/reports/cashflow", "Pul oqimi"),
        ("/reports/sales", "Savdo"),
    ]

    @app.get("/reports")
    def reports_index():
        if not h.can("reports.view"):
            abort(403)
        date_from, date_to = _month_range()
        tax = S.get("reports").tax_report(date_from, date_to)
        content = (h.page_head("Hisobotlar") +
                   h.tabs(_REPORT_TABS, "/reports") +
                   _period_form("/reports") +
                   f"""<div class="grid cols-3">
                   {h.stat_card("QQS (to'lanadigan)",
                                h.m(tax['vat']['payable']), "so'm")}
                   {h.stat_card("Ish haqi soliqlari",
                                h.m(tax['payroll_tax']), "so'm")}
                   {h.stat_card("Jami soliq yuki",
                                h.m(tax['total_tax']), "so'm", "amber")}
                   </div>""")
        return render(ctx, "Hisobotlar", content, "/reports")

    @app.get("/reports/pl")
    def report_pl():
        if not h.can("reports.view"):
            abort(403)
        date_from, date_to = _month_range()
        pl = S.get("accounting").profit_loss(date_from, date_to)
        income_rows = [[e(r["code"]), e(r["name"]), h.m(r["amount"])]
                       for r in pl["income"]]
        expense_rows = [[e(r["code"]), e(r["name"]), h.m(r["amount"])]
                        for r in pl["expenses"]]
        summary = f"""<div class="grid cols-3 mt">
        {h.stat_card("Jami daromad", h.m(pl['total_income']), "", "green")}
        {h.stat_card("Jami xarajat", h.m(pl['total_expense']), "", "red")}
        {h.stat_card("SOF FOYDA", h.m(pl['net_profit']), "",
                     "green" if pl['net_profit'] >= 0 else "red")}
        </div>"""
        content = (h.page_head("Foyda-zarar hisoboti",
                               _export_buttons("pl")) +
                   h.tabs(_REPORT_TABS, "/reports/pl") +
                   _period_form("/reports/pl") + summary +
                   f'<div class="grid cols-2 mt">'
                   f'{h.card("Daromadlar", h.data_table(["Kod", "Hisob", "Summa"], income_rows, num_cols=(2,)))}'
                   f'{h.card("Xarajatlar", h.data_table(["Kod", "Hisob", "Summa"], expense_rows, num_cols=(2,)))}'
                   "</div>")
        return render(ctx, "Foyda-zarar", content, "/reports")

    @app.get("/reports/balance")
    def report_balance():
        if not h.can("reports.view"):
            abort(403)
        _, date_to = _month_range()
        bs = S.get("accounting").balance_sheet(date_to)

        def _section(rows):
            return h.data_table(
                ["Kod", "Hisob", "Summa"],
                [[e(r["code"]), e(r["name"]), h.m(r["balance"])]
                 for r in rows], num_cols=(2,))

        check = ('<span class="badge green">Balans teng ✓</span>'
                 if bs["balanced"] else
                 '<span class="badge red">Balans buzilgan!</span>')
        content = (h.page_head(f"Balans ({bs['date_to']})",
                               _export_buttons("balance")) +
                   h.tabs(_REPORT_TABS, "/reports/balance") +
                   _period_form("/reports/balance") +
                   f"""<div class="grid cols-3">
                   {h.stat_card("AKTIV", h.m(bs['total_assets']))}
                   {h.stat_card("MAJBURIYAT", h.m(bs['total_liabilities']))}
                   {h.stat_card("KAPITAL", h.m(bs['total_equity']))}
                   </div><p class="mt">{check}</p>
                   <div class="grid cols-3 mt">
                   {h.card("Aktivlar", _section(bs['assets']))}
                   {h.card("Majburiyatlar", _section(bs['liabilities']))}
                   {h.card("Kapital", _section(bs['equity']))}
                   </div>""")
        return render(ctx, "Balans", content, "/reports")

    @app.get("/reports/trial")
    def report_trial():
        if not h.can("reports.view"):
            abort(403)
        _, date_to = _month_range()
        tb = S.get("accounting").trial_balance(date_to)
        rows = [[e(r["code"]), e(r["name"]), h.m(r["total_debit"]),
                 h.m(r["total_credit"]), h.m(r["balance"])]
                for r in tb if float(r["total_debit"] or 0)
                or float(r["total_credit"] or 0)]
        content = (h.page_head("Aylanma qaydnoma",
                               _export_buttons("trial")) +
                   h.tabs(_REPORT_TABS, "/reports/trial") +
                   _period_form("/reports/trial") +
                   h.card("", h.data_table(
                       ["Kod", "Hisob", "Debet aylanma", "Kredit aylanma",
                        "Qoldiq"], rows, num_cols=(2, 3, 4))))
        return render(ctx, "Aylanma", content, "/reports")

    @app.get("/reports/vat")
    def report_vat():
        if not h.can("reports.view"):
            abort(403)
        date_from, date_to = _month_range()
        vat = S.get("accounting").vat_report(date_from, date_to)
        content = (h.page_head("QQS hisoboti", _export_buttons("vat")) +
                   h.tabs(_REPORT_TABS, "/reports/vat") +
                   _period_form("/reports/vat") +
                   f"""<div class="grid cols-3">
                   {h.stat_card("Chiqim QQS (savdo)", h.m(vat['output_vat']))}
                   {h.stat_card("Kirim QQS (xarid)", h.m(vat['input_vat']))}
                   {h.stat_card("TO'LANADIGAN QQS", h.m(vat['payable']), "",
                                "amber")}
                   </div>
                   <p class="muted mt">Stavka: {e(vat['rate'])}% ·
                   Davr: {e(date_from)} — {e(date_to)}</p>""")
        return render(ctx, "QQS", content, "/reports")

    @app.get("/reports/cashflow")
    def report_cashflow():
        if not h.can("reports.view"):
            abort(403)
        date_from, date_to = _month_range()
        cf = S.get("payments").cash_flow(date_from, date_to)
        rows = [[h.badge(r["payment_type"]), e(r["method"]),
                 h.m(r["total"])] for r in cf["rows"]]
        content = (h.page_head("Pul oqimi", _export_buttons("cashflow")) +
                   h.tabs(_REPORT_TABS, "/reports/cashflow") +
                   _period_form("/reports/cashflow") +
                   f"""<div class="grid cols-3">
                   {h.stat_card("Kirim", h.m(cf['inflow']), "", "green")}
                   {h.stat_card("Chiqim", h.m(cf['outflow']), "", "red")}
                   {h.stat_card("Sof oqim", h.m(cf['net']))}
                   </div>""" +
                   h.card("Usul kesimida", h.data_table(
                       ["Turi", "Usul", "Summa"], rows, num_cols=(2,))))
        return render(ctx, "Pul oqimi", content, "/reports")

    @app.get("/reports/sales")
    def report_sales():
        if not h.can("reports.view"):
            abort(403)
        date_from, date_to = _month_range()
        sr = S.get("reports").sales_report(date_from, date_to)
        rows = [[e(r["period"]), e(r["docs"]), h.m(r["total"]),
                 h.m(r["vat"]), h.m(r["discount"])] for r in sr["rows"]]
        content = (h.page_head("Savdo hisoboti", _export_buttons("sales")) +
                   h.tabs(_REPORT_TABS, "/reports/sales") +
                   _period_form("/reports/sales") +
                   f"""<div class="grid cols-3">
                   {h.stat_card("Jami savdo", h.m(sr['total']), "", "green")}
                   {h.stat_card("Hujjatlar", str(sr['total_docs']))}
                   {h.stat_card("QQS", h.m(sr['total_vat']))}
                   </div>""" +
                   h.card("Kunlar kesimida", h.data_table(
                       ["Sana", "Hujjatlar", "Summa", "QQS", "Chegirma"],
                       rows, num_cols=(1, 2, 3, 4))))
        return render(ctx, "Savdo hisoboti", content, "/reports")

    # ------------------------------------------------------------------ #
    #  Eksport
    # ------------------------------------------------------------------ #

    @app.get("/reports/<report>/export/<fmt>")
    def report_export(report: str, fmt: str):
        if not h.can("reports.export"):
            abort(403)
        date_from, date_to = _month_range()
        try:
            title, headers, rows = _report_data(S, report, date_from, date_to)
            path = S.get("exporter").export_rows(
                fmt, f"{report}_hisoboti", title, headers, rows, g.user)
        except UzERPError as exc:
            return redirect(h.redirect_msg(f"/reports/{report}"
                                           if report != "sales" else
                                           "/reports/sales", err=str(exc)))
        return send_file(path, as_attachment=True,
                         download_name=path.name)


def _report_data(S, report: str, date_from: str, date_to: str):
    """Eksport uchun hisobot ma'lumotlarini jadval ko'rinishiga keltiradi."""
    accounting = S.get("accounting")
    if report == "pl":
        pl = accounting.profit_loss(date_from, date_to)
        rows = ([["DAROMADLAR", "", ""]] +
                [[r["code"], r["name"], r["amount"]] for r in pl["income"]] +
                [["XARAJATLAR", "", ""]] +
                [[r["code"], r["name"], r["amount"]] for r in pl["expenses"]] +
                [["", "SOF FOYDA", pl["net_profit"]]])
        return (f"Foyda-zarar {date_from} — {date_to}",
                ["Kod", "Nomi", "Summa"], rows)
    if report == "balance":
        bs = accounting.balance_sheet(date_to)
        rows = ([["AKTIVLAR", "", ""]] +
                [[r["code"], r["name"], r["balance"]] for r in bs["assets"]] +
                [["MAJBURIYATLAR", "", ""]] +
                [[r["code"], r["name"], r["balance"]]
                 for r in bs["liabilities"]] +
                [["KAPITAL", "", ""]] +
                [[r["code"], r["name"], r["balance"]] for r in bs["equity"]])
        return (f"Balans {bs['date_to']}", ["Kod", "Nomi", "Summa"], rows)
    if report == "trial":
        tb = accounting.trial_balance(date_to)
        rows = [[r["code"], r["name"], r["total_debit"], r["total_credit"],
                 r["balance"]] for r in tb]
        return (f"Aylanma qaydnoma {date_to}",
                ["Kod", "Nomi", "Debet", "Kredit", "Qoldiq"], rows)
    if report == "vat":
        vat = accounting.vat_report(date_from, date_to)
        rows = [["Chiqim QQS", vat["output_vat"]],
                ["Kirim QQS", vat["input_vat"]],
                ["To'lanadigan", vat["payable"]]]
        return (f"QQS {date_from} — {date_to}",
                ["Ko'rsatkich", "Summa"], rows)
    if report == "cashflow":
        cf = S.get("payments").cash_flow(date_from, date_to)
        rows = [[r["payment_type"], r["method"], r["total"]]
                for r in cf["rows"]]
        rows += [["JAMI KIRIM", "", cf["inflow"]],
                 ["JAMI CHIQIM", "", cf["outflow"]]]
        return (f"Pul oqimi {date_from} — {date_to}",
                ["Turi", "Usul", "Summa"], rows)
    # default: sales
    sr = S.get("reports").sales_report(date_from, date_to)
    rows = [[r["period"], r["docs"], r["total"], r["vat"], r["discount"]]
            for r in sr["rows"]]
    return (f"Savdo hisoboti {date_from} — {date_to}",
            ["Sana", "Hujjatlar", "Summa", "QQS", "Chegirma"], rows)
