from fastapi import APIRouter, status

from app.api.deps import CurrentUser, DbSession
from app.core.config import settings
from app.repositories.user_repository import UserRepository
from app.schemas.auth import (
    GoogleLoginRequest,
    LoginRequest,
    OtpRequest,
    OtpRequestResponse,
    OtpVerifyRequest,
    RefreshRequest,
    RegisterRequest,
    TokenPair,
)
from app.schemas.user import UserRead
from app.services.auth_service import AuthService
from app.services.google_auth import get_google_verifier
from app.services.otp_service import get_otp_service

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/register", response_model=UserRead, status_code=status.HTTP_201_CREATED)
async def register(payload: RegisterRequest, db: DbSession) -> UserRead:
    service = AuthService(UserRepository(db))
    user = await service.register(payload.phone, payload.password, payload.full_name, payload.language)
    return UserRead.model_validate(user)


@router.post("/login", response_model=TokenPair)
async def login(payload: LoginRequest, db: DbSession) -> TokenPair:
    service = AuthService(UserRepository(db))
    _, tokens = await service.login(payload.phone, payload.password, payload.device_id)
    return tokens


@router.post("/refresh", response_model=TokenPair)
async def refresh(payload: RefreshRequest, db: DbSession) -> TokenPair:
    service = AuthService(UserRepository(db))
    return await service.refresh(payload.refresh_token, payload.device_id)


@router.post("/otp/request", response_model=OtpRequestResponse)
async def request_otp(payload: OtpRequest) -> OtpRequestResponse:
    """SMS orqali bir martalik kod so'rash.

    Dev muhitda kod `dev_code`da qaytadi (MockSmsSender). Production'da SMS
    provayder (masalan Eskiz.uz) adapteri ulanadi va dev_code hech qachon qaytmaydi.
    """
    code = get_otp_service().request_code(payload.phone)
    is_dev = settings.ENVIRONMENT != "production"
    return OtpRequestResponse(
        message="Tasdiqlash kodi yuborildi",
        dev_code=code if is_dev else None,
    )


@router.post("/otp/verify", response_model=TokenPair)
async def verify_otp(payload: OtpVerifyRequest, db: DbSession) -> TokenPair:
    """Kodni tekshiradi; foydalanuvchi bo'lmasa parolsiz hisob ochib, token beradi."""
    get_otp_service().verify_code(payload.phone, payload.code)
    service = AuthService(UserRepository(db))
    _, tokens = await service.login_with_otp(payload.phone, payload.device_id)
    return tokens


@router.post("/google", response_model=TokenPair)
async def google_login(payload: GoogleLoginRequest, db: DbSession) -> TokenPair:
    """Google ID token bilan kirish. GOOGLE_CLIENT_ID sozlanmagan dev muhitda
    mock verifier ishlaydi (`mock-google:<email>:<ism>` formatidagi token)."""
    info = get_google_verifier().verify(payload.id_token)
    service = AuthService(UserRepository(db))
    _, tokens = await service.login_with_google(info, payload.device_id)
    return tokens


@router.get("/me", response_model=UserRead)
async def me(current_user: CurrentUser) -> UserRead:
    return UserRead.model_validate(current_user)
