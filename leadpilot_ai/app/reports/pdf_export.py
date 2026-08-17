"""PDF report generation with reportlab (dark-on-light printable layout)."""

from __future__ import annotations

import logging
from collections.abc import Iterable, Sequence
from pathlib import Path
from typing import Any

from reportlab.lib import colors
from reportlab.lib.enums import TA_LEFT
from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import (
    KeepTogether,
    PageBreak,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)

from app.config import APP_NAME, APP_VERSION
from app.utils.dates import fmt_datetime, now

logger = logging.getLogger(__name__)

ACCENT = colors.HexColor("#1D4ED8")
HEADER_BG = colors.HexColor("#1E293B")
HEADER_TEXT = colors.HexColor("#F8FAFC")
ROW_ALT = colors.HexColor("#EEF2F7")
BORDER = colors.HexColor("#CBD5E1")


def _styles() -> dict[str, ParagraphStyle]:
    """Return the paragraph styles used by every report."""
    base = getSampleStyleSheet()
    return {
        "title": ParagraphStyle(
            "ReportTitle", parent=base["Title"], fontSize=16, spaceAfter=4, textColor=ACCENT
        ),
        "subtitle": ParagraphStyle(
            "ReportSubtitle",
            parent=base["Normal"],
            fontSize=9,
            textColor=colors.HexColor("#64748B"),
            spaceAfter=10,
        ),
        "section": ParagraphStyle(
            "Section", parent=base["Heading3"], fontSize=11, spaceBefore=10, spaceAfter=4
        ),
        "cell": ParagraphStyle(
            "Cell", parent=base["Normal"], fontSize=8, leading=10, alignment=TA_LEFT
        ),
    }


def _table(headers: Sequence[str], rows: Iterable[Sequence[Any]], styles) -> Table:
    """Build a styled table flowable."""
    data = [[Paragraph(f"<b>{h}</b>", styles["cell"]) for h in headers]]
    for row in rows:
        data.append(
            [Paragraph(str(value if value is not None else ""), styles["cell"]) for value in row]
        )
    table = Table(data, repeatRows=1, hAlign="LEFT")
    table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), HEADER_BG),
                ("TEXTCOLOR", (0, 0), (-1, 0), HEADER_TEXT),
                ("GRID", (0, 0), (-1, -1), 0.4, BORDER),
                ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, ROW_ALT]),
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                ("LEFTPADDING", (0, 0), (-1, -1), 5),
                ("RIGHTPADDING", (0, 0), (-1, -1), 5),
                ("TOPPADDING", (0, 0), (-1, -1), 3),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
            ]
        )
    )
    return table


def build_report(
    path: str,
    title: str,
    sections: list[tuple[str, Sequence[str], Iterable[Sequence[Any]]]],
    *,
    subtitle: str = "",
    company: str = "",
    landscape_mode: bool = True,
) -> str:
    """Render a multi-section report and return the file path."""
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    styles = _styles()
    page = landscape(A4) if landscape_mode else A4
    document = SimpleDocTemplate(
        str(target),
        pagesize=page,
        leftMargin=12 * mm,
        rightMargin=12 * mm,
        topMargin=12 * mm,
        bottomMargin=12 * mm,
        title=title,
        author=APP_NAME,
    )
    story: list[Any] = [Paragraph(title, styles["title"])]
    meta = f"{company or ''} · {fmt_datetime(now())} · {APP_NAME} v{APP_VERSION}"
    if subtitle:
        meta = f"{subtitle}<br/>{meta}"
    story.append(Paragraph(meta, styles["subtitle"]))

    for index, (section_title, headers, rows) in enumerate(sections):
        materialised = [list(r) for r in rows]
        block = [Paragraph(section_title, styles["section"])]
        if materialised:
            block.append(_table(headers, materialised, styles))
        else:
            block.append(Paragraph("—", styles["cell"]))
        story.append(KeepTogether(block) if len(materialised) < 12 else block[0])
        if len(materialised) >= 12:
            story.append(_table(headers, materialised, styles))
        story.append(Spacer(1, 6))
        if index < len(sections) - 1 and len(materialised) > 25:
            story.append(PageBreak())

    document.build(story)
    logger.info("PDF report written: %s", target)
    return str(target)
