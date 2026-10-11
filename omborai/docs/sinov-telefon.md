# Sinov: telefon va kompyuter (serversiz)

Ilovalarda server yo'q. Login, do'kon, tovar, savdo va smena — hammasi qurilmada saqlanadi. Qurilmalar
bir-biri bilan faqat MQTT broker (`broker.hivemq.com`) orqali gaplashadi. Demak sinov uchun:

- Telefon va kompyuterda internet bo'lishi kifoya (bir Wi-Fi shart emas).
- Hech qanday Docker, server yoki IP sozlamasi kerak emas.

## 1. Telefon: APK o'rnatish

- APK: `omborai/mobile/build/app/outputs/flutter-apk/app-release.apk` (yoki yangisini
  `flutter build apk --release` bilan yig'ing).
- Telefonga o'tkazing va o'rnating (noma'lum manbadan o'rnatishga ruxsat bering).

## 2. Kompyuter: desktop ilova (ixtiyoriy, ikkinchi qurilma)

```
cd omborai/desktop
python -m omborai_desktop
```

Birinchi ishga tushirishda "Yangi do'kon" yoki "Do'konga qo'shilish" tanlanadi.

## 3. Ikki qurilmani ulash (juftlash)

1. Birinchi qurilmada (masalan telefon) do'kon yarating: do'kon nomi, egasi, login, parol (kamida 8 belgi).
2. Shu qurilmada **Juftlash** ekranini oching va kodni nusxalang (`<do'kon ID>:<kalit>`).
3. Ikkinchi qurilmada "Do'konga qo'shilish" ni tanlab kodni kiriting.
4. Ikkinchi qurilma ma'lumotni (do'kon, foydalanuvchilar, tovarlar) MQTT orqali oladi. Bir necha soniyadan bir
   daqiqagacha kutish mumkin. Keyin egasining login/parolini kiriting.

Kalit juftlashdan keyin ikkala qurilmada bir xil bo'lishi kerak. Kodni ishonchli kanal orqali yuboring
(xabar, qo'lda). Kod ichida do'kon kaliti bor: kim o'qisa, shu do'konga ulanadi.

## 4. Sinov ro'yxati

Har bandni o'tkazib, natijani yozing (o'tdi / o'tmadi + nima ko'rindi).

1. **Do'kon yaratish:** telefonda do'kon yarating. Login ekranidan keyin bosh sahifa ochiladi.
2. **Noto'g'ri parol:** kirishda xato xabari chiqadi.
3. **Juftlash:** kompyuterda kodni kiritib qo'shiling. Do'kon nomi va login ishlaydi.
4. **Yangi foydalanuvchi:** egasi ikkinchi kassir qo'shadi (yoki hozircha faqat egasi bilan sinang).
5. **Smena ochish:** naqd boshlang'ich summa. Ikkinchi qurilmada ham ochiq smena ko'rinadi.
6. **Tovar qo'shish va tahrirlash:** telefonda yarating, kompyuterda paydo bo'ladi. Narxni o'zgartiring.
7. **Savdo:** ikkita tovar soting (skaner yoki qo'lda). Qoldiq kamayadi, ikkinchi qurilmada ham ko'rinadi.
8. **Skaner:** kamera ruxsatini so'raydi, shtrix-kodni o'qiydi.
9. **Qaytarish:** chekni qaytaring. Qoldiq tiklanadi. Ikkinchi marta qaytarib bo'lmasligi kerak.
10. **Oflayn navbat:** telefonni samolyot rejimiga qo'ying, savdo qiling, internetni qaytaring.
    Ikkinchi qurilmada savdo keyinroq paydo bo'lishi va dublikat bo'lmasligi kerak.
11. **Smena yopish:** hisobot (savdo soni, jami, naqd) to'g'ri chiqadi.
12. **Qayta kirish:** ilovani yopib qayta oching. Sessiya saqlanadi, ma'lumotlar qoladi.

## Ma'lum cheklovlar

- Ikki qurilma bir vaqtda oxirgi donani sotsa, qoldiq manfiyga tushishi mumkin (markaziy hakam yo'q).
- Ommaviy brokerda yetkazib berish kafolati yo'q. Uzilish paytida yuborilgan xabar kechikishi mumkin.
- Parol xeshi do'kon kaliti bilan shifrlangan MQTT orqali uzatiladi. Kalit tarqalsa, xeshni taxmin qilish
  mumkin: parollar kuchli bo'lsin.
- Fiskal chek hozircha "ishlab chiqish jarayonida".
