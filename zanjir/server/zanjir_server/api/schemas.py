"""So'rov/javob sxemalari (Pydantic v2). Noma'lum maydonlar rad etiladi."""

from __future__ import annotations

from datetime import datetime
from typing import Annotated

from pydantic import BaseModel, ConfigDict, Field, StringConstraints

from zanjir_server.security.passwords import MAX_PASSWORD_LENGTH, MIN_PASSWORD_LENGTH

Uuid = Annotated[str, StringConstraints(pattern=r"^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$")]
Name = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=200)]
Password = Annotated[str, StringConstraints(min_length=MIN_PASSWORD_LENGTH, max_length=MAX_PASSWORD_LENGTH)]
PhoneIn = Annotated[str, StringConstraints(min_length=9, max_length=20)]
SafetyGroup = Annotated[str, StringConstraints(pattern=r"^(I|II|III|IV|V)$")]


class Strict(BaseModel):
    model_config = ConfigDict(extra="forbid")


class RegisterIn(Strict):
    """Yangi laboratoriya (ixtiyoriy: ilovada oflayn yaratilgan `org_id`/`user_id` bilan — ADR-0011)."""

    org_id: Uuid | None = None
    user_id: Uuid | None = None
    org_name: Name
    license_no: Annotated[str, StringConstraints(max_length=64)] | None = None
    full_name: Name
    phone: PhoneIn
    password: Password
    role: Annotated[str, StringConstraints(pattern=r"^(ADMIN|LEAD)$")] = "LEAD"
    safety_group: SafetyGroup | None = None


class LoginIn(Strict):
    phone: PhoneIn
    password: Annotated[str, StringConstraints(min_length=1, max_length=MAX_PASSWORD_LENGTH)]


class RefreshIn(Strict):
    refresh_token: Annotated[str, StringConstraints(min_length=20, max_length=200)]


class AcceptInviteIn(Strict):
    code: Annotated[str, StringConstraints(strip_whitespace=True, to_upper=True, min_length=16, max_length=16)]
    user_id: Uuid | None = None
    full_name: Name
    phone: PhoneIn
    password: Password
    safety_group: SafetyGroup | None = None


class UserOut(BaseModel):
    id: str
    org_id: str
    full_name: str
    role: str
    safety_group: str | None


class TokensOut(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"  # noqa: S105 — parol emas, OAuth turi
    expires_in: int
    user: UserOut


class InviteIn(Strict):
    role: Annotated[str, StringConstraints(pattern=r"^(ADMIN|LEAD|ENGINEER|VIEWER)$")]
    ttl_hours: int = Field(default=72, ge=1)


class InviteOut(BaseModel):
    id: str
    role: str
    expires_at: datetime
    used_at: datetime | None
    code: str | None = None


class UserAdminOut(UserOut):
    phone: str
    deleted: bool


class RoleIn(Strict):
    role: Annotated[str, StringConstraints(pattern=r"^(ADMIN|LEAD|ENGINEER|VIEWER)$")]


class DeviceIn(Strict):
    id: Uuid | None = None
    public_key_ed25519: Annotated[str, StringConstraints(pattern=r"^[0-9a-f]{64}$")]
    sig_alg: Annotated[str, StringConstraints(max_length=32)] = "Ed25519"


class DeviceOut(BaseModel):
    id: str
    user_id: str
    public_key_ed25519: str
    sig_alg: str
    registered_at: datetime
    revoked_at: datetime | None
