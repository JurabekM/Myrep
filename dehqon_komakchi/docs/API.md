# Backend API reference

Base URL: `http://<host>/v1`. Interactive Swagger UI is always available at `/docs` (and
ReDoc at `/redoc`) when the server is running -- this file is a quick-scan companion, not a
replacement.

All error responses use a uniform envelope (`app/schemas.py:ErrorOut`):

```json
{ "error": "validation_error", "detail": "Invalid request payload" }
```

Unhandled exceptions are caught and returned the same way (`internal_error`, generic message)
-- the API never leaks stack traces to the client.

## Auth (`/v1/auth`) -- rate limited 10/minute per route

Phone-number + OTP flow. In `AUTH_OTP_MODE=demo` (the default) the code is always `123456` and
no SMS is sent -- no external account needed to develop or demo this end-to-end.

### `POST /v1/auth/otp/request`

```json
// request
{ "phone_number": "+998901234567" }
// response 200
{ "request_id": "…", "demo_code_hint": "Demo rejim: kod 123456" }
```

`phone_number` must match `^\+998\d{9}$`. `demo_code_hint` is `null` outside demo mode.

### `POST /v1/auth/otp/verify`

```json
// request
{ "request_id": "…", "code": "123456" }
// response 200
{ "access_token": "…", "token_type": "bearer" }
```

404 if `request_id` is unknown; 400 if the code is expired (5-minute TTL), already used, or
wrong. On success, creates the `User` row if it doesn't exist yet and issues a JWT (default
7-day expiry, `JWT_EXPIRE_MINUTES`). Send the token as `Authorization: Bearer <token>` on
authenticated routes below.

## Weather (`/v1/weather`)

### `GET /v1/weather?region=<name>`

Returns current conditions + a short forecast for `region` (1-100 chars, required). Backed by
`MockWeatherProvider` by default (deterministic per region+day, so results are stable across
calls on the same day) -- set `WEATHER_PROVIDER_API_KEY` and swap in a real provider in
`app/providers/weather.py` to go live.

```json
{
  "region": "Farg'ona viloyati",
  "current_temp_c": 27.4,
  "current_condition": "Ochiq",
  "forecast": [
    { "epoch_day": 20308, "temp_min_c": 18.2, "temp_max_c": 31.0, "rain_probability_percent": 10, "summary": "Ochiq" }
  ]
}
```

## Diagnosis (`/v1/diagnosis`) -- rate limited 20/minute (POST), auth optional

Server-side parity implementation of the same RGB/HSV heuristic the Android app runs
on-device; not currently called by the app itself (see `docs/ARCHITECTURE.md`).

### `POST /v1/diagnosis` (multipart, field `file`)

Accepts `image/jpeg`, `image/png`, or `image/webp`, max `MAX_UPLOAD_IMAGE_MB` (default 8 MB).

| Status | When |
|---|---|
| 200 | Diagnosis produced |
| 400 | Empty file |
| 413 | File exceeds size limit |
| 415 | Unsupported content type |
| 422 | Photo too small/low quality (`detail.reason`, e.g. `"too_small"`) |

```json
// 200 response
{
  "diagnosis_log_id": "…",
  "category": "FUNGAL",
  "confidence": 0.71,
  "cause": "…",
  "safe_steps": ["…"],
  "watch_for": ["…"],
  "consult_advice": "Shubha bo'lsa, agronomga murojaat qiling.",
  "disclaimer": "Bu umumiy yo'nalish, yakuniy tashxis emas. Shubha bo'lsa, agronomga murojaat qiling."
}
```

`category` is one of `PEST | FUNGAL | NUTRIENT | WATERING | HEAT_STRESS | UNCLEAR`;
`confidence` is capped at 0.95 (the heuristic never claims certainty). Every request is logged
to `DiagnosisLog` (associated with the caller if authenticated, else anonymous) for aggregate
quality metrics only -- never required for the response.

### `POST /v1/diagnosis/rate`

```json
{ "diagnosis_log_id": "…", "useful": true }
```

204 on success, 404 if the id is unknown. Records a binary usefulness signal against the log.

## Bozor marketplace (`/v1/market`)

The one genuinely multi-user feature: listings are visible to every caller, not scoped to a
device. `GET` routes are open; mutating routes require `Authorization: Bearer <token>`.

### `GET /v1/market/listings?region=<name>&min_quantity_kg=<n>`

Returns up to 200 non-hidden listings, newest first. Both query params are optional filters.
`contact_value` is only included when the listing owner set `contact_consent: true`.

### `POST /v1/market/listings` (auth required, 20/minute)

```json
{
  "variety": "San Marzano",
  "quantity_kg": 500,
  "price_som": 4000,
  "negotiable": false,
  "region": "Farg'ona viloyati",
  "availability_date": "2026-08-10T00:00:00+00:00",
  "contact_method": "phone",
  "contact_value": "+998901112233",
  "contact_consent": true,
  "group_id": null
}
```

Returns 201 with the created `ListingOut`. If `negotiable: true`, `price_som` is stored as
`null` regardless of what was sent. 404 if `group_id` doesn't reference an existing group.

### `DELETE /v1/market/listings/{listing_id}` (auth required)

204 on success. 404 if not found; 403 if the caller isn't the listing's owner.

### `POST /v1/market/listings/{listing_id}/report` (auth required, 10/minute)

```json
{ "reason": "spam", "note": "" }
```

`reason` is one of `spam | fraud | inappropriate | other`. 204 on success; 404 if the listing
doesn't exist. After the 3rd independent report (`AUTO_HIDE_REPORT_THRESHOLD` in
`app/routers/market.py`), the listing is auto-hidden from `GET /listings` and an audit event is
logged -- simple, dependency-free moderation with no human reviewer required to keep obvious
spam off the public feed.

### `POST /v1/market/groups` (auth required)

```json
{ "name": "Farg'ona pomidor birlashmasi", "region": "Farg'ona viloyati" }
```

Creates a "sell group" (co-op) with the caller as admin. Returns 201 with `SellGroupOut`.

### `GET /v1/market/groups`

Returns all groups with `aggregated_quantity_kg` computed live as the sum of that group's
non-hidden listings' `quantity_kg` -- lets a group show "how much do we collectively have to
sell" without any client-side aggregation.

## Health

### `GET /health`

`{ "status": "ok" }` -- no auth, no rate limit. Suitable for a load-balancer health check.
