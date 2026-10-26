#!/usr/bin/env python3
"""NIST ACVP-Server vektorlaridan M-Pay ishlatadigan qismini ajratadi.

Manba: https://github.com/usnistgov/ACVP-Server — gen-val/json-files/<Algo>/internalProjection.json
(AQSh hukumati ishi, public domain). Faqat ML-KEM-768 va ML-DSA-65 (PQ Link to'plami), faqat biz
ishlatadigan interfeyslar (sof/pure, prehash va external-mu yo'q).

    python scripts/trim_acvp.py <yuklab-olingan-papka> testvectors/acvp
"""

import json
import pathlib
import sys

SRC = "https://github.com/usnistgov/ACVP-Server/tree/master/gen-val/json-files"


def load(d: pathlib.Path, name: str) -> dict:
    return json.loads((d / f"{name}.json").read_text(encoding="utf-8"))


def pick(doc: dict, keep, limit: int, fields) -> list:
    groups = []
    for g in doc["testGroups"]:
        if not keep(g):
            continue
        meta = {k: v for k, v in g.items() if k != "tests"}
        tests = [{k: t[k] for k in fields if k in t} for t in g["tests"][:limit]]
        groups.append({**meta, "tests": tests})
    return groups


def main() -> None:
    src, out = pathlib.Path(sys.argv[1]), pathlib.Path(sys.argv[2])
    out.mkdir(parents=True, exist_ok=True)
    jobs = {
        "ml-kem-768-keygen": ("ML-KEM-keyGen-FIPS203",
                              lambda g: g["parameterSet"] == "ML-KEM-768", 10,
                              ["tcId", "d", "z", "ek", "dk"]),
        "ml-kem-768-encapdecap": ("ML-KEM-encapDecap-FIPS203",
                                  lambda g: g["parameterSet"] == "ML-KEM-768", 10,
                                  ["tcId", "ek", "dk", "c", "k", "m", "testPassed", "reason"]),
        "ml-dsa-65-keygen": ("ML-DSA-keyGen-FIPS204",
                             lambda g: g["parameterSet"] == "ML-DSA-65", 10,
                             ["tcId", "seed", "pk", "sk"]),
        "ml-dsa-65-siggen": ("ML-DSA-sigGen-FIPS204",
                             lambda g: g["parameterSet"] == "ML-DSA-65" and not g["externalMu"]
                             and g["preHash"] in ("pure", "none"), 5,
                             ["tcId", "sk", "pk", "message", "context", "rnd", "signature"]),
        "ml-dsa-65-sigver": ("ML-DSA-sigVer-FIPS204",
                             lambda g: g["parameterSet"] == "ML-DSA-65" and not g["externalMu"]
                             and g["preHash"] in ("pure", "none"), 15,
                             ["tcId", "pk", "message", "context", "signature", "testPassed", "reason"]),
    }
    for name, (algo, keep, limit, fields) in jobs.items():
        doc = load(src, algo)
        res = {
            "source": f"{SRC}/{algo}/internalProjection.json",
            "retrieved": "2026-10-23",
            "algorithm": doc["algorithm"],
            "mode": doc["mode"],
            "revision": doc["revision"],
            "testGroups": pick(doc, keep, limit, fields),
        }
        n = sum(len(g["tests"]) for g in res["testGroups"])
        (out / f"{name}.json").write_text(json.dumps(res, indent=1) + "\n", encoding="utf-8")
        print(f"{name}: {len(res['testGroups'])} guruh, {n} test")


if __name__ == "__main__":
    main()
