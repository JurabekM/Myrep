"""1.4 — parolni o'zgartirish, shifrlangan zaxira/tiklash, sertifikat va limit ogohlantirishi."""

from __future__ import annotations

import pytest

from core.buyurtma import Zarbxona
from core.ibtido import ochiq_kalit
from core.ombor import (OmborXatosi, ombor_och, ombor_ochiq_kalit, ombor_tikla, ombor_yarat,
                        ombor_zaxira, parol_almashtir)
from core.sertifikat import KUN_MS, OGOHLANTIRISH_KUN, sertifikat_yarat
from core.surat import Surat


@pytest.fixture
def kalit(tmp_path):
    yol = tmp_path / "kalit.json"
    sk = ombor_yarat(yol, "eski-parol-1", n=4096)
    return yol, ochiq_kalit(sk)


def test_parol_almashtirish(kalit):
    yol, pk = kalit
    parol_almashtir(yol, "eski-parol-1", "yangi-parol-2")
    assert ochiq_kalit(ombor_och(yol, "yangi-parol-2")) == pk      # kalit o'sha
    with pytest.raises(OmborXatosi):
        ombor_och(yol, "eski-parol-1")
    assert not yol.with_name("kalit.json.tmp").exists()


def test_parol_almashtirish_rad_etiladi_fayl_ozgarmaydi(kalit):
    yol, _ = kalit
    asl = yol.read_bytes()
    for eski, yangi in (("notogri-parol", "yangi-parol-2"),   # eski noto'g'ri
                        ("eski-parol-1", "qisqa"),            # yangi juda qisqa
                        ("eski-parol-1", "eski-parol-1")):    # o'zgarmagan
        with pytest.raises(OmborXatosi):
            parol_almashtir(yol, eski, yangi)
        assert yol.read_bytes() == asl


def test_zaxira_va_tiklash(kalit, tmp_path):
    yol, pk = kalit
    z = tmp_path / "zaxira" / "k.json"
    z.parent.mkdir()
    assert ombor_zaxira(yol, z) == pk
    with pytest.raises(OmborXatosi):
        ombor_zaxira(yol, yol)                       # o'zining ustiga emas
    yangi = tmp_path / "yangi_profil" / "kalit.json"
    with pytest.raises(OmborXatosi):
        ombor_tikla(z, yangi, "notogri-parol")       # noto'g'ri parol — fayl yaratilmaydi
    assert not yangi.exists()
    sk = ombor_tikla(z, yangi, "eski-parol-1")
    assert ochiq_kalit(sk) == pk == ombor_ochiq_kalit(yangi)
    with pytest.raises(OmborXatosi):
        ombor_tikla(z, yangi, "eski-parol-1")        # mavjud kalit ustiga yozilmaydi


def test_sertifikat_ogohlantirishi(kalitlar):
    zsk, zpk, bsk, bpk = kalitlar
    boshi, oxiri = 1_000 * KUN_MS, 2_000 * KUN_MS
    s = sertifikat_yarat(bsk, bpk, zpk, bytes(16), "T", 1000, boshi, oxiri)
    assert s.ogohlantirish(oxiri - (OGOHLANTIRISH_KUN + 1) * KUN_MS) is None
    m = s.ogohlantirish(oxiri - 10 * KUN_MS)
    assert m and "10 kundan keyin" in m
    assert "soatdan keyin" in s.ogohlantirish(oxiri - 5 * 3_600_000)
    assert s.ogohlantirish(oxiri + 1) is None        # muddati o'tgan — muammo(), ogohlantirish emas
    assert s.ogohlantirish(boshi - 1) is None


def test_zarbxona_ogohlantirishlari(tmp_path, kalitlar):
    zsk, zpk, bsk, bpk = kalitlar
    hozir = 1_800_000_000_000
    s = sertifikat_yarat(bsk, bpk, zpk, bytes(16), "T", 10_000, hozir - KUN_MS,
                         hozir + 5 * KUN_MS)
    s.yoz(tmp_path / "s.aqcert")
    z = Zarbxona(tmp_path / "p", zsk, soat_ms=lambda: hozir)
    try:
        z.sertifikat_import(tmp_path / "s.aqcert")
        q = z.ogohlantirishlar()
        assert len(q) == 1 and "5 kundan keyin" in q[0]
        b = z.buyurtma_yarat(9_500, "Q", "", Surat(rejim="cheklovsiz"))
        z.buyurtmani_bajar(b.buyurtma_id)
        q = z.ogohlantirishlar()
        assert len(q) == 2 and "95 %" in q[1] and "500 so'm" in q[1]
    finally:
        z.yop()
