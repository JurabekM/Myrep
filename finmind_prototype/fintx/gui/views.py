"""Desktop oynalari: kirish, umumiy ko'rinish, tranzaksiyalar, xavfsizlik.

Interfeys hech narsani o'zi tekshirmaydi va bazaga tegmaydi: maydonlardagi xom
matn `fintx.app.App` xizmatlariga uzatiladi, xato matnlari esa o'sha yerdan keladi.
Shu sabab terminal va desktopda qoidalar bir xil.

Bazadan o'qilgan matn faqat oddiy matn sifatida ko'rsatiladi (`PlainText`,
jadval kataklari); Qt'ning "rich text"ni avtomatik aniqlashiga yo'l qo'yilmaydi,
aks holda izohdagi `<img ...>` kabi teglar HTML sifatida talqin qilinardi.
"""

from __future__ import annotations

import calendar
import html
from collections.abc import Callable
from datetime import date, datetime
from decimal import Decimal

from PySide6.QtCore import QDate, QEvent, QObject, QRectF, Qt, QTimer
from PySide6.QtGui import QColor, QPainter
from PySide6.QtWidgets import (
    QAbstractItemView,
    QApplication,
    QButtonGroup,
    QComboBox,
    QDateEdit,
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QSizePolicy,
    QStackedWidget,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from ..app import App
from ..auth import IDLE_TIMEOUT_SECONDS, MAX_FAILED_ATTEMPTS, Session
from ..errors import FinTxError, SessionExpired
from ..money import CURRENCY, format_amount, format_percent
from ..transactions import HISTORY_LIMIT_MAX
from ..validation import (
    CATEGORIES,
    KIND_EXPENSE,
    KIND_INCOME,
    KIND_LABELS,
    MIN_DATE,
    NOTE_MAX,
    PASSWORD_MIN,
    category_label,
    printable,
)
from . import theme

_RIGHT = Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter
_LEFT = Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter
_ID_ROLE = Qt.ItemDataRole.UserRole

PERIODS = (
    ("all", "Butun tarix"),
    ("month", "Shu oy"),
    ("prev_month", "O'tgan oy"),
    ("year", "Shu yil"),
)


def period_bounds(key: str, today: date) -> tuple[date | None, date | None]:
    """Davr tanlovini sana oralig'iga aylantiradi (ikkala chegara ham kiradi)."""
    if key == "month":
        last = calendar.monthrange(today.year, today.month)[1]
        return today.replace(day=1), today.replace(day=last)
    if key == "prev_month":
        year, month = (today.year, today.month - 1) if today.month > 1 else (today.year - 1, 12)
        return date(year, month, 1), date(year, month, calendar.monthrange(year, month)[1])
    if key == "year":
        return date(today.year, 1, 1), date(today.year, 12, 31)
    return None, None


# --- kichik yordamchilar -------------------------------------------------------


def make_label(text: str = "", name: str | None = None, *, wrap: bool = False) -> QLabel:
    label = QLabel(text)
    label.setTextFormat(Qt.TextFormat.PlainText)
    label.setWordWrap(wrap)
    if name:
        label.setObjectName(name)
    return label


def make_card() -> tuple[QFrame, QVBoxLayout]:
    card = QFrame()
    card.setObjectName("card")
    layout = QVBoxLayout(card)
    layout.setContentsMargins(18, 16, 18, 16)
    layout.setSpacing(10)
    return card, layout


def make_field(placeholder: str = "", *, secret: bool = False, max_length: int = 64) -> QLineEdit:
    field = QLineEdit()
    field.setPlaceholderText(placeholder)
    field.setMaxLength(max_length)
    if secret:
        field.setEchoMode(QLineEdit.EchoMode.Password)
    return field


def make_segments(options: list[tuple[str, str]]) -> tuple[QWidget, QButtonGroup]:
    """Ikki-uch variantli almashtirgich; tanlov `checkedButton().property('key')`."""
    holder = QWidget()
    row = QHBoxLayout(holder)
    row.setContentsMargins(0, 0, 0, 0)
    row.setSpacing(0)
    group = QButtonGroup(holder)
    group.setExclusive(True)
    for index, (key, text) in enumerate(options):
        button = QPushButton(text)
        button.setObjectName("segment")
        button.setCheckable(True)
        button.setProperty("key", key)
        button.setChecked(index == 0)
        button.setFocusPolicy(Qt.FocusPolicy.TabFocus)
        group.addButton(button)
        row.addWidget(button, 1)
    return holder, group


def make_table(headers: list[str], stretch_columns: set[int]) -> QTableWidget:
    table = QTableWidget(0, len(headers))
    table.setHorizontalHeaderLabels(headers)
    table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
    table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
    table.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
    table.setShowGrid(False)
    table.verticalHeader().setVisible(False)
    table.verticalHeader().setDefaultSectionSize(34)
    header = table.horizontalHeader()
    header.setHighlightSections(False)
    header.setDefaultAlignment(_LEFT)
    header.setSectionResizeMode(QHeaderView.ResizeMode.ResizeToContents)
    for column in stretch_columns:
        header.setSectionResizeMode(column, QHeaderView.ResizeMode.Stretch)
    return table


def fill_table(table: QTableWidget, rows: list[list[str]], right_columns: set[int]) -> None:
    table.setRowCount(len(rows))
    for r, row in enumerate(rows):
        for c, text in enumerate(row):
            item = QTableWidgetItem(printable(text))
            item.setTextAlignment(_RIGHT if c in right_columns else _LEFT)
            item.setToolTip(html.escape(printable(text)))
            table.setItem(r, c, item)
    for c in right_columns:
        header_item = table.horizontalHeaderItem(c)
        if header_item is not None:
            header_item.setTextAlignment(_RIGHT)


def set_message(label: QLabel, text: str, *, ok: bool = False) -> None:
    label.setObjectName("success" if ok else "error")
    label.setText(text)
    label.setVisible(bool(text))
    # objectName o'zgargach uslub qayta qo'llanishi kerak.
    label.style().unpolish(label)
    label.style().polish(label)


class Bar(QWidget):
    """Bitta gorizontal ustun: ulush (0..1) bo'yicha to'ldirilgan ingichka chiziq."""

    def __init__(self, fraction: float) -> None:
        super().__init__()
        self._fraction = max(0.0, min(1.0, fraction))
        self.setFixedHeight(8)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)

    def paintEvent(self, _event: object) -> None:
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setPen(Qt.PenStyle.NoPen)
        radius = self.height() / 2
        painter.setBrush(QColor(theme.LINE))
        painter.drawRoundedRect(QRectF(0, 0, self.width(), self.height()), radius, radius)
        if self._fraction > 0:
            width = max(self.height(), self.width() * self._fraction)
            painter.setBrush(QColor(theme.CHART))
            painter.drawRoundedRect(QRectF(0, 0, width, self.height()), radius, radius)
        painter.end()


class BarList(QWidget):
    """Kategoriyalar ulushi: nom va qiymat matn bilan, ulush — ustun uzunligi bilan."""

    def __init__(self) -> None:
        super().__init__()
        self._layout = QVBoxLayout(self)
        self._layout.setContentsMargins(0, 0, 0, 0)
        self._layout.setSpacing(12)

    def set_rows(self, rows: list[tuple[str, int, Decimal]]) -> None:
        while self._layout.count():
            item = self._layout.takeAt(0)
            widget = item.widget()
            if widget is not None:
                widget.deleteLater()
        for name, amount_minor, share in rows:
            value = f"{format_amount(amount_minor)} {CURRENCY}  ·  {format_percent(share)}"
            row = QWidget()
            row.setToolTip(html.escape(f"{printable(name)}: {value}"))
            grid = QGridLayout(row)
            grid.setContentsMargins(0, 0, 0, 0)
            grid.setVerticalSpacing(5)
            grid.addWidget(make_label(printable(name)), 0, 0)
            grid.addWidget(make_label(value, "muted"), 0, 1, _RIGHT)
            grid.addWidget(Bar(float(share) / 100), 1, 0, 1, 2)
            self._layout.addWidget(row)
        self._layout.addStretch(1)


# --- umumiy kontekst ---------------------------------------------------------


class Context:
    """Sahifalar uchun umumiy holat: yadro, joriy sessiya va xatolarni ko'rsatish."""

    def __init__(self, app: App, on_session_lost: Callable[[str], None]) -> None:
        self.app = app
        self.session: Session | None = None
        self._on_session_lost = on_session_lost

    def run(self, action: Callable[[], object], message: QLabel | None = None) -> bool:
        """Amalni bajaradi. Kutilgan xato — yozuvda; sessiya tugasa — kirish oynasiga."""
        if message is not None:
            set_message(message, "")
        try:
            action()
        except SessionExpired as exc:
            self._on_session_lost(str(exc))
            return False
        except FinTxError as exc:
            if message is not None:
                set_message(message, str(exc))
            return False
        return True


# --- kirish va ro'yxatdan o'tish ---------------------------------------------


class AuthView(QWidget):
    def __init__(self, ctx: Context, on_login: Callable[[Session], None]) -> None:
        super().__init__()
        self.setObjectName("paper")
        self._ctx = ctx
        self._on_login = on_login

        card, body = make_card()
        card.setFixedWidth(400)
        body.setSpacing(12)
        body.addWidget(make_label("FinTx", "brand"))
        body.addWidget(make_label("Moliyaviy tranzaksiyalar prototipi", "muted"))

        segments, self._mode = make_segments(
            [("login", "Kirish"), ("register", "Ro'yxatdan o'tish")]
        )
        self._mode.buttonClicked.connect(lambda _button: self._sync_mode())
        body.addWidget(segments)

        self.username = make_field("Login")
        self.password = make_field("Parol", secret=True, max_length=256)
        self.repeat = make_field("Parolni takrorlang", secret=True, max_length=256)
        self._hint = make_label(
            f"Parol kamida {PASSWORD_MIN} belgi bo'lsin. Uzun ibora — eng yaxshi tanlov.",
            "muted",
            wrap=True,
        )
        self.message = make_label("", "error", wrap=True)
        self.submit_button = QPushButton("Kirish")
        self.submit_button.setObjectName("primary")
        self.submit_button.clicked.connect(self.submit)
        for field in (self.username, self.password, self.repeat):
            field.returnPressed.connect(self.submit)

        body.addWidget(make_label("Login", "fieldLabel"))
        body.addWidget(self.username)
        body.addWidget(make_label("Parol", "fieldLabel"))
        body.addWidget(self.password)
        body.addWidget(self.repeat)
        body.addWidget(self._hint)
        body.addWidget(self.message)
        body.addWidget(self.submit_button)

        outer = QVBoxLayout(self)
        outer.addStretch(1)
        outer.addWidget(card, 0, Qt.AlignmentFlag.AlignHCenter)
        outer.addStretch(1)
        self._sync_mode()

    def mode(self) -> str:
        return str(self._mode.checkedButton().property("key"))

    def set_mode(self, key: str) -> None:
        for button in self._mode.buttons():
            button.setChecked(button.property("key") == key)
        self._sync_mode()

    def _sync_mode(self) -> None:
        registering = self.mode() == "register"
        self.repeat.setVisible(registering)
        self._hint.setVisible(registering)
        self.submit_button.setText("Hisob yaratish" if registering else "Kirish")
        set_message(self.message, "")

    def show_notice(self, text: str, *, ok: bool = False) -> None:
        set_message(self.message, text, ok=ok)

    def submit(self) -> None:
        username = self.username.text()
        password = self.password.text()
        repeat = self.repeat.text()
        # Parol maydonlari natijadan qat'i nazar darhol tozalanadi.
        self.password.clear()
        self.repeat.clear()

        if self.mode() == "register":
            if password != repeat:
                set_message(self.message, "Parollar mos kelmadi.")
                return
            if self._hashing(lambda: self._ctx.app.auth.register(username, password)):
                self.set_mode("login")
                set_message(self.message, "Hisob yaratildi. Endi tizimga kiring.", ok=True)
                self.password.setFocus()
            return

        sessions: list[Session] = []
        if self._hashing(lambda: sessions.append(self._ctx.app.auth.login(username, password))):
            self.username.clear()
            self._on_login(sessions[0])

    def _hashing(self, action: Callable[[], object]) -> bool:
        """Parol xeshlash taxminan yarim soniya oladi — kutish kursorini ko'rsatamiz."""
        QApplication.setOverrideCursor(Qt.CursorShape.WaitCursor)
        try:
            return self._ctx.run(action, self.message)
        finally:
            QApplication.restoreOverrideCursor()


# --- umumiy ko'rinish --------------------------------------------------------


class KpiCard(QFrame):
    def __init__(self, title: str, unit: str) -> None:
        super().__init__()
        self.setObjectName("card")
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 14, 16, 14)
        layout.setSpacing(4)
        layout.addWidget(make_label(title, "muted"))
        self.value = make_label("—", "kpiValue")
        layout.addWidget(self.value)
        layout.addWidget(make_label(unit, "kpiUnit"))


def make_period_combo() -> QComboBox:
    combo = QComboBox()
    for key, text in PERIODS:
        combo.addItem(text, key)
    return combo


class DashboardPage(QWidget):
    def __init__(self, ctx: Context) -> None:
        super().__init__()
        self._ctx = ctx
        root = QVBoxLayout(self)
        root.setContentsMargins(28, 24, 28, 24)
        root.setSpacing(16)

        top = QHBoxLayout()
        top.addWidget(make_label("Umumiy ko'rinish", "pageTitle"))
        top.addStretch(1)
        self.period = make_period_combo()
        self.period.currentIndexChanged.connect(lambda _index: self.refresh())
        self.initial_focus = self.period
        top.addWidget(self.period)
        root.addLayout(top)

        self.message = make_label("", "error", wrap=True)
        self.message.setVisible(False)
        root.addWidget(self.message)

        kpis = QHBoxLayout()
        kpis.setSpacing(12)
        self.income = KpiCard("Daromad", CURRENCY)
        self.expense = KpiCard("Xarajat", CURRENCY)
        self.balance = KpiCard("Balans", CURRENCY)
        self.savings = KpiCard("Jamg'arma ulushi", "daromaddan")
        for card in (self.income, self.expense, self.balance, self.savings):
            kpis.addWidget(card, 1)
        root.addLayout(kpis)

        panels = QHBoxLayout()
        panels.setSpacing(12)
        categories_card, categories = make_card()
        categories.addWidget(make_label("Xarajatlar kategoriya bo'yicha", "cardTitle"))
        self.categories_empty = make_label("Bu davrda xarajat yo'q.", "muted")
        categories.addWidget(self.categories_empty)
        self.bars = BarList()
        categories.addWidget(self.bars, 1)
        panels.addWidget(categories_card, 1)

        monthly_card, monthly = make_card()
        monthly.addWidget(make_label("Oylar bo'yicha", "cardTitle"))
        self.monthly = make_table(
            ["Oy", f"Daromad, {CURRENCY}", f"Xarajat, {CURRENCY}", f"Farq, {CURRENCY}"],
            {1, 2, 3},
        )
        monthly.addWidget(self.monthly, 1)
        panels.addWidget(monthly_card, 1)
        root.addLayout(panels, 1)

    def refresh(self) -> None:
        session = self._ctx.session
        if session is None:
            return
        start, end = period_bounds(self.period.currentData(), self._ctx.app.today())

        def load() -> None:
            report = self._ctx.app.report(session, date_from=start, date_to=end)
            self.income.value.setText(format_amount(report.income_minor))
            self.expense.value.setText(format_amount(report.expense_minor))
            self.balance.value.setText(format_amount(report.balance_minor, signed=True))
            self.savings.value.setText(
                "—" if report.savings_rate is None else format_percent(report.savings_rate)
            )
            self.bars.set_rows(
                [
                    (category_label(KIND_EXPENSE, s.category), s.amount_minor, s.percent)
                    for s in report.expense_by_category
                ]
            )
            self.categories_empty.setVisible(not report.expense_by_category)
            fill_table(
                self.monthly,
                [
                    [
                        m.month,
                        format_amount(m.income_minor),
                        format_amount(m.expense_minor),
                        format_amount(m.net_minor, signed=True),
                    ]
                    for m in report.monthly
                ],
                right_columns={1, 2, 3},
            )

        self._ctx.run(load, self.message)


# --- tranzaksiyalar ----------------------------------------------------------


class TransactionsPage(QWidget):
    def __init__(self, ctx: Context) -> None:
        super().__init__()
        self._ctx = ctx
        root = QVBoxLayout(self)
        root.setContentsMargins(28, 24, 28, 24)
        root.setSpacing(16)
        root.addWidget(make_label("Tranzaksiyalar", "pageTitle"))

        columns = QHBoxLayout()
        columns.setSpacing(12)
        columns.addWidget(self._build_form(), 0)
        columns.addWidget(self._build_history(), 1)
        root.addLayout(columns, 1)
        self._sync_categories()
        self.initial_focus = self.amount

    def _build_form(self) -> QFrame:
        card, form = make_card()
        card.setFixedWidth(320)
        form.addWidget(make_label("Yangi tranzaksiya", "cardTitle"))

        segments, self._kind = make_segments(
            [(KIND_EXPENSE, KIND_LABELS[KIND_EXPENSE]), (KIND_INCOME, KIND_LABELS[KIND_INCOME])]
        )
        self._kind.buttonClicked.connect(lambda _button: self._sync_categories())
        form.addWidget(segments)

        self.amount = make_field("masalan: 125 000,50", max_length=32)
        self.category = QComboBox()
        today = self._ctx.app.today()
        self.date = QDateEdit(QDate(today.year, today.month, today.day))
        self.date.setDisplayFormat("yyyy-MM-dd")
        self.date.setCalendarPopup(True)
        self.date.setMinimumDate(QDate(MIN_DATE.year, MIN_DATE.month, MIN_DATE.day))
        self.date.setMaximumDate(QDate(today.year, today.month, today.day))
        self.note = make_field("ixtiyoriy", max_length=NOTE_MAX)
        self.form_message = make_label("", "error", wrap=True)
        self.form_message.setVisible(False)
        self.save_button = QPushButton("Saqlash")
        self.save_button.setObjectName("primary")
        self.save_button.clicked.connect(self.save)
        self.amount.returnPressed.connect(self.save)
        self.note.returnPressed.connect(self.save)

        for title, widget in (
            (f"Summa, {CURRENCY}", self.amount),
            ("Kategoriya", self.category),
            ("Sana", self.date),
            ("Izoh", self.note),
        ):
            form.addWidget(make_label(title, "fieldLabel"))
            form.addWidget(widget)
        form.addWidget(self.form_message)
        form.addWidget(self.save_button)
        form.addStretch(1)
        return card

    def _build_history(self) -> QFrame:
        card, history = make_card()
        top = QHBoxLayout()
        top.addWidget(make_label("Tarix", "cardTitle"))
        top.addStretch(1)
        self.kind_filter = QComboBox()
        self.kind_filter.addItem("Hammasi", "")
        self.kind_filter.addItem(KIND_LABELS[KIND_INCOME], KIND_INCOME)
        self.kind_filter.addItem(KIND_LABELS[KIND_EXPENSE], KIND_EXPENSE)
        self.period = make_period_combo()
        self.kind_filter.currentIndexChanged.connect(lambda _index: self.refresh())
        self.period.currentIndexChanged.connect(lambda _index: self.refresh())
        top.addWidget(self.kind_filter)
        top.addWidget(self.period)
        history.addLayout(top)

        self.table = make_table(["Sana", "Turi", "Kategoriya", f"Summa, {CURRENCY}", "Izoh"], {4})
        history.addWidget(self.table, 1)

        bottom = QHBoxLayout()
        self.count = make_label("", "muted")
        self.history_message = make_label("", "error", wrap=True)
        self.history_message.setVisible(False)
        self.delete_button = QPushButton("Tanlanganni o'chirish")
        self.delete_button.setObjectName("danger")
        self.delete_button.clicked.connect(self.delete_selected)
        bottom.addWidget(self.count)
        bottom.addWidget(self.history_message, 1)
        bottom.addWidget(self.delete_button)
        history.addLayout(bottom)
        return card

    def kind(self) -> str:
        return str(self._kind.checkedButton().property("key"))

    def set_kind(self, kind: str) -> None:
        for button in self._kind.buttons():
            button.setChecked(button.property("key") == kind)
        self._sync_categories()

    def _sync_categories(self) -> None:
        self.category.clear()
        for key, text in CATEGORIES[self.kind()].items():
            self.category.addItem(text, key)

    def save(self) -> None:
        session = self._ctx.session
        if session is None:
            return
        saved = self._ctx.run(
            lambda: self._ctx.app.transactions.add(
                session,
                kind=self.kind(),
                amount=self.amount.text(),
                category=self.category.currentData(),
                occurred_on=self.date.date().toString("yyyy-MM-dd"),
                note=self.note.text(),
            ),
            self.form_message,
        )
        if saved:
            self.amount.clear()
            self.note.clear()
            set_message(self.form_message, "Saqlandi.", ok=True)
            self.amount.setFocus()
            self.refresh()

    def refresh(self) -> None:
        session = self._ctx.session
        if session is None:
            return
        start, end = period_bounds(self.period.currentData(), self._ctx.app.today())

        def load() -> None:
            rows = self._ctx.app.transactions.history(
                session,
                kind=self.kind_filter.currentData(),
                date_from=start,
                date_to=end,
                limit=HISTORY_LIMIT_MAX,
            )
            fill_table(
                self.table,
                [
                    [
                        tx.occurred_on.isoformat(),
                        KIND_LABELS[tx.kind],
                        category_label(tx.kind, tx.category),
                        format_amount(tx.signed_minor, signed=True),
                        tx.note,
                    ]
                    for tx in rows
                ],
                right_columns={3},
            )
            for index, tx in enumerate(rows):
                self.table.item(index, 0).setData(_ID_ROLE, tx.id)
            suffix = " (eng yangilari)" if len(rows) == HISTORY_LIMIT_MAX else ""
            self.count.setText(f"{len(rows)} ta yozuv{suffix}")

        self._ctx.run(load, self.history_message)

    def delete_selected(self) -> None:
        session = self._ctx.session
        row = self.table.currentRow()
        if session is None:
            return
        if row < 0:
            set_message(self.history_message, "Avval jadvaldan qatorni tanlang.")
            return
        transaction_id = self.table.item(row, 0).data(_ID_ROLE)
        answer = QMessageBox.question(
            self,
            "Tranzaksiyani o'chirish",
            "Tanlangan tranzaksiya o'chirilsinmi? Bu amalni ortga qaytarib bo'lmaydi.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )
        if answer != QMessageBox.StandardButton.Yes:
            return
        if self._ctx.run(
            lambda: self._ctx.app.transactions.delete(session, transaction_id),
            self.history_message,
        ):
            self.refresh()


# --- xavfsizlik ----------------------------------------------------------------


def _local_time(stamp: str) -> str:
    try:
        return datetime.fromisoformat(stamp).astimezone().strftime("%Y-%m-%d %H:%M:%S")
    except ValueError:
        return stamp


class SecurityPage(QWidget):
    def __init__(self, ctx: Context) -> None:
        super().__init__()
        self._ctx = ctx
        root = QVBoxLayout(self)
        root.setContentsMargins(28, 24, 28, 24)
        root.setSpacing(16)
        root.addWidget(make_label("Xavfsizlik", "pageTitle"))

        columns = QHBoxLayout()
        columns.setSpacing(12)

        card, form = make_card()
        card.setFixedWidth(320)
        form.addWidget(make_label("Parolni o'zgartirish", "cardTitle"))
        self.current = make_field(secret=True, max_length=256)
        self.initial_focus = self.current
        self.new = make_field(secret=True, max_length=256)
        self.repeat = make_field(secret=True, max_length=256)
        for title, field in (
            ("Joriy parol", self.current),
            ("Yangi parol", self.new),
            ("Yangi parolni takrorlang", self.repeat),
        ):
            form.addWidget(make_label(title, "fieldLabel"))
            form.addWidget(field)
            field.returnPressed.connect(self.change_password)
        self.message = make_label("", "error", wrap=True)
        self.message.setVisible(False)
        form.addWidget(self.message)
        self.change_button = QPushButton("Parolni o'zgartirish")
        self.change_button.setObjectName("primary")
        self.change_button.clicked.connect(self.change_password)
        form.addWidget(self.change_button)
        form.addWidget(
            make_label(
                f"Sessiya {int(IDLE_TIMEOUT_SECONDS // 60)} daqiqa harakatsizlikdan keyin "
                f"yopiladi. Ketma-ket {MAX_FAILED_ATTEMPTS} ta xato parol hisobni "
                "vaqtincha qulflaydi.",
                "muted",
                wrap=True,
            )
        )
        form.addStretch(1)
        columns.addWidget(card, 0)

        log_card, log = make_card()
        log.addWidget(make_label("Xavfsizlik jurnali", "cardTitle"))
        self.audit_message = make_label("", "error", wrap=True)
        self.audit_message.setVisible(False)
        log.addWidget(self.audit_message)
        self.audit = make_table(["Vaqt", "Hodisa", "Tafsilot"], {1})
        log.addWidget(self.audit, 1)
        columns.addWidget(log_card, 1)
        root.addLayout(columns, 1)

    def change_password(self) -> None:
        session = self._ctx.session
        if session is None:
            return
        current, new, repeat = self.current.text(), self.new.text(), self.repeat.text()
        for field in (self.current, self.new, self.repeat):
            field.clear()
        if new != repeat:
            set_message(self.message, "Yangi parollar mos kelmadi.")
            return
        QApplication.setOverrideCursor(Qt.CursorShape.WaitCursor)
        try:
            changed = self._ctx.run(
                lambda: self._ctx.app.auth.change_password(session, current, new),
                self.message,
            )
        finally:
            QApplication.restoreOverrideCursor()
        if changed:
            set_message(self.message, "Parol o'zgartirildi.", ok=True)
        self.refresh()

    def refresh(self) -> None:
        session = self._ctx.session
        if session is None:
            return

        def load() -> None:
            events = self._ctx.app.auth.audit_events(session, limit=50)
            fill_table(
                self.audit,
                [[_local_time(e.at), e.label, e.detail] for e in events],
                right_columns=set(),
            )

        self._ctx.run(load, self.audit_message)


# --- asosiy oyna ---------------------------------------------------------------

_ACTIVITY_EVENTS = frozenset(
    {QEvent.Type.KeyPress, QEvent.Type.MouseButtonPress, QEvent.Type.Wheel}
)


class MainWindow(QMainWindow):
    def __init__(self, app: App) -> None:
        super().__init__()
        self.setWindowTitle("FinTx")
        self.resize(1240, 780)
        self.setMinimumSize(1100, 660)
        self.ctx = Context(app, self._session_lost)

        self._stack = QStackedWidget()
        self.auth_view = AuthView(self.ctx, self._enter)
        self._stack.addWidget(self.auth_view)
        self._stack.addWidget(self._build_shell())
        self.setCentralWidget(self._stack)

        # Harakatsizlik nazorati: kiritish hodisalari sessiyani uzaytiradi,
        # taymer esa muddati o'tgan sessiyani ekran ochiq tursa ham yopadi.
        self._idle_timer = QTimer(self)
        self._idle_timer.setInterval(5_000)
        self._idle_timer.timeout.connect(self._check_idle)
        self._idle_timer.start()
        QApplication.instance().installEventFilter(self)

    def _build_shell(self) -> QWidget:
        shell = QWidget()
        shell.setObjectName("paper")
        row = QHBoxLayout(shell)
        row.setContentsMargins(0, 0, 0, 0)
        row.setSpacing(0)

        sidebar = QWidget()
        sidebar.setObjectName("sidebar")
        sidebar.setFixedWidth(220)
        side = QVBoxLayout(sidebar)
        side.setContentsMargins(14, 20, 14, 16)
        side.setSpacing(6)
        side.addWidget(make_label("FinTx", "brand"))
        self.user_label = make_label("", "muted")
        side.addWidget(self.user_label)
        side.addSpacing(14)

        self.dashboard = DashboardPage(self.ctx)
        self.transactions = TransactionsPage(self.ctx)
        self.security = SecurityPage(self.ctx)
        self.pages = QStackedWidget()
        self._nav = QButtonGroup(self)
        self._nav.setExclusive(True)
        for index, (title, page) in enumerate(
            (
                ("Umumiy ko'rinish", self.dashboard),
                ("Tranzaksiyalar", self.transactions),
                ("Xavfsizlik", self.security),
            )
        ):
            self.pages.addWidget(page)
            button = QPushButton(title)
            button.setObjectName("nav")
            button.setCheckable(True)
            button.setFocusPolicy(Qt.FocusPolicy.TabFocus)
            self._nav.addButton(button, index)
            side.addWidget(button)
        self._nav.idClicked.connect(self.show_page)
        side.addStretch(1)
        self.logout_button = QPushButton("Tizimdan chiqish")
        self.logout_button.clicked.connect(self.logout)
        side.addWidget(self.logout_button)

        row.addWidget(sidebar)
        row.addWidget(self.pages, 1)
        return shell

    # --- sessiya ---------------------------------------------------------------

    def _enter(self, session: Session) -> None:
        self.ctx.session = session
        self.user_label.setText(printable(session.username))
        self._stack.setCurrentIndex(1)
        self.show_page(0)

    def show_page(self, index: int) -> None:
        self._nav.button(index).setChecked(True)
        self.pages.setCurrentIndex(index)
        page = self.pages.currentWidget()
        page.refresh()
        # Klaviatura fokusi sahifaning birinchi maydoniga o'tadi (yon panelda qolmaydi).
        page.initial_focus.setFocus()

    def _leave(self, notice: str = "", *, ok: bool = False) -> None:
        """Kirish oynasiga qaytadi va ekrandagi shaxsiy ma'lumotlarni tozalaydi."""
        self.ctx.session = None
        self.user_label.setText("")
        for table in (self.dashboard.monthly, self.transactions.table, self.security.audit):
            table.setRowCount(0)
        self.dashboard.bars.set_rows([])
        for card in (
            self.dashboard.income,
            self.dashboard.expense,
            self.dashboard.balance,
            self.dashboard.savings,
        ):
            card.value.setText("—")
        for field in (
            self.transactions.amount,
            self.transactions.note,
            self.security.current,
            self.security.new,
            self.security.repeat,
        ):
            field.clear()
        self._stack.setCurrentIndex(0)
        self.auth_view.set_mode("login")
        self.auth_view.show_notice(notice, ok=ok)

    def logout(self) -> None:
        if self.ctx.session is not None:
            self.ctx.app.auth.logout(self.ctx.session)
        self._leave("Tizimdan chiqdingiz.", ok=True)

    def _session_lost(self, message: str) -> None:
        self._leave(message)

    def _check_idle(self) -> None:
        session = self.ctx.session
        if session is not None and self.ctx.app.auth.is_expired(session):
            self.ctx.run(lambda: self.ctx.app.auth.require(session))

    def eventFilter(self, watched: QObject, event: QEvent) -> bool:
        session = self.ctx.session
        if session is not None and event.type() in _ACTIVITY_EVENTS:
            # Muddati o'tgan bo'lsa, shu yerning o'zida kirish oynasiga qaytadi.
            self.ctx.run(lambda: self.ctx.app.auth.require(session))
        return super().eventFilter(watched, event)

    def closeEvent(self, event: QEvent) -> None:
        if self.ctx.session is not None:
            self.ctx.app.auth.logout(self.ctx.session)
            self.ctx.session = None
        super().closeEvent(event)
