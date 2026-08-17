"""Account/device avtorizatsiya holat mashinasi — spec §13 (R8 tuzatishi).

v1.0 faqat "yangi qurilma qo'shish" oqimini tasvirlagan, lekin kim ruxsat
etilgan qurilmalar ro'yxatini boshqarishini, tiklash so'rovi qanday
bog'lanishini, eski qurilmalar qanday bekor qilinishini ta'riflamagan
edi. `policy_epoch` — SCUTUM-Q1 `revoke_epoch` (Y-8) bilan bir xil naqsh,
endi akkount darajasida.
"""
from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Optional

from ..crypto import canonical
from ..crypto.primitives import HybridSignature, hybrid_sign, hybrid_verify, sha3_256
from .errors import AccountAuthError

RECOVERY_METHODS = ("existing_device_cosign", "institutional_quorum")
DEFAULT_RECOVERY_TTL_SECS = 600


@dataclass
class DeviceEntry:
    device_id: bytes
    dc_hash: bytes
    added_at: int
    added_via: str


@dataclass
class RecoveryPolicy:
    method: str
    k: int
    n: int
    approver_roster_ref: bytes
    #: tashqi audit (2026-08-17): avval `apply_recovery()` ga chaqiruvchi
    #: TOMONIDAN erkin `approver_pks` uzatilardi, siyosatning o'zi buni
    #: majburlamasdi ("revoke_existing" ham xuddi shunday chetlab
    #: o'tilardi) — endi ikkalasi ham SIYOSATNING o'zida.
    revoke_existing: bool = True


def commit_approver_roster(approver_pks: dict[bytes, tuple[bytes, bytes]]) -> bytes:
    """`RecoveryPolicy.approver_roster_ref` — shu funksiyaning natijasi
    bo'lishi SHART. Akkount sozlanganda BIR MARTA hisoblanadi va
    saqlanadi; `apply_recovery()` chaqiruvchi taqdim etgan `approver_pks`
    aynan shu ro'yxatga mos kelishini talab qiladi — aks holda hujumchi
    (yoki chaqiruvchi kodning o'zidagi xato) o'zining kalitlarini
    "approver ro'yxati" sifatida taqdim eta olardi."""
    items = sorted(approver_pks.items())
    return sha3_256(canonical.encode([[k, list(v)] for k, v in items]))


@dataclass
class AccountAuthState:
    account_id: bytes
    policy_epoch: int
    authorized_devices: list[DeviceEntry] = field(default_factory=list)
    recovery_policy: Optional[RecoveryPolicy] = None

    def is_authorized(self, device_id: bytes) -> bool:
        return any(d.device_id == device_id for d in self.authorized_devices)


# ---------------------------------------------------------------------------
# Tiklash so'rovi
# ---------------------------------------------------------------------------
@dataclass
class RecoveryRequest:
    v: int
    new_device_dc: dict
    account_id: bytes
    policy_epoch: int          # kutilayotgan (joriy) epoch
    requested_at: int
    expires_at: int
    method: str

    def _unsigned_dict(self) -> dict:
        return {
            "v": self.v, "new_device_dc": self.new_device_dc, "account_id": self.account_id,
            "policy_epoch": self.policy_epoch, "requested_at": self.requested_at,
            "expires_at": self.expires_at, "method": self.method,
        }

    def request_hash(self) -> bytes:
        return sha3_256(canonical.encode(self._unsigned_dict()))


def create_recovery_request(
    new_device_dc: dict, account_id: bytes, policy_epoch: int, method: str,
    *, ttl_secs: int = DEFAULT_RECOVERY_TTL_SECS, now: Optional[int] = None,
) -> RecoveryRequest:
    if method not in RECOVERY_METHODS:
        raise AccountAuthError(f"noma'lum tiklash usuli: {method}")
    now = int(now if now is not None else time.time())
    return RecoveryRequest(
        v=1, new_device_dc=new_device_dc, account_id=account_id,
        policy_epoch=policy_epoch, requested_at=now, expires_at=now + ttl_secs,
        method=method,
    )


@dataclass
class QuorumApproval:
    approver_id: bytes
    request_hash: bytes
    approval_sig: HybridSignature

    def signed_payload(self) -> bytes:
        return b"ROSTOR-1/quorum-approval" + canonical.encode({
            "approver_id": self.approver_id, "request_hash": self.request_hash,
        })


def create_quorum_approval(approver_id: bytes, ed_sk, mldsa_sk, request: RecoveryRequest) -> QuorumApproval:
    appr = QuorumApproval(
        approver_id=approver_id, request_hash=request.request_hash(),
        approval_sig=HybridSignature(b"", b""),
    )
    appr.approval_sig = hybrid_sign(ed_sk, mldsa_sk, appr.signed_payload())
    return appr


# ---------------------------------------------------------------------------
# Kvorumni tekshirish va holatni atomik yangilash
# ---------------------------------------------------------------------------
def apply_recovery(
    state: AccountAuthState,
    request: RecoveryRequest,
    approvals: list[QuorumApproval],
    approver_pks: dict[bytes, tuple[bytes, bytes]],   # approver_id -> (ed_pk, mldsa_pk)
    *,
    now: Optional[int] = None,
) -> AccountAuthState:
    """Yangi qurilmani qo'shadi va (siyosat bo'yicha) eski qurilmalarni
    ATOMIK ravishda bekor qiladi — ikkalasi bitta, bo'linmas amal
    sifatida, oraliq "ikkalasi ham ishonchli" holati bo'lmaydi.

    KRITIK TUZATISH (tashqi audit, 2026-08-17): avval `approver_pks`
    hech qanday tekshiruvsiz, to'g'ridan-to'g'ri CHAQIRUVCHIDAN qabul
    qilinardi — `state.recovery_policy.approver_roster_ref` maydoni
    e'lon qilingan bo'lsa-da, HECH QAYERDA ishlatilmasdi. Bu shuni
    anglatardiki, chaqiruvchi (yoki uni buzgan hujumchi) O'ZINING
    kalitlarini "approver ro'yxati" sifatida uzatib, o'z tasdig'ini
    haqiqiy qilib ko'rsatishi mumkin edi. Endi `approver_pks`
    `commit_approver_roster()` orqali `approver_roster_ref`ga MAJBURIY
    bog'lanadi. `request.method` ham endi siyosatga solishtiriladi va
    `revoke_existing` chaqiruv nuqtasidan emas, siyosatning o'zidan
    olinadi."""
    now = int(now if now is not None else time.time())

    if request.account_id != state.account_id:
        raise AccountAuthError("account_id mos emas")
    if request.policy_epoch != state.policy_epoch:
        raise AccountAuthError(
            f"ROLLBACK yoki eskirish: so'rov epoch={request.policy_epoch}, "
            f"joriy epoch={state.policy_epoch}"
        )
    if now > request.expires_at:
        raise AccountAuthError("tiklash so'rovi muddati o'tgan")
    if state.recovery_policy is None:
        raise AccountAuthError("akkount uchun tiklash siyosati belgilanmagan")
    if request.method != state.recovery_policy.method:
        raise AccountAuthError(
            f"so'rov usuli ({request.method}) siyosatga "
            f"({state.recovery_policy.method}) mos emas"
        )
    if commit_approver_roster(approver_pks) != state.recovery_policy.approver_roster_ref:
        raise AccountAuthError(
            "taqdim etilgan approver kalitlari siyosatdagi approver_roster_ref "
            "bilan mos emas — ishonchsiz roster"
        )

    req_hash = request.request_hash()
    valid_approvers: set[bytes] = set()
    for appr in approvals:
        if appr.request_hash != req_hash:
            continue   # boshqa so'rovga berilgan tasdiq — e'tiborga olinmaydi
        pks = approver_pks.get(appr.approver_id)
        if pks and hybrid_verify(pks[0], pks[1], appr.approval_sig, appr.signed_payload()):
            valid_approvers.add(appr.approver_id)

    if len(valid_approvers) < state.recovery_policy.k:
        raise AccountAuthError(
            f"kvorum yetarli emas: {len(valid_approvers)} < {state.recovery_policy.k}"
        )

    new_devices = [] if state.recovery_policy.revoke_existing else list(state.authorized_devices)
    new_devices.append(DeviceEntry(
        device_id=request.new_device_dc["device_id"],
        dc_hash=sha3_256(canonical.encode(request.new_device_dc)),
        added_at=now, added_via=request.method,
    ))
    return AccountAuthState(
        account_id=state.account_id, policy_epoch=state.policy_epoch + 1,
        authorized_devices=new_devices, recovery_policy=state.recovery_policy,
    )
