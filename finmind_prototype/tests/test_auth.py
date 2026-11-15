"""Ro'yxatdan o'tish, kirish, qulflash, sessiya va jurnal."""

from __future__ import annotations

import os
import stat
import tempfile
import unittest
from pathlib import Path

from fintx.auth import (
    IDLE_TIMEOUT_SECONDS,
    LOCK_MAX_SECONDS,
    MAX_FAILED_ATTEMPTS,
    lock_duration,
)
from fintx.errors import AccountLocked, AuthError, SessionExpired, ValidationError
from fintx.security import PasswordHasher

from .helpers import FAST_HASHER, OTHER_PASSWORD, PASSWORD, FakeClock, make_app


class AuthTestCase(unittest.TestCase):
    def setUp(self) -> None:
        self.clock = FakeClock()
        self.app = make_app(clock=self.clock)
        self.addCleanup(self.app.close)
        self.auth = self.app.auth

    def stored_hash(self, username: str = "jurabek") -> str:
        row = self.app.conn.execute(
            "SELECT password_hash FROM users WHERE username = ?", (username,)
        ).fetchone()
        return row["password_hash"]

    def fail_login(self, times: int, username: str = "jurabek") -> None:
        for _ in range(times):
            with self.assertRaises(AuthError):
                self.auth.login(username, "xato-parol-xato-parol")


class RegistrationTests(AuthTestCase):
    def test_register_then_login(self) -> None:
        user_id = self.auth.register("Jurabek", PASSWORD)
        session = self.auth.login("  JURABEK ", PASSWORD)
        self.assertEqual(session.user_id, user_id)
        self.assertEqual(session.username, "jurabek")
        self.assertTrue(session.active)

    def test_password_is_stored_only_as_hash(self) -> None:
        self.auth.register("jurabek", PASSWORD)
        stored = self.stored_hash()
        self.assertNotIn(PASSWORD, stored)
        self.assertTrue(stored.startswith(("scrypt$", "pbkdf2-sha256$")))
        dump = "\n".join(self.app.conn.iterdump())
        self.assertNotIn(PASSWORD, dump)

    def test_duplicate_username_is_rejected_case_insensitively(self) -> None:
        self.auth.register("jurabek", PASSWORD)
        with self.assertRaises(ValidationError) as caught:
            self.auth.register("JuraBek", OTHER_PASSWORD)
        self.assertEqual(caught.exception.field, "username")

    def test_weak_password_is_rejected_and_no_user_created(self) -> None:
        with self.assertRaises(ValidationError):
            self.auth.register("jurabek", "qisqa")
        count = self.app.conn.execute("SELECT COUNT(*) FROM users").fetchone()[0]
        self.assertEqual(count, 0)

    def test_sql_injection_in_username_is_rejected(self) -> None:
        for name in ("x' OR '1'='1", "admin'--", "a; DROP TABLE users;--"):
            with self.subTest(name=name), self.assertRaises(ValidationError):
                self.auth.register(name, PASSWORD)
        self.app.conn.execute("SELECT COUNT(*) FROM users").fetchone()


class LoginTests(AuthTestCase):
    def setUp(self) -> None:
        super().setUp()
        self.auth.register("jurabek", PASSWORD)

    def test_wrong_password_and_unknown_user_give_same_message(self) -> None:
        with self.assertRaises(AuthError) as wrong_password:
            self.auth.login("jurabek", "xato-parol-xato-parol")
        with self.assertRaises(AuthError) as unknown_user:
            self.auth.login("begona", "xato-parol-xato-parol")
        with self.assertRaises(AuthError) as invalid_name:
            self.auth.login("x' OR '1'='1", "xato-parol-xato-parol")
        messages = {
            str(wrong_password.exception),
            str(unknown_user.exception),
            str(invalid_name.exception),
        }
        self.assertEqual(len(messages), 1)
        self.assertNotIsInstance(unknown_user.exception, AccountLocked)

    def test_unknown_user_still_costs_a_hash_verification(self) -> None:
        calls: list[str] = []

        class CountingHasher(PasswordHasher):
            def verify(self, password: str, encoded: str) -> bool:
                calls.append(encoded)
                return super().verify(password, encoded)

        app = make_app()
        self.addCleanup(app.close)
        app.auth._hasher = CountingHasher(scrypt_ln=8, pbkdf2_iterations=1_000)
        with self.assertRaises(AuthError):
            app.auth.login("begona", "xato-parol-xato-parol")
        self.assertEqual(len(calls), 1)

    def test_non_string_and_oversized_credentials(self) -> None:
        for username, password in (
            (None, PASSWORD),
            ("jurabek", None),
            ("jurabek", b"bytes"),
            ("jurabek", "x" * 10_000),
        ):
            with self.subTest(username=username), self.assertRaises(AuthError):
                self.auth.login(username, password)

    def test_account_locks_after_repeated_failures(self) -> None:
        self.fail_login(MAX_FAILED_ATTEMPTS - 1)
        with self.assertRaises(AccountLocked) as caught:
            self.auth.login("jurabek", "xato-parol-xato-parol")
        self.assertEqual(caught.exception.retry_after, 30)
        # Qulf paytida to'g'ri parol ham qabul qilinmaydi.
        with self.assertRaises(AccountLocked):
            self.auth.login("jurabek", PASSWORD)

    def test_lock_expires_and_success_resets_counter(self) -> None:
        self.fail_login(MAX_FAILED_ATTEMPTS)
        self.clock.advance(31)
        session = self.auth.login("jurabek", PASSWORD)
        self.assertTrue(session.active)
        row = self.app.conn.execute(
            "SELECT failed_attempts, locked_until FROM users WHERE username = 'jurabek'"
        ).fetchone()
        self.assertEqual(row["failed_attempts"], 0)
        self.assertIsNone(row["locked_until"])

    def test_lock_grows_with_further_failures(self) -> None:
        self.fail_login(MAX_FAILED_ATTEMPTS)
        self.clock.advance(31)
        with self.assertRaises(AccountLocked) as caught:
            self.auth.login("jurabek", "xato-parol-xato-parol")
        self.assertEqual(caught.exception.retry_after, 60)
        self.assertEqual(lock_duration(MAX_FAILED_ATTEMPTS + 2), 120)
        self.assertEqual(lock_duration(10_000), LOCK_MAX_SECONDS)

    def test_one_users_lock_does_not_affect_another(self) -> None:
        self.auth.register("malika", OTHER_PASSWORD)
        self.fail_login(MAX_FAILED_ATTEMPTS)
        self.assertTrue(self.auth.login("malika", OTHER_PASSWORD).active)

    def test_weak_hash_is_upgraded_on_login(self) -> None:
        weak = PasswordHasher(scrypt_ln=4, pbkdf2_iterations=10)
        with self.app.conn:
            self.app.conn.execute(
                "UPDATE users SET password_hash = ? WHERE username = 'jurabek'",
                (weak.hash(PASSWORD),),
            )
        self.assertTrue(FAST_HASHER.needs_rehash(self.stored_hash()))
        self.auth.login("jurabek", PASSWORD)
        self.assertFalse(FAST_HASHER.needs_rehash(self.stored_hash()))
        self.assertTrue(self.auth.login("jurabek", PASSWORD).active)


class SessionTests(AuthTestCase):
    def setUp(self) -> None:
        super().setUp()
        self.auth.register("jurabek", PASSWORD)
        self.session = self.auth.login("jurabek", PASSWORD)

    def test_activity_keeps_session_alive(self) -> None:
        for _ in range(5):
            self.clock.advance(IDLE_TIMEOUT_SECONDS - 1)
            self.auth.require(self.session)
        self.assertTrue(self.session.active)

    def test_idle_session_expires(self) -> None:
        self.clock.advance(IDLE_TIMEOUT_SECONDS + 1)
        self.assertTrue(self.auth.is_expired(self.session))
        with self.assertRaises(SessionExpired):
            self.auth.require(self.session)
        # Muddati o'tgan sessiya vaqt orqaga qaytsa ham tirilmaydi.
        self.clock.advance(-IDLE_TIMEOUT_SECONDS)
        with self.assertRaises(SessionExpired):
            self.auth.require(self.session)

    def test_logout_invalidates_session(self) -> None:
        self.auth.logout(self.session)
        with self.assertRaises(SessionExpired):
            self.auth.require(self.session)
        with self.assertRaises(SessionExpired):
            self.app.transactions.history(self.session)

    def test_change_password(self) -> None:
        self.auth.change_password(self.session, PASSWORD, OTHER_PASSWORD)
        with self.assertRaises(AuthError):
            self.auth.login("jurabek", PASSWORD)
        self.assertTrue(self.auth.login("jurabek", OTHER_PASSWORD).active)

    def test_change_password_requires_current_password(self) -> None:
        with self.assertRaises(AuthError):
            self.auth.change_password(self.session, "xato-parol-xato", OTHER_PASSWORD)
        self.assertTrue(self.auth.login("jurabek", PASSWORD).active)

    def test_change_password_enforces_policy_and_difference(self) -> None:
        with self.assertRaises(ValidationError):
            self.auth.change_password(self.session, PASSWORD, "qisqa")
        with self.assertRaises(ValidationError):
            self.auth.change_password(self.session, PASSWORD, PASSWORD)

    def test_repeated_wrong_current_password_closes_session(self) -> None:
        for _ in range(MAX_FAILED_ATTEMPTS - 1):
            with self.assertRaises(AuthError):
                self.auth.change_password(self.session, "xato-parol-xato", OTHER_PASSWORD)
        with self.assertRaises(SessionExpired):
            self.auth.change_password(self.session, "xato-parol-xato", OTHER_PASSWORD)
        self.assertFalse(self.session.active)


class AuditTests(AuthTestCase):
    def test_events_are_recorded_without_secrets(self) -> None:
        self.auth.register("jurabek", PASSWORD)
        with self.assertRaises(AuthError):
            self.auth.login("jurabek", "xato-parol-SIR-12345")
        # Login maydoniga adashib parol terilgan holat: jurnalga tushmasligi kerak.
        with self.assertRaises(AuthError):
            self.auth.login("Adashgan-Parol-999", "xato-parol-SIR-12345")
        session = self.auth.login("jurabek", PASSWORD)
        events = [e.event for e in self.auth.audit_events(session)]
        self.assertEqual(events, ["login_ok", "login_failed", "register"])
        dump = "\n".join(self.app.conn.iterdump())
        for secret in (PASSWORD, "xato-parol-SIR-12345", "Adashgan-Parol-999"):
            self.assertNotIn(secret, dump)
            self.assertNotIn(secret.lower(), dump)

    def test_user_sees_only_own_events(self) -> None:
        self.auth.register("jurabek", PASSWORD)
        self.auth.register("malika", OTHER_PASSWORD)
        self.auth.login("jurabek", PASSWORD)
        malika = self.auth.login("malika", OTHER_PASSWORD)
        events = self.auth.audit_events(malika)
        self.assertEqual([e.event for e in events], ["login_ok", "register"])


class DatabaseFileTests(unittest.TestCase):
    @unittest.skipUnless(os.name == "posix", "POSIX fayl ruxsatlari")
    def test_database_file_is_private(self) -> None:
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "nested" / "fintx.db"
            app = make_app(str(path))
            app.auth.register("jurabek", PASSWORD)
            app.close()
            self.assertEqual(stat.S_IMODE(path.stat().st_mode), 0o600)
            self.assertNotIn(PASSWORD.encode(), path.read_bytes())

    @unittest.skipUnless(os.name == "posix", "POSIX fayl ruxsatlari")
    def test_loose_permissions_are_tightened(self) -> None:
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "fintx.db"
            path.touch(mode=0o644)
            os.chmod(path, 0o644)
            make_app(str(path)).close()
            self.assertEqual(stat.S_IMODE(path.stat().st_mode), 0o600)

    def test_data_survives_reopen(self) -> None:
        with tempfile.TemporaryDirectory() as folder:
            path = str(Path(folder) / "fintx.db")
            app = make_app(path)
            app.auth.register("jurabek", PASSWORD)
            app.close()
            app = make_app(path)
            self.assertTrue(app.auth.login("jurabek", PASSWORD).active)
            app.close()


if __name__ == "__main__":
    unittest.main()
