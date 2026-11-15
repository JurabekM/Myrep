"""Terminal interfeysi: ssenariy bo'yicha boshidan oxirigacha."""

from __future__ import annotations

import io
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from fintx.cli import Cli

from .helpers import PASSWORD, FakeClock, make_app

PROJECT_ROOT = Path(__file__).resolve().parent.parent


class Script:
    """Oldindan yozilgan javoblar: oddiy kirish va yashirin (parol) kirish alohida."""

    def __init__(self, lines: list[str], secrets: list[str]) -> None:
        self.lines = list(lines)
        self.secrets = list(secrets)
        self.secret_prompts: list[str] = []

    def input(self, prompt: str) -> str:
        self.out.write(prompt)
        if not self.lines:
            raise EOFError
        return self.lines.pop(0)

    def getpass(self, prompt: str) -> str:
        self.secret_prompts.append(prompt)
        self.out.write(prompt + "\n")
        if not self.secrets:
            raise EOFError
        return self.secrets.pop(0)

    def run(self, app) -> str:
        self.out = io.StringIO()
        code = Cli(app, input_fn=self.input, getpass_fn=self.getpass, out=self.out).run()
        assert code == 0
        return self.out.getvalue()


class CliTests(unittest.TestCase):
    def setUp(self) -> None:
        self.clock = FakeClock()
        self.app = make_app(clock=self.clock)
        self.addCleanup(self.app.close)

    def test_full_flow(self) -> None:
        script = Script(
            lines=[
                "2",
                "jurabek",  # ro'yxatdan o'tish
                "1",
                "jurabek",  # kirish
                "1",
                "12 500 000,50",
                "1",
                "2026-11-01",
                "Noyabr maoshi",
                "2",
                "350000",
                "1",
                "",
                "Bozor",
                "2",
                "150000",
                "2",
                "2026-11-10",
                "",
                "3",
                "",
                "",  # tarix
                "4",
                "",
                "",  # hisobot
                "5",
                "3",
                "ha",  # o'chirish
                "3",
                "2026-11-01",
                "2026-11-30",
                "7",
                "0",
                "0",
            ],
            secrets=[PASSWORD, PASSWORD, PASSWORD],
        )
        out = script.run(self.app)
        self.assertIn("Hisob yaratildi", out)
        self.assertIn("Xush kelibsiz, jurabek!", out)
        self.assertIn("Saqlandi: #1  +12 500 000,50 so'm", out)
        self.assertIn("Saqlandi: #2  -350 000,00 so'm", out)
        self.assertIn("Jami: 3 ta yozuv.", out)
        self.assertIn("12 000 000,50", out)  # balans: 12 500 000,50 − 500 000
        self.assertIn("96,0 %", out)  # jamg'arma ulushi
        self.assertIn("70,0 %", out)  # oziq-ovqat ulushi
        self.assertIn("O'chirildi.", out)
        self.assertIn("Jami: 2 ta yozuv.", out)
        self.assertIn("Tizimga kirildi", out)
        self.assertIn("Xayr!", out)
        # Parol hech qayerda chiqmaydi va faqat yashirin kirish orqali so'raladi.
        self.assertNotIn(PASSWORD, out)
        self.assertEqual(len(script.secret_prompts), 3)

    def test_validation_errors_are_shown_and_menu_continues(self) -> None:
        self.app.auth.register("jurabek", PASSWORD)
        script = Script(
            lines=[
                "1",
                "jurabek",
                "2",
                "-5",  # noto'g'ri summa: darhol rad etiladi
                "2",
                "100",
                "99",  # yo'q kategoriya
                "2",
                "100",
                "1",
                "2099-01-01",  # kelajak sana
                "9",  # yo'q menyu bandi
                "3",
                "",
                "",
                "0",
                "0",
            ],
            secrets=[PASSWORD],
        )
        out = script.run(self.app)
        self.assertIn("! Summa noto'g'ri", out)
        self.assertIn("! Kategoriya raqami", out)
        self.assertIn("! Sana kelajakda", out)
        self.assertIn("! Bunday band yo'q.", out)
        self.assertIn("Tranzaksiyalar yo'q.", out)

    def test_failed_login_is_generic_and_lockout_is_reported(self) -> None:
        self.app.auth.register("jurabek", PASSWORD)
        lines, secrets = [], []
        for _ in range(5):
            lines += ["1", "jurabek"]
            secrets.append("xato-parol-xato-parol")
        lines += ["1", "begona"]
        secrets.append("xato-parol-xato-parol")
        lines.append("0")
        out = Script(lines, secrets).run(self.app)
        self.assertEqual(out.count("! Login yoki parol noto'g'ri."), 5)
        self.assertIn("Juda ko'p xato urinish. 30 soniyadan keyin", out)
        self.assertNotIn("xato-parol", out)

    def test_password_mismatch_on_registration(self) -> None:
        out = Script(["2", "jurabek", "0"], [PASSWORD, PASSWORD + "x"]).run(self.app)
        self.assertIn("! Parollar mos kelmadi.", out)
        count = self.app.conn.execute("SELECT COUNT(*) FROM users").fetchone()[0]
        self.assertEqual(count, 0)

    def test_idle_session_is_closed(self) -> None:
        self.app.auth.register("jurabek", PASSWORD)

        def lines():
            yield "1"
            yield "jurabek"
            self.clock.advance(16 * 60)  # 15 daqiqalik chegaradan o'tdi
            yield "3"
            yield "0"

        feed = lines()
        script = Script([], [PASSWORD])
        script.input = lambda prompt: next(feed)  # type: ignore[method-assign]
        out = script.run(self.app)
        self.assertIn("! Sessiya muddati tugadi. Qaytadan kiring.", out)
        self.assertNotIn("Davr (", out)  # tarix so'rovi bajarilmadi

    def test_stored_control_characters_are_neutralised_on_output(self) -> None:
        # Xizmat qatlamini chetlab o'tib yozilgan "zaharli" izoh ham ekranni buzmasin.
        self.app.auth.register("jurabek", PASSWORD)
        user_id = self.app.conn.execute("SELECT id FROM users").fetchone()[0]
        with self.app.conn:
            self.app.conn.execute(
                "INSERT INTO transactions "
                "(user_id, kind, amount_minor, category, note, occurred_on, created_at) "
                "VALUES (?, 'expense', 100, 'food', ?, '2026-11-01', 'x')",
                (user_id, "\x1b[2J\x1b[31mBuzuq"),
            )
        out = Script(["1", "jurabek", "3", "", "", "0", "0"], [PASSWORD]).run(self.app)
        self.assertNotIn("\x1b", out)
        self.assertIn("?[2J?[31mBuzuq", out)

    def test_end_of_input_exits_cleanly(self) -> None:
        self.app.auth.register("jurabek", PASSWORD)
        out = Script(["1", "jurabek"], [PASSWORD]).run(self.app)
        self.assertIn("Xayr!", out)
        events = [
            row[0] for row in self.app.conn.execute("SELECT event FROM audit_log ORDER BY id")
        ]
        self.assertEqual(events[-1], "logout")


class EntryPointTests(unittest.TestCase):
    """`python -m fintx` haqiqiy jarayon sifatida ishga tushishini tekshiradi."""

    def run_module(self, *args: str, stdin: str = "") -> subprocess.CompletedProcess:
        env = dict(os.environ, PYTHONIOENCODING="utf-8", PYTHONPATH=str(PROJECT_ROOT))
        return subprocess.run(
            [sys.executable, "-m", "fintx", *args],
            input=stdin,
            capture_output=True,
            text=True,
            encoding="utf-8",
            cwd=PROJECT_ROOT,
            env=env,
            timeout=60,
        )

    def test_version(self) -> None:
        result = self.run_module("--version")
        self.assertEqual(result.returncode, 0)
        self.assertIn("fintx 0.1.0", result.stdout)

    def test_starts_and_exits_from_menu(self) -> None:
        with tempfile.TemporaryDirectory() as folder:
            result = self.run_module("--db", str(Path(folder) / "fintx.db"), stdin="0\n")
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertIn("1) Kirish", result.stdout)
            self.assertIn("Xayr!", result.stdout)

    def test_corrupt_database_gives_clean_error(self) -> None:
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "fintx.db"
            path.write_bytes(b"bu SQLite fayli emas" * 100)
            result = self.run_module("--db", str(path), stdin="0\n")
            self.assertEqual(result.returncode, 1)
            self.assertIn("Xato:", result.stderr)
            self.assertNotIn("Traceback", result.stderr)


if __name__ == "__main__":
    unittest.main()
