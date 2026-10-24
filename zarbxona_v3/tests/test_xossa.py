"""2.2 — xossaga asoslangan (property-based) va fuzz testlar (hypothesis).

Xossalar: nominallar yig'indisi = summa; bo'lak = ro'yxat kesmasi; har Merkle isboti
ildizga olib boradi, boshqa barg/indeks bilan emas; cheklov JSON kanonik va xesh
barqaror. Fuzz: protokol, wire, qator va partiya fayli tahlilchilari tasodifiy kirishda
faqat O'Z xatosini beradi — boshqa istisno yoki osilib qolish yo'q.
"""

from __future__ import annotations

import json
import sqlite3

import pytest

hypothesis = pytest.importorskip("hypothesis")
from hypothesis import HealthCheck, given, settings  # noqa: E402
from hypothesis import strategies as st  # noqa: E402

from core.cheklov import CheklovXatosi, cheklov_json, cheklov_xeshi  # noqa: E402
from core.ibtido import sha3  # noqa: E402
from core.konstanta import NOMINALLAR  # noqa: E402
from core.merkle import Daraxt, isbot_ajrat, isbot_togri  # noqa: E402
from core.partiya import (FaylXatosi, nominallar_bolagi, nominallar_soni,  # noqa: E402
                          nominallarga_bol, partiya_oqi)
from core.protokol import (B2C, C2B, ProtokolXatosi, Wire, och, qator_kodla,  # noqa: E402
                           qator_och)
from core.zanjir import bosh_tahlil  # noqa: E402

TEZ = settings(max_examples=200, deadline=None,
               suppress_health_check=[HealthCheck.function_scoped_fixture])


@TEZ
@given(st.integers(min_value=1, max_value=10**12))
def test_nominallar_yigindisi_summa(summa):
    n = nominallarga_bol(summa) if summa < 10**7 else None
    k = nominallar_soni(summa)
    if n is not None:
        assert sum(n) == summa and len(n) == k
        assert n == sorted(n, reverse=True) and set(n) <= set(NOMINALLAR)
    # ochko'z algoritm: 5000 dan kichik nominallar soni cheklangan (≤ 1 ta 500, …)
    kichik = nominallar_bolagi(summa, summa // 5000, k)
    assert sum(kichik) == summa % 5000


@TEZ
@given(st.integers(min_value=1, max_value=2_000_000), st.integers(min_value=0, max_value=600),
       st.integers(min_value=1, max_value=400))
def test_nominallar_bolagi_kesma(summa, boshi, soni):
    assert nominallar_bolagi(summa, boshi, soni) == nominallarga_bol(summa)[boshi:boshi + soni]


@TEZ
@given(st.lists(st.binary(min_size=32, max_size=32), min_size=1, max_size=70))
def test_merkle_har_isbot_togri(barglar):
    d = Daraxt(barglar)
    n = len(barglar)
    for i in range(n):
        yol = d.isbot(i)
        assert isbot_togri(barglar[i], yol, i, n, d.ildiz)
        assert isbot_ajrat(b"".join(yol)) == yol
        if n > 1:
            j = (i + 1) % n
            if barglar[j] != barglar[i]:
                assert not isbot_togri(barglar[j], yol, i, n, d.ildiz)
        assert not isbot_togri(sha3(barglar[i]), yol, i, n, d.ildiz)


toifa = st.text(alphabet=st.sampled_from("abcXYZ019_ "), min_size=0, max_size=12)


@TEZ
@given(st.lists(toifa, max_size=10), st.one_of(st.none(), st.integers(-5, 10**13)),
       st.integers(-5, 10_005), st.text(max_size=10))
def test_cheklov_kanonik_yoki_aniq_xato(toifalar, muddat, bps, hisob):
    try:
        s = cheklov_json(toifalar, muddat, bps, hisob)
    except CheklovXatosi:
        return
    if s == "":
        assert cheklov_xeshi(s) == bytes(32)
        return
    d = json.loads(s)
    # kanonik: qayta kodlash o'sha satr; toifalar tartiblangan, katta harf, takrorsiz
    assert json.dumps(d, sort_keys=True, separators=(",", ":"), ensure_ascii=False) == s
    t = d.get("categories", [])
    assert t == sorted(set(t)) and all(x == x.upper() for x in t) and len(t) <= 8
    # tartib va registr natijaga ta'sir qilmaydi
    assert cheklov_json(list(reversed([x.lower() for x in toifalar])), muddat, bps,
                        hisob) == s


@TEZ
@given(st.binary(max_size=400))
def test_fuzz_xabar_tahlili(b):
    try:
        d = och(b)
    except ProtokolXatosi:
        return
    assert isinstance(d, dict) and d.get("v") == 1


@TEZ
@given(st.lists(st.one_of(st.binary(max_size=80), st.text(max_size=20), st.integers(),
                          st.none()), max_size=10), st.integers(0, 10))
def test_fuzz_qator(r, i):
    try:
        q = qator_och(r, i)
    except ProtokolXatosi:
        return
    assert qator_och(qator_kodla(q), i) == q            # qabul qilingani — aniq round-trip


@TEZ
@given(st.lists(st.binary(max_size=120), max_size=30))
def test_fuzz_wire_tashlaydi_haqiqiysi_otadi(begona):
    k = bytes(range(32))
    mijoz, bank = Wire(k), Wire(k, yuborish=B2C, qabul=C2B)
    for p in begona:
        assert bank.ech(p) is None                      # begona teg — hech qachon o'tmaydi
    assert bank.tashlangan == len(begona)
    assert bank.ech(mijoz.ora(b"haqiqiy")) == b"haqiqiy"


@settings(max_examples=60, deadline=None,
          suppress_health_check=[HealthCheck.function_scoped_fixture])
@given(st.binary(max_size=4096))
def test_fuzz_partiya_fayli(tmp_path_factory, b):
    yol = tmp_path_factory.mktemp("fuzz") / "x.aqbatch"
    yol.write_bytes(b)
    with pytest.raises(FaylXatosi):
        partiya_oqi(yol)


@settings(max_examples=40, deadline=None,
          suppress_health_check=[HealthCheck.function_scoped_fixture])
@given(st.sampled_from(["magic", "version", "note_count", "leaf_index"]),
       st.one_of(st.integers(-3, 3), st.text(max_size=5), st.none()))
def test_fuzz_buzilgan_sxema(tmp_path_factory, ustun, qiymat):
    """Haqiqiy partiya faylining sarlavhasini buzib ochish: yo FaylXatosi, yo o'qiladi —
    boshqa istisno yo'q (tekshiruvchi keyin mazmunni rad etadi)."""
    from core.ibtido import kalit_urugdan
    from core.partiya import ZarbKirishi, partiya_yoz, zarb_qil
    p = zarb_qil(ZarbKirishi([5, 10], bytes(16), "Q", 1), kalit_urugdan(bytes(32)))
    yol = partiya_yoz(p, tmp_path_factory.mktemp("sx"))
    db = sqlite3.connect(yol)
    with db:
        jadval = "notes" if ustun == "leaf_index" else "header"
        try:
            db.execute(f"UPDATE {jadval} SET {ustun}=?", (qiymat,))
        except sqlite3.IntegrityError:
            pass
    db.close()
    try:
        partiya_oqi(yol)
    except FaylXatosi:
        pass


@TEZ
@given(st.text(max_size=200))
def test_fuzz_zanjir_boshi(s):
    r = bosh_tahlil(s)
    assert r is None or (isinstance(r[0], int) and isinstance(r[1], bytes))
