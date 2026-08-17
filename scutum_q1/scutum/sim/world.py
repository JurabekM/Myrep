"""Simulyatsiya dunyosi: Alisa, Bobur, ishonchsiz server va (ixtiyoriy) Mallory."""
from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Optional

from ..config import ProtocolConfig, spec_config
from ..protocol.envelope import Envelope, MsgType
from ..protocol.identity import DeviceKeys, fingerprint_words
from ..protocol.sfile import EncryptedFile, ReceiveResult, encrypt_file, receive_file
from ..protocol.session import Client, DecryptedMessage
from .server import UntrustedServer
from .trace import Level, Trace


@dataclass
class ChatLine:
    who: str
    text: str
    ts: float = field(default_factory=time.time)
    ok: bool = True
    detail: str = ""


class World:
    """Bitta to'liq simulyatsiya seansi."""

    def __init__(self, cfg: Optional[ProtocolConfig] = None,
                 trace: Optional[Trace] = None) -> None:
        self.cfg = cfg or spec_config()
        self.trace = trace or Trace()
        self.chat: list[ChatLine] = []
        self.files: dict[bytes, EncryptedFile] = {}
        self.build()

    # ------------------------------------------------------------------
    def build(self) -> None:
        cfg = self.cfg
        self.server = UntrustedServer(cfg, self.trace)

        def hook(actor: str, text: str, data: dict) -> None:
            self.trace.emit(actor, Level.INFO, text)

        self.alice = Client(DeviceKeys.generate("Alisa", cfg), cfg, on_event=hook)
        self.bob = Client(DeviceKeys.generate("Bobur", cfg), cfg, on_event=hook)
        self.mallory = Client(DeviceKeys.generate("Mallory", cfg), cfg, on_event=hook)

        for c in (self.alice, self.bob, self.mallory):
            self.server.publish_bundle(c.device_id, c.bundle())

        self.session_id: Optional[bytes] = None
        self.trace.ok("sim", f"dunyo qurildi — {cfg.describe()}")

    def reconfigure(self, cfg: ProtocolConfig) -> None:
        self.cfg = cfg
        self.chat.clear()
        self.files.clear()
        self.build()

    # ------------------------------------------------------------------
    def clients(self) -> dict[str, Client]:
        return {"Alisa": self.alice, "Bobur": self.bob, "Mallory": self.mallory}

    def other(self, c: Client) -> Client:
        return self.bob if c is self.alice else self.alice

    def fingerprints(self) -> dict[str, str]:
        return {
            c.name: fingerprint_words(c.fingerprint())
            for c in self.clients().values()
        }

    # ------------------------------------------------------------------
    # INIT -> ACK
    # ------------------------------------------------------------------
    def handshake(self, initiator: Optional[Client] = None) -> bytes:
        a = initiator or self.alice
        b = self.other(a)

        bundle = self.server.fetch_bundle(b.device_id)
        init_env = a.start_session(bundle)
        self.server.enqueue(init_env)
        self.trace.ok(a.name, f"INIT yuborildi ({init_env.size(self.cfg)} bayt)")

        wire = self.server.deliver(b.device_id)
        env = Envelope.from_wire(wire, self.cfg)
        ack = b.accept_session(env)
        self.server.publish_bundle(b.device_id, b.bundle())   # OPK yangilandi
        self.server.enqueue(ack)
        self.trace.ok(b.name, "INIT tekshirildi, ACK yuborildi")

        wire = self.server.deliver(a.device_id)
        a.accept_ack(Envelope.from_wire(wire, self.cfg))
        self.trace.ok(a.name, "ACK tasdiqlandi — sessiya tayyor")

        self.session_id = init_env.session_id
        self.chat.append(ChatLine("sim", f"Sessiya ochildi: {self.session_id.hex()[:8]}"))
        return self.session_id

    # ------------------------------------------------------------------
    # MSG
    # ------------------------------------------------------------------
    def send(self, sender: Client, text: str) -> ChatLine:
        if self.session_id is None:
            raise RuntimeError("avval handshake qiling")
        receiver = self.other(sender)
        env = sender.send(self.session_id, text.encode("utf-8"))
        self.server.enqueue(env)

        wire = self.server.deliver(receiver.device_id)
        if wire is None:
            line = ChatLine(sender.name, text, ok=False, detail="paket yetkazilmadi")
            self.chat.append(line)
            return line
        try:
            msg = receiver.receive(Envelope.from_wire(wire, self.cfg))
            line = ChatLine(sender.name, msg.plaintext.decode("utf-8", "replace"))
            self.trace.ok(receiver.name, f"MSG #{env.message_no} ochildi")
        except Exception as exc:  # noqa: BLE001
            line = ChatLine(sender.name, text, ok=False, detail=str(exc))
            self.trace.fail(receiver.name, f"MSG ochilmadi: {exc}")
        self.chat.append(line)
        return line

    def _keepalive(self, sender: Client, receiver: Client) -> None:
        """Ko'rinmas xizmat xabari — ratchet qadamini majburlash uchun."""
        env = sender.send(self.session_id, b"")
        self.server.enqueue(env)
        wire = self.server.deliver(receiver.device_id)
        receiver.receive(Envelope.from_wire(wire, self.cfg))

    def pq_ratchet(self, side: Client) -> None:
        """Spec §6.1 post-kvant ratchet qadami.

        PQ siri DH ratchet qadamiga biriktirilgani uchun `side` avval bir
        xabar QABUL QILISHI kerak — yangi ratchet kaliti aynan o'shanda
        yaratiladi. Shuning uchun bu yerda to'liq borish-kelish bajariladi.
        """
        peer = self.other(side)
        side.request_pq_ratchet(self.session_id)

        self._keepalive(side, peer)   # peer YANGI ratchet kalitini yaratadi
        self._keepalive(peer, side)   # `side` uni ko'radi -> PQ bilan ratchet qiladi
        self._keepalive(side, peer)   # peer ct ni oladi va root-key'ga aralashtiradi

        steps = side.sessions[self.session_id].state.pq_steps
        self.trace.ok("sim", f"post-kvant ratchet bajarildi (#{steps})")
        self.chat.append(
            ChatLine("sim", f"🔄 RATCHET_PQ — root-key ML-KEM siri bilan yangilandi (#{steps})")
        )

    # ------------------------------------------------------------------
    # S-FILE
    # ------------------------------------------------------------------
    def send_file(
        self, sender: Client, data: bytes, name: str, mime: str = "application/octet-stream"
    ) -> tuple[EncryptedFile, ReceiveResult]:
        enc = encrypt_file(data, self.cfg, name=name, mime=mime)
        self.files[enc.file_id] = enc
        self.server.upload(enc.file_id, enc.chunks)

        # Manifest + FK S-MSG sessiyasi ichida yuboriladi (spec §7.1)
        if self.session_id is not None:
            from ..crypto import canonical

            payload = canonical.encode(
                {"kind": "file", "manifest": enc.manifest, "fk": enc.fk}, self.cfg.encoding
            )
            env = sender.send(self.session_id, payload)
            self.server.enqueue(env)
            wire = self.server.deliver(self.other(sender).device_id)
            self.other(sender).receive(Envelope.from_wire(wire, self.cfg))
            self.trace.ok("sim", "manifest + FK sessiya ichida yuborildi")

        chunks = self.server.download(enc.file_id)
        proofs = {i: enc.proof(i) for i in range(min(4, len(enc.chunks)))}
        res = receive_file(enc.manifest, enc.fk, chunks, self.cfg, proofs=proofs)
        return enc, res

    def reverify_file(self, file_id: bytes) -> ReceiveResult:
        enc = self.files[file_id]
        chunks = self.server.download(file_id)
        return receive_file(enc.manifest, enc.fk, chunks, self.cfg)
