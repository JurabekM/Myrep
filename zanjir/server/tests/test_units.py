"""Bazasiz unit testlar: protokol qoidalari, sim formati, tokenlar, telefon, rate limiter, rollar."""

from __future__ import annotations

import base64
from datetime import UTC, datetime
from typing import Any

import pytest

from zanjir_server.middleware import RateLimiter
from zanjir_server.security.phone import normalize_phone
from zanjir_server.security.roles import INVITABLE, Role
from zanjir_server.security.tokens import AccessClaims, AccessTokens, TokenError, new_invite_code
from zanjir_server.sync.protocol_rules import protocol_payload_violation
from zanjir_server.sync.wire import WireError, from_wire, iso, normalized


def payload(**over: Any) -> dict[str, Any]:
    p: dict[str, Any] = {
        "schema": "zanjir.protocol/1",
        "norm_set": {"reviewed_by": "Muhandis"},
        "instruments": [{"id": "i1", "verified_until": "2027-01-01T00:00:00.000Z"}],
        "measurements": [
            {"id": "m1", "instrument_id": "i1", "created_at": "2026-10-26T08:00:00.000Z", "verdict": "PASS"}
        ],
        "lab": {"license_no": "EL-1", "license_valid_until": "2027-12-31T00:00:00.000Z"},
        "signed_at": "2026-10-27T08:00:00.000Z",
        "lead_comment": None,
    }
    p.update(over)
    return p


@pytest.mark.parametrize(
    ("over", "role", "expected"),
    [
        ({}, "ENGINEER", None),
        ({"schema": "x"}, "LEAD", "unknown_schema"),
        ({"norm_set": None}, "LEAD", "norms_not_reviewed"),
        ({"norm_set": {"reviewed_by": "  "}}, "LEAD", "norms_not_reviewed"),
        ({"measurements": []}, "LEAD", "no_measurements"),
        ({"instruments": None}, "LEAD", "no_measurements"),
        ({"measurements": ["x"]}, "LEAD", "invalid_payload"),
        ({"instruments": [{"id": "i1", "verified_until": "2026-10-25T00:00:00.000Z"}]}, "LEAD", "instrument_expired"),
        ({"instruments": [{"id": "i1", "verified_until": None}]}, "LEAD", "instrument_expired"),
        ({"instruments": [{"id": "i1", "verified_until": "yaroqsiz"}]}, "LEAD", "instrument_expired"),
        ({"instruments": []}, "LEAD", "instrument_expired"),
        ({"lab": {"license_no": "EL-1", "license_valid_until": "2026-10-26T00:00:00.000Z"}}, "LEAD", "license_invalid"),
        ({"lab": {"license_no": " ", "license_valid_until": "2027-12-31T00:00:00.000Z"}}, "LEAD", "license_invalid"),
        ({"lab": {"license_valid_until": "2027-12-31T00:00:00.000Z"}}, "LEAD", "license_invalid"),
        ({"lab": None}, "LEAD", "license_invalid"),
        ({"signed_at": None}, "LEAD", "license_invalid"),
    ],
)
def test_protocol_rules(over: dict[str, Any], role: str, expected: str | None) -> None:
    assert protocol_payload_violation(payload(**over), role) == expected


@pytest.mark.parametrize(
    ("at_record", "expected"),
    [
        (None, "instrument_expired"),
        ("2026-10-25T00:00:00.000Z", "instrument_expired"),
        ("2026-10-26T00:00:00.000Z", None),
    ],
)
def test_protocol_rules_instrument_validity_at_record(at_record: str | None, expected: str | None) -> None:
    """O'lchov paytida yozib qo'yilgan muddat ham tekshiriladi (asbob keyin qayta qiyoslangan bo'lsa ham)."""
    m = {"id": "m1", "instrument_id": "i1", "created_at": "2026-10-26T08:00:00.000Z", "verdict": "PASS"}
    assert (
        protocol_payload_violation(payload(measurements=[{**m, "instrument_verified_until": at_record}]), "LEAD")
        == expected
    )


def test_protocol_rules_needs_review() -> None:
    nr = [{"id": "m1", "instrument_id": "i1", "created_at": "2026-10-26T08:00:00.000Z", "verdict": "NEEDS_REVIEW"}]
    assert protocol_payload_violation(payload(measurements=nr), "ENGINEER") == "needs_review_requires_lead"
    assert protocol_payload_violation(payload(measurements=nr), "LEAD") == "lead_comment_required"
    assert protocol_payload_violation(payload(measurements=nr, lead_comment=" "), "LEAD") == "lead_comment_required"
    assert protocol_payload_violation(payload(measurements=nr, lead_comment="Sabab"), "LEAD") is None


def site(**over: Any) -> dict[str, Any]:
    row: dict[str, Any] = {
        "id": "s",
        "org_id": "o",
        "created_at": "2026-10-27T08:00:00.000+05:00",
        "updated_at": "2026-10-27T08:00:00Z",
        "rev": 1,
        "deleted": False,
        "name": "Obyekt",
        "earthing_system": "TN-S",
        "u0_volts": 220,
    }
    row.update(over)
    return row


def test_wire_parse_and_normalize() -> None:
    v = from_wire("site", site())
    assert v["created_at"] == datetime(2026, 10, 27, 3, tzinfo=UTC)
    assert v["address"] is None and v["u0_volts"] == 220.0
    n = normalized("site", v)
    assert n["created_at"] == "2026-10-27T03:00:00.000Z"
    doc = from_wire(
        "protocol_document",
        {
            "id": "d",
            "org_id": "o",
            "created_at": iso(v["created_at"]),
            "updated_at": iso(v["created_at"]),
            "rev": 1,
            "protocol_id": "p",
            "payload_json": "{}",
            "pdf": base64.b64encode(b"%PDF").decode(),
        },
    )
    assert doc["pdf"] == b"%PDF"
    assert normalized("protocol_document", doc)["pdf"] == base64.b64encode(b"%PDF").decode()


@pytest.mark.parametrize(
    ("table", "over", "reason"),
    [
        ("site", {"name": None}, "null:site.name"),
        ("site", {"deleted": "false"}, "type:site.deleted"),
        ("site", {"rev": True}, "type:site.rev"),
        ("site", {"rev": 1.5}, "type:site.rev"),
        ("site", {"u0_volts": float("inf")}, "type:site.u0_volts"),
        ("site", {"u0_volts": False}, "type:site.u0_volts"),
        ("site", {"created_at": "2026-10-27"}, "type:site.created_at"),
        ("site", {"created_at": 5}, "type:site.created_at"),
        ("site", {"name": 5}, "type:site.name"),
        ("site", {"earthing_system": "TN-C-S-XX"}, "too_long:site.earthing_system"),
    ],
)
def test_wire_errors(table: str, over: dict[str, Any], reason: str) -> None:
    with pytest.raises(WireError) as e:
        from_wire(table, site(**over))
    assert e.value.reason == reason


def test_wire_json_and_binary_errors() -> None:
    base = {
        "id": "n",
        "org_id": "o",
        "created_at": "2026-10-27T08:00:00Z",
        "updated_at": "2026-10-27T08:00:00Z",
        "rev": 1,
        "deleted": False,
        "site_id": "s",
        "kind": "CABLE",
        "label": "W1",
        "verified": False,
    }
    with pytest.raises(WireError, match=r"type:node\.attrs"):
        from_wire("node", {**base, "attrs": []})
    plan = {
        **{k: base[k] for k in ("id", "org_id", "created_at", "updated_at", "rev", "deleted")},
        "site_id": "s",
        "solver_version": "1",
        "graph_snapshot_hash": "a",
        "steps": [],
        "warnings": [],
        "status": "DRAFT",
    }
    with pytest.raises(WireError, match=r"type:isolation_plan\.target_node_ids"):
        from_wire("isolation_plan", {**plan, "target_node_ids": {}})
    doc = {
        "id": "d",
        "org_id": "o",
        "created_at": "2026-10-27T08:00:00Z",
        "updated_at": "2026-10-27T08:00:00Z",
        "rev": 1,
        "protocol_id": "p",
        "payload_json": "{}",
    }
    for bad in ("@@@", 5):
        with pytest.raises(WireError, match=r"type:protocol_document\.pdf"):
            from_wire("protocol_document", {**doc, "pdf": bad})


def test_tokens() -> None:
    now = datetime(2026, 10, 27, tzinfo=UTC)
    t = AccessTokens("s" * 40, 900, clock=lambda: now)
    claims = AccessClaims("u", "o", "LEAD")
    assert t.decode(t.issue(claims)) == claims
    future = AccessTokens("s" * 40, 900, clock=lambda: now.replace(year=2027))
    with pytest.raises(TokenError, match="issued_in_future"):
        t.decode(future.issue(claims))
    with pytest.raises(TokenError):
        t.decode("a.b.c")
    import jwt

    refresh_like = jwt.encode(
        {
            "iss": "zanjir",
            "sub": "u",
            "org": "o",
            "typ": "refresh",
            "iat": int(now.timestamp()),
            "exp": int(now.timestamp()) + 60,
        },
        "s" * 40,
        algorithm="HS256",
    )
    with pytest.raises(TokenError, match="wrong_type"):
        t.decode(refresh_like)
    none_alg = jwt.encode(
        {"iss": "zanjir", "sub": "u", "org": "o", "typ": "access", "iat": 1, "exp": 2**40}, "", algorithm="none"
    )
    with pytest.raises(TokenError):
        t.decode(none_alg)
    code = new_invite_code()
    assert len(code) == 16 and not set(code) & set("01OI")


def test_phone() -> None:
    assert normalize_phone("+998 90 123-45-67") == "+998901234567"
    assert normalize_phone("998901234567") == "+998901234567"
    assert normalize_phone("(90) 123 45 67") is None
    assert normalize_phone("+7 900 123 45 67") is None


def test_rate_limiter_window() -> None:
    t = [0.0]
    rl = RateLimiter(clock=lambda: t[0])
    assert [rl.hit("a", "ip", 2) for _ in range(3)] == [None, None, 60]
    assert rl.hit("b", "ip", 2) is None
    t[0] = 61.0
    assert rl.hit("a", "ip", 2) is None


def test_roles() -> None:
    assert Role.ADMIN.at_least(Role.LEAD) and not Role.VIEWER.at_least(Role.ENGINEER)
    assert INVITABLE[Role.LEAD] == {Role.ENGINEER, Role.VIEWER}
    assert not INVITABLE[Role.ENGINEER]


def test_login_guard_memory_bounded() -> None:
    """L5: tekshiruv yozuv yaratmaydi; chegaradan oshganda muddati o'tgan kalitlar tozalanadi."""
    from zanjir_server.security.login_guard import LoginGuard

    now = [0.0]
    g = LoginGuard(max_failures=2, window_seconds=60, clock=lambda: now[0])
    assert not g.blocked("+998900000000")
    assert g._failures == {}
    for i in range(100_001):
        g.failed(f"k{i}")
    now[0] = 120.0
    g.failed("yangi")
    assert list(g._failures) == ["yangi"]
    g.failed("yangi")
    assert g.blocked("yangi")
    g.succeeded("yangi")
    assert not g.blocked("yangi")


def test_rate_limiter_sweeps_once_per_window() -> None:
    """Chegaradan oshganda tozalash oynaga bir marta (har so'rovda butun lug'at aylanmaydi)."""
    now = [0.0]
    r = RateLimiter(clock=lambda: now[0])
    for i in range(100_001):
        r.hit("b", f"ip{i}", 10)
    swept = r._hits
    r.hit("b", "yana", 10)
    assert r._hits is swept  # shu oynada qayta tozalanmadi
    now[0] = 61.0
    r.hit("b", "keyingi", 10)
    assert list(r._hits) == [("b", "keyingi")]
