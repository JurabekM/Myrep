"""Tranzaksiyalar: yozish, tarix, filtr, o'chirish va foydalanuvchilar izolyatsiyasi."""

from __future__ import annotations

import sqlite3
import unittest
from datetime import date

from fintx.errors import NotFound, SessionExpired, ValidationError

from .helpers import OTHER_PASSWORD, PASSWORD, TODAY, make_app


class TransactionTestCase(unittest.TestCase):
    def setUp(self) -> None:
        self.app = make_app()
        self.addCleanup(self.app.close)
        self.tx = self.app.transactions
        self.app.auth.register("jurabek", PASSWORD)
        self.app.auth.register("malika", OTHER_PASSWORD)
        self.jurabek = self.app.auth.login("jurabek", PASSWORD)
        self.malika = self.app.auth.login("malika", OTHER_PASSWORD)

    def add(self, session=None, **overrides):
        fields = {
            "kind": "expense",
            "amount": "50 000",
            "category": "food",
            "occurred_on": "2026-11-10",
            "note": "",
        }
        fields.update(overrides)
        return self.tx.add(session or self.jurabek, **fields)


class RecordingTests(TransactionTestCase):
    def test_add_income_and_expense(self) -> None:
        income = self.add(kind="income", amount="12 500 000,50", category="salary")
        expense = self.add(amount="350000", note="Bozor")
        self.assertEqual(income.amount_minor, 1_250_000_050)
        self.assertEqual(income.signed_minor, 1_250_000_050)
        self.assertEqual(expense.signed_minor, -35_000_000)
        self.assertEqual(expense.note, "Bozor")
        self.assertEqual(expense.occurred_on, date(2026, 11, 10))

    def test_empty_date_means_today(self) -> None:
        self.assertEqual(self.add(occurred_on="").occurred_on, TODAY)
        self.assertEqual(self.add(occurred_on=None).occurred_on, TODAY)

    def test_invalid_fields_are_rejected_and_nothing_is_stored(self) -> None:
        bad = [
            {"kind": "transfer"},
            {"amount": "-100"},
            {"amount": "0"},
            {"amount": "abc"},
            {"amount": 100},
            {"category": "salary"},  # daromad kategoriyasi xarajatda
            {"category": "yo'q-kategoriya"},
            {"occurred_on": "2026-11-16"},
            {"occurred_on": "kecha"},
            {"note": "x" * 201},
            {"note": "\x1b[31mqizil"},
        ]
        for overrides in bad:
            with self.subTest(overrides=overrides), self.assertRaises(ValidationError):
                self.add(**overrides)
        self.assertEqual(self.tx.history(self.jurabek), [])

    def test_sql_injection_payload_is_stored_as_plain_text(self) -> None:
        payload = "'); DROP TABLE transactions; --"
        created = self.add(note=payload)
        rows = self.tx.history(self.jurabek)
        self.assertEqual([r.note for r in rows], [payload])
        self.assertEqual(rows[0].id, created.id)
        tables = {
            row[0]
            for row in self.app.conn.execute("SELECT name FROM sqlite_master WHERE type = 'table'")
        }
        self.assertEqual(tables, {"users", "transactions", "audit_log"})

    def test_requires_active_session(self) -> None:
        self.app.auth.logout(self.jurabek)
        with self.assertRaises(SessionExpired):
            self.add()
        with self.assertRaises(SessionExpired):
            self.tx.delete(self.jurabek, 1)


class HistoryTests(TransactionTestCase):
    def setUp(self) -> None:
        super().setUp()
        self.add(kind="income", amount="5000000", category="salary", occurred_on="2026-10-05")
        self.add(amount="120000", category="transport", occurred_on="2026-10-20")
        self.add(amount="80000", category="food", occurred_on="2026-11-01")
        self.add(amount="40000", category="food", occurred_on="2026-11-01")

    def test_newest_first(self) -> None:
        rows = self.tx.history(self.jurabek)
        self.assertEqual(
            [(r.occurred_on.isoformat(), r.amount_minor) for r in rows],
            [
                ("2026-11-01", 4_000_000),
                ("2026-11-01", 8_000_000),
                ("2026-10-20", 12_000_000),
                ("2026-10-05", 500_000_000),
            ],
        )

    def test_filters(self) -> None:
        self.assertEqual(len(self.tx.history(self.jurabek, kind="income")), 1)
        self.assertEqual(len(self.tx.history(self.jurabek, kind="expense")), 3)
        october = self.tx.history(self.jurabek, date_from="2026-10-01", date_to="2026-10-31")
        self.assertEqual(len(october), 2)
        self.assertEqual(len(self.tx.history(self.jurabek, date_from="2026-11-01")), 2)

    def test_pagination(self) -> None:
        first = self.tx.history(self.jurabek, limit=3)
        rest = self.tx.history(self.jurabek, limit=3, offset=3)
        self.assertEqual(len(first), 3)
        self.assertEqual(len(rest), 1)
        self.assertEqual(len({r.id for r in first + rest}), 4)
        # Chegaradan tashqari qiymatlar xato emas, xavfsiz oraliqqa keltiriladi.
        self.assertEqual(len(self.tx.history(self.jurabek, limit=-5)), 1)
        self.assertEqual(len(self.tx.history(self.jurabek, limit=10**9)), 4)

    def test_invalid_filters(self) -> None:
        for kwargs in (
            {"kind": "expense' OR '1'='1"},
            {"date_from": "2026-11-01' OR 1=1 --"},
            {"date_from": "2026-11-10", "date_to": "2026-11-01"},
            {"limit": "10; DROP TABLE users"},
        ):
            with self.subTest(kwargs=kwargs), self.assertRaises(ValidationError):
                self.tx.history(self.jurabek, **kwargs)


class IsolationTests(TransactionTestCase):
    def test_users_do_not_see_each_others_transactions(self) -> None:
        self.add(self.jurabek, note="Jurabekniki")
        self.add(self.malika, note="Malikaniki")
        self.assertEqual([r.note for r in self.tx.history(self.jurabek)], ["Jurabekniki"])
        self.assertEqual([r.note for r in self.tx.history(self.malika)], ["Malikaniki"])
        self.assertEqual(self.app.report(self.malika).count, 1)

    def test_cannot_delete_another_users_transaction(self) -> None:
        theirs = self.add(self.jurabek)
        with self.assertRaises(NotFound) as foreign:
            self.tx.delete(self.malika, theirs.id)
        with self.assertRaises(NotFound) as missing:
            self.tx.delete(self.malika, 999_999)
        # Begona yozuv va mavjud bo'lmagan yozuv bir xil javob oladi.
        self.assertEqual(str(foreign.exception), str(missing.exception))
        self.assertEqual(len(self.tx.history(self.jurabek)), 1)

    def test_delete_own_transaction(self) -> None:
        mine = self.add()
        self.tx.delete(self.jurabek, str(mine.id))
        self.assertEqual(self.tx.history(self.jurabek), [])
        with self.assertRaises(NotFound):
            self.tx.delete(self.jurabek, mine.id)

    def test_delete_rejects_malformed_ids(self) -> None:
        mine = self.add()
        for value in ("1 OR 1=1", "", "-1", "1.0", None, True, 0, 2**70, f"{mine.id};"):
            with self.subTest(value=value), self.assertRaises(ValidationError):
                self.tx.delete(self.jurabek, value)
        self.assertEqual(len(self.tx.history(self.jurabek)), 1)


class SchemaConstraintTests(TransactionTestCase):
    """Xizmat qatlamini chetlab o'tgan yozuvni bazaning o'zi rad etadi."""

    def insert(self, **overrides) -> None:
        row = {
            "user_id": self.jurabek.user_id,
            "kind": "expense",
            "amount_minor": 100,
            "category": "food",
            "note": "",
            "occurred_on": "2026-11-10",
            "created_at": "2026-11-10T00:00:00+00:00",
        }
        row.update(overrides)
        with self.app.conn:
            self.app.conn.execute(
                "INSERT INTO transactions "
                "(user_id, kind, amount_minor, category, note, occurred_on, created_at) "
                "VALUES (:user_id, :kind, :amount_minor, :category, :note, "
                ":occurred_on, :created_at)",
                row,
            )

    def test_valid_row_is_accepted(self) -> None:
        self.insert()

    def test_invalid_rows_are_rejected(self) -> None:
        for overrides in (
            {"amount_minor": 0},
            {"amount_minor": -5},
            {"amount_minor": 1.5},
            {"amount_minor": 10**17},
            {"kind": "transfer"},
            {"occurred_on": "kecha"},
            {"note": "x" * 201},
            {"category": ""},
            {"user_id": 424242},  # mavjud bo'lmagan foydalanuvchi
        ):
            with self.subTest(overrides=overrides):
                with self.assertRaises(sqlite3.IntegrityError):
                    self.insert(**overrides)


if __name__ == "__main__":
    unittest.main()
