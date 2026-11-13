"""Asosiy oyna: chapda bo'limlar, o'ngda sahifa, yuqorida til va ulanish holati.

Sahifalar birinchi ochilganda quriladi (xotira tejaladi): ro'yxatda faqat
nomi turadi, vidjetlar esa kerak bo'lgandagina yaratiladi.
"""

from collections.abc import Callable
from functools import partial
from typing import Any

from pydantic import ValidationError
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QCloseEvent, QShowEvent
from PyQt6.QtWidgets import (
    QComboBox,
    QHBoxLayout,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QMainWindow,
    QSplitter,
    QStackedWidget,
    QVBoxLayout,
    QWidget,
)

from srv1_sdk.panel import PanelSpec
from srv1_shell.api import Api, Reply
from srv1_shell.common import AppContext, Page, dark_title_bar
from srv1_shell.config import ShellConfig
from srv1_shell.events import EventStream
from srv1_shell.i18n import I18n
from srv1_shell.pages.logs_page import LogsPage
from srv1_shell.pages.memory_page import MemoryPage
from srv1_shell.pages.panel_page import PanelPage
from srv1_shell.pages.plugins_page import STATE_TOPIC, PluginsPage
from srv1_shell.pages.system_page import SystemPage
from srv1_shell.translations import LANGUAGE_NAMES

PANEL_KEY_PREFIX = "panel:"
PageFactory = Callable[[AppContext], Page]
_FIXED_PAGES: tuple[tuple[str, PageFactory], ...] = (
    ("system", SystemPage),
    ("plugins", PluginsPage),
    ("logs", LogsPage),
    ("memory", MemoryPage),
)


class MainWindow(QMainWindow):
    def __init__(
        self,
        config: ShellConfig,
        token: str,
        on_language_changed: Callable[[str], None] | None = None,
    ) -> None:
        super().__init__()
        self.config = config
        self._on_language_changed = on_language_changed
        self.api = Api(config.http_url, token, self)
        self.events = EventStream(config.ws_url, token, self)
        self.ctx = AppContext(self.api, self.events, I18n(config.language))
        self._factories: dict[str, PageFactory] = {}
        self._pages: dict[str, Page] = {}
        self._panel_specs: dict[str, PanelSpec] = {}
        self._current: Page | None = None
        self._closed = False

        self.resize(1180, 760)
        self.setMinimumSize(900, 560)
        root = QWidget()
        root.setObjectName("Root")
        outer = QVBoxLayout(root)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(0)
        outer.addWidget(self._build_header())

        self.nav = QListWidget()
        self.nav.setObjectName("Nav")
        self.nav.currentItemChanged.connect(self._on_nav_changed)
        sidebar = QWidget()
        sidebar.setObjectName("Sidebar")
        sidebar.setMinimumWidth(180)
        side_layout = QVBoxLayout(sidebar)
        side_layout.setContentsMargins(0, 10, 0, 10)
        side_layout.addWidget(self.nav)

        self.stack = QStackedWidget()
        self.stack.setObjectName("PageHost")
        splitter = QSplitter(Qt.Orientation.Horizontal)
        splitter.setHandleWidth(1)
        splitter.addWidget(sidebar)
        splitter.addWidget(self.stack)
        splitter.setStretchFactor(1, 1)
        splitter.setSizes([210, 970])
        splitter.setChildrenCollapsible(False)
        outer.addWidget(splitter, 1)
        self.setCentralWidget(root)

        self.events.connection_changed.connect(self._show_connection)
        self.events.received.connect(self._on_event)
        self._build_nav("system")
        self._show_connection(False)
        self.events.start()

    # --- sarlavha -----------------------------------------------------------
    def _build_header(self) -> QWidget:
        header = QWidget()
        header.setObjectName("Header")
        layout = QHBoxLayout(header)
        layout.setContentsMargins(18, 10, 18, 10)
        self.title = QLabel()
        self.title.setObjectName("AppTitle")
        self.connection = QLabel()
        self.language_label = QLabel()
        self.language_label.setObjectName("Muted")
        self.language = QComboBox()
        for code, name in LANGUAGE_NAMES.items():
            self.language.addItem(name, code)
        self.language.setCurrentIndex(max(0, self.language.findData(self.config.language)))
        self.language.currentIndexChanged.connect(self._change_language)
        layout.addWidget(self.title)
        layout.addStretch(1)
        layout.addWidget(self.connection)
        layout.addSpacing(18)
        layout.addWidget(self.language_label)
        layout.addWidget(self.language)
        return header

    def _show_connection(self, connected: bool) -> None:
        t = self.ctx.i18n.t
        address = t("conn.core", address=f"{self.config.host}:{self.config.port}")
        state = t("conn.connected" if connected else "conn.disconnected")
        self.connection.setText(f"● {state} — {address}")
        self.connection.setObjectName("ConnOk" if connected else "ConnBad")
        style = self.connection.style()
        if style is not None:
            style.unpolish(self.connection)
            style.polish(self.connection)
        if connected:
            self._refresh_plugins()
            if self._current is not None:
                self._current.activate()

    # --- bo'limlar ro'yxati va sahifalar ---------------------------------------
    def _build_nav(self, select: str) -> None:
        """Ro'yxatni joriy tilda quradi; mavjud sahifalar tashlanadi, keyin qayta yaratiladi."""
        t = self.ctx.i18n.t
        self.setWindowTitle(t("app.title"))
        self.title.setText(t("app.title"))
        self.language_label.setText(t("header.language"))
        if self._current is not None:
            self._current.deactivate()
            self._current = None
        for page in self._pages.values():
            self._discard(page)
        self._pages = {}
        self._factories = {}
        self.nav.blockSignals(True)
        self.nav.clear()
        self.nav.blockSignals(False)
        for key, factory in _FIXED_PAGES:
            self._add_entry(key, t(f"nav.{key}"), factory)
        for name, spec in self._panel_specs.items():
            self._add_panel_entry(name, spec)
        self.select(select if select in self._factories else "system")
        self._refresh_plugins()

    def _add_entry(self, key: str, label: str, factory: PageFactory) -> None:
        self._factories[key] = factory
        item = QListWidgetItem(label)
        item.setData(Qt.ItemDataRole.UserRole, key)
        self.nav.addItem(item)

    def _discard(self, page: Page) -> None:
        page.deactivate()
        self.stack.removeWidget(page)
        page.deleteLater()

    def page_keys(self) -> list[str]:
        """Ro'yxatdagi bo'lim kalitlari (tartibi bilan)."""
        return list(self._factories)

    def page(self, key: str) -> Page:
        """Sahifani qaytaradi; hali qurilmagan bo'lsa quradi."""
        existing = self._pages.get(key)
        if existing is not None:
            return existing
        page = self._factories[key](self.ctx)
        self._pages[key] = page
        self.stack.addWidget(page)
        return page

    def select(self, key: str) -> None:
        for row in range(self.nav.count()):
            item = self.nav.item(row)
            if item is not None and item.data(Qt.ItemDataRole.UserRole) == key:
                self.nav.setCurrentRow(row)
                return

    def current_key(self) -> str:
        item = self.nav.currentItem()
        return str(item.data(Qt.ItemDataRole.UserRole)) if item is not None else "system"

    def _on_nav_changed(self, current: QListWidgetItem | None, _previous: object) -> None:
        if current is None:
            return
        key = str(current.data(Qt.ItemDataRole.UserRole))
        if key not in self._factories:
            return
        page = self.page(key)
        if page is self._current:
            return
        if self._current is not None:
            self._current.deactivate()
        self._current = page
        self.stack.setCurrentWidget(page)
        page.activate()

    # --- plagin panellari ---------------------------------------------------------
    def _on_event(self, topic: str, _data: dict[str, Any]) -> None:
        if topic == STATE_TOPIC:
            self._refresh_plugins()

    def _refresh_plugins(self) -> None:
        self.api.get("/api/v1/plugins", self._on_plugins, owner=self)

    def _on_plugins(self, reply: Reply) -> None:
        if reply.ok:
            self._sync_panels(reply.rows())

    def _sync_panels(self, plugins: list[dict[str, Any]]) -> None:
        """Ishlayotgan va paneli bor plaginlar uchun bo'lim ochadi, qolganlarini yopadi."""
        wanted = {str(p["name"]) for p in plugins if p["status"] == "running" and p["has_panel"]}
        for name in [n for n in self._panel_specs if n not in wanted]:
            self._remove_panel(name)
        for name in sorted(wanted - set(self._panel_specs)):
            self.api.get(f"/api/v1/plugins/{name}/panel", partial(self._on_panel, name), owner=self)

    def _on_panel(self, name: str, reply: Reply) -> None:
        if not reply.ok or name in self._panel_specs:
            return
        try:
            spec = PanelSpec.model_validate(reply.data)
        except ValidationError:
            return
        self._panel_specs[name] = spec
        self._add_panel_entry(name, spec)

    def _add_panel_entry(self, name: str, spec: PanelSpec) -> None:
        def build(ctx: AppContext) -> Page:
            return PanelPage(ctx, name, spec)

        self._add_entry(PANEL_KEY_PREFIX + name, self.ctx.i18n.pick(spec.title), build)

    def _remove_panel(self, name: str) -> None:
        key = PANEL_KEY_PREFIX + name
        self._panel_specs.pop(name, None)
        if key not in self._factories:
            return
        if self.current_key() == key:
            self.select("plugins")
        del self._factories[key]
        for row in range(self.nav.count()):
            item = self.nav.item(row)
            if item is not None and item.data(Qt.ItemDataRole.UserRole) == key:
                self.nav.takeItem(row)
                break
        page = self._pages.pop(key, None)
        if page is not None:
            self._discard(page)

    # --- til ------------------------------------------------------------------------
    def _change_language(self, _index: int) -> None:
        self.set_language(str(self.language.currentData()))

    def set_language(self, language: str) -> None:
        if language == self.ctx.i18n.language or language not in LANGUAGE_NAMES:
            return
        selected = self.current_key()
        self.config.language = language
        self.ctx = AppContext(self.api, self.events, I18n(language))
        self.language.blockSignals(True)
        self.language.setCurrentIndex(self.language.findData(language))
        self.language.blockSignals(False)
        self._build_nav(selected)
        self._show_connection(self.events.connected)
        if self._on_language_changed is not None:
            self._on_language_changed(language)

    # --- yopilish ---------------------------------------------------------------------
    def shutdown(self) -> None:
        """Taymerlar, WebSocket va fon oqimini shu tartibda to'xtatadi."""
        if self._closed:
            return
        self._closed = True
        if self._current is not None:
            self._current.deactivate()
        self.events.stop()
        self.api.shutdown()

    def showEvent(self, a0: QShowEvent | None) -> None:
        super().showEvent(a0)
        dark_title_bar(int(self.winId()))

    def closeEvent(self, a0: QCloseEvent | None) -> None:
        self.shutdown()
        super().closeEvent(a0)
