"""AETHER-Q v5.1.0 — vendor qilingan yadro. O'ZGARTIRILMAYDI.

Manba: ``C:/Users/comp_2.1/Downloads/aether_q_v3/aether_q_v51/`` (v5.1.0).
Nusxaning baytma-bayt o'zgarmaganini
``tests/security/test_aetherq_vendor.py`` SHA-256 manifesti bilan qulflaydi.

Nega manifest kerak: ``ruff --fix`` yoki formatter auditdan o'tgan kripto
kodini «tozalab» qo'yishi mumkin — kod ishlashda davom etadi, hech qanday
test yiqilmaydi, o'zgarish jimgina o'tib ketadi. Kriptografiyada auditor
tekshirgan bayt bilan ishlatilayotgan bayt bir xil bo'lishi SHART.

Olingan modullar (0x01 HYBRID / 0x03 MINIMAL production profillari):

* ``kdf``       — HKDF-SHA3-256, KMAC256, cSHAKE256, constant-time yordamchilar
* ``kem``       — ML-KEM-768 (FIPS 203, OpenSSL orqali)
* ``sig``       — ML-DSA-65 (FIPS 204)
* ``hybrid``    — ML-KEM + X25519 gibrid combiner (profil 0x01)
* ``handshake`` — negotiation, kalit jadvali, resumption, ticket
* ``transport`` — §8 AEAD record qatlami (ChaCha20-Poly1305)
* ``dos``       — stateless PoW cookie
* ``early``     — 0-RTT (ISHLATILMAYDI; ``handshake`` import qiladi)
* ``field``     — GF(p) arifmetikasi (``hybrid`` uchun)

OLINMAGAN: ``zkp*``, ``threshold*``, ``dkg_pq``, ``kkw``, ``lsag``, ``puf``,
``mimc``, ``zkboo`` — 0x06/0x07/0x08 tadqiqot profillari, AETHER-Q ning
5-audit raundida ikkita KRITIK topilma (AQ-L01, AQ-L02) sababli deployable
build'dan chiqarilgan. ``net`` — TCP framing, bizda transport MQTT.

⚠ HALOL BAHO: AETHER-Q ning o'z hujjatlari bo'yicha maqomi «tadqiqot/demo —
tayyor; pilot — shartli; production — mustaqil audit SHART». DistribOS AI
uni sinovdan o'tgan qatlam sifatida ishlatadi, sertifikatlangan deb da'vo
QILMAYDI. Batafsil: ``docs/SECURITY.md``.
"""

from __future__ import annotations

AETHERQ_VERSION = "5.1.0"

PROFILE_HYBRID = 0x01
PROFILE_MINIMAL = 0x03

from . import dos, handshake, hybrid, kdf, kem, sig, transport  # noqa: E402

__all__ = [
    "AETHERQ_VERSION",
    "PROFILE_HYBRID",
    "PROFILE_MINIMAL",
    "dos",
    "handshake",
    "hybrid",
    "kdf",
    "kem",
    "sig",
    "transport",
]
