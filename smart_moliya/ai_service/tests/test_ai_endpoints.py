from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_health_check():
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"


def test_classify_food():
    response = client.post("/api/v1/classify", json={"text": "bozor dan sabzavot meva oldim"})
    assert response.status_code == 200
    body = response.json()
    assert body["category"] == "food"
    assert body["confidence"] > 0.5


def test_classify_transport():
    response = client.post("/api/v1/classify", json={"text": "yandex taxi orqali ketdim"})
    assert response.status_code == 200
    assert response.json()["category"] == "transport"


def test_classify_unknown_text_falls_back_to_other():
    response = client.post("/api/v1/classify", json={"text": "zzxxqqww"})
    assert response.status_code == 200
    body = response.json()
    assert body["category"] == "other"
    assert body["confidence"] == 0.0


def test_forecast_spending_increasing_trend():
    response = client.post(
        "/api/v1/forecast/spending",
        json={"daily_expenses": [10000, 12000, 14000, 16000, 18000, 20000]},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["daily_trend_slope"] > 0
    assert body["predicted_next_30_days_total"] > 0


def test_forecast_runout_detects_depletion():
    response = client.post(
        "/api/v1/forecast/runout",
        json={
            "current_balance": 50000,
            "daily_expenses": [10000, 10000, 10000, 10000, 10000],
            "daily_income": [1000],
        },
    )
    assert response.status_code == 200
    body = response.json()
    assert body["will_run_out"] is True
    assert body["days_until_depletion"] is not None


def test_anomaly_detects_outlier():
    response = client.post(
        "/api/v1/anomaly",
        json={"amount": 5_000_000, "category_history": [50000, 60000, 55000, 48000, 52000]},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["is_anomaly"] is True


def test_anomaly_normal_amount():
    response = client.post(
        "/api/v1/anomaly",
        json={"amount": 51000, "category_history": [50000, 60000, 55000, 48000, 52000]},
    )
    assert response.status_code == 200
    assert response.json()["is_anomaly"] is False


def test_chatbot_balance_intent_uz():
    response = client.post("/api/v1/chatbot", json={"message": "qancha pul bor mening balansimda?", "language": "uz"})
    assert response.status_code == 200
    body = response.json()
    assert body["intent"] == "balance"


def test_chatbot_save_advice_ru():
    response = client.post("/api/v1/chatbot", json={"message": "как экономить деньги?", "language": "ru"})
    assert response.status_code == 200
    body = response.json()
    assert body["intent"] == "save_advice"
    assert "50/30/20" in body["reply"]


def test_chatbot_unknown_message_en():
    response = client.post("/api/v1/chatbot", json={"message": "asdkjaskdj", "language": "en"})
    assert response.status_code == 200
    assert response.json()["intent"] == "unknown"
