"""Desktop interfeys: oynasiz (offscreen) rejimda asosiy oqimlar.

PySide6 o'rnatilmagan bo'lsa, bu testlar o'tkazib yuboriladi — yadro va
terminal testlari PySide6'ga bog'liq emas.
"""

from __future__ import annotations

import os
import unittest
from unittest import mock

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

try:
    from PySide6.QtCore import Qt
    from PySide6.QtWidgets import QApplication, QLabel, QMessageBox
except ImportError:  # pragma: no cover — muhitga bog'liq
    QApplication = None  # type: ignore[assignment,misc]

from fintx.auth import IDLE_TIMEOUT_SECONDS

from .helpers import PASSWORD, FakeClock, make_app


@unittest.skipIf(QApplication is None, "PySide6 o'rnatilmagan")
class GuiTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        from fintx.gui.theme import apply_theme

        cls.qt = QApplication.instance() or QApplication([])
        apply_theme(cls.qt)

    def setUp(self) -> None:
        from fintx.gui.views import MainWindow

        self.clock = FakeClock()
        self.core = make_app(clock=self.clock)
        self.window = MainWindow(self.core)
        self.window.show()
        self.addCleanup(self.core.close)
        self.addCleanup(self.window.close)
        self.auth = self.window.auth_view

    def register(self, username: str = "jurabek", password: str = PASSWORD) -> None:
        self.auth.set_mode("register")
        self.auth.username.setText(username)
        self.auth.password.setText(password)
        self.auth.repeat.setText(password)
        self.auth.submit()

    def login(self, username: str = "jurabek", password: str = PASSWORD) -> None:
        self.auth.set_mode("login")
        self.auth.username.setText(username)
        self.auth.password.setText(password)
        self.auth.submit()

    def enter(self) -> None:
        self.register()
        self.login()
        self.assertIsNotNone(self.window.ctx.session)

    def add(self, amount: str, note: str = "", kind: str = "expense") -> None:
        page = self.window.transactions
        page.set_kind(kind)
        page.amount.setText(amount)
        page.note.setText(note)
        page.save()

    def test_register_login_and_record(self) -> None:
        self.register()
        self.assertEqual(self.auth.mode(), "login")
        self.assertIn("Hisob yaratildi", self.auth.message.text())
        self.login()
        self.assertEqual(self.window.user_label.text(), "jurabek")

        self.window.show_page(1)
        self.add("12 500 000,50", "Maosh", kind="income")
        self.add("350000", "Bozor")
        table = self.window.transactions.table
        self.assertEqual(table.rowCount(), 2)
        self.assertEqual(self.window.transactions.amount.text(), "")

        self.window.show_page(0)
        dashboard = self.window.dashboard
        self.assertEqual(dashboard.income.value.text(), "12 500 000,50")
        self.assertEqual(dashboard.expense.value.text(), "350 000,00")
        self.assertEqual(dashboard.balance.value.text(), "+12 150 000,50")
        self.assertEqual(dashboard.savings.value.text(), "97,2 %")
        self.assertEqual(dashboard.monthly.rowCount(), 1)

    def test_password_fields_are_cleared_and_errors_are_generic(self) -> None:
        self.register()
        self.login(password="xato-parol-xato-parol")
        self.assertIsNone(self.window.ctx.session)
        self.assertEqual(self.auth.password.text(), "")
        self.assertEqual(self.auth.message.text(), "Login yoki parol noto'g'ri.")
        self.login(username="begona", password="xato-parol-xato-parol")
        self.assertEqual(self.auth.message.text(), "Login yoki parol noto'g'ri.")

    def test_registration_mismatch_and_weak_password(self) -> None:
        self.auth.set_mode("register")
        self.auth.username.setText("jurabek")
        self.auth.password.setText(PASSWORD)
        self.auth.repeat.setText(PASSWORD + "x")
        self.auth.submit()
        self.assertEqual(self.auth.message.text(), "Parollar mos kelmadi.")
        self.register(password="qisqa")
        self.assertIn("kamida", self.auth.message.text())
        count = self.core.conn.execute("SELECT COUNT(*) FROM users").fetchone()[0]
        self.assertEqual(count, 0)

    def test_invalid_amount_is_reported_and_nothing_saved(self) -> None:
        self.enter()
        self.window.show_page(1)
        self.add("-5")
        page = self.window.transactions
        self.assertIn("Summa noto'g'ri", page.form_message.text())
        self.assertEqual(page.table.rowCount(), 0)
        self.assertEqual(page.amount.text(), "-5")  # tuzatish uchun qoldiriladi

    def test_user_text_is_never_rendered_as_rich_text(self) -> None:
        self.enter()
        self.window.show_page(1)
        payload = '<b>qalin</b><img src="file:///etc/passwd">'
        self.add("1000", payload)
        item = self.window.transactions.table.item(0, 4)
        self.assertEqual(item.text(), payload)
        self.assertIn("&lt;b&gt;", item.toolTip())
        for label in self.window.findChildren(QLabel):
            self.assertEqual(label.textFormat(), Qt.TextFormat.PlainText, label.objectName())

    def test_delete_requires_confirmation(self) -> None:
        self.enter()
        self.window.show_page(1)
        self.add("1000", "birinchi")
        page = self.window.transactions
        page.delete_selected()
        self.assertIn("qatorni tanlang", page.history_message.text())
        page.table.selectRow(0)
        with mock.patch.object(QMessageBox, "question", return_value=QMessageBox.StandardButton.No):
            page.delete_selected()
        self.assertEqual(page.table.rowCount(), 1)
        with mock.patch.object(
            QMessageBox, "question", return_value=QMessageBox.StandardButton.Yes
        ):
            page.delete_selected()
        self.assertEqual(page.table.rowCount(), 0)

    def test_logout_clears_screen(self) -> None:
        self.enter()
        self.window.show_page(1)
        self.add("1000", "maxfiy izoh")
        self.window.logout()
        self.assertIsNone(self.window.ctx.session)
        self.assertEqual(self.window.transactions.table.rowCount(), 0)
        self.assertEqual(self.window.user_label.text(), "")
        self.assertEqual(self.window.dashboard.income.value.text(), "—")
        self.assertEqual(self.auth.message.text(), "Tizimdan chiqdingiz.")

    def test_idle_session_returns_to_login(self) -> None:
        self.enter()
        self.clock.advance(IDLE_TIMEOUT_SECONDS + 1)
        self.window._check_idle()
        self.assertIsNone(self.window.ctx.session)
        self.assertIn("Sessiya muddati tugadi", self.auth.message.text())

    def test_change_password(self) -> None:
        self.enter()
        self.window.show_page(2)
        page = self.window.security
        new_password = "Daryo-bo'yida-tong-1991"
        page.current.setText("xato-parol-xato-parol")
        page.new.setText(new_password)
        page.repeat.setText(new_password)
        page.change_password()
        self.assertEqual(page.message.text(), "Joriy parol noto'g'ri.")
        self.assertEqual(page.current.text(), "")
        page.current.setText(PASSWORD)
        page.new.setText(new_password)
        page.repeat.setText(new_password)
        page.change_password()
        self.assertEqual(page.message.text(), "Parol o'zgartirildi.")
        events = [page.audit.item(row, 1).text() for row in range(page.audit.rowCount())]
        self.assertEqual(events[0], "Parol o'zgartirildi")
        self.window.logout()
        self.login(password=new_password)
        self.assertIsNotNone(self.window.ctx.session)


if __name__ == "__main__":
    unittest.main()
