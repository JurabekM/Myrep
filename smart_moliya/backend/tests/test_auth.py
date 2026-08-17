from app.core.security import create_access_token, create_refresh_token, decode_token, hash_password, verify_password
import uuid


def test_password_hash_roundtrip():
    hashed = hash_password("super-secret")
    assert verify_password("super-secret", hashed)
    assert not verify_password("wrong-password", hashed)


def test_access_token_roundtrip():
    user_id = uuid.uuid4()
    token = create_access_token(user_id)
    payload = decode_token(token)
    assert payload is not None
    assert payload["sub"] == str(user_id)
    assert payload["type"] == "access"


def test_refresh_token_is_bound_to_device():
    user_id = uuid.uuid4()
    token = create_refresh_token(user_id, device_id="device-A")
    payload = decode_token(token)
    assert payload is not None
    assert payload["type"] == "refresh"
    assert payload["device_id"] == "device-A"


def test_invalid_token_returns_none():
    assert decode_token("not-a-real-token") is None
