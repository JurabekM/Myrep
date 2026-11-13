"""Jurnal xesh-zanjiri — jurnalni sezdirmay o'zgartirishni aniqlash.

Har partiya yozuvi o'zidan oldingi bo'g'inning xeshini o'z ichiga oladi:

    bo'g'in_i = tagged_hash(L_ZANJIR, bo'g'in_{i-1}, partiya maydonlari…)
    bo'g'in_0 dan oldingisi = 32 nol bayt

Zanjir boshi (oxirgi bo'g'in va uzunlik) zarbxona ML-DSA kaliti bilan imzolanadi.
Kalitsiz odam jurnalda yozuvni o'zgartirsa, o'chirsa yoki qo'shsa, zanjirni qayta
hisoblasa ham boshning imzosini qayta qo'ya olmaydi — tekshiruv buni topadi.

Chegara (halol): zanjir jurnalni ICHIDAN himoyalaydi. Butun jurnalni eski, o'sha
kalit imzolagan nusxasiga qaytarish (rollback) faqat tashqi nuqta bilan aniqlanadi —
masalan bankning qabul yozuvlari yoki boshning boshqa joyga eksport qilingan nusxasi.

Bu zarbxonaning ichki formati: bank protokoliga (SPEC §3.1) kirmaydi.
"""

from __future__ import annotations

import json

from .ibtido import imzo_togri, tagged_hash, u64be

L_ZANJIR = b"AETHER-Q-ZARBXONA/JURNAL-ZANJIR/v1"
L_ZANJIR_BOSH = b"AETHER-Q-ZARBXONA/JURNAL-BOSH/v1"
NOL = bytes(32)


def bogin_xeshi(oldingi: bytes, y) -> bytes:
    """`y` — PartiyaYozuvi. Faqat o'zgarmas maydonlar: topshirilgan_ms,
    topshirish_xatosi va davomiylik_ms keyin o'zgaradi yoki o'lchov — kirmaydi."""
    return tagged_hash(
        L_ZANJIR, oldingi, bytes.fromhex(y.partiya_id),
        (y.buyurtma_id or "").encode("utf-8"), bytes.fromhex(y.sert_id),
        bytes.fromhex(y.ildiz), u64be(y.soni), u64be(y.jami), u64be(y.birinchi_seq),
        u64be(y.oxirgi_seq), y.zaxira_qulfi.encode("utf-8"), y.cheklov.encode("utf-8"),
        u64be(y.zarb_ms), y.fayl.encode("utf-8"))


def bosh_xabari(tartib: int, xesh: bytes) -> bytes:
    return tagged_hash(L_ZANJIR_BOSH, u64be(tartib), xesh)


def bosh_json(tartib: int, xesh: bytes, imzo: bytes) -> str:
    return json.dumps({"tartib": tartib, "xesh": xesh.hex(), "imzo": imzo.hex()},
                      separators=(",", ":"))


def bosh_tahlil(s: str | None) -> tuple[int, bytes, bytes] | None:
    if not s:
        return None
    try:
        d = json.loads(s)
        return int(d["tartib"]), bytes.fromhex(d["xesh"]), bytes.fromhex(d["imzo"])
    except (ValueError, KeyError, TypeError):
        return None


def zanjirni_tekshir(yozuvlar, boginlar, bosh: str | None, versiya: str | None,
                     zarbxona_pk: bytes) -> list[tuple[str, str, str]]:
    """Qaytaradi: muammolar ro'yxati (qayerda, qoida, izoh). Bo'sh — toza.

    `yozuvlar` — partiyalar (birinchi_seq bo'yicha), `boginlar` — (tartib,
    partiya_id, oldingi_hex, xesh_hex) (tartib bo'yicha).
    """
    m: list[tuple[str, str, str]] = []
    if versiya is None:
        if yozuvlar:
            m.append(("jurnal", "zanjir", "jurnalda xesh-zanjir yo'q (belgisi o'chirilgan)"))
        return m
    x = NOL
    for i, y in enumerate(yozuvlar):
        kutilgan = bogin_xeshi(x, y)
        if i >= len(boginlar):
            m.append((f"jurnal #{i}", "zanjir",
                      f"partiya {y.partiya_id[:12]} uchun zanjir bo'g'ini yo'q"))
            return m
        tartib, pid, old, xesh = boginlar[i]
        if tartib != i or pid != y.partiya_id or old != x.hex() or xesh != kutilgan.hex():
            m.append((f"jurnal #{i}", "zanjir",
                      f"partiya {y.partiya_id[:12]}: yozuv zanjirga mos emas — o'zgartirilgan, "
                      "o'chirilgan yoki orasiga qo'shilgan"))
            return m
        x = kutilgan
    if len(boginlar) > len(yozuvlar):
        m.append(("jurnal", "zanjir", f"zanjirda {len(boginlar) - len(yozuvlar)} ta ortiqcha "
                                      "bo'g'in — partiya yozuvi o'chirilgan"))
        return m
    b = bosh_tahlil(bosh)
    if b is None:
        if yozuvlar:
            m.append(("jurnal", "zanjir-bosh", "zanjir boshi yo'q yoki buzilgan"))
        return m
    tartib, xesh, imzo = b
    if not imzo_togri(zarbxona_pk, imzo, bosh_xabari(tartib, xesh)):
        m.append(("jurnal", "zanjir-bosh", "zanjir boshining imzosi noto'g'ri"))
    elif tartib != len(yozuvlar) or xesh != x:
        m.append(("jurnal", "zanjir-bosh",
                  f"imzolangan boshda {tartib} ta partiya, jurnalda {len(yozuvlar)} — "
                  "yozuvlar o'chirilgan yoki qo'shilgan"))
    return m
