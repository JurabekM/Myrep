"""ROSTOR-1 simulyatsiya dunyosi: banklar, davlat idorasi, registrator
konsorsiumi, fuqarolar va firibgar — spec `docs/SPEC-ROSTOR-1.1.md`.

SCUTUM-Q1 `sim/world.py` (Alisa/Bobur/Mallory, xabar almashinuvi) dan
ATAYLAB alohida — bu yerda diqqat markazida institutsional ishonch,
tranzaksiya tasdiqlash va shaffoflik jurnali turadi, ikki tomonlama
Double Ratchet sessiyasi emas (garchi IDC lar hali ham oddiy
`DeviceKeys` bo'lgani uchun kerak bo'lganda SCUTUM sessiyasi ochishlari
mumkin).
"""
from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Optional

from ..config import hardened_config
from ..crypto import canonical
from ..crypto.primitives import (
    ed25519_generate,
    ed25519_pub,
    hybrid_sign,
    mldsa_generate,
    mldsa_pub,
    random_bytes,
    sha3_256,
)
from ..protocol.identity import DeviceKeys
from .trace import Level, Trace
from ..rostor.registrar import (
    GenesisAnchor, RegistrarEntry, RegistrarRoster, RegistrarApproval,
    verify_registrar_approval,
)
from ..rostor.identity import InstitutionKeys, issue_endorsement
from ..rostor.transparency import (
    TransparencyLog,
    LogClient,
    Witness,
    build_registry_payload,
    sign_log_entry,
)
from ..rostor.badge import LogSnapshot
from ..rostor.account import AccountAuthState, RecoveryPolicy, commit_approver_roster

CONSORTIUM_SIZE = 5
CONSORTIUM_K = 3
WITNESS_COUNT = 2

#: Simulyatsiyada ROSTOR ilova qatlami har doim to'g'ri, HARDENED SCUTUM-Q1
#: transportidan foydalanadi — SPEC/HARDENED tanlovi faqat transport
#: kamchiliklarini namoyish qilish uchun edi, bu yerga tegishli emas.
CFG = hardened_config()


@dataclass
class Institution:
    keys: InstitutionKeys
    idc: DeviceKeys
    endorsement: object   # IDCEndorsement

    @property
    def display_name(self) -> str:
        return self.keys.display_name


@dataclass
class RegistrarMember:
    registrar_id: bytes
    ed_sk: object
    mldsa_sk: object
    entry: RegistrarEntry


class RostorWorld:
    def __init__(self, trace: Optional[Trace] = None) -> None:
        self.trace = trace or Trace()
        self.institutions: dict[str, Institution] = {}
        self.citizens: dict[str, DeviceKeys] = {}
        self.accounts: dict[str, AccountAuthState] = {}
        self.build()

    # ------------------------------------------------------------------
    def build(self) -> None:
        now = int(time.time())

        # --- Registrator konsorsiumi (§4.1) ---
        self.members: list[RegistrarMember] = []
        for i in range(CONSORTIUM_SIZE):
            ed, ml = ed25519_generate(), mldsa_generate()
            rid = random_bytes(16)
            entry = RegistrarEntry(rid, ed25519_pub(ed), mldsa_pub(ml), f"Registrator-{i}")
            self.members.append(RegistrarMember(rid, ed, ml, entry))
        genesis = GenesisAnchor(
            v=1, roster_epoch=0, published_at=now,
            registrars=[m.entry for m in self.members],
        )
        self.roster = RegistrarRoster(genesis)
        self.k = CONSORTIUM_K

        # --- Shaffoflik jurnali + witness'lar (§8) ---
        op_ed, op_ml = ed25519_generate(), mldsa_generate()
        self.log_operator_id = random_bytes(16)
        self.log = TransparencyLog(self.log_operator_id, op_ed, op_ml, roster=self.roster)
        self._log_op_pks = (ed25519_pub(op_ed), mldsa_pub(op_ml))
        self.witnesses = [Witness(random_bytes(16), ed25519_generate(), mldsa_generate())
                          for _ in range(WITNESS_COUNT)]
        self.log_client = LogClient(
            self._log_op_pks[0], self._log_op_pks[1],
            {w.witness_id: (ed25519_pub(w.ed_sk), mldsa_pub(w.mldsa_sk)) for w in self.witnesses},
        )

        # --- Fuqarolar va firibgar ---
        self.citizens["Alisa"] = DeviceKeys.generate("Alisa", CFG)
        self.fraudster = DeviceKeys.generate("Mallory", CFG)

        # Alisaning HAQIQIY tiklash kvorumi a'zolari (masalan ikkita
        # ishonchli qurilma). `approver_roster_ref` shu aniq kalitlar
        # to'plamiga MAJBURIY bog'langan (account.py::commit_approver_roster) —
        # tashqi audit (2026-08-17) topilmasi: avval bu tasodifiy
        # placeholder edi va HECH QAYERDA tekshirilmasdi.
        self.alice_approvers: dict[bytes, tuple[object, object]] = {
            random_bytes(16): (ed25519_generate(), mldsa_generate()) for _ in range(3)
        }
        alice_approver_pks = {
            aid: (ed25519_pub(ed), mldsa_pub(ml))
            for aid, (ed, ml) in self.alice_approvers.items()
        }
        self.accounts["Alisa"] = AccountAuthState(
            account_id=random_bytes(16), policy_epoch=0,
            authorized_devices=[], recovery_policy=RecoveryPolicy(
                "existing_device_cosign", k=2, n=3,
                approver_roster_ref=commit_approver_roster(alice_approver_pks),
            ),
        )
        self.alice_approver_pks = alice_approver_pks

        self.trace.ok("sim", f"ROSTOR dunyo qurildi: {CONSORTIUM_SIZE} registrator "
                             f"(k={CONSORTIUM_K}), {WITNESS_COUNT} witness")

        # --- Namuna institutsiyalar ---
        self.register_institution("Bank X", "bank")
        self.register_institution("mygov.uz", "government")

    # ------------------------------------------------------------------
    def register_institution(self, display_name: str, category: str) -> Institution:
        """To'liq oqim: IC yaratish -> konsorsium k-of-n tasdig'i ->
        jurnalga yozuv -> SMT reestrga qo'shish -> IDC (SCUTUM DC) va
        endorsement chiqarish."""
        ic = InstitutionKeys.generate(category, display_name)
        target_hash_ = sha3_256(canonical.encode(ic.certificate()))

        appr = RegistrarApproval(
            log_id=self.log_operator_id, action="issue_ic",
            roster_epoch=self.roster.epoch, target_hash=target_hash_,
        )
        signed = appr.signed_payload()
        for m in self.members[: self.k]:
            appr.approvals.append((m.registrar_id, hybrid_sign(m.ed_sk, m.mldsa_sk, signed)))
        if not verify_registrar_approval(appr, self.roster, self.k):
            raise RuntimeError("registrator tasdig'i yetarli emas")

        # TUZATISH (tashqi audit, KRITIK #2/#3): SMT reestr endi FAQAT
        # `log.submit()` orqali, muvaffaqiyatli qo'shilgan yozuvdan
        # yangilanadi — alohida "apply_registry_update" yo'li yopildi.
        submitter = self.members[0]
        entry = sign_log_entry(
            submitter.ed_sk, submitter.mldsa_sk, submitter.registrar_id,
            "institution",
            build_registry_payload(ic.institution_id, canonical.encode(ic.certificate())),
        )
        self.log.submit(entry)

        idc = DeviceKeys.generate(f"{display_name} backend", CFG)
        endorsement = issue_endorsement(ic, idc.dc())

        inst = Institution(keys=ic, idc=idc, endorsement=endorsement)
        self.institutions[display_name] = inst
        self.trace.ok("sim", f"institutsiya ro'yxatdan o'tdi: {display_name} "
                             f"({self.k}/{CONSORTIUM_SIZE} registrator tasdig'i bilan)")
        return inst

    def _submit(self, entry_type: str, key: bytes, value: bytes) -> None:
        submitter = self.members[0]
        entry = sign_log_entry(
            submitter.ed_sk, submitter.mldsa_sk, submitter.registrar_id,
            entry_type, build_registry_payload(key, value),
        )
        self.log.submit(entry)

    def revoke_institution(self, display_name: str) -> None:
        inst = self.institutions[display_name]
        inst.keys.revoke()
        self._submit("institution", inst.keys.institution_id,
                     canonical.encode(inst.keys.certificate()))
        self.trace.attack("sim", f"institutsiya bekor qilindi: {display_name}")

    def add_malicious_hash(self, raw_hash: bytes, *, note: str = "") -> None:
        self._submit("malicious_hash", raw_hash, b"malicious:" + note.encode())
        self.trace.attack("sim", f"zararli xesh reestrga qo'shildi: {raw_hash.hex()[:16]}… {note}")

    # ------------------------------------------------------------------
    def publish_and_witness_sth(self):
        sth = self.log.publish_sth()
        entries = list(self.log.entries)
        sth.witness_sigs = [w.cosign(sth, entries) for w in self.witnesses]
        self.log_client.accept_sth(sth, entries=entries)
        return sth

    def snapshot(self) -> LogSnapshot:
        """Client tomonida ALLAQACHON ishonch bilan tekshirilgan
        (`accept_sth`) holatning oddiy ko'rinishi — `badge.derive_badge`
        shu ustida ishlaydi. To'liq SMT proof-yo'li `rostor/smt.py` va
        `rostor/transparency.py` da alohida testlangan; bu yerda
        soddalashtirilgan, chunki hujum lab diqqati ishonch MANTIG'ida."""
        institutions = {inst.keys.institution_id: inst.keys.certificate()
                        for inst in self.institutions.values()}
        endorsements = {inst.idc.device_id: inst.endorsement
                        for inst in self.institutions.values()}
        return LogSnapshot(institutions=institutions, endorsements=endorsements)
