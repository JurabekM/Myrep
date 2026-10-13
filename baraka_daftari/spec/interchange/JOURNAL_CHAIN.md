# Kelishuv jurnali: xesh-zanjir (mobil va desktop uchun)

Bu hujjat SPEC 2F.6, D8A va D14 bo'yicha. Mobil ilova xuddi shu xeshlarni chiqarishi shart. Desktop
implementatsiyasi (`crates/domain/src/journal.rs`) shu qoidalar bilan test vektorlari orqali qotirilgan:
`spec/test-vectors/journal_chain.json` (chain-001…006, canonical-001…002).

## 1. Yozuv maydonlari

Xeshga kiradigan maydonlar (yozuv JSON'iga faqat mavjud bo'lsa qo'shiladi; yo'q bo'lsa kalit yo'q):

| Kalit | Majburiy | Qoida |
|---|---|---|
| `id` | ha | Yozuv identifikatori (UUID). |
| `agreementId` | ha | Kelishuv identifikatori. |
| `kind` | ha | Yozuv turi: `OPENING_BALANCE`, `CONTRIBUTION`, `VENTURE_INCOME`, `VENTURE_EXPENSE`, `PROFIT_DISTRIBUTION`, `LOSS_SHARE`, `BUYOUT_PAYMENT`, `PAYMENT`, `PERIOD_CLOSED`, `CORRECTION`, `DUTY_INCIDENT`, `DISPUTE_OPENED`, `DISPUTE_RESOLVED`, `PROFIT_ALERT_ACK`, `REVIEW_ACK`, `REVIEW_CLOSED`. |
| `date` | ha | `YYYY-MM-DD`. |
| `note` | ha | 1…300 belgi. Ichki bo'shliqlar bitta bo'shliqqa keltiriladi (qo'shishda). |
| `partyId` | yo'q | Tomon identifikatori. |
| `amount` | yo'q | `{ "minor": "<butun son, satr>", "currency": "UZS" \| "USD" \| "EUR" \| "RUB" }`. |
| `ref` | yo'q | Manba yozuv yoki davr (masalan, `2026-10` ko'rigi, venture yozuvi identifikatori). |
| `corrects` | yo'q | Tuzatilayotgan asl yozuv identifikatori; faqat `CORRECTION` da. |

Xeshga **kirmaydi**: `seq` (tartib zanjirning o'zidan kelib chiqadi), `prev_hash`, `hash`, `household_id`,
`created_at`, `updated_at`, `version`, `origin_device_id`, `deleted_at`.

## 2. Kanonik JSON (RFC 8785, JCS)

- Kalitlar UTF-16 kod birliklari bo'yicha saralanadi.
- **Sonlar taqiqlangan.** Barcha pul va son qiymatlari satr sifatida yoziladi (`"minor": "1500000"`).
- Satrlarda `"` va `\` escape qilinadi; boshqaruv belgilari `\u00xx` ko'rinishida. Boshqa belgilar
  (o'zbekcha `ʻ`, `’`, kirill harflari) UTF-8 da to'g'ridan-to'g'ri yoziladi.
- Ortiqcha bo'shliq yo'q.

Misol (kalitlar tartibi muhim): `{"agreementId":"a1","date":"2026-10-12","id":"j1","kind":"VENTURE_INCOME","note":"Buyurtma 1"}`

## 3. Xesh zanjiri

- `link_hash(prev, canonical) = hex_kichik_harf(SHA256(prev + "\n" + canonical))`.
- `prev` — oldingi yozuvning xeshi (64 belgi, kichik harf). Birinchi yozuv uchun **genesis**: 64 ta `0`.
- `hash_n = link_hash(hash_(n-1), canonical(yozuv_n))`.
- Har bir kelishuvning o'z zanjiri bor; `seq` 1 dan boshlanadi va bo'shliqsiz ketma-ket bo'ladi.

## 4. Zanjir boshi (`chainHead`)

Oxirgi yozuvning xeshi. Zanjir bo'sh bo'lsa — genesis. Ko'rik yakunlanganda (`REVIEW_CLOSED`) zanjir boshi
yozuvning `ref` maydoniga `davr|boshi` ko'rinishida qayd etiladi. Bayonnomada shu qiymat chop etiladi.
Keyin biror eski yozuv o'zgarsa, qayta hisoblangan boshi qayd etilgan qiymatga mos kelmaydi — bu o'zgarishning
dalilidir.

## 5. Import qoidalari (D14)

1. Kelgan qatorlar tartib raqamlari bo'yicha ketma-ket bo'lishi shart. Har bir xesh qayta hisoblanadi.
   Biror xesh mos kelmasa — **import rad etiladi**, hech narsa yozilmaydi (xato).
2. Kelgan zanjir mahalliy zanjirga ulanishi shart: birinchi kelgan yozuvning `prev` qiymati mahalliy
   `seq-1` yozuvining xeshiga teng (`seq = 1` bo'lsa genesis). Umumiy tartib raqamlaridagi xeshlar bir xil
   bo'lishi kerak.
3. Ulanmasa (uzilish) yoki umumiy tartibda xesh farq qilsa (**fork**): hech narsa yozilmaydi, hisobotda
   `JOURNAL` ziddiyati ko'rsatiladi. Zanjirlar **hech qachon avtomatik birlashtirilmaydi**.
4. Faqat kelishuvning hisob yurituvchi qurilmasi (`custody.keeper_device_id`) yozuv qo'shadi. Boshqa
   qurilmada jurnal faqat o'qish uchun.
5. Hisob yurituvchini almashtirish faqat kelishuvning yangi versiyasi orqali (SPEC 2F.6).

## 6. Test vektorlari

- `spec/test-vectors/journal_chain.json`:
  - `chain-001…004` — yozuv turlari va zanjir boshi;
  - `chain-005` — to'g'ri zanjir (tekshiruv o'tadi);
  - `chain-006` — o'zgartirilgan zanjir: birinchi buzilgan yozuv raqami `2`;
  - `canonical-001…002` — kanonik satr (tartib, escape, o'zbekcha belgilar).
- Mobil ilova shu vektorlarni o'z testlarida o'qib, xeshlarni solishtirishi kerak.

## 7. Mobil tomon tekshiruv ro'yxati

- [ ] Barcha vektorlar yashil.
- [ ] Yangi yozuv `prev` ni oldingi `hash` dan oladi; birinchisi genesis.
- [ ] Son qiymatlari kanonik satrga faqat satr sifatida kiradi.
- [ ] Import: buzilgan yoki ayrilib ketgan zanjir bo'lsa hech narsa yozilmaydi, foydalanuvchiga hisobot chiqadi.
