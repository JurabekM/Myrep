"""§9 — kalit ombori (`kalit.json`). Bank dasturi bilan bir xil format."""

from __future__ import annotations

import hashlib
import json
import os
import secrets
from pathlib import Path

from cryptography.exceptions import InvalidTag
from cryptography.hazmat.primitives.ciphers.aead import ChaCha20Poly1305

from .ibtido import kalit_urugdan, ochiq_kalit
from .konstanta import L_KEYSTORE_AAD, ML_DSA_PK_UZ

N_ISHLAB_CHIQARISH = 32768
MIN_PAROL = 8
_NOTOGRI = "parol noto'g'ri yoki fayl buzilgan"


class OmborXatosi(ValueError):
    pass


def _kdf(parol: str, salt: bytes, n: int, r: int, p: int) -> bytes:
    return hashlib.scrypt(parol.encode("utf-8"), salt=salt, n=n, r=r, p=p, dklen=32,
                          maxmem=256 * 2**20)


def ombor_lugat(sk_urug: bytes, parol: str, n: int = N_ISHLAB_CHIQARISH) -> dict:
    if len(parol) < MIN_PAROL:
        raise OmborXatosi(f"parol kamida {MIN_PAROL} belgi bo'lsin")
    salt, nonce = secrets.token_bytes(16), secrets.token_bytes(12)
    k = _kdf(parol, salt, n, 8, 1)
    ct = ChaCha20Poly1305(k).encrypt(nonce, sk_urug, L_KEYSTORE_AAD)
    pk = ochiq_kalit(kalit_urugdan(sk_urug))
    return {"version": 1,
            "kdf": {"name": "scrypt", "n": n, "r": 8, "p": 1, "salt": salt.hex()},
            "nonce": nonce.hex(), "ciphertext": ct.hex(), "public_key": pk.hex()}


def ombor_yarat(yol: Path, parol: str, n: int = N_ISHLAB_CHIQARISH,
                urug: bytes | None = None):
    """Yangi kalit yaratadi va atomik yozadi. Qaytaradi: maxfiy kalit obyekti."""
    yol = Path(yol)
    if yol.exists():
        raise OmborXatosi("kalit fayli allaqachon bor — ustiga yozilmaydi")
    urug = urug if urug is not None else secrets.token_bytes(32)
    d = ombor_lugat(urug, parol, n)
    yol.parent.mkdir(parents=True, exist_ok=True)
    tmp = yol.with_name(yol.name + ".tmp")
    tmp.write_text(json.dumps(d, indent=2), encoding="utf-8")
    os.replace(tmp, yol)
    return kalit_urugdan(urug)


def _oqi(yol: Path) -> dict:
    try:
        return json.loads(Path(yol).read_text(encoding="utf-8"))
    except (OSError, ValueError) as e:
        raise OmborXatosi(_NOTOGRI) from e


def ombor_ochiq_kalit(yol: Path) -> bytes:
    """Parolsiz: kirish ekranida kalit izini ko'rsatish uchun."""
    try:
        pk = bytes.fromhex(_oqi(yol)["public_key"])
    except (KeyError, ValueError, TypeError) as e:
        raise OmborXatosi("kalit fayli buzilgan") from e
    if len(pk) != ML_DSA_PK_UZ:
        raise OmborXatosi("kalit fayli buzilgan")
    return pk


def ombor_lugatdan_och(d: dict, parol: str) -> bytes:
    """Urug'ni qaytaradi."""
    try:
        kd = d["kdf"]
        if d.get("version") != 1 or kd.get("name") != "scrypt":
            raise OmborXatosi("kalit fayli formati noma'lum")
        k = _kdf(parol, bytes.fromhex(kd["salt"]), int(kd["n"]), int(kd["r"]), int(kd["p"]))
        urug = ChaCha20Poly1305(k).decrypt(bytes.fromhex(d["nonce"]),
                                           bytes.fromhex(d["ciphertext"]), L_KEYSTORE_AAD)
    except OmborXatosi:
        raise
    except (KeyError, ValueError, TypeError, InvalidTag) as e:
        raise OmborXatosi(_NOTOGRI) from e
    if ochiq_kalit(kalit_urugdan(urug)).hex() != d.get("public_key"):
        raise OmborXatosi("ombordagi ochiq kalit urug'ga mos emas")
    return urug


def ombor_urug(yol: Path, parol: str) -> bytes:
    """32 baytli urug' — FAQAT kalitni Pico'ga ko'chirish (KALIT_IMPORT) uchun."""
    return ombor_lugatdan_och(_oqi(yol), parol)


def ombor_och(yol: Path, parol: str):
    """Maxfiy kalit obyekti."""
    return kalit_urugdan(ombor_lugatdan_och(_oqi(yol), parol))


def _atomik_yoz(yol: Path, matn: str) -> None:
    yol = Path(yol)
    tmp = yol.with_name(yol.name + ".tmp")
    tmp.write_text(matn, encoding="utf-8")
    os.replace(tmp, yol)


def parol_almashtir(yol: Path, eski: str, yangi: str) -> None:
    """Urug' o'zgarmaydi (kalit va izi o'sha), faqat shifrlovchi parol. scrypt `n`
    fayldagidan kichraymaydi. Eski parol noto'g'ri bo'lsa fayl o'zgarmaydi."""
    d = _oqi(yol)
    urug = ombor_lugatdan_och(d, eski)
    if len(yangi) < MIN_PAROL:
        raise OmborXatosi(f"yangi parol kamida {MIN_PAROL} belgi bo'lsin")
    if yangi == eski:
        raise OmborXatosi("yangi parol eskisi bilan bir xil")
    n = max(int(d["kdf"]["n"]), N_ISHLAB_CHIQARISH)
    _atomik_yoz(yol, json.dumps(ombor_lugat(urug, yangi, n), indent=2))


def ombor_zaxira(yol: Path, manzil: Path) -> bytes:
    """Shifrlangan kalit faylining zaxira nusxasi (o'sha parol bilan ochiladi).
    Qaytaradi: ochiq kalit — izni ko'rsatish uchun."""
    pk = ombor_ochiq_kalit(yol)
    manzil = Path(manzil)
    if manzil.resolve() == Path(yol).resolve():
        raise OmborXatosi("zaxira kalit faylining o'zi bo'lishi mumkin emas")
    _atomik_yoz(manzil, Path(yol).read_text(encoding="utf-8"))
    if ombor_ochiq_kalit(manzil) != pk:
        raise OmborXatosi("zaxira yozilishi tekshiruvdan o'tmadi")
    return pk


def ombor_tikla(zaxira: Path, yol: Path, parol: str):
    """Zaxiradan profilga. Avval parol bilan OCHIB tekshiriladi; mavjud kalit ustiga
    yozilmaydi. Qaytaradi: maxfiy kalit obyekti."""
    yol = Path(yol)
    if yol.exists():
        raise OmborXatosi("profilda kalit allaqachon bor — ustiga yozilmaydi")
    d = _oqi(zaxira)
    urug = ombor_lugatdan_och(d, parol)
    yol.parent.mkdir(parents=True, exist_ok=True)
    _atomik_yoz(yol, json.dumps(d, indent=2))
    return kalit_urugdan(urug)
