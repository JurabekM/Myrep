import hmac
from datetime import datetime, timedelta, timezone

from fastapi import Request
from fastapi.responses import RedirectResponse
from jose import JWTError, jwt

from app.core.config import settings

SESSION_COOKIE_NAME = "admin_session"


def verify_credentials(username: str, password: str) -> bool:
    """Taqqoslash vaqtidan ma'lumot oqmasligi uchun constant-time solishtirish."""
    username_ok = hmac.compare_digest(username, settings.ADMIN_USERNAME)
    password_ok = hmac.compare_digest(password, settings.ADMIN_PASSWORD)
    return username_ok and password_ok


def create_session_token() -> str:
    now = datetime.now(timezone.utc)
    payload = {
        "sub": settings.ADMIN_USERNAME,
        "type": "admin_session",
        "iat": now,
        "exp": now + timedelta(hours=settings.SESSION_EXPIRE_HOURS),
    }
    return jwt.encode(payload, settings.ADMIN_SECRET_KEY, algorithm="HS256")


def is_session_valid(token: str | None) -> bool:
    if not token:
        return False
    try:
        payload = jwt.decode(token, settings.ADMIN_SECRET_KEY, algorithms=["HS256"])
    except JWTError:
        return False
    return payload.get("type") == "admin_session"


def require_admin(request: Request) -> RedirectResponse | None:
    """Sessiya yaroqsiz bo'lsa login sahifasiga yo'naltirish, aks holda None."""
    if is_session_valid(request.cookies.get(SESSION_COOKIE_NAME)):
        return None
    return RedirectResponse(url="/login", status_code=303)
