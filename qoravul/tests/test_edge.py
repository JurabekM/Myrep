"""Detector, firmware parity, evidence/ledger and end-to-end fleet tests."""
from __future__ import annotations

import asyncio
import json
import math
import re
import shutil
import subprocess
from pathlib import Path

import numpy as np
import pytest

from qoravul.crypto import backend as pq
from qoravul.edge.node import EVIDENCE_CTX, IncidentFSM, canonical, decode_alert, encode_alert
from qoravul.gateway.server import GENESIS, EvidenceLedger, Gateway, verify_evidence
from qoravul.protocol.handshake import Identity
from qoravul.protocol.wire import ProtocolError
from qoravul.sim.run import run_fleet
from qoravul.tinyml.meter import ATTACKS, FEATURES, dataset
from qoravul.tinyml.model import QuantAE, quantize_multiplier

ROOT = Path(__file__).resolve().parents[1]
MODEL_PATH = ROOT / "models" / "qv_model.json"


@pytest.fixture(scope="module")
def model() -> QuantAE:
    return QuantAE.load(MODEL_PATH)


# ------------------------------------------------------------------ detector
def test_model_shape(model):
    assert [L["w"].shape for L in model.layers] == [(16, 8), (4, 16), (16, 4), (8, 16)]
    assert sum(L["w"].size + L["b"].size for L in model.layers) == 428
    assert all(2**30 <= L["m0"] < 2**31 for L in model.layers)
    assert math.isclose(float(model.s_in), 8 / 127, rel_tol=1e-6)


@pytest.mark.parametrize("m", [1e-6, 3.3e-4, 0.0123, 0.2, 0.5, 0.7071, 0.999999])
def test_quantize_multiplier_accuracy(m):
    m0, sh = quantize_multiplier(m)
    assert 2**30 <= m0 < 2**31
    assert abs(m0 / 2.0**sh - m) / m < 2.0**-30


def test_quantize_multiplier_rejects_out_of_range():
    for bad in (0.0, 1.0, 2.5, -0.1):
        with pytest.raises(ValueError):
            quantize_multiplier(bad)


def test_fpr_on_unseen_households(model):
    x = dataset(meters=4096, n=50_000, seed=31337)
    assert model.detect(x)["anomaly"].mean() < 0.005


@pytest.mark.parametrize("attack", ATTACKS)
def test_attack_tpr(model, attack):
    x = dataset(meters=4096, n=3000, seed=4000 + ATTACKS.index(attack), attack=attack)
    assert model.detect(x)["anomaly"].mean() > 0.95


@pytest.mark.parametrize("attack,expected", [("bypass", "n_imb"), ("freq", "f_dev"), ("sag", "v_dev")])
def test_culprit_points_at_tampered_feature(model, attack, expected):
    d = model.detect(dataset(n=500, seed=77, attack=attack))
    culprits = [FEATURES[c] for c in d["culprit"][d["anomaly"]]]
    assert max(set(culprits), key=culprits.count) == expected


def test_incident_fsm_debounce():
    fsm = IncidentFSM()
    assert [fsm.step(a) for a in (1, 0, 1, 0, 0, 1)] == [None] * 6  # 3 of 6: no incident
    assert fsm.step(1) is None  # 1,0,0,1,1 ... still 3 of last 6
    fsm = IncidentFSM()
    events = [fsm.step(a) for a in (1, 1, 0, 1, 1)]
    assert events == [None, None, None, None, "open"] and fsm.active
    events = [fsm.step(0) for _ in range(30)]
    assert events[-1] == "close" and events.count("close") == 1 and not fsm.active


# ------------------------------------------------------------------ firmware
@pytest.mark.skipif(shutil.which("gcc") is None and shutil.which("cc") is None, reason="no C compiler")
def test_c_parity_bit_exact():
    out = subprocess.run(["make", "-s", "-C", str(ROOT / "firmware"), "test"], capture_output=True, text=True)
    assert out.returncode == 0, out.stdout + out.stderr
    assert "parity: 500/500 vectors bit-exact" in out.stdout


@pytest.mark.skipif(shutil.which("arm-none-eabi-gcc") is None or shutil.which("qemu-system-arm") is None,
                    reason="needs arm-none-eabi-gcc and qemu-system-arm")
def test_c_parity_on_cortex_m33_qemu():
    out = subprocess.run(["make", "-s", "-C", str(ROOT / "firmware"), "qemu-m33"], capture_output=True, text=True,
                         timeout=300)
    assert out.returncode == 0, out.stdout + out.stderr
    assert "parity: 500/500 vectors bit-exact" in out.stdout


def test_exported_header_matches_model(model):
    text = (ROOT / "firmware" / "qv_model.h").read_text()
    assert f"#define QV_THRESHOLD {model.threshold}" in text
    literals = re.findall(r"[-+]?[\d.]+(?:e[-+]\d+)?f\b", text)
    assert literals and all(re.fullmatch(r"-?\d\.\d{9}e[-+]\d{2}f", v) for v in literals)  # %.9e + f


# ------------------------------------------------------------ evidence/ledger
@pytest.fixture(scope="module")
def node_id():
    return Identity.generate()


def _evidence(node: Identity, window: int = 42) -> bytes:
    return canonical({"node": node.node_id.hex(), "window": window, "hour": 3.5, "score": 9999, "culprit": "n_imb",
                      "features": [0.0] * 8, "model_thr": 2917})


def test_alert_payload_is_binary(node_id):
    ev = _evidence(node_id)
    sig = pq.sign(node_id.sk, ev, EVIDENCE_CTX)
    payload = encode_alert(ev, sig)
    assert len(payload) == 2 + len(ev) + 3309  # raw signature, not hex
    assert decode_alert(payload) == (ev, sig)


def test_evidence_non_repudiation(tmp_path, node_id):
    gw = Gateway(Identity.generate(), {node_id.node_id: node_id.pk}, EvidenceLedger(tmp_path / "l.jsonl"))
    ev = _evidence(node_id)
    gw.handle_alert(node_id.node_id.hex(), encode_alert(ev, pq.sign(node_id.sk, ev, EVIDENCE_CTX)))
    rec = gw.ledger.entries()[0]["record"]
    assert verify_evidence(rec, node_id.pk)  # anyone holding the node pk can check it
    forged = dict(rec, evidence=rec["evidence"].replace('"score":9999', '"score":1'))
    assert not verify_evidence(forged, node_id.pk)
    other = Identity.generate()
    assert not verify_evidence(rec, other.pk)


def test_gateway_rejects_bad_or_foreign_evidence(tmp_path, node_id):
    other = Identity.generate()
    reg = {node_id.node_id: node_id.pk, other.node_id: other.pk}
    gw = Gateway(Identity.generate(), reg, EvidenceLedger(tmp_path / "l.jsonl"))
    ev = _evidence(node_id)
    bad = bytearray(pq.sign(node_id.sk, ev, EVIDENCE_CTX))
    bad[10] ^= 1
    with pytest.raises(ProtocolError, match="bad evidence signature"):
        gw.handle_alert(node_id.node_id.hex(), encode_alert(ev, bytes(bad)))
    with pytest.raises(ProtocolError, match="bad evidence signature"):  # wrong ctx
        gw.handle_alert(node_id.node_id.hex(), encode_alert(ev, pq.sign(node_id.sk, ev, b"other")))
    # node B relays evidence about node A over B's own session
    ev_other = _evidence(node_id)
    with pytest.raises(ProtocolError):
        gw.handle_alert(other.node_id.hex(), encode_alert(ev_other, pq.sign(other.sk, ev_other, EVIDENCE_CTX)))
    assert gw.ledger.count == 0


def test_ledger_chain_and_tamper(tmp_path):
    path = tmp_path / "ledger.jsonl"
    led = EvidenceLedger(path)
    assert led.head == GENESIS and led.verify_chain()
    for i in range(5):
        led.append({"node": "aa", "evidence": json.dumps({"i": i}), "sig": "00"})
    assert led.verify_chain() and EvidenceLedger(path).head == led.head  # reload keeps head

    lines = path.read_text().splitlines()
    e = json.loads(lines[2])
    e["record"]["evidence"] = json.dumps({"i": 99})
    path.write_text("\n".join(lines[:2] + [json.dumps(e)] + lines[3:]) + "\n")
    assert not EvidenceLedger(path).verify_chain()

    path.write_text("\n".join(lines[:2] + lines[3:]) + "\n")  # deletion breaks the chain too
    assert not EvidenceLedger(path).verify_chain()


# ----------------------------------------------------------------------- e2e
def test_e2e_fleet(tmp_path, model):
    rep = asyncio.run(run_fleet(nodes=8, thieves=3, hours=6, seed=11, model=model,
                                ledger_path=tmp_path / "ledger.jsonl"))
    assert rep["detected"] == 3, rep
    assert rep["false_alerts"] == 0
    assert rep["ledger_ok"] and rep["ledger_entries"] == rep["alerts"]
    assert not rep["gateway_errors"] and not rep["rejects"]
    assert rep["saving"] > 0.70, rep["saving"]
    assert rep["summaries"] == 8 * 6 * 60 // 15


def test_night_load_robust_to_training_seed():
    """Lesson 10: night_load must not depend on the init/data seed (was 16%..100% without hour-clean DAE)."""
    from qoravul.tinyml.model import train_and_quantize

    q, _ = train_and_quantize(seed=3)
    x = dataset(meters=4096, n=3000, seed=9090, attack="night_load")
    assert q.detect(x)["anomaly"].mean() > 0.95
    assert q.detect(dataset(meters=4096, n=30_000, seed=9091))["anomaly"].mean() < 0.005
