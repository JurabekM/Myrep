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
normaga avtomatik solishtirish, Ed25519 bilan imzolangan PDF protokol va QR orqali ilova ichida tekshirish. Ajratish rejasi
5 ta texnik tadbir bo'yicha **tavsiya** qilinadi; ilova hech qachon ish xavfsiz deb aytmaydi — javobgarlik naryad beruvchi
va ish rahbarida. Ilova to'liq oflayn — internetsiz ishlaydi; xodimlar o'rtasida ma'lumot imzolangan va shifrlangan fayl
orqali almashiladi, telefon yo'qolishidan — parolli zaxira.

**ru:** ZANJIR — офлайн-приложение для электролабораторий и электриков. Схема объекта, замеры на месте, автоматическая
сверка с нормами, подписанный (Ed25519) PDF-протокол и проверка по QR в приложении. План отключения по 5 техническим
мероприятиям — только **рекомендация**; ответственность несут выдающий наряд и руководитель работ. Работает полностью
без интернета; обмен между сотрудниками — подписанным зашифрованным файлом, резервная копия — с паролем.

## App content (javoblar)

| Bo'lim | Javob |
|---|---|
| Reklama | Yo'q |
| Kirish (App access) | Hisob va kirish yo'q — barcha funksiyalar oflayn profil bilan ochiq (sinov hisobi kerak emas) |
| Kontent reytingi | Utility/Productivity; zo'ravonlik, foydalanuvchi kontenti almashinuvi yo'q |
| Maqsadli auditoriya | 18+ (mutaxassislar); bolalarga mo'ljallanmagan |
| Yangiliklar ilovasi | Yo'q |
| Hukumat ilovasi | Yo'q |
| Moliyaviy xususiyatlar | Yo'q |
| Salomatlik | Yo'q |

## Data safety

Ilovada `INTERNET` ruxsati yo'q (release AAB tekshiruvi talab qiladi, ADR-0017): hech qanday ma'lumot qurilmadan
dastur tomonidan uzatilmaydi. Google ta'rifi bo'yicha "yig'ish" — qurilmadan tashqariga uzatish; qurilmadagi qayta
ishlash va foydalanuvchi o'zi tanlagan ilova orqali yuborgan fayl (zaxira, almashish fayli — tizim fayl oynasi) yig'ish
hisoblanmaydi.

| Savol | Javob |
|---|---|
| Ilova foydalanuvchi ma'lumotini yig'adimi yoki ulashadimi? | **Yo'q** |
| Uzatishda shifrlanadimi? | Qo'llanmaydi (uzatish yo'q); foydalanuvchi yaratgan fayllar shifrlangan (ChaCha20-Poly1305) |
| O'chirish so'rovi | Ma'lumot faqat telefonda: ilova ma'lumotini tozalash yoki o'chirish; imzolangan protokollar laboratoriya tartibi bo'yicha saqlanadi |

⚠️ Javoblar huquqshunos bilan va Play'ning amaldagi yo'riqnomasi bo'yicha qayta tekshiriladi (release checklist).

## "What's new" (0.1.0, pilot)

- uz: `Pilot versiya: obyekt sxemasi, o'lchovlar va normaga solishtirish, ajratish rejasi, fayl orqali almashish va shifrlangan zaxira (internetsiz). Protokol imzolash
  normalar muhandis tomonidan tasdiqlangandan keyin yoqiladi.`
- ru: `Пилотная версия: схема объекта, замеры и сверка с нормами, план отключения, обмен файлами и зашифрованная копия (без интернета). Подписание протоколов
  включится после утверждения норм инженером.`

## Skrinshotlar (foydalanuvchi oladi)

Telefon, 1080 × 1920 yoki yuqori, dark mavzu, kamida 4 ta: obyekt sxemasi, o'lchov kiritish (natija bilan), ajratish
rejasi (ogohlantirish matni ko'rinib turgan holda), protokol (QR). Imzolash ekrani `FLAG_SECURE` — skrinshot olinmaydi
(namuna sifatida PDF ko'rinishi ishlatiladi). Haqiqiy mijoz ma'lumotlari skrinshotda bo'lmasin.
