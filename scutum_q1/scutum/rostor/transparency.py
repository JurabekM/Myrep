"""Shaffoflik jurnali — spec §8.

Ikki tuzilma birga ishlaydi:
  * append-only jurnal (SCUTUM-Q1 `protocol/merkle.py` — RFC 6962 uslubi,
    o'zgarishsiz qayta ishlatiladi) — TARIXIY audit izi: kim, qachon,
    nima yubordi;
  * `RegistrySMT` (yangi, `rostor/smt.py`) — JORIY HOLAT: institutsiya/
    APK/firibgar-signal reestri, borlik VA yo'qlik isboti bilan.

KRITIK TUZATISH (tashqi audit, 2026-08-17): avvalgi versiyada SMT reestr
jurnal yozuvlaridan MUSTAQIL, alohida `apply_registry_update()` chaqiruvi
orqali o'zgarardi — hech qanday LogEntry talab qilinmasdan. Bu "append-only
audit tarixi" degan da'voni ma'nosiz qilardi: SMT holati jurnaldan
DERIVE QILINMASDI, shuning uchun uni jurnaldan mustaqil tekshirib
bo'lmasdi. Endi:
  * `derive_registry(entries)` — SMT holatini FAQAT jurnal yozuvlaridan
    hisoblaydigan TOZA (pure) funksiya — istalgan auditor/witness/mijoz
    mustaqil qayta hisoblab, `sth.smt_root` bilan solishtira oladi;
  * `TransparencyLog.submit()` — YAGONA yo'l: yozuv reestrga ta'sir
    qiladigan bo'lsa, `self.registry` FAQAT shu yerda, faqat muvaffaqiyatli
    qo'shilgan yozuvdan yangilanadi;
  * `Witness.cosign()` va `LogClient.accept_sth()` — endi `smt_root`ni
    `derive_registry()` orqali MUSTAQIL qayta hisoblab tasdiqlaydi, oldin
    faqat `tree_size`/`root_hash` (jurnal) tekshirilar, `smt_root`
    tekshirilmas edi;
  * `submit()` — endi (agar `roster` berilgan bo'lsa) submitter imzosini
    ANIQ registrator a'zosiga tekshiradi; avval bu tekshiruv umuman yo'q
    edi (istalgan kim, istalgan turdagi yozuvni qo'sha olardi).
"""
from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Optional

from ..config import hardened_config
from ..crypto import canonical
from ..crypto.primitives import (
    HybridSignature,
    hybrid_sign,
    hybrid_verify,
    sha3_256,
)
from ..protocol import merkle as M
from .errors import LogError, TrustError
from .smt import SparseMerkleTree, verify_smt_proof, SMTProof, smt_key

#: ROSTOR har doim to'g'ri (HARDENED) Merkle semantikasini ishlatadi —
#: SPEC/HARDENED tanlovi faqat transport qatlamiga tegishli edi.
_CFG = hardened_config()

MAX_MERGE_DELAY = 24 * 3600          # R4: MMD, tavsiya qiymat
MAX_STH_AGE = 3600                    # §8.4: freshness chegarasi
MIN_WITNESS_COSIGNS = 2               # §8.6: W

LOG_ENTRY_TYPES = (
    "institution", "publisher", "malicious_hash", "payment_gateway",
    "fraud_report", "rebuttal", "revocation",
)
#: Shu turdagi yozuvlar SMT reestriga TA'SIR qiladi — `derive_registry()`
#: faqat shularni ko'radi. `fraud_report`/`rebuttal` alohida (fraud_report.py
#: dagi ballash mexanizmi orqali) yig'iladi, reestr kalit-qiymat holatiga
#: emas.
REGISTRY_TYPES = ("institution", "publisher", "malicious_hash", "payment_gateway", "revocation")


def build_registry_payload(key: bytes, value: bytes) -> bytes:
    """`REGISTRY_TYPES`dagi yozuvlar uchun yagona payload shakli — bu
    `derive_registry()` uni umumiy tarzda dekodlashi uchun zarur."""
    return canonical.encode({"key": key, "value": value})


# ---------------------------------------------------------------------------
# LogEntry
# ---------------------------------------------------------------------------
@dataclass
class LogEntry:
    v: int
    seq: Optional[int]          # log tomonidan tayinlanguncha None
    type: str
    payload: bytes
    submitted_at: int
    submitter_id: bytes
    submitter_sig: HybridSignature

    def _unsequenced_payload(self) -> bytes:
        return canonical.encode({
            "v": self.v, "type": self.type, "payload": self.payload,
            "submitted_at": self.submitted_at, "submitter_id": self.submitter_id,
        })

    def canonical_full(self) -> bytes:
        """`seq` tayinlangandan keyingi to'liq kanonik shakl (barg xeshi uchun)."""
        if self.seq is None:
            raise LogError("seq hali tayinlanmagan")
        return canonical.encode({
            "v": self.v, "seq": self.seq, "type": self.type, "payload": self.payload,
            "submitted_at": self.submitted_at, "submitter_id": self.submitter_id,
            "submitter_sig": self.submitter_sig.to_bytes(),
        })


def sign_log_entry(
    submitter_sk_ed, submitter_sk_mldsa, submitter_id: bytes,
    entry_type: str, payload: bytes, *, submitted_at: Optional[int] = None,
) -> LogEntry:
    if entry_type not in LOG_ENTRY_TYPES:
        raise LogError(f"noma'lum LogEntry turi: {entry_type}")
    entry = LogEntry(
        v=1, seq=None, type=entry_type, payload=payload,
        submitted_at=int(submitted_at if submitted_at is not None else time.time()),
        submitter_id=submitter_id,
        submitter_sig=HybridSignature(b"", b""),   # vaqtinchalik
    )
    signed = b"ROSTOR-1/log-entry" + entry._unsequenced_payload()
    entry.submitter_sig = hybrid_sign(submitter_sk_ed, submitter_sk_mldsa, signed)
    return entry


def verify_log_entry_sig(entry: LogEntry, ed_pk: bytes, mldsa_pk: bytes) -> bool:
    signed = b"ROSTOR-1/log-entry" + entry._unsequenced_payload()
    return hybrid_verify(ed_pk, mldsa_pk, entry.submitter_sig, signed)


def derive_registry(entries: list[LogEntry]) -> SparseMerkleTree:
    """SMT holatini FAQAT jurnal yozuvlaridan hisoblaydigan TOZA funksiya.
    `TransparencyLog.registry` — shu funksiyaning natijasiga tenglashi
    KERAK; `Witness`/`LogClient` buni MUSTAQIL qayta hisoblab tekshiradi."""
    reg = SparseMerkleTree()
    for e in entries:
        if e.type not in REGISTRY_TYPES:
            continue
        try:
            d = canonical.decode(e.payload)
            key, value = d["key"], d["value"]
        except Exception:
            continue   # nomuvofiq payload — reestrga ta'sir qilmaydi
        if e.type == "revocation" or not value:
            reg.remove(smt_key(key))
        else:
            reg.set(smt_key(key), value)
    return reg


# ---------------------------------------------------------------------------
# SubmissionReceipt (R4)
# ---------------------------------------------------------------------------
@dataclass
class SubmissionReceipt:
    entry_hash: bytes
    max_merge_delay: int
    promised_by: int
    sequencer_sig: HybridSignature

    def signed_payload(self) -> bytes:
        return b"ROSTOR-1/submission-receipt" + canonical.encode({
            "entry_hash": self.entry_hash, "max_merge_delay": self.max_merge_delay,
            "promised_by": self.promised_by,
        })


# ---------------------------------------------------------------------------
# STH (Signed Tree Head)
# ---------------------------------------------------------------------------
@dataclass
class STH:
    tree_size: int
    root_hash: bytes
    smt_root: bytes
    smt_epoch: int
    timestamp: int
    operator_id: bytes
    operator_sig: HybridSignature
    witness_sigs: list[tuple[bytes, HybridSignature]] = field(default_factory=list)

    def core_payload(self) -> bytes:
        return canonical.encode({
            "tree_size": self.tree_size, "root_hash": self.root_hash,
            "smt_root": self.smt_root, "smt_epoch": self.smt_epoch,
            "timestamp": self.timestamp, "operator_id": self.operator_id,
        })

    def signed_payload(self) -> bytes:
        return b"ROSTOR-1/sth" + self.core_payload()

    def witness_payload(self) -> bytes:
        return b"ROSTOR-1/witness-cosign" + self.core_payload()


def _entries_leaves(entries: list[LogEntry]) -> list[bytes]:
    return [M.leaf_hash(e.seq, e.canonical_full(), _CFG) for e in entries]


# ---------------------------------------------------------------------------
# Witness — mustaqil operator, jurnal IZCHILLIGINI **va** SMT reestrning
# jurnaldan to'g'ri kelib chiqqanini tekshirib STH'ni hamqo'llaydi
# (to'liq mirror emas, yengil rol — §8.6)
# ---------------------------------------------------------------------------
@dataclass
class Witness:
    witness_id: bytes
    ed_sk: object
    mldsa_sk: object
    last_tree_size: int = 0
    last_root: bytes = b""

    def cosign(self, sth: STH, entries: list[LogEntry]) -> tuple[bytes, HybridSignature]:
        """`entries` — witness o'zi mustaqil kuzatib borgan TO'LIQ yozuvlar
        ro'yxati (haqiqiy joriylashtirishda bu witness'ning o'z jurnal
        nusxasidan keladi; bu yerda sequencer bilan bir xil jurnalni
        ko'rish orqali soddalashtirilgan).

        TUZATISH (tashqi audit): avval faqat `tree_size`/`root_hash`
        (append-only jurnal) tekshirilardi — `smt_root` operator
        tomonidan HAR QANDAY qiymatga o'rnatilishi mumkin edi, witness
        buni sezmasdi. Endi `smt_root` ham `derive_registry(entries)`
        orqali MUSTAQIL qayta hisoblanadi."""
        if len(entries) != sth.tree_size:
            raise LogError(
                f"witness {self.witness_id.hex()[:8]}: entries soni "
                f"({len(entries)}) tree_size'ga ({sth.tree_size}) mos emas"
            )
        leaves = _entries_leaves(entries)
        expected_root = M.build_tree(leaves, _CFG).tree_root if leaves else \
            sha3_256(b"ROSTOR-1/empty-log")
        if expected_root != sth.root_hash:
            raise LogError(
                f"witness {self.witness_id.hex()[:8]}: root_hash berilgan "
                "entries'dan qayta hisoblanganiga mos emas"
            )
        expected_smt_root = derive_registry(entries).root()
        if expected_smt_root != sth.smt_root:
            raise LogError(
                f"witness {self.witness_id.hex()[:8]}: smt_root jurnal "
                "yozuvlaridan DERIVE QILINGANIGA mos emas — operator "
                "reestrni jurnaldan tashqarida o'zgartirgan bo'lishi mumkin"
            )

        if self.last_tree_size > 0:
            if sth.tree_size < self.last_tree_size:
                raise LogError(
                    f"witness {self.witness_id.hex()[:8]}: rollback — "
                    f"tree_size kamaydi ({self.last_tree_size} -> {sth.tree_size})"
                )
            if sth.tree_size > self.last_tree_size:
                proof = M.consistency_proof(leaves, self.last_tree_size, _CFG)
                if not M.verify_consistency(
                    self.last_tree_size, sth.tree_size, proof,
                    self.last_root, sth.root_hash, _CFG,
                ):
                    raise LogError(
                        f"witness {self.witness_id.hex()[:8]}: consistency proof "
                        "mos kelmadi — tarix qayta yozilgan bo'lishi mumkin"
                    )
        self.last_tree_size = sth.tree_size
        self.last_root = sth.root_hash
        return self.witness_id, hybrid_sign(self.ed_sk, self.mldsa_sk, sth.witness_payload())


# ---------------------------------------------------------------------------
# TransparencyLog — operator (sequencer) tomoni
# ---------------------------------------------------------------------------
class TransparencyLog:
    def __init__(self, operator_id: bytes, ed_sk, mldsa_sk, *, roster=None) -> None:
        """`roster` — `rostor.registrar.RegistrarRoster` (ixtiyoriy, lekin
        `SHOULD`): berilsa, `submit()` submitter imzosini ANIQ registrator
        a'zosiga tekshiradi. Berilmasa (masalan quyi-darajadagi testlarda),
        submit() faqat imzoning STRUKTURA jihatdan mavjudligini talab
        qiladi — bu holat production uchun mos emas, faqat sinov uchun."""
        self.operator_id = operator_id
        self._ed_sk = ed_sk
        self._mldsa_sk = mldsa_sk
        self.roster = roster
        self.entries: list[LogEntry] = []
        self.registry = SparseMerkleTree()
        self.smt_epoch = 0
        self._receipts: dict[bytes, SubmissionReceipt] = {}

    # ------------------------------------------------------------------
    def submit(self, entry: LogEntry) -> SubmissionReceipt:
        """Yozuvni qabul qiladi va darhol imzolangan dalolatnoma beradi
        (R4). Agar `self.roster` o'rnatilgan bo'lsa, submitter imzosi
        ANIQ registrator a'zosiga (`entry.submitter_id`) tekshiriladi —
        avval bu tekshiruv UMUMAN yo'q edi: istalgan kim, istalgan
        submitter_id bilan, istalgan turdagi yozuvni qo'sha olardi.

        Reestrga ta'sir qiluvchi turlar (`REGISTRY_TYPES`) uchun
        `self.registry` FAQAT shu yerda, faqat muvaffaqiyatli qo'shilgan
        yozuvdan yangilanadi — bu SMT holatini jurnaldan mustaqil
        o'zgartirish yo'lini butunlay yopadi (`derive_registry()` bilan
        bir xil natija kafolatlanadi)."""
        if self.roster is not None:
            signed = b"ROSTOR-1/log-entry" + entry._unsequenced_payload()
            if not self.roster.verify_member_sig(entry.submitter_id, entry.submitter_sig, signed):
                raise TrustError(
                    "submitter imzosi roster a'zosiga mos emas yoki haqiqiy emas"
                )

        entry_hash = sha3_256(entry._unsequenced_payload())
        now = int(time.time())
        receipt = SubmissionReceipt(
            entry_hash=entry_hash,
            max_merge_delay=MAX_MERGE_DELAY,
            promised_by=now + MAX_MERGE_DELAY,
            sequencer_sig=HybridSignature(b"", b""),
        )
        receipt.sequencer_sig = hybrid_sign(
            self._ed_sk, self._mldsa_sk, receipt.signed_payload()
        )
        entry.seq = len(self.entries)
        self.entries.append(entry)
        self._receipts[entry_hash] = receipt

        if entry.type in REGISTRY_TYPES:
            try:
                d = canonical.decode(entry.payload)
                key, value = d["key"], d["value"]
            except Exception as exc:
                raise LogError(
                    f"'{entry.type}' turidagi yozuv payload'i "
                    "build_registry_payload() shaklida bo'lishi kerak"
                ) from exc
            if entry.type == "revocation" or not value:
                self.registry.remove(smt_key(key))
            else:
                self.registry.set(smt_key(key), value)
            self.smt_epoch += 1

        return receipt

    def entry_included(self, entry_hash: bytes) -> bool:
        """R4: dalolatnoma bergan yozuv haqiqatan jurnalda ekanini
        tekshiradi — agar `False` bo'lsa va `promised_by` o'tgan bo'lsa,
        dalolatnomaning o'zi sequencer'ning noto'g'ri ish tutganining
        ommaviy isboti bo'ladi."""
        for e in self.entries:
            if sha3_256(e._unsequenced_payload()) == entry_hash:
                return True
        return False

    # ------------------------------------------------------------------
    def _leaves(self) -> list[bytes]:
        return _entries_leaves(self.entries)

    def publish_sth(self) -> STH:
        """DIQQAT: `root_hash` — MerkleTree.tree_root (XOM MTH), `.root`
        EMAS. `.root` S-FILE uchun mo'ljallangan va `total_chunks`ni
        ichiga o'rab yuboradi (`0x02||total||tree_root`) — bu o'rash
        o'sib boruvchi jurnal uchun mos emas, chunki consistency proof
        RFC 6962 xom MTH fazosida ishlaydi va `tree_size` STH'da
        alohida maydon sifatida allaqachon bor."""
        leaves = self._leaves()
        tree = M.build_tree(leaves, _CFG) if leaves else None
        sth = STH(
            tree_size=len(self.entries),
            root_hash=tree.tree_root if tree else sha3_256(b"ROSTOR-1/empty-log"),
            smt_root=self.registry.root(),
            smt_epoch=self.smt_epoch,
            timestamp=int(time.time()),
            operator_id=self.operator_id,
            operator_sig=HybridSignature(b"", b""),
        )
        sth.operator_sig = hybrid_sign(self._ed_sk, self._mldsa_sk, sth.signed_payload())
        return sth

    def lookup(self, raw_id: bytes) -> SMTProof:
        return self.registry.prove(smt_key(raw_id))


# ---------------------------------------------------------------------------
# LogClient — mijoz tomoni: freshness + lokal monoton checkpoint (§8.4)
# ---------------------------------------------------------------------------
class LogClient:
    def __init__(self, operator_ed_pk: bytes, operator_mldsa_pk: bytes,
                 witness_pks: dict[bytes, tuple[bytes, bytes]],
                 *, min_witness_cosigns: int = MIN_WITNESS_COSIGNS,
                 max_sth_age: int = MAX_STH_AGE) -> None:
        self._op_ed_pk = operator_ed_pk
        self._op_mldsa_pk = operator_mldsa_pk
        self._witness_pks = witness_pks   # witness_id -> (ed_pk, mldsa_pk)
        self._min_w = min_witness_cosigns
        self._max_age = max_sth_age
        self._checkpoint: Optional[tuple[int, bytes]] = None   # (tree_size, root_hash)

    def accept_sth(self, sth: STH, leaves_for_consistency: Optional[list[bytes]] = None,
                   *, entries: Optional[list[LogEntry]] = None,
                   now: Optional[int] = None) -> None:
        """STH'ni qabul qilishdan oldin barcha shartlarni tekshiradi.
        Muvaffaqiyatli bo'lsa, lokal checkpoint yangilanadi.

        `entries` berilsa (`SHOULD` — real mijoz o'z jurnal nusxasidan
        oladi), `smt_root` `derive_registry(entries)` orqali MUSTAQIL
        qayta hisoblanib tasdiqlanadi — avval bu tekshiruv yo'q edi."""
        now = int(now if now is not None else time.time())

        if not hybrid_verify(self._op_ed_pk, self._op_mldsa_pk,
                             sth.operator_sig, sth.signed_payload()):
            raise LogError("STH operator imzosi haqiqiy emas")

        if now - sth.timestamp > self._max_age:
            raise LogError(
                f"STH eskirgan: {now - sth.timestamp}s > {self._max_age}s (freshness, §8.4)"
            )

        distinct_witnesses = set()
        for wid, sig in sth.witness_sigs:
            pks = self._witness_pks.get(wid)
            if pks and hybrid_verify(pks[0], pks[1], sig, sth.witness_payload()):
                distinct_witnesses.add(wid)
        if len(distinct_witnesses) < self._min_w:
            raise LogError(
                f"witness-cosign yetarli emas: {len(distinct_witnesses)} < "
                f"{self._min_w} (§8.6, split-view himoyasi)"
            )

        if entries is not None:
            if len(entries) != sth.tree_size:
                raise LogError("berilgan entries soni tree_size'ga mos emas")
            if derive_registry(entries).root() != sth.smt_root:
                raise LogError(
                    "smt_root berilgan jurnal yozuvlaridan DERIVE QILINGANIGA "
                    "mos emas — reestr jurnaldan tashqarida o'zgartirilgan"
                )
            if leaves_for_consistency is None:
                leaves_for_consistency = _entries_leaves(entries)

        if self._checkpoint is not None:
            old_size, old_root = self._checkpoint
            if sth.tree_size < old_size:
                raise LogError(
                    f"ROLLBACK: yangi STH eskisidan kichik ({sth.tree_size} < {old_size})"
                )
            if sth.tree_size > old_size:
                if leaves_for_consistency is None:
                    raise LogError(
                        "lokal checkpoint mavjud, lekin consistency proof "
                        "uchun barglar berilmadi"
                    )
                proof = M.consistency_proof(leaves_for_consistency, old_size, _CFG)
                if not M.verify_consistency(
                    old_size, sth.tree_size, proof, old_root, sth.root_hash, _CFG,
                ):
                    raise LogError(
                        "consistency proof mos kelmadi — jurnal tarixi "
                        "o'zgartirilgan bo'lishi mumkin (split-view/rewrite hujumi)"
                    )
            elif sth.root_hash != old_root:
                raise LogError(
                    "bir xil tree_size, LEKIN turli root_hash — split-view hujumi"
                )

        self._checkpoint = (sth.tree_size, sth.root_hash)

    @property
    def checkpoint(self) -> Optional[tuple[int, bytes]]:
        return self._checkpoint

    def verify_lookup(self, proof: SMTProof, sth: STH) -> bool:
        """`proof` (borlik/yo'qlik) `sth.smt_root`ga mos ekanini tekshiradi.
        Chaqiruvchi bundan oldin `accept_sth(sth, ...)` orqali STH'ning
        o'zi haqiqiy va freshdek qabul qilinganini ta'minlashi kerak."""
        return verify_smt_proof(proof, sth.smt_root)
