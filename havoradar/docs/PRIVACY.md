# HavoRadar — Maxfiylik siyosati

**Kuchga kirgan sana:** 2026-yil 2-noyabr
**Ilova:** HavoRadar (Android, paket nomi `uz.havoradar.app`)
**Ishlab chiquvchi:** JurabekM — aloqa: [GitHub Issues](https://github.com/JurabekM/Myrep/issues)

HavoRadar ochiq ob-havo va havo sifati prognozini tahlil qilib, kuchli issiqlik va havo ifloslanishi haqida
ogohlantiradi. U **shaxsiy ma'lumot yig'maydi va ishlab chiquvchiga hech narsa yubormaydi.**

## 1. Biz nimani yig'amiz
**Hech narsa.** Hisob (akkaunt), reklama, analitika, crash-hisobot yo'q. Ishlab chiquvchining serveri yo'q.
Ilova joylashuv (GPS) ruxsatini so'ramaydi.

## 2. Qurilmangizda nima saqlanadi
Faqat telefoningiz xotirasida, ilovaning yopiq papkasida:
- sozlamalar: tanlangan shaharlar, sezgir guruhlar (masalan, «65 yoshdan kattalar»), ogohlantirish darajasi,
  yangilash chastotasi, mavzu;
- yuklangan prognoz (internet bo'lmaganda ko'rsatish uchun);
- qaysi kunlar haqida bildirishnoma yuborilgani (takror yubormaslik uchun).

Sezgir guruhlar haqidagi belgilar sog'liq bilan bog'liq ma'lumot bo'lgani uchun **hech qachon telefondan chiqmaydi**:
ular faqat ball hisoblashda ishlatiladi. Ma'lumotlar Google zaxira nusxasiga kiritilmaydi. O'chirish:
*Sozlamalar → Ilovalar → HavoRadar → Xotira → Ma'lumotlarni tozalash* yoki ilovani o'chirish.

## 3. Internetga qanday murojaat qilinadi

| Server | Nima yuboriladi | Nima olinadi |
|---|---|---|
| `api.open-meteo.com` | tanlangan **shahar markazining** koordinatalari | ob-havo prognozi |
| `air-quality-api.open-meteo.com` | tanlangan **shahar markazining** koordinatalari | havo sifati prognozi |

Sizning aniq joylashuvingiz emas, ro'yxatdan tanlangan shaharning umumiy koordinatasi yuboriladi (masalan, Toshkent
markazi). Har qanday internet so'rovidagi kabi server IP-manzilingizni ko'radi — Open-Meteo'ning maxfiylik siyosati:
https://open-meteo.com/en/terms. Manbaning asl sahifasini ochsangiz, u brauzeringizda ochiladi.

## 4. Ruxsatlar
- **Internet** — prognozni yuklash uchun.
- **Bildirishnomalar** (Android 13+) — ogohlantirish yuborish uchun; istalgan vaqtda o'chirish mumkin.

## 5. Bolalar
Ilova bolalarga mo'ljallanmagan va hech kimdan ma'lumot yig'maydi.

## 6. O'zgarishlar
Siyosat o'zgarsa, shu sahifa yangilanadi va sana o'zgaradi.
