"""Asosiy oyna — sidebar navigatsiya + almashinuvchi sahifalar (QStackedWidget)."""

from __future__ import annotations

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QButtonGroup,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QStackedWidget,
    QVBoxLayout,
    QWidget,
)

from app.container import Container
from app.ui.pages.chat_page import ChatPage
from app.ui.pages.consultant_page import ConsultantPage
from app.ui.pages.dashboard_page import DashboardPage
from app.ui.pages.documents_page import DocumentsPage
from app.ui.pages.finance_page import FinancePage
from app.ui.pages.legal_page import LegalPage
from app.ui.pages.marketing_page import MarketingPage
from app.ui.pages.settings_page import SettingsPage
from app.ui.pages.tax_page import TaxPage

# (belgi, matn, sahifa klassi)
_NAV = [
    ("💬", "AI Chat", ChatPage),
    ("📋", "Konsultant", ConsultantPage),
    ("⚖️", "Huquq", LegalPage),
    ("🧮", "Soliq", TaxPage),
    ("💰", "Moliya", FinancePage),
    ("📣", "Marketing", MarketingPage),
    ("📄", "Hujjatlar", DocumentsPage),
    ("📊", "Dashboard", DashboardPage),
    ("⚙️", "Sozlamalar", SettingsPage),
]


class MainWindow(QWidget):
    def __init__(self, container: Container):
        super().__init__()
        self._container = container
        self.setWindowTitle("AI Business Advisor Uzbekistan")
        self.resize(1200, 800)
        self.setMinimumSize(960, 640)

        root = QHBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        root.addWidget(self._build_sidebar())

        self._stack = QStackedWidget()
        root.addWidget(self._stack, stretch=1)

        # Sahifalar lazy emas — hammasi bir marta yaratiladi (holat saqlanadi).
        for icon, text, page_cls in _NAV:
            self._stack.addWidget(page_cls(container))

        self._buttons[0].setChecked(True)
        self._stack.setCurrentIndex(0)

    def _build_sidebar(self) -> QWidget:
        sidebar = QWidget()
        sidebar.setObjectName("Sidebar")
        sidebar.setFixedWidth(220)
        layout = QVBoxLayout(sidebar)
        layout.setContentsMargins(12, 16, 12, 16)
        layout.setSpacing(4)

        brand = QLabel("AI Business Advisor")
        brand.setObjectName("BrandLabel")
        layout.addWidget(brand)
        sub = QLabel("Uzbekistan · standalone")
        sub.setObjectName("BrandSub")
        layout.addWidget(sub)
        layout.addSpacing(16)

        self._buttons: list[QPushButton] = []
        self._group = QButtonGroup(self)
        self._group.setExclusive(True)
        for index, (icon, text, _) in enumerate(_NAV):
            button = QPushButton(f"  {icon}   {text}")
            button.setObjectName("SidebarButton")
            button.setCheckable(True)
            button.setCursor(Qt.CursorShape.PointingHandCursor)
            button.clicked.connect(lambda _checked, i=index: self._navigate(i))
            layout.addWidget(button)
            self._buttons.append(button)
            self._group.addButton(button)

        layout.addStretch(1)

        provider_note = QLabel(self._provider_status())
        provider_note.setObjectName("BrandSub")
        provider_note.setWordWrap(True)
        self._provider_note = provider_note
        layout.addWidget(provider_note)
        return sidebar

    def _provider_status(self) -> str:
        providers = self._container.router.available_providers()
        if providers:
            return "AI: " + ", ".join(providers)
        return "⚠️ AI sozlanmagan — Sozlamalarga o'ting"

    def _navigate(self, index: int) -> None:
        self._stack.setCurrentIndex(index)
        # Dashboard va Sozlamalarga kirganda holatni yangilaymiz.
        current = self._stack.currentWidget()
        if isinstance(current, DashboardPage):
            current.refresh()
        if hasattr(self, "_provider_note"):
            self._provider_note.setText(self._provider_status())
