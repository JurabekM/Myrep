"""`pyqtgraph` o'rami: siljiydigan chiziqli grafik."""
# pyqtgraph tip ma'lumotisiz keladi; shu fayl uning yagona iste'molchisi.
# pyright: reportMissingTypeStubs=false, reportUnknownMemberType=false
# pyright: reportUnknownVariableType=false, reportUnknownArgumentType=false

from collections import deque
from collections.abc import Sequence
from typing import Any

import pyqtgraph as pg
from PyQt6.QtWidgets import QVBoxLayout, QWidget

BACKGROUND = "#1c2128"
AXIS = "#8b95a5"
PALETTE = ("#4c9aff", "#3fb950", "#d29922", "#f85149")


class LineChart(QWidget):
    """Har seriya uchun oxirgi `window` ta qiymatni ko'rsatadi."""

    def __init__(
        self,
        series: Sequence[str],
        *,
        window: int = 120,
        y_range: tuple[float, float] | None = None,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self._plot: Any = pg.PlotWidget(background=BACKGROUND)
        self._plot.setMenuEnabled(False)
        self._plot.setMouseEnabled(x=False, y=False)
        self._plot.hideButtons()
        self._plot.showGrid(x=False, y=True, alpha=0.15)
        for axis in ("left", "bottom"):
            self._plot.getAxis(axis).setPen(pg.mkPen(AXIS))
            self._plot.getAxis(axis).setTextPen(pg.mkPen(AXIS))
        if y_range is not None:
            self._plot.setYRange(*y_range, padding=0.02)
        if len(series) > 1:
            self._plot.addLegend(offset=(-8, 8), labelTextColor=AXIS)
        self._data: list[deque[float]] = [deque(maxlen=window) for _ in series]
        self._curves: list[Any] = [
            self._plot.plot(pen=pg.mkPen(PALETTE[index % len(PALETTE)], width=2), name=name)
            for index, name in enumerate(series)
        ]
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self._plot)
        self.setMinimumHeight(180)

    def append(self, values: Sequence[float]) -> None:
        """Har seriyaga bittadan qiymat qo'shadi."""
        for data, curve, value in zip(self._data, self._curves, values, strict=True):
            data.append(float(value))
            curve.setData(list(data))

    def point_count(self, series_index: int = 0) -> int:
        return len(self._data[series_index])

    def last_value(self, series_index: int = 0) -> float | None:
        data = self._data[series_index]
        return data[-1] if data else None
