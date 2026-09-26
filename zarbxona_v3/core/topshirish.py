"""§13.5 — onlayn topshirish oqimi va §15.7 — avto-topshirish."""

from __future__ import annotations

import time
from collections.abc import Callable
from pathlib import Path

from .kanal import Kanal, KanalXatosi
from .konstanta import BOLAK_QATOR
from .partiya import FaylXatosi, Partiya, partiya_oqi
from .protokol import (ProtokolXatosi, Wire, batch_begin_param, kodla, mint_auth_imzo, och,
                       qator_kodla)
from .sertifikat import Sertifikat
from .sessiya import SessiyaFabrikasi
from .surat import BekorQilindi

SOROV_MUDDATI = 60.0
HANDSHAKE_MUDDATI = 90.0
ABORT_MUDDATI = 5.0
ALLAQACHON = "allaqachon qabul qilingan"


class TarmoqXatosi(Exception):
    """Vaqtinchalik: qayta urinish mumkin."""


class BankXatosi(Exception):
    """Bank `ok:false` qaytardi."""

    def __init__(self, code: str, matn: str):
        super().__init__(f"{code}: {matn}")
        self.code, self.matn = code, matn

    @property
    def allaqachon(self) -> bool:
        return ALLAQACHON in self.matn

    @property
    def vaqtinchalik(self) -> bool:
        return self.code == "internal"


class Mijoz:
    """Bitta onlayn sessiya: handshake → challenge → mint_auth → partiyalar → bye."""

    def __init__(self, kanal: Kanal, fabrika: SessiyaFabrikasi, sert: Sertifikat, sk, *,
                 muddat: float = SOROV_MUDDATI, hs_muddat: float = HANDSHAKE_MUDDATI,
                 soat: Callable[[], float] = time.monotonic,
                 log: Callable[[str], None] | None = None):
        self.kanal, self.fabrika, self.sert, self.sk = kanal, fabrika, sert, sk
        self.muddat, self.hs_muddat, self.soat = muddat, hs_muddat, soat
        self.log = log or (lambda s: None)
        self._id = 0
        self.sessiya = None
        self.wire: Wire | None = None
        self.vakolat: dict | None = None

    # --- ulanish ------------------------------------------------------------------

    def _qabul(self, oxiri: float, nima: str) -> bytes:
        p = self.kanal.qabul(oxiri - self.soat())
        if p is None:
            raise TarmoqXatosi(f"{nima}: javob kelmadi (muddat tugadi)")
        return p

    def ulan(self) -> dict:
        oxiri = self.soat() + self.hs_muddat
        try:
            # bank kaliti — FAQAT sertifikatdan, pinlangan
            hs = self.fabrika.mijoz(self.sert.bank_public_key)
            self.kanal.yubor(hs.start())
            while not hs.is_connected:
                javob = hs.recv(self._qabul(oxiri, "handshake"))
                if javob:
                    self.kanal.yubor(javob)
            self.sessiya = hs.take_session()
            # challenge — wire'SIZ keladi
            while True:
                p = self._qabul(oxiri, "challenge")
                try:
                    _, pt = self.sessiya.open(p)
                    m = och(pt)
                except (ProtokolXatosi, Exception) as e:  # noqa: BLE001
                    raise TarmoqXatosi(f"challenge o'qilmadi: {e}") from e
                if m.get("op") == "event":
                    continue
                if m.get("op") != "challenge":
                    raise TarmoqXatosi(f"challenge kutilgan edi, keldi: {m.get('op')}")
                break
            nonce, wk = bytes.fromhex(m["nonce"]), bytes.fromhex(m["wire_key"])
        except KanalXatosi as e:
            raise TarmoqXatosi(str(e)) from e
        except (KeyError, ValueError) as e:
            raise TarmoqXatosi(f"challenge buzilgan: {e}") from e
        self.wire = Wire(wk)
        self.log("sessiya o'rnatildi, wire yoqildi")
        imzo = mint_auth_imzo(self.sk, self.sert.bank_public_key, nonce, self.sert.cert_id)
        self.vakolat = self.sorov("mint_auth", cert_id=self.sert.cert_id.hex(),
                                  signature=imzo.hex())
        self.log(f"vakolat tasdiqlandi: qolgan limit {self.vakolat.get('remaining')}")
        return self.vakolat

    # --- so'rov/javob ---------------------------------------------------------------

    def _yubor(self, d: dict) -> None:
        assert self.wire is not None and self.sessiya is not None
        try:
            self.kanal.yubor(self.wire.ora(self.sessiya.seal(kodla(d))))
        except KanalXatosi as e:
            raise TarmoqXatosi(str(e)) from e

    def sorov(self, op: str, muddat: float | None = None, **param) -> dict:
        self._id += 1
        sid = self._id
        self._yubor({"v": 1, "op": op, "id": sid, **param})
        oxiri = self.soat() + (self.muddat if muddat is None else muddat)
        while True:
            try:
                p = self._qabul(oxiri, op)
            except KanalXatosi as e:
                raise TarmoqXatosi(str(e)) from e
            y = self.wire.ech(p)
            if y is None:            # soxta/takroriy — jim tashlandi, kutish davom etadi
                continue
            try:
                _, pt = self.sessiya.open(y)
            except Exception as e:  # noqa: BLE001 — sessiya o'ldi
                raise TarmoqXatosi(f"sessiya yozuvi ochilmadi: {e}") from e
            m = och(pt)
            if m.get("op") == "event":
                continue
            if m.get("id") != sid:
                raise ProtokolXatosi(f"javob id {m.get('id')} ≠ so'rov id {sid}")
            if m.get("ok") is True:
                return m.get("data") or {}
            raise BankXatosi(str(m.get("code", "?")), str(m.get("error", "")))

    # --- partiya --------------------------------------------------------------------

    def partiya_topshir(self, p: Partiya, bekormi: Callable[[], bool] | None = None,
                        jarayon: Callable[[int, int], None] | None = None) -> dict:
        """Qaytaradi: bank javobi; `{"allaqachon": True}` — oldin qabul qilingan."""
        ochiq = False
        try:
            r = self.sorov("batch_begin", **batch_begin_param(p))
            ochiq = True
            bolak = int(r.get("chunk_notes", BOLAK_QATOR)) or BOLAK_QATOR
            bolak = min(bolak, BOLAK_QATOR)
            for i in range(0, p.soni, bolak):
                if bekormi and bekormi():
                    raise BekorQilindi()
                rows = [qator_kodla(q) for q in p.qatorlar[i:i + bolak]]
                self.sorov("batch_chunk", rows=rows)
                if jarayon:
                    jarayon(min(i + bolak, p.soni), p.soni)
            natija = self.sorov("batch_commit")
            ochiq = False
            return natija
        except BankXatosi as e:
            if e.allaqachon:
                self._abort(ochiq)
                return {"allaqachon": True}
            self._abort(ochiq)
            raise
        except BaseException:
            self._abort(ochiq)
            raise

    def _abort(self, ochiq: bool) -> None:
        """Muddat 5 s; uning xatosi asosiy xatoni yashirmaydi."""
        if not ochiq or self.wire is None:
            return
        try:
            self.sorov("batch_abort", muddat=ABORT_MUDDATI)
        except Exception:  # noqa: BLE001
            pass

    def yop(self) -> None:
        try:
            if self.wire is not None:
                self._yubor({"v": 1, "op": "bye", "id": 0})
        except Exception:  # noqa: BLE001
            pass
        finally:
            self.kanal.yop()


# --- §15.7 avto-topshirish -------------------------------------------------------

RAD = "RAD: "
KUTISH_BOSHI, KUTISH_MAX = 5.0, 300.0


class AvtoTopshiruvchi:
    """`topshirilgan_ms IS NULL` partiyalarni seq tartibida bittadan topshiradi.

    Bank rad etsa — o'sha partiya to'xtaydi va keyingilari YUBORILMAYDI.
    Operator xatoni tozalaguncha (`qayta_urin`) yoki «topshirildi» deb
    belgilaguncha shu holatda turadi.
    """

    def __init__(self, jurnal, partiya_papka: Path, mijoz_yarat: Callable[[], Mijoz], *,
                 soat_ms: Callable[[], int] = lambda: int(time.time() * 1000),
                 log: Callable[[str], None] | None = None):
        self.jurnal, self.papka, self.mijoz_yarat = jurnal, Path(partiya_papka), mijoz_yarat
        self.soat_ms = soat_ms
        self.log = log or (lambda s: None)
        self.kutish = KUTISH_BOSHI

    def bir_aylanish(self, bekormi: Callable[[], bool] | None = None) -> str:
        """Qaytaradi: 'bosh' | 'bajarildi' | 'tarmoq' | 'rad'."""
        navbat = self.jurnal.topshirilmaganlar()
        if not navbat:
            return "bosh"
        if navbat[0].topshirish_xatosi and navbat[0].topshirish_xatosi.startswith(RAD):
            return "rad"
        mijoz = None
        try:
            mijoz = self.mijoz_yarat()
            mijoz.ulan()
            for y in navbat:
                if bekormi and bekormi():
                    break
                try:
                    p = partiya_oqi(self.papka / y.fayl)
                except FaylXatosi as e:
                    self.jurnal.topshirish_xatosi(y.partiya_id, RAD + str(e))
                    self.log(f"partiya {y.partiya_id[:12]}: {e}")
                    return "rad"
                try:
                    r = mijoz.partiya_topshir(p, bekormi=bekormi)
                except BankXatosi as e:
                    if e.vaqtinchalik:
                        raise TarmoqXatosi(str(e)) from e
                    self.jurnal.topshirish_xatosi(y.partiya_id, RAD + str(e))
                    self.log(f"BANK RAD ETDI {y.partiya_id[:12]}: {e} — keyingilari "
                             "yuborilmaydi")
                    return "rad"
                self.jurnal.topshirildi(y.partiya_id, self.soat_ms())
                self.log(f"topshirildi {y.partiya_id[:12]}"
                         + (" (allaqachon qabul qilingan edi)" if r.get("allaqachon") else ""))
            self.kutish = KUTISH_BOSHI
            return "bajarildi"
        except BekorQilindi:
            return "bajarildi"
        except (TarmoqXatosi, KanalXatosi, ProtokolXatosi, OSError) as e:
            self.jurnal.topshirish_xatosi(navbat[0].partiya_id, f"tarmoq: {e}")
            self.log(f"tarmoq xatosi: {e} — {self.kutish:.0f} s dan keyin qayta urinish")
            return "tarmoq"
        except BankXatosi as e:  # mint_auth rad etildi
            if e.vaqtinchalik:
                self.jurnal.topshirish_xatosi(navbat[0].partiya_id, f"tarmoq: {e}")
                return "tarmoq"
            self.jurnal.topshirish_xatosi(navbat[0].partiya_id, RAD + str(e))
            self.log(f"BANK RAD ETDI: {e}")
            return "rad"
        finally:
            if mijoz is not None:
                mijoz.yop()

    def keyingi_kutish(self) -> float:
        """Eksponensial: 5 → 10 → 20 … ≤ 300 s."""
        k = self.kutish
        self.kutish = min(self.kutish * 2, KUTISH_MAX)
        return k

    def ishlat(self, toxtatildi: Callable[[], bool],
               uxla: Callable[[float], None] = time.sleep) -> None:
        while not toxtatildi():
            holat = self.bir_aylanish(bekormi=toxtatildi)
            kut = self.keyingi_kutish() if holat == "tarmoq" else KUTISH_BOSHI
            qolgan = kut
            while qolgan > 0 and not toxtatildi():
                uxla(min(0.2, qolgan))
                qolgan -= 0.2
