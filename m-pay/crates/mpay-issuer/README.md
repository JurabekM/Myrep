# mpay-issuer

Emitent emulyatori: ISO 8583 `0100` → tekshiruvlar → `0110`. Vault va Shield'ni faqat port
trait'lari (`Detokenizer`, `RiskScorer`) orqali ko'radi.

## Qaror tartibi

1. Format: majburiy maydonlar (2, 3, 4, 7, 11, 14, 22, 35, 37, 41, 42, 49, 55), Track 2 ↔ maydon 2/14,
   CID = ARQC, CDOL (`9F02`, `5F2A`) ↔ maydon 4/49.
2. `Detokenizer::lookup(DPAN, LUK seq)` — noma'lum token `05`.
2a. Token (DPAN) muddati o'tgan — `54` (oyning oxirigacha amal qiladi; ADR-0022).
3. LUK noma'lum / muddati o'tgan / limiti tugagan — `Q1`.
4. ARQC: `IMK → MK_tok → LUK → SK`, constant-time — `Q1` (ARPC berilmaydi).
5. Token holati ≠ ACTIVE — `05`; `Detokenizer::consume` (ATC replay — `Q1`, ARPC berilmaydi).
6. FPAN BIN `offline_bins` da — `91`.
6a. Summa `cvm_limit_minor` dan katta va CVR'da CDCVM bajarilmagan — `Q2` (`CVM_REQUIRED`).
7. Shield: DECLINE — `59`; REVIEW — `review_action`: `step_up` (standart) — CDCVM bo'lsa tasdiq,
   aks holda `Q2` (`REVIEW_STEP_UP`); `approve`; `decline` — `05`.
8. Hisob (PAN barmoq izi bo'yicha) yo'q — `05`; qoldiq yetarli emas — `51` (atomar `UPDATE … WHERE balance >= amount`).
9. Aks holda `00`.

ARQC to'g'ri bo'lsa javobda `55`: `91` = ARPC ‖ ARC, `8A` = ARC. Har avtorizatsiya
`issuer_authorizations` jadvaliga (maskalangan DPAN, sabab, skor) yoziladi; PAN saqlanmaydi.

## Konfiguratsiya (`[issuer]`)

```toml
[issuer]
offline_bins = ["990013"]
review_action = "step_up"   # "approve" yoki "decline" (05)
cvm_limit_minor = 100000000 # 1 000 000,00 UZS — CDCVM'siz eng katta summa (tokenga ham beriladi)

[[issuer.accounts]]
pan = "9900121000010014"
balance_minor = 500000000   # tiyin
label = "GREEN, 5 000 000 UZS"
```

## Reversal (`0400`/`0401` → `0410`, ADR-0024)

`process_reversal_bytes` — asl avtorizatsiya `(terminal, STAN, RRN, merchant)` bo'yicha topiladi
(maydon 2 yo'q), summa va valyuta mos kelishi shart:

* tasdiqlangan va qaytarilmagan — summa yechilgan hisobga (`issuer_authorizations.account_id`)
  qaytadi, `reversed_at` yoziladi; shartli `UPDATE` — parallel xabarlar ikki marta qaytarmaydi → `00`;
* avval qaytarilgan / asl rad etilgan → `00`; topilmadi yoki bir nechta mos → `25`; summa farqli → `13`;
  maydon 90 noto'g'ri → `30`.

Har xabar `issuer_reversals` ga yoziladi (migratsiya `2003`). `report(from, to)` — solishtirish
uchun avtorizatsiyalar (maskalangan DPAN, kod, `reversed_at`). Sandbox: `response_delay_ms` — `0110`
ni commit'dan keyin kechiktiradi (acquirer timeout'ini sinash).

## Kliring (ADR-0025)

`process_clearing(fayl)` — har yozuv asl avtorizatsiyaga moslanadi: `00 ACCEPTED` (paket ID'si
`cleared_batch` ga), `25` topilmadi, `13` summa farqli, `12` rad etilgan yoki qaytarilgan, `94` boshqa
paketda o'tgan. Natija — tasdiq (ack) fayli. Bir paket ID — bitta natija (`issuer_clearing_batches`,
migratsiya `2004`). Kliringdan o'tgan tranzaksiyaga reversal — `12 ALREADY_CLEARED`. Emulyator
avtorizatsiyada yechadi, kliring balansni o'zgartirmaydi.

`validate_request(&IsoMessage)` — `0100` ni DB va kalitlarsiz tahlil qiladi (majburiy maydonlar,
Track 2 ↔ maydon 2/14, ICC teglari, PDOL ↔ maydon 4/49); `fuzz/fuzz_targets/issuer_parse.rs` ishlatadi.

## Tranzaksiyalar tarixi (ADR-0030)

`Issuer::token_history(token_id, cursor, limit)` — hamyon uchun: qaydnomadan token bo'yicha, yangilari
birinchi (`ts`, ATC, `auth_id`), kursor `<ts>.<atc>.<auth_id>`. Holat `APPROVED` / `REVERSED` /
`DECLINED`, `cleared` — kliringdan o'tgan. PAN yo'q. Real bankda — emitent API'si (`TODO(spec)`, BK-1).

## Testlar

```bash
cargo test -p mpay-issuer
```

`tests/iso_flow.rs` — to'g'ridan-to'g'ri ISO xabarlar: tasdiq, maydon nomuvofiqliklari, ICC yo'qligi,
noma'lum sxema, noto'g'ri MTI, tasodifiy baytlar (proptest). To'liq oqim — `tests/e2e`.
