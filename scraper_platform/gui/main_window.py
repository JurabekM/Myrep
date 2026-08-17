# -*- coding: utf-8 -*-
"""
gui/main_window.py
==================
Asosiy oyna. Yon menyu (sidebar) va sahifalarni (QStackedWidget)
birlashtiradi. Loglarni GUI'ga real-time uzatish uchun signal ko'prigi
o'rnatiladi.
"""

from __future__ import annotations

from PyQt6.QtCore import Qt, QObject, pyqtSignal
from PyQt6.QtWidgets import (
    QMainWindow, QWidget, QHBoxLayout, QVBoxLayout, QListWidget,
    QListWidgetItem, QStackedWidget, QLabel,
)

from gui.theme import DARK_QSS
from gui.pages import (
    DashboardPage, NewTaskPage, SchedulerPage, ResultsPage, LogsPage,
)
from logs.logger import add_gui_sink
from scheduler.task_scheduler import SCHEDULER


class LogBridge(QObject):
    """Loguru sink'idan (istalgan oqim) GUI thread'iga xabar uzatuvchi ko'prik."""
    message = pyqtSignal(str)


class MainWindow(QMainWindow):
    """Platformaning asosiy oynasi."""

    # Yon menyu bandlari (nom, sahifa indeksi)
    MENU_ITEMS = ["📊  Dashboard", "➕  Yangi vazifa", "⏰  Rejalashtirish",
                  "📁  Natijalar", "📜  Loglar"]

    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("Universal Web Scraping Platform")
        self.resize(1200, 780)
        self.setStyleSheet(DARK_QSS)

        # Markaziy widget
        central = QWidget()
        self.setCentralWidget(central)
        root = QHBoxLayout(central)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        # --- Yon menyu ---
        sidebar_container = QWidget()
        sidebar_container.setFixedWidth(230)
        sb_layout = QVBoxLayout(sidebar_container)
        sb_layout.setContentsMargins(0, 0, 0, 0)
        sb_layout.setSpacing(0)

        logo = QLabel("🕸️  ScrapePro")
        logo.setStyleSheet("font-size: 18px; font-weight: bold; padding: 22px 20px;")
        sb_layout.addWidget(logo)

        self.sidebar = QListWidget()
        self.sidebar.setObjectName("sidebar")
        for item in self.MENU_ITEMS:
            QListWidgetItem(item, self.sidebar)
        self.sidebar.currentRowChanged.connect(self._switch_page)
        sb_layout.addWidget(self.sidebar)
        root.addWidget(sidebar_container)

        # --- Sahifalar ---
        self.stack = QStackedWidget()
        self.dashboard = DashboardPage()
        self.new_task = NewTaskPage(on_finished=self._on_task_finished)
        self.scheduler_page = SchedulerPage()
        self.results = ResultsPage()
        self.logs = LogsPage()
        for page in (self.dashboard, self.new_task, self.scheduler_page,
                     self.results, self.logs):
            self.stack.addWidget(page)
        root.addWidget(self.stack, stretch=1)

        self.sidebar.setCurrentRow(0)

        # --- Loglarni GUI'ga ulash ---
        self._log_bridge = LogBridge()
        self._log_bridge.message.connect(self.logs.append_log)
        add_gui_sink(lambda msg: self._log_bridge.message.emit(msg), level="INFO")

        # --- Scheduler'ni ishga tushiramiz ---
        SCHEDULER.start()

    # -----------------------------------------------------------------
    def _switch_page(self, index: int) -> None:
        """Sahifani almashtiradi va kerak bo'lsa yangilaydi."""
        self.stack.setCurrentIndex(index)
        current = self.stack.currentWidget()
        # Ba'zi sahifalarni ochilganda yangilaymiz
        if hasattr(current, "refresh"):
            current.refresh()

    def _on_task_finished(self) -> None:
        """Vazifa yakunlanganda dashboard va natijalarni yangilaydi."""
        self.dashboard.refresh()
        self.results.refresh()

    def closeEvent(self, event) -> None:  # noqa: N802 - Qt override
        """Oyna yopilganda scheduler'ni to'xtatadi."""
        SCHEDULER.shutdown()
        super().closeEvent(event)
