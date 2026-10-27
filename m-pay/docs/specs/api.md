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
| POST | `/v1/tokens/{token_id}/idv/resend` | qurilma | sealed | OTP SMS'ni qayta yuborish (ADR-0016) |
| POST | `/v1/tokens/{token_id}/luks` | qurilma | sealed | LUK to'ldirish |
| GET | `/v1/tokens/{token_id}` | operator | — | token holati (maskalangan) |
| POST | `/v1/tokens/{token_id}/suspend` | operator | — | ACTIVE → SUSPENDED |
| POST | `/v1/tokens/{token_id}/resume` | operator | — | SUSPENDED → ACTIVE |
| DELETE | `/v1/tokens/{token_id}` | operator | — | → DELETED (LUK'lar bekor qilinadi, qaytarib bo'lmaydi) |
| GET | `/v1/audit/verify` | operator | — | audit xesh-zanjirini tekshirish |
| GET | `/v1/recon?date=YYYY-MM-DD` | operator | — | solishtirish hisoboti: acquirer jurnali ↔ emitent (ADR-0024) |
| GET | `/v1/sandbox/otp/{challenge_id}` | operator, faqat sandbox | — | simulyatsiya qilingan OTP |
| POST | `/v1/authorizations` | terminal | JSON | tap natijasi → ISO 8583 `0100` → `0110` |
| GET | `/v1/pqlink/revocations` | — | — | oflayn ildiz imzolagan bekor qilingan identifikatorlar (ADR-0014; sozlanmagan — 404) |
| POST | `/v1/devices/rekey` | qurilma (sealed) | `{cert_chain[], signature}` | qurilma kalitini almashtirish, tokenlar ko'chadi (ADR-0015) |
| POST | `/v1/pqlink/enroll` | — (IP chegarasi) | `{}` | yangi qurilma uchun bir martalik nonce: `{nonce, expires_at}` (P1.7) |
| GET | `/v1/terminal/ping` | terminal | — | diagnostika: `{key_id, mtls, server_time}` (kalit, mTLS, chegaralar) |
| GET | `/v1/sandbox/accounts` | operator, faqat sandbox | — | emitent test hisoblari va qoldiqlar |
| POST | `/v1/sandbox/integrity-token` | operator, faqat `[integrity] mode = "mock"` | `{request_hash, preset?}` | Play Integrity o'rnida mock token (§3.10, ADR-0021) |
| POST | `/v1/sandbox/integrity-token/device` | qurilma (sealed), faqat `mode = "mock"` | `{request_hash, preset?}` | o'sha mock token o'z PQ Link sessiyasi uchun — operator kaliti/mTLS'siz (§3.10) |

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
{ "pan": "9900121000010014", "expiry": "3112", "integrity_token": "<Play Integrity tokeni>" }
```

`integrity_token` (2-faza P2.6, ADR-0021) — Play Integrity standart so'rovi tokeni,
`requestHash = base64url(SHA-256("MPAY-PI-V1" ‖ 0x00 ‖ "provision" ‖ 0x00 ‖ PQ Link sessiya ID))`
(paddingsiz; PAN kirmaydi). `[integrity] required = true` bo'lsa majburiy. Server: token haqiqiyligi
(mock — ES256 imzo, google — `decodeIntegrityToken`), paket nomi, imzo sertifikati, `requestHash` va
yangilik (`max_age_secs`); verdict sifati Shield ID&V qoidalarida (`IDV_INTEGRITY_*`).

Javob (`data`) — `status` bo'yicha:

```json
{ "status": "ACTIVE",
  "token_id": "tok_<32 hex>", "dpan": "990077…", "dpan_expiry": "2910", "psn": 0,
  "aid": "F04D50415901", "scheme": "MPAY-AES128-CMAC-V1",
  "luks": [ { "seq": 1, "key": "<32 hex>", "issued_at": 1792, "expires_at": 1793, "max_uses": 10 } ],
  "cvm_limit_minor": 100000000,
  "idv": { "decision": "GREEN", "score": 100, "reasons": ["STUB_SCENARIO_10"] } }

{ "status": "PENDING_IDV", "token_id": "tok_…", "challenge_id": "chl_<32 hex>",
  "otp_expires_at": 1792, "idv": { "decision": "YELLOW", … },
  "otp_sent_to": "+998*******01" }

{ "status": "DECLINED", "idv": { "decision": "RED", … } }
```

`otp_sent_to` — `[otp] channel = "webhook"` da kod yuborishga qo'yilgan emitentdagi telefon
(maskalangan). SMS fonda yuboriladi — shlyuz sekin bo'lsa ham javob kechikmaydi; yetib kelmasa
qurilma `/idv/resend` qiladi. Sandbox kanalida yoki emitentda raqam bo'lmasa maydon yo'q (ADR-0016).

`cvm_limit_minor` (P2.7, ADR-0022) — shu summadan (tiyin) yuqori tap'da qurilma CDCVM so'raydi; emitent
ham tekshiradi (`Q2`). LUK to'ldirish javobida (`{"luks": [...], "cvm_limit_minor": …}`) joriy qiymat keladi.

Xatolar: `BAD_REQUEST` (FPAN emas, real BIN, Luhn, muddat), `TOO_MANY_TOKENS`, `TOO_MANY_DEVICES`,
`CARD_ALREADY_ON_DEVICE`, `IDV_UNAVAILABLE`,
`INTEGRITY_REQUIRED` (403), `INTEGRITY_INVALID` (403: imzo, paket, sertifikat, boshqa sessiya, eskirgan —
sabab faqat server logida), `INTEGRITY_UNAVAILABLE` (503 + `Retry-After`: Google javob bermadi).

### 3.3 `POST /v1/tokens/{token_id}/idv/verify` (sealed)

So'rov: `{"challenge_id": "chl_…", "otp": "123456"}`. Javob: token profili (`ACTIVE` dagi
`token_id … luks` maydonlari, `status` va `idv` siz).
Xatolar: `OTP_INVALID` (422), `OTP_EXPIRED` (410), `OTP_LOCKED` (423, 3 urinish),
`CHALLENGE_NOT_FOUND`, `DEVICE_MISMATCH` (403), `INVALID_STATE` (409).

### 3.3a `POST /v1/tokens/{token_id}/idv/resend` (sealed)

So'rov: `{"challenge_id": "chl_…"}`. Javob: `{"otp_sent_to": "+998*******01"}` — o'sha kod
karta egasining emitentdagi raqamiga qayta yuborildi (ADR-0016).
Xatolar: `OTP_RESEND_LIMIT` (429, challenge uchun 3 marta; SMS aniq ketmagan urinishlar hisoblanmaydi),
`OTP_LOCKED` (423, 3 noto'g'ri kod — SMS yuborilmaydi), `OTP_EXPIRED` (410), `CHALLENGE_NOT_FOUND` (404),
`INVALID_STATE` (409, token `PENDING_IDV` emas), `DEVICE_MISMATCH` (403), `NO_CONTACT` (409, emitentda
raqam yo'q), `OTP_CHANNEL_DISABLED` (409, sandbox kanali), `OTP_DELIVERY_FAILED` (502, shlyuz javob bermadi).

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

### 3.10 `POST /v1/sandbox/integrity-token` (operator, faqat sandbox)

```json
{ "request_hash": "<43 belgi base64url>", "preset": "strong" }
```

→ `{"integrity_token": "<JWS>"}`. Stsenariylar: `strong` (standart), `device`, `basic`, `no_integrity`,
`unrecognized`, `play_protect_risk`, `remote_control`. Faqat `[integrity] mode = "mock"` (u faqat
`sandbox = true` bilan ruxsat); aks holda 404. `mpay-tsim` shu yerdan oladi.

`POST /v1/sandbox/integrity-token/device` — o'sha so'rov, lekin **muhrlangan** (PQ Link): kalit va mTLS
sertifikati kerak emas, `request_hash` **shu sessiyaniki** bo'lishi shart (aks holda 400). Emulyatordagi
demo ilova shundan foydalanadi — TLS + mTLS sandbox'ida ham (operator yo'li u yerda `403 MTLS_REQUIRED`).

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

`response_code`: `00`, `05`, `51`, `54`, `59`, `91`, `Q1`, `Q2` (ADR-0007, ADR-0022). `Q2` — terminal
"telefonda tasdiqlang" ko'rsatadi va o'sha summa bilan qayta tap kutadi. `reason`: `APPROVED`,
`APPROVED_AFTER_REVIEW`, `UNKNOWN_TOKEN`, `TOKEN_NOT_ACTIVE`, `LUK_UNKNOWN`, `LUK_EXPIRED`,
`LUK_EXHAUSTED`, `ARQC_MISMATCH`, `ATC_REPLAY`, `FIELD_MISMATCH`, `ICC_DATA_MISSING`,
`UNSUPPORTED_SCHEME`, `ISSUER_OFFLINE`, `RISK_DECLINE`, `RISK_REVIEW`, `ACCOUNT_NOT_FOUND`,
`CURRENCY_MISMATCH`, `INSUFFICIENT_FUNDS`, `TOKEN_EXPIRED` (54), `CVM_REQUIRED` va `REVIEW_STEP_UP`
(Q2). `issuer_auth_data` faqat ARQC to'g'ri bo'lganda
(replay'da — yo'q). Xatolar: `BAD_REQUEST` (ICC hex/TLV, Track 2, maydon uzunliklari),
`ISSUER_ERROR` / `ISSUER_FORMAT` (502).

`96` — natija noma'lum (ADR-0024): `ISSUER_TIMEOUT` (emitent `[acquirer] issuer_timeout_ms` ichida
javob bermadi), `ISSUER_RESPONSE_UNREADABLE`, `OUTCOME_UNKNOWN` (avvalgi ishlov tugamagan). Emitent pul
yechgan bo'lsa, server uni avtomatik reversal (`0400`/`0401`) bilan qaytaradi. Terminal o'sha so'rovni
qayta yuborsa — o'sha `96`; xaridni davom ettirish uchun yangi tap (yangi STAN).

### 3.11 `GET /v1/recon` (operator)

Solishtirish (ADR-0024): `?date=YYYY-MM-DD` — sxema vaqti bo'yicha kun (UTC+5; berilmasa — bugun) yoki
`?from=<unix>&to=<unix>` (≤ 7 kun). Acquirer jurnali 3 kun saqlanadi — undan eski davr `BAD_REQUEST`.

```json
{ "from": 1793041200, "to": 1793127600, "generated_at": 1793090000,
  "acquirer_records": 120, "issuer_records": 121, "matched": 119,
  "approved": [{ "currency": 860, "count": 101, "amount_minor": 125000000 }],
  "discrepancies": [{ "kind": "ISSUER_ONLY_APPROVED", "terminal_id": "TERM0001",
    "merchant_id": "SHOP0000000001", "stan": "000011", "rrn": "630014000011",
    "dpan_masked": "990077******1234", "at": 1793050000, "acquirer_code": null,
    "acquirer_amount_minor": null, "issuer_code": "00", "issuer_amount_minor": 200000,
    "issuer_reversed": false, "currency": 860, "reversal": null }],
  "notes": [] }
```

`kind`: `ISSUER_ONLY_APPROVED`, `ACQUIRER_ONLY_APPROVED`, `AMOUNT_MISMATCH`, `REVERSAL_FAILED`
(tafovutlar); `REVERSAL_PENDING`, `IN_FLIGHT` (`notes` — vaqtinchalik). PAN yo'q. CLI:
`mpay-server recon --date … [--out report.json]` (tafovut bo'lsa chiqish kodi 1).

### 3.9 `GET /v1/sandbox/accounts` (operator, faqat sandbox)

Emitent test hisoblari: `[{"account_id", "pan_masked", "label", "currency", "balance_minor"}]`.

## 4. Xato kodlari

| Kod | HTTP |
|---|---|
| `BAD_REQUEST` | 400 |
| `UNAUTHORIZED` / `FORBIDDEN` | 401 / 403 |
| `TOKEN_NOT_FOUND`, `CHALLENGE_NOT_FOUND`, `NOT_FOUND` | 404 |
| `INVALID_STATE`, `TOO_MANY_TOKENS`, `TOO_MANY_LUKS` | 409 |
| `TOO_MANY_DEVICES` (karta `max_devices_per_card` qurilmada), `CARD_ALREADY_ON_DEVICE` (ADR-0022) | 409 |
| `TOKEN_EXPIRED` (LUK to'ldirish; token muddati o'tgan) | 410 |
| `DEVICE_MISMATCH` | 403 |
| `OTP_INVALID` / `OTP_EXPIRED` / `OTP_LOCKED` | 422 / 410 / 423 |
| `UNSUPPORTED_MEDIA_TYPE` | 415 |
| `IDV_UNAVAILABLE`, `PQLINK_BUSY`, `INTEGRITY_UNAVAILABLE` | 503 |
| `INTEGRITY_REQUIRED`, `INTEGRITY_INVALID` (provisioning, ADR-0021) | 403 |
| `PQLINK_MALFORMED`, `PQLINK_HANDSHAKE` | 400 |
| `PQLINK_ATTESTATION`, `PQLINK_AUTH`, `PQLINK_ENROLLMENT` | 403 |
| `PQLINK_SESSION` / `PQLINK_REPLAY` | 401 / 409 |
| `DB_ERROR`, `CRYPTO_ERROR`, `AUDIT_BROKEN`, `PQLINK_INTERNAL` | 500 |
| `MTLS_REQUIRED` (`require_mtls`: sertifikat yo'q yoki CN ≠ kalit id) | 403 |
| `REATTEST_REQUIRED` (muhrlangan; attestatsiya `reattest_after_days` dan eski — `/v1/devices/rekey`) | 403 |
| `RATE_LIMITED` | 429 (+ `Retry-After`) |
| `BUSY` (handshake navbati to'la) | 503 (+ `Retry-After`) |
| `REQUEST_IN_PROGRESS` (shu avtorizatsiya hali ishlanmoqda) | 409 (+ `Retry-After`) |

## 5. So'rovlar chegarasi (1-faza, P1.1)

`[rate_limit]` (standart qiymatlar `mpay-server init` yozadi):

| Chegara | Kalit | Standart | Oshganda |
|---|---|---|---|
| `/v1/pqlink/hello`, `/finish` | mijoz IP | 300/daqiqa, burst 60 | 429 |
| Bir vaqtdagi handshake hisoblashlari | global | CPU × 2 | 503 `BUSY` |
| Operator/terminal endpointlari | API kaliti | 500/s, burst 1000 | 429 |
| Muhrlangan endpointlar | qurilma | 60/daqiqa, burst 30 | 429 (javob muhrlangan — sessiya buzilmaydi) |

Mijoz `Retry-After` dan keyin qayta urinadi. Teskari proksi ortida: `[http] trusted_proxies = ["10.0.0.0/8"]`
— ulanish shu tarmoqlardan kelsa mijoz IP'si `X-Forwarded-For` dan o'ngdan chapga (birinchi ishonchsiz
manzil) olinadi; boshqa ulanishlarda sarlavha e'tiborsiz (soxtalashtirib bo'lmaydi).

## 6. Takroriy avtorizatsiya so'rovlari (1-faza, P1.2)

`POST /v1/authorizations` `(terminal_id, stan, UTC sana)` bo'yicha eslab qolinadi (3 kun):

* aynan bir xil so'rov (merchant va `icc_data` ham) — birinchi javob qaytariladi (timeout'dan keyin
  xavfsiz qayta yuborish; emitentga ikkinchi marta bormaydi);
* shu STAN boshqa mazmun bilan — `200`, `response_code = "94"`, `reason = "DUPLICATE_TRANSMISSION"`,
  `rrn` bo'sh;
* birinchisi hali ishlanmoqda — `409 REQUEST_IN_PROGRESS`.

