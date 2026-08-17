import time

import pytest
from fastapi.testclient import TestClient

from app.core.config import settings
from app.main import app
from app.services.exceptions import UnauthorizedError
from app.services.google_auth import MockGoogleTokenVerifier
from app.services.otp_service import InMemoryOtpStore, MockSmsSender, OtpService

client = TestClient(app)


def _make_service() -> OtpService:
    return OtpService(InMemoryOtpStore(), MockSmsSender())


def test_otp_roundtrip_succeeds():
    service = _make_service()
    code = service.request_code("+998901112233")
    assert len(code) == 6 and code.isdigit()
    service.verify_code("+998901112233", code)  # xato ko'tarmasligi kerak


def test_otp_code_is_single_use():
    service = _make_service()
    code = service.request_code("+998901112233")
    service.verify_code("+998901112233", code)
    with pytest.raises(UnauthorizedError):
        service.verify_code("+998901112233", code)


def test_otp_wrong_code_rejected():
    service = _make_service()
    service.request_code("+998901112233")
    with pytest.raises(UnauthorizedError):
        service.verify_code("+998901112233", "000000")


def test_otp_expired_code_rejected():
    service = _make_service()
    code = service.request_code("+998901112233")
    record = service.store.get("+998901112233")
    record.expires_at = time.time() - 1  # muddatini sun'iy o'tkazamiz
    with pytest.raises(UnauthorizedError):
        service.verify_code("+998901112233", code)


def test_otp_attempts_limit_enforced():
    service = _make_service()
    code = service.request_code("+998901112233")
    for _ in range(settings.OTP_MAX_ATTEMPTS):
        with pytest.raises(UnauthorizedError):
            service.verify_code("+998901112233", "999999")
    # limitdan keyin hatto to'g'ri kod ham rad etiladi (yozuv o'chirilgan)
    with pytest.raises(UnauthorizedError):
        service.verify_code("+998901112233", code)


def test_otp_request_endpoint_returns_dev_code_in_dev():
    response = client.post("/api/v1/auth/otp/request", json={"phone": "+998905556677"})
    assert response.status_code == 200
    body = response.json()
    assert body["dev_code"] is not None
    assert len(body["dev_code"]) == 6


def test_mock_google_verifier_parses_token():
    info = MockGoogleTokenVerifier().verify("mock-google:user@example.com:Ali Valiyev")
    assert info.email == "user@example.com"
    assert info.full_name == "Ali Valiyev"


def test_mock_google_verifier_rejects_invalid_tokens():
    with pytest.raises(UnauthorizedError):
        MockGoogleTokenVerifier().verify("real-looking-jwt-token")
    with pytest.raises(UnauthorizedError):
        MockGoogleTokenVerifier().verify("mock-google:not-an-email")
