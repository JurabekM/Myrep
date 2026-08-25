"""Lokalizatsiya — `tr()` xavfsizligi va tarjima to'liqligi.

Ikkita narsa tekshiriladi:

1. `tr()` funksiyasining o'zi — tarjima topilmasa asl matn qaytishi,
   noma'lum til rad etilishi (fail-closed).
2. `presentation/main_window.py` va `presentation/pages/system.py`
   ichidagi HAR BIR `tr(...)` chaqiruvi (shu jumladan navigatsiya
   ro'yxatidagi dinamik matnlar) `i18n/ru.json` da tarjimaga ega —
   busiz yangi qo'shilgan matn "tarjima qilingan" deb hisoblanib,
   aslida asl o'zbekcha holida qolib ketishi mumkin edi va buni hech
   kim payqamasdi (`tr()` hech qachon xato bermaydi — bu ataylab, lekin
   shu tufayli yetishmagan tarjimani FAQAT shu sinov ushlaydi).
"""

from __future__ import annotations

import ast
import json
from pathlib import Path

import pytest
from distribos import i18n

_REPO_ROOT = Path(__file__).resolve().parents[2]
_RU_PATH = _REPO_ROOT / "i18n" / "ru.json"

#: `tr()` orqali o'tkazilgan fayllar. Navigatsiya ro'yxati kabi
#: DINAMIK (o'zgaruvchidan keladigan) chaqiruvlar AST orqali
#: ko'rinmaydi, shuning uchun ular qo'lda qo'shiladi.
_WRAPPED_FILES = (
    "apps/desktop/src/distribos/presentation/main_window.py",
    "apps/desktop/src/distribos/presentation/pages/system.py",
    "apps/desktop/src/distribos/presentation/pages/sales.py",
    "apps/desktop/src/distribos/presentation/pages/operations.py",
    "apps/desktop/src/distribos/presentation/pages/reporting.py",
    "apps/desktop/src/distribos/presentation/pages/base.py",
    "apps/desktop/src/distribos/presentation/status.py",
)

#: `main_window.NAVIGATION` — bo'lim va sahifa nomlari `tr(section)` /
#: `tr(title)` orqali dinamik o'tadi (AST bunday chaqiruvni ko'ravermaydi).
_DYNAMIC_STRINGS = (
    "SAVDO", "OMBOR VA MOLIYA", "HISOBOT", "TIZIM",
    "Buyurtmalar", "Mijozlar", "Mahsulotlar",
    "Ombor", "Kassa va to'lovlar", "Tashriflar",
    "Hisobotlar", "Hujjatlar", "AI yordamchi",
    "Sinxronizatsiya", "Tekshiruv navbati", "Xavfsizlik",
    "Zaxira nusxa", "Audit jurnali", "Sozlamalar",
)


def _tr_call_strings(path: Path) -> set[str]:
    """Fayldagi `tr("literal matn")` chaqiruvlarining literal argumentlari."""
    tree = ast.parse(path.read_text(encoding="utf-8"))
    found: set[str] = set()
    for node in ast.walk(tree):
        if (
            isinstance(node, ast.Call)
            and isinstance(node.func, ast.Name)
            and node.func.id == "tr"
            and node.args
            and isinstance(node.args[0], ast.Constant)
            and isinstance(node.args[0].value, str)
        ):
            found.add(node.args[0].value)
    return found


def _all_wrapped_strings() -> set[str]:
    strings: set[str] = set(_DYNAMIC_STRINGS)
    for rel in _WRAPPED_FILES:
        strings |= _tr_call_strings(_REPO_ROOT / rel)
    return strings


def test_tr_asosiy_tilda_ozgarmaydi():
    i18n.set_locale("uz-Latn")
    assert i18n.tr("Saqlash") == "Saqlash"


def test_tr_royxatga_olinmagan_matnni_ozgarishsiz_qaytaradi():
    """Tarjima yo'q matn — bo'sh emas, aynan o'zi qaytadi (fail-safe)."""
    i18n.set_locale("ru")
    try:
        assert i18n.tr("Bu matn hech qachon tarjima qilinmaydi 12345") == (
            "Bu matn hech qachon tarjima qilinmaydi 12345"
        )
    finally:
        i18n.set_locale(i18n.DEFAULT_LOCALE)


def test_tr_royxatdagi_matnni_targima_qiladi():
    i18n.set_locale("ru")
    try:
        assert i18n.tr("Sozlamalar") == "Настройки"
    finally:
        i18n.set_locale(i18n.DEFAULT_LOCALE)


def test_bosh_matn_xato_bermaydi():
    assert i18n.tr("") == ""


def test_nomalum_til_rad_etiladi():
    """Fail-closed: yozuv xatosi (masalan 'ru-RU') jimgina asosiy tilga
    o'tib ketmasligi kerak — bu xato ekanini aniq ko'rsatish kerak."""
    with pytest.raises(i18n.UnsupportedLocaleError):
        i18n.set_locale("ru-RU")
    with pytest.raises(i18n.UnsupportedLocaleError):
        i18n.set_locale("uz-Cyrl")   # Kirill ATAYLAB qo'llab-quvvatlanmaydi


def test_ruscha_fayl_haqiqiy_json():
    data = json.loads(_RU_PATH.read_text(encoding="utf-8"))
    assert isinstance(data, dict)
    assert all(isinstance(k, str) and isinstance(v, str) for k, v in data.items())


def test_royxatdagi_har_bir_matn_tarjima_qilingan():
    """Manba kodidagi HAR bir `tr()` chaqiruvi `ru.json` da bor.

    Bu sinov aynan shuning uchun yozildi: `tr()` o'zi hech qachon xato
    bermaydi (tarjima yo'q bo'lsa asl matnni ko'rsatadi) — bu to'g'ri
    xulq, lekin shu sabab yangi qo'shilgan matn tarjimasiz qolib
    ketishini HECH KIM darhol payqamaydi. Faqat shu sinov ushlaydi.
    """
    source_strings = _all_wrapped_strings()
    translated = json.loads(_RU_PATH.read_text(encoding="utf-8"))
    missing = source_strings - translated.keys()
    assert not missing, f"ru.json da tarjima yo'q: {sorted(missing)}"


def test_ruscha_faylda_ortiqcha_kalit_yoq():
    """Manba kodidan olib tashlangan matn `ru.json` da QOLIB KETMASIN.

    Aks holda fayl vaqt o'tishi bilan o'lik yozuvlar bilan to'lib,
    qaysi tarjima hali kerakligini bilib bo'lmay qoladi.
    """
    source_strings = _all_wrapped_strings()
    translated = json.loads(_RU_PATH.read_text(encoding="utf-8"))
    stale = translated.keys() - source_strings
    assert not stale, f"ru.json da endi ishlatilmaydigan kalitlar: {sorted(stale)}"


def test_joyplaceholder_moslashadi():
    """`{n}`, `{peers}` kabi joy egalari ikkala tilda ham bir xil bo'lishi
    kerak — aks holda `.format()` `KeyError` bilan yiqiladi."""
    translated = json.loads(_RU_PATH.read_text(encoding="utf-8"))
    for source, target in translated.items():
        source_fields = {
            part.split("!")[0].split(":")[0]
            for _, part, _, _ in __import__("string").Formatter().parse(source)
            if part
        }
        target_fields = {
            part.split("!")[0].split(":")[0]
            for _, part, _, _ in __import__("string").Formatter().parse(target)
            if part
        }
        assert source_fields == target_fields, (
            f"joy egalari mos kelmaydi: {source!r} -> {target!r}"
        )
