from abc import ABC, abstractmethod
from dataclasses import dataclass

from app.core.config import settings
from app.services.exceptions import UnauthorizedError


@dataclass
class GoogleUserInfo:
    google_sub: str
    email: str
    full_name: str | None


class GoogleTokenVerifier(ABC):
    @abstractmethod
    def verify(self, id_token: str) -> GoogleUserInfo: ...


class MockGoogleTokenVerifier(GoogleTokenVerifier):
    """Dev/test uchun: `mock-google:<email>:<ism>` formatidagi soxta tokenni qabul qiladi.

    Router darajasida faqat non-production muhitda ishlatiladi.
    """

    def verify(self, id_token: str) -> GoogleUserInfo:
        if not id_token.startswith("mock-google:"):
            raise UnauthorizedError("Google token yaroqsiz")
        parts = id_token.split(":", 2)
        email = parts[1] if len(parts) > 1 and parts[1] else None
        if not email or "@" not in email:
            raise UnauthorizedError("Google token yaroqsiz")
        full_name = parts[2] if len(parts) > 2 and parts[2] else None
        return GoogleUserInfo(google_sub=f"mock-sub-{email}", email=email, full_name=full_name)


class GoogleAuthLibraryVerifier(GoogleTokenVerifier):
    """Haqiqiy Google ID token tekshiruvi - `google-auth` kutubxonasi orqali.

    Ishlatish uchun: `pip install google-auth` va `.env`da GOOGLE_CLIENT_ID.
    Kutubxona lazy import qilinadi - o'rnatilmagan bo'lsa aniq xabar beriladi.
    """

    def verify(self, id_token_str: str) -> GoogleUserInfo:
        try:
            from google.auth.transport import requests as google_requests
            from google.oauth2 import id_token as google_id_token
        except ImportError as exc:  # pragma: no cover
            raise RuntimeError(
                "google-auth o'rnatilmagan: `pip install google-auth` va GOOGLE_CLIENT_ID sozlang"
            ) from exc

        try:
            claims = google_id_token.verify_oauth2_token(
                id_token_str, google_requests.Request(), settings.GOOGLE_CLIENT_ID
            )
        except ValueError as exc:
            raise UnauthorizedError("Google token yaroqsiz yoki muddati tugagan") from exc

        return GoogleUserInfo(
            google_sub=claims["sub"],
            email=claims["email"],
            full_name=claims.get("name"),
        )


def get_google_verifier() -> GoogleTokenVerifier:
    """GOOGLE_CLIENT_ID sozlangan bo'lsa haqiqiy verifier, aks holda (faqat
    non-production) mock qaytadi. Production'da client ID'siz Google login yopiq."""
    if settings.GOOGLE_CLIENT_ID:
        return GoogleAuthLibraryVerifier()
    if settings.ENVIRONMENT == "production":
        raise UnauthorizedError("Google login sozlanmagan")
    return MockGoogleTokenVerifier()
