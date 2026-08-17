from datetime import date
from typing import Annotated

from fastapi import APIRouter, Depends, Response

from app.api.deps import CurrentUser, get_category_repository, get_transaction_repository
from app.repositories.category_repository import CategoryRepository
from app.repositories.transaction_repository import TransactionRepository
from app.schemas.report import ReportSummary
from app.services.report_export import build_excel, build_pdf
from app.services.report_service import ReportService

router = APIRouter(prefix="/reports", tags=["reports"])


def get_service(
    txn_repo: Annotated[TransactionRepository, Depends(get_transaction_repository)],
    category_repo: Annotated[CategoryRepository, Depends(get_category_repository)],
) -> ReportService:
    return ReportService(txn_repo, category_repo)


def _default_dates(start_date: date | None, end_date: date | None) -> tuple[date, date]:
    resolved_end = end_date or date.today()
    resolved_start = start_date or resolved_end.replace(day=1)
    return resolved_start, resolved_end


@router.get("/summary", response_model=ReportSummary)
async def get_summary(
    current_user: CurrentUser,
    service: Annotated[ReportService, Depends(get_service)],
    start_date: date | None = None,
    end_date: date | None = None,
):
    resolved_start, resolved_end = _default_dates(start_date, end_date)
    return await service.get_summary(current_user.id, resolved_start, resolved_end)


@router.get("/export.pdf")
async def export_pdf(
    current_user: CurrentUser,
    service: Annotated[ReportService, Depends(get_service)],
    start_date: date | None = None,
    end_date: date | None = None,
):
    resolved_start, resolved_end = _default_dates(start_date, end_date)
    summary = await service.get_summary(current_user.id, resolved_start, resolved_end)
    pdf_bytes = build_pdf(summary)
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="hisobot_{resolved_start}_{resolved_end}.pdf"'},
    )


@router.get("/export.xlsx")
async def export_excel(
    current_user: CurrentUser,
    service: Annotated[ReportService, Depends(get_service)],
    start_date: date | None = None,
    end_date: date | None = None,
):
    resolved_start, resolved_end = _default_dates(start_date, end_date)
    summary = await service.get_summary(current_user.id, resolved_start, resolved_end)
    excel_bytes = build_excel(summary)
    return Response(
        content=excel_bytes,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": f'attachment; filename="hisobot_{resolved_start}_{resolved_end}.xlsx"'},
    )
