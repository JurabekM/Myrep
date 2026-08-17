"""Data import page — file, folder, internet, database, text, samples."""
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
    "All supported (*.csv *.tsv *.txt *.log *.json *.jsonl *.ndjson "
    "*.xlsx *.xls *.parquet *.db *.sqlite *.sqlite3 *.xml *.yaml *.yml *.html *.gz *.zip);;"
    "Tabular (*.csv *.tsv *.xlsx *.xls *.parquet);;"
    "Logs and text (*.log *.txt *.out *.err);;"
    "JSON (*.json *.jsonl *.ndjson);;"
    "Database (*.db *.sqlite *.sqlite3);;"
    "All files (*.*)"
)


class ImportPage(BasePage):
    title = "Import data"
    subtitle = ("Read from any source: log files, CSV/Excel/Parquet, JSON, SQLite, "
                "a folder full of files, the internet (HTTP API) or raw pasted text.")

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

        # ---- left: sources
        left = QWidget()
        lv = QVBoxLayout(left)
        lv.setContentsMargins(0, 0, 0, 0)
        lv.setSpacing(12)

        tabs = QTabWidget()
        tabs.addTab(self._tab_file(), "File")
        tabs.addTab(self._tab_folder(), "Folder")
        tabs.addTab(self._tab_url(), "Internet")
        tabs.addTab(self._tab_db(), "Database")
        tabs.addTab(self._tab_text(), "Text")
        tabs.addTab(self._tab_samples(), "Samples")
        lv.addWidget(tabs)

        self.status = QLabel("Pick a source and load it.")
        self.status.setObjectName("Hint")
        self.status.setWordWrap(True)
        lv.addWidget(self.status)
        split.addWidget(left)

        # ---- right: loaded datasets
        right = QWidget()
        rv = QVBoxLayout(right)
        rv.setContentsMargins(0, 0, 0, 0)
        rv.setSpacing(12)

        card = Card("Loaded tables", "pick the active table")
        self.dataset_list = QListWidget()
        self.dataset_list.setObjectName("DatasetList")
        self.dataset_list.setMinimumHeight(180)
        self.dataset_list.currentItemChanged.connect(self._on_select)
        card.add(self.dataset_list)

        row = QHBoxLayout()
        row.addWidget(make_button("Rename", "Ghost", self._rename))
        row.addWidget(make_button("Export…", "Ghost", self._export))
        row.addWidget(make_button("Remove", "Danger", self._remove))
        row.addStretch(1)
        card.add_layout(row)
        rv.addWidget(card)

        prev = Card("Preview", "first 100 rows")
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

    # ---- tab: file
    def _tab_file(self) -> QWidget:
        w = QWidget()
        lay = QVBoxLayout(w)
        lay.setContentsMargins(14, 14, 14, 14)
        lay.setSpacing(10)

        lay.addWidget(QLabel("File path:"))
        row = QHBoxLayout()
        self.file_path = QLineEdit()
        self.file_path.setPlaceholderText("C:\\logs\\access.log")
        row.addWidget(self.file_path, 1)
        row.addWidget(make_button("Browse…", "Ghost", self._browse_file))
        lay.addLayout(row)

        grid = QGridLayout()
        grid.setHorizontalSpacing(10)
        grid.addWidget(QLabel("Format:"), 0, 0)
        self.file_format = QComboBox()
        self.file_format.addItems(["auto", "csv", "json", "excel", "parquet",
                                   "sqlite", "xml", "yaml", "html"])
        grid.addWidget(self.file_format, 0, 1)
        grid.addWidget(QLabel("Delimiter:"), 1, 0)
        self.file_delim = QComboBox()
        self.file_delim.addItems(["auto", ",", ";", "TAB", "|", "space"])
        grid.addWidget(self.file_delim, 1, 1)
        grid.addWidget(QLabel("Max rows:"), 2, 0)
        self.file_nrows = QSpinBox()
        self.file_nrows.setRange(0, 50_000_000)
        self.file_nrows.setValue(0)
        self.file_nrows.setSpecialValueText("unlimited")
        self.file_nrows.setSingleStep(10_000)
        grid.addWidget(self.file_nrows, 2, 1)
        grid.setColumnStretch(1, 1)
        lay.addLayout(grid)

        self.file_types = make_checkbox("Detect column types automatically", True)
        lay.addWidget(self.file_types)
        lay.addWidget(make_button("Load", "Primary", self._load_file))
        lay.addStretch(1)
        return w

    # ---- tab: folder
    def _tab_folder(self) -> QWidget:
        w = QWidget()
        lay = QVBoxLayout(w)
        lay.setContentsMargins(14, 14, 14, 14)
        lay.setSpacing(10)
        lay.addWidget(QLabel("Folder:"))
        row = QHBoxLayout()
        self.folder_path = QLineEdit()
        self.folder_path.setPlaceholderText("C:\\logs")
        row.addWidget(self.folder_path, 1)
        row.addWidget(make_button("Browse…", "Ghost", self._browse_folder))
        lay.addLayout(row)
        lay.addWidget(QLabel("File pattern (glob):"))
        self.folder_pattern = QLineEdit("*.log")
        lay.addWidget(self.folder_pattern)
        self.folder_recursive = make_checkbox("Search sub-folders too", True)
        lay.addWidget(self.folder_recursive)
        hint = QLabel("All files are merged into one table and the source file name "
                      "is written into the '_source' column.")
        hint.setObjectName("Hint")
        hint.setWordWrap(True)
        lay.addWidget(hint)
        lay.addWidget(make_button("Load", "Primary", self._load_folder))
        lay.addStretch(1)
        return w

    # ---- tab: internet
    def _tab_url(self) -> QWidget:
        w = QWidget()
        lay = QVBoxLayout(w)
        lay.setContentsMargins(14, 14, 14, 14)
        lay.setSpacing(10)
        lay.addWidget(QLabel("URL:"))
        self.url_input = QLineEdit()
        self.url_input.setPlaceholderText("https://api.example.com/logs.json")
        lay.addWidget(self.url_input)
        lay.addWidget(QLabel("Extra headers (one Key: Value per line):"))
        self.url_headers = QPlainTextEdit()
        self.url_headers.setPlaceholderText("Authorization: Bearer …")
        self.url_headers.setFixedHeight(76)
        lay.addWidget(self.url_headers)
        hint = QLabel("JSON API, CSV, HTML table or plain log — the format is detected "
                      "from the response type.")
        hint.setObjectName("Hint")
        hint.setWordWrap(True)
        lay.addWidget(hint)
        lay.addWidget(make_button("Download", "Primary", self._load_url))
        lay.addStretch(1)
        return w

    # ---- tab: database
    def _tab_db(self) -> QWidget:
        w = QWidget()
        lay = QVBoxLayout(w)
        lay.setContentsMargins(14, 14, 14, 14)
        lay.setSpacing(10)
        lay.addWidget(QLabel("SQLite file:"))
        row = QHBoxLayout()
        self.db_path = QLineEdit()
        row.addWidget(self.db_path, 1)
        row.addWidget(make_button("Browse…", "Ghost", self._browse_db))
        lay.addLayout(row)
        lay.addWidget(QLabel("Table:"))
        self.db_table = QComboBox()
        self.db_table.setEditable(False)
        lay.addWidget(self.db_table)
        lay.addWidget(QLabel("Or an SQL query:"))
        self.db_query = QPlainTextEdit()
        self.db_query.setPlaceholderText("SELECT * FROM events WHERE level='ERROR'")
        self.db_query.setFixedHeight(88)
        lay.addWidget(self.db_query)
        lay.addWidget(make_button("Load", "Primary", self._load_db))
        lay.addStretch(1)
        return w

    # ---- tab: text
    def _tab_text(self) -> QWidget:
        w = QWidget()
        lay = QVBoxLayout(w)
        lay.setContentsMargins(14, 14, 14, 14)
        lay.setSpacing(10)
        lay.addWidget(QLabel("Paste your text here (log, CSV, JSON):"))
        self.text_input = QPlainTextEdit()
        self.text_input.setPlaceholderText(
            "2024-05-01 12:00:01 - api - ERROR - database connection lost\n…")
        self.text_input.setMinimumHeight(220)
        lay.addWidget(self.text_input, 1)
        row = QHBoxLayout()
        row.addWidget(make_button("Paste from clipboard", "Ghost", self._paste))
        row.addWidget(make_button("Load", "Primary", self._load_text))
        row.addStretch(1)
        lay.addLayout(row)
        return w

    # ---- tab: samples
    def _tab_samples(self) -> QWidget:
        w = QWidget()
        lay = QVBoxLayout(w)
        lay.setContentsMargins(14, 14, 14, 14)
        lay.setSpacing(10)
        info = QLabel("Ready-made demo data for trying the application out:")
        info.setObjectName("Hint")
        info.setWordWrap(True)
        lay.addWidget(info)

        self.sample_list = QListWidget()
        self.sample_list.setMinimumHeight(220)
        lay.addWidget(self.sample_list, 1)

        row = QHBoxLayout()
        row.addWidget(make_button("Generate samples", "Ghost", self._make_samples))
        row.addWidget(make_button("Load", "Primary", self._load_sample))
        row.addStretch(1)
        lay.addLayout(row)
        self._refresh_samples()
        return w

    # ------------------------------------------------------------- actions --
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
        first = msg.strip().splitlines()[0] if msg.strip() else "unknown error"
        self.status.setText(f"✕ Error: {first}")
        self.status.setStyleSheet("color:#F87171;")
        self.notify(f"Import error: {first}", "error")

    def _run(self, fn, *args, **kwargs) -> None:
        self._busy("Loading…")
        run_async(fn, *args, on_done=self._done, on_error=self._fail, **kwargs)

    def _browse_file(self) -> None:
        path, _ = QFileDialog.getOpenFileName(self, "Choose a file", "", FILE_FILTER)
        if path:
            self.file_path.setText(path)

    def _browse_folder(self) -> None:
        path = QFileDialog.getExistingDirectory(self, "Choose a folder")
        if path:
            self.folder_path.setText(path)

    def _browse_db(self) -> None:
        path, _ = QFileDialog.getOpenFileName(
            self, "SQLite database", "", "SQLite (*.db *.sqlite *.sqlite3);;All files (*.*)")
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
            self._fail("No file path was entered")
            return
        opts = {}
        fmt = self.file_format.currentText()
        if fmt != "auto":
            opts["force"] = fmt
        delim = self.file_delim.currentText()
        if delim != "auto":
            opts["delimiter"] = {"TAB": "\t", "space": " "}.get(delim, delim)
        if self.file_nrows.value():
            opts["nrows"] = self.file_nrows.value()
        self._run(ingest.load_file, path, **opts)

    def _load_folder(self) -> None:
        path = self.folder_path.text().strip().strip('"')
        if not path:
            self._fail("No folder was selected")
            return
        self._run(ingest.load_folder, path,
                  pattern=self.folder_pattern.text().strip() or "*",
                  recursive=self.folder_recursive.isChecked())

    def _load_url(self) -> None:
        url = self.url_input.text().strip()
        if not url:
            self._fail("No URL was entered")
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
            self._fail("No database file was selected")
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
            self._fail("The text is empty")
            return
        name, ok = QInputDialog.getText(self, "Table name", "Name:", text="text")
        if not ok:
            return
        self._run(ingest.load_text, text, name=name or "text", source="<text>")

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

        self._busy("Generating samples…")
        run_async(build,
                  on_done=lambda _: (self._refresh_samples(),
                                     self.status.setText("✓ Samples are ready")),
                  on_error=self._fail)

    def _load_sample(self) -> None:
        item = self.sample_list.currentItem()
        if item is None:
            self._fail("No sample was selected")
            return
        self._run(ingest.load_file, item.data(Qt.ItemDataRole.UserRole))

    # -------------------------------------------------------------- listing --
    def _refresh_list(self) -> None:
        current = self.store.active_name
        self.dataset_list.blockSignals(True)
        self.dataset_list.clear()
        for name in self.store.names:
            df = self.store.get(name)
            item = QListWidgetItem(f"{name}\n{len(df):,} rows · {df.shape[1]} columns")
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
                f"{len(df):,} rows × {df.shape[1]} columns",
                f"{ingest.memory_usage_mb(df):.2f} MB"]
        if meta.get("format"):
            bits.append(str(meta["format"]))
        if meta.get("source"):
            bits.append(f"source: {Path(str(meta['source'])).name}")
        if meta.get("confidence"):
            bits.append(f"confidence: {float(meta['confidence']):.0%}")
        self.meta_label.setText(" · ".join(bits))

    def refresh(self) -> None:
        self._refresh_list()

    # ---- dataset management
    def _rename(self) -> None:
        name = self.store.active_name
        if not name:
            return
        new, ok = QInputDialog.getText(self, "Rename", "New name:", text=name)
        if ok and new.strip():
            self.store.rename(name, new.strip())

    def _remove(self) -> None:
        name = self.store.active_name
        if name:
            self.store.remove(name)
            self.notify(f"'{name}' removed", "info")

    def _export(self) -> None:
        df = self.df
        if df.empty:
            self.notify("There is nothing to export", "warn")
            return
        path, _ = QFileDialog.getSaveFileName(
            self, "Export", f"{self.store.active_name}.csv",
            "CSV (*.csv);;Excel (*.xlsx);;Parquet (*.parquet);;JSON (*.json);;"
            "JSON Lines (*.jsonl);;SQLite (*.db);;HTML (*.html);;Markdown (*.md)")
        if not path:
            return
        try:
            ingest.export_df(df, path)
            self.notify(f"Saved: {path}", "success")
        except Exception as exc:
            self.notify(f"Export error: {exc}", "error")
