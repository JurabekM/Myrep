# M-Pay Pay Sandbox — HTTP API

> Holat: **M4 — barcha sandbox endpointlari amalga oshirilgan**.
> DTO'lar: `crates/mpay-common/src/api.rs`, marshrutlar: `crates/mpay-server/src/routes.rs`.

## 1. Umumiy qoidalar

* Ochiq JSON: `application/json`. PQ Link tanalari: `application/x-mpay-pqlink` (`docs/specs/pqlink.md`).
* Ochiq xato: HTTP status + `{"error": {"code": "TOKEN_NOT_FOUND", "message": "..."}}`.
  5xx xatolarda `message` = `"ichki xato"`, tafsilot faqat server logida.
* Rollar: `operator`, `terminal` — `Authorization: Bearer <kalit>`. Konfiguratsiyada faqat
  `SHA-256(kalit)` saqlanadi. Qurilma endpointlari PQ Link sessiyasi bilan himoyalangan.
* Javoblarda PAN faqat maskalangan (`990012******3456`). Ochiq PAN/DPAN va LUK faqat PQ Link
  muhrlangan javoblarda.
* So'rov tanasi chegarasi — 256 KiB.

### 1.1 Muhrlangan (sealed) endpointlar

So'rov tanasi — PQ Link `Record` (c2s), ichida JSON. Javob:

* yozuv ochildi → muhrlangan `Record` (s2c), ichida konvert:
  `{"ok": true, "data": {...}}` yoki `{"ok": false, "error": {"code", "message"}}`; HTTP status konvertga mos;
* yozuvni ochib bo'lmadi → **ochiq** JSON xato (`PQLINK_SESSION` 401, `PQLINK_REPLAY` 409,
  `PQLINK_MALFORMED` 400).

Client javob `Content-Type` iga qarab uni ochadi yoki ochiq xato sifatida o'qiydi — shu tufayli
`seq` hisoblagichlari doim mos qoladi.

## 2. Endpointlar

| Metod | Yo'l | Kim | Tana | Tavsif |
|---|---|---|---|---|
| GET | `/healthz` | — | — | holat, versiya, KeyStore backend, sessiyalar soni |
| GET | `/v1/pqlink/identity` | — | — | server ochiq kalitlari va barmoq izi |
| POST | `/v1/pqlink/hello` | qurilma | PQ Link | ClientHello → ServerHello |
| POST | `/v1/pqlink/finish` | qurilma | PQ Link | ClientFinished → ServerAccept |
| POST | `/v1/tokens` | qurilma | sealed | provisioning |
| POST | `/v1/tokens/{token_id}/idv/verify` | qurilma | sealed | YELLOW: OTP |
| POST | `/v1/tokens/{token_id}/luks` | qurilma | sealed | LUK to'ldirish |
| GET | `/v1/tokens/{token_id}` | operator | — | token holati (maskalangan) |
| POST | `/v1/tokens/{token_id}/suspend` | operator | — | ACTIVE → SUSPENDED |
| POST | `/v1/tokens/{token_id}/resume` | operator | — | SUSPENDED → ACTIVE |
| DELETE | `/v1/tokens/{token_id}` | operator | — | → DELETED (LUK'lar bekor qilinadi, qaytarib bo'lmaydi) |
| GET | `/v1/audit/verify` | operator | — | audit xesh-zanjirini tekshirish |
| GET | `/v1/sandbox/otp/{challenge_id}` | operator, faqat sandbox | — | simulyatsiya qilingan OTP |
| POST | `/v1/authorizations` | terminal | JSON | tap natijasi → ISO 8583 `0100` → `0110` |
| GET | `/v1/sandbox/accounts` | operator, faqat sandbox | — | emitent test hisoblari va qoldiqlar |

## 3. Sxemalar

### 3.1 `GET /v1/pqlink/identity`

```json
{
  "suite": "PQL1_X25519MLKEM768_ED25519MLDSA65_CHACHA20POLY1305_SHA256",
  "ed25519": "<64 hex>",
  "mldsa65": "<3904 hex>",
  "fingerprint": "<64 hex>"
}
```

Sandbox'da qurilma birinchi ulanishda pinlaydi (TOFU) va `mpay-server init` chiqargan barmoq izi
bilan solishtiradi. Production'da barmoq izi ilovaga oldindan joylanadi.

### 3.2 `POST /v1/tokens` (sealed)

So'rov:

```json
{ "pan": "9900121000010014", "expiry": "3112" }
```

Javob (`data`) — `status` bo'yicha:

```json
{ "status": "ACTIVE",
  "token_id": "tok_<32 hex>", "dpan": "990077…", "dpan_expiry": "2910", "psn": 0,
  "aid": "F04D50415901", "scheme": "MPAY-AES128-CMAC-V1",
  "luks": [ { "seq": 1, "key": "<32 hex>", "issued_at": 1792, "expires_at": 1793, "max_uses": 10 } ],
  "idv": { "decision": "GREEN", "score": 100, "reasons": ["STUB_SCENARIO_10"] } }

{ "status": "PENDING_IDV", "token_id": "tok_…", "challenge_id": "chl_<32 hex>",
  "otp_expires_at": 1792, "idv": { "decision": "YELLOW", … } }

{ "status": "DECLINED", "idv": { "decision": "RED", … } }
```

Xatolar: `BAD_REQUEST` (FPAN emas, real BIN, Luhn, muddat), `TOO_MANY_TOKENS`, `IDV_UNAVAILABLE`.

### 3.3 `POST /v1/tokens/{token_id}/idv/verify` (sealed)

So'rov: `{"challenge_id": "chl_…", "otp": "123456"}`. Javob: token profili (`ACTIVE` dagi
`token_id … luks` maydonlari, `status` va `idv` siz).
Xatolar: `OTP_INVALID` (422), `OTP_EXPIRED` (410), `OTP_LOCKED` (423, 3 urinish),
`CHALLENGE_NOT_FOUND`, `DEVICE_MISMATCH` (403), `INVALID_STATE` (409).

### 3.4 `POST /v1/tokens/{token_id}/luks` (sealed)

So'rov: `{}`. Javob: `{"luks": [...]}`. Faqat `ACTIVE` token, faqat bog'langan qurilma; faol
LUK'lar `2 × batch_size` dan ko'p bo'lsa `TOO_MANY_LUKS`.

### 3.5 Operator: token holati

```json
{ "token_id": "tok_…", "state": "ACTIVE", "dpan_masked": "990077******1234",
  "fpan_masked": "990012******0014", "dpan_expiry": "2910", "device_id": "<64 hex>",
  "idv_decision": "GREEN", "luks_active": 5, "luks_issued": 5, "last_atc": null,
  "created_at": 1792, "updated_at": 1792 }
```

`suspend`/`resume`/`DELETE` — xuddi shu ko'rinishni qaytaradi; ruxsat etilmagan o'tish — `INVALID_STATE` (409).

### 3.6 `GET /v1/audit/verify`

`{"entries": 7, "head_hash": "<64 hex>"}` yoki `AUDIT_BROKEN` (500).

### 3.7 `GET /v1/sandbox/otp/{challenge_id}`

`{"challenge_id": "chl_…", "otp": "123456"}` — faqat `sandbox = true` va `sandbox_api.expose_otp = true`.

### 3.8 `POST /v1/authorizations` (terminal)

Acquirer shlyuzi: terminal JSON → ISO 8583 `0100` (ikkilik, `crates/mpay-common/src/iso8583.rs`) →
emitent emulyatori → `0110` → JSON.

So'rov:

```json
{ "terminal_id": "TERM0001", "merchant_id": "SHOP0000000001", "stan": 1,
  "icc_data": "<BER-TLV hex: GPO javobi (82, 57, 5F34, 5F24, 9F36, 9F26, 9F27, 9F10) + PDOL teglari>" }
```

`0100` maydonlari: 2 = DPAN (`57` dan), 3 = `000000`, 4 = `9F02`, 7 = UTC `MMDDhhmmss`, 11 = STAN,
14 = token muddati, 22 = `071`, 35 = Track 2 (`=`), 37 = RRN (`yDDDhh` + STAN), 41/42 = probel bilan
to'ldirilgan, 49 = `5F2A`, 55 = ARQC, CID, IAD, UN, ATC, TVR, sana, tur, summa, valyuta, AIP,
mamlakat, boshqa summa.

Javob:

```json
{ "approved": true, "response_code": "00", "reason": "APPROVED", "stan": 1, "rrn": "629612000001",
  "dpan_masked": "990077******1234", "amount_minor": 1250000, "currency": 860,
  "issuer_auth_data": "<ARPC(4) ‖ ARC(2), hex>", "risk_score": 50 }
```

`response_code`: `00`, `05`, `51`, `59`, `91`, `Q1` (ADR-0007). `reason`: `APPROVED`,
`APPROVED_AFTER_REVIEW`, `UNKNOWN_TOKEN`, `TOKEN_NOT_ACTIVE`, `LUK_UNKNOWN`, `LUK_EXPIRED`,
`LUK_EXHAUSTED`, `ARQC_MISMATCH`, `ATC_REPLAY`, `FIELD_MISMATCH`, `ICC_DATA_MISSING`,
`UNSUPPORTED_SCHEME`, `ISSUER_OFFLINE`, `RISK_DECLINE`, `RISK_REVIEW`, `ACCOUNT_NOT_FOUND`,
`CURRENCY_MISMATCH`, `INSUFFICIENT_FUNDS`. `issuer_auth_data` faqat ARQC to'g'ri bo'lganda
(replay'da — yo'q). Xatolar: `BAD_REQUEST` (ICC hex/TLV, Track 2, maydon uzunliklari),
`ISSUER_ERROR` / `ISSUER_FORMAT` (502).

### 3.9 `GET /v1/sandbox/accounts` (operator, faqat sandbox)

Emitent test hisoblari: `[{"account_id", "pan_masked", "label", "currency", "balance_minor"}]`.

## 4. Xato kodlari

| Kod | HTTP |
|---|---|
| `BAD_REQUEST` | 400 |
| `UNAUTHORIZED` / `FORBIDDEN` | 401 / 403 |
| `TOKEN_NOT_FOUND`, `CHALLENGE_NOT_FOUND`, `NOT_FOUND` | 404 |
| `INVALID_STATE`, `TOO_MANY_TOKENS`, `TOO_MANY_LUKS` | 409 |
| `DEVICE_MISMATCH` | 403 |
| `OTP_INVALID` / `OTP_EXPIRED` / `OTP_LOCKED` | 422 / 410 / 423 |
| `UNSUPPORTED_MEDIA_TYPE` | 415 |
| `IDV_UNAVAILABLE`, `PQLINK_BUSY` | 503 |
| `PQLINK_MALFORMED`, `PQLINK_HANDSHAKE` | 400 |
| `PQLINK_ATTESTATION`, `PQLINK_AUTH` | 403 |
| `PQLINK_SESSION` / `PQLINK_REPLAY` | 401 / 409 |
| `DB_ERROR`, `CRYPTO_ERROR`, `AUDIT_BROKEN`, `PQLINK_INTERNAL` | 500 |
