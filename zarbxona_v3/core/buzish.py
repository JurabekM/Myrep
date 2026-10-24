"""§12 — «Buzib ko'rish» demosi: faylni yoki jurnalni ataylab buzadi,
tekshiruv topishini ko'rsatadi, «Tiklash» asl holatga qaytaradi.

Demo HECH QACHON haqiqiy profilga tegmaydi: `DemoNusxa` jurnalning va tanlangan
partiya faylining vaqtinchalik nusxasini yaratadi, buzish faqat shu nusxada
bo'ladi. Demo o'rtasida dastur yopilsa yoki tok o'chsa, haqiqiy ma'lumot butun
qoladi — eng yomoni tizim temp papkasida keraksiz nusxa qoladi.

⚠ Buzish qiymati joriy qiymatdan FARQ qilishi shart (v2 dagi xato).
"""

from __future__ import annotations

import shutil
import sqlite3
import tempfile
from pathlib import Path

from .jurnal import Jurnal
from .konstanta import NOMINALLAR, XAZINA

TURLAR = {
    "nominal": "kupyura nominalini o'zgartirish",
    "egasi": "kupyura egasini o'zgartirish",
    "seq": "kupyura tartib raqamini o'zgartirish",
    "imzo": "imzoning bitta baytini o'zgartirish",
    "isbot": "Merkle isbotini buzish",
    "cheklov": "e'lon qilingan cheklovni o'zgartirish",
    "jurnal-summa": "jurnaldagi summani o'zgartirish",
    "jurnal-ochirish": "jurnaldan partiya yozuvini o'chirish (zanjiri bilan)",
    "fayl-ochirish": "partiya faylini o'chirish",
}

# har tur tekshiruvda qaysi qoida(lar)dan biri bilan topilishi kerak. Jurnal yozuvini
# o'chirish: o'rtadagisi — zanjir bo'g'ini, oxirgisi (dum) — imzolangan zanjir boshi.
KUTILGAN_QOIDA = {
    "nominal": {"jami"}, "egasi": {"egasi"}, "seq": {"tartib"}, "imzo": {"imzo"},
    "isbot": {"isbot"}, "cheklov": {"cheklov"}, "jurnal-summa": {"jurnal-summa", "zanjir"},
    "jurnal-ochirish": {"zanjir", "zanjir-bosh"}, "fayl-ochirish": {"fayl"},
}


class BuzishXatosi(Exception):
    pass


def _farqli(joriy, nomzodlar):
    for n in nomzodlar:
        if n != joriy:
            return n
    raise BuzishXatosi("farqli qiymat topilmadi")


class Buzuvchi:
    """Bitta demo seansi. Asl baytlar xotirada saqlanadi."""

    def __init__(self, partiya_papka: Path, jurnal: Jurnal):
        self.papka = Path(partiya_papka)
        self.jurnal = jurnal
        self._fayllar: dict[Path, bytes] = {}
        self._jurnal: list[tuple[str, int]] = []
        self._ochirilgan: list[tuple[tuple, tuple | None]] = []

    @property
    def buzilgan(self) -> bool:
        return bool(self._fayllar or self._jurnal or self._ochirilgan)

    def _saqla(self, yol: Path) -> None:
        if yol not in self._fayllar:
            self._fayllar[yol] = yol.read_bytes()

    def _sql(self, yol: Path, sql: str, param: tuple = ()) -> None:
        self._saqla(yol)
        db = sqlite3.connect(yol)
        try:
            with db:
                db.execute(sql, param)
        finally:
            db.close()

    def _qiymat(self, yol: Path, sql: str):
        db = sqlite3.connect(f"file:{yol.resolve().as_posix()}?mode=ro", uri=True)
        try:
            return db.execute(sql).fetchone()[0]
        finally:
            db.close()

    def buz(self, tur: str, partiya_id: str) -> str:
        """Qaytaradi: nima qilingani (eski → yangi)."""
        y = self.jurnal.partiya(partiya_id)
        if y is None:
            raise BuzishXatosi("partiya jurnalda topilmadi")
        yol = self.papka / y.fayl
        if tur != "jurnal-summa" and not yol.exists():
            raise BuzishXatosi("partiya fayli yo'q")
        if tur == "nominal":
            eski = self._qiymat(yol, "SELECT denomination FROM notes WHERE leaf_index=0")
            yangi = _farqli(eski, NOMINALLAR)
            self._sql(yol, "UPDATE notes SET denomination=? WHERE leaf_index=0", (yangi,))
        elif tur == "egasi":
            eski = self._qiymat(yol, "SELECT owner FROM notes WHERE leaf_index=0")
            yangi = _farqli(eski, ("AQ-BOSQINCHI", XAZINA + "-X"))
            self._sql(yol, "UPDATE notes SET owner=? WHERE leaf_index=0", (yangi,))
        elif tur == "seq":
            eski = self._qiymat(yol, "SELECT seq FROM notes WHERE leaf_index=0")
            yangi = eski + 1_000_000
            self._sql(yol, "UPDATE notes SET seq=? WHERE leaf_index=0", (yangi,))
        elif tur == "imzo":
            s = bytearray(self._qiymat(yol, "SELECT signature FROM header"))
            eski = s[0]
            s[0] ^= 0x01
            yangi = s[0]
            self._sql(yol, "UPDATE header SET signature=?", (bytes(s),))
        elif tur == "isbot":
            p = bytes(self._qiymat(yol, "SELECT proof FROM notes WHERE leaf_index=0"))
            yangi_b = bytes([p[0] ^ 0x01]) + p[1:] if p else bytes(32)
            eski, yangi = f"{len(p)} B", f"{len(yangi_b)} B (o'zgartirilgan)"
            self._sql(yol, "UPDATE notes SET proof=? WHERE leaf_index=0", (yangi_b,))
        elif tur == "cheklov":
            eski = self._qiymat(yol, "SELECT constraints FROM header")
            yangi = _farqli(eski, ('{"categories":["BUZILGAN"]}', ""))
            self._sql(yol, "UPDATE header SET constraints=?", (yangi,))
        elif tur == "jurnal-summa":
            eski = y.jami
            yangi = eski + 1
            self._jurnal.append((partiya_id, eski))
            self.jurnal._xom_yangila("UPDATE partiyalar SET jami=? WHERE partiya_id=?",
                                     (yangi, partiya_id))
        elif tur == "jurnal-ochirish":
            # «aqlli» bosqinchi: partiya yozuvini ham, uning zanjir bo'g'inini ham o'chiradi
            db = self.jurnal.db
            qator = db.execute("SELECT * FROM partiyalar WHERE partiya_id=?",
                               (partiya_id,)).fetchone()
            bogin = db.execute("SELECT * FROM zanjir WHERE partiya_id=?",
                               (partiya_id,)).fetchone()
            self._ochirilgan.append((tuple(qator), tuple(bogin) if bogin else None))
            self.jurnal._xom_yangila("DELETE FROM zanjir WHERE partiya_id=?", (partiya_id,))
            self.jurnal._xom_yangila("DELETE FROM partiyalar WHERE partiya_id=?", (partiya_id,))
            eski, yangi = f"{y.partiya_id[:12]} jurnalda", "o'chirildi"
        elif tur == "fayl-ochirish":
            self._saqla(yol)
            yol.unlink()
            eski, yangi = y.fayl, "o'chirildi"
        else:
            raise BuzishXatosi(f"noma'lum tur: {tur}")
        if eski == yangi:  # himoya: hech narsani buzmaydigan demo — xato
            raise BuzishXatosi("buzish qiymati joriy qiymatga teng")
        return f"{TURLAR[tur]}: {eski} → {yangi}"

    def tikla(self) -> int:
        """Asl holatga qaytaradi. Qaytaradi: tiklangan ob'ektlar soni."""
        n = 0
        for yol, b in self._fayllar.items():
            yol.write_bytes(b)
            n += 1
        for pid, jami in reversed(self._jurnal):
            self.jurnal._xom_yangila("UPDATE partiyalar SET jami=? WHERE partiya_id=?",
                                     (jami, pid))
            n += 1
        for qator, bogin in reversed(self._ochirilgan):
            q = ",".join("?" * len(qator))
            self.jurnal._xom_yangila(f"INSERT INTO partiyalar VALUES ({q})", qator)
            if bogin:
                self.jurnal._xom_yangila("INSERT INTO zanjir VALUES (?,?,?,?)", bogin)
            n += 1
        self._fayllar.clear()
        self._jurnal.clear()
        self._ochirilgan.clear()
        return n


class DemoNusxa:
    """Haqiqiy jurnal va bitta partiya faylining vaqtinchalik nusxasi.

    Jurnal SQLite backup API bilan ko'chiriladi (WAL rejimida ham izchil nusxa);
    fayldan faqat tanlangan partiya olinadi — katta profilda ham tez.
    """

    def __init__(self, jurnal_yoli: Path, partiya_papka: Path, partiya_id: str):
        self.partiya_id = partiya_id
        self.papka = Path(tempfile.mkdtemp(prefix="zarbxona-demo-"))
        self.jurnal: Jurnal | None = None
        try:
            manba = sqlite3.connect(Path(jurnal_yoli))
            nishon = sqlite3.connect(self.papka / "jurnal.db")
            try:
                manba.backup(nishon)
            finally:
                nishon.close()
                manba.close()
            self.jurnal = Jurnal(self.papka / "jurnal.db")
            y = self.jurnal.partiya(partiya_id)
            if y is None:
                raise BuzishXatosi("partiya jurnalda topilmadi")
            self.partiya_papka.mkdir()
            asl = Path(partiya_papka) / y.fayl
            if not asl.exists():
                raise BuzishXatosi(f"partiya fayli yo'q: {y.fayl}")
            shutil.copy2(asl, self.partiya_papka / y.fayl)
        except BaseException:
            self.yop()
            raise
        self.buzuvchi = Buzuvchi(self.partiya_papka, self.jurnal)

    @property
    def partiya_papka(self) -> Path:
        return self.papka / "partiyalar"

    def buz(self, tur: str) -> str:
        return self.buzuvchi.buz(tur, self.partiya_id)

    def tikla(self) -> int:
        return self.buzuvchi.tikla()

    def tekshir(self, zarbxona_pk: bytes, sert):
        from .tekshiruv import jurnalni_tekshir
        return jurnalni_tekshir(self.jurnal, self.partiya_papka, zarbxona_pk, sert,
                                faqat={self.partiya_id})

    def yop(self) -> None:
        if self.jurnal is not None:
            self.jurnal.yop()
            self.jurnal = None
        shutil.rmtree(self.papka, ignore_errors=True)
