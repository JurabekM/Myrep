"""Post-quantum primitive abstraction.

Default backend is pure Python (kyber-py ML-KEM-768 / FIPS 203 and
dilithium-py ML-DSA-65 / FIPS 204). These implementations are NOT constant
time and NOT thread safe, so every call is serialised through an RLock.

liboqs is opt-in only (``QORAVUL_PQ_BACKEND=liboqs``): ``import oqs`` can try
to build liboqs from source and hang, so it is never imported implicitly.
"""
from __future__ import annotations

import os
import threading

KEM_NAME = "ML-KEM-768"
SIG_NAME = "ML-DSA-65"


class PQBackend:
    """Interface: kem_keygen/encaps/decaps and sig_keygen/sign/verify."""

    name = "abstract"

    def kem_keygen(self) -> tuple[bytes, bytes]:  # (ek, dk)
        raise NotImplementedError

    def kem_encaps(self, ek: bytes) -> tuple[bytes, bytes]:  # (ss, ct)
        raise NotImplementedError

    def kem_decaps(self, dk: bytes, ct: bytes) -> bytes:
        raise NotImplementedError

    def sig_keygen(self) -> tuple[bytes, bytes]:  # (pk, sk)
        raise NotImplementedError

    def sign(self, sk: bytes, msg: bytes, ctx: bytes = b"") -> bytes:
        raise NotImplementedError

    def verify(self, pk: bytes, msg: bytes, sig: bytes, ctx: bytes = b"") -> bool:
        raise NotImplementedError


class PurePythonBackend(PQBackend):
    """kyber-py + dilithium-py, every method guarded by a process-wide RLock."""

    name = "pure-python"
    _lock = threading.RLock()

    def __init__(self) -> None:
        from dilithium_py.ml_dsa import ML_DSA_65
        from kyber_py.ml_kem import ML_KEM_768

        self._kem = ML_KEM_768
        self._sig = ML_DSA_65

    def kem_keygen(self):
        with self._lock:
            return self._kem.keygen()

    def kem_encaps(self, ek):
        with self._lock:
            ss, ct = self._kem.encaps(ek)
            return ss, ct

    def kem_decaps(self, dk, ct):
        with self._lock:
            return self._kem.decaps(dk, ct)

    def sig_keygen(self):
        with self._lock:
            return self._sig.keygen()

    def sign(self, sk, msg, ctx=b""):
        with self._lock:
            return self._sig.sign(sk, msg, ctx=ctx)

    def verify(self, pk, msg, sig, ctx=b""):
        with self._lock:
            try:
                return bool(self._sig.verify(pk, msg, sig, ctx=ctx))
            except Exception:
                return False


class LiboqsBackend(PQBackend):  # pragma: no cover - opt-in, not in default CI
    """liboqs-python backend. ML-DSA context strings need liboqs >= 0.12."""

    name = "liboqs"
    _lock = threading.RLock()

    def __init__(self) -> None:
        import oqs  # noqa: only reached when explicitly requested

        self._oqs = oqs

    def kem_keygen(self):
        with self._lock, self._oqs.KeyEncapsulation(KEM_NAME) as k:
            ek = k.generate_keypair()
            return ek, k.export_secret_key()

    def kem_encaps(self, ek):
        with self._lock, self._oqs.KeyEncapsulation(KEM_NAME) as k:
            ct, ss = k.encap_secret(ek)
            return ss, ct

    def kem_decaps(self, dk, ct):
        with self._lock, self._oqs.KeyEncapsulation(KEM_NAME, secret_key=dk) as k:
            return k.decap_secret(ct)

    def sig_keygen(self):
        with self._lock, self._oqs.Signature(SIG_NAME) as s:
            pk = s.generate_keypair()
            return pk, s.export_secret_key()

    def sign(self, sk, msg, ctx=b""):
        with self._lock, self._oqs.Signature(SIG_NAME, secret_key=sk) as s:
            return s.sign_with_ctx_str(msg, ctx) if ctx else s.sign(msg)

    def verify(self, pk, msg, sig, ctx=b""):
        with self._lock, self._oqs.Signature(SIG_NAME) as s:
            try:
                if ctx:
                    return bool(s.verify_with_ctx_str(msg, sig, ctx, pk))
                return bool(s.verify(msg, sig, pk))
            except Exception:
                return False


_backend: PQBackend | None = None
_backend_lock = threading.Lock()


def get_backend() -> PQBackend:
    """Return the process-wide backend selected by QORAVUL_PQ_BACKEND."""
    global _backend
    with _backend_lock:
        if _backend is None:
            choice = os.environ.get("QORAVUL_PQ_BACKEND", "pure").lower()
            _backend = LiboqsBackend() if choice == "liboqs" else PurePythonBackend()
        return _backend


def kem_keygen():
    return get_backend().kem_keygen()


def kem_encaps(ek):
    return get_backend().kem_encaps(ek)


def kem_decaps(dk, ct):
    return get_backend().kem_decaps(dk, ct)


def sig_keygen():
    return get_backend().sig_keygen()


def sign(sk, msg, ctx=b""):
    return get_backend().sign(sk, msg, ctx)


def verify(pk, msg, sig, ctx=b""):
    return get_backend().verify(pk, msg, sig, ctx)
