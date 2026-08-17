"""Asosiy oyna — yon menyu, sahifalar, menyu paneli va holat qatori."""
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
    ("MA'LUMOT", [
        ("Yuklash", "import"),
        ("Jadval", "table"),
        ("Tahrirlash", "transform"),
    ]),
    ("TAHLIL", [
        ("Profil", "profile"),
        ("Grafiklar", "chart"),
    ]),
    ("INTELLEKT", [
        ("ML Studio", "ml"),
        ("Log AI", "logai"),
    ]),
    ("NATIJA", [
        ("Hisobot", "report"),
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

        lbl = QLabel("Faol jadval:")
        lbl.setObjectName("Hint")
        lay.addWidget(lbl)
        self.dataset_combo = QComboBox()
        self.dataset_combo.setMinimumWidth(230)
        self.dataset_combo.currentTextChanged.connect(self._on_dataset_selected)
        lay.addWidget(self.dataset_combo)

        for text, tip, slot in (
            ("↶", "Bekor qilish (Ctrl+Z)", self.store.undo),
            ("↷", "Qaytarish (Ctrl+Y)", self.store.redo),
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

        m_file = mb.addMenu("&Fayl")
        self._act(m_file, "Fayl yuklash…", "Ctrl+O", lambda: self._go("import"))
        self._act(m_file, "Loyihani saqlash…", "Ctrl+S", self._save_project)
        self._act(m_file, "Loyihani ochish…", "Ctrl+Shift+O", self._open_project)
        m_file.addSeparator()
        self._act(m_file, "Ma'lumotni eksport…", "Ctrl+E", self._export)
        m_file.addSeparator()
        self._act(m_file, "Chiqish", "Ctrl+Q", self.close)

        m_edit = mb.addMenu("&Tahrir")
        self._act(m_edit, "Bekor qilish", "Ctrl+Z", self.store.undo)
        self._act(m_edit, "Qaytarish", "Ctrl+Y", self.store.redo)
        m_edit.addSeparator()
        self._act(m_edit, "Faol jadvalni o'chirish", "",
                  lambda: self.store.remove(self.store.active_name or ""))
        self._act(m_edit, "Hammasini tozalash", "", self._clear_all)

        m_view = mb.addMenu("&Ko'rinish")
        for i, (_, items) in enumerate(NAV):
            for text, key in items:
                self._act(m_view, text, f"Ctrl+{len(m_view.actions()) + 1}",
                          lambda k=key: self._go(k))

        m_help = mb.addMenu("&Yordam")
        self._act(m_help, "Qisqa qo'llanma", "F1", self._show_help)
        self._act(m_help, "Dastur haqida", "", self._show_about)

    def _act(self, menu, text: str, shortcut: str, slot) -> QAction:
        act = QAction(text, self)
        if shortcut:
            act.setShortcut(QKeySequence(shortcut))
        act.triggered.connect(lambda: slot())
        menu.addAction(act)
        return act

    def _statusbar(self) -> None:
        sb = self.statusBar()
        self.status_label = QLabel("Tayyor")
        sb.addWidget(self.status_label, 1)
        self.mem_label = QLabel("")
        sb.addPermanentWidget(self.mem_label)

    # ---------------------------------------------------------- amallar ---
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
            self.shape_label.setText("ma'lumot yo'q")
            self.mem_label.setText("")
            return
        mem = df.memory_usage(deep=True).sum() / 1024 / 1024
        self.shape_label.setText(f"{len(df):,} qator × {df.shape[1]} ustun")
        self.mem_label.setText(f"{mem:.1f} MB · {len(self.store.names)} jadval")

    # ---------------------------------------------------------- loyiha ----
    def _save_project(self) -> None:
        if self.store.is_empty:
            self._on_message("Saqlash uchun ma'lumot yo'q", "warn")
            return
        path, _ = QFileDialog.getSaveFileName(
            self, "Loyihani saqlash", str(PROJECTS_DIR / "loyiha.dfp"),
            "DataForge loyiha (*.dfp)")
        if not path:
            return
        try:
            data = {n: self.store.get(n) for n in self.store.names}
            hist = {n: (self.store.history(n).labels() if self.store.history(n) else [])
                    for n in self.store.names}
            out = project_mod.save_project(path, data, active=self.store.active_name,
                                           histories=hist)
            self._on_message(f"Loyiha saqlandi: {out}", "success")
        except Exception as exc:
            self._on_message(f"Saqlash xatosi: {exc}", "error")

    def _open_project(self) -> None:
        path, _ = QFileDialog.getOpenFileName(
            self, "Loyihani ochish", str(PROJECTS_DIR),
            "DataForge loyiha (*.dfp);;Barchasi (*.*)")
        if not path:
            return
        try:
            datasets, meta = project_mod.load_project(path)
        except Exception as exc:
            self._on_message(f"Ochilmadi: {exc}", "error")
            return
        self.store.clear()
        for name, df in datasets.items():
            self.store.add(name, df, activate=False)
        active = meta.get("active")
        if active in datasets:
            self.store.set_active(active)
        elif datasets:
            self.store.set_active(next(iter(datasets)))
        self._on_message(f"Loyiha ochildi: {Path(path).name} "
                         f"({len(datasets)} jadval)", "success")

    def _export(self) -> None:
        self._go("report")
        self.pages["report"]._export_data()

    def _clear_all(self) -> None:
        if QMessageBox.question(self, "Tasdiqlash",
                                "Barcha jadvallar o'chirilsinmi?") \
                == QMessageBox.StandardButton.Yes:
            self.store.clear()
            self._on_message("Hammasi tozalandi", "info")

    # ------------------------------------------------------------ yordam --
    def _show_help(self) -> None:
        text = """
<h3>DataForge Pro — qisqa qo'llanma</h3>
<p><b>1. Yuklash</b> — fayl, papka, internet (URL), SQLite bazasi, xom matn yoki
tayyor namunalardan ma'lumot oling. Log formati avtomatik aniqlanadi
(Apache, syslog, Python logging, JSON Lines, logfmt va boshqalar).</p>
<p><b>2. Jadval</b> — kataklarni ikki marta bosib tahrirlang, qidiring,
ustun sarlavhasiga o'ng tugma bilan bosib amallarni chaqiring.</p>
<p><b>3. Tahrirlash</b> — 30 dan ortiq amal: filtr, tozalash, matn amallari,
yangi ustun (ifoda), kodlash, guruhlash, pivot. Har biri bekor qilinadi.</p>
<p><b>4. Profil</b> — har bir ustun statistikasi, sifat muammolari,
korrelyatsiya, guruhlash va vaqt tahlili.</p>
<p><b>5. Grafiklar</b> — 25 xil grafik turi. «Hisobotga qo'shish» tugmasi
grafikni hisobot galereyasiga qo'shadi.</p>
<p><b>6. ML Studio</b> — AutoML (modellar reytingi), klasterlash, anomaliya
deteksiyasi, PCA/t-SNE, vaqt qatori bashorati, model saqlash/qo'llash.</p>
<p><b>7. Log AI</b> — shablon qazish, kam uchraydigan hodisalar, portlashlar,
matn klasterlash, IP/URL/UUID kabi entity'larni ajratish.</p>
<p><b>8. Hisobot</b> — hammasini bitta mustaqil HTML faylga jamlaydi.</p>
<p><b>Tezkor tugmalar:</b> Ctrl+O yuklash · Ctrl+S loyiha · Ctrl+Z bekor ·
Ctrl+Y qaytarish · Ctrl+E eksport · F1 yordam</p>
"""
        box = QMessageBox(self)
        box.setWindowTitle("Qo'llanma")
        box.setTextFormat(Qt.TextFormat.RichText)
        box.setText(text)
        box.exec()

    def _show_about(self) -> None:
        QMessageBox.about(
            self, f"{APP_NAME} haqida",
            f"<h3>{APP_NAME} v{VERSION}</h3>"
            "<p>Universal ma'lumot va log tahlili platformasi.</p>"
            "<p>Python · PySide6 · pandas · scikit-learn · matplotlib</p>")

    def resizeEvent(self, event) -> None:  # noqa: N802
        super().resizeEvent(event)
        if hasattr(self, "toast") and self.toast.isVisible():
            self.toast._reposition()
