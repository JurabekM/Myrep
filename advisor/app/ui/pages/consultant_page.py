"""Biznes-konsultant sahifasi — framework tanlab hujjat generatsiyasi."""

from __future__ import annotations

from PyQt6.QtCore import QThreadPool
from PyQt6.QtWidgets import (
    QComboBox,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QScrollArea,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from app.container import Container
from app.services.consultant_service import FRAMEWORK_LABELS, Framework
from app.ui.widgets.common import Card, PageHeader
from app.ui.widgets.markdown_view import MarkdownView
from app.ui.widgets.workers import CallableRunnable


class ConsultantPage(QWidget):
    def __init__(self, container: Container, parent: QWidget | None = None):
        super().__init__(parent)
        self._container = container
        self._pool = QThreadPool.globalInstance()

        root = QVBoxLayout(self)
        root.setContentsMargins(24, 20, 24, 20)
        root.setSpacing(12)
        root.addWidget(
            PageHeader("Biznes Konsultant", "Professional biznes hujjatlarini bir necha daqiqada yarating")
        )

        form = Card()
        self._framework_box = QComboBox()
        self._frameworks = list(Framework)
        for fw in self._frameworks:
            self._framework_box.addItem(FRAMEWORK_LABELS[fw])
        form.layout().addWidget(QLabel("Framework:"))
        form.layout().addWidget(self._framework_box)

        form.layout().addWidget(QLabel("Biznes tavsifi (kamida 20 belgi):"))
        self._description = QTextEdit()
        self._description.setPlaceholderText(
            "Masalan: Toshkentda milliy taomlar yetkazib berish. Auditoriya — ofis xodimlari…"
        )
        self._description.setFixedHeight(90)
        form.layout().addWidget(self._description)

        self._extra = QTextEdit()
        self._extra.setPlaceholderText("Qo'shimcha kontekst (ixtiyoriy): byudjet, muddat…")
        self._extra.setFixedHeight(56)
        form.layout().addWidget(self._extra)

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
        if len(description) < 20:
            self._status.setText("Biznes tavsifi kamida 20 belgi bo'lishi kerak")
            return
        framework = self._frameworks[self._framework_box.currentIndex()]
        extra = self._extra.toPlainText().strip()

        self._generate_btn.setEnabled(False)
        self._status.setText("Yaratilmoqda… (30-60 soniya)")

        runnable = CallableRunnable(
            self._container.consultant_service.generate, framework, description, extra
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
