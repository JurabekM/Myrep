# EpiRadar — Google Play uchun materiallar

## Do'kon sahifasi (o'zbekcha)

**Nomi (≤ 30):** EpiRadar — epidemiya radari

**Qisqa tavsif (≤ 80):** JSST, ECDC va CDC ma'lumotlari asosida epidemiya xavfidan oldindan ogohlantirish

**To'liq tavsif:**

EpiRadar dunyodagi yuqumli kasalliklar avj olishini rasmiy manbalardan kuzatib boradi va mamlakatingiz uchun
xavf darajasini hisoblaydi. Xavf oshsa — telefoningiz darhol xabar beradi.

• Faqat rasmiy manbalar: Jahon sog'liqni saqlash tashkiloti (JSST), Yevropa CDC (ECDC), AQSh CDC sayohat
  ogohlantirishlari, JSST FluNet gripp kuzatuvi.
• Mamlakatingiz uchun 0–100 xavf balli va 5 daraja: Tinch, Kuzatuv, Ogohlik, Xavf, Favqulodda — har birining
  sababi tushuntiriladi.
• Fon rejimida ogohlantirish: yangi yoki kuchaygan xavf haqida bildirishnoma.
• Gripp trendlari: mavsum me'yoridan oshgan faollikni statistik usullar bilan aniqlash.
• 32 kasallik bo'yicha internetsiz ma'lumotnoma: yuqish yo'li, alomatlar, oldini olish, qachon shifokorga.
• Oila tayyorgarligi ro'yxati, sayohat uchun kuzatuv ro'yxati, bosh ekran vidjeti.
• Shaxsiy ma'lumot yig'ilmaydi, reklama yo'q.

EpiRadar ma'lumot beradi, tashxis qo'ymaydi va shifokor o'rnini bosmaydi.

**Kategoriya:** Tibbiyot (Medical) yoki Salomatlik va fitnes — Play Console'da tanlang.
**Maxfiylik siyosati:** https://github.com/JurabekM/Myrep/blob/master/epiradar/docs/PRIVACY.md
**Kontent reytingi:** so'rovnomada zo'ravonlik/qimor/foydalanuvchi kontenti yo'q; tibbiy ma'lumot bor.

## Data safety (Ma'lumotlar xavfsizligi) — tavsiya etilgan javoblar

| Savol | Javob | Izoh |
|---|---|---|
| Ilova foydalanuvchi ma'lumotini yig'adimi yoki uzatadimi? | **Yo'q** | Hisob, analitika, reklama, crash SDK yo'q; ishlab chiquvchi serveri yo'q |
| Ma'lumot uchinchi tomonlarga beriladimi? | **Yo'q** | |
| Ma'lumot uzatishda shifrlanadimi? | Ha (HTTPS) | Faqat HTTPS; cleartext o'chirilgan |
| Ma'lumotni o'chirish so'rovi? | Talab qilinmaydi | Hamma narsa qurilmada; ilova ma'lumotini tozalash yoki o'chirish |

**E'tibor bering (o'zingiz qaror qiling):** FluNet so'rovlarida gripp statistikasi kerak bo'lgan mamlakatlar
kodi (masalan `UZB`) JSST serveriga yuboriladi. Bu foydalanuvchi bilan bog'lanmagan ochiq ma'lumot so'rovi
parametri, shaxsiy identifikator emas — shuning uchun «yig'ilmaydi» javobi asosli. Agar Google buni «taxminiy
joylashuv» deb so'rasa, siyosatdagi 3-bo'limga havola bering.

## Deklaratsiyalar

- **Sog'liq ilovalari (Health apps) deklaratsiyasi:** ilova umumiy sog'liq/epidemiologik ma'lumot beradi; tibbiy
  qurilma emas, tashxis qo'ymaydi, foydalanuvchining sog'liq ma'lumotini yig'maydi. Play Console'dagi eng yaqin
  toifani tanlang.
- **Ruxsatlar:** bildirishnoma (ixtiyoriy), internet, fon sinxronlash (WorkManager). Joylashuv, kontaktlar,
  kamera, mikrofon, fayllar yo'q. Foreground service ishlatilmaydi.
- **Reklama:** yo'q. **Maqsadli auditoriya:** 18+ (yoki 13+), bolalar uchun emas.
- Sog'liqni saqlash mavzusidagi ilovalar qo'shimcha ko'rib chiqilishi mumkin — tavsifda manbalarni aniq
  ko'rsatish va «tashxis qo'ymaydi» ogohlantirishi shu uchun.

## Skrinshotlar

CI `emulator` job'i har bir yig'ishda haqiqiy emulyatordan bosh ekran skrinshotini oladi
(`epiradar-emulator-api36` artefakti). Play uchun kamida 2 ta telefon skrinshoti (1080×1920 yoki undan katta)
kerak — real telefoningizda Radar, Signallar, hodisa tafsiloti va Kasalliklar ekranlarini oling.
