# ZANJIR — pilot uchun yo'riqnoma

> Pilot laboratoriyalar uchun (Play internal testing). Ilova — **yordamchi vosita**: u normaga solishtiradi va reja
> **tavsiya** qiladi, lekin hech qachon "ishlash xavfsiz" demaydi. Xavfsizlik bo'yicha javobgarlik naryad-ruxsatnoma beruvchi
> va ish rahbarida. Elektr qurilmalarida ish amaldagi qoidalar (PTEEP, PTB) va naryad-ruxsatnoma asosida bajariladi.

## 1. O'rnatish
1. Laboratoriya rahbaridan (LEAD) Play internal testing havolasini oling va shu Google hisobi bilan oching.
2. Android 7.0 yoki yangiroq. "ZANJIR" ni Play'dan o'rnating.
3. Ilova **to'liq oflayn** (internet ruxsati yo'q). Birinchi ochilishda: LEAD — "Oflayn profil yaratish" (yangi
   laboratoriya); xodim — "Taklif fayli bilan qo'shilish"; telefon almashtirilganda — "Zaxiradan tiklash".

## 2. Laboratoriya va xodimlar
- **LEAD (rahbar):** Sozlamalar → Laboratoriya: nomi, litsenziya raqami va muddati. Sozlamalar → "Xodimlar va almashish"
  → xodim qo'shish (rol: ENGINEER, VIEWER, LEAD yoki ADMIN) → **taklif fayli**. Faylni xodimga yuboring (messenjer, USB),
  ekrandagi **parolni faqat yuzma-yuz** ayting. Taklif 7 kun va bitta telefon uchun amal qiladi.
- **Muhandis:** boshlang'ich ekranda "Taklif fayli bilan qo'shilish" → fayl → parol.
- Laboratoriyada kamida **ikkita** LEAD/ADMIN telefoni bo'lsin: zaxiradan tiklangan telefonni boshqa LEAD/ADMIN tasdiqlaydi.
- Telefon yo'qolsa — darhol LEAD'ga ayting: u "Xodimlar va almashish" → Qurilmalar → bekor qilish; keyin almashish faylini
  boshqa telefonlarga yuboradi (`RUNBOOK.md`).

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
6. **Almashish:** server yo'q. Ish kuni oxirida har xodim "Xodimlar va almashish" → "Almashish fayli" ni LEAD'ga
   yuboradi; LEAD qabul qiladi va o'z faylini hammaga qaytaradi (LEAD tasdiqlari, rejalar, bekor qilishlar tarqaladi).
   Fayl laboratoriya kaliti bilan shifrlangan va telefon imzolagan; qabul qilishda hamma narsa tekshiriladi — biror
   tekshiruv o'tmasa, **hech narsa** yozilmaydi va sabab ko'rsatiladi (LEAD'ga ayting).
7. **Zaxira:** har kuni Sozlamalar → "Zaxira nusxa" → faylni telefondan tashqarida saqlang (`RUNBOOK.md`).

## 4. Pilotdagi cheklovlar
- ⚠️ **Normalar litsenziyali muhandis tomonidan tasdiqlanmagan** — imzolash bloklanmaydi (ADR-0019), lekin protokol
  ekranida ogohlantirish chiqadi va PDF'da "muhandis tekshiruvidan o'tmagan" deb yoziladi. Protokolning qonuniy kuchi va
  normalar to'g'riligi uchun javobgarlik — laboratoriyada.
- QR yorliqni kamera bilan skanerlash hali yo'q (havola orqali ochiladi).
- Ilovaga kirishda PIN yo'q — telefon ekran qulfini yoqing.
- Telefon soati avtomatik (tarmoq vaqti) bo'lsin: 10 daqiqadan ko'proq oldinda bo'lgan telefonning tahrirlari qabul
  qilinmaydi (`clock_skew`).
- Xodim rolini pasaytirishdan oldin uning telefonidagi barcha o'zgarishlar almashilgan bo'lsin (rol hozirgi holat bo'yicha
  tekshiriladi).

## 5. Fikr-mulohaza
Har hafta: nima qulay emas, qaysi o'lchov/norma noto'g'ri baholandi (tugun, qiymat, kutilgan natija), xatolar (vaqt,
ekran rasmi — imzolash ekranidan tashqari). Shaxsiy ma'lumot va parollarni yubormang. Kanal va mas'ul — pilot operatori
belgilaydi. Pilot yakunida 4-darvoza: keyingi reja shu fikrlar asosida.
