"""Lightweight Gantt timeline painted with QPainter."""

from __future__ import annotations

from datetime import date, timedelta

from PySide6.QtCore import QRectF, Qt, Signal
from PySide6.QtGui import QColor, QFont, QPainter, QPen
from PySide6.QtWidgets import QScrollArea, QSizePolicy, QWidget

from app.models.enums import StageStatus
from app.ui.styles.theme import COLORS
from app.utils.formatting import fmt_date

ROW_H = 34
LABEL_W = 240
HEADER_H = 34
DAY_MIN_W = 3.0

_STATUS_COLOR = {
    StageStatus.NOT_STARTED.value: COLORS.text_faint,
    StageStatus.IN_PROGRESS.value: COLORS.accent,
    StageStatus.REVIEW.value: COLORS.info,
    StageStatus.DELAYED.value: COLORS.danger,
    StageStatus.DONE.value: COLORS.success,
    StageStatus.BLOCKED.value: COLORS.warning,
}


class GanttChart(QWidget):
    """Paints planned bars, actual progress and the today marker."""

    stage_clicked = Signal(int)

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._rows: list[dict] = []
        self._start: date = date.today()
        self._end: date = date.today() + timedelta(days=30)
        self._day_width = 6.0
        self.setMinimumHeight(HEADER_H + ROW_H)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        self.setMouseTracking(True)

    def set_rows(self, rows: list[dict]) -> None:
        """Feed the chart with ``{id, name, start, end, progress, status}`` rows."""
        self._rows = [r for r in rows if r.get("start") and r.get("end")]
        if self._rows:
            self._start = min(r["start"] for r in self._rows)
            self._end = max(r["end"] for r in self._rows)
            if self._end <= self._start:
                self._end = self._start + timedelta(days=1)
        self.setMinimumHeight(HEADER_H + max(1, len(self._rows)) * ROW_H + 12)
        self._recompute_width()
        self.update()

    def resizeEvent(self, event) -> None:  # noqa: N802 - Qt naming
        super().resizeEvent(event)
        self._recompute_width()

    def _recompute_width(self) -> None:
        days = max(1, (self._end - self._start).days + 1)
        available = max(200, self.width() - LABEL_W - 16)
        self._day_width = max(DAY_MIN_W, available / days)

    def _x(self, day: date) -> float:
        return LABEL_W + (day - self._start).days * self._day_width

    def paintEvent(self, event) -> None:  # noqa: N802 - Qt naming
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        painter.fillRect(self.rect(), QColor(COLORS.surface))

        if not self._rows:
            painter.setPen(QColor(COLORS.text_faint))
            painter.drawText(self.rect(), int(Qt.AlignmentFlag.AlignCenter), "—")
            painter.end()
            return

        font = QFont(painter.font())
        font.setPointSizeF(8.5)
        painter.setFont(font)

        # month grid ------------------------------------------------------- #
        painter.setPen(QPen(QColor(COLORS.grid), 1))
        cursor = date(self._start.year, self._start.month, 1)
        while cursor <= self._end:
            x = self._x(cursor)
            if x >= LABEL_W:
                painter.drawLine(int(x), HEADER_H, int(x), self.height())
                painter.setPen(QColor(COLORS.text_muted))
                painter.drawText(int(x) + 4, HEADER_H - 12, cursor.strftime("%m.%Y"))
                painter.setPen(QPen(QColor(COLORS.grid), 1))
            month = cursor.month + 1
            year = cursor.year + (1 if month > 12 else 0)
            cursor = date(year, 1 if month > 12 else month, 1)

        # rows -------------------------------------------------------------- #
        for index, row in enumerate(self._rows):
            top = HEADER_H + index * ROW_H
            if index % 2:
                painter.fillRect(0, top, self.width(), ROW_H, QColor(COLORS.surface_alt))
            painter.setPen(QColor(COLORS.text))
            painter.drawText(
                QRectF(10, top, LABEL_W - 18, ROW_H),
                int(Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft),
                _elide(row["name"], 30),
            )

            x1 = self._x(row["start"])
            x2 = self._x(row["end"] + timedelta(days=1))
            bar = QRectF(x1, top + 8, max(6.0, x2 - x1), ROW_H - 16)
            color = QColor(_STATUS_COLOR.get(row.get("status", ""), COLORS.accent))
            painter.setPen(Qt.PenStyle.NoPen)
            painter.setBrush(QColor(color.red(), color.green(), color.blue(), 70))
            painter.drawRoundedRect(bar, 5, 5)

            progress = max(0.0, min(100.0, float(row.get("progress") or 0.0)))
            if progress:
                filled = QRectF(bar)
                filled.setWidth(bar.width() * progress / 100.0)
                painter.setBrush(color)
                painter.drawRoundedRect(filled, 5, 5)

            painter.setPen(QColor(COLORS.text))
            painter.drawText(
                bar.adjusted(6, 0, -4, 0),
                int(Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft),
                f"{progress:.0f}%",
            )

        # today marker ------------------------------------------------------ #
        today = date.today()
        if self._start <= today <= self._end:
            x = self._x(today)
            painter.setPen(QPen(QColor(COLORS.warning), 1.4, Qt.PenStyle.DashLine))
            painter.drawLine(int(x), HEADER_H - 6, int(x), self.height())
            painter.setPen(QColor(COLORS.warning))
            painter.drawText(int(x) + 4, HEADER_H - 20, fmt_date(today))
        painter.end()
        del event

    def mousePressEvent(self, event) -> None:  # noqa: N802 - Qt naming
        index = int((event.position().y() - HEADER_H) // ROW_H)
        if 0 <= index < len(self._rows):
            self.stage_clicked.emit(int(self._rows[index]["id"]))
        super().mousePressEvent(event)


def _elide(text: str, limit: int) -> str:
    return text if len(text) <= limit else text[: limit - 1] + "…"


class GanttPanel(QScrollArea):
    """Scrollable container hosting a :class:`GanttChart`."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.chart = GanttChart()
        self.setWidget(self.chart)
        self.setWidgetResizable(True)
        self.setMinimumHeight(200)

    def set_rows(self, rows: list[dict]) -> None:
        """Update the timeline."""
        self.chart.set_rows(rows)
