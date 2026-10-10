# Telefon sinovi (lokal, kompyuterda server)

Maqsad: Android telefonda ilovani kompyuterdagi backend bilan sinash. Savdo, qaytarish, smena va tovar
operatsiyalari MQTT orqali (`broker.hivemq.com`) ketadi, shuning uchun telefon va desktop ikkalasida internet
bo'lishi kerak. Login va do'konlar ro'yxati esa kompyuterdagi serverga boradi (bir Wi-Fi tarmog'ida).

Hosting qarori hali qabul qilinmagan. Bu hujjat faqat lokal sinov uchun.

## 1. Kerak bo'ladi

- Kompyuter: Docker Desktop (yoki Docker Engine), Flutter SDK (APK yig'ish uchun).
- Android telefon, USB orqali yoki APK faylini o'tkazib o'rnatish imkoniyati.
- Telefon va kompyuter bir Wi-Fi tarmog'ida.

## 2. Serverni ishga tushirish

`omborai/infra/` papkasida `.env` fayl yarating (repoga kiritilmaydi, `.gitignore`da bor):

```
POSTGRES_PASSWORD=<tasodifiy>
OMBORAI_APP_PASSWORD=<tasodifiy>
REDIS_PASSWORD=<tasodifiy>
OMBORAI_JWT_SECRET=<tasodifiy, 32+ belgi>
OMBORAI_DOMAIN=:80
```

Tasodifiy qiymat: `openssl rand -hex 16` (JWT uchun `-hex 32`). `OMBORAI_DOMAIN=:80` Caddy'ni oddiy HTTP
rejimida ishga tushiradi, shunda telefon sertifikatsiz ulanadi.

```
cd omborai/infra
docker compose --env-file .env up -d --build
```

Tekshirish (kompyuterda): `http://localhost/healthz` javobi `200` bo'lishi kerak.

Sinov foydalanuvchisini yarating:

```
curl -s -H "content-type: application/json" -d "{\"email\":\"owner@test.uz\",\"password\":\"parol-12345-xyz\",\"tenant_name\":\"Test do'kon\",\"full_name\":\"Test egasi\",\"store_name\":\"Asosiy filial\"}" http://localhost/v1/auth/register
```

## 3. Kompyuterning LAN manzili

- Windows: `ipconfig` → "IPv4 manzil" (masalan `192.168.1.23`).
- Linux/macOS: `hostname -I` yoki `ipconfig getifaddr en0`.

Windows Firewall 80-portga kirishga ruxsat berishi kerak (birinchi ishga tushirishda so'raydi).

Tekshirish telefonning brauzerida: `http://<LAN-IP>/healthz` → `200`.

## 4. APK yig'ish va o'rnatish

`--dart-define` majburiy: standart manzil emulyator uchun (`10.0.2.2`), haqiqiy telefonda ishlamaydi.

```
cd omborai/mobile
flutter build apk --debug --dart-define=OMBORAI_API_URL=http://<LAN-IP>
```

Emulyatorda (Android Studio AVD, kompyuterida virtualizatsiya yoqilgan bo'lsa) manzil boshqacha:
`--dart-define=OMBORAI_API_URL=http://10.0.2.2` (port yozilmaydi: server 80-portda, 8000 kompyuterga chiqarilmagan).

APK: `build/app/outputs/flutter-apk/app-debug.apk`. Telefonga o'tkazing va o'rnating (noma'lum manbadan
o'rnatishga ruxsat bering). Debug build HTTP'ga ruxsat beradi; release build faqat HTTPS bilan ishlaydi.

## 5. Desktop (ixtiyoriy, ikkinchi qurilma sifatida)

Ikkala qurilma bir xil do'kon kalitini ishlatishi kerak. Telefon kalitni birinchi yaratadi; desktopga uni
`OMBORAI_STORE_KEY` (64 belgili hex) muhit o'zgaruvchisi orqali bering. Desktop serveri uchun
`OMBORAI_API_URL=http://<LAN-IP>` ham kerak bo'lishi mumkin.

## 6. Sinov ro'yxati

Har bandni o'tkazib, natijani yozing (o'tdi / o'tmadi + nima ko'rindi).

1. **Kirish:** noto'g'ri parol → xato xabari. To'g'ri parol (`owner@test.uz`) → bosh sahifa.
2. **Do'kon:** do'konlar ro'yxatida "Asosiy filial" ko'rinadi.
3. **Smena ochish:** naqd boshlang'ich summa bilan. Desktopda ham ochiq smena ko'rinadi (MQTT).
4. **Tovar qo'shish:** yangi forma orqali tovar yarating (nom, birlik, narx, shtrix-kod). Desktopda paydo bo'ladi.
5. **Tovar tahrirlash:** narxni o'zgartiring. Desktopda yangi narx ko'rinadi.
6. **Savdo:** ikkita tovar soting (skaner yoki qo'lda). Qoldiq kamayadi, desktopda chek paydo bo'ladi.
7. **Skaner:** kamera ruxsatini so'raydi, shtrix-kodni o'qiydi.
8. **Qaytarish:** chekni qaytaring. Qoldiq tiklanadi. Ikkinchi marta qaytarib bo'lmasligi kerak.
9. **Oflayn navbat:** telefonni samolyot rejimiga qo'ying, savdo qiling, internetni qaytaring. Desktopda
   savdo keyinroq paydo bo'lishi kerak va dublikat bo'lmasligi kerak.
10. **Smena yopish:** hisobot (savdo soni, jami, naqd) to'g'ri chiqadi.
11. **Qayta kirish:** ilovani yopib qayta oching. Sessiya saqlanadi, ma'lumotlar qoladi.

## Ma'lum cheklovlar (sinovda kutiladigan)

- Ikki qurilma bir vaqtda oxirgi donani sotsa, qoldiq manfiyga tushishi mumkin (markaziy hakam yo'q).
- Ommaviy brokerda yetkazib berish kafolati yo'q. Uzilish paytida yuborilgan xabar kechikishi mumkin.
- Login va do'konlar ro'yxati serverga bog'liq; savdo serverga bog'liq emas.
- Fiskal chek hozircha "ishlab chiqish jarayonida".
