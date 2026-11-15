"""Moliyaviy hisob-kitoblar: jami, balans, ulushlar, oylik yig'ma."""

from __future__ import annotations

import unittest
from datetime import date
from decimal import Decimal

from fintx.reports import build_report, percent
from fintx.transactions import Transaction

from .helpers import PASSWORD, make_app


def tx(kind: str, amount_minor: int, category: str, day: str, tx_id: int = 0) -> Transaction:
    return Transaction(
        id=tx_id,
        kind=kind,
        amount_minor=amount_minor,
        category=category,
        note="",
        occurred_on=date.fromisoformat(day),
        created_at="2026-11-15T00:00:00+00:00",
    )


class PercentTests(unittest.TestCase):
    def test_rounding_half_up(self) -> None:
        self.assertEqual(percent(1, 3), Decimal("33.3"))
        self.assertEqual(percent(2, 3), Decimal("66.7"))
        self.assertEqual(percent(1, 8), Decimal("12.5"))
        self.assertEqual(percent(5, 10_000), Decimal("0.1"))  # 0,05 % → 0,1 %
        self.assertEqual(percent(-1, 4), Decimal("-25.0"))

    def test_zero_denominator(self) -> None:
        self.assertIsNone(percent(5, 0))


class BuildReportTests(unittest.TestCase):
    def test_empty(self) -> None:
        report = build_report([])
        self.assertEqual(report.count, 0)
        self.assertEqual(report.balance_minor, 0)
        self.assertIsNone(report.savings_rate)
        self.assertIsNone(report.average_expense_minor)
        self.assertIsNone(report.largest_expense)
        self.assertEqual(report.expense_by_category, ())
        self.assertEqual(report.monthly, ())

    def test_totals_balance_and_savings_rate(self) -> None:
        report = build_report(
            [
                tx("income", 1_000_000_00, "salary", "2026-10-05"),
                tx("income", 250_000_00, "gift", "2026-11-02"),
                tx("expense", 300_000_00, "food", "2026-10-10"),
                tx("expense", 200_000_00, "housing", "2026-11-03"),
            ]
        )
        self.assertEqual(report.count, 4)
        self.assertEqual(report.income_minor, 1_250_000_00)
        self.assertEqual(report.expense_minor, 500_000_00)
        self.assertEqual(report.balance_minor, 750_000_00)
        self.assertEqual(report.savings_rate, Decimal("60.0"))
        self.assertEqual(report.average_expense_minor, 250_000_00)
        self.assertEqual(report.largest_expense.category, "food")

    def test_overspending_gives_negative_balance_and_rate(self) -> None:
        report = build_report(
            [
                tx("income", 100_00, "salary", "2026-11-01"),
                tx("expense", 150_00, "food", "2026-11-02"),
            ]
        )
        self.assertEqual(report.balance_minor, -50_00)
        self.assertEqual(report.savings_rate, Decimal("-50.0"))

    def test_expenses_without_income(self) -> None:
        report = build_report([tx("expense", 99, "food", "2026-11-02")])
        self.assertIsNone(report.savings_rate)
        self.assertEqual(report.balance_minor, -99)

    def test_category_shares_are_sorted_and_sum_to_100(self) -> None:
        report = build_report(
            [
                tx("expense", 500_00, "food", "2026-11-01"),
                tx("expense", 250_00, "transport", "2026-11-02"),
                tx("expense", 250_00, "food", "2026-11-03"),
            ]
        )
        shares = report.expense_by_category
        self.assertEqual([s.category for s in shares], ["food", "transport"])
        self.assertEqual([s.amount_minor for s in shares], [750_00, 250_00])
        self.assertEqual([s.percent for s in shares], [Decimal("75.0"), Decimal("25.0")])
        self.assertEqual(sum(s.percent for s in shares), Decimal("100.0"))
        self.assertEqual(report.income_by_category, ())

    def test_monthly_summary_newest_first(self) -> None:
        report = build_report(
            [
                tx("income", 900_00, "salary", "2026-09-30"),
                tx("expense", 100_00, "food", "2026-10-01"),
                tx("income", 500_00, "salary", "2026-10-15"),
                tx("expense", 700_00, "housing", "2026-11-01"),
            ]
        )
        self.assertEqual([m.month for m in report.monthly], ["2026-11", "2026-10", "2026-09"])
        october = report.monthly[1]
        self.assertEqual((october.income_minor, october.expense_minor), (500_00, 100_00))
        self.assertEqual(october.net_minor, 400_00)
        self.assertEqual(report.monthly[0].net_minor, -700_00)

    def test_average_expense_rounds_half_up_to_tiyin(self) -> None:
        report = build_report(
            [tx("expense", 1, "food", "2026-11-01"), tx("expense", 2, "food", "2026-11-01")]
        )
        self.assertEqual(report.average_expense_minor, 2)  # 1,5 tiyin → 2

    def test_no_float_drift_on_many_small_amounts(self) -> None:
        report = build_report(tx("expense", 10, "food", "2026-11-01") for _ in range(1000))
        self.assertEqual(report.expense_minor, 10_000)

    def test_large_amounts_do_not_overflow(self) -> None:
        huge = 1_000_000_000_000 * 100
        report = build_report(tx("income", huge, "business", "2026-11-01") for _ in range(200_000))
        self.assertEqual(report.income_minor, huge * 200_000)


class AppReportTests(unittest.TestCase):
    def test_report_respects_period_and_reads_all_pages(self) -> None:
        app = make_app()
        self.addCleanup(app.close)
        app.auth.register("jurabek", PASSWORD)
        session = app.auth.login("jurabek", PASSWORD)
        for _ in range(520):  # bitta sahifadan (500) ko'p
            app.transactions.add(
                session, kind="expense", amount="1", category="food", occurred_on="2026-11-01"
            )
        app.transactions.add(
            session, kind="income", amount="1000", category="salary", occurred_on="2026-10-01"
        )
        full = app.report(session)
        self.assertEqual(full.count, 521)
        self.assertEqual(full.expense_minor, 52_000)
        november = app.report(session, date_from="2026-11-01", date_to="2026-11-30")
        # Davr oxiri (2026-11-30) bugundan keyin bo'lishi mumkin: bu filtr, yozuv emas.
        self.assertEqual(november.count, 520)


if __name__ == "__main__":
    unittest.main()
