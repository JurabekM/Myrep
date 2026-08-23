# DistribOS AI — foydalanuvchi qo'llanmasi

## Dastur nima qiladi

DistribOS AI — savdo, ombor va moliya uchun dastur. U **internetsiz ham
to'liq ishlaydi**: buyurtma yozasiz, to'lov qabul qilasiz, ombor
harakatini kiritasiz — hammasi shu kompyuterda saqlanadi. Internet paydo
bo'lganda ma'lumot boshqa qurilmalarga o'zi yuboriladi.

**Muhim:** markaziy server yo'q. Ma'lumot faqat sizning qurilmalaringizda.
Shuning uchun **zaxira nusxa olish — sizning vazifangiz**.

---

## Asosiy oyna

Chapda bo'limlar ro'yxati, o'ngda ish maydoni. Pastda holat chizig'i:

* **Hammasi sinxronlangan** — barcha yozuvlar boshqa qurilmalarga yetkazilgan;
* **Yuborilmoqda (N)** — N ta yozuv navbatda;
* **Ulanish yo'q — N ta yozuv navbatda** — ishlashda davom eting, hech
  narsa yo'qolmaydi.

---

## Kundalik ish

### Buyurtma yozish

1. **Buyurtmalar** → «Yangi buyurtma».
2. Mijozni tanlang. Uning qarzi qavs ichida ko'rinadi.
3. Mahsulot, miqdor va chegirmani kiriting → «Qatorni qo'shish».
4. «Saqlash».

Mijozning kredit limiti oshib ketsa dastur **ogohlantiradi**, lekin
qaror sizniki — davom etish yoki bekor qilish mumkin.

Buyurtma saqlangach «Qurilmada saqlandi» deb ko'rsatiladi. Bu **normal
holat**: internet bo'lganda u avtomatik «Sinxronlandi» ga o'zgaradi.

### Buyurtma holatini o'zgartirish

**Buyurtmalar** → qatorni tanlang → «Holatni o'zgartirish».

Faqat **mumkin bo'lgan** holatlar ko'rsatiladi. Masalan jo'natilgan
buyurtmani bekor qilib bo'lmaydi — tovar allaqachon ketgan, buning
o'rniga qaytarish rasmiylashtiriladi.

### To'lov qabul qilish

**Kassa va to'lovlar** → «To'lov qabul qilish».

To'lov mijozning umumiy qarzini kamaytiradi. Uni aniq buyurtmaga
biriktirish shart emas.

### To'lovni bekor qilish

To'lovni tanlab «To'lovni bekor qilish» ni bosing.

To'lov **o'chirilmaydi** — uning o'rniga teskari yozuv yaratiladi.
Shunday qilib kassa tarixi butun qoladi va tekshiruvda savol tug'ilmaydi.

### Ombor

**Ombor** → «Kirim/chiqim qo'shish».

Qoldiq **qo'lda yozilmaydi** — u kirim va chiqimlardan hisoblanadi.
Shuning uchun ikki xodim bir vaqtda ishlasa ham raqam adashmaydi.

Miqdorni manfiy qilish faqat «Tuzatish» amalida mumkin.

---

## Hisobotlar va hujjatlar

**Hisobotlar** — davrni tanlab «Shakllantirish». Natijani **CSV**
(Excel uchun) yoki **PDF** sifatida saqlash mumkin.

**Hujjatlar** — buyurtmani tanlab, kerakli hujjatni PDF qilib chiqarasiz:
buyurtma, hisob-faktura, yuk xati, qaytarish hujjati.

---

## AI yordamchi

**AI yordamchi** → «Tahlil qilish».

Dastur sizning ma'lumotlaringizni tahlil qilib tavsiya beradi: qoldig'i
kam mahsulotlar, muddati o'tgan qarzlar, kredit limitiga yaqinlashgan
mijozlar, sekin sotilayotgan tovarlar.

**AI hech qachon o'zi amal bajarmaydi.** U buyurtma tasdiqlamaydi, to'lov
yaratmaydi va qoldiqqa tegmaydi — faqat tavsiya beradi.

Tahlil shu kompyuterda, **internetsiz** bajariladi. Tashqi xizmatga hech
narsa yuborilmaydi.

---

## Zaxira nusxa — MAJBURIY

**Zaxira nusxa** → «Nusxa yaratish» → parol kiriting.

Nusxa shifrlanadi. **Parolni yo'qotsangiz nusxani ochib bo'lmaydi.**

Nusxani flesh-diskka yoki boshqa kompyuterga ham ko'chiring.

### Nusxa haqiqatan ishlashini tekshirish

«Nusxani tekshirish» tugmasi nusxani ochib, butunligini tasdiqlaydi.
**Buni oyiga bir marta qiling** — «nusxa bor» degani «nusxa ishlaydi»
degani emas.

### Agar hammasi yo'qolsa

Agar barcha kompyuter va telefonlar yo'qolsa va tashqi nusxa bo'lmasa —
ma'lumotni tiklash **imkoni bo'lmaydi**. Internet orqali sinxronizatsiya
ma'lumot ombori emas, u faqat qurilmalar o'rtasida yetkazadi.

---

## Sinxronizatsiya bo'limi

Bu texnik bo'lim. Odatda kerak emas, lekin quyidagi holatlarda qarang:

* biror yozuv boshqa qurilmada ko'rinmayapti;
* «Xatolik yuz berdi» degan holat paydo bo'ldi;
* yangi qurilma qo'shmoqchisiz.

«Hozir sinxronlash» — darhol yuborishga urinadi.
«Xatolarni qayta urinish» — yuborilmagan yozuvlarni navbatga qaytaradi.

---

## Tekshiruv navbati

Ba'zan ikki qurilmada bir-biriga **zid** o'zgarish bo'ladi. Masalan bir
xodim buyurtmani bekor qildi, boshqasi ayni paytda uni jo'natdi.

Dastur bunday holatni **jimgina hal qilmaydi** — u shu bo'limda
ko'rsatiladi va qaror sizniki.

---

## Ochiq broker ogohlantirishi

Dastur birinchi ishga tushganda quyidagi ogohlantirish chiqishi mumkin:

> Siz ochiq MQTT brokeridan foydalanmoqdasiz…

Bu **sinov rejimi**. Xabarlar himoyalangan, lekin bog'lovchi xizmatning
uzluksiz ishlashi kafolatlanmaydi. Haqiqiy mijoz ma'lumotlari bilan
ishlash uchun administratordan **xususiy broker** sozlashni so'rang.

---

## Tez-tez beriladigan savollar

**Internet yo'q — ishlay olamanmi?**
Ha. Barcha asosiy ishlar bajariladi. Ma'lumot keyin yuboriladi.

**Ma'lumot qayerda saqlanadi?**
Shu kompyuterda: `%LOCALAPPDATA%\DistribOS\data`.

**Dasturni o'chirsam ma'lumot yo'qoladimi?**
Yo'q. O'chirishda faqat log fayllar tozalanadi; baza va zaxira nusxalar
joyida qoladi.

**Telefon yo'qolsa?**
Administratorga ayting — u qurilmani ro'yxatdan chiqaradi va undan
keyingi barcha yozuvlar rad etiladi.

**Nega buyurtma «Qurilmada saqlandi» deb turibdi?**
Internet yo'q yoki boshqa qurilma o'chiq. Yozuv yo'qolmaydi.
