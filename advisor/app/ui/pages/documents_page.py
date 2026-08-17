"""Hujjat tahlili sahifasi — yuklash, matn ajratish (fon), AI tahlil."""

from __future__ import annotations

from PyQt6.QtCore import QThreadPool
from PyQt6.QtWidgets import (
    QComboBox,
    QFileDialog,
    QHBoxLayout,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QPushButton,
    QScrollArea,
    QVBoxLayout,
    QWidget,
)

from app.container import Container
from app.services.document_extractor import SUPPORTED_EXTENSIONS
from app.services.document_service import TASK_LABELS, AnalysisTask
from app.ui.widgets.common import Card, PageHeader
from app.ui.widgets.markdown_view import MarkdownView
from app.ui.widgets.workers import CallableRunnable

_STATUS_LABEL = {"pending": "Kutilmoqda", "ready": "Tayyor", "failed": "Xatolik"}


class DocumentsPage(QWidget):
    def __init__(self, container: Container, parent: QWidget | None = None):
        super().__init__(parent)
        self._container = container
        self._pool = QThreadPool.globalInstance()
        self._selected_id: int | None = None

        root = QVBoxLayout(self)
        root.setContentsMargins(24, 20, 24, 20)
        root.setSpacing(12)
        root.addWidget(PageHeader(
            "Hujjat Tahlili", "PDF, Word, Excel, CSV, rasm (OCR) — lokal o'qish"
        ))

        from PyQt6.QtCore import Qt

        upload_btn = QPushButton("Fayl yuklash")
        upload_btn.setObjectName("Primary")
        upload_btn.clicked.connect(self._upload)
        root.addWidget(upload_btn, alignment=Qt.AlignmentFlag.AlignLeft)

        body = QHBoxLayout()

        # Chap: hujjatlar ro'yxati
        list_card = Card()
        list_card.layout().addWidget(QLabel("Hujjatlarim"))
        self._list = QListWidget()
        self._list.itemClicked.connect(self._on_select)
        list_card.layout().addWidget(self._list)
        body.addWidget(list_card, stretch=1)

        # O'ng: tahlil
        analyze_card = Card()
        analyze_card.layout().addWidget(QLabel("Tahlil"))
        controls = QHBoxLayout()
        self._task_box = QComboBox()
        self._tasks = list(AnalysisTask)
        for task in self._tasks:
            self._task_box.addItem(TASK_LABELS[task])
        controls.addWidget(self._task_box)
        self._analyze_btn = QPushButton("Tahlil qilish")
        self._analyze_btn.setObjectName("Primary")
        self._analyze_btn.clicked.connect(self._analyze)
        self._analyze_btn.setEnabled(False)
        controls.addWidget(self._analyze_btn)
        analyze_card.layout().addLayout(controls)
        self._status = QLabel("Chapdan hujjat tanlang")
        self._status.setObjectName("Muted")
        analyze_card.layout().addWidget(self._status)
        self._result_view = MarkdownView()
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QScrollArea.Shape.NoFrame)
        scroll.setWidget(self._result_view)
        analyze_card.layout().addWidget(scroll)
        body.addWidget(analyze_card, stretch=2)

        root.addLayout(body, stretch=1)
        self._refresh_list()

    # ---------------------------------------------------------------- upload

    def _upload(self) -> None:
        filter_str = "Hujjatlar (" + " ".join(f"*{ext}" for ext in SUPPORTED_EXTENSIONS) + ")"
        path, _ = QFileDialog.getOpenFileName(self, "Fayl tanlang", "", filter_str)
        if not path:
            return
        try:
            document = self._container.document_service.upload(path)
        except Exception as exc:  # noqa: BLE001
            self._status.setText(f"⚠️ {exc}")
            return
        self._refresh_list()
        self._status.setText(f"'{document.filename}' qayta ishlanmoqda…")
        runnable = CallableRunnable(self._container.document_service.process, document.id)
        runnable.signals.finished.connect(lambda _: self._on_processed())
        runnable.signals.error.connect(lambda msg: self._status.setText(f"⚠️ {msg}"))
        self._pool.start(runnable)

    def _on_processed(self) -> None:
        self._status.setText("Hujjat tayyor — tahlil turini tanlang")
        self._refresh_list()

    def _refresh_list(self) -> None:
        self._list.clear()
        for doc in self._container.document_service.list_documents():
            label = f"{doc.filename}  ·  {_STATUS_LABEL.get(doc.status, doc.status)}"
            item = QListWidgetItem(label)
            item.setData(256, doc.id)  # Qt.UserRole
            self._list.addItem(item)

    def _on_select(self, item: QListWidgetItem) -> None:
        self._selected_id = item.data(256)
        document = self._container.document_service._documents.get(self._selected_id)  # noqa: SLF001
        ready = document is not None and document.status == "ready"
        self._analyze_btn.setEnabled(ready)
        self._status.setText(
            "Tahlil turini tanlang" if ready else "Hujjat hali tayyor emas"
        )

    def _analyze(self) -> None:
        if self._selected_id is None:
            return
        task = self._tasks[self._task_box.currentIndex()]
        self._analyze_btn.setEnabled(False)
        self._status.setText("Tahlil qilinmoqda…")
        runnable = CallableRunnable(
            self._container.document_service.analyze, self._selected_id, task
        )
        runnable.signals.finished.connect(self._on_analyzed)
        runnable.signals.error.connect(self._on_error)
        self._pool.start(runnable)

    def _on_analyzed(self, content: str) -> None:
        self._result_view.set_markdown(content)
        self._analyze_btn.setEnabled(True)
        self._status.setText("Tayyor")

    def _on_error(self, message: str) -> None:
        self._result_view.set_markdown(f"⚠️ Xatolik: {message}")
        self._analyze_btn.setEnabled(True)
        self._status.setText("")
