# OmborAI — Mobil (Flutter + Kotlin)

Android (8.0+) uchun kassir va egasi ilovasi. Backend (`../backend`) va desktop (`../desktop`) bilan bir xil API va
offline-sinxronizatsiya qoidalaridan foydalanadi.

## Tuzilishi

- `lib/src/api/` — HTTP klient. Aloqa yo'q bo'lsa `OfflineException` tashlaydi, server xatolari `ApiException`.
- `lib/src/offline/` — mahalliy SQLite (sqflite): tovar keshi, qoldiq nusxasi, savdo navbati, sinxron holati.
- `lib/src/domain/cart.dart` — savat. Savdo payload'ida narx yo'q, server o'zi hisoblaydi.
- `lib/src/app_session.dart` — sessiya: kirish, do'kon, smena, savdo (online yoki navbat), 15 soniyalik sinxron.
- `lib/src/screens/` — kirish, bosh sahifa, kassa, tovarlar, skaner.
- `android/app/src/main/kotlin/.../scanner/` — **native Kotlin**: CameraX + ML Kit shtrix-kod skaneri,
  Flutter'ga `uz.omborai/scanner` platform view sifatida ulanadi.

## Ishga tushirish

```bash
cd mobile
flutter pub get
# Emulyator (10.0.2.2 — kompyuterdagi localhost):
flutter run --dart-define=OMBORAI_API_URL=http://10.0.2.2:8000
```

Production uchun `OMBORAI_API_URL` HTTPS manzil bo'lishi kerak (`https://api.omborai.example.uz`).

## Testlar

```bash
flutter analyze
flutter test
```

Testlar: pul formati, savat, API klient (401 → refresh, offline aniqlash), lokal navbat va sinxronizatsiya, kirish ekrani.

## Android build

```bash
flutter build apk --debug
```

Talab: Android SDK (platform 35), JDK 17+. Native skaner uchun kamera ruxsati ilova ishga tushganda so'raladi.

## Ma'lum cheklovlar

- Sinxronizatsiya hozircha ilova ochiq paytida (har 15 soniya) ishlaydi. Fon rejimi (WorkManager) keyingi qadam.
- iOS keyinroq: Flutter tayyor, lekin skaner faqat Android'da (iOS uchun alohida native plugin kerak).
- Mobil kassada chegirma yo'q (chegirmalar desktop kassada, server huquqlari bo'yicha).
