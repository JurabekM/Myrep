"""Huquqiy yordamchi sahifasi — lex.uz RAG savol-javob + shartnoma tahlili."""

from __future__ import annotations

from PyQt6.QtCore import QThreadPool
from PyQt6.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QScrollArea,
    QTabWidget,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from app.container import Container
from app.ui.widgets.common import Card, PageHeader, confidence_badge
from app.ui.widgets.markdown_view import MarkdownView
from app.ui.widgets.workers import CallableRunnable


class LegalPage(QWidget):
    def __init__(self, container: Container, parent: QWidget | None = None):
        super().__init__(parent)
        self._container = container
        self._pool = QThreadPool.globalInstance()

        root = QVBoxLayout(self)
        root.setContentsMargins(24, 20, 24, 20)
        root.setSpacing(12)
        root.addWidget(
            PageHeader("Huquqiy Yordamchi", "lex.uz manbalariga tayangan ma'lumot")
        )

        tabs = QTabWidget()
        tabs.addTab(self._build_ask_tab(), "Savol berish")
        tabs.addTab(self._build_contract_tab(), "Shartnoma tahlili")
        tabs.addTab(self._build_import_tab(), "Qonun qo'shish")
        root.addWidget(tabs, stretch=1)

    # ------------------------------------------------------------- ask tab

    def _build_ask_tab(self) -> QWidget:
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(0, 12, 0, 0)

        self._question = QTextEdit()
        self._question.setPlaceholderText(
            "Masalan: MChJ ta'sischisi o'z ulushini qanday sotishi mumkin?"
        )
        self._question.setFixedHeight(70)
        layout.addWidget(self._question)

        row = QHBoxLayout()
        self._ask_btn = QPushButton("So'rash")
        self._ask_btn.setObjectName("Primary")
        self._ask_btn.clicked.connect(self._ask)
        row.addWidget(self._ask_btn)
        self._ask_status = QLabel("")
        self._ask_status.setObjectName("Muted")
        row.addWidget(self._ask_status)
        row.addStretch(1)
        layout.addLayout(row)

        self._answer_card = Card()
        self._badge_holder = QVBoxLayout()
        self._answer_card.layout().addLayout(self._badge_holder)
        self._answer_view = MarkdownView()
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QScrollArea.Shape.NoFrame)
        scroll.setWidget(self._answer_view)
        self._answer_card.layout().addWidget(scroll)
        layout.addWidget(self._answer_card, stretch=1)
        return page

    def _ask(self) -> None:
        question = self._question.toPlainText().strip()
        if len(question) < 5:
            self._ask_status.setText("Savolni to'liqroq yozing")
            return
        self._ask_btn.setEnabled(False)
        self._ask_status.setText("Qidirilmoqda…")
        runnable = CallableRunnable(self._container.legal_service.ask, question)
        runnable.signals.finished.connect(self._on_answer)
        runnable.signals.error.connect(self._on_ask_error)
        self._pool.start(runnable)

    def _on_answer(self, answer) -> None:  # type: ignore[no-untyped-def]
        self._clear_badges()
        self._badge_holder.addWidget(confidence_badge(answer.confidence))
        text = answer.answer
        if answer.sources:
            text += "\n\n**Manbalar:**\n"
            for i, s in enumerate(answer.sources, start=1):
                article = f", {s['article']}" if s.get("article") else ""
                url = f" — {s['url']}" if s.get("url") else ""
                text += f"[{i}] {s.get('title', 'Manba')}{article}{url}\n"
        text += f"\n\n{answer.disclaimer}"
        self._answer_view.set_markdown(text)
        self._ask_btn.setEnabled(True)
        self._ask_status.setText("")

    def _on_ask_error(self, message: str) -> None:
        self._answer_view.set_markdown(f"⚠️ Xatolik: {message}")
        self._ask_btn.setEnabled(True)
        self._ask_status.setText("")

    def _clear_badges(self) -> None:
        while self._badge_holder.count():
            item = self._badge_holder.takeAt(0)
            widget = item.widget()
            if widget:
                widget.deleteLater()

    # -------------------------------------------------------- contract tab

    def _build_contract_tab(self) -> QWidget:
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(0, 12, 0, 0)

        self._contract = QTextEdit()
        self._contract.setPlaceholderText("Shartnoma matnini joylashtiring (kamida 100 belgi)…")
        layout.addWidget(self._contract, stretch=1)

        self._focus = QLineEdit()
        self._focus.setPlaceholderText("Alohida e'tibor (ixtiyoriy): masalan, jarima bandlari")
        layout.addWidget(self._focus)

        row = QHBoxLayout()
        self._contract_btn = QPushButton("Tahlil qilish")
        self._contract_btn.setObjectName("Primary")
        self._contract_btn.clicked.connect(self._analyze_contract)
        row.addWidget(self._contract_btn)
        self._contract_status = QLabel("")
        self._contract_status.setObjectName("Muted")
        row.addWidget(self._contract_status)
        row.addStretch(1)
        layout.addLayout(row)

        self._contract_view = MarkdownView()
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QScrollArea.Shape.NoFrame)
        scroll.setWidget(self._contract_view)
        layout.addWidget(scroll, stretch=1)
        return page

    def _analyze_contract(self) -> None:
        text = self._contract.toPlainText().strip()
        if len(text) < 100:
            self._contract_status.setText("Shartnoma matni kamida 100 belgi bo'lishi kerak")
            return
        self._contract_btn.setEnabled(False)
        self._contract_status.setText("Tahlil qilinmoqda…")
        runnable = CallableRunnable(
            self._container.legal_service.analyze_contract, text, self._focus.text().strip()
        )
        runnable.signals.finished.connect(self._on_contract)
        runnable.signals.error.connect(self._on_contract_error)
        self._pool.start(runnable)

    def _on_contract(self, content: str) -> None:
        self._contract_view.set_markdown(content)
        self._contract_btn.setEnabled(True)
        self._contract_status.setText("")

    def _on_contract_error(self, message: str) -> None:
        self._contract_view.set_markdown(f"⚠️ Xatolik: {message}")
        self._contract_btn.setEnabled(True)
        self._contract_status.setText("")

    # ---------------------------------------------------------- import tab

    def _build_import_tab(self) -> QWidget:
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(0, 12, 0, 0)
        layout.addWidget(QLabel(
            "Lex.uz URL orqali qonun yuklab, lokal RAG bazasiga qo'shing "
            "(keyin 'Savol berish' bo'limi undan foydalanadi)."
        ))
        self._lex_url = QLineEdit()
        self._lex_url.setPlaceholderText("https://lex.uz/docs/...")
        layout.addWidget(self._lex_url)

        row = QHBoxLayout()
        self._import_btn = QPushButton("Yuklab indekslash")
        self._import_btn.setObjectName("Primary")
        self._import_btn.clicked.connect(self._import_lex)
        row.addWidget(self._import_btn)
        self._import_status = QLabel("")
        self._import_status.setObjectName("Muted")
        row.addWidget(self._import_status)
        row.addStretch(1)
        layout.addLayout(row)

        layout.addWidget(QLabel("Yoki qonun matnini qo'lda kiriting (internetsiz):"))
        self._manual_title = QLineEdit()
        self._manual_title.setPlaceholderText("Qonun/hujjat nomi")
        layout.addWidget(self._manual_title)
        self._manual_text = QTextEdit()
        self._manual_text.setPlaceholderText("Qonun matni…")
        layout.addWidget(self._manual_text, stretch=1)
        manual_btn = QPushButton("Matnni indekslash")
        manual_btn.clicked.connect(self._import_manual)
        layout.addWidget(manual_btn)
        return page

    def _import_lex(self) -> None:
        url = self._lex_url.text().strip()
        if not url:
            return
        self._import_btn.setEnabled(False)
        self._import_status.setText("Yuklab olinmoqda…")
        runnable = CallableRunnable(self._container.lex_scraper.ingest_url, url)
        runnable.signals.finished.connect(self._on_import)
        runnable.signals.error.connect(self._on_import_error)
        self._pool.start(runnable)

    def _import_manual(self) -> None:
        title = self._manual_title.text().strip()
        text = self._manual_text.toPlainText().strip()
        if len(title) < 3 or len(text) < 100:
            self._import_status.setText("Nom va matnni to'liqroq kiriting")
            return
        runnable = CallableRunnable(
            self._container.lex_scraper.ingest_manual_text, title, text
        )
        runnable.signals.finished.connect(self._on_import)
        runnable.signals.error.connect(self._on_import_error)
        self._pool.start(runnable)

    def _on_import(self, result: dict) -> None:
        self._import_status.setText(
            f"✓ '{result['title'][:40]}' indekslandi ({result['chunks']} chunk)"
        )
        self._import_btn.setEnabled(True)

    def _on_import_error(self, message: str) -> None:
        self._import_status.setText(f"⚠️ {message}")
        self._import_btn.setEnabled(True)
