"""2.4 — GUI'siz CLI: holat, zarb, davom, tasdiqla, buyurtmalar, tekshir (subprocess)."""

from __future__ import annotations

import os
import signal
import sqlite3
import subprocess
import sys
import time

import pytest

from conftest import ILDIZ
from core.buyurtma import Zarbxona
from core.ombor import ombor_yarat

PAROL = "cli-parol-123"
TPAROL = "tasdiqchi-cli-1"


@pytest.fixture
def profil(tmp_path, kalitlar, sertifikat):
    papka = tmp_path / "p"
    sk = ombor_yarat(papka / "kalit.json", PAROL, n=4096)
    from core.ibtido import ochiq_kalit
    from core.sertifikat import sertifikat_yarat
    zsk, zpk, bsk, bpk = kalitlar
    s = sertifikat_yarat(bsk, bpk, ochiq_kalit(sk), bytes(16), "CLI vakolati", 50_000_000,
                         int(time.time() * 1000) - 60_000, int(time.time() * 1000) + 10**10)
    s.yoz(tmp_path / "s.aqcert")
    z = Zarbxona(papka, sk)
    z.sertifikat_import(tmp_path / "s.aqcert")
    z.yop()
    return papka, sk


def cli(*args, env=None, **kw):
    e = {k: v for k, v in os.environ.items() if k != "ZARBXONA_TASDIQCHI_PAROL"}
    e.update({"PYTHONIOENCODING": "utf-8", "ZARBXONA_PAROL": PAROL, **(env or {})})
    return subprocess.run([sys.executable, "run.py", *args], cwd=ILDIZ, capture_output=True,
                          text=True, encoding="utf-8", timeout=120, env=e,
                          stdin=subprocess.DEVNULL, **kw)


def test_holat_zarb_tekshir(profil):
    papka, _ = profil
    r = cli("holat", "--papka", str(papka))
    assert r.returncode == 0, r.stdout + r.stderr
    assert "CLI vakolati" in r.stdout and "partiyalar 0" in r.stdout
    r = cli("zarb", "--papka", str(papka), "--summa", "12345", "--qulf", "AQ-RES-CLI",
            "--hajm", "4", "--surat", "cheklovsiz", "--toifalar", "seed,fuel")
    assert r.returncode == 0, r.stdout + r.stderr
    assert "TUGADI" in r.stdout and "partiya yopildi" in r.stdout
    r = cli("tekshir", "--papka", str(papka))
    assert r.returncode == 0 and "TOZA" in r.stdout
    r = cli("buyurtmalar", "--papka", str(papka))
    assert "tugadi" in r.stdout and "12 345" in r.stdout


def test_tekshir_muammoni_topadi_va_notogri_parol(profil):
    papka, _ = profil
    cli("zarb", "--papka", str(papka), "--summa", "5000", "--qulf", "Q", "--surat",
        "cheklovsiz")
    f = next((papka / "partiyalar").glob("*.aqbatch"))
    db = sqlite3.connect(f)
    with db:
        db.execute("UPDATE notes SET denomination=10")
    db.close()
    r = cli("tekshir", "--papka", str(papka))
    assert r.returncode == 1 and "MUAMMO" in r.stdout
    r = cli("holat", "--papka", str(papka), env={"ZARBXONA_PAROL": "notogri-parol"})
    assert r.returncode == 1 and "parol" in r.stdout


def test_ikki_kishilik_tasdiq_cli(profil):
    papka, sk = profil
    z = Zarbxona(papka, sk)
    z.tasdiq.tasdiqchi_yarat(TPAROL, chegara=10_000, n=4096)
    z.yop()
    r = cli("zarb", "--papka", str(papka), "--summa", "20000", "--qulf", "Q", "--surat",
            "cheklovsiz")
    assert r.returncode == 3 and "tasdig'i kerak" in r.stdout      # terminal yo'q, env yo'q
    bid = r.stdout.split("buyurtma saqlandi: ")[1].split()[0]
    r = cli("tasdiqla", "--papka", str(papka), "--buyurtma", bid,
            env={"ZARBXONA_TASDIQCHI_PAROL": "xato-parol-9"})
    assert r.returncode == 1 and "parol" in r.stdout
    r = cli("tasdiqla", "--papka", str(papka), "--buyurtma", bid,
            env={"ZARBXONA_TASDIQCHI_PAROL": TPAROL})
    assert r.returncode == 0 and "tasdiqlandi" in r.stdout
    r = cli("davom", "--papka", str(papka), "--buyurtma", bid)
    assert r.returncode == 0 and "TUGADI" in r.stdout


@pytest.mark.skipif(os.name == "nt", reason="SIGINT subprocess'ga POSIX'da yuboriladi")
def test_ctrl_c_toxtatadi_va_davom_etadi(profil):
    papka, _ = profil
    e = {**os.environ, "PYTHONIOENCODING": "utf-8", "ZARBXONA_PAROL": PAROL}
    p = subprocess.Popen([sys.executable, "run.py", "zarb", "--papka", str(papka), "--summa",
                          str(5000 * 40), "--qulf", "Q", "--hajm", "10", "--surat", "tezlik:8",
                          "--sovutish", "0:0"], cwd=ILDIZ, stdout=subprocess.PIPE,
                         stderr=subprocess.STDOUT, text=True, encoding="utf-8", env=e,
                         stdin=subprocess.DEVNULL)
    time.sleep(3.5)                       # ~2 partiya (10 kupyura / 8 s·¹)
    p.send_signal(signal.SIGINT)
    out, _ = p.communicate(timeout=30)
    assert p.returncode == 3, out
    assert "TO'XTATILDI" in out and "partiya yopildi" in out
    bid = out.split("buyurtma ")[1].split(":")[0]
    r = cli("davom", "--papka", str(papka), "--buyurtma", bid, "--surat", "cheklovsiz")
    assert r.returncode == 0 and "TUGADI" in r.stdout
    assert cli("tekshir", "--papka", str(papka)).returncode == 0


def test_cli_qt_yuklamaydi(profil):
    papka, _ = profil
    kod = ("import sys; sys.path.insert(0,'.'); from app.main import main; "
           f"r=main(['holat','--papka',{str(papka)!r}]); "
           "assert 'PySide6' not in sys.modules; raise SystemExit(r)")
    r = subprocess.run([sys.executable, "-c", kod], cwd=ILDIZ, capture_output=True, text=True,
                       encoding="utf-8", timeout=120,
                       env={**os.environ, "ZARBXONA_PAROL": PAROL, "PYTHONIOENCODING": "utf-8"})
    assert r.returncode == 0, r.stdout + r.stderr


def test_notogri_surat():
    from app.cli import surat_tahlil
    assert surat_tahlil("davomiylik:30", 0.5, "10:1").davomiylik == 30
    with pytest.raises(ValueError):
        surat_tahlil("tez", 0.25, "0:0")
    with pytest.raises(ValueError):
        surat_tahlil("tezlik:0", 0.25, "0:0")


def test_nul_stdin_interaktiv_emas(monkeypatch):
    """Windows regressiyasi: DEVNULL (NUL) stdin isatty()=True beradi — chiqish ushlangan
    bo'lsa parol SO'RALMAYDI (getpass osilib qolardi)."""
    import app.cli as c

    class Tty:
        def __init__(self, t):
            self.t = t

        def isatty(self):
            return self.t
    monkeypatch.delenv("ZARBXONA_TASDIQCHI_PAROL", raising=False)
    monkeypatch.setattr(c.getpass, "getpass", lambda *_: pytest.fail("getpass chaqirildi"))
    monkeypatch.setattr(c.sys, "stdin", Tty(True))
    monkeypatch.setattr(c.sys, "stdout", Tty(False))
    assert c.interaktiv() is False
    assert c._parol("ZARBXONA_TASDIQCHI_PAROL", "?") is None
    monkeypatch.setattr(c.sys, "stdout", Tty(True))
    monkeypatch.setattr(c.getpass, "getpass", lambda *_: "terminaldan")
    assert c._parol("ZARBXONA_TASDIQCHI_PAROL", "?") == "terminaldan"


def test_pico_cli_sozlash_zarb_va_qaytish(profil, tmp_path):
    """4.x: `pico sozla --import` (soxta Pico), keyin zarb Pico PIN bilan, `pico holat`,
    `pico qaytish`."""
    papka, _ = profil
    port = f"soxta:{tmp_path / 'flash.json'}"
    pin = {"ZARBXONA_PICO_PIN": "cli-pin-123"}
    r = cli("pico", "sozla", "--papka", str(papka), "--port", port)
    assert r.returncode == 2 and "--import" in r.stdout
    r = cli("pico", "sozla", "--papka", str(papka), "--port", port, "--import", env=pin)
    assert r.returncode == 0, r.stdout + r.stderr
    assert "Pico sozlandi" in r.stdout and "YANGI" not in r.stdout
    assert "TUGMASINI BOSING" in r.stdout               # soxta Pico tugmani «bosdi»
    r = cli("zarb", "--papka", str(papka), "--summa", "7777", "--qulf", "Q", "--hajm", "3",
            "--surat", "cheklovsiz", env={"ZARBXONA_PAROL": "", **pin})
    assert r.returncode == 0, r.stdout + r.stderr
    assert "imzolovchi: Pico" in r.stdout and "RUXSAT" in r.stdout and "TUGADI" in r.stdout
    assert cli("tekshir", "--papka", str(papka), env=pin).returncode == 0
    r = cli("zarb", "--papka", str(papka), "--summa", "5", "--qulf", "Q",
            env={"ZARBXONA_PICO_PIN": "xato-pin-00"})
    assert r.returncode == 1 and "PIN noto'g'ri" in r.stdout
    r = cli("pico", "holat", "--papka", str(papka))
    assert r.returncode == 0 and "QULFLANGAN" in r.stdout and "urinishlari qolgan: 4" in r.stdout
    r = cli("pico", "sozla", "--papka", str(papka), "--port", port, "--yangi", env=pin)
    assert r.returncode == 1 and "allaqachon Pico" in r.stdout
    r = cli("pico", "qaytish", "--papka", str(papka))
    assert r.returncode == 0
    r = cli("holat", "--papka", str(papka))                  # yana kalit.json paroli
    assert r.returncode == 0 and "imzolovchi: Pico" not in r.stdout
