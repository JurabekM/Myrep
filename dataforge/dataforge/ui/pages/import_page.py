"""Ma'lumot yuklash sahifasi — fayl, papka, internet, baza, matn, namunalar."""
from __future__ import annotations

from pathlib import Path

import pandas as pd
from PySide6.QtCore import Qt
from PySide6.QtWidgets import (QComboBox, QFileDialog, QGridLayout, QHBoxLayout,
                               QInputDialog, QLabel, QLineEdit, QListWidget,
                               QListWidgetItem, QPlainTextEdit, QSpinBox,
                               QSplitter, QTabWidget, QVBoxLayout, QWidget)

from ...config import SAMPLES_DIR
from ...core import ingest
from ..tasks import run_async
from ..widgets import (Card, FrameTable, PageHeader, make_button, make_checkbox)
from .base import BasePage

FILE_FILTER = (
    "Barcha qo'llab-quvvatlanadigan (*.csv *.tsv *.txt *.log *.json *.jsonl *.ndjson "
    "*.xlsx *.xls *.parquet *.db *.sqlite *.sqlite3 *.xml *.yaml *.yml *.html *.gz *.zip);;"
    "Jadval (*.csv *.tsv *.xlsx *.xls *.parquet);;"
    "Log va matn (*.log *.txt *.out *.err);;"
    "JSON (*.json *.jsonl *.ndjson);;"
    "Baza (*.db *.sqlite *.sqlite3);;"
    "Barcha fayllar (*.*)"
)


class ImportPage(BasePage):
    title = "Ma'lumot yuklash"
    subtitle = ("Istalgan manbadan o'qing: log fayllar, CSV/Excel/Parquet, JSON, "
                "SQLite, papkadagi ko'p fayl, internet (HTTP API) yoki to'g'ridan-to'g'ri matn.")

    def __init__(self, store, parent=None) -> None:
        super().__init__(store, parent)
        self._build()
        store.datasets_changed.connect(self._refresh_list)

    # ------------------------------------------------------------------ UI --
    def _build(self) -> None:
        root = QVBoxLayout(self)
        root.setContentsMargins(20, 18, 20, 18)
        root.setSpacing(14)
        root.addWidget(PageHeader(self.title, self.subtitle))

        split = QSplitter(Qt.Orientation.Horizontal)
        split.setChildrenCollapsible(False)

        # ---- chap: manbalar
        left = QWidget()
        lv = QVBoxLayout(left)
        lv.setContentsMargins(0, 0, 0, 0)
        lv.setSpacing(12)

        tabs = QTabWidget()
        tabs.addTab(self._tab_file(), "Fayl")
        tabs.addTab(self._tab_folder(), "Papka")
        tabs.addTab(self._tab_url(), "Internet")
        tabs.addTab(self._tab_db(), "Baza")
        tabs.addTab(self._tab_text(), "Matn")
        tabs.addTab(self._tab_samples(), "Namunalar")
        lv.addWidget(tabs)

        self.status = QLabel("Manbani tanlang va yuklang.")
        self.status.setObjectName("Hint")
        self.status.setWordWrap(True)
        lv.addWidget(self.status)
        split.addWidget(left)

        # ---- o'ng: yuklanganlar
        right = QWidget()
        rv = QVBoxLayout(right)
        rv.setContentsMargins(0, 0, 0, 0)
        rv.setSpacing(12)

        card = Card("Yuklangan jadvallar", "faol jadvalni tanlang")
        self.dataset_list = QListWidget()
        self.dataset_list.setObjectName("DatasetList")
        self.dataset_list.setMinimumHeight(180)
        self.dataset_list.currentItemChanged.connect(self._on_select)
        card.add(self.dataset_list)

        row = QHBoxLayout()
        row.addWidget(make_button("Nomini o'zgartirish", "Ghost", self._rename))
        row.addWidget(make_button("Eksport…", "Ghost", self._export))
        row.addWidget(make_button("O'chirish", "Danger", self._remove))
        row.addStretch(1)
        card.add_layout(row)
        rv.addWidget(card)

        prev = Card("Ko'rib chiqish", "birinchi 100 qator")
        self.preview = FrameTable(editable=False)
        self.preview.setMinimumHeight(240)
        prev.add(self.preview)
        self.meta_label = QLabel("")
        self.meta_label.setObjectName("Hint")
        self.meta_label.setWordWrap(True)
        prev.add(self.meta_label)
        rv.addWidget(prev, 1)
        split.addWidget(right)

        split.setSizes([420, 700])
        root.addWidget(split, 1)
        self._refresh_list()

    # ---- tab: fayl
    def _tab_file(self) -> QWidget:
        w = QWidget()
        lay = QVBoxLayout(w)
        lay.setContentsMargins(14, 14, 14, 14)
        lay.setSpacing(10)

        lay.addWidget(QLabel("Fayl yo'li:"))
        row = QHBoxLayout()
        self.file_path = QLineEdit()
        self.file_path.setPlaceholderText("C:\\loglar\\access.log")
        row.addWidget(self.file_path, 1)
        row.addWidget(make_button("Tanlash…", "Ghost", self._browse_file))
        lay.addLayout(row)

        grid = QGridLayout()
        grid.setHorizontalSpacing(10)
        grid.addWidget(QLabel("Format:"), 0, 0)
        self.file_format = QComboBox()
        self.file_format.addItems(["avtomatik", "csv", "json", "excel", "parquet",
                                   "sqlite", "xml", "yaml", "html"])
        grid.addWidget(self.file_format, 0, 1)
        grid.addWidget(QLabel("Ajratgich:"), 1, 0)
        self.file_delim = QComboBox()
        self.file_delim.addItems(["avtomatik", ",", ";", "TAB", "|", "bo'shliq"])
        grid.addWidget(self.file_delim, 1, 1)
        grid.addWidget(QLabel("Maks. qator:"), 2, 0)
        self.file_nrows = QSpinBox()
        self.file_nrows.setRange(0, 50_000_000)
        self.file_nrows.setValue(0)
        self.file_nrows.setSpecialValueText("cheklovsiz")
        self.file_nrows.setSingleStep(10_000)
        grid.addWidget(self.file_nrows, 2, 1)
        grid.setColumnStretch(1, 1)
        lay.addLayout(grid)

        self.file_types = make_checkbox("Turlarni avtomatik aniqlash", True)
        lay.addWidget(self.file_types)
        lay.addWidget(make_button("Yuklash", "Primary", self._load_file))
        lay.addStretch(1)
        return w

    # ---- tab: papka
    def _tab_folder(self) -> QWidget:
        w = QWidget()
        lay = QVBoxLayout(w)
        lay.setContentsMargins(14, 14, 14, 14)
        lay.setSpacing(10)
        lay.addWidget(QLabel("Papka:"))
        row = QHBoxLayout()
        self.folder_path = QLineEdit()
        self.folder_path.setPlaceholderText("C:\\loglar")
        row.addWidget(self.folder_path, 1)
        row.addWidget(make_button("Tanlash…", "Ghost", self._browse_folder))
        lay.addLayout(row)
        lay.addWidget(QLabel("Fayl namunasi (glob):"))
        self.folder_pattern = QLineEdit("*.log")
        lay.addWidget(self.folder_pattern)
        self.folder_recursive = make_checkbox("Ichki papkalarni ham qidirish", True)
        lay.addWidget(self.folder_recursive)
        hint = QLabel("Barcha fayllar bitta jadvalga birlashtiriladi, "
                      "manba nomi '_source' ustuniga yoziladi.")
        hint.setObjectName("Hint")
        hint.setWordWrap(True)
        lay.addWidget(hint)
        lay.addWidget(make_button("Yuklash", "Primary", self._load_folder))
        lay.addStretch(1)
        return w

    # ---- tab: internet
    def _tab_url(self) -> QWidget:
        w = QWidget()
        lay = QVBoxLayout(w)
        lay.setContentsMargins(14, 14, 14, 14)
        lay.setSpacing(10)
        lay.addWidget(QLabel("URL manzil:"))
        self.url_input = QLineEdit()
        self.url_input.setPlaceholderText("https://api.example.com/logs.json")
        lay.addWidget(self.url_input)
        lay.addWidget(QLabel("Qo'shimcha sarlavhalar (har qatorda Key: Value):"))
        self.url_headers = QPlainTextEdit()
        self.url_headers.setPlaceholderText("Authorization: Bearer …")
        self.url_headers.setFixedHeight(76)
        lay.addWidget(self.url_headers)
        hint = QLabel("JSON API, CSV, HTML jadval yoki oddiy log — format javob turiga "
                      "qarab avtomatik aniqlanadi.")
        hint.setObjectName("Hint")
        hint.setWordWrap(True)
        lay.addWidget(hint)
        lay.addWidget(make_button("Yuklab olish", "Primary", self._load_url))
        lay.addStretch(1)
        return w

    # ---- tab: baza
    def _tab_db(self) -> QWidget:
        w = QWidget()
        lay = QVBoxLayout(w)
        lay.setContentsMargins(14, 14, 14, 14)
        lay.setSpacing(10)
        lay.addWidget(QLabel("SQLite fayli:"))
        row = QHBoxLayout()
        self.db_path = QLineEdit()
        row.addWidget(self.db_path, 1)
        row.addWidget(make_button("Tanlash…", "Ghost", self._browse_db))
        lay.addLayout(row)
        lay.addWidget(QLabel("Jadval:"))
        self.db_table = QComboBox()
        self.db_table.setEditable(False)
        lay.addWidget(self.db_table)
        lay.addWidget(QLabel("Yoki SQL so'rov:"))
        self.db_query = QPlainTextEdit()
        self.db_query.setPlaceholderText("SELECT * FROM events WHERE level='ERROR'")
        self.db_query.setFixedHeight(88)
        lay.addWidget(self.db_query)
        lay.addWidget(make_button("Yuklash", "Primary", self._load_db))
        lay.addStretch(1)
        return w

    # ---- tab: matn
    def _tab_text(self) -> QWidget:
        w = QWidget()
        lay = QVBoxLayout(w)
        lay.setContentsMargins(14, 14, 14, 14)
        lay.setSpacing(10)
        lay.addWidget(QLabel("Matnni shu yerga joylang (log, CSV, JSON):"))
        self.text_input = QPlainTextEdit()
        self.text_input.setPlaceholderText(
            "2024-05-01 12:00:01 - api - ERROR - DB ulanishi uzildi\n…")
        self.text_input.setMinimumHeight(220)
        lay.addWidget(self.text_input, 1)
        row = QHBoxLayout()
        row.addWidget(make_button("Buferdan qo'yish", "Ghost", self._paste))
        row.addWidget(make_button("Yuklash", "Primary", self._load_text))
        row.addStretch(1)
        lay.addLayout(row)
        return w

    # ---- tab: namunalar
    def _tab_samples(self) -> QWidget:
        w = QWidget()
        lay = QVBoxLayout(w)
        lay.setContentsMargins(14, 14, 14, 14)
        lay.setSpacing(10)
        info = QLabel("Dasturni sinab ko'rish uchun tayyor demo ma'lumotlar:")
        info.setObjectName("Hint")
        info.setWordWrap(True)
        lay.addWidget(info)

        self.sample_list = QListWidget()
        self.sample_list.setMinimumHeight(220)
        lay.addWidget(self.sample_list, 1)

        row = QHBoxLayout()
        row.addWidget(make_button("Namunalarni yaratish", "Ghost", self._make_samples))
        row.addWidget(make_button("Yuklash", "Primary", self._load_sample))
        row.addStretch(1)
        lay.addLayout(row)
        self._refresh_samples()
        return w

    # -------------------------------------------------------------- amallar --
    def _busy(self, text: str) -> None:
        self.status.setText(text)
        self.status.setStyleSheet("color:#4C9AFF;")

    def _done(self, res) -> None:
        if isinstance(res, ingest.LoadResult):
            self.store.add(res.name, res.df, meta={
                "source": res.source, "kind": res.kind, **res.meta})
            self.status.setText(f"✓ {res.summary}")
            self.status.setStyleSheet("color:#34D399;")
        self._refresh_list()

    def _fail(self, msg: str) -> None:
        first = msg.strip().splitlines()[0] if msg.strip() else "noma'lum xato"
        self.status.setText(f"✕ Xato: {first}")
        self.status.setStyleSheet("color:#F87171;")
        self.notify(f"Yuklash xatosi: {first}", "error")

    def _run(self, fn, *args, **kwargs) -> None:
        self._busy("Yuklanmoqda…")
        run_async(fn, *args, on_done=self._done, on_error=self._fail, **kwargs)

    def _browse_file(self) -> None:
        path, _ = QFileDialog.getOpenFileName(self, "Fayl tanlang", "", FILE_FILTER)
        if path:
            self.file_path.setText(path)

    def _browse_folder(self) -> None:
        path = QFileDialog.getExistingDirectory(self, "Papka tanlang")
        if path:
            self.folder_path.setText(path)

    def _browse_db(self) -> None:
        path, _ = QFileDialog.getOpenFileName(
            self, "SQLite bazasi", "", "SQLite (*.db *.sqlite *.sqlite3);;Barchasi (*.*)")
        if path:
            self.db_path.setText(path)
            try:
                self.db_table.clear()
                self.db_table.addItems(ingest.sqlite_tables(path))
            except Exception as exc:
                self._fail(str(exc))

    def _load_file(self) -> None:
        path = self.file_path.text().strip().strip('"')
        if not path:
            self._fail("Fayl yo'li kiritilmagan")
            return
        opts = {}
        fmt = self.file_format.currentText()
        if fmt != "avtomatik":
            opts["force"] = fmt
        delim = self.file_delim.currentText()
        if delim != "avtomatik":
            opts["delimiter"] = {"TAB": "\t", "bo'shliq": " "}.get(delim, delim)
        if self.file_nrows.value():
            opts["nrows"] = self.file_nrows.value()
        self._run(ingest.load_file, path, **opts)

    def _load_folder(self) -> None:
        path = self.folder_path.text().strip().strip('"')
        if not path:
            self._fail("Papka tanlanmagan")
            return
        self._run(ingest.load_folder, path,
                  pattern=self.folder_pattern.text().strip() or "*",
                  recursive=self.folder_recursive.isChecked())

    def _load_url(self) -> None:
        url = self.url_input.text().strip()
        if not url:
            self._fail("URL kiritilmagan")
            return
        headers = {}
        for line in self.url_headers.toPlainText().splitlines():
            if ":" in line:
                k, v = line.split(":", 1)
                headers[k.strip()] = v.strip()
        self._run(ingest.load_url, url, headers=headers or None)

    def _load_db(self) -> None:
        path = self.db_path.text().strip().strip('"')
        if not path:
            self._fail("Baza fayli tanlanmagan")
            return
        query = self.db_query.toPlainText().strip()
        self._run(ingest.load_sqlite, path,
                  table=self.db_table.currentText() or None,
                  query=query or None)

    def _paste(self) -> None:
        from PySide6.QtGui import QGuiApplication

        self.text_input.setPlainText(QGuiApplication.clipboard().text())

    def _load_text(self) -> None:
        text = self.text_input.toPlainText()
        if not text.strip():
            self._fail("Matn bo'sh")
            return
        name, ok = QInputDialog.getText(self, "Jadval nomi", "Nom:", text="matn")
        if not ok:
            return
        self._run(ingest.load_text, text, name=name or "matn", source="<matn>")

    def _refresh_samples(self) -> None:
        self.sample_list.clear()
        if not SAMPLES_DIR.exists():
            return
        for p in sorted(SAMPLES_DIR.iterdir()):
            if p.suffix.lower() in (".py", ".pyc") or p.is_dir():
                continue
            size = p.stat().st_size / 1024
            item = QListWidgetItem(f"{p.name}   ·   {size:,.0f} KB")
            item.setData(Qt.ItemDataRole.UserRole, str(p))
            self.sample_list.addItem(item)

    def _make_samples(self) -> None:
        def build():
            import sys

            sys.path.insert(0, str(SAMPLES_DIR.parent))
            from samples.generate_samples import generate_all

            return generate_all(verbose=False)

        self._busy("Namunalar yaratilmoqda…")
        run_async(build,
                  on_done=lambda _: (self._refresh_samples(),
                                     self.status.setText("✓ Namunalar tayyor")),
                  on_error=self._fail)

    def _load_sample(self) -> None:
        item = self.sample_list.currentItem()
        if item is None:
            self._fail("Namuna tanlanmagan")
            return
        self._run(ingest.load_file, item.data(Qt.ItemDataRole.UserRole))

    # ------------------------------------------------------------- ro'yxat --
    def _refresh_list(self) -> None:
        current = self.store.active_name
        self.dataset_list.blockSignals(True)
        self.dataset_list.clear()
        for name in self.store.names:
            df = self.store.get(name)
            item = QListWidgetItem(f"{name}\n{len(df):,} qator · {df.shape[1]} ustun")
            item.setData(Qt.ItemDataRole.UserRole, name)
            self.dataset_list.addItem(item)
            if name == current:
                self.dataset_list.setCurrentItem(item)
        self.dataset_list.blockSignals(False)
        self._update_preview()

    def _on_select(self, item, _prev=None) -> None:
        if item:
            self.store.set_active(item.data(Qt.ItemDataRole.UserRole))
            self._update_preview()

    def _update_preview(self) -> None:
        df = self.df
        if df.empty:
            self.preview.set_df(pd.DataFrame())
            self.meta_label.setText("")
            return
        self.preview.set_df(df.head(100))
        meta = self.store.meta()
        bits = [f"<b>{self.store.active_name}</b>",
                f"{len(df):,} qator × {df.shape[1]} ustun",
                f"{ingest.memory_usage_mb(df):.2f} MB"]
        if meta.get("format"):
            bits.append(str(meta["format"]))
        if meta.get("source"):
            bits.append(f"manba: {Path(str(meta['source'])).name}")
        if meta.get("confidence"):
            bits.append(f"ishonch: {float(meta['confidence']):.0%}")
        self.meta_label.setText(" · ".join(bits))

    def refresh(self) -> None:
        self._refresh_list()

    # ---- jadval boshqaruvi
    def _rename(self) -> None:
        name = self.store.active_name
        if not name:
            return
        new, ok = QInputDialog.getText(self, "Nomni o'zgartirish", "Yangi nom:", text=name)
        if ok and new.strip():
            self.store.rename(name, new.strip())

    def _remove(self) -> None:
        name = self.store.active_name
        if name:
            self.store.remove(name)
            self.notify(f"'{name}' o'chirildi", "info")

    def _export(self) -> None:
        df = self.df
        if df.empty:
            self.notify("Eksport uchun ma'lumot yo'q", "warn")
            return
        path, _ = QFileDialog.getSaveFileName(
            self, "Eksport", f"{self.store.active_name}.csv",
            "CSV (*.csv);;Excel (*.xlsx);;Parquet (*.parquet);;JSON (*.json);;"
            "JSON Lines (*.jsonl);;SQLite (*.db);;HTML (*.html);;Markdown (*.md)")
        if not path:
            return
        try:
            ingest.export_df(df, path)
            self.notify(f"Saqlandi: {path}", "success")
        except Exception as exc:
            self.notify(f"Eksport xatosi: {exc}", "error")
