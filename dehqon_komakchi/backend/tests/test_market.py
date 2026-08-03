from datetime import datetime, timedelta, timezone


def _listing_payload(**overrides):
    payload = {
        "variety": "San Marzano",
        "quantity_kg": 500,
        "price_som": 4000,
        "negotiable": False,
        "region": "Farg'ona viloyati",
        "availability_date": (datetime.now(timezone.utc) + timedelta(days=3)).isoformat(),
        "contact_method": "phone",
        "contact_value": "+998901112233",
        "contact_consent": True,
    }
    payload.update(overrides)
    return payload


def test_create_and_list_listing(client, authed_headers):
    resp = client.post("/v1/market/listings", json=_listing_payload(), headers=authed_headers)
    assert resp.status_code == 201
    body = resp.json()
    assert body["variety"] == "San Marzano"
    assert body["contact_value"] == "+998901112233"

    listings = client.get("/v1/market/listings").json()
    assert any(item["id"] == body["id"] for item in listings)


def test_create_listing_requires_auth(client):
    resp = client.post("/v1/market/listings", json=_listing_payload())
    assert resp.status_code == 401


def test_contact_hidden_without_consent(client, authed_headers):
    resp = client.post(
        "/v1/market/listings",
        json=_listing_payload(contact_consent=False),
        headers=authed_headers,
    )
    assert resp.status_code == 201
    assert resp.json()["contact_value"] is None


def test_negotiable_listing_has_no_price(client, authed_headers):
    resp = client.post(
        "/v1/market/listings",
        json=_listing_payload(negotiable=True, price_som=9999),
        headers=authed_headers,
    )
    assert resp.status_code == 201
    assert resp.json()["price_som"] is None


def test_filter_listings_by_region(client, authed_headers):
    client.post("/v1/market/listings", json=_listing_payload(region="Xorazm viloyati"), headers=authed_headers)
    client.post("/v1/market/listings", json=_listing_payload(region="Buxoro viloyati"), headers=authed_headers)

    result = client.get("/v1/market/listings", params={"region": "Xorazm viloyati"}).json()
    assert all(item["region"] == "Xorazm viloyati" for item in result)
    assert len(result) >= 1


def test_owner_can_delete_own_listing(client, authed_headers):
    created = client.post("/v1/market/listings", json=_listing_payload(), headers=authed_headers).json()
    resp = client.delete(f"/v1/market/listings/{created['id']}", headers=authed_headers)
    assert resp.status_code == 204

    listings = client.get("/v1/market/listings").json()
    assert not any(item["id"] == created["id"] for item in listings)


def test_reporting_a_listing_enough_times_auto_hides_it(client, authed_headers):
    created = client.post("/v1/market/listings", json=_listing_payload(), headers=authed_headers).json()
    listing_id = created["id"]

    reporter_phones = ["+998911111111", "+998922222222", "+998933333333"]
    for phone in reporter_phones:
        req = client.post("/v1/auth/otp/request", json={"phone_number": phone}).json()
        verify = client.post(
            "/v1/auth/otp/verify",
            json={"request_id": req["request_id"], "code": "123456"},
        ).json()
        headers = {"Authorization": f"Bearer {verify['access_token']}"}
        resp = client.post(
            f"/v1/market/listings/{listing_id}/report",
            json={"reason": "spam", "note": ""},
            headers=headers,
        )
        assert resp.status_code == 204

    listings = client.get("/v1/market/listings").json()
    assert not any(item["id"] == listing_id for item in listings)


def test_create_group_and_aggregated_quantity(client, authed_headers):
    group = client.post(
        "/v1/market/groups",
        json={"name": "Farg'ona pomidorchilari", "region": "Farg'ona viloyati"},
        headers=authed_headers,
    ).json()

    client.post(
        "/v1/market/listings",
        json=_listing_payload(group_id=group["id"], quantity_kg=300),
        headers=authed_headers,
    )
    client.post(
        "/v1/market/listings",
        json=_listing_payload(group_id=group["id"], quantity_kg=200),
        headers=authed_headers,
    )

    groups = client.get("/v1/market/groups").json()
    updated = next(g for g in groups if g["id"] == group["id"])
    assert updated["aggregated_quantity_kg"] == 500.0


def test_create_listing_validates_quantity(client, authed_headers):
    resp = client.post(
        "/v1/market/listings",
        json=_listing_payload(quantity_kg=-5),
        headers=authed_headers,
    )
    assert resp.status_code == 422
