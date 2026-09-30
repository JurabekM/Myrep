"""§6 — partiya (zarb algoritmi, imzo xabari) va §10 — `.aqbatch` fayli."""

from __future__ import annotations

import os
import secrets
import sqlite3
import time
from collections.abc import Callable
from dataclasses import dataclass, field
from pathlib import Path

from .cheklov import cheklov_xeshi as _cheklov_xeshi
from .ibtido import imzola, lp, u64le, u128le
from .konstanta import (BATCH_MAGIC, BATCH_VERSION, L_ROOT, MAX_KUPYURA, NOMINALLAR,
                        PARTIYA_ID_UZ, SERT_ID_UZ, SIR_UZ, XAZINA)
from .kupyura import Qator, kupyura_yasa
from .merkle import Daraxt
from .surat import BekorQilindi, Ritm

CHEKLOVSIZ_TEKSHIRUV = 250  # cheklovsiz rejimda bekor qilish shuncha kupyurada bir tekshiriladi


class ZarbXatosi(ValueError):
    pass


def nominallarga_bol(summa: int) -> list[int]:
    """§6.3 — ochko'z, kattadan kichikka. Deterministik."""
    if summa <= 0:
        raise ZarbXatosi("summa musbat bo'lishi kerak")
    natija: list[int] = []
    q = summa
    for n in NOMINALLAR:
        k, q = divmod(q, n)
        natija += [n] * k
    return natija


def nominallar_soni(summa: int) -> int:
    """`len(nominallarga_bol(summa))` — ro'yxat qurmasdan."""
    s, q = 0, summa
    for n in NOMINALLAR:
        k, q = divmod(q, n)
        s += k
    return s


def nominallar_bolagi(summa: int, boshi: int, soni: int) -> list[int]:
    """`nominallarga_bol(summa)[boshi:boshi+soni]` — katta summada ham xotira tejab."""
    natija: list[int] = []
    q, pos = summa, 0
    oxiri = boshi + soni
    for n in NOMINALLAR:
        k, q = divmod(q, n)
        a, b = max(pos, boshi), min(pos + k, oxiri)
        if b > a:
            natija += [n] * (b - a)
        pos += k
        if pos >= oxiri:
            break
    return natija


def imzo_xabari(ildiz: bytes, partiya_id: bytes, soni: int, jami: int,
                zaxira_qulfi: str, zarb_ms: int) -> bytes:
    """§6.2 BATCH-ROOT/v1 — LE u64 prefiks, summa u128."""
    b = bytearray()
    lp(b, L_ROOT)
    lp(b, ildiz)
    lp(b, partiya_id)
    lp(b, u64le(soni))
    lp(b, u128le(jami))
    lp(b, zaxira_qulfi.strip().encode("utf-8"))
    lp(b, u64le(zarb_ms))
    return bytes(b)


@dataclass
class Partiya:
    """Partiya — `.aqbatch` faylining xotiradagi ko'rinishi."""

    partiya_id: bytes
    sert_id: bytes
    ildiz: bytes
    soni: int
    birinchi_seq: int
    jami: int
    zaxira_qulfi: str
    zarb_ms: int
    imzo: bytes
    mint_label: str
    cheklov: str
    qatorlar: list[Qator] = field(default_factory=list)
    davomiylik_s: float = 0.0   # faylga yozilmaydi — jurnal uchun

    @property
    def oxirgi_seq(self) -> int:
        return self.birinchi_seq + self.soni - 1

    def imzo_xabari(self) -> bytes:
        return imzo_xabari(self.ildiz, self.partiya_id, self.soni, self.jami,
                           self.zaxira_qulfi, self.zarb_ms)

    def fayl_nomi(self) -> str:
        return f"partiya-{self.partiya_id.hex()[:12]}.aqbatch"


@dataclass
class ZarbKirishi:
    nominallar: list[int]
    sert_id: bytes
    zaxira_qulfi: str
    birinchi_seq: int
    cheklov: str = ""
    egasi: str = XAZINA
    mint_label: str = ""


def _tekshir_kirish(k: ZarbKirishi) -> None:
    if not 1 <= len(k.nominallar) <= MAX_KUPYURA:
        raise ZarbXatosi(f"partiyada 1..{MAX_KUPYURA} kupyura bo'lishi kerak")
    for n in k.nominallar:
        if n not in NOMINALLAR:
            raise ZarbXatosi(f"noto'g'ri nominal: {n}")
    if k.birinchi_seq < 1:
        raise ZarbXatosi("birinchi seq ≥ 1 bo'lishi kerak")
    if not k.zaxira_qulfi.strip():
        raise ZarbXatosi("zaxira qulfi bo'sh — qoplamasiz emissiya yo'q")
    if len(k.sert_id) != SERT_ID_UZ:
        raise ZarbXatosi("sertifikat id 16 bayt bo'lishi kerak")


# kuzatuv(qator, indeks, soni); jarayon(bajarildi, soni) -> False bo'lsa bekor
Kuzatuv = Callable[[Qator, int, int], None]
Jarayon = Callable[[int, int], bool]


def zarb_qil(k: ZarbKirishi, zarbxona_kaliti, *,
             ritm: Ritm | None = None,
             kuzatuv: Kuzatuv | None = None,
             jarayon: Jarayon | None = None,
             bekormi: Callable[[], bool] | None = None,
             soat: Callable[[], float] = time.perf_counter,
             partiya_id: bytes | None = None,
             partiya_kaliti: bytes | None = None,
             master: bytes | None = None,
             zarb_ms: int | None = None) -> Partiya:
    """§6.1 — bitta partiya. Sirlar faqat shu funksiya ichida yashaydi.

    `partiya_id`, `partiya_kaliti`, `master`, `zarb_ms` faqat test/KAT uchun
    tashqaridan beriladi; aks holda tasodifdan olinadi.
    """
    _tekshir_kirish(k)
    partiya_id = partiya_id if partiya_id is not None else secrets.token_bytes(PARTIYA_ID_UZ)
    # Sirlar o'zgaruvchan bytearray'da: ish tugagach (yoki bekor qilinganda) NOL bilan
    # to'ldiriladi. Python kafolat bermaydi (vaqtinchalik nusxalar, hosila kalitlar
    # qolishi mumkin) — bu faqat sirning xotirada yashash vaqtini qisqartiradi (§20).
    partiya_kaliti = _sir(partiya_kaliti)
    master = _sir(master)
    try:
        return _zarb(k, zarbxona_kaliti, partiya_id, partiya_kaliti, master, zarb_ms, ritm,
                     kuzatuv, jarayon, bekormi, soat)
    finally:
        _tozala(partiya_kaliti)
        _tozala(master)


def _sir(berilgan: bytes | None) -> bytearray:
    return bytearray(berilgan if berilgan is not None else secrets.token_bytes(SIR_UZ))


def _tozala(b: bytearray) -> None:
    for i in range(len(b)):
        b[i] = 0


def _zarb(k, zarbxona_kaliti, partiya_id, partiya_kaliti, master, zarb_ms, ritm, kuzatuv,
          jarayon, bekormi, soat) -> Partiya:
    zarb_ms = zarb_ms if zarb_ms is not None else int(time.time() * 1000)  # partiyaga BITTA vaqt
    cx = _cheklov_xeshi(k.cheklov)
    soni = len(k.nominallar)
    har_safar = ritm is not None or kuzatuv is not None
    t0 = soat()

    qatorlar: list[Qator] = []
    barglar: list[bytes] = []
    for i, nominal in enumerate(k.nominallar):
        q, b = kupyura_yasa(i, nominal, k.egasi, k.birinchi_seq + i, partiya_id, cx,
                            partiya_kaliti, master, zarb_ms, k.sert_id)
        qatorlar.append(q)
        barglar.append(b)
        if kuzatuv:
            kuzatuv(q, i, soni)
        if ritm:
            ritm.qadam(i + 1)
        if jarayon and jarayon(i + 1, soni) is False:
            raise BekorQilindi()
        if bekormi and (har_safar or (i + 1) % CHEKLOVSIZ_TEKSHIRUV == 0) and bekormi():
            raise BekorQilindi()

    daraxt = Daraxt(barglar)     # BIR MARTA quriladi
    for i, q in enumerate(qatorlar):
        q.isbot = b"".join(daraxt.isbot(i))
    jami = sum(k.nominallar)
    p = Partiya(partiya_id=partiya_id, sert_id=k.sert_id, ildiz=daraxt.ildiz, soni=soni,
                birinchi_seq=k.birinchi_seq, jami=jami, zaxira_qulfi=k.zaxira_qulfi.strip(),
                zarb_ms=zarb_ms, imzo=b"", mint_label=k.mint_label, cheklov=k.cheklov,
                qatorlar=qatorlar)
    p.imzo = imzola(zarbxona_kaliti, p.imzo_xabari())
    p.davomiylik_s = soat() - t0
    return p


# --- §10 fayl ---------------------------------------------------------------

_SXEMA = """
CREATE TABLE header (
    magic        TEXT    NOT NULL,
    version      INTEGER NOT NULL,
    batch_id     BLOB    NOT NULL,
    cert_id      BLOB    NOT NULL,
    root         BLOB    NOT NULL,
    note_count   INTEGER NOT NULL,
    first_seq    INTEGER NOT NULL,
    total        INTEGER NOT NULL,
    reserve_lock TEXT    NOT NULL,
    minted_ms    INTEGER NOT NULL,
    signature    BLOB    NOT NULL,
    mint_label   TEXT    NOT NULL,
    constraints  TEXT    NOT NULL
);
CREATE TABLE notes (
    leaf_index       INTEGER PRIMARY KEY,
    note_id          BLOB    NOT NULL,
    denomination     INTEGER NOT NULL,
    owner            TEXT    NOT NULL,
    seq              INTEGER NOT NULL,
    batch_id         BLOB    NOT NULL,
    constraints_hash BLOB    NOT NULL,
    sealed_core      BLOB    NOT NULL,
    proof            BLOB    NOT NULL
);
"""

YARIM = ".yarim"


class FaylXatosi(ValueError):
    pass


def partiya_yoz(p: Partiya, papka: Path) -> Path:
    """Atomik: `<nom>.aqbatch.yarim` → commit → close → rename."""
    papka = Path(papka)
    papka.mkdir(parents=True, exist_ok=True)
    yol = papka / p.fayl_nomi()
    yarim = yol.with_name(yol.name + YARIM)
    if yarim.exists():
        yarim.unlink()
    if yol.exists():
        raise FaylXatosi(f"fayl allaqachon bor: {yol.name}")
    db = sqlite3.connect(yarim)
    try:
        db.executescript(_SXEMA)
        db.execute("INSERT INTO header VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)",
                   (BATCH_MAGIC, BATCH_VERSION, p.partiya_id, p.sert_id, p.ildiz, p.soni,
                    p.birinchi_seq, p.jami, p.zaxira_qulfi, p.zarb_ms, p.imzo,
                    p.mint_label, p.cheklov))
        db.executemany("INSERT INTO notes VALUES (?,?,?,?,?,?,?,?,?)",
                       ((q.leaf_index, q.note_id, q.nominal, q.egasi, q.seq, q.batch_id,
                         q.cheklov_xeshi, q.muhr, q.isbot) for q in p.qatorlar))
        db.commit()
    except BaseException:
        db.close()
        yarim.unlink(missing_ok=True)
        raise
    db.close()
    os.replace(yarim, yol)
    return yol


def partiya_oqi(yol: Path) -> Partiya:
    yol = Path(yol)
    if not yol.is_file():
        raise FaylXatosi(f"fayl topilmadi: {yol.name}")
    uri = "file:" + yol.resolve().as_posix() + "?mode=ro"
    try:
        db = sqlite3.connect(uri, uri=True)
    except sqlite3.Error as e:
        raise FaylXatosi(f"fayl ochilmadi: {e}") from e
    try:
        h = db.execute("SELECT magic, version, batch_id, cert_id, root, note_count, first_seq,"
                       " total, reserve_lock, minted_ms, signature, mint_label, constraints"
                       " FROM header").fetchall()
        if len(h) != 1:
            raise FaylXatosi("header jadvalida bitta qator bo'lishi kerak")
        (magic, ver, bid, cid, root, cnt, fseq, total, lock, ms, sig, label, cons) = h[0]
        if magic != BATCH_MAGIC or ver != BATCH_VERSION:
            raise FaylXatosi("partiya fayli emas (magic/version)")
        rows = db.execute("SELECT leaf_index, note_id, denomination, owner, seq, batch_id,"
                          " constraints_hash, sealed_core, proof FROM notes"
                          " ORDER BY leaf_index").fetchall()
    except sqlite3.Error as e:
        raise FaylXatosi(f"fayl o'qilmadi: {e}") from e
    finally:
        db.close()
    qatorlar = [Qator(r[0], bytes(r[1]), r[2], r[3], r[4], bytes(r[5]), bytes(r[6]),
                      bytes(r[7]), bytes(r[8])) for r in rows]
    return Partiya(partiya_id=bytes(bid), sert_id=bytes(cid), ildiz=bytes(root), soni=cnt,
                   birinchi_seq=fseq, jami=total, zaxira_qulfi=lock, zarb_ms=ms,
                   imzo=bytes(sig), mint_label=label, cheklov=cons, qatorlar=qatorlar)
