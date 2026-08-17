import time

from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_forecast_rejects_empty_daily_expenses():
    response = client.post("/api/v1/forecast/spending", json={"daily_expenses": []})
    assert response.status_code == 422


def test_classify_empty_text_returns_other():
    response = client.post("/api/v1/classify", json={"text": ""})
    assert response.status_code == 200
    assert response.json()["category"] == "other"


def test_anomaly_with_short_history_is_not_flagged():
    response = client.post("/api/v1/anomaly", json={"amount": 1_000_000, "category_history": [1000, 2000]})
    assert response.status_code == 200
    assert response.json()["is_anomaly"] is False


def test_classify_endpoint_responds_within_reasonable_time():
    """Sog'liq/stress bahosi - inferensiya sekundning ulushida yakunlanishi kerak."""
    start = time.monotonic()
    response = client.post("/api/v1/classify", json={"text": "yandex taxi"})
    elapsed = time.monotonic() - start

    assert response.status_code == 200
    assert elapsed < 1.0
