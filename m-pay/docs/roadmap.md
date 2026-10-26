# M-Pay yo'l xaritasi

Sana: 2026-10-24. 0-faza boshlang'ich topshiriqda belgilangan; 1–4-fazalar 0-faza yakunidagi ochiq
ishlar (`TODO(spec):`, ADR'lar, hisobotlar) asosida taklif qilingan va 2026-10-24 da qabul qilingan.
Har faza tugaganda `docs/PROGRESS.md` ga hisobot yoziladi.

| Faza | Nomi | Holat | Kimga bog'liq |
|---|---|---|---|
| 0 | Pay Sandbox | ✅ tayyor (M0–M7) | — |
| 1 | Xavfsizlikni kuchaytirish | ✅ (P1.8 radio — qurilmalar kerak) | jamoa (tashqi ma'lumot kerak emas) |
| 2 | Pilot tayyorgarligi | ishda (virtual muhitda) | pilot bank: TPS/SLA, HSM modeli, infratuzilma |
| 3 | Pilot | reja | bank, mustaqil auditor |
| 4 | Sertifikatsiya va production | reja | to'lov sxemasi, regulyator, yuristlar |

## 0-faza — Pay Sandbox ✅

Haqiqiy pulsiz, to'liq ishlaydigan demo: PQ Link (X25519+ML-KEM-768, Ed25519+ML-DSA-65) orqali
tokenizatsiya, Vault (envelope shifrlash, xesh-zanjirli audit), EMV-ga o'xshash tap-to-pay (LUK,
ARQC/ARPC, CDCVM), Shield (qoidalar + ONNX), emitent emulyatori (ISO 8583), Android SDK va ikki ilova,
fuzz kampaniyasi, yuk sinovi, 10 daqiqalik bank namoyishi. Batafsil: `docs/PROGRESS.md`.

**Ochiq qolgan**: ikki haqiqiy telefon orasida NFC tap (M6 qabul mezoni) — 1-fazaga ko'chirildi.

## 1-faza — Xavfsizlikni kuchaytirish

Maqsad: tashqi qarorlarsiz yopiladigan xavfsizlik bo'shliqlarini yopish.

| # | Ish | Manba |
|---|---|---|
| P1.1 ✅ | Rate-limit: PQ Link handshake (IP bo'yicha) va API kalitlari bo'yicha so'rovlar | tahdid modeli D2 |
| P1.2 ✅ | Takroriy STAN/RRN ni acquirer darajasida rad etish (terminal + STAN + sana oynasi) | PROGRESS M4 |
| P1.3 ✅ | Ichki API uchun mTLS (operator va terminal mijoz sertifikatlari, sandbox CA) | `architecture.md` |
| P1.4 ✅ | `terminal-app`: TLS (sandbox CA joylangan) + server pinlash, terminal kaliti Keystore'da shifrlangan | M6 ochiq bandi |
| P1.5 ✅ | Hamyon: server barmoq izi build vaqtida joylanadi (TOFU faqat sandbox opsiyasi); bir nechta pinlangan identifikator | ADR-0008 |
| P1.6 ✅ | PQ Link server kalitini almashtirish (rotation): yangi identifikatorni e'lon qilish, o'tish davri | `specs/pqlink.md` |
| P1.7 ✅ | Attestatsiya challenge'ini qurilmani ro'yxatdan o'tkazish (enrollment nonce) bilan bog'lash | `specs/pqlink.md` |
| P1.8 ◐ | Ikki telefon orasida haqiqiy NFC tap (`docs/android-testing.md` §3). Emulyatorda virtual NFC bilan to'liq tap ✅ (§5); haqiqiy radio — qurilmalar kerak | M6 qabul mezoni |

Qo'shimcha (2026-10-25, bajarildi): ishonchli proksilar, mTLS sertifikatini bekor qilish, bekor qilingan
server identifikatorlari (ADR-0014), davriy qayta attestatsiya (ADR-0015).

Qabul mezoni: har band testlar bilan, tahdid modeli yangilangan, `scripts/demo.sh` va smoke CI'da yashil.
P1.8 qurilmalar mavjud bo'lganda bajariladi.

## 2-faza — Pilot tayyorgarligi (virtual muhitda)

Pilot bank hali tanlanmagan — 2-faza **virtual muhitda** sinaladi (2026-10-25 qarorlari):

* **SLA maqsadi (faraz):** 200 TPS, p99 < 300 ms. `TODO(spec):` pilot bank bilan tasdiqlash.
* **Umumiy ombor:** PostgreSQL (sessiyalar va nonce'lar ham — KEK bilan shifrlangan); Redis yo'q.
* **Tartib:** avval OTP kanali va HSM, keyin PostgreSQL va ko'p instansiya.

| # | Ish | Virtual o'rinbosar | Holat |
|---|---|---|---|
| P2.1 | OTP kanali: emitentdagi telefon raqamiga SMS | virtual SMS shlyuzi (webhook) | ✅ (ADR-0016) |
| P2.2 | HSM bilan yuk sinovi (KDF/CMAC HSM ichida) | SoftHSM2 (Docker) | ✅ (ADR-0017) |
| P2.3 | PostgreSQL + avtorizatsiya bitta tranzaksiyada (TPS'ni qaytarish) | PostgreSQL (Docker) | ✅ (ADR-0018; HSM bilan 368 /s, p99 118 ms) |
| P2.4 | Ko'p instansiya: sessiyalar, nonce'lar, Shield ombori umumiy | 2 server + PostgreSQL + Shield roli | ✅ (ADR-0019) |
| P2.5 | Deployment: docker-compose, monitoring, zaxira nusxa | Docker Desktop | ✅ (ADR-0020; nginx orqali 332 /s, p99 164 ms, API to'xtatilganda xato 0) |
| P2.6 | Play Integrity | mock tekshiruvchi | reja |
| P2.7 | Mahsulot siyosatlari: REVIEW, CVM, token muddati, karta–qurilma | konfiguratsiya | reja |

## 3-faza — Pilot

* Bitta bank bilan cheklangan ishga tushirish (yopiq foydalanuvchilar guruhi).
* Shield'ni real ma'lumotda qayta o'qitish, chegaralarni kalibrlash, MCC va geo belgilar.
* Mustaqil pentest va kriptografik audit (PQ Link, kalit ierarxiyasi).
* HTTP API fuzzing, Kotlin uchun Jazzer.

## 4-faza — Sertifikatsiya va production

* Haqiqiy to'lov sxemasi (Humo / Uzcard / xalqaro): spetsifikatsiya, test kartalar, EMV/HCE sertifikatsiyasi;
  IAD formati va ARPC usulini qayta ko'rib chiqish.
* PCI DSS (token ombori), Markaziy bank talablari (litsenziya, ma'lumotlarni mahalliy saqlash).
* To'liq ishga tushirish va qo'llab-quvvatlash jarayonlari.
