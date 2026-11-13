"""Edge node: on-device detector, incident FSM and QVL/1 client."""
from __future__ import annotations

import asyncio
import json
import struct
from collections import deque
from dataclasses import dataclass, field

import numpy as np

from ..crypto import backend as pq
from ..protocol.handshake import Identity, NodeHandshake
from ..protocol.resume import NodeResume
from ..protocol.session import RECORD_OVERHEAD, Session
from ..protocol.wire import FrameType, ProtocolError, Suite, encode_stream, read_frame, write_frame
from ..tinyml.meter import FEATURES, VirtualMeter
from ..tinyml.model import QuantAE

EVIDENCE_CTX = b"QVL1-EVIDENCE"
DEBOUNCE_WINDOW, DEBOUNCE_HITS = 6, 4  # lesson 4: 4 of the last 6 windows
CLEAR_AFTER = 30  # consecutive clean windows that close an incident
SUMMARY_EVERY = 15  # windows per DATA summary


def canonical(obj) -> bytes:
    return json.dumps(obj, sort_keys=True, separators=(",", ":")).encode()


def encode_alert(evidence: bytes, sig: bytes) -> bytes:
    """ALERT payload: u16 len || canonical evidence JSON || raw ML-DSA-65 signature."""
    return struct.pack(">H", len(evidence)) + evidence + sig


def decode_alert(payload: bytes) -> tuple[bytes, bytes]:
    if len(payload) < 2:
        raise ProtocolError("short alert")
    (n,) = struct.unpack(">H", payload[:2])
    if 2 + n > len(payload):
        raise ProtocolError("truncated alert")
    return payload[2 : 2 + n], payload[2 + n :]


def raw_record(minute: int, raw: dict) -> bytes:
    """What a non-edge meter would stream every minute (bandwidth baseline)."""
    return canonical({"t": minute, "v": round(raw["V"], 2), "i": round(raw["I"], 3), "in": round(raw["I_n"], 3),
                      "pf": round(raw["pf"], 3), "thd": round(raw["thd"], 4), "f": round(raw["f"], 3)})


@dataclass
class IncidentFSM:
    """NORMAL -> INCIDENT when >= 4 of the last 6 windows are anomalous (one ALERT);
    INCIDENT -> NORMAL after 30 consecutive clean windows."""

    history: deque = field(default_factory=lambda: deque(maxlen=DEBOUNCE_WINDOW))
    active: bool = False
    clean: int = 0

    def step(self, anomalous: bool) -> str | None:
        self.history.append(bool(anomalous))
        if not self.active:
            if sum(self.history) >= DEBOUNCE_HITS:
                self.active, self.clean = True, 0
                return "open"
            return None
        self.clean = 0 if anomalous else self.clean + 1
        if self.clean >= CLEAR_AFTER:
            self.active = False
            self.history.clear()
            return "close"
        return None


class EdgeNode:
    """Runs the detector on each window and emits (FrameType, plaintext) messages."""

    def __init__(self, identity: Identity, gateway_pk: bytes, model: QuantAE, meter: VirtualMeter,
                 suite: Suite = Suite.HYBRID, resume: bool = True) -> None:
        self.identity = identity
        self.resume = resume
        self.ticket = None  # resumption ticket from the last session
        self.gateway_pk = gateway_pk
        self.model = model
        self.meter = meter
        self.suite = suite
        self.fsm = IncidentFSM()
        self.alerts: list[dict] = []
        self.incidents = 0
        self.raw_payload_bytes = 0  # baseline: sum of raw records' sealed sizes
        self._acc = self._new_acc()

    @staticmethod
    def _new_acc() -> dict:
        return {"n": 0, "kwh": 0.0, "vmin": 1e9, "vmax": 0.0, "pf": 0.0, "smax": 0, "nflag": 0}

    @property
    def node_hex(self) -> str:
        return self.identity.node_id.hex()

    def step(self, minute: int) -> list[tuple[FrameType, bytes]]:
        raw, x = self.meter.window(minute)
        self.raw_payload_bytes += 4 + RECORD_OVERHEAD + len(raw_record(minute, raw))
        d = self.model.detect(x)
        score, anomalous, culprit = int(d["score"][0]), bool(d["anomaly"][0]), int(d["culprit"][0])
        out: list[tuple[FrameType, bytes]] = []

        ev = self.fsm.step(anomalous)
        if ev == "open":
            self.incidents += 1
            evidence = {
                "node": self.node_hex,
                "window": minute,
                "hour": round(raw["hour"], 4),
                "score": score,
                "culprit": FEATURES[culprit],
                "features": [round(float(v), 6) for v in x],
                "model_thr": int(self.model.threshold),
            }
            body = canonical(evidence)
            sig = pq.sign(self.identity.sk, body, EVIDENCE_CTX)
            self.alerts.append(evidence)
            out.append((FrameType.ALERT, encode_alert(body, sig)))

        a = self._acc
        a["n"] += 1
        a["kwh"] += raw["V"] * raw["I"] * raw["pf"] / 60.0 / 1000.0
        a["vmin"], a["vmax"] = min(a["vmin"], raw["V"]), max(a["vmax"], raw["V"])
        a["pf"] += raw["pf"]
        a["smax"] = max(a["smax"], score)
        a["nflag"] += int(anomalous)
        if a["n"] == SUMMARY_EVERY:
            summary = {"w": minute, "kwh": round(a["kwh"], 4), "vmin": round(a["vmin"], 1),
                       "vmax": round(a["vmax"], 1), "pf": round(a["pf"] / a["n"], 3), "smax": a["smax"],
                       "nflag": a["nflag"], "inc": int(self.fsm.active)}
            out.append((FrameType.DATA, canonical(summary)))
            self._acc = self._new_acc()
        return out

    # ------------------------------------------------------------------ client
    async def _connect(self, host: str, port: int, stats: dict):
        """Resume with a stored ticket if possible, otherwise run the full handshake."""
        if self.resume and self.ticket is not None:
            reader, writer = await asyncio.open_connection(host, port)
            nr = NodeResume(self.ticket)
            self.ticket = None  # single use, whatever the outcome
            first = nr.hello()
            await write_frame(writer, first)
            reply = await read_frame(reader)
            try:
                session = nr.finish(reply)
                stats["resumed"] = True
                return reader, writer, session, first, reply
            except ProtocolError:
                writer.close()
                stats["resume_failed"] = True
        reader, writer = await asyncio.open_connection(host, port)
        hs = NodeHandshake(self.identity, self.gateway_pk, self.suite)
        first = hs.hello()
        await write_frame(writer, first)
        reply = await read_frame(reader)
        return reader, writer, hs.finish(reply), first, reply

    async def run(self, host: str, port: int, start_minute: int, minutes: int) -> dict:
        """Connect, handshake (or resume), stream ``minutes`` windows, then CLOSE. Returns byte counters."""
        stats = {"tx": 0, "rx": 0, "handshake": 0, "resumed": False}
        raw_before = self.raw_payload_bytes
        reader, writer, session, first, reply = await self._connect(host, port, stats)
        try:
            self.ticket = session.ticket
            stats["tx"] += len(encode_stream(first))
            stats["rx"] += len(encode_stream(reply))
            stats["handshake"] = stats["tx"] + stats["rx"]
            for m in range(start_minute, start_minute + minutes):
                for ftype, pt in self.step(m):
                    rec = session.seal(ftype, pt)
                    stats["tx"] += len(encode_stream(rec))
                    await write_frame(writer, rec)
            rec = session.seal(FrameType.CLOSE, b"")
            stats["tx"] += len(encode_stream(rec))
            await write_frame(writer, rec)
            await reader.read()  # wait for the gateway to close its side
        finally:
            writer.close()
            try:
                await writer.wait_closed()
            except (ConnectionError, OSError):
                pass
        # baseline: same handshake + one raw record per minute + CLOSE
        stats["raw_baseline"] = stats["handshake"] + (self.raw_payload_bytes - raw_before) + 4 + RECORD_OVERHEAD
        return stats


def feature_vector(evidence: dict) -> np.ndarray:
    return np.array(evidence["features"], dtype=np.float32)
