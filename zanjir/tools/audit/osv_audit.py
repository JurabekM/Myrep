"""Bog'liqliklar auditi (10-faza, ADR-0014): barcha lock-fayllardagi paketlar OSV.dev bazasida tekshiriladi.

Foydalanish (repo ildizidan yoki istalgan joydan):
    python3 -I zanjir/tools/audit/osv_audit.py            # topilsa — 1 bilan chiqadi
    python3 -I zanjir/tools/audit/osv_audit.py --json     # mashina o'qiydigan hisobot
Istisnolar: `allowlist.json` — har biriga sabab va muddat (muddati o'tgan istisno amal qilmaydi).
Faqat standart kutubxona; tarmoq: https://api.osv.dev.
"""

from __future__ import annotations

import json
import re
import sys
import tomllib
import urllib.request
from dataclasses import dataclass
from datetime import date
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
OSV = "https://api.osv.dev/v1"
PUB_LOCKS = ["app/pubspec.lock", *sorted(str(p.relative_to(ROOT)) for p in ROOT.glob("packages/*/pubspec.lock"))]
UV_LOCKS = ["tools/vectors/uv.lock", "tools/norms/uv.lock"]


@dataclass(frozen=True)
class Package:
    ecosystem: str
    name: str
    version: str
    lock: str


def pub_packages(path: Path) -> list[Package]:
    """`pubspec.lock` (YAML) — faqat `source: hosted` paketlar; oddiy satr tahlili (PyYAML talab qilinmaydi)."""
    out: list[Package] = []
    name = version = source = None
    for line in path.read_text(encoding="utf-8").splitlines():
        if m := re.fullmatch(r"  ([A-Za-z0-9_]+):", line):
            if name and version and source == "hosted":
                out.append(Package("Pub", name, version, str(path.relative_to(ROOT))))
            name, version, source = m[1], None, None
        elif m := re.fullmatch(r'    version: "([^"]+)"', line):
            version = m[1]
        elif m := re.fullmatch(r"    source: (\S+)", line):
            source = m[1]
        elif line and not line.startswith(" "):
            if name and version and source == "hosted":
                out.append(Package("Pub", name, version, str(path.relative_to(ROOT))))
            name = None
    if name and version and source == "hosted":
        out.append(Package("Pub", name, version, str(path.relative_to(ROOT))))
    return out


def uv_packages(path: Path) -> list[Package]:
    data = tomllib.loads(path.read_text(encoding="utf-8"))
    return [
        Package("PyPI", p["name"], p["version"], str(path.relative_to(ROOT)))
        for p in data.get("package", [])
        if "registry" in p.get("source", {})
    ]


def _request(url: str, body: object | None = None) -> Any:
    if not url.startswith(OSV + "/"):
        raise ValueError(url)
    data = None if body is None else json.dumps(body).encode()
    req = urllib.request.Request(url, data, {"content-type": "application/json"})  # noqa: S310 — faqat OSV https
    with urllib.request.urlopen(req, timeout=60) as r:  # noqa: S310
        return json.load(r)


def audit(packages: list[Package]) -> list[dict[str, Any]]:
    unique = sorted({(p.ecosystem, p.name, p.version) for p in packages})
    findings: list[dict[str, Any]] = []
    for i in range(0, len(unique), 500):
        chunk = unique[i : i + 500]
        res = _request(
            f"{OSV}/querybatch",
            {"queries": [{"package": {"name": n, "ecosystem": e}, "version": v} for e, n, v in chunk]},
        )
        for (eco, name, version), r in zip(chunk, res["results"], strict=True):
            for v in r.get("vulns", []):
                detail = _request(f"{OSV}/vulns/{v['id']}")
                fixed = sorted(
                    {
                        e["fixed"]
                        for a in detail.get("affected", [])
                        if a.get("package", {}).get("name", "").lower() == name.lower()
                        for rg in a.get("ranges", [])
                        for e in rg.get("events", [])
                        if "fixed" in e
                    }
                )
                findings.append(
                    {
                        "id": v["id"],
                        "aliases": detail.get("aliases", []),
                        "ecosystem": eco,
                        "package": name,
                        "version": version,
                        "fixed": fixed,
                        "summary": detail.get("summary", ""),
                        "locks": sorted(
                            {p.lock for p in packages if (p.ecosystem, p.name, p.version) == (eco, name, version)}
                        ),
                    }
                )
    return findings


def allowlisted(finding: dict[str, Any], allow: list[dict[str, str]]) -> bool:
    ids = {finding["id"], *finding["aliases"]}
    return any(a["id"] in ids and date.fromisoformat(a["until"]) >= date.today() for a in allow)


def main() -> int:
    packages = [p for lock in PUB_LOCKS for p in pub_packages(ROOT / lock)]
    packages += [p for lock in UV_LOCKS for p in uv_packages(ROOT / lock)]
    allow = json.loads((Path(__file__).parent / "allowlist.json").read_text(encoding="utf-8"))
    findings = audit(packages)
    open_ = [f for f in findings if not allowlisted(f, allow)]
    if "--json" in sys.argv:
        print(json.dumps({"packages": len(packages), "findings": findings}, ensure_ascii=False, indent=2))
    else:
        print(f"{len(packages)} paket ({len({(p.ecosystem, p.name) for p in packages})} nom) tekshirildi.")
        for f in findings:
            mark = "istisno" if f not in open_ else "OCHIQ"
            print(f"[{mark}] {f['ecosystem']} {f['package']} {f['version']} — {f['id']}: {f['summary']}")
            print(f"    tuzatilgan versiyalar: {f['fixed']}; lock: {f['locks']}")
        print("Zaiflik topilmadi." if not findings else f"Ochiq: {len(open_)}")
    return 1 if open_ else 0


if __name__ == "__main__":
    sys.exit(main())
