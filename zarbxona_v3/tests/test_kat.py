"""T1 — KAT: hamma qiymat v3 yadrosi bilan qayta hisoblanadi.
T2 — standart KMAC256 KAT bilan MOS KELMASLIGI qulflangan."""

from __future__ import annotations

import pytest

from core import ibtido, kupyura, merkle, protokol
from core.cheklov import cheklov_json, cheklov_xeshi
from core.ombor import ombor_lugatdan_och
from core.partiya import ZarbKirishi, imzo_xabari, nominallarga_bol, zarb_qil
from core.sertifikat import Sertifikat

X = bytes.fromhex


def test_ibtidolar(kat):
    p = kat["primitivlar"]
    for v in p["sha3_256"]:
        assert ibtido.sha3(X(v["in"])).hex() == v["out"]
    for v in p["kmac256"]:
        assert ibtido.aq_kmac256(X(v["key"]), X(v["data"]), X(v["custom"]), v["len"]).hex() \
            == v["out"]
    for v in p["hkdf_expand_sha3_256"]:
        assert ibtido.hkdf_expand(X(v["prk"]), X(v["info"]), v["len"]).hex() == v["out"]
    for v in p["chacha20poly1305"]:
        out = ibtido.aead_seal(X(v["key"]), X(v["nonce"]), X(v["plaintext"]), X(v["aad"]))
        assert out.hex() == v["out"]
        assert ibtido.aead_open(X(v["key"]), X(v["nonce"]), out, X(v["aad"])) \
            == X(v["plaintext"])
        assert ibtido.aead_open(X(v["key"]), X(v["nonce"]), out, b"boshqa") is None
    for v in p["tagged_hash_be32"]:
        assert ibtido.tagged_hash(X(v["label"]), *[X(x) for x in v["parts"]]).hex() == v["out"]


def test_standart_kmac_farq_qiladi(kat):
    """T2: kimdir «tuzatib» standart KMAC qo'ymasin."""
    Crypto = pytest.importorskip("Crypto.Hash.KMAC256")
    for v in kat["primitivlar"]["kmac256"]:
        std = Crypto.new(key=X(v["key"]), data=X(v["data"]), mac_len=v["len"],
                         custom=X(v["custom"])).digest()
        assert std.hex() != v["out"]


def test_ml_dsa(kat):
    m = kat["ml_dsa_65"]
    sk = ibtido.kalit_urugdan(X(m["seed"]))
    pk = ibtido.ochiq_kalit(sk)
    assert pk.hex() == m["public_key"]
    assert len(pk) == 1952
    assert ibtido.sha3(pk).hex() == m["public_key_sha3"]
    assert ibtido.iz(pk) == m["fingerprint"]
    assert ibtido.imzo_togri(pk, X(m["signature"]), X(m["message"]))
    s = ibtido.imzola(sk, X(m["message"]))
    assert len(s) == 3309 and ibtido.imzo_togri(pk, s, X(m["message"]))
    # fail-closed
    assert not ibtido.imzo_togri(pk, s, X(m["message"]) + b"!")
    assert not ibtido.imzo_togri(pk, b"qisqa", X(m["message"]))
    assert not ibtido.imzo_togri(b"yaroqsiz kalit", s, X(m["message"]))


def test_kalit_ombori(kat):
    ks = kat["kalit_ombori"]
    assert ombor_lugatdan_och(ks["fayl"], ks["parol"]).hex() == ks["kutilgan_seed"]


def test_cheklov(kat):
    for c in kat["cheklov"]:
        k = c["kirish"]
        s = cheklov_json(k.get("toifalar", ()), k.get("muddat_ms"), k.get("soliq_bps", 0),
                         k.get("soliq_hisobi", ""))
        assert s == c["json"]
        assert cheklov_xeshi(s).hex() == c["xesh"]


def test_sertifikat(kat):
    s = Sertifikat.lugatdan(kat["sertifikat"]["fayl"])
    assert s.xabar().hex() == kat["sertifikat"]["xabar_digest"]
    assert s.imzo_togri()
    bank = ibtido.kalit_urugdan(X(kat["sertifikat"]["bank_seed"]))
    assert ibtido.ochiq_kalit(bank) == s.bank_public_key
    pk = X(kat["ml_dsa_65"]["public_key"])
    assert s.muammo(pk, hozir_ms=1_800_000_000_000) is None
    assert s.lugat() == kat["sertifikat"]["fayl"]


@pytest.mark.parametrize("nomi", ["bitta", "uchta_toq", "yetti_cheklovli",
                                  "nominallarga_bol_1234567"])
def test_partiya(kat, nomi):
    b = next(x for x in kat["partiyalar"] if x["nomi"] == nomi)
    k = b["kirish"]
    bid, bk, mk = X(k["partiya_id"]), X(k["partiya_kaliti"]), X(k["master"])
    assert cheklov_xeshi(k["cheklov_json"]).hex() == b["cheklov_xeshi"]
    if nomi == "nominallarga_bol_1234567":
        assert k["nominallar"] == nominallarga_bol(1_234_567)
        assert len(k["nominallar"]) == 256

    zsk = ibtido.kalit_urugdan(X(kat["ml_dsa_65"]["seed"]))
    zpk = ibtido.ochiq_kalit(zsk)
    p = zarb_qil(ZarbKirishi(k["nominallar"], X(k["sert_id"]), k["zaxira_qulfi"],
                             k["birinchi_seq"], k["cheklov_json"], k["egasi"]),
                 zsk, partiya_id=bid, partiya_kaliti=bk, master=mk, zarb_ms=k["zarb_ms"])
    assert p.ildiz.hex() == b["ildiz"]
    assert p.soni == b["soni"] and p.jami == b["jami"]
    msg = p.imzo_xabari()
    assert msg.hex() == b["imzo_xabari"]
    assert ibtido.sha3(msg).hex() == b["imzo_xabari_sha3"]
    assert msg == imzo_xabari(p.ildiz, bid, p.soni, p.jami, k["zaxira_qulfi"], k["zarb_ms"])
    assert ibtido.imzo_togri(zpk, X(b["imzo"]), msg)     # KAT imzosi
    assert ibtido.imzo_togri(zpk, p.imzo, msg)           # o'z imzomiz

    for kv in b["kupyuralar"]:
        i = kv["indeks"]
        q = p.qatorlar[i]
        nid = kupyura.note_id_hisobla(bk, bid, i)
        assert nid.hex() == kv["note_id"] == q.note_id.hex()
        assert kupyura.nazorat_kaliti(bk, nid).hex() == kv["nazorat_kaliti"]
        kk, nn = kupyura.konvert(mk, nid)
        assert (kk.hex(), nn.hex()) == (kv["konvert_kalit"], kv["konvert_nonce"])
        kod = q.kod()
        assert kod.hex() == kv["sarlavha_kodi"]
        assert kupyura.sarlavha_xeshi(kod).hex() == kv["sarlavha_xeshi"]
        assert q.barg().hex() == kv["barg"]
        assert q.muhr.hex() == kv["muhr"]
        assert kupyura.muhrni_och(mk, nid, q.muhr, kod).hex() == kv["yadro_ochiq"]
        assert [x.hex() for x in merkle.isbot_ajrat(q.isbot)] == kv["isbot"]
        assert merkle.isbot_togri(q.barg(), merkle.isbot_ajrat(q.isbot), i, p.soni, p.ildiz)

    if "barglar_sha3" in b:
        barglar = [q.barg() for q in p.qatorlar]
        assert ibtido.sha3(b"".join(barglar)).hex() == b["barglar_sha3"]
        assert len(merkle.qavatlar(barglar)) == b["qavatlar_soni"]


def test_protokol(kat):
    pr = kat["protokol"]
    bpk = X(kat["sertifikat"]["fayl"]["bank_public_key"])
    assert ibtido.sha3(bpk).hex() == pr["bank_id"]["bank_public_key_sha3"]
    assert ibtido.sha3(b"AETHER-Q-v5.1-SRV-ID" + bpk).hex() == pr["bank_id"]["server_id_hash"]
    assert protokol.bank_id(bpk) == pr["bank_id"]["bank_id"]
    ma = pr["mint_auth"]
    assert protokol.mint_auth_xesh(bpk, X(ma["chaqiriq"]), X(ma["sert_id"])).hex() \
        == ma["digest"]
    w = pr["wire"]
    wire = protokol.Wire(X(w["kalit"]))
    for _ in range(w["hisoblagich"] - 1):
        wire.ora(b"")
    assert wire.ora(X(w["yozuv"])).hex() == w["c2b_paket"]
    # bank tomoni shu paketni qabul qiladi
    bank = protokol.Wire(X(w["kalit"]), yuborish=protokol.B2C, qabul=protokol.C2B)
    assert bank.ech(X(w["c2b_paket"])) == X(w["yozuv"])


def test_merkle_chekka_holatlar():
    assert merkle.ildiz([]) == bytes(32)
    b = [ibtido.sha3(bytes([i])) for i in range(5)]
    q = merkle.qavatlar(b)
    # toq tugun nusxalanmaydi: 5 barg → [5, 3, 2, 1]
    assert [len(x) for x in q] == [5, 3, 2, 1]
    assert q[1][2] == b[4]
    for i in range(5):
        assert merkle.isbot_togri(b[i], merkle.isbot(q, i), i, 5, q[-1][0])
        assert not merkle.isbot_togri(b[i], merkle.isbot(q, i), (i + 1) % 5, 5, q[-1][0])
    assert not merkle.isbot_togri(b[0], [], 0, 0, bytes(32))
