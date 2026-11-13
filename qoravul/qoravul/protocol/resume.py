"""QVL/1 PSK resumption (psk_dhe style, single-use tickets).

After a full handshake both sides derive a resumption ticket:
    rms       = HKDF-SHA384(ikm, salt=TH, info="QVL/1 resumption", L=32)
    ticket_id = HKDF-SHA384(ikm, salt=TH, info="QVL/1 ticket id", L=16)
where ikm/TH are the handshake's input keying material and transcript hash.
No extra message is needed: the gateway stores (ticket_id -> rms, node, suite).

RESUME  = [ticket_id(16), Nn(32), X25519_pub(32)] + MAC_rms("QVL1-RESUME"  || fields)
RESUMED = [Ng(32), X25519_pub(32)]                + MAC_rms("QVL1-RESUMED" || SHA384(RESUME) || fields)
TH'  = SHA384(RESUME || RESUMED)
OKM  = HKDF-SHA384(rms || ss_x, salt=TH', info="QVL/1 resumed traffic keys", L=72)

* Tickets are single use (consumed after the MAC verifies) -> a replayed RESUME is rejected.
* A ticket remembers the suite of the session that minted it; if that suite is
  no longer allowed the resume is refused ("suite below policy"), so resumption
  can never be used to climb down from the current policy.
* The fresh X25519 exchange gives forward secrecy against a later ticket leak;
  post-quantum strength comes from rms (rooted in the hybrid handshake).
* Every resumed session mints the next ticket from its own transcript.
"""
from __future__ import annotations

import hashlib
import hmac
import os
import time
from dataclasses import dataclass

from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.asymmetric.x25519 import X25519PrivateKey, X25519PublicKey
from cryptography.hazmat.primitives.kdf.hkdf import HKDF

from .session import Session
from .wire import FrameType, ProtocolError, Suite, make_frame, pack_fields, parse_frame, reject_frame, unpack_fields

RESUME_LABEL = b"QVL1-RESUME"
RESUMED_LABEL = b"QVL1-RESUMED"
RESUMED_KDF_INFO = b"QVL/1 resumed traffic keys"
TICKET_LIFETIME = 7 * 24 * 3600  # seconds
MAC_LEN = 32


def _hkdf(ikm: bytes, salt: bytes, info: bytes, n: int) -> bytes:
    return HKDF(algorithm=hashes.SHA384(), length=n, salt=salt, info=info).derive(ikm)


def _mac(key: bytes, msg: bytes) -> bytes:
    return hmac.new(key, msg, hashlib.sha384).digest()[:MAC_LEN]


def _x_pub(priv: X25519PrivateKey) -> bytes:
    from cryptography.hazmat.primitives import serialization

    return priv.public_key().public_bytes(serialization.Encoding.Raw, serialization.PublicFormat.Raw)


@dataclass
class Ticket:
    ticket_id: bytes
    secret: bytes
    suite: Suite
    node_id: bytes
    issued: float

    @classmethod
    def derive(cls, ikm: bytes, th: bytes, suite: Suite, node_id: bytes, now: float | None = None) -> "Ticket":
        return cls(_hkdf(ikm, th, b"QVL/1 ticket id", 16), _hkdf(ikm, th, b"QVL/1 resumption", 32), Suite(suite),
                   node_id, time.time() if now is None else now)


class TicketStore:
    """Gateway-side single-use ticket store."""

    def __init__(self, lifetime: float = TICKET_LIFETIME) -> None:
        self.lifetime = lifetime
        self._t: dict[bytes, Ticket] = {}

    def put(self, t: Ticket) -> None:
        self._t[t.ticket_id] = t

    def peek(self, ticket_id: bytes) -> Ticket | None:
        return self._t.get(ticket_id)

    def consume(self, ticket_id: bytes) -> None:
        self._t.pop(ticket_id, None)

    def __len__(self) -> int:
        return len(self._t)


def _session_keys(rms: bytes, ss_x: bytes, th: bytes) -> tuple[bytes, bytes, bytes]:
    okm = _hkdf(rms + ss_x, th, RESUMED_KDF_INFO, 72)
    return okm[0:32], okm[32:64], okm[64:72]


class NodeResume:
    def __init__(self, ticket: Ticket) -> None:
        self.ticket = ticket
        self._x = X25519PrivateKey.generate()
        self.resume_frame: bytes | None = None

    def hello(self) -> bytes:
        fields = [self.ticket.ticket_id, os.urandom(32), _x_pub(self._x)]
        mac = _mac(self.ticket.secret, RESUME_LABEL + pack_fields(fields))
        self.resume_frame = make_frame(FrameType.RESUME, pack_fields(fields + [mac]))
        return self.resume_frame

    def finish(self, frame: bytes) -> Session:
        if self.resume_frame is None:
            raise ProtocolError("resume not sent")
        ftype, body = parse_frame(frame)
        if ftype == FrameType.REJECT:
            raise ProtocolError("rejected: " + unpack_fields(body, 1)[0].decode(errors="replace"))
        if ftype != FrameType.RESUMED:
            raise ProtocolError("expected RESUMED")
        ng, x_pub, mac = unpack_fields(body, 3)
        if len(ng) != 32 or len(x_pub) != 32:
            raise ProtocolError("malformed resumed")
        want = _mac(self.ticket.secret, RESUMED_LABEL + hashlib.sha384(self.resume_frame).digest()
                    + pack_fields([ng, x_pub]))
        if not hmac.compare_digest(mac, want):
            raise ProtocolError("gateway resume mac invalid")
        ss_x = self._x.exchange(X25519PublicKey.from_public_bytes(x_pub))
        th = hashlib.sha384(self.resume_frame + frame).digest()
        k_up, k_down, sid = _session_keys(self.ticket.secret, ss_x, th)
        s = Session("node", k_up, k_down, sid)
        s.ticket = Ticket.derive(self.ticket.secret + ss_x, th, self.ticket.suite, self.ticket.node_id)
        return s


class GatewayResume:
    def __init__(self, store: TicketStore, allowed) -> None:
        self.store = store
        self.allowed = frozenset(Suite(s) for s in allowed)

    def respond(self, frame: bytes, now: float | None = None):
        from .handshake import HandshakeResult

        try:
            return self._respond(frame, time.time() if now is None else now)
        except ProtocolError as e:
            return HandshakeResult(reject_frame(str(e)), None, None, str(e))

    def _respond(self, frame: bytes, now: float):
        from .handshake import HandshakeResult

        ftype, body = parse_frame(frame)
        if ftype != FrameType.RESUME:
            raise ProtocolError("expected RESUME")
        tid, nn, x_pub, mac = unpack_fields(body, 4)
        if len(tid) != 16 or len(nn) != 32 or len(x_pub) != 32:
            raise ProtocolError("malformed resume")
        t = self.store.peek(tid)
        if t is None:
            raise ProtocolError("unknown ticket")
        if not hmac.compare_digest(mac, _mac(t.secret, RESUME_LABEL + pack_fields([tid, nn, x_pub]))):
            raise ProtocolError("bad resume mac")
        self.store.consume(tid)  # single use, only after the MAC proved possession
        if now - t.issued > self.store.lifetime:
            raise ProtocolError("ticket expired")
        if t.suite not in self.allowed:
            raise ProtocolError("suite below policy")
        priv = X25519PrivateKey.generate()
        fields = [os.urandom(32), _x_pub(priv)]
        rmac = _mac(t.secret, RESUMED_LABEL + hashlib.sha384(frame).digest() + pack_fields(fields))
        resumed = make_frame(FrameType.RESUMED, pack_fields(fields + [rmac]))
        ss_x = priv.exchange(X25519PublicKey.from_public_bytes(x_pub))
        th = hashlib.sha384(frame + resumed).digest()
        k_up, k_down, sid = _session_keys(t.secret, ss_x, th)
        s = Session("gateway", k_up, k_down, sid, t.node_id)
        s.ticket = Ticket.derive(t.secret + ss_x, th, t.suite, t.node_id, now)
        self.store.put(s.ticket)
        return HandshakeResult(resumed, s, t.node_id)
