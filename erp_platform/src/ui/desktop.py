# -*- coding: utf-8 -*-
"""
Desktop GUI — asosiy oyna.

Tuzilma:
  * Ribbon (yuqori panel) — tez amallar va sarlavha
  * Sidebar (chap panel) — modul navigatsiyasi (ruxsatlarga qarab)
  * Markaziy stack — native sahifalar (dashboard, jadvallar) +
    QWebEngineView (to'liq web ilova ichida)
  * Ctrl+K — global qidiruv dialogi

Native dashboard QtCharts bilan; jadval sahifalari to'g'ridan-to'g'ri
servis qatlamidan to'ldiriladi (web serversiz ham ishlaydi). WebView esa
fon Flask serveriga ulanib, avtomatik login qilinadi.
"""
from __future__ import annotations

from datetime import date

from src import __app_name__, __version__
from src.auth.rbac import has_permission, ROLE_LABELS
from src.auth.service import AuthError
from src.core.logger import get_logger
from src.core.utils import money
from src.ui.qt_compat import (
    HAS_WEBENGINE, Qt, QSize, QtCore, QtGui, QtWidgets, QUrl,
)
from src.ui.theme_qss import COLORS, QSS
from src.ui import widgets as W

if HAS_WEBENGINE:
    from src.ui.qt_compat import (
        QNetworkCookie, QWebEngineProfile, QWebEngineView,
    )

#: Sidebar navigatsiyasi: (bo'lim, [(nom, kalit, ruxsat)])
NAV = [
    ("", [("Dashboard", "dashboard", "dashboard.view")]),
    ("Savdo", [
        ("Savdo hujjatlari", "sales", "sales.view"),
        ("Mijozlar", "customers", "customers.view"),
    ]),
    ("Ombor", [
        ("Mahsulotlar", "products", "inventory.view"),
        ("Qoldiqlar", "stock", "inventory.view"),
    ]),
    ("Moliya", [
        ("Kassa/Bank", "cash", "cash.view"),
        ("Hisoblar rejasi", "accounts", "accounting.view"),
    ]),
    ("HR", [("Xodimlar", "employees", "hr.view")]),
    ("", [("Web interfeys (to'liq)", "web", "dashboard.view")]),
]


class LoginDialog(QtWidgets.QDialog):
    """Native kirish oynasi."""

    def __init__(self, ctx) -> None:
        super().__init__()
        self._ctx = ctx
        self.result_session = None
        self.result_user = None
        self.setWindowTitle(f"{__app_name__} — Kirish")
        self.setFixedWidth(380)
        self.setStyleSheet(QSS)

        layout = QtWidgets.QVBoxLayout(self)
        layout.setContentsMargins(30, 30, 30, 30)
        layout.setSpacing(12)

        title = QtWidgets.QLabel(f"{__app_name__}")
        title.setObjectName("Brand")
        subtitle = QtWidgets.QLabel("Enterprise Resource Planning")
        subtitle.setStyleSheet(f"color: {COLORS['muted']};")
        layout.addWidget(title)
        layout.addWidget(subtitle)
        layout.addSpacing(10)

        self.username = QtWidgets.QLineEdit()
        self.username.setPlaceholderText("Login")
        self.username.setText("admin")
        self.password = QtWidgets.QLineEdit()
        self.password.setPlaceholderText("Parol")
        self.password.setEchoMode(QtWidgets.QLineEdit.EchoMode.Password)
        self.password.returnPressed.connect(self._try_login)
        layout.addWidget(QtWidgets.QLabel("Login"))
        layout.addWidget(self.username)
        layout.addWidget(QtWidgets.QLabel("Parol"))
        layout.addWidget(self.password)

        self.error_lbl = QtWidgets.QLabel("")
        self.error_lbl.setStyleSheet(f"color: {COLORS['red']};")
        self.error_lbl.setWordWrap(True)
        layout.addWidget(self.error_lbl)

        btn = QtWidgets.QPushButton("Kirish")
        btn.setObjectName("PrimaryBtn")
        btn.clicked.connect(self._try_login)
        layout.addWidget(btn)

        hint = QtWidgets.QLabel(
            "Birinchi kirish: parol data/admin_credentials.txt faylida.")
        hint.setStyleSheet(f"color: {COLORS['muted']}; font-size: 10px;")
        hint.setWordWrap(True)
        layout.addWidget(hint)

    def _try_login(self) -> None:
        auth = self._ctx.services.get("auth")
        try:
            result = auth.login(self.username.text(), self.password.text(),
                                ip="127.0.0.1", user_agent="desktop")
        except AuthError as exc:
            self.error_lbl.setText(str(exc))
            return
        self.result_session = result["token"]
        self.result_user = result["user"]
        self.accept()


class GlobalSearchDialog(QtWidgets.QDialog):
    """Ctrl+K global qidiruv oynasi."""

    def __init__(self, ctx, parent=None) -> None:
        super().__init__(parent)
        self._ctx = ctx
        self.setWindowTitle("Global qidiruv")
        self.setFixedSize(560, 440)
        self.setStyleSheet(QSS)

        layout = QtWidgets.QVBoxLayout(self)
        self.input = QtWidgets.QLineEdit()
        self.input.setPlaceholderText("Qidiruv (mahsulot, mijoz, hujjat...)")
        self.input.textChanged.connect(self._search)
        layout.addWidget(self.input)

        self.results = QtWidgets.QListWidget()
        layout.addWidget(self.results)
        self.input.setFocus()

    def _search(self, text: str) -> None:
        self.results.clear()
        if len(text.strip()) < 2:
            return
        groups = self._ctx.services.get("search").global_search(text)
        for group in groups:
            header = QtWidgets.QListWidgetItem(f"— {group['group']} —")
            header.setForeground(QtGui.QColor(COLORS["muted"]))
            header.setFlags(Qt.ItemFlag.NoItemFlags)
            self.results.addItem(header)
            for item in group["items"]:
                sub = f"  {item['title']}"
                if item["subtitle"]:
                    sub += f"   ({item['subtitle']})"
                self.results.addItem(QtWidgets.QListWidgetItem(sub))


class MainWindow(QtWidgets.QMainWindow):
    """ERP desktop asosiy oynasi."""

    def __init__(self, ctx, user: dict, session_token: str) -> None:
        super().__init__()
        self._ctx = ctx
        self._user = user
        self._session = session_token
        self._log = get_logger("gui")
        self._pages: dict[str, int] = {}
        self._web_view = None

        self.setWindowTitle(f"{__app_name__} v{__version__} — Enterprise ERP")
        self.resize(1280, 800)
        self.setStyleSheet(QSS)

        central = QtWidgets.QWidget()
        self.setCentralWidget(central)
        root = QtWidgets.QVBoxLayout(central)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        root.addWidget(self._build_ribbon())

        body = QtWidgets.QHBoxLayout()
        body.setContentsMargins(0, 0, 0, 0)
        body.setSpacing(0)
        body.addWidget(self._build_sidebar())

        self.stack = QtWidgets.QStackedWidget()
        self.stack.setObjectName("Content")
        content_wrap = QtWidgets.QWidget()
        content_wrap.setObjectName("Content")
        cw = QtWidgets.QVBoxLayout(content_wrap)
        cw.setContentsMargins(20, 20, 20, 20)
        cw.addWidget(self.stack)
        body.addWidget(content_wrap, 1)
        root.addLayout(body, 1)

        self._build_pages()
        self._build_statusbar()

        # Ctrl+K global qidiruv
        shortcut = QtGui.QShortcut(QtGui.QKeySequence("Ctrl+K"), self)
        shortcut.activated.connect(self._open_search)

        # Dashboard'ni davriy yangilash (30 s)
        self._timer = QtCore.QTimer(self)
        self._timer.timeout.connect(self._refresh_dashboard)
        self._timer.start(30000)

    # ------------------------------------------------------------------ #
    #  Ribbon
    # ------------------------------------------------------------------ #

    def _build_ribbon(self) -> QtWidgets.QWidget:
        ribbon = QtWidgets.QWidget()
        ribbon.setObjectName("Ribbon")
        ribbon.setFixedHeight(58)
        layout = QtWidgets.QHBoxLayout(ribbon)
        layout.setContentsMargins(16, 8, 16, 8)

        def ribbon_btn(text: str, slot, primary: bool = False):
            btn = QtWidgets.QPushButton(text)
            btn.setObjectName("PrimaryBtn" if primary else "RibbonBtn")
            btn.clicked.connect(slot)
            return btn

        if has_permission(self._user["role"], "pos.operate"):
            layout.addWidget(ribbon_btn("▣ POS kassa",
                                        lambda: self._open_web("/pos"), True))
        if has_permission(self._user["role"], "sales.create"):
            layout.addWidget(ribbon_btn("+ Yangi savdo",
                                        lambda: self._open_web("/sales/new")))
        layout.addWidget(ribbon_btn("🔍 Qidiruv (Ctrl+K)", self._open_search))
        layout.addStretch()

        user_lbl = QtWidgets.QLabel(
            f"{self._user['full_name'] or self._user['username']}  ·  "
            f"{ROLE_LABELS.get(self._user['role'], self._user['role'])}")
        user_lbl.setStyleSheet(f"color: {COLORS['muted']};")
        layout.addWidget(user_lbl)
        return ribbon

    # ------------------------------------------------------------------ #
    #  Sidebar
    # ------------------------------------------------------------------ #

    def _build_sidebar(self) -> QtWidgets.QWidget:
        sidebar = QtWidgets.QWidget()
        sidebar.setObjectName("Sidebar")
        sidebar.setFixedWidth(220)
        layout = QtWidgets.QVBoxLayout(sidebar)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # Brand
        brand = QtWidgets.QWidget()
        bl = QtWidgets.QVBoxLayout(brand)
        bl.setContentsMargins(16, 16, 16, 12)
        name = QtWidgets.QLabel(__app_name__)
        name.setObjectName("Brand")
        ver = QtWidgets.QLabel(f"v{__version__} · ERP")
        ver.setObjectName("Ver")
        bl.addWidget(name)
        bl.addWidget(ver)
        layout.addWidget(brand)

        self._nav_buttons: dict[str, QtWidgets.QPushButton] = {}
        for section, items in NAV:
            visible = [it for it in items
                       if has_permission(self._user["role"], it[2])]
            if not visible:
                continue
            if section:
                sect = QtWidgets.QLabel(section.upper())
                sect.setObjectName("SectionTitle")
                sect.setContentsMargins(16, 10, 0, 4)
                layout.addWidget(sect)
            for label, key, _perm in visible:
                btn = QtWidgets.QPushButton(label)
                btn.setObjectName("NavBtn")
                btn.setCheckable(True)
                btn.clicked.connect(lambda _, k=key: self._navigate(k))
                layout.addWidget(btn)
                self._nav_buttons[key] = btn

        layout.addStretch()
        logout = QtWidgets.QPushButton("Chiqish")
        logout.setObjectName("NavBtn")
        logout.clicked.connect(self._logout)
        layout.addWidget(logout)
        return sidebar

    # ------------------------------------------------------------------ #
    #  Sahifalar
    # ------------------------------------------------------------------ #

    def _build_pages(self) -> None:
        S = self._ctx.services

        # Dashboard (native)
        self._dashboard = self._build_dashboard()
        self._add_page("dashboard", self._dashboard)

        # Native jadval sahifalari (servisdan to'ldiriladi)
        if has_permission(self._user["role"], "sales.view"):
            self._add_page("sales", W.TablePage("Savdo hujjatlari",
                                                self._load_sales))
        if has_permission(self._user["role"], "customers.view"):
            self._add_page("customers", W.TablePage("Mijozlar",
                                                    self._load_customers))
        if has_permission(self._user["role"], "inventory.view"):
            self._add_page("products", W.TablePage("Mahsulotlar",
                                                   self._load_products))
            self._add_page("stock", W.TablePage("Ombor qoldiqlari",
                                                self._load_stock))
        if has_permission(self._user["role"], "cash.view"):
            self._add_page("cash", W.TablePage("Kassa / Bank",
                                               self._load_cash))
        if has_permission(self._user["role"], "accounting.view"):
            self._add_page("accounts", W.TablePage("Hisoblar rejasi",
                                                   self._load_accounts))
        if has_permission(self._user["role"], "hr.view"):
            self._add_page("employees", W.TablePage("Xodimlar",
                                                    self._load_employees))

        # WebView sahifasi — lazy: haqiqiy QWebEngineView faqat foydalanuvchi
        # birinchi marta "web" sahifasiga o'tganda quriladi (startup tez,
        # native sahifalar Chromium'ga tegmaydi).
        self._web_container = QtWidgets.QWidget()
        self._web_layout = QtWidgets.QVBoxLayout(self._web_container)
        self._web_layout.setContentsMargins(0, 0, 0, 0)
        self._web_built = False
        self._add_page("web", self._web_container)

        # Dastlab dashboard
        self._navigate("dashboard")

    def _add_page(self, key: str, widget: QtWidgets.QWidget) -> None:
        self._pages[key] = self.stack.addWidget(widget)

    def _navigate(self, key: str) -> None:
        if key not in self._pages:
            return
        if key == "web":
            self._ensure_webview()
        self.stack.setCurrentIndex(self._pages[key])
        for k, btn in self._nav_buttons.items():
            btn.setChecked(k == key)
        if key == "dashboard":
            self._refresh_dashboard()

    def _ensure_webview(self) -> None:
        """WebView'ni birinchi so'ralganda quradi (lazy)."""
        if self._web_built:
            return
        self._web_built = True
        self._web_layout.addWidget(self._build_webview())

    # ------------------------------------------------------------------ #
    #  Dashboard (native, QtCharts)
    # ------------------------------------------------------------------ #

    def _build_dashboard(self) -> QtWidgets.QWidget:
        scroll = QtWidgets.QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QtWidgets.QFrame.Shape.NoFrame)
        container = QtWidgets.QWidget()
        self._dash_layout = QtWidgets.QVBoxLayout(container)
        self._dash_layout.setSpacing(14)

        title = QtWidgets.QLabel("Dashboard")
        title.setObjectName("PageTitle")
        self._dash_layout.addWidget(title)

        # KPI kartalar (qatorlar)
        self._stat_cards: dict[str, W.StatCard] = {}
        cards_row = QtWidgets.QHBoxLayout()
        for key, label, accent in (
            ("today_sales", "Bugungi savdo", "accent"),
            ("month_sales", "Oy savdosi", "green"),
            ("month_expenses", "Oy xarajatlari", "red"),
            ("month_profit", "Oy foydasi", "green"),
        ):
            card = W.StatCard(label, "—", accent=accent)
            self._stat_cards[key] = card
            cards_row.addWidget(card)
        self._dash_layout.addLayout(cards_row)

        cards_row2 = QtWidgets.QHBoxLayout()
        for key, label, accent in (
            ("cash_balance", "Kassa", "text"),
            ("bank_balance", "Bank", "accent"),
            ("stock_value", "Ombor qiymati", "amber"),
            ("receivables", "Debitorlik", "text"),
        ):
            card = W.StatCard(label, "—", accent=accent)
            self._stat_cards[key] = card
            cards_row2.addWidget(card)
        self._dash_layout.addLayout(cards_row2)

        # Grafiklar konteyneri (yangilanishda almashtiriladi)
        self._charts_holder = QtWidgets.QVBoxLayout()
        self._dash_layout.addLayout(self._charts_holder)
        self._dash_layout.addStretch()

        scroll.setWidget(container)
        return scroll

    def _refresh_dashboard(self) -> None:
        """Dashboard ma'lumotlari va grafiklarini yangilaydi."""
        if not has_permission(self._user["role"], "dashboard.view"):
            return
        try:
            data = self._ctx.services.get("reports").dashboard()
        except Exception:  # noqa: BLE001
            self._log.exception("Dashboard yangilashda xato")
            return

        for key, card in self._stat_cards.items():
            card.set_value(money(data.get(key, 0)))

        # Grafiklarni qayta chizish
        while self._charts_holder.count():
            item = self._charts_holder.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
            elif item.layout():
                self._clear_layout(item.layout())

        series = data["monthly_series"]
        labels = [s["period"][2:] for s in series]
        row = QtWidgets.QHBoxLayout()
        row.addWidget(W.line_chart(
            "Daromad va xarajat (12 oy)", labels,
            [("Daromad", [s["revenue"] for s in series], COLORS["accent"]),
             ("Xarajat", [s["expense"] for s in series], COLORS["red"])]))
        row.addWidget(W.bar_chart(
            "Oylik foyda", labels,
            [s["profit"] for s in series], COLORS["green"]))
        self._charts_holder.addLayout(row)

        by_type = data.get("sales_by_type", [])
        if by_type:
            pie_items = [(r["doc_type"], float(r["total"])) for r in by_type]
            self._charts_holder.addWidget(
                W.pie_chart("Savdo turlari (joriy oy)", pie_items))

    @staticmethod
    def _clear_layout(layout) -> None:
        while layout.count():
            item = layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

    # ------------------------------------------------------------------ #
    #  WebView (to'liq web ilova, avtomatik login)
    # ------------------------------------------------------------------ #

    def _web_base(self) -> str:
        host = self._ctx.config.get("server.host", "127.0.0.1")
        port = self._ctx.config.get("server.port", 8000)
        return f"http://{host}:{port}/"

    def _build_webview(self) -> QtWidgets.QWidget:
        if not HAS_WEBENGINE:
            lbl = QtWidgets.QLabel(
                "QWebEngine o'rnatilmagan.\n\nTo'liq web interfeys uchun:\n"
                "pip install PyQt6-WebEngine\n\n"
                f"Yoki brauzerda oching: {self._web_base()}")
            lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
            lbl.setStyleSheet(f"color: {COLORS['muted']};")
            return lbl

        self._web_view = QWebEngineView()
        # Sessiya cookie'sini inject qilish -> web avtomatik login bo'ladi
        profile = QWebEngineProfile.defaultProfile()
        cookie = QNetworkCookie(b"uzerp_session",
                                self._session.encode("ascii"))
        cookie.setPath("/")
        host = str(self._ctx.config.get("server.host", "127.0.0.1"))
        cookie.setDomain(host)
        profile.cookieStore().setCookie(cookie, QUrl(self._web_base()))
        self._web_view.setUrl(QUrl(self._web_base()))
        return self._web_view

    # ------------------------------------------------------------------ #
    #  Statusbar
    # ------------------------------------------------------------------ #

    def _build_statusbar(self) -> None:
        bar = self.statusBar()
        engine = self._ctx.db.engine
        bar.showMessage(
            f"Database: {engine}  ·  Web: {self._web_base()}  ·  "
            f"{__app_name__} v{__version__}")

    # ------------------------------------------------------------------ #
    #  Ctrl+K va boshqa amallar
    # ------------------------------------------------------------------ #

    def _open_search(self) -> None:
        dialog = GlobalSearchDialog(self._ctx, self)
        dialog.exec()

    def _open_web(self, path: str) -> None:
        """WebView sahifasiga o'tib, berilgan yo'lni ochadi."""
        if "web" in self._pages:
            self._navigate("web")  # lazy webview shu yerda quriladi
            if self._web_view is not None:
                self._web_view.setUrl(QUrl(self._web_base().rstrip("/") + path))

    def _logout(self) -> None:
        try:
            self._ctx.services.get("auth").logout(self._session)
        except Exception:  # noqa: BLE001
            pass
        self.close()

    # ------------------------------------------------------------------ #
    #  Native jadval yuklovchilari (servisdan)
    # ------------------------------------------------------------------ #

    def _load_sales(self, search: str):
        page = self._ctx.services.get("sales").list_docs(
            per_page=200, search=search or None)
        headers = ["№", "Turi", "Mijoz", "Holat", "Jami", "To'langan", "Sana"]
        rows = [[r["number"], r["doc_type"], r.get("customer_name") or "—",
                 r["status"], r["total"], r["paid_amount"], r["doc_date"]]
                for r in page.items]
        return headers, rows

    def _load_customers(self, search: str):
        page = self._ctx.services.get("customers").list_customers(
            per_page=200, search=search or None)
        headers = ["Nomi", "Telefon", "STIR", "Chegirma %", "Manzil"]
        rows = [[r["name"], r["phone"] or "", r["tin"] or "",
                 r["discount_percent"], r["address"] or ""]
                for r in page.items]
        return headers, rows

    def _load_products(self, search: str):
        page = self._ctx.services.get("products").list_products(
            per_page=200, search=search or None)
        headers = ["SKU", "Nomi", "Shtrix-kod", "Birlik", "Tannarx",
                   "Sotish narxi"]
        rows = [[r["sku"] or "", r["name"], r["barcode"] or "", r["unit"],
                 r["cost_price"], r["sale_price"]] for r in page.items]
        return headers, rows

    def _load_stock(self, search: str):
        page = self._ctx.services.get("inventory").stock_overview(
            per_page=200, search=search or None)
        headers = ["SKU", "Mahsulot", "Qoldiq", "Tannarx", "Qiymat"]
        rows = [[r["sku"] or "", r["name"], r["quantity"], r["cost_price"],
                 r["stock_value"]] for r in page.items]
        return headers, rows

    def _load_cash(self, search: str):
        page = self._ctx.services.get("payments").cashbook(per_page=200)
        headers = ["№", "Turi", "Usul", "Summa", "Izoh", "Sana"]
        rows = [[r["number"], r["payment_type"], r["method"], r["amount"],
                 r["note"] or "", r["payment_date"]] for r in page.items]
        return headers, rows

    def _load_accounts(self, search: str):
        accounting = self._ctx.services.get("accounting")
        headers = ["Kod", "Nomi", "Turi", "Qoldiq"]
        rows = [[a["code"], a["name"], a["type"],
                 accounting.account_balance(a["code"])]
                for a in accounting.accounts()]
        return headers, rows

    def _load_employees(self, search: str):
        page = self._ctx.services.get("hr").list_employees(
            per_page=200, search=search or None)
        headers = ["Kod", "F.I.Sh.", "Lavozim", "Telefon", "Maosh", "Holat"]
        rows = [[r["code"] or "", r["full_name"], r["position"] or "",
                 r["phone"] or "", r["salary"], r["status"]]
                for r in page.items]
        return headers, rows


def run_desktop(ctx) -> int:
    """
    Desktop GUI ni ishga tushiradi (app.py dan chaqiriladi).

    Web-server allaqachon fon oqimda ishlab turadi (WebView shunga ulanadi).
    """
    import sys

    app = QtWidgets.QApplication.instance() or QtWidgets.QApplication(sys.argv)
    app.setApplicationName(__app_name__)
    app.setStyleSheet(QSS)

    login = LoginDialog(ctx)
    if login.exec() != QtWidgets.QDialog.DialogCode.Accepted:
        return 0

    window = MainWindow(ctx, login.result_user, login.result_session)
    window.show()
    return app.exec()
