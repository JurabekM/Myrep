"""Demo bank — §11 qabul qoidalarini takrorlaydi va §13.5 oqimini server tomonidan
o'ynaydi. Testlarda (`SoxtaBank`) va ilovaning DEMO rejimida (`DemoBank`) ishlatiladi.

Ataylab `core.tekshiruv` ishlatilmaydi: bank zarbxonaga ishonmaydi va hammasini
o'zi hisoblaydi — shu tufayli bu tekshiruvchidan mustaqil ikkinchi fikr.

⚠ HAQIQIY BANK EMAS. Sessiya `SoxtaFabrika` — shifrsiz; bank kaliti demo papkasida
OCHIQ saqlanadi. Faqat ko'rsatish, o'qitish va sinov uchun.
"""

from __future__ import annotations

import json
import os
import secrets
import threading
import time
from collections.abc import Callable
from dataclasses import dataclass, field
from pathlib import Path

from .cheklov import cheklov_xeshi
from .ibtido import imzo_togri, kalit_urugdan, ochiq_kalit
from .kanal import XotiraKanali
from .konstanta import MAX_KUPYURA, XAZINA
from .merkle import isbot_ajrat, isbot_togri, qavatlar
from .partiya import imzo_xabari
from .protokol import B2C, C2B, Wire, kodla, mint_auth_xesh, och, qator_och
from .sertifikat import Sertifikat, sertifikat_yarat
from .sessiya import SoxtaBankHandshake, SoxtaFabrika


class RadEtildi(Exception):
    pass


@dataclass
class BankHolati:
    sertlar: dict[bytes, Sertifikat] = field(default_factory=dict)
    chiqarilgan: dict[bytes, int] = field(default_factory=dict)
    qabul: dict[bytes, dict] = field(default_factory=dict)       # batch_id → xulosa
    qulflar: dict[str, int] = field(default_factory=dict)        # qulf → bo'sh summa
    hozir_ms: int = 1_800_000_000_000
    qabul_tartibi: list[bytes] = field(default_factory=list)
    soat: Callable[[], int] | None = None            # bo'lsa hozir_ms o'rniga
    saqla: Callable[[], None] | None = None           # har qabuldan keyin
    qulf: threading.Lock = field(default_factory=threading.Lock, repr=False)

    def hozir(self) -> int:
        return self.soat() if self.soat else self.hozir_ms

    def qabul_qil(self, h: dict, qatorlar: list) -> dict:
        """§11 qoidalari 1–8. Rad etsa — hech narsa o'zgarmaydi. Oqimlar orasida xavfsiz."""
        with self.qulf:
            x = self._qabul_qil(h, qatorlar)
        if self.saqla:
            self.saqla()
        return x

    def _qabul_qil(self, h: dict, qatorlar: list) -> dict:
        hozir = self.hozir()
        cid = bytes.fromhex(h["cert_id"])
        s = self.sertlar.get(cid)
        if s is None or not s.imzo_togri():
            raise RadEtildi("sertifikat bankda yo'q yoki imzosi noto'g'ri")
        if not s.valid_from_ms <= hozir <= s.valid_until_ms:
            raise RadEtildi("sertifikat muddati ichida emas")
        n = int(h["note_count"])
        if not 1 <= n <= MAX_KUPYURA or len(qatorlar) != n:
            raise RadEtildi("kupyuralar soni noto'g'ri")
        if sum(q.nominal for q in qatorlar) != int(h["total"]):
            raise RadEtildi("nominallar yig'indisi total ga teng emas")
        if int(h["total"]) > s.limit_amount - self.chiqarilgan.get(cid, 0):
            raise RadEtildi("sertifikat limiti yetmaydi")
        bid = bytes.fromhex(h["batch_id"])
        if bid in self.qabul:
            raise RadEtildi("bu partiya allaqachon qabul qilingan")
        qulf = h["reserve_lock"]
        if qulf not in self.qulflar or int(h["total"]) > self.qulflar[qulf]:
            raise RadEtildi("zaxira qulfi yo'q yoki yetmaydi")
        root = bytes.fromhex(h["root"])
        msg = imzo_xabari(root, bid, n, int(h["total"]), qulf, int(h["minted_ms"]))
        if not imzo_togri(s.mint_public_key, bytes.fromhex(h["signature"]), msg):
            raise RadEtildi("zarbxona imzosi noto'g'ri")
        cx = cheklov_xeshi(h["constraints"])
        barglar = [q.barg() for q in qatorlar]
        q_ = qavatlar(barglar)
        if q_[-1][0] != root:
            raise RadEtildi("Merkle ildizi mos emas")
        for i, q in enumerate(qatorlar):
            if (q.batch_id != bid or q.egasi != XAZINA or q.nominal <= 0
                    or q.seq != int(h["first_seq"]) + i or q.cheklov_xeshi != cx):
                raise RadEtildi(f"kupyura #{i} qoidaga mos emas")
            yol = isbot_ajrat(q.isbot)
            if yol is None or not isbot_togri(barglar[i], yol, i, n, root):
                raise RadEtildi(f"kupyura #{i} isboti noto'g'ri")
        # hammasi o'tdi — endi o'zgartiramiz
        self.chiqarilgan[cid] = self.chiqarilgan.get(cid, 0) + int(h["total"])
        self.qulflar[qulf] -= int(h["total"])
        x = {"batch_id": h["batch_id"], "note_count": n, "total": int(h["total"]),
             "accepted_ms": hozir}
        self.qabul[bid] = x
        self.qabul_tartibi.append(bid)
        return x


class SoxtaBank(threading.Thread):
    """Bitta sessiyani xizmat qiladi (XotiraKanali bank uchi)."""

    def __init__(self, kanal, bank_pk: bytes, holat: BankHolati, *,
                 notogri_id: bool = False, hodisa_yubor: bool = False,
                 dublikat: bool = False, javobsiz_op: str | None = None):
        super().__init__(daemon=True)
        self.kanal, self.pk, self.h = kanal, bank_pk, holat
        self.notogri_id, self.hodisa_yubor, self.dublikat = notogri_id, hodisa_yubor, dublikat
        self.javobsiz_op = javobsiz_op
        self.oplar: list[str] = []
        self.bolaklar = 0
        self.abort_soni = 0
        self.xato: BaseException | None = None
        self.start()

    def run(self):
        try:
            self._xizmat()
        except BaseException as e:  # noqa: BLE001
            self.xato = e

    def _xizmat(self):
        hs = SoxtaBankHandshake(self.pk)
        p = self.kanal.qabul(10)
        if p is None:
            return
        self.kanal.yubor(hs.recv(p))
        sess = hs.take_session()
        nonce, wk = secrets.token_bytes(32), secrets.token_bytes(32)
        self.kanal.yubor(sess.seal(kodla({"v": 1, "op": "challenge", "id": 0,
                                          "nonce": nonce.hex(), "wire_key": wk.hex()})))
        wire = Wire(wk, yuborish=B2C, qabul=C2B)
        sert: Sertifikat | None = None
        ochiq: dict | None = None

        def javob(sid, ok=True, data=None, code="", error=""):
            if self.notogri_id and sid > 1:
                sid += 100
            d = {"v": 1, "id": sid, "ok": ok}
            if ok:
                d["data"] = data or {}
            else:
                d.update(code=code, error=error)
            if self.hodisa_yubor:
                self.kanal.yubor(wire.ora(sess.seal(kodla({"v": 1, "op": "event",
                                                           "kind": "ping"}))))
            pk = wire.ora(sess.seal(kodla(d)))
            self.kanal.yubor(pk)
            if self.dublikat:
                self.kanal.yubor(pk)        # QoS1 dublikati

        while True:
            p = self.kanal.qabul(10)
            if p is None:
                return
            y = wire.ech(p)
            if y is None:
                continue
            _, pt = sess.open(y)
            m = och(pt)
            op, sid = m.get("op"), m.get("id")
            self.oplar.append(op)
            if op == "bye":
                return
            if op == self.javobsiz_op:
                continue
            if op == "mint_auth":
                cid = bytes.fromhex(m["cert_id"])
                s = self.h.sertlar.get(cid)
                if s is None or not imzo_togri(s.mint_public_key, bytes.fromhex(m["signature"]),
                                               mint_auth_xesh(self.pk, nonce, cid)):
                    javob(sid, False, code="unauthorized", error="mint_auth rad etildi")
                    return
                sert = s
                c = self.h.chiqarilgan.get(cid, 0)
                javob(sid, data={"cert_id": m["cert_id"], "label": s.label,
                                 "limit": s.limit_amount, "minted_total": c,
                                 "remaining": s.limit_amount - c, "chunk_notes": 250})
                continue
            if sert is None:
                javob(sid, False, code="unauthorized", error="avval mint_auth")
                return
            if op == "batch_begin":
                if ochiq is not None:
                    javob(sid, False, code="bank_error", error="oldingi partiya ochiq")
                    continue
                if bytes.fromhex(m["batch_id"]) in self.h.qabul:
                    javob(sid, False, code="bank_error",
                          error="bu partiya allaqachon qabul qilingan")
                    continue
                ochiq = {**m, "cert_id": sert.cert_id.hex(), "qatorlar": []}
                javob(sid, data={"expect_notes": m["note_count"], "chunk_notes": 250})
            elif op == "batch_chunk":
                if ochiq is None:
                    javob(sid, False, code="bank_error", error="ochiq partiya yo'q")
                    continue
                if len(m["rows"]) > 250:
                    javob(sid, False, code="bad_request", error="bo'lak 250 dan katta")
                    continue
                n0 = len(ochiq["qatorlar"])
                ochiq["qatorlar"] += [qator_och(r, n0 + i) for i, r in enumerate(m["rows"])]
                self.bolaklar += 1
                javob(sid, data={"received": len(ochiq["qatorlar"])})
            elif op == "batch_commit":
                if ochiq is None:
                    javob(sid, False, code="bank_error", error="ochiq partiya yo'q")
                    continue
                try:
                    x = self.h.qabul_qil(ochiq, ochiq["qatorlar"])
                except RadEtildi as e:
                    ochiq = None
                    javob(sid, False, code="bank_error", error=str(e))
                    continue
                ochiq = None
                javob(sid, data=x)
            elif op == "batch_abort":
                ochiq = None
                self.abort_soni += 1
                javob(sid, data={"aborted": True})
            else:
                javob(sid, False, code="bad_request", error=f"noma'lum op {op}")


# --- ilova DEMO rejimi ----------------------------------------------------------------

DEMO_BELGI = "DEMO BANK"
DEMO_LIMIT = 100_000_000
DEMO_QULF_SUMMA = 50_000_000
KUN_MS = 86_400_000


class DemoBank:
    """Profil ichidagi `demo_bank/` papkasida yashaydigan soxta bank.

    Holat (bank kaliti urug'i — OCHIQ, sertifikatlar, qabul qilingan partiyalar,
    zaxira qulflari) `holat.json` ga atomik yoziladi: qabul qilingan partiya dastur
    qayta ochilganda ham «allaqachon qabul qilingan» bo'lib qoladi.
    """

    def __init__(self, papka: Path, soat_ms: Callable[[], int] = lambda: int(time.time() * 1000)):
        self.papka = Path(papka)
        self.papka.mkdir(parents=True, exist_ok=True)
        self.yol = self.papka / "holat.json"
        self.soat_ms = soat_ms
        self._yozish = threading.Lock()
        self.holat = BankHolati(soat=soat_ms, saqla=self.saqla)
        if self.yol.exists():
            d = json.loads(self.yol.read_text(encoding="utf-8"))
            urug = bytes.fromhex(d["bank_urug"])
            for sd in d.get("sertlar", []):
                s = Sertifikat.lugatdan(sd)
                self.holat.sertlar[s.cert_id] = s
            self.holat.chiqarilgan = {bytes.fromhex(k): int(v)
                                      for k, v in d.get("chiqarilgan", {}).items()}
            self.holat.qabul = {bytes.fromhex(k): v for k, v in d.get("qabul", {}).items()}
            self.holat.qabul_tartibi = [bytes.fromhex(x) for x in d.get("qabul_tartibi", [])]
            self.holat.qulflar = {k: int(v) for k, v in d.get("qulflar", {}).items()}
        else:
            urug = secrets.token_bytes(32)
        self.sk = kalit_urugdan(urug)
        self.pk = ochiq_kalit(self.sk)
        self._urug = urug
        if not self.yol.exists():
            self.saqla()

    @staticmethod
    def bormi(profil: Path) -> bool:
        return (Path(profil) / "demo_bank" / "holat.json").exists()

    def saqla(self) -> None:
        h = self.holat
        with h.qulf:
            d = {
                "izoh": "DEMO BANK — haqiqiy emas. Kalit urug'i ataylab ochiq saqlanadi.",
                "bank_urug": self._urug.hex(),
                "sertlar": [s.lugat() for s in h.sertlar.values()],
                "chiqarilgan": {k.hex(): v for k, v in h.chiqarilgan.items()},
                "qabul": {k.hex(): v for k, v in h.qabul.items()},
                "qabul_tartibi": [x.hex() for x in h.qabul_tartibi],
                "qulflar": dict(h.qulflar),
            }
        with self._yozish:
            tmp = self.yol.with_name(self.yol.name + ".tmp")
            tmp.write_text(json.dumps(d, indent=1, ensure_ascii=False), encoding="utf-8")
            os.replace(tmp, self.yol)

    # --- bank operatori amallari ---------------------------------------------------

    def sertifikat_ber(self, mint_pk: bytes, limit: int = DEMO_LIMIT,
                       kun: int = 365) -> Sertifikat:
        hozir = self.soat_ms()
        s = sertifikat_yarat(self.sk, self.pk, mint_pk, secrets.token_bytes(16),
                             f"{DEMO_BELGI} — haqiqiy emas", limit, hozir - 60_000,
                             hozir + kun * KUN_MS)
        with self.holat.qulf:
            self.holat.sertlar[s.cert_id] = s
        self.saqla()
        return s

    def qulf_och(self, summa: int = DEMO_QULF_SUMMA) -> str:
        if summa <= 0:
            raise ValueError("qulf summasi musbat bo'lsin")
        with self.holat.qulf:
            nom = f"AQ-DEMO-{len(self.holat.qulflar) + 1:04d}"
            self.holat.qulflar[nom] = summa
        self.saqla()
        return nom

    def qulflar(self) -> dict[str, int]:
        with self.holat.qulf:
            return dict(self.holat.qulflar)

    def qabul_qilinganlar(self) -> list[dict]:
        with self.holat.qulf:
            return [self.holat.qabul[b] for b in self.holat.qabul_tartibi][::-1]

    def chiqarilgan(self, cert_id: bytes) -> int:
        with self.holat.qulf:
            return self.holat.chiqarilgan.get(cert_id, 0)

    # --- onlayn sessiya (xotira kanali, MQTT'siz) -----------------------------------

    def mijoz(self, zarbxona_sk, sert: Sertifikat, log=None, bekormi=None):
        """Yangi sessiya: bank tomoni alohida oqimda. Qaytaradi: topshirish.Mijoz."""
        from .topshirish import Mijoz
        mk, bk = XotiraKanali.juft()
        SoxtaBank(bk, self.pk, self.holat)
        return Mijoz(mk, SoxtaFabrika(), sert, zarbxona_sk, muddat=30, hs_muddat=30, log=log,
                     bekormi=bekormi)


class DemoXatosi(RuntimeError):
    pass


def demo_tayyorla(z) -> DemoBank:
    """Profilni DEMO rejimiga tayyorlaydi: demo bank, sertifikat, zaxira qulfi.

    Himoya: haqiqiy bank sertifikati bor yoki allaqachon partiyalari bo'lgan
    (demo bo'lmagan) profil hech qachon demo'ga aylantirilmaydi.
    """
    papka = Path(z.papka) / "demo_bank"
    if not DemoBank.bormi(z.papka):
        if z.sertifikat is not None:
            raise DemoXatosi("bu profilda haqiqiy bank sertifikati bor — demo rejimi uchun "
                             "alohida papka ishlating (default: data_demo)")
        if z.jurnal.partiyalar():
            raise DemoXatosi("bu profilda zarb qilingan partiyalar bor — demo rejimi uchun "
                             "alohida papka ishlating")
    db = DemoBank(papka, soat_ms=z.soat_ms)
    s = z.sertifikat
    if s is not None and s.bank_public_key != db.pk:
        raise DemoXatosi("profil sertifikati demo bankniki emas — demo rejimi ishlamaydi")
    if s is None or s.muammo(z.pk, z.soat_ms()) is not None:
        yangi = db.sertifikat_ber(z.pk)
        yangi.yoz(papka / "sertifikat.aqcert")
        z.sertifikat_import(papka / "sertifikat.aqcert")
    if not db.qulflar():
        db.qulf_och()
    return db
