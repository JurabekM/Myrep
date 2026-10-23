# mpay-vault

Token Vault: provisioning, ID&V, LUK, lifecycle, detokenizatsiya va audit.

* **Saqlash** (SQLite, `migrations/1001_vault_init.sql`): PAN va DPAN faqat AES-256-GCM shifrmatni
  (KEK → DEK envelope, kontekst AAD `card:{id}:pan` / `token:{id}:dpan`), qidiruv HMAC-SHA256
  barmoq izi bo'yicha. LUK'lar saqlanmaydi — faqat metama'lumot (seq, muddat, limit, foydalanish).
  OTP saqlanmaydi — `HMAC(PAN-IDX, challenge_id)` dan hosil qilinadi.
* **Provisioning**: FPAN → `IdvDecider` (Shield) → GREEN: token + LUK partiyasi; YELLOW: OTP
  challenge (5 daqiqa, 3 urinish); RED: rad (token yaratilmaydi, audit yoziladi).
* **Lifecycle**: `PENDING_IDV → ACTIVE ⇄ SUSPENDED → DELETED`; o'chirishda LUK'lar bekor qilinadi.
* **LUK**: partiya (standart 5), har biri 10 foydalanish / 24 soat; to'ldirish faqat bog'langan
  qurilmadan, faol LUK'lar ≤ 2 × partiya.
* **Detokenizatsiya**: faqat [`VaultDetokenizer`] porti (issuer'ga beriladi, HTTP'da yo'q):
  `lookup` (o'zgartirmaydi) va `consume` (ARQC'dan keyin: LUK hisoblagichi + ATC monotonligi, atomar).
* **Audit**: har o'zgarish va detokenizatsiya — append-only (trigger'lar), xesh-zanjirli; `verify`.

## Testlar

```bash
cargo test -p mpay-vault
```

`tests/vault_flow.rs`: GREEN/YELLOW/RED, OTP lockout/muddat, lifecycle, detokenizatsiya qoidalari
(ATC replay, LUK limiti/muddati/noma'lum), DB faylida ochiq PAN/DPAN/LUK yo'qligi, audit
zanjiri va trigger'lar, qayta ochish (dev-urug').
