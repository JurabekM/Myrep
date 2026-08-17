"""Marketing AI sahifasi."""

from __future__ import annotations

from PyQt6.QtCore import QThreadPool
from PyQt6.QtWidgets import (
    QComboBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QScrollArea,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from app.container import Container
from app.services.marketing_service import TASK_LABELS, MarketingTask
from app.ui.widgets.common import Card, PageHeader
from app.ui.widgets.markdown_view import MarkdownView
from app.ui.widgets.workers import CallableRunnable

_CHANNELS = ["telegram", "instagram", "facebook", "google_ads", "email", "website"]


class MarketingPage(QWidget):
    def __init__(self, container: Container, parent: QWidget | None = None):
        super().__init__(parent)
        self._container = container
        self._pool = QThreadPool.globalInstance()

        root = QVBoxLayout(self)
        root.setContentsMargins(24, 20, 24, 20)
        root.setSpacing(12)
        root.addWidget(
            PageHeader("Marketing AI", "O'zbekiston auditoriyasiga moslashgan materiallar")
        )

        form = Card()
        self._task_box = QComboBox()
        self._tasks = list(MarketingTask)
        for task in self._tasks:
            self._task_box.addItem(TASK_LABELS[task])
        form.layout().addWidget(QLabel("Vazifa:"))
        form.layout().addWidget(self._task_box)

        form.layout().addWidget(QLabel("Biznes tavsifi:"))
        self._description = QTextEdit()
        self._description.setFixedHeight(80)
        self._description.setPlaceholderText("Mahsulot/xizmat, auditoriya, hozirgi holat…")
        form.layout().addWidget(self._description)

        self._channels = QLineEdit()
        self._channels.setPlaceholderText(
            "Kanallar (vergul bilan): " + ", ".join(_CHANNELS)
        )
        self._channels.setText("telegram, instagram")
        form.layout().addWidget(self._channels)

        self._budget = QLineEdit()
        self._budget.setPlaceholderText("Oylik byudjet, so'm (ixtiyoriy)")
        form.layout().addWidget(self._budget)

        row = QHBoxLayout()
        self._generate_btn = QPushButton("Yaratish")
        self._generate_btn.setObjectName("Primary")
        self._generate_btn.clicked.connect(self._generate)
        row.addWidget(self._generate_btn)
        self._status = QLabel("")
        self._status.setObjectName("Muted")
        row.addWidget(self._status)
        row.addStretch(1)
        form.layout().addLayout(row)
        root.addWidget(form)

        result_card = Card()
        result_card.layout().addWidget(QLabel("Natija:"))
        self._result_view = MarkdownView()
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QScrollArea.Shape.NoFrame)
        scroll.setWidget(self._result_view)
        result_card.layout().addWidget(scroll)
        root.addWidget(result_card, stretch=1)

    def _generate(self) -> None:
        description = self._description.toPlainText().strip()
        if len(description) < 10:
            self._status.setText("Biznes tavsifini kiriting")
            return
        task = self._tasks[self._task_box.currentIndex()]
        channels = [c.strip() for c in self._channels.text().split(",") if c.strip()]
        budget_text = self._budget.text().strip().replace(" ", "")
        budget = int(budget_text) if budget_text.isdigit() else None

        self._generate_btn.setEnabled(False)
        self._status.setText("Yaratilmoqda…")

        runnable = CallableRunnable(
            self._container.marketing_service.generate,
            task, description, channels=channels, budget_uzs=budget,
        )
        runnable.signals.finished.connect(self._on_done)
        runnable.signals.error.connect(self._on_error)
        self._pool.start(runnable)

    def _on_done(self, content: str) -> None:
        self._result_view.set_markdown(content)
        self._generate_btn.setEnabled(True)
        self._status.setText("Tayyor")

    def _on_error(self, message: str) -> None:
        self._result_view.set_markdown(f"⚠️ Xatolik: {message}")
        self._generate_btn.setEnabled(True)
        self._status.setText("")
