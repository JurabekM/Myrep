"""QORAVUL benchmarks (host CPU, pure-Python PQ by default).

    python -m bench.bench [--runs 20] [--fleet-meters 1000]
"""
from __future__ import annotations

import argparse
import os
import platform
import statistics
import time
from pathlib import Path

import numpy as np

from qoravul.crypto import backend as pq
from qoravul.edge.node import EVIDENCE_CTX, IncidentFSM, canonical, encode_alert
from qoravul.protocol.handshake import GatewayHandshake, Identity, NodeHandshake
from qoravul.protocol.session import RECORD_OVERHEAD
from qoravul.protocol.wire import FrameType, Suite, encode_stream
from qoravul.tinyml.meter import features, simulate
from qoravul.tinyml.model import QuantAE

ROOT = Path(__file__).resolve().parents[1]


def _ms(samples):
    return statistics.median(samples) * 1e3


def bench_handshake(runs: int) -> None:
    node, gw = Identity.generate(), Identity.generate()
    reg = {node.node_id: node.pk}
    print(f"\n== QVL/1 handshake ({runs} runs, median; backend={pq.get_backend().name}) ==")
    print(f"{'suite':<8} {'HELLO B':>8} {'ACCEPT B':>9} {'total B':>8} {'node ms':>8} {'gw ms':>7} {'total ms':>9}")
    for suite in Suite:
        gwh = GatewayHandshake(gw, reg, allowed=set(Suite))
        t_node, t_gw = [], []
        for _ in range(runs):
            nh = NodeHandshake(node, gw.pk, suite)
            t0 = time.perf_counter()
            hello = nh.hello()
            t1 = time.perf_counter()
            res = gwh.respond(hello)
            t2 = time.perf_counter()
            sess = nh.finish(res.frame)
            t3 = time.perf_counter()
            assert sess.session_id == res.session.session_id
            t_node.append((t1 - t0) + (t3 - t2))
            t_gw.append(t2 - t1)
        h, a = len(encode_stream(hello)), len(encode_stream(res.frame))
        print(f"{suite.name:<8} {h:>8} {a:>9} {h + a:>8} {_ms(t_node):>8.2f} {_ms(t_gw):>7.2f} "
              f"{_ms(t_node) + _ms(t_gw):>9.2f}")
    print("sizes include the 4-byte stream length prefix")
    print("authenticators per handshake: 2 ML-DSA-65 signatures (node + gateway), 2 verifications")


def bench_records(runs: int) -> None:
    node, gw = Identity.generate(), Identity.generate()
    nh = NodeHandshake(node, gw.pk)
    res = GatewayHandshake(gw, {node.node_id: node.pk}).respond(nh.hello())
    ns, gs = nh.finish(res.frame), res.session
    pt = b"x" * 100
    rec = ns.seal(FrameType.DATA, pt)
    n = 2000
    t0 = time.perf_counter()
    for _ in range(n):
        gs.open(ns.seal(FrameType.DATA, pt))
    dt = (time.perf_counter() - t0) / n
    print("\n== record layer ==")
    print(f"record overhead: {len(rec) - len(pt)} B (ver 1 + type 1 + sid 8 + seq 8 + Poly1305 tag 16)"
          f" + 4 B stream length; constant RECORD_OVERHEAD={RECORD_OVERHEAD}")
    print("MACs per record: 1 (Poly1305, 16 B); AAD = ver||type||sid||seq")
    print(f"seal+open 100 B: {dt * 1e6:.1f} us")

    ev = canonical({"node": node.node_id.hex(), "window": 123, "hour": 3.2833, "score": 12345, "culprit": "i_norm",
                    "features": [0.012345] * 8, "model_thr": 2917})
    ts, tv = [], []
    for _ in range(runs):
        t0 = time.perf_counter()
        sig = pq.sign(node.sk, ev, EVIDENCE_CTX)
        t1 = time.perf_counter()
        assert pq.verify(node.pk, ev, sig, EVIDENCE_CTX)
        tv.append(time.perf_counter() - t1)
        ts.append(t1 - t0)
    alert = ns.seal(FrameType.ALERT, encode_alert(ev, sig))
    hexed = len(ev) + 2 * len(sig) + 12  # TAXMIN: same evidence with "sig":"<hex>" inside the JSON
    print(f"ALERT record: {len(encode_stream(alert))} B on the wire (evidence {len(ev)} B + sig {len(sig)} B); "
          f"hex-in-JSON would be ~{hexed + RECORD_OVERHEAD + 4} B")
    print(f"ML-DSA-65 sign {_ms(ts):.1f} ms, verify {_ms(tv):.1f} ms (median of {runs})")


def bench_detector() -> None:
    q = QuantAE.load(ROOT / "models" / "qv_model.json")
    rng = np.random.default_rng(0)
    x = features(simulate(rng.uniform(0, 24, 10_000), 1.0, 0.0, rng))
    t0 = time.perf_counter()
    q.detect(x)
    batch = (time.perf_counter() - t0) / len(x)
    t0 = time.perf_counter()
    for i in range(500):
        q.detect(x[i])
    single = (time.perf_counter() - t0) / 500
    macs = sum(L["w"].size for L in q.layers)
    flash = sum(L["w"].size + 4 * L["b"].size + 4 + 1 for L in q.layers) + 8 * 4 * 2 + 8 * (4 + 2 + 2)
    print("\n== detector ==")
    print(f"int8 MACs per window: {macs}; model constants: {flash} B")
    print(f"python reference: {single * 1e6:.0f} us/window single, {batch * 1e6:.2f} us/window batched")


def bench_fleet_fpr(meters: int, seed: int = 99) -> None:
    """Honest meters for 24 h through detector + 4/6 FSM, no network."""
    q = QuantAE.load(ROOT / "models" / "qv_model.json")
    rng = np.random.default_rng(seed)
    minutes = np.arange(1440)
    flagged = incidents = meters_hit = 0
    for _ in range(meters):
        scale, phase = rng.uniform(0.6, 1.8), rng.normal(0.0, 0.7)
        d = q.detect(features(simulate(minutes / 60.0, scale, phase, rng)))
        flagged += int(d["anomaly"].sum())
        fsm, opened = IncidentFSM(), 0
        for a in d["anomaly"]:
            opened += fsm.step(bool(a)) == "open"
        incidents += opened
        meters_hit += opened > 0
    n = meters * 1440
    print(f"\n== honest fleet: {meters} meters x 24 h = {n} windows ==")
    print(f"window FPR {flagged / n * 100:.3f}%, false incidents {incidents} "
          f"({meters_hit} meters, {incidents / meters:.4f} per meter-day)")


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--runs", type=int, default=20)
    ap.add_argument("--fleet-meters", type=int, default=0, help="also run the honest-fleet false-incident check")
    args = ap.parse_args(argv)
    print(f"host: {platform.machine()} {platform.processor() or ''} python {platform.python_version()} "
          f"cpus={os.cpu_count()}")
    bench_handshake(args.runs)
    bench_records(args.runs)
    bench_detector()
    if args.fleet_meters:
        bench_fleet_fpr(args.fleet_meters)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
