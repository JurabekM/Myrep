"""Kirish: telefon + parol (argon2id), access JWT (15 daqiqa), refresh rotatsiya va qayta ishlatishni aniqlash,
taklif kodi bilan qo'shilish, laboratoriyani ro'yxatdan o'tkazish (sozlama bilan), SMS OTP (o'chiq)."""

from __future__ import annotations

import uuid
from datetime import timedelta

from fastapi import APIRouter, Response
from sqlalchemy import select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from zanjir_server.api.deps import AppContext, Ctx, Viewer, fail
from zanjir_server.api.schemas import AcceptInviteIn, LoginIn, RefreshIn, RegisterIn, TokensOut, UserOut
from zanjir_server.db.models import AppUser, Invite, Organization, RefreshToken
from zanjir_server.security.phone import normalize_phone
from zanjir_server.security.tokens import AccessClaims, new_secret_token, token_hash

router = APIRouter(prefix="/auth", tags=["auth"])


def _user_out(u: AppUser) -> UserOut:
    return UserOut(id=u.id, org_id=u.org_id, full_name=u.full_name, role=u.role, safety_group=u.safety_group)


def _phone(raw: str) -> str:
    phone = normalize_phone(raw)
    if phone is None:
        fail(422, "invalid_phone")
    return phone


async def _issue(ctx: AppContext, s: AsyncSession, user: AppUser, family_id: str | None = None) -> TokensOut:
    now = ctx.now()
    refresh = new_secret_token()
    s.add(
        RefreshToken(
            id=str(uuid.uuid4()),
            org_id=user.org_id,
            user_id=user.id,
            family_id=family_id or str(uuid.uuid4()),
            token_hash=token_hash(refresh),
            issued_at=now,
            expires_at=now + timedelta(seconds=ctx.settings.refresh_ttl_seconds),
        )
    )
    access = ctx.tokens.issue(AccessClaims(user_id=user.id, org_id=user.org_id, role=user.role), now)
    return TokensOut(
        access_token=access,
        refresh_token=refresh,
        expires_in=ctx.settings.access_ttl_seconds,
        user=_user_out(user),
    )


@router.post("/register", status_code=201)
async def register(body: RegisterIn, ctx: Ctx) -> TokensOut:
    if not ctx.settings.registration_open:
        fail(403, "registration_closed")
    phone = _phone(body.phone)
    org_id = body.org_id or str(uuid.uuid4())
    now = ctx.now()
    try:
        async with ctx.db.org_session(org_id) as s:
            s.add(
                Organization(id=org_id, name=body.org_name, license_no=body.license_no, created_at=now, updated_at=now)
            )
            await s.flush()
            user = AppUser(
                id=body.user_id or str(uuid.uuid4()),
                org_id=org_id,
                full_name=body.full_name,
                phone=phone,
                password_hash=ctx.passwords.hash(body.password),
                role=body.role,
                safety_group=body.safety_group,
                created_at=now,
                updated_at=now,
            )
            s.add(user)
            await s.flush()
            return await _issue(ctx, s, user)
    except IntegrityError:
        fail(409, "conflict")


@router.post("/login")
async def login(body: LoginIn, ctx: Ctx) -> TokensOut:
    phone = normalize_phone(body.phone)
    org = await ctx.db.lookup_org("zanjir_org_of_phone", phone) if phone else None
    if org is None:
        ctx.passwords.verify(None, body.password)  # topilmasa ham hash tekshiriladi — javob vaqti bir xil
        fail(401, "invalid_credentials")
    async with ctx.db.org_session(org) as s:
        user = (
            await s.execute(select(AppUser).where(AppUser.phone == phone, AppUser.deleted.is_(False)))
        ).scalar_one_or_none()
        if not ctx.passwords.verify(user.password_hash if user else None, body.password) or user is None:
            fail(401, "invalid_credentials")
        if ctx.passwords.needs_rehash(user.password_hash):
            user.password_hash = ctx.passwords.hash(body.password)
        return await _issue(ctx, s, user)


@router.post("/refresh")
async def refresh(body: RefreshIn, ctx: Ctx) -> TokensOut:
    now = ctx.now()
    outcome: TokensOut | str
    org = await ctx.db.lookup_org("zanjir_org_of_refresh", token_hash(body.refresh_token))
    if org is None:
        fail(401, "invalid_refresh")
    async with ctx.db.org_session(org) as s:
        row = (
            await s.execute(
                select(RefreshToken).where(RefreshToken.token_hash == token_hash(body.refresh_token)).with_for_update()
            )
        ).scalar_one_or_none()
        if row is None or row.revoked_at is not None:
            outcome = "invalid_refresh"
        elif row.used_at is not None:
            # Qayta ishlatish — token o'g'irlangan bo'lishi mumkin: butun oila bekor qilinadi (commit qilinadi).
            await _revoke_family(s, row.family_id, now)
            outcome = "refresh_reused"
        elif row.expires_at <= now:
            outcome = "refresh_expired"
        else:
            user = (await s.execute(select(AppUser).where(AppUser.id == row.user_id))).scalar_one()
            if user.deleted:
                await _revoke_family(s, row.family_id, now)
                outcome = "invalid_refresh"
            else:
                row.used_at = now
                outcome = await _issue(ctx, s, user, family_id=row.family_id)
    if isinstance(outcome, str):
        fail(401, outcome)
    return outcome


async def _revoke_family(s: AsyncSession, family_id: str, now: object) -> None:
    await s.execute(
        update(RefreshToken)
        .where(RefreshToken.family_id == family_id, RefreshToken.revoked_at.is_(None))
        .values(revoked_at=now)
    )


@router.post("/logout", status_code=204)
async def logout(body: RefreshIn, ctx: Ctx) -> Response:
    org = await ctx.db.lookup_org("zanjir_org_of_refresh", token_hash(body.refresh_token))
    if org is None:
        return Response(status_code=204)
    async with ctx.db.org_session(org) as s:
        row = (
            await s.execute(select(RefreshToken).where(RefreshToken.token_hash == token_hash(body.refresh_token)))
        ).scalar_one_or_none()
        if row is not None:
            await _revoke_family(s, row.family_id, ctx.now())
    return Response(status_code=204)


@router.post("/accept-invite", status_code=201)
async def accept_invite(body: AcceptInviteIn, ctx: Ctx) -> TokensOut:
    phone = _phone(body.phone)
    now = ctx.now()
    org = await ctx.db.lookup_org("zanjir_org_of_invite", token_hash(body.code))
    if org is None:
        fail(400, "invalid_invite")
    async with ctx.db.org_session(org) as s:
        # Bir martalik: shartli UPDATE — parallel so'rovlardan faqat bittasi o'tadi.
        user_id = body.user_id or str(uuid.uuid4())
        invite = (
            await s.execute(
                update(Invite)
                .where(Invite.code_hash == token_hash(body.code), Invite.used_at.is_(None), Invite.expires_at > now)
                .values(used_at=now, used_by=user_id)
                .returning(Invite)
            )
        ).scalar_one_or_none()
        if invite is None:
            result: TokensOut | str = "invalid_invite"
        else:
            user = AppUser(
                id=user_id,
                org_id=invite.org_id,
                full_name=body.full_name,
                phone=phone,
                password_hash=ctx.passwords.hash(body.password),
                role=invite.role,
                safety_group=body.safety_group,
                created_at=now,
                updated_at=now,
            )
            s.add(user)
            try:
                await s.flush()
            except IntegrityError:
                fail(409, "conflict")
            result = await _issue(ctx, s, user)
    if isinstance(result, str):
        fail(400, result)
    return result


@router.post("/otp/request")
async def otp_request(ctx: Ctx) -> None:
    if not ctx.settings.sms_otp_enabled:
        fail(404, "otp_disabled")
    fail(501, "otp_not_implemented")


me_router = APIRouter(tags=["auth"])


@me_router.get("/me")
async def me(p: Viewer) -> UserOut:
    return UserOut(id=p.user_id, org_id=p.org_id, full_name=p.full_name, role=p.role.value, safety_group=p.safety_group)
