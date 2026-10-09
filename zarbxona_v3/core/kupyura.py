"""§4 — kupyura: ochiq sarlavha va muhrlangan yadro."""

from __future__ import annotations

from dataclasses import dataclass

from .ibtido import aead_open, aead_seal, aq_kmac256, hkdf_expand, lp, sha3, u64le
from .konstanta import L_CLAIM, L_HEADER, L_ID, L_REST


def sarlavha_kodi(note_id: bytes, nominal: int, egasi: str, seq: int,
                  partiya_id: bytes, cheklov_xeshi: bytes) -> bytes:
    b = bytearray()
    lp(b, L_HEADER)
    lp(b, note_id)
    lp(b, u64le(nominal))
    lp(b, egasi.encode("utf-8"))
    lp(b, u64le(seq))
    lp(b, partiya_id)
    lp(b, cheklov_xeshi)
    return bytes(b)


def sarlavha_xeshi(kod: bytes) -> bytes:
    """AAD uchun — prefikssiz."""
    return sha3(kod)


def barg(kod: bytes) -> bytes:
    """Merkle bargi — 0x00 prefiks bilan (sarlavha xeshidan FARQLI)."""
    return sha3(b"\x00" + kod)


def note_id_hisobla(partiya_kaliti: bytes, partiya_id: bytes, indeks: int) -> bytes:
    # indeks — partiyadagi o'rni (0 dan), seq EMAS.
    return aq_kmac256(partiya_kaliti, partiya_id + u64le(indeks), L_ID)


def nazorat_kaliti(partiya_kaliti: bytes, note_id: bytes) -> bytes:
    return aq_kmac256(partiya_kaliti, note_id, L_CLAIM)


def konvert(master: bytes, note_id: bytes) -> tuple[bytes, bytes]:
    km = hkdf_expand(master, L_REST + note_id, 44)
    return km[:32], km[32:44]


def yadro(nazorat: bytes, zarb_ms: int, sert_id: bytes) -> bytes:
    return nazorat + u64le(zarb_ms) + sert_id


def muhrla(master: bytes, note_id: bytes, yadro_baytlari: bytes, kod: bytes) -> bytes:
    k, n = konvert(master, note_id)
    return aead_seal(k, n, yadro_baytlari, sarlavha_xeshi(kod))


def muhrni_och(master: bytes, note_id: bytes, muhr: bytes, kod: bytes) -> bytes | None:
    k, n = konvert(master, note_id)
    return aead_open(k, n, muhr, sarlavha_xeshi(kod))


@dataclass(slots=True)
class Qator:
    """Partiya faylidagi bitta kupyura (§10 `notes` jadvali)."""

    leaf_index: int
    note_id: bytes
    nominal: int
    egasi: str
    seq: int
    batch_id: bytes
    cheklov_xeshi: bytes
    muhr: bytes
    isbot: bytes = b""

    def kod(self) -> bytes:
        return sarlavha_kodi(self.note_id, self.nominal, self.egasi, self.seq,
                             self.batch_id, self.cheklov_xeshi)

    def barg(self) -> bytes:
        return barg(self.kod())


def kupyura_yasa(indeks: int, nominal: int, egasi: str, seq: int, partiya_id: bytes,
                 cheklov_xeshi: bytes, partiya_kaliti: bytes, master: bytes,
                 zarb_ms: int, sert_id: bytes) -> tuple[Qator, bytes]:
    """Bitta kupyura. Qaytaradi: (qator — isbotsiz, barg)."""
    nid = note_id_hisobla(partiya_kaliti, partiya_id, indeks)
    kod = sarlavha_kodi(nid, nominal, egasi, seq, partiya_id, cheklov_xeshi)
    yd = yadro(nazorat_kaliti(partiya_kaliti, nid), zarb_ms, sert_id)
    m = muhrla(master, nid, yd, kod)
    return Qator(indeks, nid, nominal, egasi, seq, partiya_id, cheklov_xeshi, m), barg(kod)
