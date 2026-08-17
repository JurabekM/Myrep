"""Application shell: title bar, sidebar and the page stack."""

from __future__ import annotations

from PySide6.QtCore import QTimer
from PySide6.QtWidgets import QHBoxLayout, QStackedWidget, QVBoxLayout, QWidget

from app.controllers.app_state import app_state
from app.controllers.sync_controller import get_sync_controller, shutdown_sync
from app.services import auth_service
from app.services.permissions import Perm
from app.sync.engine import status as sync_status
from app.ui.main_window.frameless import FramelessWindow
from app.ui.main_window.sidebar import NavItem, Sidebar
from app.ui.main_window.title_bar import TitleBar
from app.ui.pages.audit_page import AuditPage
from app.ui.pages.counterparties_page import CounterpartiesPage
from app.ui.pages.expenses_page import ExpensesPage
from app.ui.pages.materials_page import MaterialsPage
from app.ui.pages.projects_page import ProjectsPage
from app.ui.pages.purchases_page import PurchasesPage
from app.ui.pages.reports_page import ReportsPage
from app.ui.pages.settings_page import SettingsPage
from app.ui.pages.warehouse_page import WarehousePage
from app.ui.widgets.common import toast
from app.utils.formatting import fmt_datetime
from app.utils.i18n import i18n, tr

NAV_ITEMS: list[NavItem] = [
    NavItem("projects", "nav_projects", "projects", Perm.PROJECT_VIEW),
    NavItem("purchases", "nav_purchases", "purchase", Perm.PURCHASE_VIEW),
    NavItem("materials", "nav_materials", "materials", Perm.WAREHOUSE_VIEW),
    NavItem("warehouse", "nav_warehouse", "warehouse", Perm.WAREHOUSE_VIEW),
    NavItem("counterparties", "nav_counterparties", "counterparty", Perm.COUNTERPARTY_VIEW),
    NavItem("expenses", "nav_expenses", "expense", Perm.EXPENSE_VIEW),
    NavItem("reports", "nav_reports", "report", Perm.REPORT_VIEW),
    NavItem("audit", "nav_audit", "audit", Perm.AUDIT_VIEW),
    NavItem("settings", "nav_settings", "settings", Perm.SETTINGS_MANAGE),
]


class MainWindow(FramelessWindow):
    """The single main window of the application."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("RootWindow")
        self.setMinimumSize(1180, 720)
        self.resize(1440, 860)

        outer = QVBoxLayout(self)
        outer.setContentsMargins(1, 1, 1, 1)
        outer.setSpacing(0)

        self.title_bar = TitleBar()
        self.title_bar.minimize_requested.connect(self.showMinimized)
        self.title_bar.maximize_requested.connect(self.toggle_maximized)
        self.title_bar.close_requested.connect(self.close)
        self.title_bar.drag_started.connect(self.start_drag)
        self.title_bar.drag_moved.connect(self.continue_drag)
        self.title_bar.drag_finished.connect(self.end_drag)
        self.title_bar.language_changed.connect(self._change_language)
        self.title_bar.logout_requested.connect(self._logout)
        self.title_bar.sync_requested.connect(self._sync_now)
        outer.addWidget(self.title_bar)

        body = QHBoxLayout()
        body.setContentsMargins(0, 0, 0, 0)
        body.setSpacing(0)
        outer.addLayout(body, 1)

        self.sidebar = Sidebar(NAV_ITEMS)
        self.sidebar.navigated.connect(self.navigate)
        body.addWidget(self.sidebar)

        self.stack = QStackedWidget()
        self.stack.setObjectName("ContentArea")
        body.addWidget(self.stack, 1)

        self.pages: dict[str, QWidget] = {}
        self._build_pages()

        self.sync = get_sync_controller()
        self.sync.started.connect(self._on_sync_started)
        self.sync.finished.connect(self._on_sync_finished)
        self._sync_timer = QTimer(self)
        self._sync_timer.timeout.connect(self._refresh_sync_badge)
        self._sync_timer.start(5000)

        self.title_bar.set_language(app_state.language)
        self._apply_user()
        self._refresh_sync_badge()
        app_state.user_changed.connect(lambda _user: self._apply_user())
        if app_state.sidebar_collapsed:
            self.sidebar.set_collapsed(True)
        self.navigate("projects")

    # -- construction -------------------------------------------------------- #
    def _build_pages(self) -> None:
        factories = {
            "projects": ProjectsPage,
            "purchases": PurchasesPage,
            "materials": MaterialsPage,
            "warehouse": WarehousePage,
            "counterparties": CounterpartiesPage,
            "expenses": ExpensesPage,
            "reports": ReportsPage,
            "audit": AuditPage,
            "settings": SettingsPage,
        }
        for key, factory in factories.items():
            page = factory()
            self.pages[key] = page
            self.stack.addWidget(page)

    # -- navigation ---------------------------------------------------------- #
    def navigate(self, key: str) -> None:
        """Switch the central stack to ``key``."""
        page = self.pages.get(key)
        if page is None:
            return
        self.stack.setCurrentWidget(page)
        self.sidebar.set_active(key)
        item = next((i for i in NAV_ITEMS if i.key == key), None)
        self.title_bar.set_context(tr(item.label_key) if item else "")
        if hasattr(page, "refresh"):
            page.refresh()

    def set_context(self, text: str) -> None:
        """Update the contextual label in the title bar."""
        self.title_bar.set_context(text)

    # -- session ------------------------------------------------------------- #
    def _apply_user(self) -> None:
        user = app_state.user
        if user is None:
            self.title_bar.set_user("", "")
            return
        self.title_bar.set_user(user.label, user.role_label(app_state.language))
        self.sidebar.apply_permissions(user.can)

    def _logout(self) -> None:
        from app.ui.dialogs.base_dialog import confirm

        if not confirm(self, tr("confirm_question"), tr("logout")):
            return
        auth_service.logout(app_state.user)
        app_state.set_user(None)
        self.close()
        from app.ui.pages.login_page import LoginWindow

        window = LoginWindow()
        window.logged_in.connect(lambda _user: _restart_main(window))
        window.show()

    def _change_language(self, language: str) -> None:
        """Switch the interface language and rebuild every page."""
        if language == app_state.language:
            return
        app_state.language = language
        i18n.set_language(language)
        current = self.stack.currentWidget()
        current_key = next((k for k, v in self.pages.items() if v is current), "projects")
        for page in list(self.pages.values()):
            self.stack.removeWidget(page)
            page.deleteLater()
        self.pages.clear()
        self._build_pages()
        self._apply_user()
        self.navigate(current_key)

    # -- synchronisation ------------------------------------------------------ #
    def _sync_now(self) -> None:
        """Trigger a manual synchronisation round from the title bar."""
        if not app_state.sync_enabled:
            self.navigate("settings")
            return
        if not self.sync.sync_now():
            return
        self._refresh_sync_badge()

    def _on_sync_started(self) -> None:
        self.title_bar.set_sync_state("busy", tr("sync_running"))

    def _on_sync_finished(self, report) -> None:
        self._refresh_sync_badge()
        page = self.pages.get("projects")
        if report.applied and page is not None and hasattr(page, "refresh"):
            page.refresh()
        toast(
            self,
            (
                f"{tr('sync_failed')}: {report.errors[0]}"
                if report.errors
                else f"{tr('sync_ok')} · {report.summary()}"
            ),
            "danger" if report.errors else "success",
        )

    def _refresh_sync_badge(self) -> None:
        """Keep the title bar indicator in step with the engine."""
        if not app_state.sync_enabled:
            self.title_bar.set_sync_state("off", tr("sync_disabled"))
            return
        if self.sync.busy:
            self.title_bar.set_sync_state("busy", tr("sync_running"))
            return
        try:
            state = sync_status()
        except Exception:  # pragma: no cover - defensive
            self.title_bar.set_sync_state("error", tr("sync_failed"))
            return
        detail = (
            f"{tr('sync_pending')}: {state['pending']} · "
            f"{tr('sync_last_pull')}: {fmt_datetime(state['last_pull_at'])}"
        )
        self.title_bar.set_sync_state(
            "error" if state["last_error"] else "idle",
            state["last_error"] or detail,
            state["pending"],
        )

    # -- window -------------------------------------------------------------- #
    def closeEvent(self, event) -> None:  # noqa: N802 - Qt naming
        app_state.sidebar_collapsed = self.sidebar.collapsed
        self._sync_timer.stop()
        shutdown_sync()
        super().closeEvent(event)


def _restart_main(login_window) -> None:  # pragma: no cover - interactive path
    """Open a fresh main window after re-authentication."""
    window = MainWindow()
    window.show()
    login_window._main_window = window  # keep a reference alive
