"""Terminal interfeysi (Windows Terminal, PowerShell, cmd, macOS/Linux).

Ishga tushirish: `python -m fintx`

Xavfsizlik jihatlari:
- parol `getpass` orqali so'raladi — ekranda ko'rinmaydi va buyruqlar
  tarixiga tushmaydi (parol hech qachon buyruq argumenti sifatida olinmaydi);
- bazadan o'qilgan matn chiqarishdan oldin `printable()` dan o'tadi;
- kutilmagan xatoda foydalanuvchiga ichki tafsilot emas, umumiy xabar chiqadi.
"""

from __future__ import annotations

import argparse
import getpass
import sys
from collections.abc import Callable
from typing import TextIO

from . import __version__
from .app import App
from .auth import Session
from .errors import FinTxError, SessionExpired, ValidationError
from .money import CURRENCY, format_amount, format_percent, parse_amount
from .reports import Report
from .transactions import Transaction
from .validation import (
    CATEGORIES,
    KIND_EXPENSE,
    KIND_INCOME,
    KIND_LABELS,
    PASSWORD_MIN,
    category_label,
    parse_date,
    printable,
)

_RULE = "-" * 64


class _Quit(Exception):
    """Foydalanuvchi dasturdan chiqishni so'radi (yoki kirish oqimi tugadi)."""


class Cli:
    def __init__(
        self,
        app: App,
        *,
        input_fn: Callable[[str], str] = input,
        getpass_fn: Callable[[str], str] = getpass.getpass,
        out: TextIO | None = None,
    ) -> None:
        self._app = app
        self._input = input_fn
        self._getpass = getpass_fn
        self._out = out if out is not None else sys.stdout
        self._session: Session | None = None

    # --- kirish-chiqish ----------------------------------------------------

    def _say(self, text: str = "") -> None:
        print(text, file=self._out)

    def _ask(self, prompt: str) -> str:
        try:
            return self._input(prompt).strip()
        except (EOFError, KeyboardInterrupt):
            raise _Quit from None

    def _ask_secret(self, prompt: str) -> str:
        try:
            return self._getpass(prompt)
        except (EOFError, KeyboardInterrupt):
            raise _Quit from None

    def _title(self, text: str) -> None:
        self._say()
        self._say(_RULE)
        self._say(text)
        self._say(_RULE)

    # --- asosiy sikl -------------------------------------------------------

    def run(self) -> int:
        self._title(f"FinTx {__version__} — moliyaviy tranzaksiyalar prototipi")
        try:
            while True:
                if self._session is None:
                    self._guest_menu()
                else:
                    self._user_menu()
        except _Quit:
            pass
        finally:
            if self._session is not None:
                self._app.auth.logout(self._session)
                self._session = None
        self._say()
        self._say("Xayr!")
        return 0

    def _guarded(self, action: Callable[[], None]) -> None:
        """Amalni bajaradi; kutilgan xatolarni tushunarli xabarga aylantiradi."""
        try:
            action()
        except SessionExpired as exc:
            self._session = None
            self._say(f"! {exc}")
        except FinTxError as exc:
            self._say(f"! {exc}")

    # --- mehmon menyusi ----------------------------------------------------

    def _guest_menu(self) -> None:
        self._say()
        self._say("1) Kirish")
        self._say("2) Ro'yxatdan o'tish")
        self._say("0) Dasturdan chiqish")
        choice = self._ask("Tanlang: ")
        if choice == "1":
            self._guarded(self._login)
        elif choice == "2":
            self._guarded(self._register)
        elif choice == "0":
            raise _Quit
        else:
            self._say("! Bunday band yo'q.")

    def _login(self) -> None:
        username = self._ask("Login: ")
        password = self._ask_secret("Parol (ko'rinmaydi): ")
        self._session = self._app.auth.login(username, password)
        self._say(f"Xush kelibsiz, {printable(self._session.username)}!")

    def _register(self) -> None:
        self._say(f"Parol kamida {PASSWORD_MIN} belgi bo'lsin; uzun ibora eng yaxshi tanlov.")
        username = self._ask("Yangi login: ")
        password = self._ask_secret("Parol (ko'rinmaydi): ")
        repeat = self._ask_secret("Parolni takrorlang: ")
        if password != repeat:
            self._say("! Parollar mos kelmadi.")
            return
        self._app.auth.register(username, password)
        self._say("Hisob yaratildi. Endi tizimga kiring.")

    # --- foydalanuvchi menyusi ---------------------------------------------

    def _user_menu(self) -> None:
        assert self._session is not None
        self._say()
        self._say(f"[{printable(self._session.username)}]")
        self._say("1) Daromad qo'shish")
        self._say("2) Xarajat qo'shish")
        self._say("3) Tranzaksiyalar tarixi")
        self._say("4) Hisobot")
        self._say("5) Tranzaksiyani o'chirish")
        self._say("6) Parolni o'zgartirish")
        self._say("7) Xavfsizlik jurnali")
        self._say("0) Tizimdan chiqish")
        choice = self._ask("Tanlang: ")
        actions: dict[str, Callable[[], None]] = {
            "1": lambda: self._add(KIND_INCOME),
            "2": lambda: self._add(KIND_EXPENSE),
            "3": self._history,
            "4": self._report,
            "5": self._delete,
            "6": self._change_password,
            "7": self._audit,
            "0": self._logout,
        }
        action = actions.get(choice)
        if action is None:
            self._say("! Bunday band yo'q.")
            return
        self._guarded(action)

    def _logout(self) -> None:
        assert self._session is not None
        self._app.auth.logout(self._session)
        self._session = None
        self._say("Tizimdan chiqdingiz.")

    def _add(self, kind: str) -> None:
        assert self._session is not None
        # Shakl to'ldirilishidan oldin sessiyani tekshiramiz: muddati o'tgan
        # bo'lsa, foydalanuvchi ma'lumotni bekorga termaydi.
        self._app.auth.require(self._session)
        self._title(f"{KIND_LABELS[kind]} qo'shish")
        amount = self._ask(f"Summa ({CURRENCY}): ")
        parse_amount(amount)  # xatoni darhol ko'rsatamiz; yakuniy tekshiruv xizmatda
        keys = list(CATEGORIES[kind])
        for number, key in enumerate(keys, start=1):
            self._say(f"  {number}) {CATEGORIES[kind][key]}")
        picked = self._ask("Kategoriya raqami: ")
        if not (picked.isascii() and picked.isdigit() and 1 <= int(picked) <= len(keys)):
            raise ValidationError("Kategoriya raqami ro'yxatdan tanlanishi kerak.", "category")
        category = keys[int(picked) - 1]
        today = self._app.today()
        occurred_on = self._ask(f"Sana (YYYY-MM-DD, bo'sh = bugun {today.isoformat()}): ")
        if occurred_on:
            parse_date(occurred_on, today=today)
        note = self._ask("Izoh (ixtiyoriy): ")
        tx = self._app.transactions.add(
            self._session,
            kind=kind,
            amount=amount,
            category=category,
            occurred_on=occurred_on,
            note=note,
        )
        self._say(f"Saqlandi: #{tx.id}  {format_amount(tx.signed_minor, signed=True)} {CURRENCY}")

    def _period(self) -> tuple[str, str]:
        self._say("Davr (ikkalasini bo'sh qoldirsangiz — butun tarix).")
        date_from = self._ask("  Boshlanish sanasi (YYYY-MM-DD): ")
        date_to = self._ask("  Tugash sanasi (YYYY-MM-DD): ")
        return date_from, date_to

    def _history(self) -> None:
        assert self._session is not None
        self._app.auth.require(self._session)
        self._title("Tranzaksiyalar tarixi")
        date_from, date_to = self._period()
        rows = self._app.transactions.history(
            self._session, date_from=date_from, date_to=date_to, limit=200
        )
        self._print_transactions(rows)

    def _print_transactions(self, rows: list[Transaction]) -> None:
        if not rows:
            self._say("Tranzaksiyalar yo'q.")
            return
        self._say()
        self._say(
            f"{'#':>5}  {'Sana':<10}  {'Turi':<8}  {'Kategoriya':<18}  "
            f"{'Summa, ' + CURRENCY:>20}  Izoh"
        )
        for tx in rows:
            self._say(
                f"{tx.id:>5}  {tx.occurred_on.isoformat():<10}  "
                f"{KIND_LABELS[tx.kind]:<8}  "
                f"{printable(category_label(tx.kind, tx.category)):<18}  "
                f"{format_amount(tx.signed_minor, signed=True):>20}  "
                f"{printable(tx.note)}"
            )
        self._say(f"Jami: {len(rows)} ta yozuv.")

    def _report(self) -> None:
        assert self._session is not None
        self._app.auth.require(self._session)
        self._title("Hisobot")
        date_from, date_to = self._period()
        report = self._app.report(self._session, date_from=date_from, date_to=date_to)
        self._print_report(report)

    def _print_report(self, report: Report) -> None:
        if report.count == 0:
            self._say("Bu davrda tranzaksiyalar yo'q.")
            return

        def line(label: str, value: str) -> None:
            self._say(f"{label:<28}{value:>24}")

        self._say()
        line("Tranzaksiyalar soni:", str(report.count))
        line("Jami daromad:", f"{format_amount(report.income_minor)} {CURRENCY}")
        line("Jami xarajat:", f"{format_amount(report.expense_minor)} {CURRENCY}")
        line(
            "Balans:",
            f"{format_amount(report.balance_minor, signed=True)} {CURRENCY}",
        )
        rate = "mavjud emas (daromad yo'q)"
        if report.savings_rate is not None:
            rate = format_percent(report.savings_rate)
        line("Jamg'arma ulushi:", rate)
        if report.average_expense_minor is not None:
            line(
                "O'rtacha xarajat:",
                f"{format_amount(report.average_expense_minor)} {CURRENCY}",
            )
        if report.largest_expense is not None:
            top = report.largest_expense
            line(
                "Eng katta xarajat:",
                f"{format_amount(top.amount_minor)} {CURRENCY}",
            )
            self._say(
                f"  ({top.occurred_on.isoformat()}, "
                f"{printable(category_label(top.kind, top.category))})"
            )
        for title, kind, shares in (
            ("Xarajatlar kategoriya bo'yicha", KIND_EXPENSE, report.expense_by_category),
            ("Daromadlar kategoriya bo'yicha", KIND_INCOME, report.income_by_category),
        ):
            if not shares:
                continue
            self._say()
            self._say(f"{title}:")
            for share in shares:
                self._say(
                    f"  {printable(category_label(kind, share.category)):<22}"
                    f"{format_amount(share.amount_minor):>20} {CURRENCY}"
                    f"{format_percent(share.percent):>10}"
                )
        self._say()
        self._say("Oylar bo'yicha:")
        self._say(f"  {'Oy':<8}{'Daromad':>20}{'Xarajat':>20}{'Farq':>20}")
        for month in report.monthly:
            self._say(
                f"  {month.month:<8}"
                f"{format_amount(month.income_minor):>20}"
                f"{format_amount(month.expense_minor):>20}"
                f"{format_amount(month.net_minor, signed=True):>20}"
            )

    def _delete(self) -> None:
        assert self._session is not None
        self._app.auth.require(self._session)
        self._title("Tranzaksiyani o'chirish")
        number = self._ask("Tranzaksiya raqami (#): ")
        confirm = self._ask(f"#{printable(number)} o'chirilsinmi? (ha/yo'q): ").lower()
        if confirm != "ha":
            self._say("Bekor qilindi.")
            return
        self._app.transactions.delete(self._session, number)
        self._say("O'chirildi.")

    def _change_password(self) -> None:
        assert self._session is not None
        self._app.auth.require(self._session)
        self._title("Parolni o'zgartirish")
        current = self._ask_secret("Joriy parol (ko'rinmaydi): ")
        new = self._ask_secret("Yangi parol (ko'rinmaydi): ")
        repeat = self._ask_secret("Yangi parolni takrorlang: ")
        if new != repeat:
            self._say("! Parollar mos kelmadi.")
            return
        self._app.auth.change_password(self._session, current, new)
        self._say("Parol o'zgartirildi.")

    def _audit(self) -> None:
        assert self._session is not None
        self._title("Xavfsizlik jurnali (oxirgi 20 hodisa, vaqt UTC)")
        for event in self._app.auth.audit_events(self._session, limit=20):
            detail = f" ({printable(event.detail)})" if event.detail else ""
            self._say(f"{printable(event.at)}  {event.label}{detail}")


def _configure_stdio() -> None:
    """Windows konsolida ham o'zbekcha matn buzilmasligi uchun UTF-8 chiqish."""
    for stream in (sys.stdout, sys.stderr):
        reconfigure = getattr(stream, "reconfigure", None)
        if reconfigure is not None:
            reconfigure(encoding="utf-8", errors="replace")


def _self_test() -> int:
    """Reliz tekshiruvi: xotiradagi bazada yadroni to'liq yuritadi (CI ishlatadi)."""
    from .selftest import run_core_selftest

    try:
        for step in run_core_selftest():
            print(f"ok: {step}")
    except Exception as exc:
        print(
            f"O'z-o'zini tekshirish muvaffaqiyatsiz: {type(exc).__name__}: {exc}", file=sys.stderr
        )
        return 3
    print(f"fintx {__version__}: o'z-o'zini tekshirish muvaffaqiyatli")
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="fintx",
        description="FinTx — moliyaviy tranzaksiyalar prototipi (terminal interfeysi).",
    )
    parser.add_argument(
        "--db",
        metavar="FAYL",
        help="ma'lumotlar bazasi fayli (standart: foydalanuvchi papkasida)",
    )
    parser.add_argument("--version", action="version", version=f"fintx {__version__}")
    parser.add_argument("--self-test", action="store_true", help=argparse.SUPPRESS)
    args = parser.parse_args(argv)
    _configure_stdio()
    if args.self_test:
        return _self_test()
    try:
        app = App.open(args.db)
    except FinTxError as exc:
        print(f"Xato: {exc}", file=sys.stderr)
        return 1
    except OSError:
        print("Xato: ma'lumotlar bazasi faylini ochib bo'lmadi.", file=sys.stderr)
        return 1
    try:
        return Cli(app).run()
    except Exception:
        print("Kutilmagan xato yuz berdi. Dastur yopildi.", file=sys.stderr)
        return 2
    finally:
        app.close()


if __name__ == "__main__":
    raise SystemExit(main())
