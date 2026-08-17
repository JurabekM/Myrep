"""ROSTOR-1 — O'zbekistondagi kiberfiribgarlikka qarshi ishonch protokoli.

Spec: `docs/SPEC-ROSTOR-1.1.md`. Bu paket SCUTUM-Q1 transport qatlami
(`scutum.protocol`, `scutum.crypto`) ustiga quriladigan **ilova qatlami** —
identiteti, shaffoflik jurnali, tranzaksiya tasdiqlash, to'lov niyati,
akkount avtorizatsiyasi, firibgarlik hisoboti va APK obro'si.

DIQQAT: bu ISHLAB CHIQARISH uchun emas — spetsifikatsiyani sinash va
haqiqiy hujum ssenariylarini namoyish qilish uchun referens modeli.
"""

__all__ = [
    "smt",
    "transparency",
    "registrar",
    "identity",
    "badge",
    "txn_confirm",
    "payment",
    "account",
    "fraud_report",
    "apk",
]
