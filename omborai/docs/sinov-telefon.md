# Sinov: telefon va kompyuter (serversiz, protokol v2)

Ilovalarda server yo'q. Do'kon, foydalanuvchilar, tovar, savdo va smena qurilmada saqlanadi. Qurilmalar faqat
MQTT broker (`broker.hivemq.com`, TLS 8883) orqali gaplashadi va har bir operatsiya imzolanadi
(`docs/sync-mqtt.md`). Sinov uchun internet yetarli; bir Wi-Fi shart emas.

## 1. APK o'rnatish (telefon)

- Arm64 release APK: `omborai/mobile/build/app/outputs/flutter-apk/app-arm64-v8a-release.apk`
- `flutter build apk --release --split-per-abi` bilan qayta yig'ing (kod o'zgarsa).
- Telefonga o'tkazib, "noma'lum manbadan o'rnatish"ga ruxsat bering.

## 2. Kompyuter: desktop (ikkinchi qurilma)

```powershell
cd omborai\desktop
.venv\Scripts\activate
python -m omborai_desktop
```

Birinchi ishga tushirishda: "Yangi do'kon" (egasi) yoki "Mavjud do'konga qo'shilish" (kassa).

## 3. Juftlash va tasdiq

1. Egasi qurilmasida do'kon yarating (nom, egasi login, parol ≥ 8 belgi).
2. Egasi qurilmasida **Juftlash kodi** ni oching (telefonda kalit ikonkasi, desktopda "Foydalanuvchilar va
   qurilmalar"). Kod sir: faqat ishonchli qurilmaga yuboring.
3. Yangi qurilmada kodni kiriting. U "egasi tasdig'i kutilmoqda" holatiga o'tadi.
4. Egasi qurilmasida "Yangi qurilma" so'rovi chiqadi: **Kassir sifatida** / **Egasi sifatida** / **Rad etish**.
5. Tasdiqdan keyin yangi qurilma do'kon ma'lumotini oladi (bir necha soniya). Login oynasi shundan keyin ochiladi.

Egasi qurilmasi o'chiq bo'lsa, yangi qurilma kutadi va "egasi qurilmasini tekshiring" deb ko'rsatadi.

## 4. Sinov ro'yxati

Har bir bandni o'tkazib, natijani yozing (o'tdi / o'tmadi + nima ko'rindi).

1. **Do'kon yaratish:** egasi qurilmasida do'kon yarating, bosh ekran ochiladi.
2. **Noto'g'ri parol:** kirishda xato xabari chiqadi.
3. **Juftlash va tasdiq:** kassa qurilmasi kodni kiritadi, egasi tasdiqlaydi, kassa login qila oladi.
4. **Kassir qurilmasi cheklovi:** kassirda Tovarlar, Qaytarish, Foydalanuvchilar tugmalari o'chiq, sababi ko'rinadi.
5. **Egasi hisobi:** kassir qo'shish, faollashtirish/o'chirish ishlaydi; egasini o'chirib bo'lmaydi.
6. **Smena:** har bir qurilmada alohida ochiladi; ikkala qurilmada ham ochiq bo'lishi mumkin.
7. **Tovar:** egasi qo'shadi, o'zgartiradi; kassirda ko'rinadi.
8. **Savdo:** ikki tovar soting. Qoldiq ikkala qurilmada kamayadi. Narx katalogdagidan farq qilsa, savdo rad etiladi.
9. **Qaytarish:** faqat egasi qaytaradi; qoldiq tiklanadi; ikkinchi marta qaytarib bo'lmaydi.
10. **Oflayn navbat:** telefonni samolyot rejimiga qo'ying, savdo qiling, internetni qaytaring. Savdo
    kompyuterda bir marta paydo bo'lishi kerak (dublikat yo'q).
11. **Qurilmani bloklash:** egasi kassa qurilmasini bloklaydi; bloklangan qurilma endi savdo yubora olmaydi.
12. **Qayta kirish:** ilovani yopib qayta oching. Sessiya va ma'lumotlar qoladi.

## Ma'lum cheklovlar

- Broker kafolati yo'q: uzilish paytida yuborilgan xabar kechikishi mumkin (navbat va dublikat himoyasi bor).
- Ikki qurilma bir vaqtda oxirgi donani sotsa, qoldiq manfiy bo'lishi mumkin.
- `K` (do'kon kaliti) kassirda ham bor: kassir shifrlangan ma'lumotni o'qiy oladi. Bu keyingi bosqichda hal qilinadi.
- Fiskal chek hozircha "ishlab chiqish jarayonida".
