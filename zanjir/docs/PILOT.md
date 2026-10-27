# ZANJIR — pilot uchun yo'riqnoma

> Pilot laboratoriyalar uchun (Play internal testing). Ilova — **yordamchi vosita**: u normaga solishtiradi va reja
> **tavsiya** qiladi, lekin hech qachon "ishlash xavfsiz" demaydi. Xavfsizlik bo'yicha javobgarlik naryad-ruxsatnoma beruvchi
> va ish rahbarida. Elektr qurilmalarida ish amaldagi qoidalar (PTEEP, PTB) va naryad-ruxsatnoma asosida bajariladi.

## 1. O'rnatish
1. Laboratoriya rahbaridan (LEAD) Play internal testing havolasini oling va shu Google hisobi bilan oching.
2. Android 7.0 yoki yangiroq. "ZANJIR" ni Play'dan o'rnating.
3. Birinchi ochilishda profil yaratiladi (F.I.Sh., telefon, xavfsizlik guruhi). Internet shart emas — ilova oflayn ishlaydi.

## 2. Laboratoriya va xodimlar
- **LEAD (rahbar):** Sozlamalar → Laboratoriya: nomi, litsenziya raqami va muddati. Sozlamalar → Server → "Laboratoriyani
  serverda ro'yxatdan o'tkazish" (pilot operatori ro'yxatdan o'tishni vaqtincha ochadi). Keyin "Taklif kodi yaratish" —
  har xodimga alohida kod (rol: ENGINEER yoki VIEWER), kod 72 soat amal qiladi.
- **Muhandis:** ilovada "Taklif kodi bilan qo'shilish" → kod, F.I.Sh., telefon, parol. Yangi telefonda — "Kirish".
- Telefon yo'qolsa — darhol LEAD'ga ayting: u pilot operatori orqali qurilmani bekor qildiradi (ilovada bu ekran hali yo'q).

## 3. Ish tartibi
1. **Obyekt** → sxema: shchit, avtomat, UZO, kabel, rozetka guruhlari, yerga ulagich. Har tugunda QR yorliq (`zanjir://app/n/...`).
2. **Asboblar:** model, seriya, qiyoslash guvohnomasi va muddati. Muddati o'tgan asbob bilan olingan o'lchov protokolga kirmaydi.
3. **Sessiya:** turi (qabul-topshirish / davriy / navbatdan tashqari), harorat, namlik → tugun bo'yicha o'lchovlar. Natija: PASS / FAIL / NEEDS_REVIEW
   (ma'lumot yetishmasa yoki norma noaniq bo'lsa — NEEDS_REVIEW; buni faqat LEAD izoh bilan imzolaydi).
4. **Protokol:** sessiyani yopish → protokol → bloklovchi shartlar (ochiq sessiya, muddati o'tgan asbob, tekshirilmagan
   normalar, litsenziya...) → imzolash. PDF va QR (tekshirish sahifasi). Imzolangan protokol o'zgartirilmaydi, faqat
   sabab bilan bekor qilinadi.
5. **Ajratish rejasi** (5 ta texnik tadbir): obyekt → reja → ishlanadigan tugunlar → reja (tavsiya) → LEAD tasdiqlaydi →
   joyda qadamlar ketma-ket belgilanadi. "Kuchlanish yo'qligini tekshirish" — indikatorni ishlaydigan manbada sinash va
   kuchlanish yo'qligini tasdiqlash, ikkalasi ham qo'lda. Sxema o'zgarsa reja eskiradi (STALE) — yangisini tuzing.
6. **Sinxronlash:** internet bo'lganda avtomatik (5 daqiqada bir va ilova ochilganda) yoki Sozlamalar → Server →
   "Sinxronlash". Oflayn kiritilgan ma'lumot yo'qolmaydi. Server yozuvni rad etsa, ekranda jadval va sabab
   ko'rsatiladi — LEAD'ga ayting.

## 4. Pilotdagi cheklovlar
- ⚠️ **Normalar hali litsenziyali muhandis tomonidan tasdiqlanmagan** (1-darvoza). Shu sababli protokol imzolash
  bloklangan bo'ladi ("normalar tekshirilmagan"): pilotda o'lchov, baholash va reja sinaladi; rasmiy protokol — amaldagi
  tartibda (qog'oz/eski dastur).
- QR yorliqni kamera bilan skanerlash hali yo'q (havola orqali ochiladi).
- Ilovaga kirishda PIN yo'q — telefon ekran qulfini yoqing.
- Telefon soati avtomatik (tarmoq vaqti) bo'lsin: soati noto'g'ri telefonning ma'lumotini server rad etadi.

## 5. Fikr-mulohaza
Har hafta: nima qulay emas, qaysi o'lchov/norma noto'g'ri baholandi (tugun, qiymat, kutilgan natija), xatolar (vaqt,
ekran rasmi — imzolash ekranidan tashqari). Shaxsiy ma'lumot va parollarni yubormang. Kanal va mas'ul — pilot operatori
belgilaydi. Pilot yakunida 4-darvoza: keyingi reja shu fikrlar asosida.
