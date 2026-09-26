"""QVL/1 1-RTT authenticated key exchange (node initiates).

HELLO  = [suite, node_id(16), Nn(32), x25519_pub|"", mlkem_ek|""] + SIG_node
         SIG_node over "QVL1-HELLO" || pack_fields(fields)
ACCEPT = [Ng(32), x25519_pub|"", mlkem_ct|""] + SIG_gw
         SIG_gw over "QVL1-ACCEPT" || SHA384(HELLO) || pack_fields(fields)
TH     = SHA384(HELLO || ACCEPT)
OKM    = HKDF-SHA384(ss_x || ss_kem, salt=TH, info="QVL/1 traffic keys", L=72)
"""
from __future__ import annotations

import hashlib
import os
from dataclasses import dataclass, field

from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric.x25519 import X25519PrivateKey, X25519PublicKey
from cryptography.hazmat.primitives.kdf.hkdf import HKDF

from ..crypto import backend as pq
from .session import Session
from .wire import FrameType, ProtocolError, Suite, make_frame, pack_fields, parse_frame, reject_frame, unpack_fields

HELLO_LABEL = b"QVL1-HELLO"
ACCEPT_LABEL = b"QVL1-ACCEPT"
KDF_INFO = b"QVL/1 traffic keys"
NODE_ID_LEN = 16
NONCE_LEN = 32
X25519_LEN = 32
MLKEM_EK_LEN = 1184
MLKEM_CT_LEN = 1088
DEFAULT_POLICY = frozenset({Suite.HYBRID})


@dataclass
class Identity:
    """Long-term ML-DSA-65 identity."""

    node_id: bytes
    pk: bytes
    sk: bytes = field(repr=False)

    @classmethod
    def generate(cls, node_id: bytes | None = None) -> "Identity":
        pk, sk = pq.sig_keygen()
        return cls(node_id or os.urandom(NODE_ID_LEN), pk, sk)

    def sign(self, msg: bytes, ctx: bytes = b"") -> bytes:
        return pq.sign(self.sk, msg, ctx)


def _x_pub(priv: X25519PrivateKey) -> bytes:
    return priv.public_key().public_bytes(serialization.Encoding.Raw, serialization.PublicFormat.Raw)


def derive_keys(ss_x: bytes, ss_kem: bytes, th: bytes) -> tuple[bytes, bytes, bytes]:
    okm = HKDF(algorithm=hashes.SHA384(), length=72, salt=th, info=KDF_INFO).derive(ss_x + ss_kem)
    return okm[0:32], okm[32:64], okm[64:72]


def _check_len(val: bytes, want: int, used: bool, what: str) -> None:
    if used and len(val) != want:
        raise ProtocolError(f"bad {what} length")
    if not used and val:
        raise ProtocolError(f"unexpected {what}")


class NodeHandshake:
    """Initiator. Pins the gateway's ML-DSA public key."""

    def __init__(self, identity: Identity, gateway_pk: bytes, suite: Suite = Suite.HYBRID) -> None:
        self.identity = identity
        self.gateway_pk = gateway_pk
        self.suite = Suite(suite)
        self._x_priv: X25519PrivateKey | None = None
        self._dk: bytes | None = None
        self.hello_frame: bytes | None = None

    def hello(self) -> bytes:
        x_pub = ek = b""
        if self.suite.uses_x25519:
            self._x_priv = X25519PrivateKey.generate()
            x_pub = _x_pub(self._x_priv)
        if self.suite.uses_kem:
            ek, self._dk = pq.kem_keygen()
        fields = [bytes([self.suite]), self.identity.node_id, os.urandom(NONCE_LEN), x_pub, ek]
        sig = self.identity.sign(HELLO_LABEL + pack_fields(fields))
        self.hello_frame = make_frame(FrameType.HELLO, pack_fields(fields + [sig]))
        return self.hello_frame

    def finish(self, frame: bytes) -> Session:
        if self.hello_frame is None:
            raise ProtocolError("hello not sent")
        ftype, body = parse_frame(frame)
        if ftype == FrameType.REJECT:
            reason = unpack_fields(body, 1)[0].decode(errors="replace")
            raise ProtocolError(f"rejected: {reason}")
        if ftype != FrameType.ACCEPT:
            raise ProtocolError("expected ACCEPT")
        ng, x_pub, ct, sig = unpack_fields(body, 4)
        if len(ng) != NONCE_LEN:
            raise ProtocolError("bad nonce length")
        _check_len(x_pub, X25519_LEN, self.suite.uses_x25519, "x25519 key")
        _check_len(ct, MLKEM_CT_LEN, self.suite.uses_kem, "ML-KEM ciphertext")
        signed = ACCEPT_LABEL + hashlib.sha384(self.hello_frame).digest() + pack_fields([ng, x_pub, ct])
        if not pq.verify(self.gateway_pk, signed, sig):
            raise ProtocolError("gateway signature invalid")
        ss_x = self._x_priv.exchange(X25519PublicKey.from_public_bytes(x_pub)) if self.suite.uses_x25519 else b""
        ss_kem = pq.kem_decaps(self._dk, ct) if self.suite.uses_kem else b""
        th = hashlib.sha384(self.hello_frame + frame).digest()
        k_up, k_down, sid = derive_keys(ss_x, ss_kem, th)
        self._x_priv = self._dk = None
        return Session("node", k_up, k_down, sid)


@dataclass
class HandshakeResult:
    frame: bytes  # ACCEPT or REJECT to send back
    session: Session | None
    node_id: bytes | None
    reason: str = ""


class GatewayHandshake:
    """Responder. ``registry`` maps node_id -> node ML-DSA public key."""

    def __init__(self, identity: Identity, registry: dict[bytes, bytes], allowed=DEFAULT_POLICY) -> None:
        self.identity = identity
        self.registry = registry
        self.allowed = frozenset(Suite(s) for s in allowed)

    def respond(self, hello: bytes) -> HandshakeResult:
        try:
            return self._respond(hello)
        except ProtocolError as e:
            reason = str(e)
            return HandshakeResult(reject_frame(reason), None, None, reason)

    def _respond(self, hello: bytes) -> HandshakeResult:
        ftype, body = parse_frame(hello)
        if ftype != FrameType.HELLO:
            raise ProtocolError("expected HELLO")
        suite_b, node_id, nn, x_pub, ek, sig = unpack_fields(body, 6)
        if len(node_id) != NODE_ID_LEN or len(nn) != NONCE_LEN or len(suite_b) != 1:
            raise ProtocolError("malformed hello")
        pk = self.registry.get(node_id)
        if pk is None:
            raise ProtocolError("unknown node")
        # Signature first: a flipped suite byte must surface as "bad signature".
        if not pq.verify(pk, HELLO_LABEL + pack_fields([suite_b, node_id, nn, x_pub, ek]), sig):
            raise ProtocolError("bad signature")
        try:
            suite = Suite(suite_b[0])
        except ValueError as e:
            raise ProtocolError("unknown suite") from e
        if suite not in self.allowed:
            raise ProtocolError("suite below policy")
        _check_len(x_pub, X25519_LEN, suite.uses_x25519, "x25519 key")
        _check_len(ek, MLKEM_EK_LEN, suite.uses_kem, "ML-KEM key")

        ss_x = ss_kem = my_x = ct = b""
        if suite.uses_x25519:
            priv = X25519PrivateKey.generate()
            my_x = _x_pub(priv)
            ss_x = priv.exchange(X25519PublicKey.from_public_bytes(x_pub))
        if suite.uses_kem:
            try:
                ss_kem, ct = pq.kem_encaps(ek)
            except Exception as e:  # malformed ek (modulus check) etc.
                raise ProtocolError("bad ML-KEM key") from e
        fields = [os.urandom(NONCE_LEN), my_x, ct]
        gsig = self.identity.sign(ACCEPT_LABEL + hashlib.sha384(hello).digest() + pack_fields(fields))
        accept = make_frame(FrameType.ACCEPT, pack_fields(fields + [gsig]))
        th = hashlib.sha384(hello + accept).digest()
        k_up, k_down, sid = derive_keys(ss_x, ss_kem, th)
        return HandshakeResult(accept, Session("gateway", k_up, k_down, sid, node_id), node_id)
