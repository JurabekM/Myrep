# ZANJIR — Play Console ma'lumotlari (qoralama)

> 12-faza. Play Console'ga foydalanuvchi kiritadi. ⚠️ Maxfiylik siyosati va "Data safety" javoblari huquqshunos bilan
> tekshirilsin (shaxsga doir ma'lumotlar to'g'risidagi qonun, ma'lumotlar lokalizatsiyasi — `DEPLOY.md`).

## Asosiy

| Maydon | Qiymat |
|---|---|
| Ilova nomi | ZANJIR |
| Paket | `uz.zanjir.app` |
| Standart til | O'zbek (lotin) — `uz`; qo'shimcha: rus — `ru` |
| Turkum | Business (Biznes) |
| Narx | Bepul (reklama yo'q, ilova ichida xarid yo'q) |
| Ikonka | `docs/store/icon-512.png` (512 × 512, `app/tool/gen_icons.py`) |
| Aloqa | operator e-pochtasi (2-darvoza) |
| Maxfiylik siyosati | `https://<domen>/privacy` — matn `docs/PRIVACY.md` |

## Qisqa tavsif (≤ 80 belgi)

- uz: `Elektrolaboratoriya: o'lchovlar, normaga solishtirish, imzolangan protokol, QR.`
- ru: `Электролаборатория: замеры, сверка с нормами, подписанный протокол, QR.`

## To'liq tavsif

**uz:** ZANJIR — elektrolaboratoriyalar va elektriklar uchun oflayn ishlaydigan ilova. Obyektning elektr sxemasi (shchit,
avtomat, UZO, kabel, yerga ulagich), dalada o'lchovlar (izolyatsiya qarshiligi, faza–nol sirtmog'i, UZO, yerga ulash),
normaga avtomatik solishtirish, Ed25519 bilan imzolangan PDF protokol va QR orqali tekshirish sahifasi. Ajratish rejasi
5 ta texnik tadbir bo'yicha **tavsiya** qilinadi; ilova hech qachon ish xavfsiz deb aytmaydi — javobgarlik naryad beruvchi
va ish rahbarida. Ma'lumotlar laboratoriya serveriga shifrlangan kanal orqali sinxronlanadi.

**ru:** ZANJIR — офлайн-приложение для электролабораторий и электриков. Схема объекта, замеры на месте, автоматическая
сверка с нормами, подписанный (Ed25519) PDF-протокол и страница проверки по QR. План отключения по 5 техническим
мероприятиям — только **рекомендация**; ответственность несут выдающий наряд и руководитель работ.

## App content (javoblar)

| Bo'lim | Javob |
|---|---|
| Reklama | Yo'q |
| Kirish (App access) | Ilova kirishsiz (oflayn profil) ishlaydi; server funksiyalari uchun sinov hisobi Play'ga beriladi (operator yaratadi, parol faqat Play Console'da) |
| Kontent reytingi | Utility/Productivity; zo'ravonlik, foydalanuvchi kontenti almashinuvi yo'q |
| Maqsadli auditoriya | 18+ (mutaxassislar); bolalarga mo'ljallanmagan |
| Yangiliklar ilovasi | Yo'q |
| Hukumat ilovasi | Yo'q |
| Moliyaviy xususiyatlar | Yo'q |
| Salomatlik | Yo'q |

## Data safety

| Ma'lumot turi | Yig'iladi | Ulashiladi (uchinchi tomon) | Maqsad | Majburiy |
|---|---|---|---|---|
| Ism (F.I.Sh.) | Ha | Yo'q | Ilova funksiyasi (protokol imzolovchisi), hisob | Ha |
| Telefon raqami | Ha | Yo'q | Hisob (kirish) | Ha (server bilan ishlaganda) |
| Ilovadagi boshqa kontent (obyektlar, o'lchovlar, protokollar) | Ha | Yo'q | Ilova funksiyasi | Ha |
| Joylashuv, kontaktlar, rasmlar, fayllar, moliya, salomatlik, xabarlar | Yo'q | — | — | — |
| Qurilma yoki boshqa ID | Ha (ilova yaratgan qurilma ID si va ochiq kalit — imzo tekshiruvi) | Yo'q | Xavfsizlik, firibgarlikka qarshi | Ha |
| Diagnostika / analitika | Yo'q (tashqi xizmat yo'q) | — | — | — |

- Uzatishda shifrlanadi: **ha** (faqat HTTPS, cleartext taqiqlangan).
- O'chirish so'rovi: laboratoriya administratori xodimni o'chiradi; imzolangan protokollar qonun bo'yicha saqlanadi
  (o'zgartirilmaydi) — siyosatda tushuntiriladi.
- "Uchinchi tomonga ulashish" — yo'q: server laboratoriya operatorining o'zi (O'zbekistonda).

## "What's new" (0.1.0, pilot)

- uz: `Pilot versiya: obyekt sxemasi, o'lchovlar va normaga solishtirish, ajratish rejasi, sinxronlash. Protokol imzolash
  normalar muhandis tomonidan tasdiqlangandan keyin yoqiladi.`
- ru: `Пилотная версия: схема объекта, замеры и сверка с нормами, план отключения, синхронизация. Подписание протоколов
  включится после утверждения норм инженером.`

## Skrinshotlar (foydalanuvchi oladi)

Telefon, 1080 × 1920 yoki yuqori, dark mavzu, kamida 4 ta: obyekt sxemasi, o'lchov kiritish (natija bilan), ajratish
rejasi (ogohlantirish matni ko'rinib turgan holda), protokol (QR). Imzolash ekrani `FLAG_SECURE` — skrinshot olinmaydi
(namuna sifatida PDF ko'rinishi ishlatiladi). Haqiqiy mijoz ma'lumotlari skrinshotda bo'lmasin.
