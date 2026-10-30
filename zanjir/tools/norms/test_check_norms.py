"""check_norms.py testlari: haqiqiy norms/ papkasi va buzilgan to'plamlar."""

from __future__ import annotations

import copy
import json
from pathlib import Path
from typing import Any

import pytest
import yaml
from jsonschema import Draft202012Validator

from check_norms import check_norm_set, main, review_warnings

NORMS_DIR = Path(__file__).resolve().parents[2] / "norms"


@pytest.fixture(scope="module")
def validator() -> Draft202012Validator:
    schema = json.loads((NORMS_DIR / "schema.json").read_text(encoding="utf-8"))
    Draft202012Validator.check_schema(schema)
    return Draft202012Validator(schema)


@pytest.fixture
def v0() -> Any:
    return yaml.safe_load((NORMS_DIR / "v0.yaml").read_text(encoding="utf-8"))


def test_real_norms_dir_passes() -> None:
    assert main([str(NORMS_DIR)]) == 0


def test_v0_is_valid(validator: Draft202012Validator, v0: Any) -> None:
    assert check_norm_set(v0, validator) == []


def test_v0_contains_all_prompt_norms(v0: Any) -> None:
    ids = {n["id"] for n in v0["norms"]}
    expected = {
        "INS-WIRING", "INS-SWGR", "INS-SECONDARY", "INS-CABLE-LV",
        "LOOP-TN-FINAL", "LOOP-TN-DIST",
        "LOOP-TN-OTHER-U0-127", "LOOP-TN-OTHER-U0-380", "LOOP-TN-OTHER-U0-GT380",
        "RCD-1X", "RCD-1X-S", "RCD-2X", "RCD-2X-S", "RCD-5X", "RCD-5X-S", "RCD-RAMP",
        "EARTH-NEUTRAL-380", "EARTH-REPEAT-380-TOTAL", "EARTH-REPEAT-380-SINGLE", "EARTH-TT",
        "BOND-CONTACT",
    }  # fmt: skip
    assert ids == expected


def test_v0_is_not_reviewed(v0: Any) -> None:
    # Claude reviewed_by ni hech qachon to'ldirmaydi (CLAUDE.md, 11-qoida).
    assert v0["reviewed_by"] == ""
    assert v0["reviewed_at"] == ""


def test_duplicate_id_rejected(validator: Draft202012Validator, v0: Any) -> None:
    data = copy.deepcopy(v0)
    data["norms"].append(copy.deepcopy(data["norms"][0]))
    errors = check_norm_set(data, validator)
    assert any("takrorlangan" in e for e in errors)


def test_unknown_field_rejected(validator: Draft202012Validator, v0: Any) -> None:
    data = copy.deepcopy(v0)
    data["norms"][0]["magic"] = 1
    assert check_norm_set(data, validator)


def test_unknown_node_kind_rejected(validator: Draft202012Validator, v0: Any) -> None:
    data = copy.deepcopy(v0)
    data["norms"][0]["applies_to"]["node_kinds"] = ["TOASTER"]
    assert check_norm_set(data, validator)


def test_range_min_gt_max_rejected(validator: Draft202012Validator, v0: Any) -> None:
    data = copy.deepcopy(v0)
    rcd_s = next(n for n in data["norms"] if n["id"] == "RCD-1X-S")
    rcd_s["rule"]["min"], rcd_s["rule"]["max"] = 500, 130
    errors = check_norm_set(data, validator)
    assert any("range min > max" in e for e in errors)


def test_insulation_without_test_voltage_rejected(validator: Draft202012Validator, v0: Any) -> None:
    data = copy.deepcopy(v0)
    del data["norms"][0]["test_voltage_v"]
    errors = check_norm_set(data, validator)
    assert any("test_voltage_v" in e for e in errors)


def test_review_status_is_warning_not_error(validator: Draft202012Validator, v0: Any) -> None:
    # 1-darvoza olib tashlangan (ADR-0019): tekshirilmagan normalar release'ni to'xtatmaydi, lekin ogohlantiriladi.
    assert check_norm_set(copy.deepcopy(v0), validator) == []
    warnings = review_warnings(v0)
    assert any("reviewed_by" in w for w in warnings)
    assert any("needs_verification" in w for w in warnings)


def test_no_warnings_when_fully_reviewed(v0: Any) -> None:
    data = copy.deepcopy(v0)
    data["reviewed_by"] = "Test Muhandis, guvohnoma 000"
    data["reviewed_at"] = "2026-01-01"
    data["trip_multipliers"]["status"] = "source_seen"
    for n in data["norms"]:
        n["status"] = "source_seen"
    assert review_warnings(data) == []


def test_blank_reviewer_warned(v0: Any) -> None:
    data = copy.deepcopy(v0)
    data["reviewed_by"] = "   "
    data["reviewed_at"] = "2026-01-01"
    assert any("reviewed_by" in w for w in review_warnings(data))


def test_release_mode_passes_with_warnings() -> None:
    assert main(["--release", str(NORMS_DIR)]) == 0


def test_empty_dir_fails(tmp_path: Path) -> None:
    (tmp_path / "schema.json").write_text((NORMS_DIR / "schema.json").read_text(encoding="utf-8"), encoding="utf-8")
    assert main([str(tmp_path)]) == 1


def test_duplicate_version_across_files_fails(tmp_path: Path) -> None:
    (tmp_path / "schema.json").write_text((NORMS_DIR / "schema.json").read_text(encoding="utf-8"), encoding="utf-8")
    text = (NORMS_DIR / "v0.yaml").read_text(encoding="utf-8")
    (tmp_path / "a.yaml").write_text(text, encoding="utf-8")
    (tmp_path / "b.yaml").write_text(text, encoding="utf-8")
    assert main([str(tmp_path)]) == 1
