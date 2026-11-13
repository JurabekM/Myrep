"""Ikki kishilik tasdiq (dual control): chegaradan katta buyurtmani ikkinchi operator —
TASDIQCHI — o'z ML-DSA-65 kaliti bilan imzolamaguncha zarb boshlanmaydi.

- Tasdiqchi kaliti `<profil>/tasdiqchi.json` da, o'z paroli bilan shifrlangan (§9
  formati). Uning ochiq kaliti jurnalda ro'yxatga olinadi; zarbxona kaliti bilan bir xil
  bo'lolmaydi.
- Imzo buyurtmaning o'zgarmas maydonlariga bog'lanadi: id, sertifikat, summa, zaxira
  qulfi, cheklov, yaratilgan vaqt. Birortasi o'zgarsa — imzo yaroqsiz.
- Chegaraning o'zi ham tasdiqchi imzosi bilan saqlanadi: birinchi operator uni yolg'iz
  pasaytira olmaydi. Imzo yo'q yoki buzilgan bo'lsa — XAVFSIZ tomonga: har buyurtma
  tasdiq talab qiladi (chegara = 1 so'm).

Chegarasi (halol): bu ilova ichidagi nazorat. `jurnal.db` ni to'g'ridan-to'g'ri
tahrirlay oladigan odam tasdiqchini butunlay o'chirib, o'zinikini ro'yxatdan o'tkazishi
mumkin — buni faqat tashqi nazorat (bank tomonida, jurnal zanjiri eksporti) aniqlaydi.
Bu zarbxonaning ichki formati, bank protokoliga kirmaydi.
"""

from __future__ import annotations

import json
from pathlib import Path

from .ibtido import imzo_togri, imzola, iz, ochiq_kalit, tagged_hash, u64be
from .ombor import OmborXatosi, ombor_och, ombor_yarat

L_TASDIQ = b"AETHER-Q-ZARBXONA/IKKI-TASDIQ/v1"
L_CHEGARA = b"AETHER-Q-ZARBXONA/TASDIQ-CHEGARA/v1"
DEFAULT_CHEGARA = 10_000_000
XAVFSIZ_CHEGARA = 1            # imzo buzilgan bo'lsa: har buyurtma tasdiq talab qiladi
TASDIQCHI_PK = "tasdiqchi_pk"
TASDIQ_CHEGARA = "tasdiq_chegara"

HOLAT_NOMI = {"kerak emas": "kerak emas", "kutilmoqda": "kutilmoqda",
              "tasdiqlangan": "tasdiqlangan ✓", "yaroqsiz": "YAROQSIZ"}


class TasdiqXatosi(ValueError):
    pass


def buyurtma_xabari(b) -> bytes:
    """`b` — BuyurtmaYozuvi. Faqat o'zgarmas, xavfsizlikka taalluqli maydonlar."""
    return tagged_hash(L_TASDIQ, b.buyurtma_id.encode(), bytes.fromhex(b.sert_id),
                       u64be(b.summa), b.zaxira_qulfi.encode("utf-8"),
                       b.cheklov.encode("utf-8"), u64be(b.yaratilgan_ms))


def chegara_xabari(chegara: int) -> bytes:
    return tagged_hash(L_CHEGARA, u64be(chegara))


class IkkiTasdiq:
    """Bitta `Zarbxona` profili ustida. Holatni saqlamaydi — hamma narsa jurnalda."""

    def __init__(self, z):
        self.z = z

    @property
    def kalit_yoli(self) -> Path:
        return Path(self.z.papka) / "tasdiqchi.json"

    # --- ro'yxatdan o'tkazish va chegara -------------------------------------------

    def tasdiqchi_pk(self) -> bytes | None:
        s = self.z.jurnal.sozlama(TASDIQCHI_PK)
        return bytes.fromhex(s) if s else None

    @property
    def yoqilgan(self) -> bool:
        return self.tasdiqchi_pk() is not None

    def tasdiqchi_yarat(self, parol: str, chegara: int = DEFAULT_CHEGARA,
                        n: int | None = None) -> bytes:
        """Tasdiqchi kalitini yaratadi (parolni IKKINCHI operator kiritadi) va
        boshlang'ich chegarani uning kaliti bilan imzolaydi. Qaytaradi: ochiq kalit."""
        if self.yoqilgan:
            raise TasdiqXatosi("tasdiqchi allaqachon ro'yxatdan o'tgan")
        if chegara < 1:
            raise TasdiqXatosi("chegara kamida 1 so'm bo'lsin")
        if self.kalit_yoli.exists():
            raise TasdiqXatosi("tasdiqchi.json allaqachon bor — ustiga yozilmaydi")
        try:
            sk = ombor_yarat(self.kalit_yoli, parol, **({"n": n} if n else {}))
        except OmborXatosi as e:
            raise TasdiqXatosi(str(e)) from e
        pk = ochiq_kalit(sk)
        if pk == self.z.pk:          # amalda imkonsiz, lekin qoida — alohida kalit
            self.kalit_yoli.unlink()
            raise TasdiqXatosi("tasdiqchi kaliti zarbxona kaliti bilan bir xil bo'lolmaydi")
        self.z.jurnal.sozlama_yoz(TASDIQCHI_PK, pk.hex())
        self._chegara_yoz(sk, chegara)
        return pk

    def _och(self, parol: str):
        pk = self.tasdiqchi_pk()
        if pk is None:
            raise TasdiqXatosi("tasdiqchi ro'yxatdan o'tmagan")
        try:
            sk = ombor_och(self.kalit_yoli, parol)
        except OmborXatosi as e:
            raise TasdiqXatosi(f"tasdiqchi: {e}") from e
        if ochiq_kalit(sk) != pk:
            raise TasdiqXatosi("tasdiqchi.json ro'yxatdagi tasdiqchi kalitiga mos emas")
        if pk == self.z.pk:
            raise TasdiqXatosi("tasdiqchi zarbxona operatorining o'zi bo'lolmaydi")
        return sk

    def _chegara_yoz(self, sk, chegara: int) -> None:
        self.z.jurnal.sozlama_yoz(TASDIQ_CHEGARA, json.dumps(
            {"chegara": chegara, "imzo": imzola(sk, chegara_xabari(chegara)).hex()}))

    def chegara(self) -> int | None:
        """None — ikki kishilik tasdiq o'chiq. Imzo buzilgan/yo'q — XAVFSIZ_CHEGARA."""
        pk = self.tasdiqchi_pk()
        if pk is None:
            return None
        try:
            d = json.loads(self.z.jurnal.sozlama(TASDIQ_CHEGARA) or "")
            ch = int(d["chegara"])
            if ch >= 1 and imzo_togri(pk, bytes.fromhex(d["imzo"]), chegara_xabari(ch)):
                return ch
        except (ValueError, KeyError, TypeError):
            pass
        return XAVFSIZ_CHEGARA

    def chegara_ornat(self, chegara: int, parol: str) -> None:
        if chegara < 1:
            raise TasdiqXatosi("chegara kamida 1 so'm bo'lsin")
        self._chegara_yoz(self._och(parol), chegara)

    # --- buyurtma tasdig'i ------------------------------------------------------------

    def kerakmi(self, b) -> bool:
        if self.z.jurnal.tasdiq(b.buyurtma_id) is not None:
            return True              # yaratilganda talab qilingan — chegara keyin o'zgarsa ham
        ch = self.chegara()
        return ch is not None and b.summa >= ch

    def togrimi(self, b) -> bool:
        t = self.z.jurnal.tasdiq(b.buyurtma_id)
        pk = self.tasdiqchi_pk()
        if not t or not t.get("imzo") or pk is None:
            return False
        return imzo_togri(pk, bytes.fromhex(t["imzo"]), buyurtma_xabari(b))

    def holat(self, b) -> str:
        if not self.kerakmi(b):
            return "kerak emas"
        t = self.z.jurnal.tasdiq(b.buyurtma_id)
        if not t or not t.get("imzo"):
            return "kutilmoqda"
        return "tasdiqlangan" if self.togrimi(b) else "yaroqsiz"

    def tasdiqla(self, buyurtma_id: str, parol: str) -> str:
        b = self.z.jurnal.buyurtma(buyurtma_id)
        if b is None:
            raise TasdiqXatosi("buyurtma topilmadi")
        if b.holat in ("tugadi", "bekor"):
            raise TasdiqXatosi(f"buyurtma holati: {b.holat}")
        if not self.kerakmi(b):
            raise TasdiqXatosi("bu buyurtmaga ikkinchi tasdiq kerak emas")
        sk = self._och(parol)
        imzo = imzola(sk, buyurtma_xabari(b))
        self.z.jurnal.tasdiq_yoz(buyurtma_id, iz(ochiq_kalit(sk)), imzo.hex(), self.z.soat_ms())
        return iz(ochiq_kalit(sk))
