import uuid

from app.core.security import (
    create_access_token,
    create_refresh_token,
    decode_token,
    hash_password,
    verify_password,
)
from app.models.enums import AuthProvider, Language
from app.models.user import User
from app.repositories.user_repository import UserRepository
from app.schemas.auth import TokenPair
from app.services.exceptions import ConflictError, UnauthorizedError
from app.services.google_auth import GoogleUserInfo


class AuthService:
    def __init__(self, user_repository: UserRepository):
        self.user_repository = user_repository

    async def register(
        self, phone: str, password: str, full_name: str | None, language: Language
    ) -> User:
        existing = await self.user_repository.get_by_phone(phone)
        if existing is not None:
            raise ConflictError("Bu telefon raqami allaqachon ro'yxatdan o'tgan")

        user = User(
            phone=phone,
            password_hash=hash_password(password),
            full_name=full_name,
            language=language,
        )
        user = await self.user_repository.add(user)
        await self.user_repository.commit()
        return user

    async def login(self, phone: str, password: str, device_id: str) -> tuple[User, TokenPair]:
        user = await self.user_repository.get_by_phone(phone)
        if user is None or user.password_hash is None or not verify_password(password, user.password_hash):
            raise UnauthorizedError("Telefon raqami yoki parol noto'g'ri")
        return user, self._issue_tokens(user.id, device_id)

    async def refresh(self, refresh_token: str, device_id: str) -> TokenPair:
        payload = decode_token(refresh_token)
        if payload is None or payload.get("type") != "refresh":
            raise UnauthorizedError("Refresh token yaroqsiz")

        if payload.get("device_id") != device_id:
            raise UnauthorizedError("Token boshqa qurilmaga tegishli")

        user_id = uuid.UUID(payload["sub"])
        user = await self.user_repository.get(user_id)
        if user is None or not user.is_active:
            raise UnauthorizedError("Foydalanuvchi topilmadi")
        return self._issue_tokens(user.id, device_id)

    async def login_with_otp(self, phone: str, device_id: str) -> tuple[User, TokenPair]:
        """OTP tasdiqlangandan keyin chaqiriladi (kod tekshiruvi OtpService'da).

        Foydalanuvchi mavjud bo'lmasa parolsiz (passwordless) hisob avtomatik ochiladi.
        """
        user = await self.user_repository.get_by_phone(phone)
        if user is None:
            user = User(phone=phone, auth_provider=AuthProvider.PHONE, language=Language.UZ)
            user = await self.user_repository.add(user)
            await self.user_repository.commit()
        if not user.is_active:
            raise UnauthorizedError("Hisob faol emas")
        return user, self._issue_tokens(user.id, device_id)

    async def login_with_google(self, info: GoogleUserInfo, device_id: str) -> tuple[User, TokenPair]:
        """Tasdiqlangan Google ma'lumoti asosida kirish; email bo'yicha topilmasa yangi hisob ochiladi."""
        user = await self.user_repository.get_by_email(info.email)
        if user is None:
            user = User(
                email=info.email,
                full_name=info.full_name,
                auth_provider=AuthProvider.GOOGLE,
                language=Language.UZ,
            )
            user = await self.user_repository.add(user)
            await self.user_repository.commit()
        if not user.is_active:
            raise UnauthorizedError("Hisob faol emas")
        return user, self._issue_tokens(user.id, device_id)

    @staticmethod
    def _issue_tokens(user_id: uuid.UUID, device_id: str) -> TokenPair:
        return TokenPair(
            access_token=create_access_token(user_id),
            refresh_token=create_refresh_token(user_id, device_id),
        )
