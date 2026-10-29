# mpay-vault

Token Vault: provisioning, ID&V, LUK, lifecycle, detokenizatsiya va audit.

* **Saqlash** (`migrations/1001_vault_init.sql` …): PAN va DPAN faqat AES-256-GCM shifrmatni
  (KEK → DEK envelope, kontekst AAD `card:{id}:pan` / `token:{id}:dpan`), qidiruv HMAC-SHA256
  barmoq izi bo'yicha. LUK'lar saqlanmaydi — faqat metama'lumot (seq, muddat, limit, foydalanish).
  OTP saqlanmaydi — `HMAC(PAN-IDX, challenge_id)` dan hosil qilinadi.
* **Provisioning**: FPAN → `IdvDecider` (Shield) → GREEN: token + LUK partiyasi; YELLOW: OTP
  challenge (5 daqiqa, 3 urinish); RED: rad (token yaratilmaydi, audit yoziladi).
* **Lifecycle**: `PENDING_IDV → ACTIVE ⇄ SUSPENDED → DELETED`; o'chirishda LUK'lar bekor qilinadi.
  Hamyon (ADR-0030): `device_tokens`, `device_token`, `device_set_state` — faqat o'z qurilmasi;
  `suspended_by` (`DEVICE`/`BANK`, migratsiya `1004`) — bank to'xtatganini qurilma yoqa olmaydi
  (`SUSPENDED_BY_BANK`), tekshiruv o'tish tranzaksiyasi ichida.
* **LUK**: partiya (standart 5), har biri 10 foydalanish / 24 soat; to'ldirish faqat bog'langan
  qurilmadan, faol LUK'lar ≤ 2 × partiya.
* **Token muddati** (ADR-0022): `min(hozir + token_validity_months, karta muddati)`, sxema vaqti bilan
  (UTC+5, `CardExpiry::end_unix`). `renew_token` — oxirgi `token_renew_before_days` kunda (yoki muddat
  o'tgach) karta muddati doirasida uzaytiradi (DPAN, PSN, LUK'lar o'zgarmaydi; audit `TOKEN_RENEWED`;
  takroriy chaqiruv o'zgartirmaydi). Har token o'z karta muddatini saqlaydi (migratsiya `1003`). Muddati
  o'tgan tokenlar chegaralarda hisoblanmaydi — yangilangan karta bilan qayta qo'shish mumkin.
* **Detokenizatsiya**: faqat [`VaultDetokenizer`] porti (issuer'ga beriladi, HTTP'da yo'q):
  `lookup` (o'zgartirmaydi) va `consume` (ARQC'dan keyin: LUK hisoblagichi + ATC monotonligi, atomar).
* **Audit**: har o'zgarish va detokenizatsiya — append-only (trigger'lar), xesh-zanjirli; `verify`.
* **Tranzaksiyalar** (`mpay-db`, ADR-0009, ADR-0018): SQLite yoki PostgreSQL (`sqlx::Any`).
  Yozuvchilar `Db::begin_write`: SQLite'da jarayon qulfi + `BEGIN IMMEDIATE` (hovuz 1 ulanish),
  PostgreSQL'da parallel; poygasi bor joylarda `FOR UPDATE` / advisory qulflar (ATC iste'moli, OTP,
  holat o'tishlari, provisioning hisoblari, audit zanjiri). Tranzaksiya ochiq turganda hovuzdan boshqa
  so'rov qilinmaydi — tayyorgarlik (DEK, DPAN, shifrlash) undan oldin, ichida faqat `&mut tx`.
  Migratsiyalar: `migrations/sqlite` va `migrations/postgres`. PostgreSQL'da sinov:
  `MPAY_TEST_PG_URL=postgres://… cargo test -p mpay-vault -p mpay-e2e`.

## Testlar

```bash
cargo test -p mpay-vault
```

`tests/vault_flow.rs`: GREEN/YELLOW/RED, OTP lockout/muddat, lifecycle, mahsulot siyosati (karta
qurilmalari chegarasi `max_devices_per_card`, takroriy karta, LUK token muddatigacha; ADR-0022), detokenizatsiya qoidalari
(ATC replay, LUK limiti/muddati/noma'lum), DB faylida ochiq PAN/DPAN/LUK yo'qligi, audit
zanjiri va trigger'lar, qayta ochish (dev-urug').
