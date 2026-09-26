"""§15 — buyurtma, partiyalarga bo'lish, davom ettirish, tiklash, yagona yozuvchi.

`Zarbxona` — bitta profil papkasi ustidagi yagona yozuvchi. Uni yaratgan oqim
jurnal ulanishining egasi: boshqa oqim o'z `Zarbxona`/`Jurnal` ini ochadi.
"""

from __future__ import annotations

import os
import secrets
import shutil
import time
from collections.abc import Callable
from dataclasses import dataclass, field
from pathlib import Path

from .jurnal import BuyurtmaYozuvi, Jurnal, JurnalXatosi
from .konstanta import MAX_KUPYURA
from .partiya import (YARIM, FaylXatosi, Partiya, ZarbKirishi, ZarbXatosi, nominallar_bolagi,
                      nominallar_soni, partiya_yoz, zarb_qil)
from .sertifikat import Sertifikat, SertifikatXatosi
from .surat import BekorQilindi, Ritm, Surat
from .tekshiruv import Hisobot, faylni_tekshir, partiyani_tekshir
from .ibtido import ochiq_kalit

DEFAULT_PARTIYA_HAJMI = 500


class BandXatosi(RuntimeError):
    """Profil boshqa nusxa tomonidan band."""


class BuyurtmaXatosi(ValueError):
    pass


# --- yagona yozuvchi (§15.6) -----------------------------------------------


class YagonaYozuvchi:
    """OS darajasidagi eksklyuziv qulf. Ikkinchi nusxa zarb qila olmaydi."""

    def __init__(self, yol: Path):
        self.yol = Path(yol)
        self.yol.parent.mkdir(parents=True, exist_ok=True)
        self._f = open(self.yol, "a+b")  # noqa: SIM115 — yopilguncha ochiq turadi
        try:
            if os.name == "nt":
                import msvcrt
                self._f.seek(0)
                msvcrt.locking(self._f.fileno(), msvcrt.LK_NBLCK, 1)
            else:
                import fcntl
                fcntl.flock(self._f.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
        except OSError as e:
            self._f.close()
            raise BandXatosi("profil boshqa Zarbxona nusxasi tomonidan band "
                             f"({self.yol.name})") from e
        self._f.seek(0)
        self._f.truncate()
        self._f.write(str(os.getpid()).encode())
        self._f.flush()

    def ozod(self) -> None:
        if self._f.closed:
            return
        try:
            if os.name == "nt":
                import msvcrt
                self._f.seek(0)
                msvcrt.locking(self._f.fileno(), msvcrt.LK_UNLCK, 1)
            else:
                import fcntl
                fcntl.flock(self._f.fileno(), fcntl.LOCK_UN)
        finally:
            self._f.close()


# --- natijalar ------------------------------------------------------------------


@dataclass
class BajarishNatijasi:
    holat: str                     # 'tugadi' | 'toxtatildi' | 'pauza'
    xabar: str
    partiyalar: list[Partiya] = field(default_factory=list)
    hisobot: Hisobot | None = None


@dataclass
class TiklashHisoboti:
    ochirilgan_yarim: list[str] = field(default_factory=list)
    qabul_qilingan: list[str] = field(default_factory=list)
    karantin: list[tuple[str, str]] = field(default_factory=list)
    davom_taklifi: list[BuyurtmaYozuvi] = field(default_factory=list)

    @property
    def bosh(self) -> bool:
        return not (self.ochirilgan_yarim or self.qabul_qilingan or self.karantin
                    or self.davom_taklifi)

    def matn(self) -> str:
        q = []
        if self.ochirilgan_yarim:
            q.append(f"yarim yozilgan fayl o'chirildi: {len(self.ochirilgan_yarim)}")
        if self.qabul_qilingan:
            q.append("jurnalga tiklandi: " + ", ".join(self.qabul_qilingan))
        for nom, sabab in self.karantin:
            q.append(f"KARANTIN: {nom} — {sabab}")
        for b in self.davom_taklifi:
            q.append(f"tugallanmagan buyurtma {b.buyurtma_id}: "
                     f"{b.bajarilgan_kupyura}/{b.kupyura_soni} kupyura")
        return "\n".join(q) if q else "tiklash kerak emas"


Hodisa = Callable[[str, dict], None]


def _hozir_ms() -> int:
    return int(time.time() * 1000)


class Zarbxona:
    """Profil papkasi: kalit.json, sertifikat.aqcert, jurnal.db, partiyalar/, karantin/."""

    def __init__(self, papka: Path, sk, *, soat_ms: Callable[[], int] = _hozir_ms):
        self.papka = Path(papka)
        self.papka.mkdir(parents=True, exist_ok=True)
        self.qulf = YagonaYozuvchi(self.papka / "zarbxona.lock")
        try:
            self.sk = sk
            self.pk = ochiq_kalit(sk)
            self.soat_ms = soat_ms
            self.partiya_papka.mkdir(exist_ok=True)
            self.karantin_papka.mkdir(exist_ok=True)
            self.jurnal = Jurnal(self.papka / "jurnal.db")
            self.sertifikat: Sertifikat | None = None
            if self.sert_yoli.exists():
                self.sertifikat = Sertifikat.oqi(self.sert_yoli)
        except BaseException:
            self.qulf.ozod()
            raise

    # --- yo'llar ---------------------------------------------------------------

    @property
    def partiya_papka(self) -> Path:
        return self.papka / "partiyalar"

    @property
    def karantin_papka(self) -> Path:
        return self.papka / "karantin"

    @property
    def sert_yoli(self) -> Path:
        return self.papka / "sertifikat.aqcert"

    def yop(self) -> None:
        try:
            self.jurnal.yop()
        finally:
            if self.qulf is not None:
                self.qulf.ozod()

    def oqim_nusxasi(self) -> Zarbxona:
        """Fon oqimi uchun: o'z jurnal ulanishi, qulf esa asl nusxada qoladi (§16.5).
        Nusxa o'sha oqimda yaratiladi va yopiladi; qulfni ozod qilmaydi."""
        n = object.__new__(Zarbxona)
        n.papka, n.sk, n.pk, n.soat_ms = self.papka, self.sk, self.pk, self.soat_ms
        n.qulf = None
        n.jurnal = Jurnal(self.papka / "jurnal.db")
        n.sertifikat = self.sertifikat
        return n

    # --- sertifikat va limit ---------------------------------------------------

    def sertifikat_import(self, yol: Path) -> Sertifikat:
        s = Sertifikat.oqi(yol)
        m = s.muammo(self.pk, self.soat_ms())
        if m:
            raise SertifikatXatosi(m)
        s.yoz(self.sert_yoli)
        self.sertifikat = s
        return s

    def chiqarilgan(self) -> int:
        if not self.sertifikat:
            return 0
        return self.jurnal.sert_jami(self.sertifikat.cert_id.hex())

    def qolgan_limit(self) -> int:
        if not self.sertifikat:
            return 0
        return self.sertifikat.limit_amount - self.chiqarilgan()

    def band_summa(self, bundan_tashqari: str | None = None) -> int:
        """Boshqa faol/pauza buyurtmalarning hali zarb qilinmagan summasi."""
        if not self.sertifikat:
            return 0
        sid = self.sertifikat.cert_id.hex()
        return sum(b.qolgan_summa for b in self.jurnal.buyurtmalar(("faol", "pauza"))
                   if b.sert_id == sid and b.buyurtma_id != bundan_tashqari)

    # --- buyurtma ----------------------------------------------------------------

    def buyurtma_yarat(self, summa: int, zaxira_qulfi: str, cheklov: str = "",
                       surat: Surat | None = None,
                       partiya_hajmi: int = DEFAULT_PARTIYA_HAJMI) -> BuyurtmaYozuvi:
        s = self.sertifikat
        if s is None:
            raise BuyurtmaXatosi("sertifikat yo'q — avval bank vakolatini import qiling")
        m = s.muammo(self.pk, self.soat_ms())
        if m:
            raise BuyurtmaXatosi(m)
        if summa <= 0:
            raise BuyurtmaXatosi("summa musbat bo'lishi kerak")
        if not zaxira_qulfi.strip():
            raise BuyurtmaXatosi("zaxira qulfi bo'sh — qoplamasiz emissiya yo'q")
        if not 1 <= partiya_hajmi <= MAX_KUPYURA:
            raise BuyurtmaXatosi(f"partiya hajmi 1..{MAX_KUPYURA}")
        erkin = self.qolgan_limit() - self.band_summa()
        if summa > erkin:
            raise BuyurtmaXatosi(f"summa limitdan oshadi: bo'sh limit {erkin:,} so'm"
                                 .replace(",", " "))
        surat = surat or Surat()
        surat.tekshir()
        b = BuyurtmaYozuvi(
            buyurtma_id=secrets.token_bytes(8).hex(), sert_id=s.cert_id.hex(), summa=summa,
            kupyura_soni=nominallar_soni(summa), bajarilgan_kupyura=0, bajarilgan_summa=0,
            partiya_hajmi=partiya_hajmi, zaxira_qulfi=zaxira_qulfi.strip(), cheklov=cheklov,
            surat=surat.json(), holat="faol", yaratilgan_ms=self.soat_ms(), tugagan_ms=None)
        self.jurnal.buyurtma_qosh(b)
        return b

    def buyurtma_bekor(self, buyurtma_id: str) -> None:
        b = self.jurnal.buyurtma(buyurtma_id)
        if b is None:
            raise BuyurtmaXatosi("buyurtma topilmadi")
        if b.holat == "tugadi":
            raise BuyurtmaXatosi("tugagan buyurtmani bekor qilib bo'lmaydi")
        self.jurnal.buyurtma_holat(buyurtma_id, "bekor", self.soat_ms())

    def _pauza(self, bid: str, xabar: str, partiyalar: list[Partiya],
               hisobot: Hisobot | None = None, holat: str = "pauza") -> BajarishNatijasi:
        self.jurnal.buyurtma_holat(bid, "pauza")
        return BajarishNatijasi(holat, xabar, partiyalar, hisobot)

    def buyurtmani_bajar(self, buyurtma_id: str, *,
                         surat: Surat | None = None,
                         kuzatuv=None, jarayon=None,
                         bekormi: Callable[[], bool] | None = None,
                         pauzada: Callable[[], bool] | None = None,
                         tanaffus: Callable[[float], None] | None = None,
                         hodisa: Hodisa | None = None,
                         soat: Callable[[], float] = time.perf_counter,
                         uxla: Callable[[float], None] = time.sleep) -> BajarishNatijasi:
        """Buyurtmani partiyama-partiya bajaradi (§15.4). Uzilsa — faqat joriy
        partiya yo'qoladi; keyingi chaqiriq keyingi kupyuradan davom etadi."""
        hodisa = hodisa or (lambda t, d: None)
        b = self.jurnal.buyurtma(buyurtma_id)
        if b is None:
            raise BuyurtmaXatosi("buyurtma topilmadi")
        if b.holat in ("tugadi", "bekor"):
            raise BuyurtmaXatosi(f"buyurtma holati: {b.holat}")
        surat = surat or Surat.json_dan(b.surat)
        surat.tekshir()
        rs = surat.ritm_sozlamasi(b.kupyura_soni)
        self.jurnal.buyurtma_holat(buyurtma_id, "faol")
        tayyor: list[Partiya] = []

        while b.bajarilgan_kupyura < b.kupyura_soni:
            if bekormi and bekormi():
                return self._pauza(buyurtma_id, "TO'XTATILDI", tayyor, holat="toxtatildi")
            s = self.sertifikat
            if s is None:
                return self._pauza(buyurtma_id, "sertifikat yo'q", tayyor)
            m = s.muammo(self.pk, self.soat_ms())
            if m:
                return self._pauza(buyurtma_id, m, tayyor)
            if s.cert_id.hex() != b.sert_id:
                return self._pauza(buyurtma_id, "buyurtma boshqa sertifikatga tegishli", tayyor)
            soni = min(b.partiya_hajmi, b.qolgan_kupyura)
            noms = nominallar_bolagi(b.summa, b.bajarilgan_kupyura, soni)
            qolgan = self.qolgan_limit()
            if sum(noms) > qolgan:
                return self._pauza(buyurtma_id, f"limit yetmaydi (qolgan {qolgan})", tayyor)
            seq = self.jurnal.keyingi_seq()
            hodisa("partiya_boshlandi", {"soni": soni, "birinchi_seq": seq,
                                         "bajarilgan": b.bajarilgan_kupyura,
                                         "jami_kupyura": b.kupyura_soni})
            ritm = Ritm(rs, soat=soat, uxla=uxla, toxtatildi=bekormi, tanaffus=tanaffus,
                        pauzada=pauzada)
            try:
                p = zarb_qil(ZarbKirishi(noms, s.cert_id, b.zaxira_qulfi, seq, b.cheklov,
                                         mint_label=s.label),
                             self.sk, ritm=ritm, kuzatuv=kuzatuv, jarayon=jarayon,
                             bekormi=bekormi, soat=soat)
            except BekorQilindi:
                hodisa("toxtatildi", {})
                return self._pauza(buyurtma_id, "TO'XTATILDI — partiya yozilmadi", tayyor,
                                   holat="toxtatildi")
            except ZarbXatosi as e:
                return self._pauza(buyurtma_id, f"zarb xatosi: {e}", tayyor)

            h = partiyani_tekshir(p, self.pk, s, hozir_ms=self.soat_ms(), limit_qolgan=qolgan)
            if not h.ok:
                hodisa("tekshiruv_xato", {"hisobot": h})
                return self._pauza(buyurtma_id, "o'z tekshiruvi xato topdi — fayl yozilmadi",
                                   tayyor, h)
            yol = partiya_yoz(p, self.partiya_papka)
            try:
                self.jurnal.partiya_yoz(p, yol.name, buyurtma_id)
            except (JurnalXatosi, Exception) as e:
                yol.unlink(missing_ok=True)   # jurnalda yo'q partiya diskda qolmasin
                return self._pauza(buyurtma_id, f"jurnalga yozilmadi: {e}", tayyor)
            tayyor.append(p)
            hodisa("partiya_yopildi", {"partiya": p, "fayl": yol.name})
            b = self.jurnal.buyurtma(buyurtma_id)

        self.jurnal.buyurtma_holat(buyurtma_id, "tugadi", self.soat_ms())
        hodisa("buyurtma_tugadi", {"buyurtma_id": buyurtma_id})
        return BajarishNatijasi("tugadi", "buyurtma bajarildi", tayyor)

    # --- tiklash (§15.5) -------------------------------------------------------

    def tiklash(self) -> TiklashHisoboti:
        t = TiklashHisoboti()
        for f in sorted(self.partiya_papka.glob("*.aqbatch" + YARIM)):
            f.unlink()
            t.ochirilgan_yarim.append(f.name)

        jurnalda = {y.fayl for y in self.jurnal.partiyalar()}
        yetimlar = []
        for f in self.partiya_papka.glob("*.aqbatch"):
            if f.name in jurnalda:
                continue
            h, p = faylni_tekshir(f, self.pk, self.sertifikat)
            yetimlar.append((p.birinchi_seq if p else 0, f, h, p))
        for _, f, h, p in sorted(yetimlar, key=lambda x: x[0]):
            sabab = self._yetim_qabul(f, h, p)
            if sabab is None:
                t.qabul_qilingan.append(f.name)
            else:
                self.karantin_papka.mkdir(exist_ok=True)
                shutil.move(str(f), str(self.karantin_papka / f.name))
                t.karantin.append((f.name, sabab))

        t.davom_taklifi = self.jurnal.buyurtmalar(("faol",))
        return t

    def _yetim_qabul(self, f: Path, h: Hisobot, p: Partiya | None) -> str | None:
        """Qabul qilinsa None, aks holda sabab."""
        if p is None or not h.ok:
            return "tekshiruvdan o'tmadi: " + "; ".join(str(m) for m in h.muammolar[:3])
        s = self.sertifikat
        if s is None or p.sert_id != s.cert_id:
            return "sertifikat mos emas"
        if p.birinchi_seq != self.jurnal.keyingi_seq():
            return f"seq mos emas (kutilgan {self.jurnal.keyingi_seq()})"
        if p.jami > self.qolgan_limit():
            return "limitdan oshadi"
        noms = [q.nominal for q in p.qatorlar]
        egasi = None
        for b in self.jurnal.buyurtmalar(("faol", "pauza")):
            if (b.sert_id == s.cert_id.hex() and b.zaxira_qulfi == p.zaxira_qulfi
                    and b.cheklov == p.cheklov and b.qolgan_kupyura >= p.soni
                    and nominallar_bolagi(b.summa, b.bajarilgan_kupyura, p.soni) == noms):
                egasi = b.buyurtma_id
                break
        try:
            self.jurnal.partiya_yoz(p, f.name, egasi)
        except JurnalXatosi as e:
            return f"jurnalga yozilmadi: {e}"
        if egasi:
            b = self.jurnal.buyurtma(egasi)
            if b and b.bajarilgan_kupyura >= b.kupyura_soni:
                self.jurnal.buyurtma_holat(egasi, "tugadi", self.soat_ms())
        return None


def partiya_fayli(z: Zarbxona, partiya_id: str) -> Path:
    y = z.jurnal.partiya(partiya_id)
    if y is None:
        raise FaylXatosi("partiya jurnalda yo'q")
    return z.partiya_papka / y.fayl
