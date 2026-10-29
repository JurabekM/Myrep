# Fuzz kampaniyasi hisoboti (M7)

Sana: 2026-10-24. Qayta yugurish: `bash scripts/fuzz-campaign.sh [soniya] [maqsad ...]`
(nightly + `cargo-fuzz`, libFuzzer + AddressSanitizer). CI: har push'da har maqsad 60 s (`mpay-ci.yml`,
`fuzz` job'i; branch hali push qilinmagani uchun CI'da yugurtirilmagan).

## 1. Maqsadlar va invariantlar

| Maqsad | Hujum yuzasi | Invariant (panic'dan tashqari) |
|---|---|---|
| `tlv_parse` | BER-TLV, DOL (`mpay-common`) | qayta kodlash → qayta o'qish = o'sha daraxt |
| `iso8583_unpack` | ISO 8583 (bitmap, LLVAR) | `pack(unpack(x)) == x` (kanonik format) |
| `emv_parse` | PDOL ma'lumoti, Track 2 (EMV/ISO), IAD | PDOL roundtrip |
| `pqlink_decode` | PQ Link xabarlari, KeyDescription (ASN.1) | encode/decode roundtrip |
| `apdu_card` **(yangi)** | soft-karta applet'i: ixtiyoriy C-APDU ketma-ketligi | javob ≥ 2 bayt; ATC kamaymaydi; `9000` GPO → bitta `77` shablon; GPO soni ≤ LUK limiti; CDCVM'siz > 1 000 000 so'm o'tmaydi |
| `issuer_parse` **(yangi)** | emitent `0100` tahlilchisi (Track 2, maydon 55 ICC, PDOL ↔ 4/49) | ixtiyoriy bayt / almashtirilgan maydon 55 / bit-flip; buzilmagan haqiqiy xabar doim o'tadi |
| `pqlink_session` **(yangi)** | o'rnatilgan PQ Link sessiyasi: yozuvga bit-flip, kesish, qo'shish | server faqat aynan o'zgarmagan yozuvni qabul qiladi, ochilgan matn = asl; buzilmagan yozuv rad etilmaydi |

Yangi maqsadlar uchun boshlang'ich kirishlar `fuzz/seeds/` da (haqiqiy SELECT/GPO ketma-ketliklari),
lug'at — `fuzz/emv.dict` (EMV teglari, APDU sarlavhalari, AID, PPSE). `apdu_card` seed'lari GPO `9000`,
CDCVM `6986` va LUK limiti `6985` holatlariga yetishi kuzatuv bilan tekshirildi.

## 2. Natijalar

Mashina: Intel i5-10300H, Windows 10, MSVC ASan; 3 maqsad parallel.

| Maqsad | Vaqt, s | Yugurishlar | exec/s | Qamrov (cov) | Korpus | Natija |
|---|---|---|---|---|---|---|
| `apdu_card` | 300 | 678 614 | 2 254 | 812 | 684 | toza |
| `emv_parse` | 300 | 6 855 864 | 22 776 | 284 | 173 | toza |
| `iso8583_unpack` | 300 | 10 804 505 | 35 895 | 258 | 150 | toza |
| `issuer_parse` | 300 | 1 266 922 | 4 209 | 1 639 | 692 | toza |
| `pqlink_decode` | 300 | 2 202 326 | 7 316 | 484 | 653 | toza |
| `pqlink_session` | 300 | 8 440 | 28 | 5 644 | 178 | toza |
| `tlv_parse` | 300 | 2 300 937 | 7 644 | 262 | 844 | toza |
| **Jami** | | **≈ 24,1 mln** | | | | **crash yo'q** |

Qo'shimcha uzun yugurish (alohida, 1 maqsad):

| Maqsad | Vaqt, s | Yugurishlar | exec/s | Qamrov (cov) | Korpus | Natija |
|---|---|---|---|---|---|---|
| `pqlink_session` | 1 800 | 81 291 | 45 | 5 649 | 296 | toza |

`pqlink_session` sekin: har rad etilgan yozuvdan keyin yangi handshake (ML-KEM-768, ML-DSA-65,
attestatsiya zanjiri) — bu maqsad uzunroq yugurtirildi (yuqoridagi qo'shimcha qator).

## 3. Topilmalar

* M7 kampaniyasida crash, ASan xatosi yoki invariant buzilishi yo'q.
* Oldingi bosqichlarda fuzz topgani: bo'sh ikkilamchi ISO 8583 bitmap `pack(unpack(x)) != x`
  (M1, `NonCanonicalBitmap` bilan rad etiladi).
* Fuzz bo'lmagan, lekin M7 yuk sinovi topgan xato: SQLite `SQLITE_BUSY` → `91` (`docs/load-report.md`, ADR-0009).

## 4. Qamrovdan tashqarida

* ~~HTTP/JSON qatlami~~ — §5 (`http_api`, 2026-10-26).
* ~~Kotlin tomoni~~ — §5 (Jazzer, 2026-10-26).
* PKCS#11 (SoftHSM) chegarasi fuzz qilinmagan.

## 5. HTTP API va Kotlin (Jazzer) — 2026-10-26 (3-faza tayyorgarligi)

**`http_api` (cargo-fuzz).** `mpay-server` router'i jarayon ichida, tarmoqsiz (`tests/e2e/src/apifuzz.rs`).
Bir kirish → bitta so'rov:

* ochiq rejim: 20 marshrut × metod × API kaliti (yo'q / operator / terminal / soxta) × `Content-Type` × tana;
* muhrlangan rejim: ixtiyoriy tana **haqiqiy PQ Link sessiyasi** bilan muhrlanadi (provisioning, OTP,
  LUK, rekey, sandbox yaxlitlik) — JSON tahlili va handler mantig'i kriptografiya to'sig'idan o'tib sinanadi.

Invariantlar: panic yo'q; `500` yo'q (`502` faqat `/v1/authorizations`, `503` — ataylab); muhrlanmagan
xato — `{"error": {"code"}}`; muhrlangan javob ochiladi va konvert bo'ladi, `INTERNAL`/`DB_ERROR` yo'q.
Lug'at — `fuzz/http_api.dict` (API JSON kalitlari), seed'lar — `fuzz/seeds/http_api/`. Xuddi shu harness
`tests/api_robustness.rs` da proptest bilan har `cargo test` da (Windows ham) va qamrovni tasdiqlovchi
aniq test bilan ishlaydi (muhrlangan provisioning token yaratadi, takror — `CARD_ALREADY_ON_DEVICE`).

| Maqsad | Vaqt, s | Yugurishlar | exec/s | Qamrov (cov) | Korpus | Natija |
|---|---|---|---|---|---|---|
| `http_api` | 300 | 195 957 | 651 | 12 506 | 1 288 | toza |

**Kotlin (Jazzer 0.30, JUnit 5).** `android/mpay-core/src/test/kotlin/uz/mpay/core/FuzzTests.kt`, oddiy
`test` da — regressiya rejimi, `bash scripts/android-fuzz.sh` — haqiqiy fuzzing. Faqat hujjatlashtirilgan
xatolar ushlanadi.

| Test | Hujum yuzasi / invariant | Yugurishlar | exec/s | Natija |
|---|---|---|---|---|
| `tlvRoundtrip` | BER-TLV: tahlil → kodlash → tahlil | 3 335 908 | 54 687 | toza |
| `hexStrict` | `decode → encode` = kirish | 2 286 466 | 73 756 | **topilma** → tuzatildi, toza |
| `appletApduSequence` | HCE applet: ixtiyoriy C-APDU; javob ≥ 2, ATC kamaymaydi, LUK limiti | 13 200 996 | 216 409 | toza |
| `serverHello` | MITM'dan ixtiyoriy ServerHello: faqat `PqLinkException` | 453 007 | 7 426 | toza |
| `recordOpen` | soxta PQ Link yozuvi ochilmaydi | 2 445 379 | 78 883 | toza |
| `revocationsJson` | imzosiz bekor qilish ro'yxati qabul qilinmaydi | 2 134 883 | 68 867 | toza |
| `terminalBundle` | buzilgan terminal paketi: faqat hujjatlashtirilgan xatolar | 2 315 777 | 74 702 | toza |

**Topilma.** Kotlin `Hex.decode` `String.toInt(16)` ishlatardi — u `+`/`-` belgisini qabul qiladi:
`"+9000000"` va `"-1"` hex sifatida o'tardi (`"-1"` → `0xFF`). Ta'siri past (bir xil baytlarga turli
satrlar — kanonik bo'lmagan qabul; barmoq izlari bayt bo'yicha solishtiriladi), lekin qat'iy hex'ga
o'tkazildi. Kirishlar regressiya korpusida (`FuzzTestsInputs/hexStrict/`).

CI: `fuzz` job'i `http_api` ni ham yuguradi (har maqsad 60 s); yangi `kotlin` job'i — `mpay-core`
testlari va Jazzer kampaniyasi.
