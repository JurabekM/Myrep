# mpay-common

M-Pay modullari uchun umumiy tiplar. Kriptografiyaga bog'liq emas.

| Modul | Vazifasi |
|---|---|
| `pan` | `Pan` — faqat test BIN (`990000`–`990099`), Luhn, 16 raqam; `Debug`/`Display` faqat maskalangan (`990012******3456`); `Drop` da tozalanadi. `CardExpiry` (YYMM). |
| `tlv` | BER-TLV parser/encoder: 1–4 baytli teglar, uzun uzunliklar (`0x81`–`0x84`), konstruktiv obyektlar (chuqurlik ≤ 16), `0x00` to'ldiruvchi, DOL. `Debug` qiymatlarni chiqarmaydi. |
| `iso8583` | ISO 8583 subset: MTI (`0100`/`0110`, reversal `0400`/`0401`/`0410`), ikkilik bitmap (ikkilamchi bilan), maydonlar 2, 3, 4, 7, 11, 14, 22, 35, 37, 39, 41, 42, 49, 55, 90. Qat'iy unpack (ortiqcha bayt, noma'lum maydon, kanonik bo'lmagan bitmap — xato). |
| `emv` | M-Pay Test Scheme: AID, PPSE, teglar, PDOL (29 bayt), CDOL (41 bayt), IAD (8 bayt), Track 2 (EMV `57` va ISO maydon 35), BCD. |
| `ports` | `IdvDecider`, `RiskScorer`, `Detokenizer` trait'lari va DTO'lar (ADR-0002). |
| `ids` | `TokenId` (`tok_` + 32 hex), `DeviceId`, `PanFingerprint`. |
| `clock` | `Clock` trait, `SystemClock`, testlar uchun `ManualClock`. |
| `config` | TOML yuklovchi, `LukPolicy` (standart: 10 foydalanish, 24 soat, 5 ta LUK). |

Kliring (`clearing`, ADR-0025): M-Pay Test Scheme kliring fayli (`H`/`D`/`S`/`T`, qat'iy uzunlikli
qatorlar, nazorat yig'indilari, SHA-256) va emitent tasdig'i (`A`/`R`/`Z`); faqat maskalangan DPAN,
qat'iy tahlil.

## Testlar

```bash
cargo test -p mpay-common
```

Proptest: TLV va ISO 8583 roundtrip, ixtiyoriy baytlarda panic yo'qligi, Luhn bitta raqam
xatosini aniqlashi. Fuzz (nightly, `m-pay/fuzz`):

```bash
cargo +nightly fuzz run tlv_parse -- -max_total_time=60
```

Windows'da avval MSVC ASan DLL papkasini `PATH` ga qo'shing (`clang_rt.asan_dynamic-x86_64.dll`).
