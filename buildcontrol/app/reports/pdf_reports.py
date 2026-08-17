"""PDF rendering built on ReportLab."""

from __future__ import annotations

from datetime import datetime
from pathlib import Path

from reportlab.lib import colors
from reportlab.lib.enums import TA_RIGHT
from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import (
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)

from app.config import REPORTS_DIR
from app.services import purchase_service, settings_service
from app.services.report_service import DATE, MONEY, NUMBER, PERCENT, ReportData
from app.utils.formatting import fmt_date, fmt_money, fmt_percent, fmt_qty
from app.utils.i18n import tr

#: Candidate Unicode fonts shipped with Windows.
_FONT_CANDIDATES = [
    ("BC-Sans", r"C:\Windows\Fonts\segoeui.ttf"),
    ("BC-Sans", r"C:\Windows\Fonts\arial.ttf"),
    ("BC-Sans", "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"),
]
_BOLD_CANDIDATES = [
    ("BC-Sans-Bold", r"C:\Windows\Fonts\segoeuib.ttf"),
    ("BC-Sans-Bold", r"C:\Windows\Fonts\arialbd.ttf"),
    ("BC-Sans-Bold", "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"),
]

FONT = "Helvetica"
FONT_BOLD = "Helvetica-Bold"


def _register_fonts() -> None:
    """Register a Unicode capable font when one is available."""
    global FONT, FONT_BOLD
    for name, path in _FONT_CANDIDATES:
        if Path(path).is_file():
            try:
                pdfmetrics.registerFont(TTFont(name, path))
                FONT = name
                break
            except Exception:  # pragma: no cover - broken font file
                continue
    for name, path in _BOLD_CANDIDATES:
        if Path(path).is_file():
            try:
                pdfmetrics.registerFont(TTFont(name, path))
                FONT_BOLD = name
                break
            except Exception:  # pragma: no cover
                continue


_register_fonts()

# Print palette (light, ink friendly) -------------------------------------- #
INK = colors.HexColor("#111827")
MUTED = colors.HexColor("#64748B")
ACCENT = colors.HexColor("#1D4ED8")
HEAD_BG = colors.HexColor("#E8EDF6")
ROW_BG = colors.HexColor("#F6F8FC")
LINE = colors.HexColor("#C7D2E1")
RED = colors.HexColor("#B91C1C")


def _styles() -> dict:
    base = getSampleStyleSheet()
    return {
        "title": ParagraphStyle(
            "BCTitle", parent=base["Title"], fontName=FONT_BOLD, fontSize=16, textColor=INK
        ),
        "subtitle": ParagraphStyle(
            "BCSub", parent=base["Normal"], fontName=FONT, fontSize=9.5, textColor=MUTED
        ),
        "cell": ParagraphStyle(
            "BCCell", parent=base["Normal"], fontName=FONT, fontSize=8, leading=10
        ),
        "cell_bold": ParagraphStyle(
            "BCCellB", parent=base["Normal"], fontName=FONT_BOLD, fontSize=8, leading=10
        ),
        "right": ParagraphStyle(
            "BCRight", parent=base["Normal"], fontName=FONT, fontSize=9, alignment=TA_RIGHT
        ),
    }


def _cell_text(row: dict, column) -> str:
    value = row.get(column.key)
    if value in (None, ""):
        return ""
    if column.kind == MONEY:
        return fmt_money(float(value), with_suffix=False)
    if column.kind == NUMBER:
        return fmt_qty(float(value))
    if column.kind == PERCENT:
        return fmt_percent(float(value), 1)
    if column.kind == DATE:
        return fmt_date(value)
    return str(value)


def _output_path(name: str, extension: str = "pdf") -> Path:
    REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    return REPORTS_DIR / f"{name}_{stamp}.{extension}"


def render_report(data: ReportData, path: str | Path | None = None) -> Path:
    """Render a :class:`ReportData` table into a landscape A4 PDF."""
    target = Path(path) if path else _output_path(data.key)
    company = settings_service.get_company()
    styles = _styles()

    doc = SimpleDocTemplate(
        str(target),
        pagesize=landscape(A4),
        leftMargin=12 * mm,
        rightMargin=12 * mm,
        topMargin=12 * mm,
        bottomMargin=12 * mm,
        title=data.title,
        author=company.get("name", "BuildControl"),
    )
    story = [
        Paragraph(company.get("name", "BuildControl"), styles["subtitle"]),
        Paragraph(data.title, styles["title"]),
    ]
    meta = " · ".join(
        part
        for part in (
            data.subtitle,
            f"{tr('date')}: {fmt_date(datetime.now())}",
            company.get("address", ""),
        )
        if part
    )
    story.append(Paragraph(meta, styles["subtitle"]))
    story.append(Spacer(1, 6 * mm))

    header = [Paragraph(c.title, styles["cell_bold"]) for c in data.columns]
    body = [header]
    for row in data.rows:
        cells = []
        for column in data.columns:
            style = styles["cell_bold"] if row.get("_group") else styles["cell"]
            cells.append(Paragraph(_cell_text(row, column).replace("\n", "<br/>"), style))
        body.append(cells)

    if data.totals:
        totals_row = []
        for index, column in enumerate(data.columns):
            if index == 0:
                totals_row.append(Paragraph(tr("total"), styles["cell_bold"]))
            elif column.key in data.totals:
                totals_row.append(
                    Paragraph(
                        fmt_money(float(data.totals[column.key]), with_suffix=False),
                        styles["cell_bold"],
                    )
                )
            else:
                totals_row.append(Paragraph("", styles["cell"]))
        body.append(totals_row)

    available = doc.width
    weights = [c.width or 1.0 for c in data.columns]
    total_weight = sum(weights) or 1.0
    widths = [available * w / total_weight for w in weights]

    table = Table(body, colWidths=widths, repeatRows=1)
    style = [
        ("BACKGROUND", (0, 0), (-1, 0), HEAD_BG),
        ("TEXTCOLOR", (0, 0), (-1, 0), INK),
        ("GRID", (0, 0), (-1, -1), 0.4, LINE),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("TOPPADDING", (0, 0), (-1, -1), 3),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
        ("ROWBACKGROUNDS", (0, 1), (-1, -2 if data.totals else -1), [colors.white, ROW_BG]),
    ]
    for index, column in enumerate(data.columns):
        if column.kind in (MONEY, NUMBER, PERCENT):
            style.append(("ALIGN", (index, 1), (index, -1), "RIGHT"))
    if data.totals:
        style.append(("BACKGROUND", (0, -1), (-1, -1), HEAD_BG))
    table.setStyle(TableStyle(style))
    story.append(table)

    if data.notes:
        story.append(Spacer(1, 4 * mm))
        for note in data.notes:
            story.append(Paragraph(note, styles["subtitle"]))

    doc.build(story, onFirstPage=_footer, onLaterPages=_footer)
    return target


def _footer(canvas, doc) -> None:
    """Draw the page number footer."""
    canvas.saveState()
    canvas.setFont(FONT, 7.5)
    canvas.setFillColor(MUTED)
    canvas.drawRightString(
        doc.pagesize[0] - 12 * mm, 8 * mm, f"BuildControl · {canvas.getPageNumber()}"
    )
    canvas.restoreState()


def export_purchase_order(order_id: int, path: str | Path | None = None) -> Path:
    """Render a purchase order document."""
    payload = purchase_service.order_document(order_id)
    company = settings_service.get_company()
    styles = _styles()
    target = Path(path) if path else _output_path(f"order_{payload['order_no']}")

    doc = SimpleDocTemplate(
        str(target),
        pagesize=A4,
        leftMargin=18 * mm,
        rightMargin=18 * mm,
        topMargin=16 * mm,
        bottomMargin=16 * mm,
        title=payload["order_no"],
    )
    story = [
        Paragraph(company.get("name", "BuildControl"), styles["subtitle"]),
        Paragraph(f"{tr('purchase_order')} {payload['order_no']}", styles["title"]),
        Paragraph(
            f"{tr('date')}: {fmt_date(payload['order_date'])} · "
            f"{tr('project')}: {payload['project']}",
            styles["subtitle"],
        ),
        Spacer(1, 6 * mm),
    ]

    info = [
        [tr("supplier"), payload["supplier"]],
        [tr("contact"), payload["supplier_phone"]],
        [tr("delivery_address"), payload["delivery_address"]],
        [tr("payment_terms"), payload["payment_terms"]],
        [tr("delivery_days"), str(payload["delivery_days"])],
    ]
    info_table = Table(
        [
            [Paragraph(k, styles["cell_bold"]), Paragraph(str(v or "—"), styles["cell"])]
            for k, v in info
        ],
        colWidths=[45 * mm, doc.width - 45 * mm],
    )
    info_table.setStyle(
        TableStyle(
            [
                ("GRID", (0, 0), (-1, -1), 0.4, LINE),
                ("BACKGROUND", (0, 0), (0, -1), ROW_BG),
                ("TOPPADDING", (0, 0), (-1, -1), 4),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
            ]
        )
    )
    story.append(info_table)
    story.append(Spacer(1, 6 * mm))

    goods = [
        [
            Paragraph(tr("product_service"), styles["cell_bold"]),
            Paragraph(tr("quantity"), styles["cell_bold"]),
            Paragraph(tr("unit_price"), styles["cell_bold"]),
            Paragraph(tr("delivery_cost"), styles["cell_bold"]),
            Paragraph(tr("total_value"), styles["cell_bold"]),
        ],
        [
            Paragraph(payload["title"], styles["cell"]),
            Paragraph(fmt_qty(payload["quantity"]), styles["cell"]),
            Paragraph(fmt_money(payload["unit_price"], with_suffix=False), styles["cell"]),
            Paragraph(fmt_money(payload["delivery_cost"], with_suffix=False), styles["cell"]),
            Paragraph(fmt_money(payload["total_amount"], with_suffix=False), styles["cell_bold"]),
        ],
    ]
    goods_table = Table(goods, colWidths=[doc.width * w for w in (0.4, 0.12, 0.16, 0.16, 0.16)])
    goods_table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), HEAD_BG),
                ("GRID", (0, 0), (-1, -1), 0.4, LINE),
                ("ALIGN", (1, 1), (-1, -1), "RIGHT"),
                ("TOPPADDING", (0, 0), (-1, -1), 5),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
            ]
        )
    )
    story.append(goods_table)
    story.append(Spacer(1, 8 * mm))
    story.append(
        Paragraph(f"<b>{tr('total')}: {fmt_money(payload['total_amount'])}</b>", styles["right"])
    )
    if payload["note"]:
        story.append(Spacer(1, 4 * mm))
        story.append(Paragraph(f"{tr('note')}: {payload['note']}", styles["subtitle"]))
    story.append(Spacer(1, 14 * mm))
    story.append(
        Paragraph(company.get("requisites", ""), styles["subtitle"]),
    )
    doc.build(story, onFirstPage=_footer, onLaterPages=_footer)
    return target
