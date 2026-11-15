"""O'z-o'zini tekshirish: yig'ilgan (PyInstaller) ilova to'liq ishlashini isbotlaydi.

`--self-test` bayrog'i bilan ishga tushirilganda foydalanuvchi bazasiga tegilmaydi:
hammasi xotiradagi vaqtinchalik bazada bajariladi. Reliz yig'ilgach CI aynan shu
tekshiruvni o'rnatilgan ijro fayllarda ishga tushiradi — paketga `hashlib.scrypt`,
`sqlite3` yoki shriftlar kirmay qolsa, reliz chiqmaydi.
"""

from __future__ import annotations

import secrets

from . import db
from .app import App
from .security import PasswordHasher, scrypt_available


def run_core_selftest() -> list[str]:
    """Yadroni ishlab chiqarish parametrlari bilan boshidan oxirigacha yuritadi.

    Muammo topilsa `AssertionError` ko'taradi; aks holda bajarilgan qadamlar ro'yxati.
    """
    steps: list[str] = []
    # Ishlab chiqarishdagi xeshlovchi (scrypt N=2^17): paketdagi OpenSSL uni
    # haqiqatan bajara olishini tekshiradi.
    app = App.open(db.MEMORY, hasher=PasswordHasher())
    try:
        password = secrets.token_urlsafe(18)
        app.auth.register("selftest", password)
        stored = app.conn.execute("SELECT password_hash FROM users").fetchone()[0]
        expected = "scrypt$" if scrypt_available() else "pbkdf2-sha256$"
        if not stored.startswith(expected) or password in stored:
            raise AssertionError("parol xeshi kutilgan ko'rinishda emas")
        steps.append(f"parol xeshi: {stored.split('$')[0]}")

        session = app.auth.login("selftest", password)
        steps.append("kirish")

        app.transactions.add(session, kind="income", amount="1 000 000,50", category="salary")
        app.transactions.add(session, kind="expense", amount="250000", category="food")
        report = app.report(session)
        if (report.income_minor, report.expense_minor, report.balance_minor) != (
            100_000_050,
            25_000_000,
            75_000_050,
        ):
            raise AssertionError("hisob-kitob natijasi noto'g'ri")
        if str(report.savings_rate) != "75.0":
            raise AssertionError("jamg'arma ulushi noto'g'ri")
        steps.append("tranzaksiyalar va hisobot")

        app.auth.logout(session)
        steps.append("chiqish")
    finally:
        app.close()
    return steps
