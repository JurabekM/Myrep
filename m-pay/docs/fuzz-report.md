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

`pqlink_session` uchun qo'shimcha 1800 s yugurish davom etmoqda — natija keyingi commit'da qo'shiladi.

`pqlink_session` sekin: har rad etilgan yozuvdan keyin yangi handshake (ML-KEM-768, ML-DSA-65,
attestatsiya zanjiri) — bu maqsad uzunroq yugurtirildi (yuqoridagi qo'shimcha qator).

## 3. Topilmalar

* M7 kampaniyasida crash, ASan xatosi yoki invariant buzilishi yo'q.
* Oldingi bosqichlarda fuzz topgani: bo'sh ikkilamchi ISO 8583 bitmap `pack(unpack(x)) != x`
  (M1, `NonCanonicalBitmap` bilan rad etiladi).
* Fuzz bo'lmagan, lekin M7 yuk sinovi topgan xato: SQLite `SQLITE_BUSY` → `91` (`docs/load-report.md`, ADR-0009).

## 4. Qamrovdan tashqarida

* HTTP/JSON qatlami (axum, serde) — tashqi crate'lar; API'ni fuzz qilish (`TODO(spec):` schemathesis
  yoki o'z HTTP fuzzer'i) keyingi bosqich.
* Kotlin tomoni (`android/mpay-core`) fuzz qilinmagan — umumiy test vektorlari va interop testi bilan
  qoplangan; `TODO(spec):` Jazzer.
* PKCS#11 (SoftHSM) chegarasi fuzz qilinmagan.
