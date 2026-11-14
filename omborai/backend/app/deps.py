import uuid
from dataclasses import dataclass

import jwt
from fastapi import Depends
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from .db import get_db, set_db_context
from .errors import ProblemError
from .models import Membership
from .security import decode_access_token

_bearer = HTTPBearer(auto_error=False)


@dataclass(frozen=True)
class Principal:
    user_id: uuid.UUID
    tenant_id: uuid.UUID


async def get_principal(
    creds: HTTPAuthorizationCredentials | None = Depends(_bearer),
    session: AsyncSession = Depends(get_db),
) -> Principal:
    if creds is None:
        raise ProblemError(401, "Autentifikatsiya talab qilinadi")
    try:
        claims = decode_access_token(creds.credentials)
        principal = Principal(uuid.UUID(claims["sub"]), uuid.UUID(claims["tid"]))
    except (jwt.PyJWTError, ValueError, KeyError) as exc:
        raise ProblemError(401, "Token yaroqsiz yoki muddati tugagan") from exc

    # Shu so'rovdan boshlab barcha so'rovlar faqat shu tenant ma'lumotini ko'radi (RLS)
    await set_db_context(session, tenant_id=principal.tenant_id, user_id=None)
    return principal


def require_roles(*allowed: str):
    async def _check(
        principal: Principal = Depends(get_principal),
        session: AsyncSession = Depends(get_db),
    ) -> Principal:
        result = await session.execute(select(Membership.role).where(Membership.user_id == principal.user_id))
        roles = set(result.scalars().all())
        if not roles & set(allowed):
            raise ProblemError(403, "Ruxsat yo'q", "Bu amal uchun rolingiz yetarli emas")
        return principal

    return _check
