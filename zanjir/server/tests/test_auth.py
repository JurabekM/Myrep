"""Kirish, tokenlar, takliflar, foydalanuvchi va qurilma boshqaruvi."""

from __future__ import annotations

import uuid

from pydantic import SecretStr

from tests.conftest import Clock, make_settings
from tests.support.api import PASSWORD, Api, phone
from zanjir_server.main import create_app
from zanjir_server.middleware import RateLimiter
from zanjir_server.security.tokens import AccessClaims


async def test_register_login_me(api: Api) -> None:
    lead = await api.register("LEAD", safety_group="V")
    r = await api.c.get("/me", headers=lead.headers)
    assert r.status_code == 200
    assert r.json()["role"] == "LEAD"
    assert r.json()["safety_group"] == "V"
    # Telefon turli yozilishda ham.
    raw = f"998 {lead.phone[4:6]} {lead.phone[6:9]}-{lead.phone[9:11]}-{lead.phone[11:]}"
    r = await api.c.post("/auth/login", json={"phone": raw, "password": PASSWORD})
    assert r.status_code == 200, r.text
    assert r.json()["expires_in"] == 15 * 60


async def test_register_with_offline_ids_and_conflicts(api: Api) -> None:
    """Ilovada oflayn yaratilgan laboratoriya o'z ID lari bilan ro'yxatdan o'tadi (ADR-0011)."""
    org_id, user_id = str(uuid.uuid4()), str(uuid.uuid4())
    u = await api.register(
        "ADMIN", org_id=org_id, user_id=user_id, license_no="EL-1", license_valid_until="2027-12-31T00:00:00.000Z"
    )
    assert (u.org_id, u.id) == (org_id, user_id)
    org = (await api.c.get("/sync/pull", headers=u.headers)).json()["changes"][0]["row"]
    assert (org["license_no"], org["license_valid_until"]) == ("EL-1", "2027-12-31T00:00:00.000Z")
    body = {"org_name": "X", "full_name": "Y", "password": PASSWORD, "org_id": org_id}
    r = await api.c.post("/auth/register", json={**body, "phone": phone()})
    assert r.status_code == 409
    r = await api.c.post(
        "/auth/register", json={"org_name": "X", "full_name": "Y", "password": PASSWORD, "phone": u.phone}
    )
    assert r.status_code == 409
    for bad in (
        {"role": "ENGINEER"},
        {"phone": "12345"},
        {"password": "qisqa"},
        {"org_id": "not-a-uuid"},
        {"extra": 1},
    ):
        r = await api.c.post(
            "/auth/register", json={"org_name": "X", "full_name": "Y", "password": PASSWORD, "phone": phone(), **bad}
        )
        assert r.status_code == 422, bad


async def test_registration_closed_by_default(app_url: str) -> None:
    from httpx import ASGITransport, AsyncClient

    app = create_app(make_settings(app_url, registration_open=False))
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://t") as c:
        r = await c.post(
            "/auth/register", json={"org_name": "X", "full_name": "Y", "phone": phone(), "password": PASSWORD}
        )
    assert r.status_code == 403
    assert r.json()["detail"]["code"] == "registration_closed"
    await app.state.ctx.db.dispose()


async def test_login_errors_are_uniform(api: Api) -> None:
    lead = await api.register()
    for body in (
        {"phone": lead.phone, "password": "Noto'g'ri-parol"},
        {"phone": phone(), "password": PASSWORD},
        {"phone": "yaroqsiz-raqam", "password": PASSWORD},
    ):
        r = await api.c.post("/auth/login", json=body)
        assert r.status_code == 401
        assert r.json() == {"detail": {"code": "invalid_credentials"}}


async def test_access_token_expires_after_15_minutes(api: Api, clock: Clock) -> None:
    lead = await api.register()
    clock.advance(minutes=14)
    assert (await api.c.get("/me", headers=lead.headers)).status_code == 200
    clock.advance(minutes=2)
    r = await api.c.get("/me", headers=lead.headers)
    assert r.status_code == 401
    assert r.json()["detail"]["code"] == "invalid_token"
    for header in ("Bearer", "Basic abc", f"Bearer {lead.access}x", ""):
        assert (await api.c.get("/me", headers={"authorization": header})).status_code == 401


async def test_token_with_other_secret_rejected(api: Api, app_url: str) -> None:
    lead = await api.register()
    other = create_app(make_settings(app_url, jwt_secret=SecretStr("z" * 48)))
    forged = other.state.ctx.tokens.issue(AccessClaims(lead.id, lead.org_id, "ADMIN"))
    assert (await api.c.get("/me", headers={"authorization": f"Bearer {forged}"})).status_code == 401
    await other.state.ctx.db.dispose()


async def test_refresh_rotation_and_reuse_detection(api: Api) -> None:
    lead = await api.register()
    r1 = await api.c.post("/auth/refresh", json={"refresh_token": lead.refresh})
    assert r1.status_code == 200
    new_refresh = r1.json()["refresh_token"]
    assert new_refresh != lead.refresh
    # Eski token qayta keldi — o'g'irlik belgisi: butun oila bekor qilinadi, yangisi ham ishlamaydi.
    r2 = await api.c.post("/auth/refresh", json={"refresh_token": lead.refresh})
    assert r2.json()["detail"]["code"] == "refresh_reused"
    r3 = await api.c.post("/auth/refresh", json={"refresh_token": new_refresh})
    assert r3.status_code == 401
    assert r3.json()["detail"]["code"] == "invalid_refresh"
    # Boshqa sessiya (yangi kirish) ta'sirlanmaydi.
    r = await api.c.post("/auth/login", json={"phone": lead.phone, "password": PASSWORD})
    assert (await api.c.post("/auth/refresh", json={"refresh_token": r.json()["refresh_token"]})).status_code == 200


async def test_refresh_expiry_and_logout(api: Api, clock: Clock) -> None:
    lead = await api.register()
    r = await api.c.post("/auth/login", json={"phone": lead.phone, "password": PASSWORD})
    second = r.json()["refresh_token"]
    assert (await api.c.post("/auth/logout", json={"refresh_token": lead.refresh})).status_code == 204
    assert (await api.c.post("/auth/refresh", json={"refresh_token": lead.refresh})).status_code == 401
    assert (await api.c.post("/auth/logout", json={"refresh_token": "x" * 40})).status_code == 204
    clock.advance(days=31)
    r = await api.c.post("/auth/refresh", json={"refresh_token": second})
    assert r.json()["detail"]["code"] == "refresh_expired"


async def test_invites(api: Api, clock: Clock) -> None:
    admin = await api.register("ADMIN")
    lead = await api.member(admin, "LEAD")
    # LEAD faqat ENGINEER/VIEWER taklif qiladi.
    for role, ok in (("ENGINEER", True), ("VIEWER", True), ("LEAD", False), ("ADMIN", False)):
        r = await api.c.post("/invites", json={"role": role}, headers=lead.headers)
        assert (r.status_code == 201) is ok, role
    assert (
        await api.c.post("/invites", json={"role": "VIEWER", "ttl_hours": 24 * 30}, headers=lead.headers)
    ).status_code == 422
    code = await api.invite(lead, "ENGINEER", ttl_hours=1)
    user_id = str(uuid.uuid4())
    eng = await api.join(code.lower(), user_id=user_id)
    assert (eng.id, eng.role, eng.org_id) == (user_id, "ENGINEER", admin.org_id)
    # Bir martalik.
    r = await api.c.post(
        "/auth/accept-invite", json={"code": code, "full_name": "X", "phone": phone(), "password": PASSWORD}
    )
    assert r.status_code == 400
    # Muddati o'tgan.
    code2 = await api.invite(lead, "VIEWER", ttl_hours=1)
    clock.advance(hours=2)
    r = await api.c.post(
        "/auth/accept-invite", json={"code": code2, "full_name": "X", "phone": phone(), "password": PASSWORD}
    )
    assert r.json()["detail"]["code"] == "invalid_invite"
    # 2 soatdan keyin access token muddati o'tgan — qayta kirish.
    relog = await api.c.post("/auth/login", json={"phone": lead.phone, "password": PASSWORD})
    headers = {"authorization": f"Bearer {relog.json()['access_token']}"}
    invites = (await api.c.get("/invites", headers=headers)).json()
    assert all("code" not in i or i["code"] is None for i in invites)
    assert len(invites) >= 4


async def test_users_roles_and_delete(api: Api) -> None:
    users = await api.org()
    admin, eng = users["ADMIN"], users["ENGINEER"]
    listed = (await api.c.get("/users", headers=users["LEAD"].headers)).json()
    assert {u["role"] for u in listed} == {"ADMIN", "LEAD", "ENGINEER", "VIEWER"}
    assert all("password_hash" not in u for u in listed)
    r = await api.c.patch(f"/users/{eng.id}/role", json={"role": "LEAD"}, headers=admin.headers)
    assert r.json()["role"] == "LEAD"
    # Rol bazadan olinadi — eski token bilan ham yangi rol amal qiladi.
    assert (await api.c.get("/users", headers=eng.headers)).status_code == 200
    assert (
        await api.c.patch(f"/users/{admin.id}/role", json={"role": "VIEWER"}, headers=admin.headers)
    ).status_code == 422
    assert (
        await api.c.patch(f"/users/{uuid.uuid4()}/role", json={"role": "VIEWER"}, headers=admin.headers)
    ).status_code == 404
    pk = "ab" * 32
    dev = await api.device(eng, pk)
    assert (await api.c.delete(f"/users/{eng.id}", headers=admin.headers)).status_code == 204
    assert (await api.c.get("/me", headers=eng.headers)).status_code == 401
    assert (await api.c.post("/auth/refresh", json={"refresh_token": eng.refresh})).status_code == 401
    assert (await api.c.post("/auth/login", json={"phone": eng.phone, "password": PASSWORD})).status_code == 401
    devices = {d["id"]: d for d in (await api.c.get("/devices", headers=admin.headers)).json()}
    assert devices[dev]["revoked_at"] is not None
    assert (await api.c.delete(f"/users/{admin.id}", headers=admin.headers)).status_code == 422


async def test_devices(api: Api) -> None:
    users = await api.org()
    eng, admin = users["ENGINEER"], users["ADMIN"]
    dev = await api.device(eng, "cd" * 32)
    r = await api.c.post("/devices", json={"id": dev, "public_key_ed25519": "cd" * 32}, headers=eng.headers)
    assert r.status_code == 409
    r = await api.c.post("/devices", json={"public_key_ed25519": "xyz"}, headers=eng.headers)
    assert r.status_code == 422
    r = await api.c.post("/devices", json={"public_key_ed25519": "cd" * 32, "sig_alg": "RSA"}, headers=eng.headers)
    assert r.json()["detail"]["code"] == "unsupported_sig_alg"
    r = await api.c.post(f"/devices/{dev}/revoke", headers=admin.headers)
    assert r.json()["revoked_at"] is not None
    assert (await api.c.post(f"/devices/{uuid.uuid4()}/revoke", headers=admin.headers)).status_code == 404
    # Boshqa tashkilot qurilmasi ko'rinmaydi va bekor qilinmaydi.
    other = await api.register("ADMIN")
    assert (await api.c.post(f"/devices/{dev}/revoke", headers=other.headers)).status_code == 404
    assert dev not in {d["id"] for d in (await api.c.get("/devices", headers=other.headers)).json()}


async def test_otp_disabled(api: Api) -> None:
    r = await api.c.post("/auth/otp/request")
    assert r.status_code == 404
    assert r.json()["detail"]["code"] == "otp_disabled"


async def test_auth_rate_limit(app_url: str) -> None:
    from httpx import ASGITransport, AsyncClient

    app = create_app(make_settings(app_url, rate_limit_auth_per_minute=3), rate_limiter=RateLimiter(clock=lambda: 0.0))
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://t") as c:
        codes = [(await c.post("/auth/login", json={"phone": phone(), "password": "x"})).status_code for _ in range(5)]
        assert codes == [401, 401, 401, 429, 429]
        r = await c.post("/auth/login", json={"phone": phone(), "password": "x"})
        assert int(r.headers["retry-after"]) >= 1
        assert (await c.get("/healthz")).status_code == 200
    await app.state.ctx.db.dispose()
