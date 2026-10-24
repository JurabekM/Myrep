"""§15.3 — jurnal (SQLite). Har oqim o'z `Jurnal` obyektini ochadi (§16.5)."""

from __future__ import annotations

import sqlite3
from dataclasses import dataclass
from pathlib import Path

from .partiya import Partiya
from .zanjir import NOL, bogin_xeshi, bosh_json

_SXEMA = """
CREATE TABLE IF NOT EXISTS sozlama (kalit TEXT PRIMARY KEY, qiymat TEXT NOT NULL);

CREATE TABLE IF NOT EXISTS buyurtmalar (
    buyurtma_id        TEXT PRIMARY KEY,
    sert_id            TEXT    NOT NULL,
    summa              INTEGER NOT NULL,
    kupyura_soni       INTEGER NOT NULL,
    bajarilgan_kupyura INTEGER NOT NULL DEFAULT 0,
    bajarilgan_summa   INTEGER NOT NULL DEFAULT 0,
    partiya_hajmi      INTEGER NOT NULL,
    zaxira_qulfi       TEXT    NOT NULL,
    cheklov            TEXT    NOT NULL,
    surat              TEXT    NOT NULL,
    holat              TEXT    NOT NULL,
    yaratilgan_ms      INTEGER NOT NULL,
    tugagan_ms         INTEGER
);

CREATE TABLE IF NOT EXISTS partiyalar (
    partiya_id      TEXT PRIMARY KEY,
    buyurtma_id     TEXT REFERENCES buyurtmalar(buyurtma_id),
    sert_id         TEXT    NOT NULL,
    ildiz           TEXT    NOT NULL,
    soni            INTEGER NOT NULL,
    jami            INTEGER NOT NULL,
    birinchi_seq    INTEGER NOT NULL,
    oxirgi_seq      INTEGER NOT NULL,
    zaxira_qulfi    TEXT    NOT NULL,
    cheklov         TEXT    NOT NULL,
    zarb_ms         INTEGER NOT NULL,
    davomiylik_ms   REAL    NOT NULL DEFAULT 0,
    fayl            TEXT    NOT NULL,
    topshirilgan_ms INTEGER,
    topshirish_xatosi TEXT
);

CREATE TABLE IF NOT EXISTS zanjir (
    tartib      INTEGER PRIMARY KEY,
    partiya_id  TEXT UNIQUE NOT NULL,
    oldingi     TEXT NOT NULL,
    xesh        TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS tasdiqlar (
    buyurtma_id   TEXT PRIMARY KEY,
    tasdiqchi_iz  TEXT,
    imzo          TEXT,
    vaqt_ms       INTEGER
);
"""
ZANJIR_VERSIYA = "zanjir_versiya"
OXIRGI_VAQT = "oxirgi_vaqt_ms"
ZANJIR_BOSH = "zanjir_bosh"

HOLATLAR = ("faol", "pauza", "tugadi", "bekor")


@dataclass
class BuyurtmaYozuvi:
    buyurtma_id: str
    sert_id: str
    summa: int
    kupyura_soni: int
    bajarilgan_kupyura: int
    bajarilgan_summa: int
    partiya_hajmi: int
    zaxira_qulfi: str
    cheklov: str
    surat: str
    holat: str
    yaratilgan_ms: int
    tugagan_ms: int | None

    @property
    def qolgan_summa(self) -> int:
        return self.summa - self.bajarilgan_summa

    @property
    def qolgan_kupyura(self) -> int:
        return self.kupyura_soni - self.bajarilgan_kupyura


@dataclass
class PartiyaYozuvi:
    partiya_id: str
    buyurtma_id: str | None
    sert_id: str
    ildiz: str
    soni: int
    jami: int
    birinchi_seq: int
    oxirgi_seq: int
    zaxira_qulfi: str
    cheklov: str
    zarb_ms: int
    davomiylik_ms: float
    fayl: str
    topshirilgan_ms: int | None
    topshirish_xatosi: str | None


class JurnalXatosi(Exception):
    pass


class Jurnal:
    def __init__(self, yol: Path):
        self.yol = Path(yol)
        self.db = sqlite3.connect(self.yol, timeout=10)
        self.db.execute("PRAGMA journal_mode=WAL")
        self.db.execute("PRAGMA foreign_keys=ON")
        self.db.executescript(_SXEMA)
        self.db.commit()
        if self.sozlama(ZANJIR_VERSIYA) is None and not self._partiya_bormi():
            self.sozlama_yoz(ZANJIR_VERSIYA, "1")     # yangi jurnal — zanjir boshidan

    def _partiya_bormi(self) -> bool:
        return self.db.execute("SELECT 1 FROM partiyalar LIMIT 1").fetchone() is not None

    # --- xesh-zanjir ---------------------------------------------------------

    def zanjir_migratsiya_kerak(self) -> bool:
        """Zanjirsiz (eski v3) jurnal: belgisi yo'q, partiyalar bor."""
        return self.sozlama(ZANJIR_VERSIYA) is None and self._partiya_bormi()

    def zanjir_migratsiya(self, imzolovchi) -> int:
        """Eski jurnalga zanjirni bir marta quradi. Faqat belgisi yo'q bo'lsa —
        mavjud zanjirni hech qachon «tuzatmaydi» (bu buzilishni yashirardi)."""
        if not self.zanjir_migratsiya_kerak():
            return 0
        with self.db:
            self.db.execute("BEGIN IMMEDIATE")
            self.db.execute("DELETE FROM zanjir")
            x = NOL
            ys = self.partiyalar()
            for i, y in enumerate(ys):
                yangi = bogin_xeshi(x, y)
                self.db.execute("INSERT INTO zanjir VALUES (?,?,?,?)",
                                (i, y.partiya_id, x.hex(), yangi.hex()))
                x = yangi
            self._bosh_yoz(len(ys), x, imzolovchi)
            self.db.execute("INSERT OR REPLACE INTO sozlama VALUES (?,?)", (ZANJIR_VERSIYA, "1"))
        return len(ys)

    def _bosh_yoz(self, tartib: int, xesh: bytes, imzolovchi) -> None:
        imzo = imzolovchi(tartib, xesh)     # (tartib, xesh) -> imzo; xabarni imzolovchi quradi
        self.db.execute("INSERT OR REPLACE INTO sozlama VALUES (?,?)",
                        (ZANJIR_BOSH, bosh_json(tartib, xesh, imzo)))

    def zanjir_boginlari(self) -> list[tuple[int, str, str, str]]:
        return [tuple(r) for r in self.db.execute(
            "SELECT tartib, partiya_id, oldingi, xesh FROM zanjir ORDER BY tartib")]

    def yop(self) -> None:
        self.db.close()

    # --- sozlama ------------------------------------------------------------

    def sozlama(self, kalit: str, default: str | None = None) -> str | None:
        r = self.db.execute("SELECT qiymat FROM sozlama WHERE kalit=?", (kalit,)).fetchone()
        return r[0] if r else default

    def sozlama_yoz(self, kalit: str, qiymat: str) -> None:
        with self.db:
            self.db.execute("INSERT OR REPLACE INTO sozlama VALUES (?,?)", (kalit, qiymat))

    # --- buyurtmalar ----------------------------------------------------------

    def buyurtma_qosh(self, b: BuyurtmaYozuvi) -> None:
        with self.db:
            self.db.execute("INSERT INTO buyurtmalar VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)",
                            tuple(b.__dict__.values()))

    def buyurtma(self, buyurtma_id: str) -> BuyurtmaYozuvi | None:
        r = self.db.execute("SELECT * FROM buyurtmalar WHERE buyurtma_id=?",
                            (buyurtma_id,)).fetchone()
        return BuyurtmaYozuvi(*r) if r else None

    def buyurtmalar(self, holatlar: tuple[str, ...] | None = None) -> list[BuyurtmaYozuvi]:
        if holatlar:
            q = ",".join("?" * len(holatlar))
            rs = self.db.execute(f"SELECT * FROM buyurtmalar WHERE holat IN ({q})"
                                 " ORDER BY yaratilgan_ms DESC, rowid DESC", holatlar).fetchall()
        else:
            rs = self.db.execute("SELECT * FROM buyurtmalar ORDER BY yaratilgan_ms DESC, rowid DESC")\
                .fetchall()
        return [BuyurtmaYozuvi(*r) for r in rs]

    def buyurtma_holat(self, buyurtma_id: str, holat: str, tugagan_ms: int | None = None) -> None:
        if holat not in HOLATLAR:
            raise JurnalXatosi(f"noma'lum holat: {holat}")
        with self.db:
            self.db.execute("UPDATE buyurtmalar SET holat=?, tugagan_ms=? WHERE buyurtma_id=?",
                            (holat, tugagan_ms, buyurtma_id))

    # --- partiyalar -----------------------------------------------------------

    def keyingi_seq(self) -> int:
        r = self.db.execute("SELECT MAX(oxirgi_seq) FROM partiyalar").fetchone()
        return (r[0] or 0) + 1

    def partiya_yoz(self, p: Partiya, fayl: str, buyurtma_id: str | None, *,
                    imzolovchi) -> None:
        """§15.4-5 — BITTA tranzaksiya: INSERT partiya + zanjir bo'g'ini + imzolangan
        zanjir boshi + UPDATE buyurtma. `birinchi_seq` shu yerda qayta tekshiriladi."""
        try:
            with self.db:
                self.db.execute("BEGIN IMMEDIATE")
                if p.birinchi_seq != self.keyingi_seq():
                    raise JurnalXatosi(
                        f"seq uzilgan: kutilgan {self.keyingi_seq()}, keldi {p.birinchi_seq}")
                self.db.execute(
                    "INSERT INTO partiyalar VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
                    (p.partiya_id.hex(), buyurtma_id, p.sert_id.hex(), p.ildiz.hex(), p.soni,
                     p.jami, p.birinchi_seq, p.oxirgi_seq, p.zaxira_qulfi, p.cheklov,
                     p.zarb_ms, p.davomiylik_s * 1000, fayl, None, None))
                if self.sozlama(ZANJIR_VERSIYA) is None:
                    raise JurnalXatosi("jurnal zanjiri migratsiya qilinmagan")
                r = self.db.execute("SELECT tartib, xesh FROM zanjir ORDER BY tartib DESC"
                                    " LIMIT 1").fetchone()
                tartib, oldingi = (r[0] + 1, bytes.fromhex(r[1])) if r else (0, NOL)
                yangi = bogin_xeshi(oldingi, self.partiya(p.partiya_id.hex()))
                self.db.execute("INSERT INTO zanjir VALUES (?,?,?,?)",
                                (tartib, p.partiya_id.hex(), oldingi.hex(), yangi.hex()))
                self._bosh_yoz(tartib + 1, yangi, imzolovchi)
                if buyurtma_id is not None:
                    c = self.db.execute(
                        "UPDATE buyurtmalar SET bajarilgan_kupyura = bajarilgan_kupyura + ?,"
                        " bajarilgan_summa = bajarilgan_summa + ? WHERE buyurtma_id=?",
                        (p.soni, p.jami, buyurtma_id))
                    if c.rowcount != 1:
                        raise JurnalXatosi("buyurtma topilmadi")
        except sqlite3.Error as e:
            raise JurnalXatosi(str(e)) from e

    def partiyalar(self, buyurtma_id: str | None = None) -> list[PartiyaYozuvi]:
        if buyurtma_id:
            rs = self.db.execute("SELECT * FROM partiyalar WHERE buyurtma_id=?"
                                 " ORDER BY birinchi_seq", (buyurtma_id,)).fetchall()
        else:
            rs = self.db.execute("SELECT * FROM partiyalar ORDER BY birinchi_seq").fetchall()
        return [PartiyaYozuvi(*r) for r in rs]

    def partiya(self, partiya_id: str) -> PartiyaYozuvi | None:
        r = self.db.execute("SELECT * FROM partiyalar WHERE partiya_id=?",
                            (partiya_id,)).fetchone()
        return PartiyaYozuvi(*r) if r else None

    def topshirilmaganlar(self) -> list[PartiyaYozuvi]:
        rs = self.db.execute("SELECT * FROM partiyalar WHERE topshirilgan_ms IS NULL"
                             " ORDER BY birinchi_seq").fetchall()
        return [PartiyaYozuvi(*r) for r in rs]

    def topshirildi(self, partiya_id: str, ms: int) -> None:
        with self.db:
            self.db.execute("UPDATE partiyalar SET topshirilgan_ms=?, topshirish_xatosi=NULL"
                            " WHERE partiya_id=?", (ms, partiya_id))

    def topshirish_xatosi(self, partiya_id: str, matn: str | None) -> None:
        with self.db:
            self.db.execute("UPDATE partiyalar SET topshirish_xatosi=? WHERE partiya_id=?",
                            (matn, partiya_id))

    def eng_oxirgi_vaqt(self) -> int:
        """Jurnal ko'rgan eng keyingi vaqt: saqlangan belgi va partiyalarning zarb_ms."""
        r = self.db.execute("SELECT COALESCE(MAX(zarb_ms),0) FROM partiyalar").fetchone()
        return max(int(r[0]), int(self.sozlama(OXIRGI_VAQT, "0") or 0))

    def vaqt_belgila(self, ms: int) -> None:
        if ms > int(self.sozlama(OXIRGI_VAQT, "0") or 0):
            self.sozlama_yoz(OXIRGI_VAQT, str(ms))

    def sert_jami(self, sert_id_hex: str) -> int:
        r = self.db.execute("SELECT COALESCE(SUM(jami),0) FROM partiyalar WHERE sert_id=?",
                            (sert_id_hex,)).fetchone()
        return int(r[0])

    def jami_statistika(self) -> dict:
        r = self.db.execute("SELECT COUNT(*), COALESCE(SUM(soni),0), COALESCE(SUM(jami),0),"
                            " COALESCE(SUM(CASE WHEN topshirilgan_ms IS NULL THEN 1 END),0)"
                            " FROM partiyalar").fetchone()
        return {"partiya": r[0], "kupyura": r[1], "summa": r[2], "topshirilmagan": r[3]}

    def oxirgi_qulflar(self, n: int = 8) -> list[str]:
        rs = self.db.execute("SELECT zaxira_qulfi, MAX(yaratilgan_ms) m FROM buyurtmalar"
                             " GROUP BY zaxira_qulfi ORDER BY m DESC LIMIT ?", (n,)).fetchall()
        return [r[0] for r in rs]

    # --- ikki kishilik tasdiq (core/tasdiq.py) ------------------------------------

    def tasdiq(self, buyurtma_id: str) -> dict | None:
        r = self.db.execute("SELECT tasdiqchi_iz, imzo, vaqt_ms FROM tasdiqlar"
                            " WHERE buyurtma_id=?", (buyurtma_id,)).fetchone()
        return None if r is None else {"iz": r[0], "imzo": r[1], "vaqt_ms": r[2]}

    def tasdiq_kutish(self, buyurtma_id: str) -> None:
        with self.db:
            self.db.execute("INSERT OR IGNORE INTO tasdiqlar VALUES (?,?,?,?)",
                            (buyurtma_id, None, None, None))

    def tasdiq_yoz(self, buyurtma_id: str, iz: str, imzo_hex: str, vaqt_ms: int) -> None:
        with self.db:
            self.db.execute("INSERT OR REPLACE INTO tasdiqlar VALUES (?,?,?,?)",
                            (buyurtma_id, iz, imzo_hex, vaqt_ms))

    # --- buzish demosi uchun (faqat tekshiruv sahifasi) ----------------------

    def _xom_yangila(self, sql: str, param: tuple) -> None:
        with self.db:
            self.db.execute(sql, param)
