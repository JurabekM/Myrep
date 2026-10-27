"""Test mijozi: tashkilot yaratish, taklif bilan foydalanuvchi qo'shish, so'rov yuborish."""

from __future__ import annotations

import secrets
import uuid
from dataclasses import dataclass, field
from typing import Any

from fastapi import FastAPI
from httpx import AsyncClient, Response

PASSWORD = "Juda-maxfiy-parol-1"  # noqa: S105 — faqat test


def phone() -> str:
    return "+99890" + "".join(secrets.choice("0123456789") for _ in range(7))


@dataclass
class User:
    id: str
    org_id: str
    role: str
    phone: str
    access: str
    refresh: str
    headers: dict[str, str] = field(default_factory=dict)

    def __post_init__(self) -> None:
        self.headers = {"authorization": f"Bearer {self.access}"}


class Api:
    def __init__(self, client: AsyncClient, app: FastAPI) -> None:
        self.c = client
        self.app = app

    async def register(self, role: str = "LEAD", **extra: Any) -> User:
        p = phone()
        body = {
            "org_name": "Elektrolab",
            "full_name": f"{role} F.I.Sh.",
            "phone": p,
            "password": PASSWORD,
            "role": role,
        }
        r = await self.c.post("/auth/register", json={**body, **extra})
        assert r.status_code == 201, r.text
        return self._user(r, p)

    async def invite(self, by: User, role: str, ttl_hours: int = 72) -> str:
        r = await self.c.post("/invites", json={"role": role, "ttl_hours": ttl_hours}, headers=by.headers)
        assert r.status_code == 201, r.text
        code: str = r.json()["code"]
        return code

    async def join(self, code: str, user_id: str | None = None) -> User:
        p = phone()
        body: dict[str, Any] = {"code": code, "full_name": "Yangi xodim", "phone": p, "password": PASSWORD}
        if user_id:
            body["user_id"] = user_id
        r = await self.c.post("/auth/accept-invite", json=body)
        assert r.status_code == 201, r.text
        return self._user(r, p)

    async def member(self, lead: User, role: str) -> User:
        admin_needed = role in ("ADMIN", "LEAD") and lead.role != "ADMIN"
        assert not admin_needed, "LEAD faqat ENGINEER/VIEWER taklif qiladi"
        return await self.join(await self.invite(lead, role))

    async def org(self) -> dict[str, User]:
        """Bir tashkilotda har bir roldan bittadan foydalanuvchi."""
        admin = await self.register("ADMIN", license_no="EL-1", license_valid_until="2027-12-31T00:00:00.000Z")
        users = {"ADMIN": admin}
        for role in ("LEAD", "ENGINEER", "VIEWER"):
            users[role] = await self.member(admin, role)
        return users

    async def device(self, user: User, public_key_hex: str, device_id: str | None = None) -> str:
        r = await self.c.post(
            "/devices",
            json={"id": device_id or str(uuid.uuid4()), "public_key_ed25519": public_key_hex},
            headers=user.headers,
        )
        assert r.status_code == 201, r.text
        did: str = r.json()["id"]
        return did

    @staticmethod
    def _user(r: Response, p: str) -> User:
        d = r.json()
        u = d["user"]
        return User(u["id"], u["org_id"], u["role"], p, d["access_token"], d["refresh_token"])
