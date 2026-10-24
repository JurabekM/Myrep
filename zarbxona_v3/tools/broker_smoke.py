"""Haqiqiy MQTT broker ustida sinov (SPEC §18.2 A4). Bulutdagi testlar brokerni SINAMAYDI.

1) Kanal rejimi (default) — AETHER-Q ham, bank ham kerak emas:
       python tools/broker_smoke.py [--broker broker.hivemq.com] [--port 1883]
   Bir jarayonda ikki uch (zarbxona va «oyna») haqiqiy broker orqali wire (AQW1)
   bilan o'ralgan paketlarni almashadi. Tekshiriladi: obuna tasdig'idan keyin
   yuborish, ikki yo'nalish, begona/dublikat paketlar jim tashlanishi, kechikish.
   ⚠ Bu faqat broker + kanal + wire ni sinaydi, bank protokolini EMAS.

2) To'liq rejim — haqiqiy bank onlayn bo'lishi va aetherq_core o'rnatilgan bo'lishi kerak:
       python tools/broker_smoke.py --toliq --papka data
   Profildagi topshirilmagan partiyalarni seq tartibida haqiqiy bankka topshiradi
   (AetherQFabrika + MqttKanal) va natijani jurnalga yozadi.
"""

from __future__ import annotations

import argparse
import getpass
import secrets
import sys
import time
from pathlib import Path

ILDIZ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ILDIZ))

from core.kanal import KanalXatosi, MqttKanal  # noqa: E402
from core.protokol import B2C, C2B, Wire, bank_id  # noqa: E402


def kanal_rejimi(broker: str, port: int, soni: int) -> int:
    soxta_bank_pk = secrets.token_bytes(1952)       # faqat mavzu nomi uchun
    sid = secrets.token_bytes(8).hex()
    print(f"broker {broker}:{port} · bank_id {bank_id(soxta_bank_pk)} · sessiya {sid}")
    t0 = time.monotonic()
    try:
        mijoz = MqttKanal(broker, port, soxta_bank_pk, sid, taraf="mijoz")
        oyna = MqttKanal(broker, port, soxta_bank_pk, sid, taraf="bank")
    except KanalXatosi as e:
        print(f"XATO: {e}")
        return 1
    print(f"ikkala uch ulandi va obuna tasdiqlandi: {time.monotonic() - t0:.2f} s")
    wk = secrets.token_bytes(32)
    wm, wo = Wire(wk, C2B, B2C), Wire(wk, B2C, C2B)
    xato = 0
    rtt = []
    try:
        for i in range(soni):
            yuk = f"salom #{i}".encode()
            t = time.monotonic()
            paket = wm.ora(yuk)
            mijoz.yubor(paket)
            olindi = None
            oxiri = time.monotonic() + 15
            while olindi is None and time.monotonic() < oxiri:
                p = oyna.qabul(oxiri - time.monotonic())
                if p is not None:
                    olindi = wo.ech(p)
            if olindi != yuk:
                print(f"  #{i}: c2b yetib kelmadi")
                xato += 1
                continue
            oyna.yubor(wo.ora(b"javob " + yuk))
            javob = None
            while javob is None and time.monotonic() < oxiri:
                p = mijoz.qabul(oxiri - time.monotonic())
                if p is not None:
                    javob = wm.ech(p)
            if javob != b"javob " + yuk:
                print(f"  #{i}: b2c yetib kelmadi")
                xato += 1
                continue
            rtt.append(time.monotonic() - t)
        # begona paketlar: bosqinchi sessiya mavzusiga tashlaydi
        tashlangan0 = wo.tashlangan
        mijoz.yubor(b"AQW1" + bytes(24) + b"soxta")
        mijoz.yubor(b"qisqa")
        mijoz.yubor(paket)                            # eski (takroriy) paket
        mijoz.yubor(wm.ora(b"oxirgi"))
        oxiri = time.monotonic() + 15
        oxirgi = None
        while oxirgi is None and time.monotonic() < oxiri:
            p = oyna.qabul(oxiri - time.monotonic())
            if p is not None:
                oxirgi = wo.ech(p)
        tashlandi = wo.tashlangan - tashlangan0
        print(f"begona/takroriy paketlar tashlandi: {tashlandi} (kutilgan ≥ 3), "
              f"keyingi haqiqiy paket: {'OK' if oxirgi == b'oxirgi' else 'YETMADI'}")
        if tashlandi < 3 or oxirgi != b"oxirgi":
            xato += 1
    finally:
        mijoz.yop()
        oyna.yop()
    if rtt:
        rtt.sort()
        print(f"{len(rtt)}/{soni} aylanish · kechikish: min {rtt[0] * 1000:.0f} ms, "
              f"median {rtt[len(rtt) // 2] * 1000:.0f} ms, max {rtt[-1] * 1000:.0f} ms (o'lchangan)")
    print("NATIJA:", "BROKER KANALI ISHLAYDI" if xato == 0 else f"{xato} ta XATO")
    return 1 if xato else 0


def toliq_rejim(broker: str, port: int, papka: Path) -> int:
    from core.buyurtma import Zarbxona
    from core.ombor import ombor_och
    from core.sessiya import AetherQFabrika, SessiyaXatosi
    from core.topshirish import AvtoTopshiruvchi, Mijoz

    try:
        fabrika = AetherQFabrika()
    except SessiyaXatosi as e:
        print(f"XATO: {e}")
        return 1
    sk = ombor_och(papka / "kalit.json", getpass.getpass("zarbxona paroli: "))
    z = Zarbxona(papka, sk)
    try:
        if z.sertifikat is None:
            print("XATO: profilda sertifikat yo'q")
            return 1
        navbat = z.jurnal.topshirilmaganlar()
        print(f"topshirilmagan partiyalar: {len(navbat)}")

        def mijoz():
            k = MqttKanal(broker, port, z.sertifikat.bank_public_key)
            print(f"sessiya {k.sessiya_id}")
            return Mijoz(k, fabrika, z.sertifikat, sk, log=print)

        holat = AvtoTopshiruvchi(z.jurnal, z.partiya_papka, mijoz, log=print).bir_aylanish()
        qoldi = len(z.jurnal.topshirilmaganlar())
        print(f"NATIJA: {holat} · qoldi {qoldi}")
        return 0 if holat in ("bajarildi", "bosh") and qoldi == 0 else 1
    finally:
        z.yop()


def main() -> int:
    a = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    a.add_argument("--broker", default="broker.hivemq.com")
    a.add_argument("--port", type=int, default=1883)
    a.add_argument("--soni", type=int, default=5, help="kanal rejimida aylanishlar soni")
    a.add_argument("--toliq", action="store_true", help="haqiqiy bankka topshirish")
    a.add_argument("--papka", type=Path, default=ILDIZ / "data")
    x = a.parse_args()
    if x.toliq:
        return toliq_rejim(x.broker, x.port, x.papka)
    return kanal_rejimi(x.broker, x.port, x.soni)


if __name__ == "__main__":
    raise SystemExit(main())
