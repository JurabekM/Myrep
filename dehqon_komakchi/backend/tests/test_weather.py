def test_get_weather_returns_forecast(client):
    resp = client.get("/v1/weather", params={"region": "Toshkent viloyati"})
    assert resp.status_code == 200
    body = resp.json()
    assert body["region"] == "Toshkent viloyati"
    assert len(body["forecast"]) == 5
    for day in body["forecast"]:
        assert 0 <= day["rain_probability_percent"] <= 100


def test_get_weather_requires_region(client):
    resp = client.get("/v1/weather")
    assert resp.status_code == 422


def test_get_weather_is_stable_for_same_region_same_day(client):
    first = client.get("/v1/weather", params={"region": "Andijon viloyati"}).json()
    second = client.get("/v1/weather", params={"region": "Andijon viloyati"}).json()
    assert first["current_temp_c"] == second["current_temp_c"]
    assert first["forecast"] == second["forecast"]
