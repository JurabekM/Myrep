from tests.conftest import make_test_jpeg_bytes


def test_diagnose_accepts_a_good_photo(client):
    photo = make_test_jpeg_bytes()
    resp = client.post("/v1/diagnosis", files={"file": ("leaf.jpg", photo, "image/jpeg")})
    assert resp.status_code == 200
    body = resp.json()
    assert body["category"] in {"PEST", "FUNGAL", "NUTRIENT", "WATERING", "HEAT_STRESS", "UNCLEAR"}
    assert 0.0 <= body["confidence"] <= 0.95
    assert body["safe_steps"]
    assert "agronom" in body["consult_advice"].lower() or "murojaat" in body["consult_advice"].lower()
    assert body["diagnosis_log_id"]


def test_diagnose_rejects_unsupported_content_type(client):
    resp = client.post(
        "/v1/diagnosis",
        files={"file": ("leaf.txt", b"not an image", "text/plain")},
    )
    assert resp.status_code == 415


def test_diagnose_rejects_too_small_photo(client):
    photo = make_test_jpeg_bytes(width=50, height=50)
    resp = client.post("/v1/diagnosis", files={"file": ("leaf.jpg", photo, "image/jpeg")})
    assert resp.status_code == 422
    assert resp.json()["detail"]["reason"] == "too_small"


def test_diagnose_rejects_empty_file(client):
    resp = client.post("/v1/diagnosis", files={"file": ("leaf.jpg", b"", "image/jpeg")})
    assert resp.status_code == 400


def test_diagnose_rejects_oversized_file(client, monkeypatch):
    from app import config

    config.get_settings.cache_clear()
    monkeypatch.setenv("MAX_UPLOAD_IMAGE_MB", "0")
    config.get_settings.cache_clear()

    photo = make_test_jpeg_bytes()
    resp = client.post("/v1/diagnosis", files={"file": ("leaf.jpg", photo, "image/jpeg")})
    assert resp.status_code == 413

    config.get_settings.cache_clear()


def test_rate_diagnosis_after_result(client):
    photo = make_test_jpeg_bytes()
    diag = client.post("/v1/diagnosis", files={"file": ("leaf.jpg", photo, "image/jpeg")}).json()

    resp = client.post(
        "/v1/diagnosis/rate",
        json={"diagnosis_log_id": diag["diagnosis_log_id"], "useful": True},
    )
    assert resp.status_code == 204


def test_rate_diagnosis_unknown_id(client):
    resp = client.post("/v1/diagnosis/rate", json={"diagnosis_log_id": "nope", "useful": True})
    assert resp.status_code == 404
