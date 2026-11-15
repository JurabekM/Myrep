"""Reliz tekshiruvi (`--self-test`) o'zi ishlashini tasdiqlaydi."""

from __future__ import annotations

import contextlib
import io
import unittest

from fintx.cli import main
from fintx.selftest import run_core_selftest


class SelfTestTests(unittest.TestCase):
    def test_core_selftest_passes(self) -> None:
        steps = run_core_selftest()
        self.assertEqual(len(steps), 4)
        self.assertTrue(steps[0].startswith("parol xeshi: "))

    def test_cli_flag_reports_success(self) -> None:
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            code = main(["--self-test"])
        self.assertEqual(code, 0)
        self.assertIn("muvaffaqiyatli", out.getvalue())


if __name__ == "__main__":
    unittest.main()
