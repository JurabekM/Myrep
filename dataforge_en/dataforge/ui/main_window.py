"""Main window — sidebar, pages, menu bar and status bar."""
from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtGui import QAction, QKeySequence
from PySide6.QtWidgets import (QApplication, QButtonGroup, QComboBox, QFileDialog,
                               QHBoxLayout, QLabel, QMainWindow, QMessageBox,
                               QPushButton, QStackedWidget, QVBoxLayout, QWidget)

from ..config import APP_NAME, PALETTE, PROJECTS_DIR, VERSION
from ..core import project as project_mod
from .pages.chart_page import ChartPage
from .pages.import_page import ImportPage
from .pages.logai_page import LogAIPage
from .pages.ml_page import MLPage
from .pages.profile_page import ProfilePage
from .pages.report_page import ReportPage
from .pages.table_page import TablePage
from .pages.transform_page import TransformPage
from .store import DataStore
from .theme import QSS
from .widgets import Toast, WheelGuard

NAV = [
    ("DATA", [
        ("Import", "import"),
        ("Table", "table"),
        ("Transform", "transform"),
    ]),
    ("ANALYSIS", [
        ("Profile", "profile"),
        ("Charts", "chart"),
    ]),
    ("INTELLIGENCE", [
        ("ML Studio", "ml"),
        ("Log AI", "logai"),
    ]),
    ("OUTPUT", [
        ("Report", "report"),
    ]),
]


class MainWindow(QMainWindow):
    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle(f"{APP_NAME} v{VERSION}")
        self.resize(1500, 940)
        self.setMinimumSize(1160, 720)
        self.setStyleSheet(QSS)

        self.store = DataStore(self)
        self.pages: dict[str, QWidget] = {}
        self._wheel_guard = WheelGuard(self)
        app = QApplication.instance()
        if app is not None:
            app.installEventFilter(self._wheel_guard)
        self._build()
        self.store.message.connect(self._on_message)
        self.store.datasets_changed.connect(self._refresh_dataset_combo)
        self.store.active_changed.connect(lambda _: self._refresh_dataset_combo())
        self.store.data_changed.connect(self._update_status)

    # -------------------------------------------------------------- UI ----
    def _build(self) -> None:
        central = QWidget()
        root = QHBoxLayout(central)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        root.addWidget(self._sidebar())

        right = QWidget()
        rv = QVBoxLayout(right)
        rv.setContentsMargins(0, 0, 0, 0)
        rv.setSpacing(0)
        rv.addWidget(self._topbar())

        self.stack = QStackedWidget()
        chart_page = ChartPage(self.store)
        ml_page = MLPage(self.store)
        self.pages = {
            "import": ImportPage(self.store),
            "table": TablePage(self.store),
            "transform": TransformPage(self.store),
            "profile": ProfilePage(self.store),
            "chart": chart_page,
            "ml": ml_page,
            "logai": LogAIPage(self.store),
            "report": ReportPage(self.store, chart_page=chart_page, ml_page=ml_page),
        }
        for page in self.pages.values():
            self.stack.addWidget(page)
        rv.addWidget(self.stack, 1)
        root.addWidget(right, 1)

        self.setCentralWidget(central)
        self._menubar()
        self._statusbar()
        self.toast = Toast(self)
        self._go("import")

    def _sidebar(self) -> QWidget:
        bar = QWidget()
        bar.setObjectName("Sidebar")
        bar.setFixedWidth(212)
        lay = QVBoxLayout(bar)
        lay.setContentsMargins(0, 0, 0, 12)
        lay.setSpacing(0)

        brand = QLabel("◆ DataForge")
        brand.setObjectName("Brand")
        sub = QLabel("Pro · Data Intelligence")
        sub.setObjectName("BrandSub")
        lay.addWidget(brand)
        lay.addWidget(sub)

        self.nav_group = QButtonGroup(self)
        self.nav_group.setExclusive(True)
        self.nav_buttons: dict[str, QPushButton] = {}
        for section, items in NAV:
            label = QLabel(section)
            label.setObjectName("NavSection")
            lay.addWidget(label)
            for text, key in items:
                btn = QPushButton(text)
                btn.setObjectName("NavButton")
                btn.setCheckable(True)
                btn.setCursor(Qt.CursorShape.PointingHandCursor)
                btn.clicked.connect(lambda _=False, k=key: self._go(k))
                self.nav_group.addButton(btn)
                self.nav_buttons[key] = btn
                lay.addWidget(btn)

        lay.addStretch(1)
        version = QLabel(f"v{VERSION}")
        version.setObjectName("BrandSub")
        lay.addWidget(version)
        return bar

    def _topbar(self) -> QWidget:
        bar = QWidget()
        bar.setFixedHeight(52)
        bar.setObjectName("TopBar")
        bar.setStyleSheet(
            f"#TopBar {{ background:{PALETTE['surface']};"
            f" border-bottom:1px solid {PALETTE['border']}; }}")
        lay = QHBoxLayout(bar)
        lay.setContentsMargins(18, 8, 18, 8)
        lay.setSpacing(10)

        lbl = QLabel("Active table:")
        lbl.setObjectName("Hint")
        lay.addWidget(lbl)
        self.dataset_combo = QComboBox()
        self.dataset_combo.setMinimumWidth(230)
        self.dataset_combo.currentTextChanged.connect(self._on_dataset_selected)
        lay.addWidget(self.dataset_combo)

        for text, tip, slot in (
            ("↶", "Undo (Ctrl+Z)", self.store.undo),
            ("↷", "Redo (Ctrl+Y)", self.store.redo),
        ):
            b = QPushButton(text)
            b.setObjectName("Ghost")
            b.setFixedWidth(38)
            b.setToolTip(tip)
            b.clicked.connect(slot)
            lay.addWidget(b)

        lay.addStretch(1)
        self.shape_label = QLabel("")
        self.shape_label.setObjectName("Hint")
        lay.addWidget(self.shape_label)
        return bar

    def _menubar(self) -> None:
        mb = self.menuBar()

        m_file = mb.addMenu("&File")
        self._act(m_file, "Import data…", "Ctrl+O", lambda: self._go("import"))
        self._act(m_file, "Save project…", "Ctrl+S", self._save_project)
        self._act(m_file, "Open project…", "Ctrl+Shift+O", self._open_project)
        m_file.addSeparator()
        self._act(m_file, "Export data…", "Ctrl+E", self._export)
        m_file.addSeparator()
        self._act(m_file, "Quit", "Ctrl+Q", self.close)

        m_edit = mb.addMenu("&Edit")
        self._act(m_edit, "Undo", "Ctrl+Z", self.store.undo)
        self._act(m_edit, "Redo", "Ctrl+Y", self.store.redo)
        m_edit.addSeparator()
        self._act(m_edit, "Remove the active table", "",
                  lambda: self.store.remove(self.store.active_name or ""))
        self._act(m_edit, "Clear everything", "", self._clear_all)

        m_view = mb.addMenu("&View")
        for i, (_, items) in enumerate(NAV):
            for text, key in items:
                self._act(m_view, text, f"Ctrl+{len(m_view.actions()) + 1}",
                          lambda k=key: self._go(k))

        m_help = mb.addMenu("&Help")
        self._act(m_help, "Quick guide", "F1", self._show_help)
        self._act(m_help, "About", "", self._show_about)

    def _act(self, menu, text: str, shortcut: str, slot) -> QAction:
        act = QAction(text, self)
        if shortcut:
            act.setShortcut(QKeySequence(shortcut))
        act.triggered.connect(lambda: slot())
        menu.addAction(act)
        return act

    def _statusbar(self) -> None:
        sb = self.statusBar()
        self.status_label = QLabel("Ready")
        sb.addWidget(self.status_label, 1)
        self.mem_label = QLabel("")
        sb.addPermanentWidget(self.mem_label)

    # ---------------------------------------------------------- actions ---
    def _go(self, key: str) -> None:
        page = self.pages.get(key)
        if page is None:
            return
        self.stack.setCurrentWidget(page)
        btn = self.nav_buttons.get(key)
        if btn:
            btn.setChecked(True)

    def _on_message(self, text: str, level: str) -> None:
        self.toast.show_message(text, level)
        self.status_label.setText(text)

    def _refresh_dataset_combo(self) -> None:
        self.dataset_combo.blockSignals(True)
        self.dataset_combo.clear()
        self.dataset_combo.addItems(self.store.names)
        if self.store.active_name:
            i = self.dataset_combo.findText(self.store.active_name)
            if i >= 0:
                self.dataset_combo.setCurrentIndex(i)
        self.dataset_combo.blockSignals(False)
        self._update_status()

    def _on_dataset_selected(self, name: str) -> None:
        if name:
            self.store.set_active(name)

    def _update_status(self) -> None:
        df = self.store.df()
        if df.empty:
            self.shape_label.setText("no data")
            self.mem_label.setText("")
            return
        mem = df.memory_usage(deep=True).sum() / 1024 / 1024
        self.shape_label.setText(f"{len(df):,} rows × {df.shape[1]} columns")
        self.mem_label.setText(f"{mem:.1f} MB · {len(self.store.names)} tables")

    # ---------------------------------------------------------- project ---
    def _save_project(self) -> None:
        if self.store.is_empty:
            self._on_message("There is nothing to save", "warn")
            return
        path, _ = QFileDialog.getSaveFileName(
            self, "Save the project", str(PROJECTS_DIR / "project.dfp"),
            "DataForge project (*.dfp)")
        if not path:
            return
        try:
            data = {n: self.store.get(n) for n in self.store.names}
            hist = {n: (self.store.history(n).labels() if self.store.history(n) else [])
                    for n in self.store.names}
            out = project_mod.save_project(path, data, active=self.store.active_name,
                                           histories=hist)
            self._on_message(f"Project saved: {out}", "success")
        except Exception as exc:
            self._on_message(f"Save error: {exc}", "error")

    def _open_project(self) -> None:
        path, _ = QFileDialog.getOpenFileName(
            self, "Open a project", str(PROJECTS_DIR),
            "DataForge project (*.dfp);;All files (*.*)")
        if not path:
            return
        try:
            datasets, meta = project_mod.load_project(path)
        except Exception as exc:
            self._on_message(f"Could not open it: {exc}", "error")
            return
        self.store.clear()
        for name, df in datasets.items():
            self.store.add(name, df, activate=False)
        active = meta.get("active")
        if active in datasets:
            self.store.set_active(active)
        elif datasets:
            self.store.set_active(next(iter(datasets)))
        self._on_message(f"Project opened: {Path(path).name} "
                         f"({len(datasets)} tables)", "success")

    def _export(self) -> None:
        self._go("report")
        self.pages["report"]._export_data()

    def _clear_all(self) -> None:
        if QMessageBox.question(self, "Confirm",
                                "Remove every loaded table?") \
                == QMessageBox.StandardButton.Yes:
            self.store.clear()
            self._on_message("Everything was cleared", "info")

    # -------------------------------------------------------------- help --
    def _show_help(self) -> None:
        text = """
<h3>DataForge Pro — quick guide</h3>
<p><b>1. Import</b> — read from a file, a folder, the internet (URL), a SQLite
database, raw text or the bundled samples. The log format is detected
automatically (Apache, syslog, Python logging, JSON Lines, logfmt and more).</p>
<p><b>2. Table</b> — double-click a cell to edit it, search, and right-click a
column header to reach the column operations.</p>
<p><b>3. Transform</b> — 30+ operations: filtering, cleaning, string operations,
derived columns (expressions), encoding, grouping, pivoting. Everything is undoable.</p>
<p><b>4. Profile</b> — per-column statistics, quality issues, correlation,
grouping and time analysis.</p>
<p><b>5. Charts</b> — 25 chart types. The «Add to report» button puts a chart into
the report gallery.</p>
<p><b>6. ML Studio</b> — AutoML (model leaderboard), clustering, anomaly detection,
PCA/t-SNE, time series forecasting, saving and applying models.</p>
<p><b>7. Log AI</b> — template mining, rare events, bursts, text clustering and
extraction of entities such as IP/URL/UUID.</p>
<p><b>8. Report</b> — collects everything into one self-contained HTML file.</p>
<p><b>Shortcuts:</b> Ctrl+O import · Ctrl+S project · Ctrl+Z undo ·
Ctrl+Y redo · Ctrl+E export · F1 help</p>
"""
        box = QMessageBox(self)
        box.setWindowTitle("Guide")
        box.setTextFormat(Qt.TextFormat.RichText)
        box.setText(text)
        box.exec()

    def _show_about(self) -> None:
        QMessageBox.about(
            self, f"About {APP_NAME}",
            f"<h3>{APP_NAME} v{VERSION}</h3>"
            "<p>Universal data and log intelligence platform.</p>"
            "<p>Python · PySide6 · pandas · scikit-learn · matplotlib</p>")

    def resizeEvent(self, event) -> None:  # noqa: N802
        super().resizeEvent(event)
        if hasattr(self, "toast") and self.toast.isVisible():
            self.toast._reposition()
