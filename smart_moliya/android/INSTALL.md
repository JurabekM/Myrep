# O'rnatish va Build qilish (Android Studio)

## Talablar

- **Android Studio**: eng so'nggi barqaror versiya (Ladybug yoki undan yuqori)
- **JDK 17** (Android Studio bilan birga keladi)
- **Android SDK**: API 35 (compileSdk/targetSdk), minimum API 29 (Android 10)

## Ochish

1. Android Studio'ni oching → **File > Open** → `smart_moliya/android` papkasini tanlang (bu Gradle root — `settings.gradle.kts` shu yerda).
2. Gradle wrapper (`gradlew.bat`, `gradle/wrapper/gradle-wrapper.jar`) loyihaga kiritilgan — Android Studio ochilishida avtomatik sync boshlanadi, qo'shimcha hech narsa kerak emas.
3. Gradle sync tugagach: **Run ▶** tugmasini bosing (yoki `Shift+F10`), emulyator/qurilmani tanlang.

Loyiha **to'liq build qilinishi tasdiqlangan**: `gradlew assembleDebug` → BUILD SUCCESSFUL, barcha unit testlar o'tgan.

## Ikki xil APK (flavor'lar)

| Flavor | APK | Package | Tavsif |
|---|---|---|---|
| **online** | `app/build/outputs/apk/online/debug/app-online-debug.apk` | `com.smartmoliya.app` | Backend bilan ishlaydi (login, sync, to'lovlar, yutuqlar, oila) |
| **offline** | `app/build/outputs/apk/offline/debug/app-offline-debug.apk` | `com.smartmoliya.app.offline` | **To'liq avtonom** — serverga ulanmaydi, login yo'q (to'g'ridan-to'g'ri PIN). Barcha funksiyalar lokal: hamyonlar/tranzaksiyalar (seed kategoriyalar), hisobot + CSV eksport, naqd to'ldirish, yutuqlar (XP/streak/nishon/challenge), vazifalar-mukofotlar |

Ikkalasi bitta telefonga yonma-yon o'rnatiladi. Android Studio'da flavor tanlash: **Build Variants** paneli → `onlineDebug` yoki `offlineDebug`. Terminal: `gradlew assembleOfflineDebug` yoki `gradlew assembleOnlineDebug`.

Eslatma (online APK, jismoniy telefon): `10.0.2.2` faqat emulyator uchun. Telefonda sinash uchun kompyuter IP'sini `app/build.gradle.kts` dagi `API_BASE_URL`ga yozing (masalan `http://192.168.1.50:8000/`) va telefon bilan kompyuter bir Wi-Fi'da bo'lsin.

## Testlar

```bash
cd smart_moliya/android
./gradlew test          # JVM unit testlar (mapper, domain logika)
./gradlew connectedAndroidTest   # instrumented testlar (qurilma/emulyator talab qiladi)
```

## Terminal orqali build

```bash
cd smart_moliya/android
./gradlew assembleDebug      # yoki gradlew.bat assembleDebug (Windows)
```

APK: `app/build/outputs/apk/debug/app-debug.apk`

## Google Sign-In'ni yoqish (ixtiyoriy)

1. [Google Cloud Console](https://console.cloud.google.com) → APIs & Services → Credentials → **Web application** turidagi OAuth client ID yarating (Android turi emas — Credential Manager server client ID talab qiladi; qo'shimcha ravishda Android client ID ham yaratib SHA-1 kiritish kerak).
2. `app/build.gradle.kts` dagi `GOOGLE_SERVER_CLIENT_ID` qiymatiga client ID'ni yozing.
3. Backend `.env`ga ham xuddi shu ID'ni `GOOGLE_CLIENT_ID=` qatoriga yozing va `pip install google-auth`.
4. Rebuild — Login ekranida "Google bilan kirish" tugmasi paydo bo'ladi.

ID kiritilmagan bo'lsa tugma ko'rinmaydi — ilova SMS OTP va parol bilan to'liq ishlayveradi.

## Backend'ga ulanish

Ilova standart holatda `http://10.0.2.2:8000/` ga ulanadi (emulyatordan host mashinadagi backend). Backend'ni ishga tushirish: `backend/README.md` (uvicorn) yoki `docs/11_DEPLOYMENT.md` (Docker, u holda port `8080` bo'ladi — `core/network/NetworkModule.kt`dagi `BASE_URL`ni moslang).

## Eslatma: baza shifrlash (SQLCipher)

Lokal Room bazasi SQLCipher bilan shifrlangan. Agar qurilmada ilovaning **eski (shifrlash qo'shilishidan avvalgi)** versiyasi turgan bo'lsa, eski baza fayli ochilmaydi — ilovani o'chirib qayta o'rnating (dev bosqichida ma'lumot yo'qolishi muammo emas, hammasi serverdan qayta sync bo'ladi).

## Joriy holat

To'liq funksional ilova: Login/Register + PIN + biometrik, Dashboard, Hamyonlar, Tranzaksiyalar (offline-first), Hisobotlar (Pie chart, PDF/Excel eksport), Menyu (To'lovlar/Yutuqlar/Oila). Barcha ma'lumotlar backend bilan sinxronlanadi, internet bo'lmasa Room'dagi lokal nusxa ishlaydi.
