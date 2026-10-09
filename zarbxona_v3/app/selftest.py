"""`--selftest` — Qt'siz: vaqtinchalik papkada kalit → o'z-o'zi imzolagan
sertifikat → kichik buyurtma → tekshiruv. Natija konsolga VA faylga yoziladi."""

from __future__ import annotations

import secrets
import sys
import tempfile
import time
import traceback
from pathlib import Path

from core.buyurtma import Zarbxona
from core.cheklov import cheklov_json
from core.ibtido import iz, kalit_urugdan, ochiq_kalit
from core.konstanta import VERSIYA
from core.ombor import ombor_och, ombor_yarat
from core.sertifikat import sertifikat_yarat
from core.surat import Surat
from core.tekshiruv import jurnalni_tekshir


def selftest(natija_fayli: Path) -> int:
    satrlar: list[str] = []

    def yoz(s: str) -> None:
        satrlar.append(s)
        try:
            print(s, flush=True)
        except UnicodeEncodeError:   # Windows konsoli — faylga baribir to'liq yoziladi
            print(s.encode("ascii", "replace").decode(), flush=True)

    kod = 1
    yoz(f"Zarbxona v{VERSIYA} — o'z-o'zini sinash ({time.strftime('%Y-%m-%d %H:%M:%S')})")
    try:
        with tempfile.TemporaryDirectory(prefix="zarbxona-selftest-") as t:
            papka = Path(t) / "profil"
            parol = secrets.token_hex(8)
            ombor_yarat(papka / "kalit.json", parol, n=4096)
            sk = ombor_och(papka / "kalit.json", parol)
            pk = ochiq_kalit(sk)
            yoz(f"1. kalit yaratildi va ochildi, iz: {iz(pk)}")
            bank = kalit_urugdan(secrets.token_bytes(32))
            hozir = int(time.time() * 1000)
            s = sertifikat_yarat(bank, ochiq_kalit(bank), pk, secrets.token_bytes(16),
                                 "Selftest vakolati", 1_000_000, hozir - 60_000,
                                 hozir + 3_600_000)
            s.yoz(Path(t) / "s.aqcert")
            z = Zarbxona(papka, sk)
            try:
                z.sertifikat_import(Path(t) / "s.aqcert")
                yoz("2. o'z-o'zi imzolagan sertifikat import qilindi")
                b = z.buyurtma_yarat(12_345, "AQ-RES-SELFTEST", cheklov_json(["SEED"]),
                                     Surat(rejim="cheklovsiz"), partiya_hajmi=4)
                r = z.buyurtmani_bajar(b.buyurtma_id)
                yoz(f"3. buyurtma 12 345 so'm: {r.holat}, {len(r.partiyalar)} partiya, "
                    f"{b.kupyura_soni} kupyura")
                h = jurnalni_tekshir(z.jurnal, z.partiya_papka, z.pk, z.sertifikat)
                yoz("4. tekshiruv: " + h.matn())
                kod = 0 if (r.holat == "tugadi" and h.ok) else 1
            finally:
                z.yop()
    except Exception:  # noqa: BLE001
        yoz("XATO:\n" + traceback.format_exc())
        kod = 1
    yoz("NATIJA: " + ("MUVAFFAQIYATLI" if kod == 0 else "XATO"))
    try:
        Path(natija_fayli).write_text("\n".join(satrlar) + "\n", encoding="utf-8")
        print(f"natija fayli: {natija_fayli}", flush=True)
    except OSError as e:
        print(f"natija faylga yozilmadi: {e}", file=sys.stderr)
    return kod
