"""Kirish ma'lumotlarini tekshirish: summa, login, parol siyosati, sana, izoh."""

from __future__ import annotations

import unittest
from datetime import date
from decimal import Decimal

from fintx.errors import ValidationError
from fintx.money import MAX_AMOUNT_MINOR, format_amount, format_percent, parse_amount
from fintx.validation import (
    normalize_username,
    parse_date,
    printable,
    validate_category,
    validate_kind,
    validate_new_password,
    validate_note,
)

from .helpers import TODAY


class AmountTests(unittest.TestCase):
    def test_accepts_common_formats(self) -> None:
        cases = {
            "125000": 12_500_000,
            "125 000": 12_500_000,
            "125 000,50": 12_500_050,
            "125000.5": 12_500_050,
            "0,01": 1,
            "  7  ": 700,
            "1 000 000 000 000": MAX_AMOUNT_MINOR,
        }
        for text, expected in cases.items():
            with self.subTest(text=text):
                self.assertEqual(parse_amount(text), expected)

    def test_rejects_invalid_input(self) -> None:
        bad = [
            "",
            "   ",
            "0",
            "0,00",
            "-5",
            "+5",
            "1e5",
            "NaN",
            "Infinity",
            "1.234",  # uchinchi kasr xonasi
            "1,2,3",
            "12abc",
            "1_000",
            "١٢٣",  # arab-hind raqamlari
            "１２３",  # to'liq enli raqamlar
            "1000000000000,01",  # chegaradan bir tiyin ortiq
            "9" * 40,
            "1; DROP TABLE users",
            "0x10",
        ]
        for text in bad:
            with self.subTest(text=text), self.assertRaises(ValidationError):
                parse_amount(text)

    def test_rejects_non_string(self) -> None:
        for value in (None, 5, 5.5, Decimal("5"), b"5", ["5"]):
            with self.subTest(value=value), self.assertRaises(ValidationError):
                parse_amount(value)

    def test_format(self) -> None:
        self.assertEqual(format_amount(125_000_050), "1 250 000,50")
        self.assertEqual(format_amount(0), "0,00")
        self.assertEqual(format_amount(-99), "-0,99")
        self.assertEqual(format_amount(700, signed=True), "+7,00")
        self.assertEqual(format_percent(Decimal("97.2")), "97,2 %")

    def test_roundtrip_is_exact(self) -> None:
        # float bilan 0.1 + 0.2 != 0.3; tiyinda esa aniq.
        total = parse_amount("0,10") + parse_amount("0,20")
        self.assertEqual(total, parse_amount("0,30"))


class UsernameTests(unittest.TestCase):
    def test_normalizes_case_and_spaces(self) -> None:
        self.assertEqual(normalize_username("  Jurabek_M  "), "jurabek_m")
        self.assertEqual(normalize_username("ali.vali-7"), "ali.vali-7")

    def test_rejects_invalid(self) -> None:
        bad = [
            "",
            "ab",
            "a" * 33,
            "_ali",
            "ali vali",
            "ali@uz",
            "жўрабек",
            "ali'--",
            "ali\x00",
            "ali\nvali",
            None,
            123,
        ]
        for value in bad:
            with self.subTest(value=value), self.assertRaises(ValidationError):
                normalize_username(value)


class PasswordPolicyTests(unittest.TestCase):
    def test_accepts_long_passphrase(self) -> None:
        self.assertEqual(
            validate_new_password("to'g'ri ot batareya qisqich", "ali"),
            "to'g'ri ot batareya qisqich",
        )

    def test_rejects_weak(self) -> None:
        cases = {
            "qisqa": "ali",  # juda qisqa
            "x" * 129: "ali",  # juda uzun
            "aaaaaaaaaaaaaaaa": "ali",  # bir xil belgi
            "abababababababab": "ali",  # ikki xil belgi
            "Password12345": "ali",  # keng tarqalgan
            "QWERTYQWERTY": "ali",  # keng tarqalgan (registrdan qat'i nazar)
            "mening-Jurabek-parolim": "jurabek",  # ichida login bor
        }
        for password, username in cases.items():
            with self.subTest(password=password), self.assertRaises(ValidationError):
                validate_new_password(password, username)

    def test_rejects_non_string(self) -> None:
        with self.assertRaises(ValidationError):
            validate_new_password(None, "ali")


class TransactionFieldTests(unittest.TestCase):
    def test_kind(self) -> None:
        self.assertEqual(validate_kind("income"), "income")
        for value in ("", "INCOME", "transfer", None, 1):
            with self.subTest(value=value), self.assertRaises(ValidationError):
                validate_kind(value)

    def test_category_is_whitelisted_per_kind(self) -> None:
        self.assertEqual(validate_category("expense", "food"), "food")
        self.assertEqual(validate_category("income", "salary"), "salary")
        for kind, value in (
            ("income", "food"),  # xarajat kategoriyasi daromadga yaramaydi
            ("expense", "salary"),
            ("expense", "Oziq-ovqat"),  # nom emas, kalit kutiladi
            ("expense", ""),
            ("expense", None),
        ):
            with self.subTest(kind=kind, value=value):
                with self.assertRaises(ValidationError):
                    validate_category(kind, value)

    def test_note(self) -> None:
        self.assertEqual(validate_note("  Bozor: go'sht, non  "), "Bozor: go'sht, non")
        self.assertEqual(validate_note(None), "")
        self.assertEqual(validate_note("x" * 200), "x" * 200)
        bad = [
            "x" * 201,
            "tushlik\x1b[2J",  # terminalni tozalovchi ESC ketma-ketligi
            "bir\nikki",
            "nol\x00bayt",
            "o'ng‮chapga",  # bidi almashtirish belgisi
            123,
        ]
        for value in bad:
            with self.subTest(value=value), self.assertRaises(ValidationError):
                validate_note(value)

    def test_date(self) -> None:
        self.assertEqual(parse_date("2026-11-15", today=TODAY), TODAY)
        self.assertEqual(parse_date(date(2026, 1, 2), today=TODAY), date(2026, 1, 2))
        bad = [
            "2026-11-16",  # kelajak
            "1999-12-31",  # juda eski
            "2026-02-30",  # mavjud emas
            "2026-13-01",
            "15.11.2026",
            "20261115",
            "2026-11-15T10:00",
            "",
            None,
            20261115,
        ]
        for value in bad:
            with self.subTest(value=value), self.assertRaises(ValidationError):
                parse_date(value, today=TODAY)

    def test_printable_neutralises_control_chars(self) -> None:
        self.assertEqual(printable("a\x1b[31mb\nc"), "a?[31mb?c")
        self.assertEqual(printable("Sog'liq — 100%"), "Sog'liq — 100%")


if __name__ == "__main__":
    unittest.main()
