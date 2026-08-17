"""Spec §9: ishonchsiz server.

Server ATAYLAB "halol emas" qilib yozilgan — u paketni ushlab qolishi,
takrorlashi, o'zgartirishi va bundle maydonlarini almashtira olishi kerak.
Aynan shu qobiliyatlar hujum laboratoriyasining asosi.
"""
from __future__ import annotations

import time
from collections import defaultdict, deque
from dataclasses import dataclass, field
from typing import Optional

from ..config import ProtocolConfig
from ..protocol.envelope import Envelope
from ..protocol.sfile import EncryptedChunk
from .trace import Level, Trace


@dataclass
class StoredBlob:
    file_id: bytes
    chunks: dict[int, bytes]
    manifest_ct: Optional[bytes] = None
    uploaded_at: float = field(default_factory=time.time)


class UntrustedServer:
    """Spec §9 dagi minimal server + hujum uchun qo'shimcha imkoniyatlar."""

    def __init__(self, cfg: ProtocolConfig, trace: Optional[Trace] = None) -> None:
        self.cfg = cfg
        self.trace = trace or Trace()
        self.bundles: dict[bytes, dict] = {}
        self.queues: dict[bytes, deque[bytes]] = defaultdict(deque)
        self.blobs: dict[bytes, StoredBlob] = {}
        self.captured: list[tuple[float, bytes, bytes]] = []   # (ts, rcv, wire)
        self.metadata_log: list[dict] = []
        self.delivered = 0
        self.dropped = 0

        # --- hujum bayroqlari ---
        self.capture_all = True
        self.drop_next: set[bytes] = set()

    # ------------------------------------------------------------------
    # Pre-key store (spec §9)
    # ------------------------------------------------------------------
    def publish_bundle(self, device_id: bytes, bundle: dict) -> None:
        self.bundles[device_id] = bundle
        self.trace.emit("server", Level.INFO,
                        f"bundle e'lon qilindi: {device_id.hex()[:8]}")

    def fetch_bundle(self, device_id: bytes) -> dict:
        b = self.bundles.get(device_id)
        if b is None:
            raise KeyError("bundle topilmadi")
        return dict(b)

    # ------------------------------------------------------------------
    # Envelope navbati
    # ------------------------------------------------------------------
    def enqueue(self, env: Envelope) -> bytes:
        wire = env.to_wire(self.cfg)
        rcv = env.recipient_device_id or b""
        # Server FAQAT shuni ko'radi — metama'lumot oqishini o'lchash uchun:
        self.metadata_log.append(
            {
                "ts": env.timestamp,
                "type": env.type,
                "snd": env.sender_device_id.hex()[:8],
                "rcv": rcv.hex()[:8] if rcv else "-",
                "sid": env.session_id.hex()[:8] if env.session_id else "-",
                "no": env.message_no,
                "bytes": len(wire),
            }
        )
        if self.capture_all:
            self.captured.append((time.time(), rcv, wire))
        if rcv in self.drop_next:
            self.drop_next.discard(rcv)
            self.dropped += 1
            self.trace.emit("server", Level.ATTACK, "paket TASHLAB YUBORILDI")
            return wire
        self.queues[rcv].append(wire)
        self.trace.emit("server", Level.WIRE,
                        f"{env.type} navbatga qo'yildi ({len(wire)} bayt)")
        return wire

    def deliver(self, device_id: bytes) -> Optional[bytes]:
        q = self.queues[device_id]
        if not q:
            return None
        self.delivered += 1
        return q.popleft()

    def deliver_all(self, device_id: bytes) -> list[bytes]:
        out = []
        while True:
            w = self.deliver(device_id)
            if w is None:
                return out
            out.append(w)

    def pending(self, device_id: bytes) -> int:
        return len(self.queues[device_id])

    # ------------------------------------------------------------------
    # Blob store (S-FILE)
    # ------------------------------------------------------------------
    def upload(self, file_id: bytes, chunks: list[EncryptedChunk]) -> None:
        self.blobs[file_id] = StoredBlob(
            file_id=file_id, chunks={c.index: c.ciphertext for c in chunks}
        )
        total = sum(len(c.ciphertext) for c in chunks)
        self.trace.emit("server", Level.INFO,
                        f"fayl yuklandi: {len(chunks)} bo'lak, {total} bayt (ciphertext)")

    def download(self, file_id: bytes) -> list[EncryptedChunk]:
        blob = self.blobs[file_id]
        return [EncryptedChunk(i, blob.chunks[i], b"") for i in sorted(blob.chunks)]

    # ------------------------------------------------------------------
    # Hujum operatsiyalari (server yovuz bo'lganda)
    # ------------------------------------------------------------------
    def tamper_chunk(self, file_id: bytes, index: int, mutate: bytes) -> None:
        blob = self.blobs[file_id]
        ct = bytearray(blob.chunks[index])
        for i, b in enumerate(mutate):
            ct[i % len(ct)] ^= b
        blob.chunks[index] = bytes(ct)
        self.trace.emit("server", Level.ATTACK, f"bo'lak {index} o'zgartirildi")

    def truncate_file(self, file_id: bytes, keep: int) -> None:
        blob = self.blobs[file_id]
        blob.chunks = {i: c for i, c in blob.chunks.items() if i < keep}
        self.trace.emit("server", Level.ATTACK, f"fayl {keep} bo'lakka qisqartirildi")

    def replay_last(self, recipient: bytes) -> Optional[bytes]:
        for _ts, rcv, wire in reversed(self.captured):
            if rcv == recipient:
                self.queues[recipient].append(wire)
                self.trace.emit("server", Level.ATTACK, "oxirgi paket QAYTA yuborildi")
                return wire
        return None

    def stats(self) -> dict:
        return {
            "bundles": len(self.bundles),
            "queued": sum(len(q) for q in self.queues.values()),
            "delivered": self.delivered,
            "dropped": self.dropped,
            "captured": len(self.captured),
            "blobs": len(self.blobs),
            "blob_bytes": sum(
                sum(len(c) for c in b.chunks.values()) for b in self.blobs.values()
            ),
        }
