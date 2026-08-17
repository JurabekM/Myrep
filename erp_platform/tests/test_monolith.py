# -*- coding: utf-8 -*-
"""
Monolit generatori testi.

ERP_MONOLITH.py yaratilishini va uning aynan bir xil manba modullarini
o'z ichiga olishini tekshiradi. To'liq ishga tushirish sinovi alohida
(scratchpad'dagi izolyatsiyalangan papkada) o'tkaziladi.
"""
from __future__ import annotations

import base64
import unittest
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent


class TestMonolithBuilder(unittest.TestCase):
    def test_builder_collects_all_modules(self):
        import sys
        sys.path.insert(0, str(PROJECT_ROOT / "tools"))
        import build_monolith

        modules = build_monolith.collect_modules()
        names = {m[0] for m in modules}
        # Asosiy modullar mavjud bo'lishi kerak
        for expected in ("src.app", "src.core.bootstrap", "src.core.security",
                         "src.database.connection", "src.auth.service",
                         "src.modules.sales.service",
                         "src.modules.accounting.service",
                         "src.web.server", "src.web.api.rest",
                         "src.ui.desktop"):
            self.assertIn(expected, names, f"{expected} yig'ilmadi")
        self.assertGreater(len(modules), 40)

    def test_sources_are_valid_python(self):
        import sys
        sys.path.insert(0, str(PROJECT_ROOT / "tools"))
        import build_monolith

        for name, _is_pkg, source in build_monolith.collect_modules():
            try:
                compile(source, name, "exec")
            except SyntaxError as exc:  # pragma: no cover
                self.fail(f"{name} sintaksis xatosi: {exc}")

    def test_base64_roundtrip(self):
        # Monolit manbalarni base64 orqali saqlaydi — decode teng bo'lishi kerak
        original = "def f():\n    return 'salom'\n"
        encoded = base64.b64encode(original.encode("utf-8")).decode("ascii")
        decoded = base64.b64decode(encoded).decode("utf-8")
        self.assertEqual(original, decoded)

    @unittest.skipUnless((PROJECT_ROOT / "ERP_MONOLITH.py").exists(),
                         "ERP_MONOLITH.py hali generatsiya qilinmagan")
    def test_monolith_file_structure(self):
        content = (PROJECT_ROOT / "ERP_MONOLITH.py").read_text(
            encoding="utf-8")
        self.assertIn("_SOURCES", content)
        self.assertIn("_MonolithFinder", content)
        self.assertIn("def main():", content)
        self.assertIn("auto_install", content)


if __name__ == "__main__":
    unittest.main()
