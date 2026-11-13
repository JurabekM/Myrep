"""Gateway: asyncio QVL/1 server and hash-chained evidence ledger.

PQ calls run inline on the event loop on purpose: kyber-py / dilithium-py are
not thread safe (lesson 5), so no ``asyncio.to_thread``.
"""
from __future__ import annotations

import asyncio
import hashlib
import json
from collections import defaultdict
from pathlib import Path

from ..crypto import backend as pq
from ..edge.node import EVIDENCE_CTX, canonical, decode_alert
from ..protocol.handshake import DEFAULT_POLICY, GatewayHandshake, Identity
from ..protocol.resume import GatewayResume, TicketStore
from ..protocol.wire import FrameType, ProtocolError, encode_stream, read_frame, write_frame

GENESIS = "0" * 64


class EvidenceLedger:
    """Append-only JSONL ledger; ``hash_i = SHA256(prev_hash || canonical(record))``."""

    def __init__(self, path: str | Path) -> None:
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.head = GENESIS
        self.count = 0
        if self.path.exists():
            for entry in self.entries():
                self.head = entry["hash"]
                self.count += 1

    @staticmethod
    def link(prev: str, record: dict) -> str:
        return hashlib.sha256(prev.encode() + canonical(record)).hexdigest()

    def append(self, record: dict) -> str:
        h = self.link(self.head, record)
        with self.path.open("a") as fh:
            fh.write(json.dumps({"prev": self.head, "hash": h, "record": record}, sort_keys=True) + "\n")
        self.head = h
        self.count += 1
        return h

    def entries(self) -> list[dict]:
        if not self.path.exists():
            return []
        with self.path.open() as fh:
            return [json.loads(line) for line in fh if line.strip()]

    def verify_chain(self) -> bool:
        prev = GENESIS
        for e in self.entries():
            if e["prev"] != prev or self.link(prev, e["record"]) != e["hash"]:
                return False
            prev = e["hash"]
        return True


def verify_evidence(record: dict, node_pk: bytes) -> bool:
    """Third-party check of a ledger record: the node's signature over its evidence."""
    return pq.verify(node_pk, record["evidence"].encode(), bytes.fromhex(record["sig"]), EVIDENCE_CTX)


class Gateway:
    def __init__(self, identity: Identity, registry: dict[bytes, bytes], ledger: EvidenceLedger,
                 allowed=DEFAULT_POLICY) -> None:
        self.identity = identity
        self.registry = registry
        self.ledger = ledger
        self.tickets = TicketStore()
        self.hs = GatewayHandshake(identity, registry, allowed, self.tickets)
        self.resumer = GatewayResume(self.tickets, allowed)
        self.resumptions = 0
        self.summaries: dict[str, list[dict]] = defaultdict(list)
        self.alerts: list[dict] = []
        self.rejects: list[str] = []
        self.errors: list[str] = []
        self.rx_bytes: dict[str, int] = defaultdict(int)
        self.tx_bytes: dict[str, int] = defaultdict(int)
        self._server: asyncio.base_events.Server | None = None

    async def start(self, host: str = "127.0.0.1", port: int = 0) -> int:
        self._server = await asyncio.start_server(self._handle, host, port)
        return self._server.sockets[0].getsockname()[1]

    async def stop(self) -> None:
        if self._server:
            self._server.close()
            await self._server.wait_closed()

    def handle_alert(self, node_hex: str, payload: bytes) -> dict:
        evidence, sig = decode_alert(payload)
        pk = self.registry[bytes.fromhex(node_hex)]
        if not pq.verify(pk, evidence, sig, EVIDENCE_CTX):
            raise ProtocolError("bad evidence signature")
        ev = json.loads(evidence)
        if ev.get("node") != node_hex:
            raise ProtocolError("evidence node mismatch")
        record = {"node": node_hex, "evidence": evidence.decode(), "sig": sig.hex()}
        self.ledger.append(record)
        self.alerts.append(ev)
        return ev

    async def _handle(self, reader: asyncio.StreamReader, writer: asyncio.StreamWriter) -> None:
        node_hex = "?"
        try:
            hello = await read_frame(reader)
            if hello[1:2] == bytes([FrameType.RESUME]):
                res = self.resumer.respond(hello)
                self.resumptions += res.session is not None
            else:
                res = self.hs.respond(hello)
            await write_frame(writer, res.frame)
            if res.session is None:
                self.rejects.append(res.reason)
                return
            session = res.session
            node_hex = res.node_id.hex()
            self.rx_bytes[node_hex] += len(encode_stream(hello))
            self.tx_bytes[node_hex] += len(encode_stream(res.frame))
            while True:
                frame = await read_frame(reader)
                self.rx_bytes[node_hex] += len(encode_stream(frame))
                ftype, pt = session.open(frame)
                if ftype == FrameType.DATA:
                    self.summaries[node_hex].append(json.loads(pt))
                elif ftype == FrameType.ALERT:
                    self.handle_alert(node_hex, pt)
                elif ftype == FrameType.CLOSE:
                    return
        except (ProtocolError, ValueError, KeyError) as e:
            self.errors.append(f"{node_hex}: {e}")
        except asyncio.IncompleteReadError:
            pass
        finally:
            writer.close()
            try:
                await writer.wait_closed()
            except (ConnectionError, OSError):
                pass
