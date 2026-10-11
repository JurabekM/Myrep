# OmborAI — Mobil (Flutter + Kotlin, Android)

Android (8.0+, minSdk 26) uchun kassir va egasi ilovasi. Serversiz: desktop bilan bir xil protokol v2
(`../docs/sync-mqtt.md`): imzolangan operatsiyalar, MQTT (`broker.hivemq.com`, TLS 8883), SQLCipher baza.

## Tuzilishi

- `lib/src/sync/` — `crypto.dart` (konvert AES-256-GCM, canonical JSON, Ed25519 imzo), `identity.dart`
  (qurilma kaliti), `ops.dart` (turlar, ruxsatlar, `ts` formati), `mqtt_sync.dart` (PUBACK bilan nashr,
  persistent sessiya, xatolarga chidamli qabul).
- `lib/src/offline/local_db.dart` — SQLCipher baza va protokol qoidalari (desktop `store.py` bilan bir xil):
  imzo → muallif faolligi → ruxsat → tekshiruv → qo'llash; kutish buferi; bootstrap (snapshot).
- `lib/src/app_session.dart` — sessiya: juftlash, tasdiq so'rovi, snapshot, savdo, smena (har bir qurilmada),
  qaytarish (faqat egasi), tovar va foydalanuvchilar (faqat egasi), qurilmalarni boshqarish.
- `lib/src/domain/cart.dart` — savat. Savdo narxi katalogdan olinadi va qabul qilinadigan qurilmalarda tekshiriladi.
- `lib/src/theme.dart` — tungi (dark) mavzu, desktop bilan bir xil ranglar. Yorug' rejim yo'q.
- `lib/src/screens/` — kirish, bosh sahifa, kassa, tovarlar, qaytarish, foydalanuvchilar/qurilmalar, juftlash kodi.
- `android/app/src/main/kotlin/.../scanner/` — **native Kotlin**: CameraX + ML Kit shtrix-kod skaneri,
  Flutter'ga `uz.omborai/scanner` platform view sifatida ulanadi.

## Ishga tushirish

Talab: Flutter 3.47.x (Dart 3.13.x), Android SDK (platform 36, NDK 28.2.13676358), JDK 21 (Android Studio JBR).
Gradle/Kotlin JDK 25 bilan buziladi — JDK 21 ishlating.

```powershell
flutter pub get
flutter analyze
flutter test                                     # mahalliy testlar (broker talab qilmaydi)
flutter build apk --release --split-per-abi      # arm64-v8a: telefon uchun
```

Haqiqiy broker integratsiyasi (ixtiyoriy): `OMBORAI_TEST_MQTT_HOST`, `OMBORAI_TEST_MQTT_PORT` env o'zgaruvchilari.

## Muhim qoidalar

- Qurilma imzo kaliti (Ed25519 seed) Android Keystore (`flutter_secure_storage`) da saqlanadi.
- Operatsiya navbatdan faqat broker PUBACK bergach o'chiriladi.
- Egasi qurilmasi o'chiq bo'lsa, yangi qurilma do'kon ma'lumotini kutadi (`docs/sinov-telefon.md`).
- Baza fayli: `omborai_local_v2.db` (eski v1 bazadan ajratilgan).
