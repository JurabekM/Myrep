"""Dashboard data layer (no Qt): load a gateway export and verify it."""
from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path

from ..gateway.server import EvidenceLedger, verify_evidence

SLOT_MIN = 15  # summaries are sent every 15 windows


@dataclass
class LedgerRow:
    index: int
    node: str
    window: int
    score: int
    threshold: int
    culprit: str
    sig_ok: bool
    hash: str


@dataclass
class Incident:
    node: str
    opened: int  # window of the ALERT
    culprit: str
    active: bool  # last summary from the node still reports inc=1


@dataclass
class DashboardData:
    rows: list[LedgerRow]
    chain_ok: bool
    incidents: list[Incident]
    nodes: list[str]
    kwh_slots: list[int] = field(default_factory=list)  # window index of each slot end
    kwh_fleet: list[float] = field(default_factory=list)
    kwh_node: dict[str, list[float]] = field(default_factory=dict)

    @property
    def total_kwh(self) -> float:
        return sum(self.kwh_fleet)

    @property
    def sig_failures(self) -> int:
        return sum(not r.sig_ok for r in self.rows)


def load(export_dir: str | Path) -> DashboardData:
    d = Path(export_dir)
    nodes = json.loads((d / "nodes.json").read_text())
    summaries: dict[str, list[dict]] = json.loads((d / "summaries.json").read_text())
    ledger = EvidenceLedger(d / "ledger.jsonl")

    rows = []
    for i, e in enumerate(ledger.entries()):
        rec = e["record"]
        ev = json.loads(rec["evidence"])
        pk = nodes.get(rec["node"], {}).get("pk")
        sig_ok = pk is not None and verify_evidence(rec, bytes.fromhex(pk))
        rows.append(LedgerRow(i, rec["node"], int(ev["window"]), int(ev["score"]), int(ev["model_thr"]),
                              ev["culprit"], sig_ok, e["hash"]))

    incidents, seen = [], set()
    for r in rows:
        if r.node in seen:
            continue
        seen.add(r.node)
        last = summaries.get(r.node, [{}])[-1]
        incidents.append(Incident(r.node, r.window, r.culprit, bool(last.get("inc", 0))))

    slots = sorted({s["w"] for v in summaries.values() for s in v})
    pos = {w: i for i, w in enumerate(slots)}
    fleet = [0.0] * len(slots)
    per_node = {}
    for node, lst in summaries.items():
        series = [0.0] * len(slots)
        for s in lst:
            series[pos[s["w"]]] = s["kwh"]
            fleet[pos[s["w"]]] += s["kwh"]
        per_node[node] = series
    return DashboardData(rows, ledger.verify_chain(), incidents, sorted(nodes), slots, fleet, per_node)
