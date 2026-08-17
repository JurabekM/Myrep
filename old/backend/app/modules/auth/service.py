"""Auth business logic — framework-independent."""

from bson import ObjectId

from app.core.exceptions import AuthenticationError, ValidationError
from app.core.security import TokenService, TwoFactorService, hash_password, verify_password
from app.domain.entities.user import User
from app.domain.interfaces.repositories import AuditLogRepository, UserRepository
from app.modules.auth.schemas import (
    LoginRequest,
    ProfileUpdateRequest,
    RegisterRequest,
    TokenPair,
    TwoFASetupResponse,
)


class AuthService:
    def __init__(
        self,
        users: UserRepository,
        tokens: TokenService,
        two_factor: TwoFactorService,
        audit: AuditLogRepository,
    ):
        self._users = users
        self._tokens = tokens
        self._two_factor = two_factor
        self._audit = audit

    async def register(self, req: RegisterRequest) -> User:
        user = User(
            id=str(ObjectId()),
            email=req.email.lower(),
            phone=req.phone,
            full_name=req.full_name,
            password_hash=hash_password(req.password),
            locale=req.locale,
        )
        created = await self._users.create(user)
        await self._audit.record(actor_id=created.id, action="user.register", resource=created.id)
        return created

    async def login(self, req: LoginRequest, *, ip: str | None = None) -> TokenPair:
        user = await self._users.get_by_email(req.email)
        # Constant-time-ish behaviour: always run a hash verification even
        # when the user does not exist, to avoid email enumeration by timing.
        password_ok = verify_password(
            req.password, user.password_hash if user else hash_password("invalid")
        )
        if user is None or not password_ok:
            raise AuthenticationError("Email yoki parol noto'g'ri")
        if not user.is_active:
            raise AuthenticationError("Hisob bloklangan")
        if user.two_fa_enabled:
            if not req.totp_code:
                raise AuthenticationError("2FA kodi talab qilinadi")
            if not user.two_fa_secret or not self._two_factor.verify(
                user.two_fa_secret, req.totp_code
            ):
                raise AuthenticationError("2FA kodi noto'g'ri")
        access = self._tokens.create_access_token(user.id, user.role.value, user.plan.value)
        refresh = await self._tokens.create_refresh_token(user.id, req.device_id)
        await self._audit.record(actor_id=user.id, action="user.login", resource=user.id, ip=ip)
        return TokenPair(access_token=access, refresh_token=refresh)

    async def refresh(self, refresh_token: str) -> TokenPair:
        user_id, new_refresh = await self._tokens.rotate_refresh_token(refresh_token)
        user = await self._users.get_by_id(user_id)
        if user is None or not user.is_active:
            raise AuthenticationError("Foydalanuvchi topilmadi yoki bloklangan")
        access = self._tokens.create_access_token(user.id, user.role.value, user.plan.value)
        return TokenPair(access_token=access, refresh_token=new_refresh)

    async def logout(self, user_id: str, device_id: str | None = None) -> None:
        await self._tokens.revoke_refresh_tokens(user_id, device_id)

    async def setup_two_fa(self, user: User) -> TwoFASetupResponse:
        if user.two_fa_enabled:
            raise ValidationError("2FA allaqachon yoqilgan")
        secret = self._two_factor.generate_secret()
        await self._users.update(user.id, {"two_fa_secret": secret})
        return TwoFASetupResponse(
            secret=secret,
            provisioning_uri=self._two_factor.provisioning_uri(secret, user.email),
        )

    async def confirm_two_fa(self, user: User, code: str) -> None:
        fresh = await self._users.get_by_id(user.id)
        if fresh is None or not fresh.two_fa_secret:
            raise ValidationError("Avval 2FA sozlashni boshlang")
        if not self._two_factor.verify(fresh.two_fa_secret, code):
            raise AuthenticationError("2FA kodi noto'g'ri")
        await self._users.update(user.id, {"two_fa_enabled": True})
        await self._audit.record(actor_id=user.id, action="user.2fa_enabled", resource=user.id)

    async def update_profile(self, user: User, req: ProfileUpdateRequest) -> User:
        fields: dict[str, object] = {}
        if req.full_name is not None:
            fields["full_name"] = req.full_name
        if req.locale is not None:
            fields["locale"] = req.locale
        if req.profile is not None:
            fields["profile"] = req.profile.model_dump()
        if not fields:
            return user
        return await self._users.update(user.id, fields)
