import uuid
from datetime import timedelta

from jose import jwt

from app.core.config import settings
from app.core.security import create_access_token, decode_token


def test_expired_access_token_is_rejected():
    user_id = uuid.uuid4()
    from app.core.security import _create_token

    expired_token = _create_token(user_id, timedelta(seconds=-1), "access")
    assert decode_token(expired_token) is None


def test_tampered_token_is_rejected():
    user_id = uuid.uuid4()
    token = create_access_token(user_id)
    tampered = token[:-4] + ("aaaa" if not token.endswith("aaaa") else "bbbb")
    assert decode_token(tampered) is None


def test_token_signed_with_wrong_secret_is_rejected():
    payload = {"sub": str(uuid.uuid4()), "type": "access"}
    forged_token = jwt.encode(payload, "some-other-secret", algorithm=settings.JWT_ALGORITHM)
    assert decode_token(forged_token) is None


def test_access_and_refresh_tokens_have_distinct_type_claim():
    user_id = uuid.uuid4()
    from app.core.security import create_refresh_token

    access = decode_token(create_access_token(user_id))
    refresh = decode_token(create_refresh_token(user_id, device_id="device-1"))

    assert access["type"] == "access"
    assert refresh["type"] == "refresh"
    assert access["type"] != refresh["type"]
