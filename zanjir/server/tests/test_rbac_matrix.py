"""RBAC matritsasi (prompt 7-bo'lim): har bir endpoint × har bir rol (+ anonim) — docs/SECURITY.md jadvali.

Matritsada yo'q endpoint qo'shilsa — `test_matrix_covers_every_route` yiqiladi.
"""

from __future__ import annotations

import uuid
from typing import Any

import pytest
from fastapi.routing import APIRoute

from tests.support.api import Api, User
from zanjir_server.main import ROUTERS

ROLES = ("VIEWER", "ENGINEER", "LEAD", "ADMIN")
LEVEL = {r: i for i, r in enumerate(ROLES)}
X = str(uuid.uuid4())

# (metod, yo'l, minimal rol yoki None — ochiq, so'rov tanasi)
MATRIX: list[tuple[str, str, str | None, dict[str, Any] | None]] = [
    ("POST", "/auth/register", None, {}),
    ("POST", "/auth/login", None, {"phone": "+998900000000", "password": "x"}),
    ("POST", "/auth/refresh", None, {"refresh_token": "x" * 40}),
    ("POST", "/auth/logout", None, {"refresh_token": "x" * 40}),
    ("POST", "/auth/accept-invite", None, {}),
    ("POST", "/auth/otp/request", None, None),
    ("GET", "/v/{qr_token}", None, None),
    ("GET", "/v/{qr_token}/pdf", None, None),
    ("GET", "/healthz", None, None),
    ("GET", "/readyz", None, None),
    ("GET", "/metrics", None, None),
    ("GET", "/me", "VIEWER", None),
    ("GET", "/devices", "VIEWER", None),
    ("GET", "/sync/pull", "VIEWER", None),
    ("POST", "/devices", "ENGINEER", {"public_key_ed25519": "ef" * 32}),
    ("POST", "/sync/push", "ENGINEER", {"ops": [{"client_op_id": "x", "table": "site", "row": {}}]}),
    ("POST", "/invites", "LEAD", {"role": "VIEWER"}),
    ("GET", "/invites", "LEAD", None),
    ("GET", "/users", "LEAD", None),
    ("PATCH", "/users/{user_id}/role", "ADMIN", {"role": "VIEWER"}),
    ("DELETE", "/users/{user_id}", "ADMIN", None),
    ("POST", "/devices/{device_id}/revoke", "ADMIN", None),
]

AUTH_CODES = {"not_authenticated", "invalid_token", "forbidden_role"}


def test_matrix_covers_every_route() -> None:
    routes: dict[tuple[str, str], str | None] = {}
    for r in (route for router in ROUTERS for route in router.routes):
        assert isinstance(r, APIRoute)
        min_role = None
        for dep in r.dependant.dependencies:
            for sub in [dep, *dep.dependencies]:
                role = getattr(sub.call, "min_role", None)
                if role is not None:
                    min_role = str(role)
        for m in r.methods or ():
            routes[(m, r.path)] = min_role
    expected = {(m, p): role for m, p, role, _ in MATRIX}
    assert routes == expected


def _code(body: Any) -> str | None:
    detail = body.get("detail") if isinstance(body, dict) else None
    return detail.get("code") if isinstance(detail, dict) else None


@pytest.mark.parametrize(("method", "path", "min_role", "body"), MATRIX, ids=[f"{m} {p}" for m, p, _, _ in MATRIX])
async def test_rbac(api: Api, method: str, path: str, min_role: str | None, body: dict[str, Any] | None) -> None:
    users = await api.org()
    url = path.format(qr_token="0" * 32, user_id=X, device_id=X)
    callers: list[tuple[str, User | None]] = [("ANON", None), *((r, users[r]) for r in ROLES)]
    for name, user in callers:
        headers = user.headers if user else {}
        r = await api.c.request(method, url, json=body, headers=headers)
        code = _code(r.json()) if r.headers.get("content-type", "").startswith("application/json") else None
        if min_role is None:
            assert code not in AUTH_CODES, (name, r.status_code, code)
        elif user is None:
            assert (r.status_code, code) == (401, "not_authenticated"), name
        elif LEVEL[name] < LEVEL[min_role]:
            assert (r.status_code, code) == (403, "forbidden_role"), name
        else:
            assert r.status_code not in (401, 403), (name, r.status_code, r.text)
