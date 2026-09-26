"""§12 — o'z tekshiruvchisi. Bank qoidalarini (§11) topshirishdan OLDIN takrorlaydi.

Hisobot `ok` faqat muammo yo'q VA nimadir haqiqatan tekshirilgan bo'lsa.
«Tekshirilmadi» hech qachon «toza» deb ko'rsatilmaydi.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

from .cheklov import cheklov_xeshi
from .ibtido import imzo_togri
from .jurnal import Jurnal
from .konstanta import MAX_KUPYURA, MUHR_UZ, NOMINALLAR, XAZINA
from .merkle import Daraxt, isbot_ajrat, isbot_togri
from .partiya import FaylXatosi, Partiya, partiya_oqi
from .sertifikat import Sertifikat

ISBOT_NAMUNA = 2000


@dataclass(frozen=True)
class Muammo:
    qayerda: str
    qoida: str
    izoh: str

    def __str__(self) -> str:
        return f"[{self.qoida}] {self.qayerda}: {self.izoh}"


@dataclass
class Hisobot:
    muammolar: list[Muammo] = field(default_factory=list)
    tekshirildi: list[str] = field(default_factory=list)

    @property
    def ok(self) -> bool:
        return bool(self.tekshirildi) and not self.muammolar

    def qosh(self, qayerda: str, qoida: str, izoh: str) -> None:
        self.muammolar.append(Muammo(qayerda, qoida, izoh))

    def qoidalar(self) -> set[str]:
        return {m.qoida for m in self.muammolar}

    def birlashtir(self, h: Hisobot) -> None:
        self.muammolar += h.muammolar
        self.tekshirildi += h.tekshirildi

    def matn(self) -> str:
        if self.ok:
            return f"TOZA — {len(self.tekshirildi)} ta ob'ekt tekshirildi, muammo yo'q"
        if not self.tekshirildi and not self.muammolar:
            return "TEKSHIRILMADI — tekshiriladigan narsa topilmadi"
        return f"MUAMMO: {len(self.muammolar)} ta\n" + "\n".join(str(m) for m in self.muammolar)


def _isbot_indekslari(soni: int) -> list[int]:
    if soni <= ISBOT_NAMUNA:
        return list(range(soni))
    uch = ISBOT_NAMUNA // 3
    orta = soni // 2 - uch // 2
    s = set(range(uch)) | set(range(orta, orta + uch)) | set(range(soni - uch, soni))
    return sorted(s)


def partiyani_tekshir(p: Partiya, zarbxona_pk: bytes, sert: Sertifikat | None, *,
                      hozir_ms: int | None = None, limit_qolgan: int | None = None,
                      qayerda: str | None = None) -> Hisobot:
    """Partiyani noldan qayta hisoblaydi. `hozir_ms` — sertifikat vaqti tekshiruvi
    uchun (default: partiyaning zarb vaqti)."""
    h = Hisobot()
    w = qayerda or f"partiya {p.partiya_id.hex()[:12]}"
    h.tekshirildi.append(w)

    if p.soni < 1 or not p.qatorlar:
        h.qosh(w, "bo'sh", "partiyada kupyura yo'q")
        return h
    if p.soni > MAX_KUPYURA:
        h.qosh(w, "soni", f"{MAX_KUPYURA} dan ko'p kupyura")
    if len(p.qatorlar) != p.soni:
        h.qosh(w, "soni", f"sarlavhada {p.soni}, qatorlar {len(p.qatorlar)}")

    cx = cheklov_xeshi(p.cheklov)
    jami = 0
    barglar = []
    for i, q in enumerate(p.qatorlar):
        k = f"{w} #{i}"
        if q.leaf_index != i:
            h.qosh(k, "tartib", f"leaf_index {q.leaf_index} ≠ {i}")
        if q.seq != p.birinchi_seq + i:
            h.qosh(k, "tartib", f"seq {q.seq} ≠ {p.birinchi_seq + i}")
        if q.nominal not in NOMINALLAR:
            h.qosh(k, "nominal", f"noto'g'ri nominal {q.nominal}")
        if q.egasi != XAZINA:
            h.qosh(k, "egasi", f"egasi {q.egasi!r} ≠ {XAZINA}")
        if q.batch_id != p.partiya_id:
            h.qosh(k, "partiya-id", "kupyuradagi partiya id sarlavhadagidan farq qiladi")
        if q.cheklov_xeshi != cx:
            h.qosh(k, "cheklov", "kupyura cheklov xeshi e'lon qilingan cheklovga mos emas")
        if len(q.muhr) != MUHR_UZ:
            h.qosh(k, "muhr", f"muhr uzunligi {len(q.muhr)} ≠ {MUHR_UZ}")
        jami += q.nominal
        barglar.append(q.barg())
    if jami != p.jami:
        h.qosh(w, "jami", f"nominallar yig'indisi {jami} ≠ sarlavhadagi {p.jami}")

    daraxt = Daraxt(barglar)   # ildiz HAMMA bargdan
    if daraxt.ildiz != p.ildiz:
        h.qosh(w, "ildiz", "barglardan qayta hisoblangan ildiz fayldagidan farq qiladi")
    for i in _isbot_indekslari(len(p.qatorlar)):
        q = p.qatorlar[i]
        yol = isbot_ajrat(q.isbot)
        if yol is None or not isbot_togri(barglar[i], yol, i, len(barglar), p.ildiz):
            h.qosh(f"{w} #{i}", "isbot", "Merkle isboti ildizga olib bormaydi")

    if not imzo_togri(zarbxona_pk, p.imzo, p.imzo_xabari()):
        h.qosh(w, "imzo", "zarbxona ML-DSA imzosi noto'g'ri")

    if sert is None:
        h.qosh(w, "sertifikat", "sertifikat yuklanmagan — vakolat tekshirilmadi")
    elif sert.cert_id != p.sert_id:
        h.qosh(w, "sertifikat", "partiya boshqa sertifikat bilan zarb qilingan")
    else:
        m = sert.muammo(zarbxona_pk, p.zarb_ms if hozir_ms is None else hozir_ms)
        if m:
            h.qosh(w, "vakolat", m)
        chegara = sert.limit_amount if limit_qolgan is None else limit_qolgan
        if p.jami > chegara:
            h.qosh(w, "limit", f"jami {p.jami} limitdan ({chegara}) oshadi")
    return h


def faylni_tekshir(yol: Path, zarbxona_pk: bytes, sert: Sertifikat | None,
                   **kw) -> tuple[Hisobot, Partiya | None]:
    try:
        p = partiya_oqi(yol)
    except FaylXatosi as e:
        h = Hisobot()
        h.qosh(Path(yol).name, "fayl", str(e))
        return h, None
    return partiyani_tekshir(p, zarbxona_pk, sert, qayerda=Path(yol).name, **kw), p


def jurnalni_tekshir(jurnal: Jurnal, papka: Path, zarbxona_pk: bytes,
                     sert: Sertifikat | None) -> Hisobot:
    """Jurnal ↔ fayllar."""
    h = Hisobot()
    papka = Path(papka)
    yozuvlar = jurnal.partiyalar()
    h.tekshirildi.append("jurnal")
    royxat = set()
    for y in yozuvlar:
        w = f"jurnal {y.partiya_id[:12]}"
        yol = papka / y.fayl
        royxat.add(y.fayl)
        if not yol.exists():
            h.qosh(w, "fayl", f"fayl yo'q: {y.fayl}")
            continue
        fh, p = faylni_tekshir(yol, zarbxona_pk, sert)
        h.birlashtir(fh)
        if p is None:
            continue
        if p.partiya_id.hex() != y.partiya_id:
            h.qosh(w, "jurnal", "fayldagi partiya id jurnaldagidan farq qiladi")
        if p.jami != y.jami:
            h.qosh(w, "jurnal-summa", f"jurnalda {y.jami}, faylda {p.jami}")
        if p.soni != y.soni:
            h.qosh(w, "jurnal-soni", f"jurnalda {y.soni}, faylda {p.soni}")
        if p.ildiz.hex() != y.ildiz:
            h.qosh(w, "jurnal-ildiz", "ildiz jurnaldagidan farq qiladi")
        if (p.birinchi_seq, p.oxirgi_seq) != (y.birinchi_seq, y.oxirgi_seq):
            h.qosh(w, "jurnal-seq", f"jurnalda {y.birinchi_seq}..{y.oxirgi_seq}, "
                                    f"faylda {p.birinchi_seq}..{p.oxirgi_seq}")
        if p.zaxira_qulfi != y.zaxira_qulfi:
            h.qosh(w, "jurnal-qulf", "zaxira qulfi jurnaldagidan farq qiladi")

    oraliqlar = sorted((y.birinchi_seq, y.oxirgi_seq, y.partiya_id) for y in yozuvlar)
    for (a1, b1, p1), (a2, b2, p2) in zip(oraliqlar, oraliqlar[1:]):
        if a2 <= b1:
            h.qosh(f"jurnal {p1[:12]} / {p2[:12]}", "seq-kesishma",
                   f"seq oraliqlari kesishadi: {a1}..{b1} va {a2}..{b2}")

    if sert is not None:
        jami = jurnal.sert_jami(sert.cert_id.hex())
        if jami > sert.limit_amount:
            h.qosh("jurnal", "limit", f"sertifikat bo'yicha jami {jami} > limit "
                                      f"{sert.limit_amount}")

    pdir = papka
    if pdir.exists():
        for f in sorted(pdir.glob("*.aqbatch")):
            if f.name not in royxat:
                h.qosh(f.name, "fayl", "jurnalda yo'q partiya fayli")
    return h
