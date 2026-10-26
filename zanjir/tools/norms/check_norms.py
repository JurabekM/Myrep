"""Normalar to'plamini tekshirish (ADR-0004).

Oddiy rejim: har bir `norms/*.yaml` JSON Schema'ga mosligi va ID'lar takrorlanmasligi.
`--release` rejimi: qo'shimcha ravishda `reviewed_by` / `reviewed_at` to'ldirilgan va
`needs_verification` holatidagi norma qolmaganini talab qiladi.

Foydalanish: python -I check_norms.py [--release] <norms_dir>
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

import yaml
from jsonschema import Draft202012Validator


def _load_yaml(path: Path) -> Any:
    with path.open(encoding="utf-8") as f:
        return yaml.safe_load(f)


def check_norm_set(data: Any, validator: Draft202012Validator, *, release: bool) -> list[str]:
    """Bitta norm_set uchun xatolar ro'yxati (bo'sh — hammasi joyida)."""
    errors = [
        f"schema: {'/'.join(str(p) for p in e.absolute_path) or '<root>'}: {e.message}"
        for e in sorted(validator.iter_errors(data), key=lambda e: list(e.absolute_path))
    ]
    if errors:
        return errors

    seen: set[str] = set()
    for norm in data["norms"]:
        if norm["id"] in seen:
            errors.append(f"takrorlangan norma ID: {norm['id']}")
        seen.add(norm["id"])
        rule = norm["rule"]
        if rule["type"] == "range" and rule["min"] > rule["max"]:
            errors.append(f"{norm['id']}: range min > max")
        if norm["measurement_type"] == "INSULATION" and "test_voltage_v" not in norm:
            errors.append(f"{norm['id']}: izolyatsiya normasida test_voltage_v yo'q")

    if release:
        if not data["reviewed_by"].strip():
            errors.append("release: reviewed_by bo'sh — normalar litsenziyali muhandis tomonidan tekshirilmagan")
        if not data["reviewed_at"].strip():
            errors.append("release: reviewed_at bo'sh")
        unverified = [n["id"] for n in data["norms"] if n["status"] == "needs_verification"]
        if data["trip_multipliers"]["status"] == "needs_verification":
            unverified.append("trip_multipliers")
        if unverified:
            errors.append("release: needs_verification holatida: " + ", ".join(unverified))
    return errors


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("norms_dir", type=Path)
    parser.add_argument("--release", action="store_true", help="release darvozasi")
    args = parser.parse_args(argv)

    schema = json.loads((args.norms_dir / "schema.json").read_text(encoding="utf-8"))
    Draft202012Validator.check_schema(schema)
    validator = Draft202012Validator(schema)

    files = sorted(args.norms_dir.glob("*.yaml"))
    if not files:
        print(f"{args.norms_dir}: normalar fayli topilmadi", file=sys.stderr)
        return 1

    versions: dict[str, Path] = {}
    failed = False
    for path in files:
        data = _load_yaml(path)
        errors = check_norm_set(data, validator, release=args.release)
        if isinstance(data, dict) and not errors:
            prev = versions.get(data["version"])
            if prev is not None:
                errors.append(f"version {data['version']} {prev.name} da ham bor")
            versions[data["version"]] = path
        for err in errors:
            print(f"{path.name}: {err}", file=sys.stderr)
        failed = failed or bool(errors)
        if not errors:
            print(f"{path.name}: OK")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
