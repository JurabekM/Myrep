"""Shared ReportLab styling helpers for every generated PDF."""

from __future__ import annotations

from pathlib import Path

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_LEFT
from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.pdfgen.canvas import Canvas
from reportlab.platypus import Image, SimpleDocTemplate, Table, TableStyle

BRAND = colors.HexColor("#1D4ED8")
BRAND_LIGHT = colors.HexColor("#DBEAFE")
INK = colors.HexColor("#111827")
MUTED = colors.HexColor("#6B7280")
LINE = colors.HexColor("#D1D5DB")
ZEBRA = colors.HexColor("#F3F4F6")

PAGE_MARGIN = 16 * mm


def styles() -> dict[str, ParagraphStyle]:
    """Return the named paragraph styles used across all reports."""
    base = getSampleStyleSheet()
    return {
        "title": ParagraphStyle(
            "EFTitle", parent=base["Title"], fontSize=22, textColor=BRAND, spaceAfter=6
        ),
        "subtitle": ParagraphStyle(
            "EFSubtitle", parent=base["Normal"], fontSize=11, textColor=MUTED, spaceAfter=10
        ),
        "h1": ParagraphStyle(
            "EFH1",
            parent=base["Heading1"],
            fontSize=15,
            textColor=INK,
            spaceBefore=10,
            spaceAfter=6,
        ),
        "h2": ParagraphStyle(
            "EFH2",
            parent=base["Heading2"],
            fontSize=12,
            textColor=BRAND,
            spaceBefore=8,
            spaceAfter=4,
        ),
        "body": ParagraphStyle(
            "EFBody", parent=base["Normal"], fontSize=9.5, leading=13, textColor=INK
        ),
        "small": ParagraphStyle("EFSmall", parent=base["Normal"], fontSize=8, textColor=MUTED),
        "cell": ParagraphStyle("EFCell", parent=base["Normal"], fontSize=8.5, leading=11),
        "cell_bold": ParagraphStyle(
            "EFCellBold", parent=base["Normal"], fontSize=8.5, leading=11, fontName="Helvetica-Bold"
        ),
        "center": ParagraphStyle(
            "EFCenter", parent=base["Normal"], fontSize=9, alignment=TA_CENTER
        ),
        "left": ParagraphStyle("EFLeft", parent=base["Normal"], fontSize=9, alignment=TA_LEFT),
    }


def table_style(header: bool = True, zebra: bool = True) -> TableStyle:
    """Standard grid style for data tables."""
    commands = [
        ("GRID", (0, 0), (-1, -1), 0.4, LINE),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("FONTSIZE", (0, 0), (-1, -1), 8.5),
        ("TOPPADDING", (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
        ("LEFTPADDING", (0, 0), (-1, -1), 5),
        ("RIGHTPADDING", (0, 0), (-1, -1), 5),
    ]
    if header:
        commands += [
            ("BACKGROUND", (0, 0), (-1, 0), BRAND),
            ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
            ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ]
    if zebra:
        commands.append(("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, ZEBRA]))
    return TableStyle(commands)


def make_document(path: str | Path, title: str, landscape_mode: bool = False) -> SimpleDocTemplate:
    """Create a configured ``SimpleDocTemplate``."""
    page = landscape(A4) if landscape_mode else A4
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    return SimpleDocTemplate(
        str(path),
        pagesize=page,
        leftMargin=PAGE_MARGIN,
        rightMargin=PAGE_MARGIN,
        topMargin=PAGE_MARGIN,
        bottomMargin=18 * mm,
        title=title,
        author="ExportFlow",
    )


def footer_factory(company_name: str, footer_note: str = ""):
    """Return a page callback drawing the footer and page number."""

    def _draw(canvas: Canvas, doc) -> None:
        canvas.saveState()
        canvas.setStrokeColor(LINE)
        canvas.setLineWidth(0.4)
        canvas.line(PAGE_MARGIN, 13 * mm, doc.pagesize[0] - PAGE_MARGIN, 13 * mm)
        canvas.setFont("Helvetica", 7.5)
        canvas.setFillColor(MUTED)
        canvas.drawString(PAGE_MARGIN, 9 * mm, f"{company_name} {footer_note}".strip())
        canvas.drawRightString(doc.pagesize[0] - PAGE_MARGIN, 9 * mm, f"Page {doc.page}")
        canvas.restoreState()

    return _draw


def logo_flowable(logo_path: str | None, max_width: float = 45 * mm, max_height: float = 20 * mm):
    """Return an ``Image`` flowable for the company logo, or ``None``."""
    if not logo_path:
        return None
    path = Path(logo_path)
    if not path.exists():
        return None
    try:
        from reportlab.lib.utils import ImageReader

        reader = ImageReader(str(path))
        width, height = reader.getSize()
        scale = min(max_width / width, max_height / height)
        return Image(str(path), width=width * scale, height=height * scale)
    except Exception:  # pragma: no cover - unreadable image
        return None


def kv_table(rows: list[tuple[str, str]], width: float = 90 * mm) -> Table:
    """Two-column key/value block used in document headers."""
    table = Table([[key, value] for key, value in rows], colWidths=[width * 0.42, width * 0.58])
    table.setStyle(
        TableStyle(
            [
                ("FONTSIZE", (0, 0), (-1, -1), 8.5),
                ("TEXTCOLOR", (0, 0), (0, -1), MUTED),
                ("FONTNAME", (1, 0), (1, -1), "Helvetica-Bold"),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 2),
                ("TOPPADDING", (0, 0), (-1, -1), 2),
                ("LEFTPADDING", (0, 0), (-1, -1), 0),
            ]
        )
    )
    return table
