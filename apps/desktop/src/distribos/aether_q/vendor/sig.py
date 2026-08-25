"""
AETHER-Q v5.1 — Post-Kvant Raqamli Imzo (ML-DSA-65, FIPS 204).

Handshake server autentifikatsiyasi uchun (Kuchaytirish). Backend: PyCA
`cryptography` (OpenSSL, constant-time). O'lchamlar (spec §2): PK=1952 B, Sig=3309 B.

Interfeys:
    keygen()          -> (pk_bytes, priv_obj)
    sign(priv, msg)   -> sig_bytes
    verify(pk, sig, msg) -> bool
"""

MLDSA_PK_LEN, MLDSA_SIG_LEN = 1952, 3309


class MLDSA65:
    """FIPS 204 ML-DSA-65 (PyCA cryptography / OpenSSL)."""

    name = "ML-DSA-65 (FIPS 204, OpenSSL/pyca-cryptography)"

    @staticmethod
    def keygen():
        from cryptography.hazmat.primitives.asymmetric import mldsa
        priv = mldsa.MLDSA65PrivateKey.generate()
        pk = priv.public_key().public_bytes_raw()      # 1952 B
        return pk, priv

    @staticmethod
    def sign(priv, msg: bytes) -> bytes:
        return priv.sign(msg)                          # 3309 B

    @staticmethod
    def verify(pk: bytes, sig: bytes, msg: bytes) -> bool:
        from cryptography.hazmat.primitives.asymmetric import mldsa
        try:
            mldsa.MLDSA65PublicKey.from_public_bytes(pk).verify(sig, msg)
            return True
        except Exception:
            return False
