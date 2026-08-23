"""Asosiy oyna — chap navigatsiya + modul sahifalari.

DASHBOARD YO'Q. Bu klassik biznes ilova: chapda modullar ro'yxati, o'ngda
ish maydoni. Har sahifa aniq bir vazifani bajaradi.
"""

from __future__ import annotations

import logging

from PySide6.QtCore import Qt, Slot
from PySide6.QtGui import QAction, QKeySequence
from PySide6.QtWidgets import (
    QButtonGroup,
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QStackedWidget,
    QVBoxLayout,
    QWidget,
)

from distribos.app_context import AppContext
from distribos.presentation.background import SyncController
from distribos.presentation.status import connection_status
from distribos.presentation.theme import PALETTE, SPACE_LG, SPACE_MD, SPACE_SM
from distribos.presentation.widgets import Badge

logger = logging.getLogger(__name__)

#: (bo'lim, sarlavha, sahifa fabrikasi nomi)
NAVIGATION: tuple[tuple[str, tuple[tuple[str, str], ...]], ...] = (
    ("SAVDO", (
        ("orders", "Buyurtmalar"),
        ("customers", "Mijozlar"),
        ("products", "Mahsulotlar"),
    )),
    ("OMBOR VA MOLIYA", (
        ("inventory", "Ombor"),
        ("finance", "Kassa va to'lovlar"),
        ("visits", "Tashriflar"),
    )),
    ("HISOBOT", (
        ("reports", "Hisobotlar"),
        ("documents", "Hujjatlar"),
        ("assistant", "AI yordamchi"),
    )),
    ("TIZIM", (
        ("sync", "Sinxronizatsiya"),
        ("conflicts", "Tekshiruv navbati"),
        ("security", "Xavfsizlik"),
        ("backup", "Zaxira nusxa"),
        ("audit", "Audit jurnali"),
        ("settings", "Sozlamalar"),
    )),
)


class MainWindow(QMainWindow):
    """DistribOS AI asosiy oynasi."""

    def __init__(self, context: AppContext) -> None:
        super().__init__()
        self._context = context
        self._pages: dict[str, QWidget] = {}

        self.setWindowTitle("DistribOS AI")
        self.resize(1360, 860)
        self.setMinimumSize(1100, 700)

        central = QWidget()
        layout = QHBoxLayout(central)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        layout.addWidget(self._build_navigation())
        self._stack = QStackedWidget()
        content = QWidget()
        content_layout = QVBoxLayout(content)
        content_layout.setContentsMargins(SPACE_LG, SPACE_LG, SPACE_LG, SPACE_LG)
        content_layout.addWidget(self._stack)
        layout.addWidget(content, 1)

        self.setCentralWidget(central)
        self._build_status_bar()
        self._build_menu()
        self._build_pages()

        self._sync = SyncController(context.run_sync_cycle, interval_ms=5000, parent=self)
        self._sync.status_changed.connect(self._on_sync_status)
        self._sync.error_occurred.connect(self._on_sync_error)

        self._select("orders")

    # --- qurilish ---------------------------------------------------------

    def _build_navigation(self) -> QWidget:
        panel = QWidget()
        panel.setObjectName("NavPanel")
        panel.setFixedWidth(232)

        layout = QVBoxLayout(panel)
        layout.setContentsMargins(0, SPACE_SM, 0, SPACE_MD)
        layout.setSpacing(0)

        brand = QLabel("DistribOS AI")
        brand.setObjectName("NavBrand")
        layout.addWidget(brand)

        subtitle = QLabel("Ulgurji savdo tizimi")
        subtitle.setObjectName("NavSubtitle")
        layout.addWidget(subtitle)

        self._nav_group = QButtonGroup(self)
        self._nav_group.setExclusive(True)
        self._nav_buttons: dict[str, QPushButton] = {}

        for section, items in NAVIGATION:
            header = QLabel(section)
            header.setObjectName("NavSection")
            layout.addWidget(header)
            for key, title in items:
                button = QPushButton(title)
                button.setObjectName("NavItem")
                button.setCheckable(True)
                button.setCursor(Qt.CursorShape.PointingHandCursor)
                button.setProperty("page_key", key)
                # Lambda YO'Q — bog'langan slot (background.py 1-qoida).
                button.clicked.connect(self._on_nav_clicked)
                self._nav_group.addButton(button)
                self._nav_buttons[key] = button
                layout.addWidget(button)

        layout.addStretch(1)
        return panel

    def _build_status_bar(self) -> None:
        bar = self.statusBar()

        self._sync_badge = Badge("Tekshirilmoqda…", "progress")
        bar.addPermanentWidget(self._sync_badge)

        self._broker_label = QLabel()
        mqtt = self._context.settings.mqtt
        if mqtt.is_public_pilot:
            self._broker_label.setText("Ochiq broker (sinov rejimi)")
            self._broker_label.setStyleSheet(f"color: {PALETTE.warning};")
            self._broker_label.setToolTip(
                "Xabarlar AETHER-Q bilan himoyalangan, lekin brokerning "
                "mavjudligi kafolatlanmaydi. Haqiqiy ish uchun xususiy "
                "broker sozlang."
            )
        else:
            self._broker_label.setText("Xususiy broker")
            self._broker_label.setStyleSheet(f"color: {PALETTE.ok};")
        bar.addPermanentWidget(self._broker_label)

        bar.showMessage("Tayyor")

    def _build_menu(self) -> None:
        file_menu = self.menuBar().addMenu("&Fayl")

        sync_now = QAction("Hozir sinxronlash", self)
        sync_now.setShortcut(QKeySequence("F5"))
        sync_now.triggered.connect(self._on_sync_now)
        file_menu.addAction(sync_now)

        file_menu.addSeparator()
        quit_action = QAction("Chiqish", self)
        quit_action.setShortcut(QKeySequence.StandardKey.Quit)
        quit_action.triggered.connect(self.close)
        file_menu.addAction(quit_action)

        help_menu = self.menuBar().addMenu("&Yordam")
        about = QAction("Dastur haqida", self)
        about.triggered.connect(self._on_about)
        help_menu.addAction(about)

    def _build_pages(self) -> None:
        from distribos.presentation.pages import build_pages

        for key, page in build_pages(self._context).items():
            self._pages[key] = page
            self._stack.addWidget(page)

    # --- navigatsiya ------------------------------------------------------

    @Slot()
    def _on_nav_clicked(self) -> None:
        button = self.sender()
        if not isinstance(button, QPushButton):
            return
        key = button.property("page_key")
        if isinstance(key, str):
            self._select(key)

    def _select(self, key: str) -> None:
        page = self._pages.get(key)
        if page is None:
            return
        button = self._nav_buttons.get(key)
        if button is not None and not button.isChecked():
            button.setChecked(True)
        self._stack.setCurrentWidget(page)
        if hasattr(page, "refresh"):
            try:
                page.refresh()   # type: ignore[attr-defined]
            except Exception:
                logger.exception("Sahifani yangilashda xato: %s", key)

    # --- sinxronizatsiya --------------------------------------------------

    def start_sync(self) -> None:
        self._sync.start()

    @Slot()
    def _on_sync_now(self) -> None:
        self._sync.trigger()
        self.statusBar().showMessage("Sinxronizatsiya boshlandi…", 3000)

    @Slot(int, int, int, int)
    def _on_sync_status(self, published: int, received: int, queued: int, errors: int) -> None:
        connected = bool(
            self._context.transport is not None
            and getattr(self._context.transport, "is_connected", lambda: False)()
        )
        self._sync_badge.apply(connection_status(connected, queued))
        if published:
            self.statusBar().showMessage(f"{published} ta yozuv yuborildi", 4000)

        page = self._stack.currentWidget()
        if hasattr(page, "refresh_if_live"):
            page.refresh_if_live()   # type: ignore[attr-defined]

    @Slot(str)
    def _on_sync_error(self, message: str) -> None:
        logger.warning("Sinxronizatsiya xatosi: %s", message)
        self.statusBar().showMessage("Sinxronizatsiyada xatolik", 5000)

    # --- oyna hodisalari --------------------------------------------------

    @Slot()
    def _on_about(self) -> None:
        health = self._context.provider.protocol_health_check()
        QMessageBox.information(
            self, "DistribOS AI",
            "DistribOS AI — serversiz, offline-first savdo tizimi\n\n"
            f"Xavfsizlik protokoli: AETHER-Q v{health.protocol_version}\n"
            f"Qurilma: {health.device_id_masked}\n"
            f"Ulangan qurilmalar: {health.peers_known}\n\n"
            "Dastur markaziy serversiz ishlaydi: barcha ma'lumot shu "
            "kompyuterda saqlanadi va qurilmalar o'zaro to'g'ridan-to'g'ri "
            "sinxronlanadi.",
        )

    def closeEvent(self, event) -> None:
        """Yopishdan oldin fon oqimini TARTIB BILAN to'xtatadi.

        `terminate()` ishlatilmaydi: u SQLite tranzaksiyasini yarim yo'lda
        uzib, bazani buzishi mumkin.
        """
        self._sync.stop()
        try:
            self._context.close()
        except Exception:
            logger.exception("Yopishda xato")
        event.accept()
