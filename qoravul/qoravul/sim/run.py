"""Fleet simulation over real localhost QVL/1 connections.

    python -m qoravul.sim.run --nodes 30 --thieves 6 --hours 24
"""
from __future__ import annotations

import argparse
import asyncio
import json
import sys
import tempfile
import time
from pathlib import Path

import numpy as np

from ..edge.node import EdgeNode
from ..gateway.server import EvidenceLedger, Gateway
from ..protocol.handshake import Identity
from ..tinyml.meter import ATTACKS, VirtualMeter
from ..tinyml.model import QuantAE

ROOT = Path(__file__).resolve().parents[2]
DEFAULT_MODEL = ROOT / "models" / "qv_model.json"


async def run_fleet(nodes: int = 30, thieves: int = 6, hours: float = 24.0, seed: int = 7, start_hour: float = 0.0,
                    model: QuantAE | None = None, ledger_path: str | Path | None = None,
                    reconnect_hours: float | None = None, resume: bool = True,
                    export_dir: str | Path | None = None) -> dict:
    rng = np.random.default_rng(seed)
    model = model or QuantAE.load(DEFAULT_MODEL)
    minutes = int(round(hours * 60))
    start = int(round(start_hour * 60))
    if export_dir is not None:
        Path(export_dir).mkdir(parents=True, exist_ok=True)
        ledger_path = Path(export_dir) / "ledger.jsonl"
        ledger_path.unlink(missing_ok=True)
    if ledger_path is None:
        ledger_path = Path(tempfile.mkdtemp(prefix="qoravul_")) / "ledger.jsonl"
    ledger = EvidenceLedger(ledger_path)

    gw_id = Identity.generate()
    fleet: list[EdgeNode] = []
    for i in range(nodes):
        meter = VirtualMeter(seed=int(rng.integers(2**31)))
        fleet.append(EdgeNode(Identity.generate(), gw_id.pk, model, meter, resume=resume))
    registry = {n.identity.node_id: n.identity.pk for n in fleet}
    gw = Gateway(gw_id, registry, ledger)
    port = await gw.start()

    thief_idx = rng.choice(nodes, size=thieves, replace=False)
    thief_info = {}
    for k, idx in enumerate(thief_idx):
        meter = fleet[idx].meter
        meter.attack = ATTACKS[k % len(ATTACKS)]
        # attack is switched on in the first quarter of the run (night_load only acts 01:00-05:00)
        meter.attack_start = start + int(rng.integers(0, max(1, minutes // 4)))
        if meter.first_active(start + minutes) is None:  # e.g. night_load switched on after 05:00
            meter.attack_start = start
        thief_info[fleet[idx].node_hex] = {"attack": meter.attack, "start": meter.attack_start,
                                           "first_active": meter.first_active(start + minutes)}

    t0 = time.time()
    per = int(round(reconnect_hours * 60)) if reconnect_hours else minutes

    async def node_life(node: EdgeNode) -> dict:
        tot = {"tx": 0, "rx": 0, "handshake": 0, "raw_baseline": 0, "sessions": 0, "resumed": 0}
        for s0 in range(start, start + minutes, per):
            st = await node.run("127.0.0.1", port, s0, min(per, start + minutes - s0))
            for k in ("tx", "rx", "handshake", "raw_baseline"):
                tot[k] += st[k]
            tot["sessions"] += 1
            tot["resumed"] += int(st["resumed"])
        return tot

    stats = await asyncio.gather(*(node_life(n) for n in fleet))
    wall = time.time() - t0
    await gw.stop()

    detected, false_alerts, ttd = {}, [], []
    for ev in gw.alerts:
        info = thief_info.get(ev["node"])
        if info and info["first_active"] is not None and ev["window"] >= info["first_active"]:
            if ev["node"] not in detected:
                detected[ev["node"]] = ev
                ttd.append(ev["window"] - info["first_active"])
        else:
            false_alerts.append(ev)

    qv_bytes = sum(s["tx"] + s["rx"] for s in stats)
    raw_bytes = sum(s["raw_baseline"] for s in stats)
    hs_bytes = sum(s["handshake"] for s in stats)
    report = {
        "nodes": nodes,
        "thieves": thieves,
        "hours": hours,
        "windows": nodes * minutes,
        "detected": len(detected),
        "thief_attacks": {h: v["attack"] for h, v in thief_info.items()},
        "detected_attacks": sorted(thief_info[h]["attack"] for h in detected),
        "missed_attacks": sorted(v["attack"] for h, v in thief_info.items() if h not in detected),
        "false_alerts": len(false_alerts),
        "alerts": len(gw.alerts),
        "ttd_minutes": ttd,
        "ledger_entries": ledger.count,
        "ledger_ok": ledger.verify_chain(),
        "ledger_path": str(ledger_path),
        "gateway_errors": gw.errors,
        "rejects": gw.rejects,
        "bytes_qoravul": qv_bytes,
        "bytes_raw_stream": raw_bytes,
        "bytes_handshake": hs_bytes,
        "saving": 1.0 - qv_bytes / raw_bytes,
        "summaries": sum(len(v) for v in gw.summaries.values()),
        "sessions": sum(s["sessions"] for s in stats),
        "resumed_sessions": sum(s["resumed"] for s in stats),
        "wall_s": wall,
    }
    if export_dir is not None:
        _export(Path(export_dir), fleet, gw, report)
    return report


def _export(out: Path, fleet: list[EdgeNode], gw: Gateway, report: dict) -> None:
    """Write what the gateway operator sees (for the dashboard) plus the ground-truth report."""
    (out / "nodes.json").write_text(json.dumps({n.node_hex: {"pk": n.identity.pk.hex()} for n in fleet}))
    (out / "summaries.json").write_text(json.dumps(gw.summaries))
    (out / "report.json").write_text(json.dumps(report, indent=1))


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--nodes", type=int, default=30)
    ap.add_argument("--thieves", type=int, default=6)
    ap.add_argument("--hours", type=float, default=24.0)
    ap.add_argument("--start-hour", type=float, default=0.0)
    ap.add_argument("--seed", type=int, default=7)
    ap.add_argument("--model", default=str(DEFAULT_MODEL))
    ap.add_argument("--ledger", default=None)
    ap.add_argument("--export", default=None, metavar="DIR",
                    help="write ledger.jsonl, summaries.json, nodes.json, report.json for the dashboard")
    ap.add_argument("--reconnect-hours", type=float, default=None,
                    help="close and reopen each node's session this often (PSK resumption after the first)")
    ap.add_argument("--no-resume", action="store_true", help="always run the full handshake")
    ap.add_argument("--json", action="store_true", help="print the full report as JSON")
    args = ap.parse_args(argv)

    rep = asyncio.run(run_fleet(args.nodes, args.thieves, args.hours, args.seed, args.start_hour,
                                QuantAE.load(args.model), args.ledger, args.reconnect_hours, not args.no_resume,
                                args.export))
    if args.json:
        print(json.dumps(rep, indent=1))
    else:
        print(f"fleet: {rep['nodes']} nodes, {rep['thieves']} thieves, {rep['hours']} h, {rep['windows']} windows "
              f"({rep['wall_s']:.1f} s wall)")
        print(f"detected thieves : {rep['detected']}/{rep['thieves']}  {rep['detected_attacks']}"
              + (f"  MISSED {rep['missed_attacks']}" if rep["missed_attacks"] else ""))
        print(f"time to detect   : {rep['ttd_minutes']} min after attack became active")
        print(f"false alerts     : {rep['false_alerts']}")
        print(f"ledger           : {rep['ledger_entries']} entries, chain {'OK' if rep['ledger_ok'] else 'BROKEN'}"
              f" ({rep['ledger_path']})")
        print(f"bandwidth        : QORAVUL {rep['bytes_qoravul']} B vs raw stream {rep['bytes_raw_stream']} B "
              f"(both incl. {rep['bytes_handshake']} B handshakes) -> saving {rep['saving'] * 100:.1f}%")
        print(f"sessions         : {rep['sessions']} ({rep['resumed_sessions']} resumed)")
        if rep["gateway_errors"] or rep["rejects"]:
            print(f"gateway errors   : {rep['gateway_errors']} rejects: {rep['rejects']}")
    ok = (rep["detected"] == rep["thieves"] and rep["false_alerts"] == 0 and rep["ledger_ok"]
          and not rep["gateway_errors"])
    print("RESULT:", "PASS" if ok else "FAIL")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
