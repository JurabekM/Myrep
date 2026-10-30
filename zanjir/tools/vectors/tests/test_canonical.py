"""Kanonik JSON (RFC 8785) — Dart bilan bir xil natijalar (test/crypto/canonical_json_test.dart)."""

from __future__ import annotations

import math
from datetime import UTC, datetime, timedelta, timezone

import pytest

from zanjir_refcrypto.canonical import canonical_json, canonical_json_bytes
from zanjir_refcrypto.hashing import sha256_hex


def test_keys_sorted_no_whitespace() -> None:
    value = {"b": 1, "a": [True, False, None], "c": {"z": "s", "y": 2}}
    assert canonical_json(value) == '{"a":[true,false,null],"b":1,"c":{"y":2,"z":"s"}}'


def test_keys_sorted_by_utf16_code_units() -> None:
    value = {"é": 1, "z": 2, "A": 3, "\U0001f600": 4, "דּ": 5}
    assert canonical_json(value) == '{"A":3,"z":2,"é":1,"\U0001f600":4,"דּ":5}'


def test_string_escaping() -> None:
    assert canonical_json('a"b\\c/\b\f\n\r\t\u0001\u001f') == r'"a\"b\\c/\b\f\n\r\t\u0001\u001f"'
    assert canonical_json("Ўзбек — ПУЭ €") == '"Ўзбек — ПУЭ €"'


def test_lone_surrogate_rejected() -> None:
    with pytest.raises(ValueError, match="surrogat"):
        canonical_json("\ud800")


@pytest.mark.parametrize(
    ("value", "expected"),
    [
        (0, "0"),
        (-0.0, "0"),
        (1, "1"),
        (-1, "-1"),
        (16.0, "16"),
        (2.5, "2.5"),
        (0.1, "0.1"),
        (-0.000001, "-0.000001"),
        (0.0000001, "1e-7"),
        (1e21, "1e+21"),
        (1e20, "100000000000000000000"),
        (123e-20, "1.23e-18"),
        (1.5e300, "1.5e+300"),
        (333333333.3333333, "333333333.3333333"),
        (4.000000000000001, "4.000000000000001"),
        (9007199254740991, "9007199254740991"),
        (5e-324, "5e-324"),
        (1.7976931348623157e308, "1.7976931348623157e+308"),
        (100.0, "100"),
        (0.001, "0.001"),
        (1e-27, "1e-27"),
        (1e30, "1e+30"),
    ],
)
def test_numbers_ecmascript(value: float, expected: str) -> None:
    assert canonical_json(value) == expected


@pytest.mark.parametrize("value", [math.nan, math.inf, -math.inf, 9007199254740992, -9007199254740992])
def test_bad_numbers_rejected(value: float) -> None:
    with pytest.raises(ValueError):
        canonical_json(value)


def test_bool_is_not_number() -> None:
    assert canonical_json([True, 1]) == "[true,1]"


def test_datetime_utc_milliseconds() -> None:
    assert canonical_json(datetime(2026, 10, 26, 7, 5, 3, 120999, tzinfo=UTC)) == '"2026-10-26T07:05:03.120Z"'
    assert canonical_json(datetime(5, 1, 1, tzinfo=UTC)) == '"0005-01-01T00:00:00.000Z"'
    with pytest.raises(ValueError, match="UTC"):
        canonical_json(datetime(2026, 1, 1))  # ataylab naive (vaqt zonasisiz)
    with pytest.raises(ValueError, match="UTC"):
        canonical_json(datetime(2026, 1, 1, tzinfo=timezone(timedelta(hours=5))))


def test_unsupported_rejected() -> None:
    with pytest.raises(ValueError):
        canonical_json(object())
    with pytest.raises(ValueError):
        canonical_json({1: "a"})
    with pytest.raises(ValueError):
        canonical_json((1, 2))


def test_utf8_bytes_and_sha256() -> None:
    assert canonical_json_bytes({"a": "ў"}) == '{"a":"ў"}'.encode()
    assert sha256_hex(b"abc") == "ba7816bf8f01cfea414140de5dae2223b00361a396177a9cb410ff61f20015ad"
    assert sha256_hex(b"") == "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"
