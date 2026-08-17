"""Auth HTTP endpoints — thin layer over AuthService."""

from fastapi import APIRouter, Request, status

from app.core.dependencies import Container, CurrentUser
from app.modules.auth.schemas import (
    LoginRequest,
    ProfileUpdateRequest,
    RefreshRequest,
    RegisterRequest,
    TokenPair,
    TwoFAConfirmRequest,
    TwoFASetupResponse,
    UserResponse,
)
from app.modules.auth.service import AuthService

router = APIRouter(prefix="/auth", tags=["auth"])


def _service(container) -> AuthService:  # type: ignore[no-untyped-def]
    return AuthService(
        container.users, container.token_service, container.two_factor_service, container.audit_logs
    )


def _to_response(user) -> UserResponse:  # type: ignore[no-untyped-def]
    return UserResponse(
        id=user.id,
        email=user.email,
        full_name=user.full_name,
        phone=user.phone,
        role=user.role,
        plan=user.plan,
        locale=user.locale,
        two_fa_enabled=user.two_fa_enabled,
        profile=user.profile,
    )


@router.post("/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def register(req: RegisterRequest, container: Container) -> UserResponse:
    user = await _service(container).register(req)
    return _to_response(user)


@router.post("/login", response_model=TokenPair)
async def login(req: LoginRequest, request: Request, container: Container) -> TokenPair:
    ip = request.client.host if request.client else None
    return await _service(container).login(req, ip=ip)


@router.post("/refresh", response_model=TokenPair)
async def refresh(req: RefreshRequest, container: Container) -> TokenPair:
    return await _service(container).refresh(req.refresh_token)


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
async def logout(user: CurrentUser, container: Container) -> None:
    await _service(container).logout(user.id)


@router.get("/me", response_model=UserResponse)
async def me(user: CurrentUser) -> UserResponse:
    return _to_response(user)


@router.patch("/me", response_model=UserResponse)
async def update_profile(
    req: ProfileUpdateRequest, user: CurrentUser, container: Container
) -> UserResponse:
    updated = await _service(container).update_profile(user, req)
    return _to_response(updated)


@router.post("/2fa/setup", response_model=TwoFASetupResponse)
async def setup_two_fa(user: CurrentUser, container: Container) -> TwoFASetupResponse:
    return await _service(container).setup_two_fa(user)


@router.post("/2fa/confirm", status_code=status.HTTP_204_NO_CONTENT)
async def confirm_two_fa(
    req: TwoFAConfirmRequest, user: CurrentUser, container: Container
) -> None:
    await _service(container).confirm_two_fa(user, req.totp_code)
