"""3.5 — kupyura isboti paketi (JSON/QR) va oflayn tekshiruv; 3.4 — buyurtma hisoboti."""

from __future__ import annotations

import json
import os
import subprocess
import sys

import pytest

from conftest import ILDIZ
from core.buyurtma import Zarbxona
from core.isbot import isbot_matni, isbot_paketi, isbot_tekshir, qr_png
from core.partiya import ZarbKirishi, nominallarga_bol, partiya_oqi, zarb_qil
from core.surat import Surat

HOZIR = 1_800_000_000_000


@pytest.fixture(scope="module")
def partiya(kalitlar):
    return zarb_qil(ZarbKirishi(nominallarga_bol(1_234_567), bytes(16), "AQ-RES-1", 101,
                                '{"categories":["SEED"]}'), kalitlar[0], zarb_ms=HOZIR)


def test_har_kupyura_isboti_togri(partiya, kalitlar):
    zpk = kalitlar[1]
    for i in (0, 1, 127, 128, partiya.soni - 1):
        ok, izoh = isbot_tekshir(isbot_paketi(partiya, i))
        assert ok and "imzo tekshirilmadi" in izoh
        ok, izoh = isbot_tekshir(isbot_matni(isbot_paketi(partiya, i, toliq=True)), zpk)
        assert ok and "imzosi to'g'ri" in izoh


@pytest.mark.parametrize("maydon,qiymat", [("d", 1000), ("s", 999), ("o", "BOSQINCHI"),
                                           ("i", 3), ("n", 257)])
def test_ozgartirilgan_paket_rad(partiya, maydon, qiymat):
    d = isbot_paketi(partiya, 5)
    d[maydon] = qiymat
    ok, izoh = isbot_tekshir(d)
    assert not ok and "tegishli emas" in izoh


def test_soxta_imzo_va_boshqa_kalit(partiya, kalitlar):
    d = isbot_paketi(partiya, 0, toliq=True)
    assert not isbot_tekshir(d, kalitlar[3])[0]                    # bank kaliti ≠ zarbxona
    d["jami"] += 1                                                  # imzo xabari o'zgaradi
    ok, izoh = isbot_tekshir(d, kalitlar[1])
    assert not ok and "imzo" in izoh


def test_buzilgan_paket(partiya):
    for yomon in ("{}", "emas json", json.dumps({"v": "boshqa"}),
                  json.dumps({**isbot_paketi(partiya, 0), "p": "!!!"})):
        assert not isbot_tekshir(yomon)[0]


def test_maxfiy_malumot_yoq(partiya):
    d = isbot_paketi(partiya, 0, toliq=True)
    assert not ({"muhr", "nazorat", "sealed_core"} & set(d))


def test_qr_png(partiya, tmp_path):
    pytest.importorskip("segno")
    d = isbot_paketi(partiya, partiya.soni - 1)
    qr_png(d, tmp_path / "q.png")
    b = (tmp_path / "q.png").read_bytes()
    assert b[:8] == b"\x89PNG\r\n\x1a\n" and len(b) > 500
    assert len(isbot_matni(d)) < 1500                              # QR sig'imiga bemalol


def test_isbot_tekshir_vositasi(partiya, kalitlar, tmp_path):
    f = tmp_path / "isbot.json"
    f.write_text(isbot_matni(isbot_paketi(partiya, 7, toliq=True)), encoding="utf-8")
    k = tmp_path / "k.json"
    k.write_text(json.dumps({"public_key": kalitlar[1].hex()}), encoding="utf-8")
    env = {**os.environ, "PYTHONIOENCODING": "utf-8"}
    r = subprocess.run([sys.executable, "tools/isbot_tekshir.py", str(f), "--kalit", str(k)],
                       cwd=ILDIZ, capture_output=True, text=True, encoding="utf-8", env=env)
    assert r.returncode == 0 and "TEGISHLI" in r.stdout
    d = json.loads(f.read_text(encoding="utf-8"))
    d["d"] = 1
    r = subprocess.run([sys.executable, "tools/isbot_tekshir.py", "-"], cwd=ILDIZ,
                       input=json.dumps(d), capture_output=True, text=True, encoding="utf-8",
                       env=env)
    assert r.returncode == 1 and "RAD" in r.stdout


def test_buyurtma_hisoboti(tmp_path, kalitlar, sertifikat):
    from core.hisobot import buyurtma_hisoboti
    sertifikat.yoz(tmp_path / "s.aqcert")
    z = Zarbxona(tmp_path / "p", kalitlar[0], soat_ms=lambda: HOZIR)
    try:
        z.sertifikat_import(tmp_path / "s.aqcert")
        b = z.buyurtma_yarat(12_345, "AQ-<RES>&1", "", Surat(rejim="cheklovsiz"),
                             partiya_hajmi=4)
        z.buyurtmani_bajar(b.buyurtma_id)
        h = buyurtma_hisoboti(z, b.buyurtma_id)
        assert b.buyurtma_id in h and "TOZA" in h and "12 345 so'm" in h
        assert "AQ-&lt;RES&gt;&amp;1" in h and "AQ-<RES>" not in h       # HTML qochirilgan
        assert h.count("<tr><td><code>") == len(z.jurnal.partiyalar())
        # partiya fayli buzilsa hisobot MUAMMO ko'rsatadi
        f = z.partiya_papka / z.jurnal.partiyalar()[0].fayl
        import sqlite3
        db = sqlite3.connect(f)
        with db:
            db.execute("UPDATE notes SET owner='X'")
        db.close()
        assert "MUAMMO" in buyurtma_hisoboti(z, b.buyurtma_id)
        with pytest.raises(KeyError):
            buyurtma_hisoboti(z, "yoq")
    finally:
        z.yop()


def test_partiya_faylidan_isbot(tmp_path, partiya, kalitlar):
    from core.partiya import partiya_yoz
    p = partiya_oqi(partiya_yoz(partiya, tmp_path))
    assert isbot_tekshir(isbot_paketi(p, 3, toliq=True), kalitlar[1])[0]
