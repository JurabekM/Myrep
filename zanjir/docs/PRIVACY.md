# ZANJIR — Maxfiylik siyosati (qoralama)

> ⚠️ **Huquqshunos tekshiruvidan oldin e'lon qilinmaydi.** O'zbekiston Respublikasining "Shaxsga doir ma'lumotlar
> to'g'risida"gi qonuni va lokalizatsiya talabi bo'yicha matn tasdiqlanishi kerak. `<...>` — operator ma'lumotlari.

**Kuchga kirish sanasi:** `<sana>` · **Operator:** `<tashkilot nomi, manzili, STIR>` · **Aloqa:** `<e-pochta>`

## 1. Ilova nima qiladi
ZANJIR — elektrolaboratoriyalar uchun ish vositasi: obyekt sxemasi, o'lchovlar, normaga solishtirish, protokol va ajratish
rejasi. Ilova oflayn ishlaydi; laboratoriya serveriga ulanganda ma'lumotlar sinxronlanadi.

## 2. Qanday ma'lumot qayta ishlanadi
- **Xodim:** F.I.Sh., telefon raqami, rol, elektr xavfsizligi guruhi; parol — serverda faqat argon2id hash ko'rinishida.
- **Qurilma:** ilova yaratgan qurilma identifikatori va ochiq kalit (imzolarni tekshirish uchun). Maxfiy kalit faqat qurilmada,
  Android Keystore bilan shifrlangan xotirada saqlanadi va serverga yuborilmaydi.
- **Ish ma'lumotlari:** obyektlar (nomi, manzili, buyurtmachi), sxema, o'lchovlar, asboblar, protokollar, ajratish rejalari,
  audit jurnali (kim, qachon, qaysi qurilmadan).
- Yig'ilmaydi: joylashuv, kontaktlar, rasmlar, mikrofon, reklama identifikatori, analitika.

## 3. Maqsad va asos
Laboratoriya ishini bajarish va hujjatlashtirish (protokol, uning haqiqiyligini tekshirish), xavfsizlik (kirish, imzo,
o'zgartirishlarni aniqlash). Asos — laboratoriya (operator) bilan mehnat/xizmat munosabatlari va qonun talablari.

## 4. Saqlash joyi va muddati
- Server — O'zbekiston hududida (`<hosting>`), zaxira nusxalar shifrlangan holda O'zbekiston hududida.
- Imzolangan protokollar va audit jurnali o'zgartirilmaydi va `<qonuniy muddat>` saqlanadi.
- Boshqa ma'lumotlar laboratoriya xizmatdan foydalanayotgan davrda va undan keyin `<muddat>` saqlanadi.

## 5. Kimga ochiladi
- Faqat shu laboratoriya xodimlariga, ularning roliga ko'ra (tashkilotlar bir-biridan ajratilgan).
- Protokol QR havolasi orqali: havolani olgan shaxs imzolovchining F.I.Sh., laboratoriya nomi va protokol holatini ko'radi;
  PDF — protokolning o'zi (buyurtmachiga beriladigan hujjat).
- Uchinchi tomonga sotilmaydi va reklama uchun berilmaydi. Davlat organlariga — faqat qonunda belgilangan hollarda.

## 6. Himoya
HTTPS (shifrlangan aloqa), parollar hash ko'rinishida, qurilma kaliti bilan imzo, tashkilotlar ajratilishi (bazada qatorlar
darajasida), shifrlangan zaxira, kirish urinishlarini cheklash.

## 7. Huquqlaringiz
Ma'lumotlaringiz haqida ma'lumot olish, tuzatish, o'chirishni so'rash (imzolangan protokollar va audit jurnali bundan
mustasno — ular qonun bo'yicha saqlanadi). Murojaat: laboratoriya administratori yoki `<e-pochta>`.

## 8. O'zgarishlar
Siyosat o'zgarsa — yangi sana bilan shu sahifada e'lon qilinadi.
