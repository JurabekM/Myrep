import random
from datetime import timedelta

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.orm import Session

from app.db import get_db
from app.logging_config import audit
from app.models import OtpRequest, User, utc_now_naive
from app.providers.sms_otp import DEMO_CODE, get_sms_provider
from app.rate_limit import limiter
from app.schemas import OtpRequestIn, OtpRequestOut, OtpVerifyIn, TokenOut
from app.security import create_access_token

router = APIRouter(prefix="/v1/auth", tags=["auth"])

OTP_TTL_MINUTES = 5


@router.post("/otp/request", response_model=OtpRequestOut)
@limiter.limit("10/minute")
def request_otp(request: Request, payload: OtpRequestIn, db: Session = Depends(get_db)):
    from app.config import get_settings

    settings = get_settings()
    code = DEMO_CODE if settings.auth_otp_mode == "demo" else f"{random.randint(0, 999999):06d}"

    otp = OtpRequest(
        phone_number=payload.phone_number,
        code=code,
        expires_at=utc_now_naive() + timedelta(minutes=OTP_TTL_MINUTES),
    )
    db.add(otp)
    db.commit()
    db.refresh(otp)

    get_sms_provider().send_otp(payload.phone_number, code)
    audit("otp_requested", actor=payload.phone_number)

    hint = f"Demo rejim: kod {DEMO_CODE}" if settings.auth_otp_mode == "demo" else None
    return OtpRequestOut(request_id=otp.id, demo_code_hint=hint)


@router.post("/otp/verify", response_model=TokenOut)
@limiter.limit("10/minute")
def verify_otp(request: Request, payload: OtpVerifyIn, db: Session = Depends(get_db)):
    otp = db.query(OtpRequest).filter(OtpRequest.id == payload.request_id).first()
    if otp is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Unknown request_id")
    if otp.consumed:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Code already used")
    if otp.expires_at < utc_now_naive():
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Code expired")
    if otp.code != payload.code:
        audit("otp_verify_failed", actor=otp.phone_number)
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Incorrect code")

    otp.consumed = True

    user = db.query(User).filter(User.phone_number == otp.phone_number).first()
    if user is None:
        user = User(phone_number=otp.phone_number)
        db.add(user)

    db.commit()
    audit("otp_verify_success", actor=otp.phone_number)

    token = create_access_token(subject=otp.phone_number)
    return TokenOut(access_token=token)
