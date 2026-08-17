"""Dastur/APK kelib chiqishi — spec §16 (R12 tuzatishi).

ROSTOR Android'ning o'z imzolash sxemasini (APK Signature Scheme v2/v3)
ALMASHTIRMAYDI yoki qayta amalga oshirmaydi — u tashqaridan Android
tomonidan imzolangan aniq APK'ni **vouch qiladi** (tasdiqlaydi).

MUHIM: `apk_sha256` va `android_signing_cert_sha256` — Android'ning O'ZI
ishlatadigan **SHA-256** algoritmi bilan hisoblanadi, **SHA3-256 EMAS**
— bu ROSTOR'ning boshqa joylardagi xesh tanlovidan ATAYLAB farq qiladi,
chunki bu maydonlar Android tooling (masalan `apksigner`) natijasi bilan
bayt-bayt mos kelishi kerak. `publisher_sig` esa, xuddi boshqa barcha
ROSTOR obyektlari kabi, gibrid (Ed25519+ML-DSA-65) imzo.
"""
from __future__ import annotations

import hashlib
import time
from dataclasses import dataclass
from typing import Optional

from ..crypto import canonical
from ..crypto.primitives import HybridSignature, hybrid_sign, hybrid_verify
from .errors import RostorError

CHANNELS = ("official", "play_store", "direct")


def android_sha256(data: bytes) -> bytes:
    """Android'ning o'z digest algoritmi — SHA3 EMAS, oddiy SHA-256.
    Bu funksiya ataylab `crypto/primitives.py` dagi SHA3-256 dan
    ALOHIDA — ikkalasini aralashtirib yubormaslik uchun."""
    return hashlib.sha256(data).digest()


@dataclass
class ApkManifestAttestation:
    v: int
    package_name: str
    version_code: int
    channel: str
    apk_sha256: bytes                       # Android SHA-256 (32 bayt)
    android_signing_cert_sha256: bytes      # Android SHA-256 (32 bayt)
    signing_lineage_ref: Optional[bytes]
    publisher_id: bytes
    issued_at: int
    expires_at: int
    publisher_sig: HybridSignature

    def _unsigned_dict(self) -> dict:
        return {
            "v": self.v, "package_name": self.package_name, "version_code": self.version_code,
            "channel": self.channel, "apk_sha256": self.apk_sha256,
            "android_signing_cert_sha256": self.android_signing_cert_sha256,
            "signing_lineage_ref": self.signing_lineage_ref, "publisher_id": self.publisher_id,
            "issued_at": self.issued_at, "expires_at": self.expires_at,
        }

    def signed_payload(self) -> bytes:
        return b"ROSTOR-1/apk-attestation" + canonical.encode(self._unsigned_dict())


def create_apk_attestation(
    publisher_idc, *, package_name: str, version_code: int, channel: str,
    apk_sha256: bytes, android_signing_cert_sha256: bytes,
    signing_lineage_ref: Optional[bytes] = None,
    lifetime_days: int = 365, now: Optional[int] = None,
) -> ApkManifestAttestation:
    if channel not in CHANNELS:
        raise RostorError(f"noma'lum channel: {channel}")
    if len(apk_sha256) != 32 or len(android_signing_cert_sha256) != 32:
        raise RostorError("Android SHA-256 xeshlari 32 bayt bo'lishi kerak")
    now = int(now if now is not None else time.time())
    att = ApkManifestAttestation(
        v=1, package_name=package_name, version_code=version_code, channel=channel,
        apk_sha256=apk_sha256, android_signing_cert_sha256=android_signing_cert_sha256,
        signing_lineage_ref=signing_lineage_ref, publisher_id=publisher_idc.device_id,
        issued_at=now, expires_at=now + lifetime_days * 86400,
        publisher_sig=HybridSignature(b"", b""),
    )
    att.publisher_sig = hybrid_sign(
        publisher_idc.ik_ed, publisher_idc.ik_mldsa, att.signed_payload()
    )
    return att


def verify_apk_attestation(
    att: ApkManifestAttestation, publisher_dc: dict,
    observed_apk_sha256: bytes, observed_cert_sha256: bytes,
    *, now: Optional[int] = None,
) -> bool:
    """`observed_apk_sha256`/`observed_cert_sha256` — foydalanuvchi
    qo'lidagi HAQIQIY faylning xeshlari — MAJBURIY parametrlar.

    TUZATISH (tashqi audit, 2026-08-17): avval bu ikkalasi ixtiyoriy edi
    va berilmasa TEKSHIRUV BUTUNLAY O'TKAZIB YUBORILARDI — natijada
    attestatsiya imzosi haqiqiy bo'lsa, u BOSHQA (hatto zararli) fayl
    uchun ham "tasdiqlangan" deb qaytishi mumkin edi. Endi bu ikki
    parametrsiz funksiya chaqirib bo'lmaydi — chaqiruvchi doim aniq
    QAYSI fayl haqida so'rayotganini ko'rsatishga majbur."""
    now = int(now if now is not None else time.time())
    if now > att.expires_at:
        return False
    if observed_apk_sha256 != att.apk_sha256:
        return False
    if observed_cert_sha256 != att.android_signing_cert_sha256:
        return False
    return hybrid_verify(
        publisher_dc["ed25519_pk"], publisher_dc["mldsa65_pk"],
        att.publisher_sig, att.signed_payload(),
    )
