# ADR-0030: Mijoz hamyoni API'si — kartalar, o'zim boshqarish, tarix

* Holat: qabul qilingan (2026-10-29, product hamyon ilovasi 1-bosqichi).
* Bog'liq: ADR-0006 (PQ Link HTTP), ADR-0013 (qurilma ro'yxati), ADR-0024 (reversal), ADR-0025 (kliring).

## Kontekst

Hozirgi qurilma API'si faqat provisioning, OTP, LUK to'ldirish va muddat yangilashni beradi. Product
darajadagi mijoz hamyoni (Android) uchun yana uchta narsa kerak:

* **kartalar ro'yxati** — ilova qayta o'rnatilsa yoki holat bank tomonida o'zgarsa (bank to'xtatdi,
  o'chirdi), ilova serverdagi haqiqiy holatni ko'rsin;
* **kartani o'zim boshqarish** — telefon yo'qolsa yoki shubha bo'lsa, foydalanuvchi bank call-markaziga
  qo'ng'iroq qilmasdan kartani to'xtatadi, qayta yoqadi yoki o'chiradi;
* **tranzaksiyalar tarixi** — har bir karta bo'yicha to'lovlar, rad etilganlar va qaytarilganlar.

Hozir to'xtatish/yoqish faqat operator API'sida (`/v1/tokens/{id}/suspend|resume`, Bearer + mTLS).

## Qaror

### 1. Muhrlangan endpointlar

Hammasi PQ Link muhrlangan (`POST`, tana — muhrlangan JSON), qurilma identifikatori sessiyadan olinadi:

| Yo'l | So'rov | Javob |
|---|---|---|
| `/v1/wallet/tokens` | `{}` | `{tokens: [WalletTokenDto]}` — shu qurilmaning o'chirilmagan kartalari |
| `/v1/wallet/tokens/{id}/suspend` | `{}` | `WalletTokenDto` |
| `/v1/wallet/tokens/{id}/resume` | `{}` | `WalletTokenDto` |
| `/v1/wallet/tokens/{id}/delete` | `{}` | `WalletTokenDto` (qaytarib bo'lmaydi) |
| `/v1/wallet/tokens/{id}/transactions` | `{cursor?, limit?}` | `{transactions: [TxnDto], next_cursor?}` |

`WalletTokenDto` — faqat maskalangan DPAN va FPAN, muddat, holat, `suspended_by`. Ochiq PAN, LUK va
qurilma ID'si yo'q (operator ko'rinishidan farqli).

### 2. Egalik

Har endpoint avval token shu qurilmaga tegishli ekanini tekshiradi (`DEVICE_MISMATCH` 403). Begona
qurilma ro'yxatda boshqa kartalarni ko'rmaydi, ularni boshqara olmaydi va tarixini o'qiy olmaydi.

### 3. Kim to'xtatgan

`vault_tokens.suspended_by` (`DEVICE` yoki `BANK`, migratsiya 1004). Qoidalar:

* foydalanuvchi o'zi to'xtatgan kartani o'zi qayta yoqadi;
* bank (operator) to'xtatganini ilova yoqa olmaydi — `SUSPENDED_BY_BANK` (403); aks holda firibgarlik
  sababli bloklangan kartani o'g'irlangan telefon egasi qayta yoqib olardi;
* tekshiruv o'tish bilan bitta tranzaksiyada, qator qulfi ostida — bank bilan poyga yo'q;
* operator har qanday holatni o'zgartira oladi (bank ustun).

Audit aktori — `device:<qurilma ID'sining 16 hex>`; harakatlar operator bilan bir xil
(`TOKEN_SUSPENDED`, `TOKEN_RESUMED`, `TOKEN_DELETED`).

### 4. Tarix

Manba — emitent qaydnomasi (`issuer_authorizations`), token bo'yicha. Holat foydalanuvchi uchun
soddalashtirilgan:

* `APPROVED` — `00` va qaytarilmagan;
* `REVERSED` — `00`, keyin reversal (ADR-0024);
* `DECLINED` — boshqa har qanday kod (`response_code` va `reason` ham beriladi).

`cleared` — kliringdan o'tgan (ADR-0025).

Tartib — yangilari birinchi: `ts`, bir soniya ichida karta ATC'si (har tap'da o'sadi), so'ng
`auth_id`. Kursor — `<ts>.<atc>.<auth_id>`: ochiq ma'lumot, sir emas; qat'iy tahlil qilinadi
(noto'g'risi — `BAD_REQUEST`). `limit` 1–100, standart 20. Sahifalar orasida yozuv tushib qolmaydi
va takrorlanmaydi (e2e testi bir soniyadagi 5 yozuvni 2 tadan o'qiydi).

## Oqibatlar

* Hamyon ilovasi serverdagi haqiqiy holatni ko'rsatadi va karta yo'qolganda darhol to'xtatadi.
* Bank bloklagan kartani ilova chetlab o'tolmaydi.
* Tarix emitent emulyatoridan — real bankda emitentning o'z API'sidan bo'ladi (`TODO(spec)`,
  checklist BK-1).
* Ro'yxat tartibi `created_at` (bir soniyada — token ID); ilovadagi ko'rinish tartibi va asosiy
  karta — ilovaning o'z sozlamasi.

## Ko'rib chiqilgan muqobillar

* **Operator endpointlarini qurilmaga ochish** — rad: rollar aralashadi, bank blokini chetlab o'tish
  mumkin bo'lardi.
* **Offset bilan sahifalash** — rad: yangi tranzaksiya kelganda sahifalar siljiydi (takror yoki tushib
  qolish).
* **Faqat `ts` + `auth_id` bilan tartib** — rad: `auth_id` tasodifiy, bir soniyadagi tranzaksiyalar
  aralash tartibda chiqardi (birinchi yugurishda e2e testi shuni ko'rsatdi).
* **Tarixni ilovada lokal saqlash (faqat qurilmadagi taplar)** — rad: qayta o'rnatishda yo'qoladi,
  bank tomonidagi rad sababi va reversal ko'rinmaydi.
