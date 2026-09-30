"""§8 — sertifikat (`.aqcert`): bank bergan vakolat."""

from __future__ import annotations

import json
import os
import time
from dataclasses import dataclass
from pathlib import Path

from .ibtido import imzo_togri, imzola, tagged_hash, u64be
from .konstanta import CERT_FORMAT, L_CERT, ML_DSA_IMZO_UZ, ML_DSA_PK_UZ, SERT_ID_UZ


OGOHLANTIRISH_KUN = 30
KUN_MS = 86_400_000


class SertifikatXatosi(ValueError):
    pass


@dataclass(frozen=True)
class Sertifikat:
    cert_id: bytes
    bank_public_key: bytes
    mint_public_key: bytes
    label: str
    limit_amount: int
    valid_from_ms: int
    valid_until_ms: int
    signature: bytes

    def xabar(self) -> bytes:
        """MINT-CERT/v1 — u32 BE prefiks, u64 BE sonlar (§2.6-b)."""
        return tagged_hash(L_CERT, self.mint_public_key, self.cert_id,
                           self.label.encode("utf-8"), u64be(self.limit_amount),
                           u64be(self.valid_from_ms), u64be(self.valid_until_ms))

    def imzo_togri(self) -> bool:
        return imzo_togri(self.bank_public_key, self.signature, self.xabar())

    def muammo(self, zarbxona_pk: bytes, hozir_ms: int | None = None) -> str | None:
        """§8.3 — tartib muhim, birinchi muammo qaytariladi. Yaroqli bo'lsa None."""
        hozir = int(time.time() * 1000) if hozir_ms is None else hozir_ms
        if self.mint_public_key != zarbxona_pk:
            return "sertifikat BOSHQA zarbxonaga berilgan"
        if not self.imzo_togri():
            return "bank imzosi noto'g'ri"
        if self.limit_amount <= 0:
            return "limit musbat emas"
        if hozir < self.valid_from_ms:
            return "sertifikat hali kuchga kirmagan"
        if hozir > self.valid_until_ms:
            return "sertifikat muddati o'tgan"
        return None

    def ogohlantirish(self, hozir_ms: int | None = None) -> str | None:
        """Muddat tugashiga ≤ 30 kun qolsa — ogohlantirish matni. Muddati o'tgan yoki
        hali kuchga kirmagan bo'lsa None: bular `muammo()` ning ishi."""
        hozir = int(time.time() * 1000) if hozir_ms is None else hozir_ms
        if not self.valid_from_ms <= hozir <= self.valid_until_ms:
            return None
        qolgan = self.valid_until_ms - hozir
        if qolgan > OGOHLANTIRISH_KUN * KUN_MS:
            return None
        sana = time.strftime("%Y-%m-%d %H:%M", time.localtime(self.valid_until_ms / 1000))
        if qolgan < KUN_MS:
            return (f"sertifikat muddati {max(1, qolgan // 3_600_000)} soatdan keyin tugaydi "
                    f"({sana}) — bankdan yangisini so'rang")
        kun = -(-qolgan // KUN_MS)
        return f"sertifikat muddati {kun} kundan keyin tugaydi ({sana}) — bankdan yangisini so'rang"

    # --- fayl -------------------------------------------------------------

    def lugat(self) -> dict:
        return {
            "format": CERT_FORMAT,
            "version": 1,
            "cert_id": self.cert_id.hex(),
            "bank_public_key": self.bank_public_key.hex(),
            "mint_public_key": self.mint_public_key.hex(),
            "label": self.label,
            "limit_amount": self.limit_amount,
            "valid_from_ms": self.valid_from_ms,
            "valid_until_ms": self.valid_until_ms,
            "signature": self.signature.hex(),
        }

    def json(self) -> str:
        return json.dumps(self.lugat(), indent=2, ensure_ascii=False)

    @classmethod
    def lugatdan(cls, d: dict) -> Sertifikat:
        try:
            if d.get("format") != CERT_FORMAT or d.get("version") != 1:
                raise SertifikatXatosi("sertifikat fayli emas (format/version)")
            s = cls(cert_id=bytes.fromhex(d["cert_id"]),
                    bank_public_key=bytes.fromhex(d["bank_public_key"]),
                    mint_public_key=bytes.fromhex(d["mint_public_key"]),
                    label=str(d["label"]),
                    limit_amount=int(d["limit_amount"]),
                    valid_from_ms=int(d["valid_from_ms"]),
                    valid_until_ms=int(d["valid_until_ms"]),
                    signature=bytes.fromhex(d["signature"]))
        except (KeyError, ValueError, TypeError) as e:
            if isinstance(e, SertifikatXatosi):
                raise
            raise SertifikatXatosi(f"sertifikat fayli buzilgan: {e}") from e
        if len(s.cert_id) != SERT_ID_UZ:
            raise SertifikatXatosi("cert_id 16 bayt bo'lishi kerak")
        if len(s.bank_public_key) != ML_DSA_PK_UZ or len(s.mint_public_key) != ML_DSA_PK_UZ:
            raise SertifikatXatosi("ochiq kalit 1952 bayt bo'lishi kerak")
        if len(s.signature) != ML_DSA_IMZO_UZ:
            raise SertifikatXatosi("imzo 3309 bayt bo'lishi kerak")
        return s

    @classmethod
    def oqi(cls, yol: Path) -> Sertifikat:
        try:
            d = json.loads(Path(yol).read_text(encoding="utf-8"))
        except (OSError, ValueError) as e:
            raise SertifikatXatosi(f"sertifikat o'qilmadi: {e}") from e
        return cls.lugatdan(d)

    def yoz(self, yol: Path) -> None:
        yol = Path(yol)
        tmp = yol.with_name(yol.name + ".tmp")
        tmp.write_text(self.json(), encoding="utf-8")
        os.replace(tmp, yol)


def sertifikat_yarat(bank_sk, bank_pk: bytes, mint_pk: bytes, cert_id: bytes, label: str,
                     limit: int, dan_ms: int, gacha_ms: int) -> Sertifikat:
    """Bank tomoni: sertifikatni imzolash. Zarbxonada faqat --selftest va testlar uchun."""
    s = Sertifikat(cert_id, bank_pk, mint_pk, label, limit, dan_ms, gacha_ms, b"")
    return Sertifikat(cert_id, bank_pk, mint_pk, label, limit, dan_ms, gacha_ms,
                      imzola(bank_sk, s.xabar()))
