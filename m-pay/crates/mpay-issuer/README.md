# mpay-issuer

Emitent emulyatori: ISO 8583 `0100` → tekshiruvlar → `0110`. Vault va Shield'ni faqat port
trait'lari (`Detokenizer`, `RiskScorer`) orqali ko'radi.

## Qaror tartibi

1. Format: majburiy maydonlar (2, 3, 4, 7, 11, 14, 22, 35, 37, 41, 42, 49, 55), Track 2 ↔ maydon 2/14,
   CID = ARQC, CDOL (`9F02`, `5F2A`) ↔ maydon 4/49.
2. `Detokenizer::lookup(DPAN, LUK seq)` — noma'lum token `05`.
3. LUK noma'lum / muddati o'tgan / limiti tugagan — `Q1`.
4. ARQC: `IMK → MK_tok → LUK → SK`, constant-time — `Q1` (ARPC berilmaydi).
5. Token holati ≠ ACTIVE — `05`; `Detokenizer::consume` (ATC replay — `Q1`, ARPC berilmaydi).
6. FPAN BIN `offline_bins` da — `91`.
7. Shield: DECLINE — `59`; REVIEW — `review_action` (standart: tasdiq).
8. Hisob (PAN barmoq izi bo'yicha) yo'q — `05`; qoldiq yetarli emas — `51` (atomar `UPDATE … WHERE balance >= amount`).
9. Aks holda `00`.

ARQC to'g'ri bo'lsa javobda `55`: `91` = ARPC ‖ ARC, `8A` = ARC. Har avtorizatsiya
`issuer_authorizations` jadvaliga (maskalangan DPAN, sabab, skor) yoziladi; PAN saqlanmaydi.

## Konfiguratsiya (`[issuer]`)

```toml
[issuer]
offline_bins = ["990013"]
review_action = "approve"   # yoki "decline" (05)

[[issuer.accounts]]
pan = "9900121000010014"
balance_minor = 500000000   # tiyin
label = "GREEN, 5 000 000 UZS"
```

## Testlar

```bash
cargo test -p mpay-issuer
```

`tests/iso_flow.rs` — to'g'ridan-to'g'ri ISO xabarlar: tasdiq, maydon nomuvofiqliklari, ICC yo'qligi,
noma'lum sxema, noto'g'ri MTI, tasodifiy baytlar (proptest). To'liq oqim — `tests/e2e`.
