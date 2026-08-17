# -*- coding: utf-8 -*-
"""HR sahifalari: xodimlar, davomat, ta'tillar, ish haqi."""
from __future__ import annotations

from flask import abort, g, redirect, request

from src.core.errors import UzERPError
from src.core.security import escape_html as e
from src.core.utils import money, today_str
from src.web import helpers as h


def register(app, ctx) -> None:
    """HR marshrutlari."""
    from src.web.server import render
    S = ctx.services

    def _department_options():
        return [(d["id"], d["name"]) for d in S.get("hr").departments()]

    def _employee_options():
        rows = ctx.db.query("SELECT id, full_name FROM employees "
                            "WHERE status = 'active' ORDER BY full_name")
        return [(r["id"], r["full_name"]) for r in rows]

    # ------------------------------------------------------------------ #
    #  Xodimlar
    # ------------------------------------------------------------------ #

    @app.get("/hr")
    def hr_employees():
        if not h.can("hr.view"):
            abort(403)
        hr = S.get("hr")
        page = hr.list_employees(page=request.args.get("page", 1),
                                 search=request.args.get("q") or None,
                                 status=request.args.get("status") or "active")
        rows = [[
            e(r["code"] or ""), e(r["full_name"]), e(r["position"] or ""),
            e(r["phone"] or ""), h.m(r["salary"]), h.badge(r["status"]),
            h.btn_link(f"/hr/{r['id']}/edit", "Tahrirlash", "small")
            if h.can("hr.edit") else "",
        ] for r in page.items]

        new_form = ""
        if h.can("hr.create"):
            new_form = h.card("Yangi xodim", h.form_page(
                "/hr/new",
                h.input_field("full_name", "F.I.Sh. *", required=True),
                h.select_field("department_id", "Bo'lim",
                               _department_options(), empty="—"),
                h.input_field("position", "Lavozim"),
                h.input_field("salary", "Oylik maosh", "0", "number",
                              step="0.01"),
                h.input_field("phone", "Telefon"),
                h.input_field("hire_date", "Ishga olingan sana",
                              today_str(), "date"),
                submit="Qo'shish") + "<hr class='sep'>" + h.form_page(
                "/hr/department",
                h.input_field("name", "Yangi bo'lim nomi", required=True),
                submit="Bo'lim qo'shish"))

        content = (h.page_head("Xodimlar") +
                   f'<div class="grid cols-2">'
                   f'{h.card("Ro`yxat", h.data_table(["Kod", "F.I.Sh.", "Lavozim", "Telefon", "Maosh", "Holat", ""], rows, num_cols=(4,)))}'
                   f"{new_form}</div>" +
                   h.pagination(page, "/hr", {}))
        return render(ctx, "Xodimlar", content, "/hr")

    @app.post("/hr/new")
    def hr_employee_new():
        if not h.can("hr.create"):
            abort(403)
        f = request.form
        try:
            S.get("hr").create_employee({
                "full_name": f.get("full_name", ""),
                "department_id": int(f["department_id"])
                if f.get("department_id") else None,
                "position": f.get("position", ""),
                "salary": f.get("salary", 0),
                "phone": f.get("phone", ""),
                "hire_date": f.get("hire_date") or None,
            }, g.user)
        except UzERPError as exc:
            return redirect(h.redirect_msg("/hr", err=str(exc)))
        return redirect(h.redirect_msg("/hr", msg="Xodim qo'shildi."))

    @app.post("/hr/department")
    def hr_department_new():
        if not h.can("hr.create"):
            abort(403)
        try:
            S.get("hr").create_department(request.form.get("name", ""),
                                          user=g.user)
        except UzERPError as exc:
            return redirect(h.redirect_msg("/hr", err=str(exc)))
        return redirect(h.redirect_msg("/hr", msg="Bo'lim qo'shildi."))

    @app.get("/hr/<int:employee_id>/edit")
    def hr_employee_edit(employee_id: int):
        if not h.can("hr.edit"):
            abort(403)
        try:
            emp = S.get("hr").get_employee(employee_id)
        except UzERPError:
            abort(404)
        terminate = (h.action_form(f"/hr/{employee_id}/terminate",
                                   "Ishdan bo'shatish", "danger")
                     if emp["status"] == "active" and h.can("hr.delete")
                     else "")
        content = (h.page_head(f"Xodim: {emp['full_name']}", terminate) +
                   h.card("", h.form_page(
                       f"/hr/{employee_id}/edit",
                       h.input_field("full_name", "F.I.Sh. *",
                                     emp["full_name"], required=True),
                       h.select_field("department_id", "Bo'lim",
                                      _department_options(),
                                      emp.get("department_id"), empty="—"),
                       h.input_field("position", "Lavozim",
                                     emp["position"] or ""),
                       h.input_field("salary", "Oylik maosh", emp["salary"],
                                     "number", step="0.01"),
                       h.input_field("phone", "Telefon", emp["phone"] or ""),
                       h.select_field("status", "Holat",
                                      [("active", "Faol"),
                                       ("leave", "Ta'tilda"),
                                       ("terminated", "Bo'shatilgan")],
                                      emp["status"]),
                       cancel_url="/hr")))
        return render(ctx, emp["full_name"], content, "/hr")

    @app.post("/hr/<int:employee_id>/edit")
    def hr_employee_edit_submit(employee_id: int):
        if not h.can("hr.edit"):
            abort(403)
        f = request.form
        try:
            S.get("hr").update_employee(employee_id, {
                "full_name": f.get("full_name", ""),
                "department_id": int(f["department_id"])
                if f.get("department_id") else None,
                "position": f.get("position", ""),
                "salary": f.get("salary", 0),
                "phone": f.get("phone", ""),
                "status": f.get("status", "active"),
            }, g.user)
        except UzERPError as exc:
            return redirect(h.redirect_msg(f"/hr/{employee_id}/edit",
                                           err=str(exc)))
        return redirect(h.redirect_msg("/hr", msg="Saqlandi."))

    @app.post("/hr/<int:employee_id>/terminate")
    def hr_employee_terminate(employee_id: int):
        if not h.can("hr.delete"):
            abort(403)
        S.get("hr").terminate(employee_id, g.user)
        return redirect(h.redirect_msg("/hr", msg="Xodim bo'shatildi."))

    # ------------------------------------------------------------------ #
    #  Davomat
    # ------------------------------------------------------------------ #

    @app.get("/attendance")
    def attendance_page():
        if not h.can("hr.view"):
            abort(403)
        hr = S.get("hr")
        today = today_str()
        year = int(request.args.get("y", today[:4]))
        month = int(request.args.get("m", today[5:7]))
        sheet = hr.attendance_sheet(year, month)
        rows = [[
            e(r["code"] or ""), e(r["full_name"]),
            e(r["days_present"]), e(r["days_late"]), e(r["days_absent"]),
            e(r["days_leave"]), e(r["total_hours"]),
        ] for r in sheet]

        mark_form = ""
        if h.can("hr.edit"):
            mark_form = h.card("Davomat belgilash", h.form_page(
                "/attendance/mark",
                h.select_field("employee_id", "Xodim", _employee_options()),
                h.input_field("work_date", "Sana", today, "date"),
                h.select_field("status", "Holat",
                               [("present", "Keldi"), ("late", "Kechikdi"),
                                ("absent", "Kelmadi"), ("leave", "Ta'til"),
                                ("holiday", "Bayram")]),
                h.input_field("check_in", "Kelish (HH:MM)", "09:00"),
                h.input_field("check_out", "Ketish (HH:MM)", "18:00"),
                submit="Belgilash") + "<hr class='sep'>" + h.form_page(
                "/attendance/bulk",
                h.input_field("work_date", "Sana", today, "date"),
                submit="Hammani 'keldi' deb belgilash"))

        nav = f"""
        <form method="get" action="/attendance" class="card"
              style="display:flex;gap:10px;align-items:flex-end">
          {h.input_field("y", "Yil", year, "number")}
          {h.input_field("m", "Oy", month, "number")}
          <button class="btn primary" type="submit">Ko'rsatish</button>
        </form>"""

        content = (h.page_head(f"Davomat — {year}-{month:02d}") + nav +
                   f'<div class="grid cols-2">'
                   f'{h.card("Oylik jadval", h.data_table(["Kod", "Xodim", "Keldi", "Kechikdi", "Kelmadi", "Ta`til", "Soat"], rows, num_cols=(2, 3, 4, 5, 6)))}'
                   f"{mark_form}</div>")
        return render(ctx, "Davomat", content, "/attendance")

    @app.post("/attendance/mark")
    def attendance_mark():
        if not h.can("hr.edit"):
            abort(403)
        f = request.form
        try:
            S.get("hr").mark_attendance(
                int(f["employee_id"]), f.get("work_date") or None,
                f.get("status", "present"), f.get("check_in", ""),
                f.get("check_out", ""), user=g.user)
        except (UzERPError, ValueError, KeyError) as exc:
            return redirect(h.redirect_msg("/attendance", err=str(exc)))
        return redirect(h.redirect_msg("/attendance", msg="Belgilandi."))

    @app.post("/attendance/bulk")
    def attendance_bulk():
        if not h.can("hr.edit"):
            abort(403)
        marked = S.get("hr").bulk_mark(
            request.form.get("work_date") or None, "present", g.user)
        return redirect(h.redirect_msg(
            "/attendance", msg=f"{marked} ta xodim belgilandi."))

    # ------------------------------------------------------------------ #
    #  Ta'tillar
    # ------------------------------------------------------------------ #

    @app.get("/leaves")
    def leaves_page():
        if not h.can("hr.view"):
            abort(403)
        page = S.get("hr").list_leaves(page=request.args.get("page", 1),
                                       status=request.args.get("status")
                                       or None)
        rows = []
        for r in page.items:
            decide = ""
            if r["status"] == "pending" and h.can("hr.edit"):
                decide = (h.action_form(f"/leaves/{r['id']}/approve",
                                        "Tasdiqlash", "success") + " " +
                          h.action_form(f"/leaves/{r['id']}/reject",
                                        "Rad etish", "danger"))
            type_labels = {"annual": "Yillik", "sick": "Kasallik",
                           "unpaid": "Ish haqisiz", "maternity": "Dekret",
                           "other": "Boshqa"}
            rows.append([
                e(r["full_name"]),
                e(type_labels.get(r["leave_type"], r["leave_type"])),
                f'{e(r["date_from"])} — {e(r["date_to"])}',
                e(r["days"]), h.badge(r["status"]), decide,
            ])

        new_form = ""
        if h.can("hr.edit"):
            new_form = h.card("Yangi ta'til so'rovi", h.form_page(
                "/leaves/new",
                h.select_field("employee_id", "Xodim", _employee_options()),
                h.select_field("leave_type", "Turi",
                               [("annual", "Yillik"), ("sick", "Kasallik"),
                                ("unpaid", "Ish haqisiz"),
                                ("maternity", "Dekret"),
                                ("other", "Boshqa")]),
                h.input_field("date_from", "Boshlanish", "", "date",
                              required=True),
                h.input_field("date_to", "Tugash", "", "date",
                              required=True),
                submit="So'rov yaratish"))

        content = (h.page_head("Ta'tillar") +
                   f'<div class="grid cols-2">'
                   f'{h.card("So`rovlar", h.data_table(["Xodim", "Turi", "Davr", "Kun", "Holat", ""], rows, num_cols=(3,)))}'
                   f"{new_form}</div>" +
                   h.pagination(page, "/leaves", {}))
        return render(ctx, "Ta'tillar", content, "/leaves")

    @app.post("/leaves/new")
    def leave_new():
        if not h.can("hr.edit"):
            abort(403)
        f = request.form
        try:
            S.get("hr").request_leave(
                int(f["employee_id"]), f.get("leave_type", "annual"),
                f.get("date_from", ""), f.get("date_to", ""), user=g.user)
        except (UzERPError, ValueError, KeyError) as exc:
            return redirect(h.redirect_msg("/leaves", err=str(exc)))
        return redirect(h.redirect_msg("/leaves", msg="So'rov yaratildi."))

    @app.post("/leaves/<int:leave_id>/approve")
    def leave_approve(leave_id: int):
        if not h.can("hr.edit"):
            abort(403)
        try:
            S.get("hr").decide_leave(leave_id, True, g.user)
        except UzERPError as exc:
            return redirect(h.redirect_msg("/leaves", err=str(exc)))
        return redirect(h.redirect_msg("/leaves", msg="Tasdiqlandi."))

    @app.post("/leaves/<int:leave_id>/reject")
    def leave_reject(leave_id: int):
        if not h.can("hr.edit"):
            abort(403)
        try:
            S.get("hr").decide_leave(leave_id, False, g.user)
        except UzERPError as exc:
            return redirect(h.redirect_msg("/leaves", err=str(exc)))
        return redirect(h.redirect_msg("/leaves", msg="Rad etildi."))

    # ------------------------------------------------------------------ #
    #  Ish haqi
    # ------------------------------------------------------------------ #

    @app.get("/payroll")
    def payroll_page():
        if not h.can("payroll.view"):
            abort(403)
        page = S.get("payroll").list_runs(page=request.args.get("page", 1))
        rows = [[
            h.link(f"/payroll/{r['id']}", r["period"]),
            h.badge(r["status"]), h.m(r["total_gross"]),
            h.m(r["total_tax"]), h.m(r["total_net"]),
        ] for r in page.items]

        new_form = ""
        if h.can("payroll.create"):
            new_form = h.card("Yangi vedomost", h.form_page(
                "/payroll/new",
                h.input_field("period", "Davr (YYYY-MM)",
                              today_str()[:7], required=True),
                submit="Hisoblash"))

        content = (h.page_head("Ish haqi vedomostlari") +
                   f'<div class="grid cols-2">'
                   f'{h.card("Ro`yxat", h.data_table(["Davr", "Holat", "Yalpi", "Soliqlar", "Sof"], rows, num_cols=(2, 3, 4)))}'
                   f"{new_form}</div>" +
                   h.pagination(page, "/payroll", {}))
        return render(ctx, "Ish haqi", content, "/payroll")

    @app.post("/payroll/new")
    def payroll_new():
        if not h.can("payroll.create"):
            abort(403)
        try:
            run_id = S.get("payroll").create_run(
                request.form.get("period", ""), g.user)
        except UzERPError as exc:
            return redirect(h.redirect_msg("/payroll", err=str(exc)))
        return redirect(h.redirect_msg(f"/payroll/{run_id}",
                                       msg="Vedomost hisoblandi."))

    @app.get("/payroll/<int:run_id>")
    def payroll_detail(run_id: int):
        if not h.can("payroll.view"):
            abort(403)
        try:
            data = S.get("payroll").get_run(run_id)
        except UzERPError:
            abort(404)
        run, items = data["run"], data["items"]
        rows = [[
            e(i["code"] or ""), e(i["full_name"]), e(i["position"] or ""),
            h.m(i["gross"]), h.m(i["income_tax"]), h.m(i["pension"]),
            h.m(i["other_deductions"]), h.m(i["net"]),
        ] for i in items]

        actions = []
        if run["status"] == "draft" and h.can("payroll.approve"):
            actions.append(h.action_form(f"/payroll/{run_id}/approve",
                                         "Tasdiqlash", "success"))
        if run["status"] == "approved" and h.can("cash.operate"):
            actions.append(h.action_form(f"/payroll/{run_id}/pay",
                                         "To'lash (bank)", "primary",
                                         hidden={"method": "bank"}))
            actions.append(h.action_form(f"/payroll/{run_id}/pay",
                                         "To'lash (kassa)", "",
                                         hidden={"method": "cash"}))

        summary = f"""<div class="grid cols-3">
        {h.stat_card("Yalpi (gross)", h.m(run['total_gross']))}
        {h.stat_card("Soliq + INPS", h.m(run['total_tax']), "", "amber")}
        {h.stat_card("Sof (net)", h.m(run['total_net']), "", "green")}
        </div>"""
        content = (h.page_head(f"Vedomost {run['period']}",
                               h.btn_link("/payroll", "← Ro'yxat"),
                               *actions) + summary +
                   h.card(f"Holat: {run['status']}", h.data_table(
                       ["Kod", "Xodim", "Lavozim", "Yalpi", "Soliq", "INPS",
                        "Ushlanma", "Sof"], rows,
                       num_cols=(3, 4, 5, 6, 7))))
        return render(ctx, f"Vedomost {run['period']}", content, "/payroll")

    @app.post("/payroll/<int:run_id>/approve")
    def payroll_approve(run_id: int):
        if not h.can("payroll.approve"):
            abort(403)
        try:
            S.get("payroll").approve(run_id, g.user)
        except UzERPError as exc:
            return redirect(h.redirect_msg(f"/payroll/{run_id}",
                                           err=str(exc)))
        return redirect(h.redirect_msg(f"/payroll/{run_id}",
                                       msg="Vedomost tasdiqlandi."))

    @app.post("/payroll/<int:run_id>/pay")
    def payroll_pay(run_id: int):
        if not h.can("cash.operate"):
            abort(403)
        try:
            S.get("payroll").pay(run_id,
                                 request.form.get("method", "bank"), g.user)
        except UzERPError as exc:
            return redirect(h.redirect_msg(f"/payroll/{run_id}",
                                           err=str(exc)))
        return redirect(h.redirect_msg(f"/payroll/{run_id}",
                                       msg="Ish haqi to'landi."))
