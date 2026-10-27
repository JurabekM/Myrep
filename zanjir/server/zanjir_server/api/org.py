"""Tashkilot boshqaruvi: takliflar (LEAD/ADMIN), foydalanuvchilar (LEAD ko'radi, ADMIN o'zgartiradi), qurilmalar."""

from __future__ import annotations

import uuid
from datetime import timedelta

from fastapi import APIRouter
from sqlalchemy import select, update
from sqlalchemy.exc import IntegrityError

from zanjir_server.api.deps import Admin, Ctx, Engineer, Lead, Viewer, fail
from zanjir_server.api.schemas import DeviceIn, DeviceOut, InviteIn, InviteOut, RoleIn, UserAdminOut
from zanjir_server.crypto.signing import SUPPORTED_SIG_ALGS
from zanjir_server.db.models import AppUser, Device, Invite, RefreshToken
from zanjir_server.security.roles import INVITABLE, Role
from zanjir_server.security.tokens import new_invite_code, token_hash

router = APIRouter()


@router.post("/invites", status_code=201, tags=["org"])
async def create_invite(body: InviteIn, p: Lead, ctx: Ctx) -> InviteOut:
    role = Role(body.role)
    if role not in INVITABLE[p.role]:
        fail(403, "forbidden_role")
    if body.ttl_hours > ctx.settings.invite_ttl_hours_max:
        fail(422, "ttl_too_long")
    code = new_invite_code()
    now = ctx.now()
    inv = Invite(
        id=str(uuid.uuid4()),
        org_id=p.org_id,
        code_hash=token_hash(code),
        role=role.value,
        created_by=p.user_id,
        created_at=now,
        expires_at=now + timedelta(hours=body.ttl_hours),
    )
    async with ctx.db.org_session(p.org_id) as s:
        s.add(inv)
    # Kod faqat shu javobda ko'rsatiladi; bazada — hash'i.
    return InviteOut(id=inv.id, role=inv.role, expires_at=inv.expires_at, used_at=None, code=code)


@router.get("/invites", tags=["org"])
async def list_invites(p: Lead, ctx: Ctx) -> list[InviteOut]:
    async with ctx.db.org_session(p.org_id) as s:
        rows = (await s.execute(select(Invite).where(Invite.org_id == p.org_id).order_by(Invite.created_at))).scalars()
        return [InviteOut(id=i.id, role=i.role, expires_at=i.expires_at, used_at=i.used_at) for i in rows]


def _admin_out(u: AppUser) -> UserAdminOut:
    return UserAdminOut(
        id=u.id,
        org_id=u.org_id,
        full_name=u.full_name,
        role=u.role,
        safety_group=u.safety_group,
        phone=u.phone,
        deleted=u.deleted,
    )


@router.get("/users", tags=["org"])
async def list_users(p: Lead, ctx: Ctx) -> list[UserAdminOut]:
    async with ctx.db.org_session(p.org_id) as s:
        rows = (
            await s.execute(select(AppUser).where(AppUser.org_id == p.org_id).order_by(AppUser.full_name))
        ).scalars()
        return [_admin_out(u) for u in rows]


async def _load_user(ctx: Ctx, org_id: str, user_id: str) -> AppUser:
    async with ctx.db.org_session(org_id) as s:
        u = (
            await s.execute(select(AppUser).where(AppUser.id == user_id, AppUser.org_id == org_id))
        ).scalar_one_or_none()
    if u is None or u.deleted:
        fail(404, "not_found")
    return u


@router.patch("/users/{user_id}/role", tags=["org"])
async def change_role(user_id: str, body: RoleIn, p: Admin, ctx: Ctx) -> UserAdminOut:
    if user_id == p.user_id:
        fail(422, "cannot_change_own_role")
    await _load_user(ctx, p.org_id, user_id)
    async with ctx.db.org_session(p.org_id) as s:
        u = (await s.execute(select(AppUser).where(AppUser.id == user_id))).scalar_one()
        u.role = body.role
        u.updated_at = ctx.now()
        u.rev += 1
        return _admin_out(u)


@router.delete("/users/{user_id}", status_code=204, tags=["org"])
async def delete_user(user_id: str, p: Admin, ctx: Ctx) -> None:
    """Soft delete: kirish, refresh tokenlar va qurilmalar bekor qilinadi; o'lchov va audit yozuvlari saqlanadi."""
    if user_id == p.user_id:
        fail(422, "cannot_delete_self")
    await _load_user(ctx, p.org_id, user_id)
    now = ctx.now()
    async with ctx.db.org_session(p.org_id) as s:
        u = (await s.execute(select(AppUser).where(AppUser.id == user_id))).scalar_one()
        u.deleted = True
        u.updated_at = now
        u.rev += 1
        await s.execute(
            update(RefreshToken)
            .where(RefreshToken.user_id == user_id, RefreshToken.revoked_at.is_(None))
            .values(revoked_at=now)
        )
        devices = (
            await s.execute(select(Device).where(Device.user_id == user_id, Device.revoked_at.is_(None)))
        ).scalars()
        for d in devices:
            d.revoked_at = now
            d.updated_at = now
            d.rev += 1


def _device_out(d: Device) -> DeviceOut:
    return DeviceOut(
        id=d.id,
        user_id=d.user_id,
        public_key_ed25519=d.public_key_ed25519,
        sig_alg=d.sig_alg,
        registered_at=d.registered_at,
        revoked_at=d.revoked_at,
    )


@router.post("/devices", status_code=201, tags=["devices"])
async def register_device(body: DeviceIn, p: Engineer, ctx: Ctx) -> DeviceOut:
    """Qurilma faqat ochiq kaliti bilan; maxfiy kalit qurilmadan chiqmaydi."""
    if body.sig_alg not in SUPPORTED_SIG_ALGS:
        fail(422, "unsupported_sig_alg")
    now = ctx.now()
    d = Device(
        id=body.id or str(uuid.uuid4()),
        org_id=p.org_id,
        user_id=p.user_id,
        public_key_ed25519=body.public_key_ed25519,
        sig_alg=body.sig_alg,
        registered_at=now,
        created_at=now,
        updated_at=now,
    )
    try:
        async with ctx.db.org_session(p.org_id) as s:
            s.add(d)
    except IntegrityError:
        fail(409, "conflict")
    return _device_out(d)


@router.get("/devices", tags=["devices"])
async def list_devices(p: Viewer, ctx: Ctx) -> list[DeviceOut]:
    async with ctx.db.org_session(p.org_id) as s:
        rows = (
            await s.execute(select(Device).where(Device.org_id == p.org_id).order_by(Device.registered_at))
        ).scalars()
        return [_device_out(d) for d in rows]


@router.post("/devices/{device_id}/revoke", tags=["devices"])
async def revoke_device(device_id: str, p: Admin, ctx: Ctx) -> DeviceOut:
    now = ctx.now()
    async with ctx.db.org_session(p.org_id) as s:
        d = (
            await s.execute(select(Device).where(Device.id == device_id, Device.org_id == p.org_id))
        ).scalar_one_or_none()
        if d is None:
            fail(404, "not_found")
        if d.revoked_at is None:
            d.revoked_at = now
            d.updated_at = now
            d.rev += 1
        return _device_out(d)
