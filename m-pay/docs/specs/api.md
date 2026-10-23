# M-Pay Pay Sandbox — HTTP API

> Holat: **M0 qoralama**, M3–M4 da yakunlanadi.

Umumiy qoidalar:

* JSON so'rov/javoblar `application/json`; PQ Link muhrlangan tanalar `application/x-mpay-pqlink`.
* Xatolar: `{"error": {"code": "TOKEN_NOT_FOUND", "message": "..."}}` va mos HTTP status.
* Autentifikatsiya: `Authorization: Bearer <kalit>`; rollar `operator`, `terminal`.
  Qurilma endpointlari PQ Link sessiyasi bilan himoyalangan (Bearer kerak emas).
* Javoblarda PAN faqat maskalangan holda.

| Metod | Yo'l | Kim | Tavsif |
|---|---|---|---|
| GET | `/healthz` | — | holat va versiya |
| GET | `/v1/pqlink/identity` | — | server ochiq kalitlari va `server_fp` |
| POST | `/v1/pqlink/hello` | qurilma | ClientHello → ServerHello |
| POST | `/v1/pqlink/finish` | qurilma | ClientFinished → ServerAccept |
| POST | `/v1/tokens` | qurilma (PQ Link) | provisioning |
| POST | `/v1/tokens/{token_id}/idv/verify` | qurilma (PQ Link) | YELLOW: OTP tasdiqlash |
| POST | `/v1/tokens/{token_id}/luks` | qurilma (PQ Link) | LUK to'ldirish (replenish) |
| GET | `/v1/tokens/{token_id}` | operator | token holati (maskalangan) |
| POST | `/v1/tokens/{token_id}/suspend` | operator | ACTIVE → SUSPENDED |
| POST | `/v1/tokens/{token_id}/resume` | operator | SUSPENDED → ACTIVE |
| DELETE | `/v1/tokens/{token_id}` | operator | → DELETED (qaytarib bo'lmaydi) |
| POST | `/v1/authorizations` | terminal | tap natijasi → ISO 8583 `0100` → `0110` |
| GET | `/v1/audit/verify` | operator | audit xesh-zanjirini tekshirish |
| GET | `/v1/sandbox/otp/{challenge_id}` | operator, faqat sandbox | simulyatsiya qilingan OTP |

Batafsil so'rov/javob sxemalari: `TODO(M3):`.
