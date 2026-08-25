"""Vendor qilingan AETHER-Q nusxasi O'ZGARMAGANINI qulflaydi.

Nega bu test bor: formatter yoki ``ruff --fix`` auditdan o'tgan kripto
modullarini «tozalab» qo'yishi mumkin (importlarni tartiblaydi, qatorlarni
qayta o'raydi). Kod ishlashda davom etadi, ya'ni **hech qanday test
yiqilmaydi** — o'zgarish jimgina o'tib ketadi. Kriptografiyada bu qabul
qilib bo'lmaydigan holat: auditor tekshirgan bayt bilan biz ishlatayotgan
bayt bir xil bo'lishi kerak.

Yangi AETHER-Q versiyasiga o'tilganda manifest ATAYLAB yangilanadi va
o'zgarish commit'da ko'rinadi.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pytest

_ROOT = Path(__file__).resolve().parents[2]
VENDOR_DIR = _ROOT / "apps" / "desktop" / "src" / "distribos" / "aether_q" / "vendor"
MANIFEST = Path(__file__).resolve().parent / "aetherq_vendor_manifest.json"


def _manifest() -> dict[str, str]:
    return dict(json.loads(MANIFEST.read_text(encoding="utf-8"))["files"])


def test_manifest_covers_every_vendored_module() -> None:
    present = {f.name for f in VENDOR_DIR.glob("*.py")} - {"__init__.py"}
    assert present == set(_manifest()), (
        "Vendor papkasidagi fayllar manifestga mos emas — yangi fayl "
        "qo'shildi yoki o'chirildi. Manifestni ataylab yangilang."
    )


@pytest.mark.parametrize("name", sorted(_manifest()))
def test_vendored_module_is_byte_identical(name: str) -> None:
    digest = hashlib.sha256((VENDOR_DIR / name).read_bytes()).hexdigest()
    assert digest == _manifest()[name], (
        f"{name} o'zgargan! Auditdan o'tgan kripto kodi tahrirlanmasligi "
        "kerak. Agar bu ataylab bo'lsa (yangi AETHER-Q versiyasi), "
        "manifestni yangilang va commit izohida asoslang."
    )


def test_research_profiles_are_not_vendored() -> None:
    """0x06/0x07/0x08 tadqiqot profillari olib kelinmagan (AQ-L01, AQ-L02)."""
    forbidden = {
        "zkp.py", "zkp_pq.py", "zkboo.py", "kkw.py", "lsag.py", "mimc.py",
        "threshold.py", "threshold_pq.py", "dkg_pq.py", "puf.py",
    }
    present = {f.name for f in VENDOR_DIR.glob("*.py")}
    leaked = sorted(present & forbidden)
    assert not leaked, (
        f"Tadqiqot profillari deployable build'ga kirmasligi kerak: {leaked}"
    )


def test_aetherq_uses_real_post_quantum_primitives() -> None:
    """Mock KEM emas, HAQIQIY ML-KEM-768 / ML-DSA-65 ishlayotganini tasdiqlaydi."""
    from distribos.aether_q.vendor import kem, sig

    public_key, secret_key = kem.MLKEM768.keygen()
    assert len(public_key) == 1184, "ML-KEM-768 ochiq kaliti 1184 bayt bo'lishi kerak"
    ciphertext, shared = kem.MLKEM768.encaps(public_key)
    assert len(ciphertext) == 1088
    assert len(shared) == 32
    assert kem.MLKEM768.decaps(secret_key, ciphertext) == shared

    sign_pk, sign_sk = sig.MLDSA65.keygen()
    assert len(sign_pk) == 1952, "ML-DSA-65 ochiq kaliti 1952 bayt bo'lishi kerak"
    signature = sig.MLDSA65.sign(sign_sk, b"distribos-ai")
    assert len(signature) == 3309
    assert sig.MLDSA65.verify(sign_pk, signature, b"distribos-ai")
    assert not sig.MLDSA65.verify(sign_pk, signature, b"boshqa xabar")
