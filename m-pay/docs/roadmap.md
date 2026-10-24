# M-Pay yo'l xaritasi

Sana: 2026-10-24. 0-faza boshlang'ich topshiriqda belgilangan; 1–4-fazalar 0-faza yakunidagi ochiq
ishlar (`TODO(spec):`, ADR'lar, hisobotlar) asosida taklif qilingan va 2026-10-24 da qabul qilingan.
Har faza tugaganda `docs/PROGRESS.md` ga hisobot yoziladi.

| Faza | Nomi | Holat | Kimga bog'liq |
|---|---|---|---|
| 0 | Pay Sandbox | ✅ tayyor (M0–M7) | — |
| 1 | Xavfsizlikni kuchaytirish | ishda | jamoa (tashqi ma'lumot kerak emas) |
| 2 | Pilot tayyorgarligi | reja | pilot bank: TPS/SLA, HSM modeli, infratuzilma |
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
| P1.3 | Ichki API uchun mTLS (operator va terminal mijoz sertifikatlari, sandbox CA) | `architecture.md` |
| P1.4 | `terminal-app`: TLS (sandbox CA joylangan) + server pinlash, terminal kaliti Keystore'da shifrlangan | M6 ochiq bandi |
| P1.5 | Hamyon: server barmoq izi build vaqtida joylanadi (TOFU faqat sandbox opsiyasi); bir nechta pinlangan identifikator | ADR-0008 |
| P1.6 | PQ Link server kalitini almashtirish (rotation): yangi identifikatorni e'lon qilish, o'tish davri | `specs/pqlink.md` |
| P1.7 | Attestatsiya challenge'ini qurilmani ro'yxatdan o'tkazish (enrollment nonce) bilan bog'lash | `specs/pqlink.md` |
| P1.8 | Ikki telefon orasida haqiqiy NFC tap (`docs/android-testing.md` §3) | M6 qabul mezoni |

Qabul mezoni: har band testlar bilan, tahdid modeli yangilangan, `scripts/demo.sh` va smoke CI'da yashil.
P1.8 qurilmalar mavjud bo'lganda bajariladi.

## 2-faza — Pilot tayyorgarligi

* PostgreSQL va migratsiya strategiyasi; avtorizatsiya yozuvlarini bitta tranzaksiyada birlashtirish (ADR-0009).
* Ko'p instansiya: PQ Link sessiyalari, Shield belgilar ombori va qurilma grafi uchun umumiy saqlash.
* Haqiqiy HSM (to'lov HSM'i): KDF/CMAC HSM ichida (`CKM_*_DERIVE`), HSM bilan yuk sinovi.
* OTP kanali (SMS / push / bank ilovasi).
* Play Integrity: Google Cloud loyihasi va server tomonida token tekshiruvi.
* Deployment: konteyner, monitoring va ogohlantirishlar, zaxira nusxa, DR, kalit marosimi tartibi.
* Mahsulot siyosatlari: REVIEW standarti, emitent CVM siyosati, token muddati, karta–qurilma cheklovi.

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
