"""Analitika dashboardi — matplotlib grafiklari (Ultra Dark)."""

from __future__ import annotations

from PyQt6.QtWidgets import (
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from app.container import Container
from app.ui.widgets.chart_canvas import ChartCanvas
from app.ui.widgets.common import Card, PageHeader, StatTile


class DashboardPage(QWidget):
    def __init__(self, container: Container, parent: QWidget | None = None):
        super().__init__(parent)
        self._dashboard = container.dashboard_service

        root = QVBoxLayout(self)
        root.setContentsMargins(24, 20, 24, 20)
        root.setSpacing(12)

        header_row = QHBoxLayout()
        header_row.addWidget(PageHeader("Dashboard", "Biznes salomatligi va foydalanish tahlili"))
        header_row.addStretch(1)
        refresh_btn = QPushButton("Yangilash")
        refresh_btn.clicked.connect(self.refresh)
        header_row.addWidget(refresh_btn)
        root.addLayout(header_row)

        # Statistika plitkalari
        tiles = QHBoxLayout()
        self._health_tile = StatTile("Biznes salomatligi")
        self._requests_tile = StatTile("Jami so'rovlar")
        self._profile_tile = StatTile("Profil to'liqligi")
        for tile in (self._health_tile, self._requests_tile, self._profile_tile):
            tiles.addWidget(tile)
        root.addLayout(tiles)

        # Grafiklar
        charts = QGridLayout()
        health_card = Card()
        health_card.layout().addWidget(QLabel("Biznes salomatligi"))
        self._health_chart = ChartCanvas(width=3, height=2.6)
        health_card.layout().addWidget(self._health_chart)
        charts.addWidget(health_card, 0, 0)

        usage_card = Card()
        usage_card.layout().addWidget(QLabel("Foydalanish (30 kun)"))
        self._usage_chart = ChartCanvas(width=5, height=2.6)
        usage_card.layout().addWidget(self._usage_chart)
        charts.addWidget(usage_card, 0, 1)

        module_card = Card()
        module_card.layout().addWidget(QLabel("Modullar bo'yicha so'rovlar"))
        self._module_chart = ChartCanvas(width=5, height=2.6)
        module_card.layout().addWidget(self._module_chart)
        charts.addWidget(module_card, 1, 0, 1, 2)

        charts.setColumnStretch(0, 1)
        charts.setColumnStretch(1, 2)
        root.addLayout(charts, stretch=1)

        # Tavsiyalar
        self._recommendations = QLabel("")
        self._recommendations.setObjectName("Muted")
        self._recommendations.setWordWrap(True)
        root.addWidget(self._recommendations)

        self.refresh()

    def refresh(self) -> None:
        health = self._dashboard.business_health()
        by_day = self._dashboard.usage_by_day(30)
        by_module = self._dashboard.usage_by_module()

        self._health_tile.set_value(f"{health['score']}/100")
        self._profile_tile.set_value(f"{health['profile_completeness']}%")
        total_requests = sum(d["requests"] for d in by_day)
        self._requests_tile.set_value(str(total_requests))

        self._health_chart.gauge(health["score"])

        if by_day:
            self._usage_chart.line(
                [d["day"][5:] for d in by_day], [d["requests"] for d in by_day]
            )
        else:
            self._usage_chart.line(["—"], [0])

        if by_module:
            self._module_chart.bar(
                [d["module"] for d in by_module], [d["requests"] for d in by_module]
            )
        else:
            self._module_chart.bar(["ma'lumot yo'q"], [0])

        recs = health.get("recommendations", [])
        self._recommendations.setText(
            "  •  ".join(recs) if recs else "Ajoyib! Profil to'liq va faoliyat izchil."
        )
