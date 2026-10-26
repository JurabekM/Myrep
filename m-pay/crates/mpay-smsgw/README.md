# mpay-smsgw

Virtual SMS shlyuzi — 2-faza P2.1 (ADR-0016). Bankning SMS shlyuzi o'rnida turadi va
`mpay-server` ning `[otp] channel = "webhook"` kanalini telefonsiz sinash imkonini beradi.
**Faqat sinov va demo vositasi**: xabarlar xotirada saqlanadi, ishlab chiqarishga kirmaydi.

| Endpoint | Vazifasi |
|---|---|
| `POST /send` | `{"to":"+998…","text":"…","reference":"<challenge_id>"}`, `Authorization: Bearer <token>` → `202 {"id"}`; telefon E.164 bo'lmasa `422`, token noto'g'ri bo'lsa `401` |
| `GET /messages?to=+998…` | "virtual telefonlar" qutisi (shu token bilan) |
| `DELETE /messages` | qutini tozalash |
| `POST /alerts` | Alertmanager webhook'i (virtual navbatchi kanali, compose'da) |
| `GET /alerts` | qabul qilingan ogohlantirishlar: nomi, holati, darajasi, instansiya |
| `GET /healthz` | `ok` |

Logga faqat maskalangan telefon (`+998*******01`) va `reference` yoziladi — SMS matni (ichida OTP) yo'q.
Kutubxona sifatida `Gateway::fail_next(n)` operator nosozligini (`503`) simulyatsiya qiladi —
`tests/e2e/tests/p2_otp.rs` shundan foydalanadi.

## Ishga tushirish

```bash
MPAY_SMS_TOKEN=sinov-tokeni cargo run -p mpay-smsgw -- --listen 127.0.0.1:47700
```

`mpay.toml` da:

```toml
[otp]
channel = "webhook"

[otp.webhook]
url = "http://127.0.0.1:47700/send"
token_env = "MPAY_SMS_TOKEN"
```

Server ham shu `MPAY_SMS_TOKEN` bilan ishga tushiriladi. Kelgan SMS:

```bash
curl -s -H "Authorization: Bearer sinov-tokeni" "http://127.0.0.1:47700/messages?to=%2B998000000001"
```

Demo hisoblarining telefonlari (`init`) — fiktiv `+99800000000N` (`+998 00` operator kodi mavjud emas).
