from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtGui import QAction, QKeySequence
from PySide6.QtWidgets import (QComboBox, QFileDialog, QFrame, QHBoxLayout, QLabel,
                               QMainWindow, QMessageBox, QPushButton, QStackedWidget,
                               QStatusBar, QVBoxLayout, QWidget)

from ..config import APP_NAME
from ..core.persistence import load_workspace, save_workspace
from .pages import (AnalyticsPage, DashboardPage, ExplorerPage, ImportPage, LogLabPage,
                    ModelPage, PipelinePage, ReportPage)
from .state import AppState
from .theme import QSS


class MainWindow(QMainWindow):
    def __init__(self, demo: bool = False) -> None:
        super().__init__()
        self.state = AppState()
        self.setWindowTitle(APP_NAME)
        self.resize(1480, 920)
        self.setMinimumSize(1100, 720)
        self.setStyleSheet(QSS)
        self._build_ui()
        self._actions()
        self._connect()
        if demo:
            self.pages["import"]._demo()
            self.pages["import"]._accept()
            self._go("dashboard")
        self.refresh_all()

    def _build_ui(self) -> None:
        root = QWidget()
        self.setCentralWidget(root)
        outer = QHBoxLayout(root)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(0)

        sidebar = QFrame(); sidebar.setObjectName("sidebar"); sidebar.setFixedWidth(220)
        side = QVBoxLayout(sidebar); side.setContentsMargins(14, 22, 14, 16); side.setSpacing(5)
        accent = QLabel("LOCAL DATA OS"); accent.setObjectName("brandAccent")
        brand = QLabel("InsightForge"); brand.setObjectName("brand")
        side.addWidget(accent); side.addWidget(brand); side.addSpacing(22)
        self.nav: dict[str, QPushButton] = {}
        entries = [
            ("dashboard", "⌂  Command Center"), ("import", "＋  Data Hub"),
            ("explorer", "▦  Data Explorer"), ("pipeline", "⤢  Pipeline Builder"),
            ("analytics", "◒  Analytics Lab"), ("logs", "≋  Log Intelligence"),
            ("models", "✦  Model Studio"), ("report", "▤  Report Composer"),
        ]
        for key, label in entries:
            item = QPushButton(label); item.setObjectName("nav"); item.setCheckable(True)
            item.clicked.connect(lambda checked=False, target=key: self._go(target))
            side.addWidget(item); self.nav[key] = item
        side.addStretch()
        version = QLabel("v0.1 · Python only"); version.setObjectName("muted"); side.addWidget(version)
        outer.addWidget(sidebar)

        content = QWidget(); content_layout = QVBoxLayout(content); content_layout.setContentsMargins(0, 0, 0, 0); content_layout.setSpacing(0)
        topbar = QFrame(); topbar.setObjectName("topbar"); topbar.setFixedHeight(62)
        top = QHBoxLayout(topbar); top.setContentsMargins(22, 9, 22, 9)
        top.addWidget(QLabel("Faol dataset"))
        self.dataset_combo = QComboBox(); self.dataset_combo.setMinimumWidth(260)
        self.dataset_combo.currentIndexChanged.connect(self._activate)
        top.addWidget(self.dataset_combo); top.addStretch()
        self.shape = QLabel("Dataset yuklanmagan"); self.shape.setObjectName("muted"); top.addWidget(self.shape)
        save = QPushButton("Workspace saqlash"); save.clicked.connect(self.save_workspace); top.addWidget(save)
        content_layout.addWidget(topbar)
        self.stack = QStackedWidget()
        self.pages = {
            "dashboard": DashboardPage(self.state), "import": ImportPage(self.state),
            "explorer": ExplorerPage(self.state), "pipeline": PipelinePage(self.state),
            "analytics": AnalyticsPage(self.state), "logs": LogLabPage(self.state),
            "models": ModelPage(self.state), "report": ReportPage(self.state),
        }
        for page in self.pages.values(): self.stack.addWidget(page)
        content_layout.addWidget(self.stack, 1)
        outer.addWidget(content, 1)
        self.setStatusBar(QStatusBar())
        self._go("dashboard")

    def _actions(self) -> None:
        open_action = QAction("Workspace ochish", self); open_action.setShortcut(QKeySequence.StandardKey.Open)
        open_action.triggered.connect(self.open_workspace); self.addAction(open_action)
        save_action = QAction("Workspace saqlash", self); save_action.setShortcut(QKeySequence.StandardKey.Save)
        save_action.triggered.connect(self.save_workspace); self.addAction(save_action)
        undo = QAction("Undo", self); undo.setShortcut(QKeySequence.StandardKey.Undo)
        undo.triggered.connect(self.pages["explorer"]._undo); self.addAction(undo)
        redo = QAction("Redo", self); redo.setShortcut(QKeySequence.StandardKey.Redo)
        redo.triggered.connect(self.pages["explorer"]._redo); self.addAction(redo)

    def _connect(self) -> None:
        self.state.workspace_changed.connect(self._datasets)
        self.state.active_changed.connect(self._active)
        self.state.data_changed.connect(self._refresh_current)
        self.state.message.connect(self._message)

    def _go(self, key: str) -> None:
        page = self.pages[key]
        self.stack.setCurrentWidget(page)
        for name, item in self.nav.items(): item.setChecked(name == key)
        page.refresh()

    def _datasets(self) -> None:
        active = self.state.workspace.active
        self.dataset_combo.blockSignals(True); self.dataset_combo.clear()
        for dataset in self.state.workspace.datasets:
            self.dataset_combo.addItem(dataset.name, dataset.id)
        if active:
            index = self.dataset_combo.findData(active.id)
            self.dataset_combo.setCurrentIndex(index)
        self.dataset_combo.blockSignals(False)

    def _activate(self, index: int) -> None:
        dataset_id = self.dataset_combo.itemData(index)
        if dataset_id:
            self.state.workspace.activate(dataset_id)
            self.state.active_changed.emit(); self.state.data_changed.emit()

    def _active(self) -> None:
        dataset = self.state.workspace.active
        self.shape.setText(f"{dataset.frame.shape[0]:,} qator × {dataset.frame.shape[1]} ustun" if dataset else "Dataset yuklanmagan")

    def _refresh_current(self) -> None:
        current = self.stack.currentWidget()
        if hasattr(current, "refresh"): current.refresh()
        self._active()

    def refresh_all(self) -> None:
        self._datasets(); self._active(); self._refresh_current()

    def _message(self, text: str, level: str) -> None:
        self.statusBar().showMessage(text, 6000)

    def save_workspace(self) -> None:
        if not self.state.workspace.datasets:
            return
        initial = self.state.workspace_path or str(Path.cwd() / "workspace.ifs")
        path, _ = QFileDialog.getSaveFileName(self, "Workspace saqlash", initial, "InsightForge (*.ifs)")
        if path:
            try:
                saved = save_workspace(self.state.workspace, path)
                self.state.workspace_path = str(saved)
                self._message(f"Saqlandi: {saved.name}", "success")
            except Exception as exc:
                QMessageBox.critical(self, "Saqlash xatosi", str(exc))

    def open_workspace(self) -> None:
        path, _ = QFileDialog.getOpenFileName(self, "Workspace ochish", "", "InsightForge (*.ifs)")
        if path:
            try:
                self.state.set_workspace(load_workspace(path), path)
                self.refresh_all()
            except Exception as exc:
                QMessageBox.critical(self, "Ochish xatosi", str(exc))

    def closeEvent(self, event) -> None:
        if self.state.workspace.datasets:
            answer = QMessageBox.question(self, "InsightForge", "Workspace'ni saqlamasdan yopilsinmi?",
                                          QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
            if answer != QMessageBox.StandardButton.Yes:
                event.ignore(); return
        event.accept()
