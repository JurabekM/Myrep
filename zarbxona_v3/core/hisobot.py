"""Buyurtma hisoboti (audit uchun) — HTML; ilova uni PDF ga aylantiradi (Qt QPdfWriter).
Qt'siz: sinash va boshqa formatlarga eksport qilish oson."""

from __future__ import annotations

import html
import time

from .cheklov import cheklov_tavsif
from .ibtido import iz
from .jurnal import ZANJIR_BOSH
from .tekshiruv import jurnalni_tekshir
from .zanjir import bosh_tahlil


def _v(ms: int | None) -> str:
    return "—" if not ms else time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(ms / 1000))


def _s(n: int) -> str:
    return f"{n:,}".replace(",", " ") + " so'm"


def _e(x) -> str:
    """Faqat matn tugunlari uchun (atributlarda ishlatilmaydi): <, >, & qochiriladi."""
    return html.escape(str(x), quote=False)


def buyurtma_hisoboti(z, buyurtma_id: str) -> str:
    b = z.jurnal.buyurtma(buyurtma_id)
    if b is None:
        raise KeyError("buyurtma topilmadi")
    ys = z.jurnal.partiyalar(buyurtma_id)
    h = jurnalni_tekshir(z.jurnal, z.partiya_papka, z.pk, z.sertifikat,
                         faqat={y.partiya_id for y in ys})
    s = z.sertifikat
    t = z.jurnal.tasdiq(buyurtma_id)
    th = z.tasdiq.holat(b)
    bosh = bosh_tahlil(z.jurnal.sozlama(ZANJIR_BOSH))
    qatorlar = "".join(
        f"<tr><td><code>{_e(y.partiya_id[:16])}</code></td><td>{y.birinchi_seq}..{y.oxirgi_seq}"
        f"</td><td align=right>{y.soni}</td><td align=right>{_e(_s(y.jami))}</td>"
        f"<td><code>{_e(y.ildiz[:24])}…</code></td><td>{_e(_v(y.zarb_ms))}</td>"
        f"<td>{_e(_v(y.topshirilgan_ms)) if y.topshirilgan_ms else 'yo‘q'}</td></tr>"
        for y in ys)
    muammolar = ("<p style='color:#0a7a0a'><b>" + _e(h.matn()) + "</b></p>" if h.ok else
                 "<p style='color:#b00020'><b>MUAMMO</b></p><pre>" + _e(h.matn()) + "</pre>")
    tasdiq_qator = {"kerak emas": "kerak emas", "kutilmoqda": "KUTILMOQDA",
                    "tasdiqlangan": f"tasdiqlangan · tasdiqchi {_e((t or {}).get('iz'))} · "
                                    f"{_e(_v((t or {}).get('vaqt_ms')))}",
                    "yaroqsiz": "<b style='color:#b00020'>YAROQSIZ</b>"}[th]
    return f"""<html><head><meta charset="utf-8"><style>
body {{ font-family: sans-serif; font-size: 10pt; color: #111; }}
h1 {{ font-size: 16pt; margin-bottom: 2px; }} h2 {{ font-size: 12pt; margin-top: 14px; }}
table {{ border-collapse: collapse; width: 100%; }}
td, th {{ border: 1px solid #bbb; padding: 3px 5px; }} th {{ background: #eee; }}
.xira {{ color: #555; }}
</style></head><body>
<h1>AETHER-Q Zarbxona — buyurtma hisoboti</h1>
<p class="xira">Tuzilgan: {_e(_v(z.soat_ms()))} · zarbxona kaliti izi <code>{_e(iz(z.pk))}</code></p>
<h2>Buyurtma</h2>
<table>
<tr><th align=left>ID</th><td><code>{_e(b.buyurtma_id)}</code></td></tr>
<tr><th align=left>Holat</th><td>{_e(b.holat)}</td></tr>
<tr><th align=left>Summa</th><td>{_e(_s(b.summa))} · {b.kupyura_soni} kupyura</td></tr>
<tr><th align=left>Bajarilgan</th><td>{_e(_s(b.bajarilgan_summa))} ·
 {b.bajarilgan_kupyura} kupyura</td></tr>
<tr><th align=left>Zaxira qulfi</th><td>{_e(b.zaxira_qulfi)}</td></tr>
<tr><th align=left>Cheklov</th><td>{_e(cheklov_tavsif(b.cheklov))}</td></tr>
<tr><th align=left>Yaratilgan / tugagan</th><td>{_e(_v(b.yaratilgan_ms))} /
 {_e(_v(b.tugagan_ms))}</td></tr>
<tr><th align=left>Ikki kishilik tasdiq</th><td>{tasdiq_qator}</td></tr>
</table>
<h2>Vakolat</h2>
<p>{_e(s.label) if s else "sertifikat yo'q"}{
    f" · cert_id <code>{_e(s.cert_id.hex())}</code> · bank izi <code>{_e(iz(s.bank_public_key))}</code>"
    if s else ""}</p>
<h2>Partiyalar ({len(ys)})</h2>
<table><tr><th>Partiya</th><th>Seq</th><th>Kupyura</th><th>Summa</th><th>Merkle ildizi</th>
<th>Zarb vaqti</th><th>Bankka</th></tr>{qatorlar}</table>
<h2>Tekshiruv</h2>{muammolar}
<h2>Jurnal zanjiri</h2>
<p>{f"imzolangan bosh: {bosh[0]} ta partiya · xesh <code>{_e(bosh[1].hex()[:32])}…</code>"
    if bosh else "zanjir boshi yo'q"}</p>
<p class="xira">Bu hisobot zarbxona jurnali va partiya fayllaridan avtomatik tuzilgan. Bank
qabul qilganini bankning o'z yozuvlari tasdiqlaydi.</p>
</body></html>"""
