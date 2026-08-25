"""
AETHER-Q v5.1 — KEM backend (Bosqich 1: REAL ML-KEM-768).

v5.0/mock'da `aether_q_v4.core.Mlkem768` SHA3-asosidagi SOXTA KEM edi. Bu modul
uni FIPS 203 ga mos REAL ML-KEM-768 bilan almashtiradi (PyCA `cryptography` >= 45,
OpenSSL-backed, constant-time C implementatsiya).

Interfeys mock bilan AYNAN bir xil (drop-in):
    keygen()      -> (pk: bytes, sk: bytes)
    encaps(pk)    -> (ct: bytes, ss: bytes)
    decaps(sk,ct) -> ss: bytes

Backend tanlash (env):  AETHER_KEM=real (default) | mock
    - real: production-darajali OpenSSL ML-KEM-768
    - mock: eski SHA3 surrogati (faqat oflayn/deterministik test uchun)

⚠ XAVFSIZLIK (AQ-08): `mock` backend SHIFRLASH BERMAYDI — u faqat
  deterministik test uchun. Uni tasodifan production'da yoqib qo'yish
  falokat bo'lardi, shu bois u FAIL-CLOSED: `AETHER_KEM=mock` yolg'iz
  o'zi XATO beradi. Uni yoqish uchun ATAYLAB ikkinchi tasdiq kerak:
      AETHER_KEM=mock  AETHER_ALLOW_INSECURE_MOCK_KEM=1
  Yoqilganda har safar stderr'ga baland ovozli ogohlantirish chiqadi.

O'lchamlar (FIPS 203, spec §2 ga mos):  PK=1184  CT=1088  SS=32  SK(seed)=64 B.
"""

import os

PK_LEN, CT_LEN, SS_LEN, SK_SEED_LEN = 1184, 1088, 32, 64


class RealMLKEM768:
    """FIPS 203 ML-KEM-768 (PyCA cryptography / OpenSSL)."""

    name = "ML-KEM-768 (FIPS 203, OpenSSL/pyca-cryptography)"
    real = True

    @staticmethod
    def keygen():
        from cryptography.hazmat.primitives.asymmetric import mlkem
        priv = mlkem.MLKEM768PrivateKey.generate()
        sk = priv.private_bytes_raw()                 # 64-baytli seed (d||z)
        pk = priv.public_key().public_bytes_raw()     # 1184 B
        return pk, sk

    @staticmethod
    def encaps(pk: bytes):
        from cryptography.hazmat.primitives.asymmetric import mlkem
        pub = mlkem.MLKEM768PublicKey.from_public_bytes(pk)
        ss, ct = pub.encapsulate()                    # cryptography: (shared_secret, ciphertext)
        return ct, ss                                 # AETHER interfeysi: (ct, ss)

    @staticmethod
    def load_sk(sk: bytes):
        """
        64-baytli seed'dan privat kalit OBYEKTINI quradi (qimmat: ~0.2 ms).
        Bir necha decaps uchun bir marta chaqirib, natijani qayta ishlating.
        """
        from cryptography.hazmat.primitives.asymmetric import mlkem
        return mlkem.MLKEM768PrivateKey.from_seed_bytes(bytes(sk))

    @staticmethod
    def decaps(sk, ct: bytes):
        """
        `sk` — 64-baytli seed YOKI `load_sk()` qaytargan obyekt (tez yo'l).
        Real decaps FIPS 203 implicit rejection'ni ICHIDA bajaradi (exception yo'q).
        """
        priv = MLKEM768.load_sk(sk) if isinstance(sk, (bytes, bytearray)) else sk
        return priv.decapsulate(ct)


class InsecureKEMConfiguration(RuntimeError):
    """Xavfsiz bo'lmagan (mock) KEM ATAYLAB tasdiqlanmasdan so'raldi."""


def _select_backend():
    choice = os.environ.get("AETHER_KEM", "real").lower()
    if choice != "mock":
        return RealMLKEM768

    # AQ-08: mock — SHIFRLASH BERMAYDI. Fail-closed: ikkinchi ATAYLAB
    # tasdiq bo'lmasa, ishga tushirishni to'xtatamiz. Aks holda production
    # serverida tasodifan `AETHER_KEM=mock` qolib ketsa, kanal ochiq bo'ladi.
    ack = os.environ.get("AETHER_ALLOW_INSECURE_MOCK_KEM", "").lower()
    if ack not in ("1", "true", "yes"):
        raise InsecureKEMConfiguration(
            "AETHER_KEM=mock so'raldi — bu SOXTA KEM, u HAQIQIY SHIFRLASH "
            "BERMAYDI va faqat deterministik test uchun.\n"
            "  Yoqish uchun ATAYLAB tasdiq kerak:\n"
            "      AETHER_ALLOW_INSECURE_MOCK_KEM=1  AETHER_KEM=mock\n"
            "  Production'da mock'ni HECH QACHON yoqmang.")

    # Yoqildi — lekin har safar baland ovozda ogohlantiramiz.
    import sys
    sys.stderr.write(
        "\n" + "!" * 68 + "\n"
        "!!  OGOHLANTIRISH: AETHER_KEM=mock YOQILGAN — SOXTA KEM ISHLAMOQDA  !!\n"
        "!!  Kanal HAQIQATAN shifrlanmaydi. Faqat test uchun. Production EMAS. !!\n"
        + "!" * 68 + "\n\n")
    sys.stderr.flush()
    from aether_q_v4.core import Mlkem768 as MockMLKEM768
    return MockMLKEM768


# Butun v5.1 paketi shu yagona nuqtadan KEM oladi.
MLKEM768 = _select_backend()
