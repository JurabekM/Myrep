"""Matplotlib canvas — Ultra Dark uslubga sozlangan grafiklar."""

from __future__ import annotations

import matplotlib

matplotlib.use("QtAgg")  # PyQt6 backend

from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg
from matplotlib.figure import Figure

from app.ui.theme.palette import Colors as C


class ChartCanvas(FigureCanvasQTAgg):
    def __init__(self, width: float = 5, height: float = 3):
        self.figure = Figure(figsize=(width, height), facecolor=C.BG_SURFACE)
        super().__init__(self.figure)
        self.ax = self.figure.add_subplot(111)
        self._style_axes()

    def _style_axes(self) -> None:
        self.ax.set_facecolor(C.BG_SURFACE)
        for spine in self.ax.spines.values():
            spine.set_color(C.BORDER)
        self.ax.tick_params(colors=C.TEXT_SECONDARY, labelsize=9)
        self.ax.grid(True, color=C.CHART_GRID, linewidth=0.6, alpha=0.6)
        self.ax.title.set_color(C.TEXT_PRIMARY)

    def clear(self) -> None:
        self.ax.clear()
        self._style_axes()

    def bar(self, labels: list[str], values: list[float], title: str = "") -> None:
        self.clear()
        colors = [C.CHART_SERIES[i % len(C.CHART_SERIES)] for i in range(len(labels))]
        self.ax.bar(labels, values, color=colors)
        if title:
            self.ax.set_title(title, fontsize=11)
        self.figure.autofmt_xdate(rotation=30)
        self.figure.tight_layout()
        self.draw()

    def line(self, x: list[str], y: list[float], title: str = "") -> None:
        self.clear()
        self.ax.plot(x, y, color=C.ACCENT, marker="o", markersize=3, linewidth=1.8)
        self.ax.fill_between(range(len(x)), y, color=C.ACCENT, alpha=0.12)
        if title:
            self.ax.set_title(title, fontsize=11)
        self.figure.autofmt_xdate(rotation=30)
        self.figure.tight_layout()
        self.draw()

    def gauge(self, value: float, title: str = "") -> None:
        """0-100 oralig'idagi ballni yarim doira ko'rsatkich sifatida chizadi."""
        self.clear()
        self.ax.axis("off")
        value = max(0.0, min(value, 100.0))
        color = C.SUCCESS if value >= 66 else C.WARNING if value >= 33 else C.DANGER
        self.ax.pie(
            [value, 100 - value],
            colors=[color, C.BG_ELEVATED],
            startangle=90,
            counterclock=False,
            wedgeprops={"width": 0.35},
        )
        self.ax.text(0, 0, f"{int(value)}", ha="center", va="center",
                     fontsize=26, color=C.TEXT_PRIMARY, fontweight="bold")
        if title:
            self.ax.set_title(title, fontsize=11, color=C.TEXT_PRIMARY)
        self.figure.tight_layout()
        self.draw()
