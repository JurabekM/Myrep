"""Stage delay detection and report generation."""

from __future__ import annotations

from datetime import date, timedelta

from app.models.enums import StageStatus
from app.reports import excel_reports, pdf_reports
from app.services import estimate_service, project_service, report_service, stage_service


def _project(actor) -> int:
    return project_service.save_project(
        {"name": "Jadval loyihasi", "planned_budget": 20_000_000, "status": "active"}, actor
    )


def test_overdue_stage_becomes_delayed(admin) -> None:
    project_id = _project(admin)
    stage_service.save_stage(
        {
            "project_id": project_id,
            "name": "Kechikkan bosqich",
            "plan_start": date.today() - timedelta(days=20),
            "plan_end": date.today() - timedelta(days=2),
            "progress_percent": 40,
            "status": StageStatus.IN_PROGRESS.value,
        },
        admin,
    )
    rows = stage_service.list_stages(project_id)
    assert rows[0]["status"] == StageStatus.DELAYED.value
    delayed = stage_service.delayed_stages(project_id)
    assert delayed and delayed[0]["overdue_days"] == 2


def test_completed_stage_is_not_marked_delayed(admin) -> None:
    project_id = _project(admin)
    stage_service.save_stage(
        {
            "project_id": project_id,
            "name": "Yakunlangan",
            "plan_start": date.today() - timedelta(days=30),
            "plan_end": date.today() - timedelta(days=10),
            "progress_percent": 100,
            "status": StageStatus.DONE.value,
        },
        admin,
    )
    assert stage_service.list_stages(project_id)[0]["status"] == StageStatus.DONE.value


def test_site_log_pushes_stage_progress(admin) -> None:
    project_id = _project(admin)
    stage_id = stage_service.save_stage(
        {
            "project_id": project_id,
            "name": "Montaj",
            "plan_start": date.today(),
            "plan_end": date.today() + timedelta(days=10),
            "progress_percent": 10,
            "status": StageStatus.IN_PROGRESS.value,
        },
        admin,
    )
    stage_service.save_log(
        {
            "project_id": project_id,
            "stage_id": stage_id,
            "work_done": "Karkas yig'ildi",
            "progress_percent": 55,
            "workers_count": 8,
        },
        admin,
    )
    assert stage_service.list_stages(project_id)[0]["progress_percent"] == 55


def test_reports_build_and_export(admin, tmp_path) -> None:
    project_id = _project(admin)
    version_id = estimate_service.list_versions(project_id)[0]["id"]
    section_id = estimate_service.add_section(version_id, "Beton", admin)
    estimate_service.save_item(
        {
            "section_id": section_id,
            "name": "Beton quyish",
            "quantity": 5,
            "plan_unit_price": 700_000,
        },
        admin,
    )
    filters = report_service.ReportFilters(project_id=project_id)

    for key, _title, _needs in report_service.REPORT_TYPES:
        data = report_service.build(key, filters)
        assert data.title

    data = report_service.build("estimate", filters)
    xlsx = excel_reports.render_report(data, tmp_path / "estimate.xlsx")
    pdf = pdf_reports.render_report(data, tmp_path / "estimate.pdf")
    assert xlsx.exists() and xlsx.stat().st_size > 0
    assert pdf.exists() and pdf.stat().st_size > 0


def test_excel_estimate_roundtrip(admin, tmp_path) -> None:
    template = excel_reports.estimate_template(tmp_path / "template.xlsx")
    rows = excel_reports.read_estimate_rows(template)
    assert rows and rows[0]["name"] == "Demontaj"

    project_id = _project(admin)
    version_id = estimate_service.list_versions(project_id)[0]["id"]
    imported = estimate_service.bulk_import(version_id, rows, admin)
    assert imported == 1
    tree = estimate_service.load_tree(project_id)
    assert tree.plan_total == 3_500_000
