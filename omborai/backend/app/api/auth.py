import uuid
from datetime import UTC, datetime, timedelta

from fastapi import APIRouter, Depends
from sqlalchemy import select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from ..config import get_settings
from ..db import get_db, set_db_context
from ..errors import ProblemError
from ..models import Membership, RefreshToken, Store, Tenant, User
from ..schemas import LoginIn, RefreshIn, RegisterIn, TokenOut
from ..security import (
    create_access_token,
    hash_password,
    hash_refresh_token,
    new_refresh_token,
    verify_password,
)

router = APIRouter(prefix="/auth", tags=["auth"])

INVALID_CREDENTIALS = "Email yoki parol noto'g'ri"


async def _issue_tokens(
    session: AsyncSession,
    user_id: uuid.UUID,
    tenant_id: uuid.UUID,
    family_id: uuid.UUID | None = None,
) -> TokenOut:
    access, expires_in = create_access_token(user_id, tenant_id)
    refresh = new_refresh_token()
    session.add(
        RefreshToken(
            user_id=user_id,
            family_id=family_id or uuid.uuid4(),
            token_hash=hash_refresh_token(refresh),
            expires_at=datetime.now(UTC) + timedelta(days=get_settings().refresh_token_days),
        )
    )
    await session.flush()
    return TokenOut(access_token=access, refresh_token=refresh, expires_in=expires_in)


@router.post("/register", status_code=201, response_model=TokenOut)
async def register(body: RegisterIn, session: AsyncSession = Depends(get_db)) -> TokenOut:
    """Yangi do'kon egasi: tenant, birinchi filial va owner roli bilan birga yaratiladi."""
    email = body.email.lower()
    if await session.scalar(select(User.id).where(User.email == email)):
        raise ProblemError(409, "Email band", "Bu email allaqachon ro'yxatdan o'tgan")

    tenant = Tenant(name=body.tenant_name)
    session.add(tenant)
    await session.flush()

    await set_db_context(session, tenant_id=tenant.id, user_id=None)
    store = Store(tenant_id=tenant.id, name=body.store_name)
    user = User(email=email, password_hash=hash_password(body.password), full_name=body.full_name)
    session.add_all([store, user])
    await session.flush()
    session.add(Membership(tenant_id=tenant.id, user_id=user.id, store_id=None, role="owner"))

    tokens = await _issue_tokens(session, user.id, tenant.id)
    try:
        await session.commit()
    except IntegrityError as exc:  # bir vaqtda ikki so'rov bir xil email bilan kelgan bo'lsa
        raise ProblemError(409, "Email band", "Bu email allaqachon ro'yxatdan o'tgan") from exc
    return tokens


@router.post("/login", response_model=TokenOut)
async def login(body: LoginIn, session: AsyncSession = Depends(get_db)) -> TokenOut:
    user = await session.scalar(
        select(User).where(User.email == body.email.lower(), User.deleted_at.is_(None))
    )
    password_hash = user.password_hash if user else None
    if not verify_password(password_hash, body.password) or user is None:
        raise ProblemError(401, "Kirish rad etildi", INVALID_CREDENTIALS)

    await set_db_context(session, tenant_id=None, user_id=user.id)
    tenant_id = await session.scalar(
        select(Membership.tenant_id).where(Membership.user_id == user.id).limit(1)
    )
    if tenant_id is None:
        raise ProblemError(403, "Ruxsat yo'q", "Foydalanuvchi hech qanday do'konga biriktirilmagan")

    tokens = await _issue_tokens(session, user.id, tenant_id)
    await session.commit()
    return tokens


@router.post("/refresh", response_model=TokenOut)
async def refresh(body: RefreshIn, session: AsyncSession = Depends(get_db)) -> TokenOut:
    """Refresh token rotatsiyasi. Eski token qayta ishlatilsa, butun oila bekor qilinadi."""
    now = datetime.now(UTC)
    token = await session.scalar(
        select(RefreshToken).where(RefreshToken.token_hash == hash_refresh_token(body.refresh_token))
    )
    if token is None:
        raise ProblemError(401, "Token yaroqsiz", "Refresh token topilmadi")

    if token.revoked_at is not None:
        # Ehtimoliy o'g'irlangan token: zanjirdagi barcha tokenlarni bekor qilamiz
        await session.execute(
            update(RefreshToken)
            .where(RefreshToken.family_id == token.family_id, RefreshToken.revoked_at.is_(None))
            .values(revoked_at=now)
        )
        await session.commit()
        raise ProblemError(401, "Token qayta ishlatilgan", "Barcha sessiyalar bekor qilindi")

    if token.expires_at <= now:
        raise ProblemError(401, "Token muddati tugagan")

    token.revoked_at = now
    await set_db_context(session, tenant_id=None, user_id=token.user_id)
    tenant_id = await session.scalar(
        select(Membership.tenant_id).where(Membership.user_id == token.user_id).limit(1)
    )
    if tenant_id is None:
        raise ProblemError(403, "Ruxsat yo'q", "Foydalanuvchi do'konga biriktirilmagan")

    tokens = await _issue_tokens(session, token.user_id, tenant_id, family_id=token.family_id)
    await session.commit()
    return tokens
