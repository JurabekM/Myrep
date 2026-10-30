# ZANJIR — Maxfiylik siyosati (qoralama)

> ⚠️ **Huquqshunos tekshiruvidan oldin e'lon qilinmaydi.** O'zbekiston Respublikasining "Shaxsga doir ma'lumotlar
> to'g'risida"gi qonuni va lokalizatsiya talabi bo'yicha matn tasdiqlanishi kerak. `<...>` — operator ma'lumotlari.

**Kuchga kirish sanasi:** `<sana>` · **Operator:** `<tashkilot nomi, manzili, STIR>` · **Aloqa:** `<e-pochta>`

## 1. Ilova nima qiladi
ZANJIR — elektrolaboratoriyalar uchun ish vositasi: obyekt sxemasi, o'lchovlar, normaga solishtirish, protokol va ajratish
rejasi. Ilova **to'liq oflayn**: server yo'q, internetga ulanmaydi (internet ruxsati yo'q). Ma'lumot faqat laboratoriya
xodimlarining telefonlarida va ular o'zlari yaratgan shifrlangan fayllarda (zaxira, almashish) bo'ladi.

## 2. Qanday ma'lumot qayta ishlanadi
- **Xodim:** F.I.Sh., telefon raqami (faqat o'z telefonida; almashish fayliga kirmaydi), rol, elektr xavfsizligi guruhi.
- **Qurilma:** ilova yaratgan qurilma identifikatori va ochiq kalit (imzolarni tekshirish uchun). Maxfiy kalit faqat qurilmada,
  Android Keystore bilan shifrlangan xotirada saqlanadi va hech qayerga (zaxiraga ham) chiqmaydi.
- **Ish ma'lumotlari:** obyektlar (nomi, manzili, buyurtmachi), sxema, o'lchovlar, asboblar, protokollar, ajratish rejalari,
  audit jurnali (kim, qachon, qaysi qurilmadan).
- Yig'ilmaydi: joylashuv, kontaktlar, rasmlar, mikrofon, reklama identifikatori, analitika.

## 3. Maqsad va asos
Laboratoriya ishini bajarish va hujjatlashtirish (protokol, uning haqiqiyligini tekshirish), xavfsizlik (kirish, imzo,
o'zgartirishlarni aniqlash). Asos — laboratoriya (operator) bilan mehnat/xizmat munosabatlari va qonun talablari.

## 4. Saqlash joyi va muddati
- Xodimlarning telefonlarida; zaxira va almashish fayllari — parol yoki laboratoriya kaliti bilan shifrlangan holda
  laboratoriya tanlagan joyda (kompyuter, flesh, messenjer). Fayllarni qayerda saqlash va qachon o'chirish — laboratoriya
  ichki tartibi (`RUNBOOK.md`).
- Imzolangan protokollar va audit jurnali o'zgartirilmaydi va `<qonuniy muddat>` saqlanadi.
- Boshqa ma'lumotlar laboratoriya xizmatdan foydalanayotgan davrda va undan keyin `<muddat>` saqlanadi.

## 5. Kimga ochiladi
- Faqat shu laboratoriya xodimlariga (taklif orqali qo'shilgan telefonlar), ularning roliga ko'ra.
- Protokol PDF — buyurtmachiga beriladigan hujjat; QR havola (`zanjir://`) faqat ZANJIR o'rnatilgan telefonda ochiladi.
- Ilova ishlab chiqaruvchisi ma'lumotni olmaydi: tashqi analitika, xato xizmatlari va serverlar yo'q.
- Uchinchi tomonga sotilmaydi va reklama uchun berilmaydi. Davlat organlariga — faqat qonunda belgilangan hollarda.

## 6. Himoya
Qurilma kaliti bilan imzo va audit hash-zanjiri (o'zgartirishni aniqlash), shifrlangan zaxira (Argon2id +
ChaCha20-Poly1305), almashish fayllari laboratoriya kaliti bilan shifrlangan va imzolangan, taklif — bir martalik parol
bilan, yo'qolgan telefonni bekor qilish, Android zaxirasi (`allowBackup`) o'chirilgan.

## 7. Huquqlaringiz
Ma'lumotlaringiz haqida ma'lumot olish, tuzatish, o'chirishni so'rash (imzolangan protokollar va audit jurnali bundan
mustasno — ular qonun bo'yicha saqlanadi). Murojaat: laboratoriya administratori yoki `<e-pochta>`.

## 8. O'zgarishlar
Siyosat o'zgarsa — yangi sana bilan shu sahifada e'lon qilinadi.
