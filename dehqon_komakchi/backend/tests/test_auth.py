def test_request_otp_returns_demo_hint(client):
    resp = client.post("/v1/auth/otp/request", json={"phone_number": "+998901234567"})
    assert resp.status_code == 200
    body = resp.json()
    assert "request_id" in body
    assert body["demo_code_hint"] == "Demo rejim: kod 123456"


def test_request_otp_rejects_invalid_phone(client):
    resp = client.post("/v1/auth/otp/request", json={"phone_number": "0901234567"})
    assert resp.status_code == 422


def test_verify_otp_with_correct_demo_code_issues_token(client):
    req = client.post("/v1/auth/otp/request", json={"phone_number": "+998901234567"}).json()
    resp = client.post(
        "/v1/auth/otp/verify",
        json={"request_id": req["request_id"], "code": "123456"},
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["token_type"] == "bearer"
    assert len(body["access_token"]) > 10


def test_verify_otp_with_wrong_code_is_rejected(client):
    req = client.post("/v1/auth/otp/request", json={"phone_number": "+998901234567"}).json()
    resp = client.post(
        "/v1/auth/otp/verify",
        json={"request_id": req["request_id"], "code": "000000"},
    )
    assert resp.status_code == 400


def test_verify_otp_cannot_be_replayed(client):
    req = client.post("/v1/auth/otp/request", json={"phone_number": "+998901234567"}).json()
    first = client.post(
        "/v1/auth/otp/verify",
        json={"request_id": req["request_id"], "code": "123456"},
    )
    assert first.status_code == 200
    second = client.post(
        "/v1/auth/otp/verify",
        json={"request_id": req["request_id"], "code": "123456"},
    )
    assert second.status_code == 400


def test_verify_otp_unknown_request_id(client):
    resp = client.post("/v1/auth/otp/verify", json={"request_id": "does-not-exist", "code": "123456"})
    assert resp.status_code == 404
