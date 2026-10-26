# mpay-integrity

Ilova va qurilma yaxlitligi — Google Play Integrity tokenini server tomonida tekshirish
(2-faza P2.6, [ADR-0021](../../docs/adr/0021-play-integrity.md)).

## Tarkib

| Modul | Vazifa |
|---|---|
| `lib.rs` | `request_hash` (PQ Link sessiyasiga bog'lanish), verdict tuzilmasi (`TokenPayload`), `check` (paket, imzo sertifikati, `requestHash`, yangilik → `IntegritySignals`), `IntegrityVerifier` trait, `Integrity` (verifier + siyosat + `required`) |
| `mock.rs` | Sandbox: ES256 kompakt JWS, mazmuni Play Integrity verdict tuzilmasida; `MockIssuer` (sinov stsenariylari — `Preset`), `MockVerifier` |
| `google.rs` | `decodeIntegrityToken` mijozi (`POST /v1/{paket}:decodeIntegrityToken`, Bearer OAuth2 token tashqaridan) |

## Qoidalar

* `requestHash = base64url(SHA-256("MPAY-PI-V1" ‖ 0x00 ‖ amal ‖ 0x00 ‖ sessiya ID))` — PAN **kirmaydi**
  (u Google serverlariga ketadi, PAN esa xeshdan ham tiklanadi). Kotlin: `uz.mpay.core.Integrity`, umumiy
  test vektori ikkala tilda.
* Bog'lanish buzilsa (begona imzo, boshqa paket yoki sertifikat, boshqa sessiya, eskirgan/kelajakdagi
  vaqt) — xato, so'rov rad etiladi. Verdict sifati (`app`, `device`, `licensed`, `env_risk`) — faqat
  belgilar, qaror Shield qoidalarida (`IDV_INTEGRITY_*`).
* Mock'da algoritm qat'iy `ES256` va `kid` — `alg: none` yoki boshqa kalit o'tmaydi.
* Token va verdict JSON'i logga yozilmaydi; `Integrity` ning `Debug` i faqat verifier nomi va paketni ko'rsatadi.

## Cheklovlar

* `TODO(spec):` Google xizmat akkaunti → OAuth2 access token oqimi yo'q (token fayl/muhitdan); haqiqiy
  Google bilan sinalmagan — testlar protokol shaklidagi emulyatorga qarshi. Verdict maydonlari Google'ning
  ochiq hujjatiga muvofiq yozilgan, integratsiyada joriy hujjat bilan qayta solishtirish kerak.
* Klassik so'rov (`nonce`) qo'llab-quvvatlanmaydi — faqat standart so'rov (`requestHash`).

## Testlar

```bash
cargo test -p mpay-integrity
```

e2e: `tests/e2e/tests/p2_integrity.rs` (majburiy token, sessiyaga bog'lanish, buzilgan/begona/eskirgan
tokenlar, verdict → Shield qarori, sandbox endpoint, konfiguratsiya himoyalari).
