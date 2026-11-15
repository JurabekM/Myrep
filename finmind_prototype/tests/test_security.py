"""Parol xeshlash: format, tuz, tekshiruv, parametrlarni yangilash."""

from __future__ import annotations

import unittest

from fintx.security import PasswordHasher, scrypt_available

from .helpers import FAST_HASHER, PASSWORD

PBKDF2_ONLY = PasswordHasher(prefer_scrypt=False, pbkdf2_iterations=1_000)


class PasswordHasherTests(unittest.TestCase):
    def test_production_defaults_meet_owasp_minimums(self) -> None:
        defaults = PasswordHasher()
        self.assertGreaterEqual(defaults.scrypt_ln, 17)
        self.assertGreaterEqual(defaults.scrypt_r, 8)
        self.assertGreaterEqual(defaults.scrypt_p, 1)
        self.assertGreaterEqual(defaults.pbkdf2_iterations, 600_000)

    @unittest.skipUnless(scrypt_available(), "bu muhitda scrypt yo'q")
    def test_production_parameters_actually_run(self) -> None:
        # 128 MiB xotira talab qiladigan haqiqiy parametrlar bilan bir marta.
        hasher = PasswordHasher()
        encoded = hasher.hash(PASSWORD)
        self.assertTrue(encoded.startswith("scrypt$ln=17,r=8,p=1$"))
        self.assertTrue(hasher.verify(PASSWORD, encoded))
        self.assertFalse(hasher.verify(PASSWORD + "x", encoded))

    def test_hash_does_not_contain_password(self) -> None:
        encoded = FAST_HASHER.hash(PASSWORD)
        self.assertNotIn(PASSWORD, encoded)
        self.assertEqual(encoded.count("$"), 3)

    def test_each_hash_has_its_own_salt(self) -> None:
        first, second = FAST_HASHER.hash(PASSWORD), FAST_HASHER.hash(PASSWORD)
        self.assertNotEqual(first, second)
        self.assertTrue(FAST_HASHER.verify(PASSWORD, first))
        self.assertTrue(FAST_HASHER.verify(PASSWORD, second))

    def test_verify_rejects_wrong_password(self) -> None:
        encoded = FAST_HASHER.hash(PASSWORD)
        for candidate in ("", PASSWORD[:-1], PASSWORD + " ", PASSWORD.upper()):
            with self.subTest(candidate=candidate):
                self.assertFalse(FAST_HASHER.verify(candidate, encoded))

    def test_unicode_password_is_normalised(self) -> None:
        # "é" bitta belgi va "e" + urg'u belgisi bir xil parol hisoblanadi (NFKC).
        encoded = FAST_HASHER.hash("café-parol-uzun-12")
        self.assertTrue(FAST_HASHER.verify("café-parol-uzun-12", encoded))

    def test_pbkdf2_fallback(self) -> None:
        encoded = PBKDF2_ONLY.hash(PASSWORD)
        self.assertTrue(encoded.startswith("pbkdf2-sha256$i=1000$"))
        self.assertTrue(PBKDF2_ONLY.verify(PASSWORD, encoded))
        self.assertFalse(PBKDF2_ONLY.verify("boshqa-parol-123", encoded))
        # Algoritm xesh satridan aniqlanadi: boshqa sozlamali xeshlovchi ham tekshira oladi.
        self.assertTrue(FAST_HASHER.verify(PASSWORD, encoded))

    def test_malformed_hashes_never_verify(self) -> None:
        good = FAST_HASHER.hash(PASSWORD)
        algo, params, salt, key = good.split("$")
        malformed = [
            "",
            "plain-text-password",
            PASSWORD,
            f"{algo}${params}${salt}",
            f"md5${params}${salt}${key}",
            f"{algo}$ln=8,r=8${salt}${key}",
            f"{algo}$ln=99,r=8,p=1${salt}${key}",  # xotirani yeb qo'yadigan parametr
            f"{algo}$ln=8,r=8,p=1,ln=9${salt}${key}",
            f"{algo}$ln=-8,r=8,p=1${salt}${key}",
            f"{algo}${params}$!!!!${key}",
            f"{algo}${params}${salt}$AAAA",
            f"pbkdf2-sha256$i=999999999999${salt}${key}",
            "x" * 5000,
        ]
        for encoded in malformed:
            with self.subTest(encoded=encoded[:40]):
                self.assertFalse(FAST_HASHER.verify(PASSWORD, encoded))
                self.assertTrue(FAST_HASHER.needs_rehash(encoded))

    def test_needs_rehash_when_parameters_are_weaker(self) -> None:
        weak = PasswordHasher(scrypt_ln=4, pbkdf2_iterations=10)
        encoded = weak.hash(PASSWORD)
        self.assertFalse(weak.needs_rehash(encoded))
        self.assertTrue(FAST_HASHER.needs_rehash(encoded))
        self.assertFalse(FAST_HASHER.needs_rehash(FAST_HASHER.hash(PASSWORD)))

    @unittest.skipUnless(scrypt_available(), "bu muhitda scrypt yo'q")
    def test_pbkdf2_hash_is_upgraded_to_scrypt(self) -> None:
        self.assertTrue(FAST_HASHER.needs_rehash(PBKDF2_ONLY.hash(PASSWORD)))


if __name__ == "__main__":
    unittest.main()
