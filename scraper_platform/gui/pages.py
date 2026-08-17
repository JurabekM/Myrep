# -*- coding: utf-8 -*-
"""
gui/pages.py
============
GUI sahifalari (Dashboard, New Task, Scheduler, Results, Logs).

Har bir sahifa QWidget bo'lib, asosiy oyna (MainWindow) tomonidan
QStackedWidget ichida almashtiriladi.
"""

from __future__ import annotations

import json
from typing import Any

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGridLayout, QLabel, QLineEdit,
    QComboBox, QPushButton, QFrame, QTableWidget, QTableWidgetItem,
    QCheckBox, QPlainTextEdit, QProgressBar, QHeaderView, QMessageBox,
    QFileDialog, QSpinBox, QFormLayout, QTextEdit, QAbstractItemView,
)

from config.settings import CONFIG
from database.db_manager import DB
from scheduler.task_scheduler import SCHEDULER
from scraper.task_runner import TaskOptions, TaskProgress
from gui.workers import ScrapeWorker
from logs.logger import get_logger

log = get_logger(__name__)


def _card(widget: QWidget) -> QFrame:
    """Widget'ni kartochka (card) freym ichiga o'raydi."""
    frame = QFrame()
    frame.setProperty("class", "card")
    frame.setStyleSheet("QFrame { }")  # class selektori ishlashi uchun
    layout = QVBoxLayout(frame)
    layout.setContentsMargins(18, 18, 18, 18)
    layout.addWidget(widget)
    return frame


# =====================================================================
# DASHBOARD
# =====================================================================
class DashboardPage(QWidget):
    """Umumiy statistikani ko'rsatuvchi bosh sahifa."""

    def __init__(self) -> None:
        super().__init__()
        layout = QVBoxLayout(self)
        layout.setContentsMargins(30, 30, 30, 30)
        layout.setSpacing(20)

        title = QLabel("Boshqaruv paneli")
        title.setObjectName("pageTitle")
        layout.addWidget(title)

        # Statistika kartochkalari
        self.grid = QGridLayout()
        self.grid.setSpacing(16)
        self._stat_labels: dict[str, QLabel] = {}
        specs = [
            ("total_sessions", "Jami sessiyalar"),
            ("total_items", "Yig'ilgan yozuvlar"),
            ("total_pages", "Qayta ishlangan sahifalar"),
            ("success_rate", "Muvaffaqiyat foizi (%)"),
        ]
        for i, (key, caption) in enumerate(specs):
            card = QFrame()
            card.setProperty("class", "card")
            cl = QVBoxLayout(card)
            cl.setContentsMargins(20, 20, 20, 20)
            value = QLabel("0")
            value.setObjectName("statValue")
            cap = QLabel(caption)
            cap.setObjectName("statLabel")
            cl.addWidget(value)
            cl.addWidget(cap)
            self._stat_labels[key] = value
            self.grid.addWidget(card, 0, i)
        layout.addLayout(self.grid)

        # Oxirgi sessiyalar jadvali
        rec_label = QLabel("Oxirgi sessiyalar")
        rec_label.setObjectName("pageTitle")
        layout.addWidget(rec_label)

        self.table = QTableWidget()
        self.table.setColumnCount(6)
        self.table.setHorizontalHeaderLabels(
            ["ID", "Nomi", "URL", "Dvigatel", "Holat", "Yozuvlar"])
        self.table.horizontalHeader().setSectionResizeMode(
            QHeaderView.ResizeMode.Stretch)
        self.table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        layout.addWidget(self.table)

        refresh_btn = QPushButton("Yangilash")
        refresh_btn.clicked.connect(self.refresh)
        layout.addWidget(refresh_btn, alignment=Qt.AlignmentFlag.AlignLeft)

        self.refresh()

    def refresh(self) -> None:
        """Statistika va jadvalni bazadan yangilaydi."""
        stats = DB.get_dashboard_stats()
        for key, label in self._stat_labels.items():
            label.setText(str(stats.get(key, 0)))

        sessions = DB.list_sessions(limit=50)
        self.table.setRowCount(len(sessions))
        for row, s in enumerate(sessions):
            values = [str(s["id"]), s["name"], s["start_url"],
                      s["engine"], s["status"], str(s["total_items"])]
            for col, val in enumerate(values):
                self.table.setItem(row, col, QTableWidgetItem(val))


# =====================================================================
# NEW TASK
# =====================================================================
class NewTaskPage(QWidget):
    """Yangi scraping vazifasini yaratish sahifasi."""

    def __init__(self, on_finished=None) -> None:
        super().__init__()
        self.worker: ScrapeWorker | None = None
        self._on_finished_cb = on_finished

        layout = QVBoxLayout(self)
        layout.setContentsMargins(30, 30, 30, 30)
        layout.setSpacing(16)

        title = QLabel("Yangi vazifa")
        title.setObjectName("pageTitle")
        layout.addWidget(title)

        form = QFormLayout()
        form.setSpacing(12)

        self.url_input = QLineEdit()
        self.url_input.setPlaceholderText("https://example.com")
        form.addRow("URL:", self.url_input)

        self.name_input = QLineEdit()
        self.name_input.setPlaceholderText("Vazifa nomi (ixtiyoriy)")
        form.addRow("Nomi:", self.name_input)

        self.engine_combo = QComboBox()
        self.engine_combo.addItems(["auto", "requests", "playwright", "cloudscraper"])
        form.addRow("Dvigatel:", self.engine_combo)

        self.export_combo = QComboBox()
        self.export_combo.addItems(["(eksport yo'q)", "csv", "xlsx", "json", "sqlite"])
        form.addRow("Eksport:", self.export_combo)

        # CSS selektorlar (JSON ko'rinishida)
        self.css_input = QTextEdit()
        self.css_input.setPlaceholderText(
            'Ixtiyoriy CSS selektorlar (JSON):\n'
            '{"sarlavha": "h1", "narx": ".price"}')
        self.css_input.setMaximumHeight(80)
        form.addRow("CSS selektorlar:", self.css_input)

        layout.addLayout(form)

        # Checkboxlar
        opts = QHBoxLayout()
        self.crawl_check = QCheckBox("Saytni aylanib chiqish (crawl)")
        self.scroll_check = QCheckBox("Infinite scroll")
        self.ai_check = QCheckBox("AI tahlil")
        self.ai_check.setChecked(True)
        self.plugin_check = QCheckBox("Pluginlar")
        self.plugin_check.setChecked(True)
        for w in (self.crawl_check, self.scroll_check, self.ai_check, self.plugin_check):
            opts.addWidget(w)
        opts.addStretch()
        layout.addLayout(opts)

        # Boshqaruv tugmalari
        btns = QHBoxLayout()
        self.start_btn = QPushButton("Boshlash")
        self.start_btn.clicked.connect(self.start_task)
        self.stop_btn = QPushButton("To'xtatish")
        self.stop_btn.setProperty("class", "danger")
        self.stop_btn.setEnabled(False)
        self.stop_btn.clicked.connect(self.stop_task)
        btns.addWidget(self.start_btn)
        btns.addWidget(self.stop_btn)
        btns.addStretch()
        layout.addLayout(btns)

        # Progress
        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 0)  # noaniq (busy) rejim
        self.progress_bar.hide()
        layout.addWidget(self.progress_bar)

        self.status_label = QLabel("")
        self.status_label.setObjectName("statLabel")
        layout.addWidget(self.status_label)

        layout.addStretch()

    # -----------------------------------------------------------------
    def _parse_selectors(self) -> dict[str, str]:
        """CSS selektor JSON matnini lug'atga aylantiradi."""
        text = self.css_input.toPlainText().strip()
        if not text:
            return {}
        try:
            data = json.loads(text)
            return {str(k): str(v) for k, v in data.items()}
        except json.JSONDecodeError:
            QMessageBox.warning(self, "Xatolik", "CSS selektorlar noto'g'ri JSON formatda.")
            return {}

    def start_task(self) -> None:
        """Vazifani ishga tushiradi."""
        url = self.url_input.text().strip()
        if not url:
            QMessageBox.warning(self, "Xatolik", "URL kiriting.")
            return
        if not url.startswith(("http://", "https://")):
            url = "https://" + url

        export = self.export_combo.currentText()
        options = TaskOptions(
            url=url,
            name=self.name_input.text().strip(),
            engine=self.engine_combo.currentText(),
            crawl=self.crawl_check.isChecked(),
            infinite_scroll=self.scroll_check.isChecked(),
            css_selectors=self._parse_selectors(),
            use_ai=self.ai_check.isChecked(),
            use_plugins=self.plugin_check.isChecked(),
            export_format="" if export.startswith("(") else export,
        )

        self.worker = ScrapeWorker(options)
        self.worker.progress_updated.connect(self._on_progress)
        self.worker.finished_task.connect(self._on_finished)
        self.worker.error_occurred.connect(self._on_error)
        self.worker.start()

        self.start_btn.setEnabled(False)
        self.stop_btn.setEnabled(True)
        self.progress_bar.show()
        self.status_label.setText("Ishlayapti...")

    def stop_task(self) -> None:
        """Vazifani to'xtatadi."""
        if self.worker:
            self.worker.stop()
            self.status_label.setText("To'xtatilmoqda...")

    def _on_progress(self, progress: TaskProgress) -> None:
        self.status_label.setText(
            f"Sahifa: {progress.pages_done} | Yozuv: {progress.items_found} "
            f"| {progress.current_url[:60]}")

    def _on_finished(self, result: dict[str, Any]) -> None:
        self.progress_bar.hide()
        self.start_btn.setEnabled(True)
        self.stop_btn.setEnabled(False)
        msg = (f"Yakunlandi ({result['status']}): {result['pages_done']} sahifa, "
               f"{result['items_found']} yozuv")
        if result.get("export_path"):
            msg += f"\nEksport: {result['export_path']}"
        self.status_label.setText(msg)
        QMessageBox.information(self, "Vazifa yakunlandi", msg)
        if self._on_finished_cb:
            self._on_finished_cb()

    def _on_error(self, error: str) -> None:
        self.progress_bar.hide()
        self.start_btn.setEnabled(True)
        self.stop_btn.setEnabled(False)
        self.status_label.setText(f"Xatolik: {error}")
        QMessageBox.critical(self, "Xatolik", error)


# =====================================================================
# SCHEDULER
# =====================================================================
class SchedulerPage(QWidget):
    """Rejalashtirilgan vazifalarni boshqarish sahifasi."""

    def __init__(self) -> None:
        super().__init__()
        layout = QVBoxLayout(self)
        layout.setContentsMargins(30, 30, 30, 30)
        layout.setSpacing(16)

        title = QLabel("Rejalashtirish")
        title.setObjectName("pageTitle")
        layout.addWidget(title)

        # Yangi reja formasi
        form = QFormLayout()
        self.url_input = QLineEdit()
        self.url_input.setPlaceholderText("https://example.com")
        form.addRow("URL:", self.url_input)
        self.name_input = QLineEdit()
        form.addRow("Nomi:", self.name_input)
        self.type_combo = QComboBox()
        self.type_combo.addItems(["once", "hourly", "daily", "cron"])
        self.type_combo.currentTextChanged.connect(self._toggle_cron)
        form.addRow("Reja turi:", self.type_combo)
        self.cron_input = QLineEdit()
        self.cron_input.setPlaceholderText("0 */6 * * *  (cron formati)")
        self.cron_input.setEnabled(False)
        form.addRow("Cron:", self.cron_input)
        layout.addLayout(form)

        add_btn = QPushButton("Reja qo'shish")
        add_btn.clicked.connect(self.add_job)
        layout.addWidget(add_btn, alignment=Qt.AlignmentFlag.AlignLeft)

        # Mavjud rejalar jadvali
        self.table = QTableWidget()
        self.table.setColumnCount(6)
        self.table.setHorizontalHeaderLabels(
            ["ID", "Nomi", "URL", "Turi", "Oxirgi ishlash", "Amal"])
        self.table.horizontalHeader().setSectionResizeMode(
            QHeaderView.ResizeMode.Stretch)
        self.table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        layout.addWidget(self.table)

        self.refresh()

    def _toggle_cron(self, text: str) -> None:
        self.cron_input.setEnabled(text == "cron")

    def add_job(self) -> None:
        url = self.url_input.text().strip()
        if not url:
            QMessageBox.warning(self, "Xatolik", "URL kiriting.")
            return
        if not url.startswith(("http://", "https://")):
            url = "https://" + url
        SCHEDULER.add_job(
            name=self.name_input.text().strip() or url,
            url=url,
            schedule_type=self.type_combo.currentText(),
            cron_expr=self.cron_input.text().strip(),
            task_config={"engine": "auto"},
        )
        self.url_input.clear()
        self.name_input.clear()
        self.refresh()

    def refresh(self) -> None:
        jobs = SCHEDULER.list_jobs()
        self.table.setRowCount(len(jobs))
        for row, j in enumerate(jobs):
            last = str(j["last_run"]) if j["last_run"] else "—"
            values = [str(j["id"]), j["name"], j["url"], j["schedule_type"], last]
            for col, val in enumerate(values):
                self.table.setItem(row, col, QTableWidgetItem(str(val)))
            del_btn = QPushButton("O'chirish")
            del_btn.setProperty("class", "danger")
            del_btn.clicked.connect(lambda _, jid=j["id"]: self._delete(jid))
            self.table.setCellWidget(row, 5, del_btn)

    def _delete(self, job_id: int) -> None:
        SCHEDULER.remove_job(job_id)
        self.refresh()


# =====================================================================
# RESULTS
# =====================================================================
class ResultsPage(QWidget):
    """Yig'ilgan natijalarni ko'rish, qidirish va eksport qilish sahifasi."""

    def __init__(self) -> None:
        super().__init__()
        layout = QVBoxLayout(self)
        layout.setContentsMargins(30, 30, 30, 30)
        layout.setSpacing(16)

        title = QLabel("Natijalar")
        title.setObjectName("pageTitle")
        layout.addWidget(title)

        # Qidiruv paneli
        search_row = QHBoxLayout()
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("Qidirish...")
        self.search_input.returnPressed.connect(self.refresh)
        search_btn = QPushButton("Qidirish")
        search_btn.clicked.connect(self.refresh)
        export_btn = QPushButton("Eksport (CSV)")
        export_btn.setProperty("class", "secondary")
        export_btn.clicked.connect(self.export_results)
        search_row.addWidget(self.search_input)
        search_row.addWidget(search_btn)
        search_row.addWidget(export_btn)
        layout.addLayout(search_row)

        self.table = QTableWidget()
        self.table.horizontalHeader().setSectionResizeMode(
            QHeaderView.ResizeMode.Interactive)
        self.table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        layout.addWidget(self.table)

        self._current_data: list[dict[str, Any]] = []
        self.refresh()

    def refresh(self) -> None:
        search = self.search_input.text().strip()
        data = DB.get_items(search=search, limit=500)
        self._current_data = data
        if not data:
            self.table.setRowCount(0)
            self.table.setColumnCount(0)
            return

        # Ustunlarni birlashtirib olamiz
        columns: list[str] = []
        for row in data:
            for key in row:
                if key not in columns:
                    columns.append(key)
        columns = columns[:12]  # juda ko'p ustun bo'lmasin

        self.table.setColumnCount(len(columns))
        self.table.setHorizontalHeaderLabels(columns)
        self.table.setRowCount(len(data))
        for r, row in enumerate(data):
            for c, col in enumerate(columns):
                val = row.get(col, "")
                if isinstance(val, (dict, list)):
                    val = json.dumps(val, ensure_ascii=False)[:200]
                self.table.setItem(r, c, QTableWidgetItem(str(val)))

    def export_results(self) -> None:
        if not self._current_data:
            QMessageBox.information(self, "Ma'lumot yo'q", "Eksport qilish uchun ma'lumot yo'q.")
            return
        path, _ = QFileDialog.getSaveFileName(
            self, "Eksport", "results.csv", "CSV (*.csv);;JSON (*.json);;Excel (*.xlsx)")
        if not path:
            return
        from exporters.exporter import Exporter
        fmt = path.rsplit(".", 1)[-1].lower()
        Exporter(self._current_data).export(fmt, path)
        QMessageBox.information(self, "Eksport", f"Saqlandi: {path}")


# =====================================================================
# LOGS
# =====================================================================
class LogsPage(QWidget):
    """Real-time loglarni ko'rsatuvchi sahifa."""

    def __init__(self) -> None:
        super().__init__()
        layout = QVBoxLayout(self)
        layout.setContentsMargins(30, 30, 30, 30)
        layout.setSpacing(16)

        title = QLabel("Loglar")
        title.setObjectName("pageTitle")
        layout.addWidget(title)

        self.console = QPlainTextEdit()
        self.console.setObjectName("logConsole")
        self.console.setReadOnly(True)
        self.console.setMaximumBlockCount(2000)  # xotira nazorati
        layout.addWidget(self.console)

        clear_btn = QPushButton("Tozalash")
        clear_btn.setProperty("class", "secondary")
        clear_btn.clicked.connect(self.console.clear)
        layout.addWidget(clear_btn, alignment=Qt.AlignmentFlag.AlignLeft)

    def append_log(self, message: str) -> None:
        """Yangi log xabarini konsolga qo'shadi (thread-safe emit orqali)."""
        self.console.appendPlainText(message)
