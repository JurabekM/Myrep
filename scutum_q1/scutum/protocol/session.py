"""S-MSG klienti: qurilma + sessiyalar + INIT/ACK/MSG oqimi (spec §11.2)."""
from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Callable, Optional

from ..config import ProtocolConfig
from ..crypto import canonical
from ..crypto.primitives import HybridSignature, hybrid_sign, hybrid_verify
from . import ratchet as R
from .envelope import Envelope, MsgType, RatchetHeader
from .errors import PolicyError, ProtocolError, ReplayError, VerificationError
from .handshake import (
    InitReplayCache,
    InitState,
    accept_init,
    create_init,
)
from .identity import DeviceKeys, build_prekey_bundle, device_fingerprint


@dataclass
class Session:
    session_id: bytes
    peer_device_id: bytes
    peer_dc: dict
    state: R.RatchetState
    established: bool = False
    opened_at: float = field(default_factory=time.time)
    sent: int = 0
    received: int = 0

    @property
    def short_id(self) -> str:
        return self.session_id.hex()[:8]


@dataclass
class DecryptedMessage:
    envelope: Envelope
    plaintext: bytes
    session: Session


class Client:
    """Bitta qurilmaning to'liq protokol holati."""

    def __init__(
        self,
        device: DeviceKeys,
        cfg: ProtocolConfig,
        *,
        on_event: Optional[Callable[[str, str, dict], None]] = None,
    ) -> None:
        self.device = device
        self.cfg = cfg
        self.sessions: dict[bytes, Session] = {}
        self.pending: dict[bytes, InitState] = {}
        self.replay_cache = InitReplayCache()
        self.trusted: dict[bytes, bytes] = {}      # device_id -> tasdiqlangan fingerprint
        self.revoked: set[bytes] = set()
        self.revoke_epochs: dict[bytes, int] = {}
        self._on_event = on_event

    # ------------------------------------------------------------------
    @property
    def name(self) -> str:
        return self.device.name

    @property
    def device_id(self) -> bytes:
        return self.device.device_id

    def fingerprint(self) -> bytes:
        return self.device.fingerprint(self.cfg)

    def bundle(self, *, with_opk: bool = True) -> dict:
        return build_prekey_bundle(self.device, self.cfg, with_opk=with_opk)

    def _emit(self, kind: str, text: str, **data) -> None:
        if self._on_event:
            self._on_event(self.name, f"{kind}: {text}", data)

    # ------------------------------------------------------------------
    # Ishonch (spec §3.1 / §10.1)
    # ------------------------------------------------------------------
    def trust(self, dc: dict) -> bytes:
        """QR / xavfsizlik raqami orqali qo'lda tasdiqlash."""
        fp = device_fingerprint(dc, self.cfg)
        self.trusted[dc["device_id"]] = fp
        return fp

    def check_trust(self, dc: dict) -> Optional[str]:
        """-> ogohlantirish matni yoki None."""
        known = self.trusted.get(dc["device_id"])
        if known is None:
            return "yangi qurilma — tasdiqlanmagan (TOFU)"
        if known != device_fingerprint(dc, self.cfg):
            return "XAVFSIZLIK RAQAMI O'ZGARDI"
        return None

    def _observe_trust(self, dc: dict) -> None:
        """Tashqi audit (2026-08-17): `check_trust`/`trust` mavjud edi,
        lekin hech qayerda chaqirilmasdi — spec §3.2 dagi "o'zgarganda
        aniq ogohlantirish ko'rsatishi MUST" talabi dekorativ (K-2/OPK
        naqshiga o'xshab) qolgan edi. Spec §3.2 bu talabni **blokировка**
        emas, **ogohlantirish** sifatida belgilagan (Signal'dagi "xavfsizlik
        raqami o'zgardi" banneri kabi) — shuning uchun bu yerda ham
        sessiyani to'xtatmaymiz, faqat kuzatiladigan WARN hodisasini
        chiqaramiz va TOFU asosida yangi holatni pinlaymiz."""
        warning = self.check_trust(dc)
        if warning:
            self._emit("TRUST", warning, device_id=dc["device_id"])
        self.trust(dc)

    # ------------------------------------------------------------------
    # INIT
    # ------------------------------------------------------------------
    def start_session(self, bundle: dict, *, now: Optional[int] = None) -> Envelope:
        peer_id = bundle["dc"]["device_id"]
        if peer_id in self.revoked:
            raise PolicyError("qurilma bekor qilingan — yangi sessiya ochilmaydi")
        self._observe_trust(bundle["dc"])
        if self.cfg.revoke_epoch:
            seen = self.revoke_epochs.get(peer_id, -1)
            if bundle.get("revoke_epoch", 0) < seen:
                raise PolicyError(
                    "bundle revoke_epoch orqaga qaytarilgan (rollback hujumi)"
                )
            self.revoke_epochs[peer_id] = bundle.get("revoke_epoch", 0)

        st = create_init(self.device, bundle, self.cfg, now=now)
        self.pending[st.session_id] = st

        rst = R.init_initiator(
            st.session_id, st.rk0, st.peer_spk_x_pk, st.peer_spk_mlkem_pk
        )
        self.sessions[st.session_id] = Session(
            session_id=st.session_id,
            peer_device_id=peer_id,
            peer_dc=st.peer_dc,
            state=rst,
        )
        self._emit("INIT", f"sessiya {st.session_id.hex()[:8]} ochildi", rk0=st.rk0)
        return st.envelope

    def accept_session(self, env: Envelope, *, now: Optional[int] = None) -> Envelope:
        """INIT ni qabul qilib ACK qaytaradi.

        K-6 (tashqi audit, 2026-08-16): `session_id` INIT yuboruvchisi
        tomonidan erkin tanlanadi va server orqali oshkor ko'rinadi (u AAD
        ichida, shifrlanmagan). Bu maydonni tekshirmasdan qabul qilish
        hujumchiga (yoki ishonchsiz serverning o'ziga) allaqachon mavjud
        bo'lgan sessiyaning `session_id` sini bila turib takrorlab, uni
        JIMGINA ALMASHTIRISH imkonini beradi — natijada qurbon o'z eski
        sessiyasi bilan gaplashayotganini o'ylaydi, aslida holat allaqachon
        hujumchining yangi sessiyasi bilan almashtirilgan bo'ladi (aniq
        DoS / sessiya chalkashligi). Bu original spec'da umuman
        ko'rilmagan holat, shuning uchun SPEC/HARDENED bayrog'i ortida
        emas — O-9 kabi so'zsiz tuzatiladi.
        """
        if env.session_id in self.sessions:
            raise ReplayError(
                "session_id allaqachon mavjud sessiyada ishlatilgan — "
                "kolliziya yoki sessiyani almashtirish hujumi (K-6)"
            )
        acc = accept_init(
            self.device, env, self.cfg, now=now, replay_cache=self.replay_cache
        )
        if acc.peer_dc["device_id"] in self.revoked:
            raise PolicyError("bekor qilingan qurilmadan INIT")
        self._observe_trust(acc.peer_dc)

        rst = R.init_responder(
            acc.session_id, acc.rk0, self.device.spk_x, self.device.spk_mlkem
        )
        sess = Session(
            session_id=acc.session_id,
            peer_device_id=acc.peer_dc["device_id"],
            peer_dc=acc.peer_dc,
            state=rst,
            established=True,
        )
        self.sessions[acc.session_id] = sess
        self._emit(
            "INIT",
            f"qabul qilindi, OPK ishlatildi={acc.opk_consumed}",
            rk0=acc.rk0,
        )

        ack_core = {"sid": acc.session_id, "ok": True}
        ack_env = Envelope(
            type=MsgType.ACK,
            sender_device_id=self.device_id,
            recipient_device_id=acc.peer_dc["device_id"],
            session_id=acc.session_id,
            message_no=None,
            timestamp=int(now if now is not None else time.time()),
        )
        signed = ack_env.aad(self.cfg) + canonical.encode(ack_core, self.cfg.encoding)
        sig = hybrid_sign(self.device.ik_ed, self.device.ik_mldsa, signed)
        ack_env.body = canonical.encode(
            {**ack_core, "sig": sig.to_bytes()}, self.cfg.encoding
        )
        return ack_env

    def accept_ack(self, env: Envelope) -> Session:
        sess = self.sessions.get(env.session_id)
        if sess is None:
            raise ProtocolError("noma'lum sessiya uchun ACK")
        body = canonical.decode(env.body, self.cfg.encoding)
        core = {"sid": body["sid"], "ok": body["ok"]}
        signed = env.aad(self.cfg) + canonical.encode(core, self.cfg.encoding)
        sig = HybridSignature.from_bytes(body["sig"])
        if not hybrid_verify(
            sess.peer_dc["ed25519_pk"], sess.peer_dc["mldsa65_pk"], sig, signed
        ):
            raise VerificationError("ACK imzosi haqiqiy emas")
        sess.established = True
        self.pending.pop(env.session_id, None)
        self._emit("ACK", f"sessiya {sess.short_id} tasdiqlandi")
        return sess

    # ------------------------------------------------------------------
    # MSG
    # ------------------------------------------------------------------
    def send(self, session_id: bytes, plaintext: bytes) -> Envelope:
        sess = self._session(session_id)
        env, _mk = R.encrypt(
            sess.state,
            self.cfg,
            plaintext,
            sender_id=self.device_id,
            recipient_id=sess.peer_device_id,
        )
        sess.sent += 1
        return env

    def receive(self, env: Envelope) -> DecryptedMessage:
        """Tashqi audit (2026-08-17): avval `CLOSE` HECH QANDAY
        autentifikatsiyasiz, faqat `env.type` maydoniga qarab qabul
        qilinardi — session_id ochiq ko'ringani uchun (K-6) istalgan
        hujumchi/server bitta paket bilan har qanday sessiyani bekor qila
        olardi. Endi `CLOSE` ham oddiy `MSG` kabi AEAD orqali o'tadi —
        `env.type` faqat AEAD MUVAFFAQIYATLI ochilgandan KEYIN tekshiriladi."""
        sess = self._session(env.session_id)
        try:
            pt = R.decrypt(sess.state, self.cfg, env)
        except ProtocolError:
            raise
        except Exception as exc:  # noqa: BLE001 — xom istisno tashqariga chiqmaydi
            raise ProtocolError(f"xabar qayta ishlanmadi: {type(exc).__name__}") from exc
        if env.type == MsgType.CLOSE:
            sess.state.closed = True
            return DecryptedMessage(env, b"", sess)
        sess.received += 1
        sess.established = True
        return DecryptedMessage(env, pt, sess)

    def request_pq_ratchet(self, session_id: bytes) -> None:
        """Keyingi ratchet qadamiga ML-KEM sirini qo'shishni so'raydi.

        Spec §6.1 buni alohida `RATCHET_PQ` xabari sifatida tasvirlaydi, ammo
        yuboruvchi tomonidan o'z-o'zidan bajarilgan ratchet qadami qabul
        qiluvchi tomonida takrorlanmaydi -> holatlar ajralib ketadi. Shu bois
        PQ siri DH ratchet qadamiga biriktiriladi.
        """
        R.request_pq_ratchet(self._session(session_id).state)
        self._emit("RATCHET_PQ", "keyingi ratchet qadamida PQ so'raldi")

    def pq_pending(self, session_id: bytes) -> bool:
        return self._session(session_id).state.pq_requested

    def close(self, session_id: bytes) -> Envelope:
        sess = self._session(session_id)
        env, _mk = R.encrypt(
            sess.state, self.cfg, b"",
            sender_id=self.device_id, recipient_id=sess.peer_device_id,
            msg_type=MsgType.CLOSE,
        )
        sess.state.closed = True
        return env

    # ------------------------------------------------------------------
    def revoke_device(self, target_dc: dict) -> Envelope:
        """Spec §8 DEVICE_REVOKE — amaldagi qurilmaning gibrid imzosi bilan."""
        self.device.revoke_epoch += 1
        core = {
            "target": target_dc["device_id"],
            "epoch": self.device.revoke_epoch,
            "at": int(time.time()),
        }
        env = Envelope(
            type=MsgType.DEVICE_REVOKE,
            sender_device_id=self.device_id,
            recipient_device_id=None,
            timestamp=core["at"],
        )
        signed = env.aad(self.cfg) + canonical.encode(core, self.cfg.encoding)
        sig = hybrid_sign(self.device.ik_ed, self.device.ik_mldsa, signed)
        env.body = canonical.encode({**core, "sig": sig.to_bytes()}, self.cfg.encoding)
        self.revoked.add(target_dc["device_id"])
        return env

    def _session(self, session_id: Optional[bytes]) -> Session:
        if session_id is None or session_id not in self.sessions:
            raise ProtocolError("sessiya topilmadi")
        return self.sessions[session_id]
