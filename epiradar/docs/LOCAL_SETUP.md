# EpiRadar — lokal muhit (Windows)

Loyiha to'liq GitHub'da: `JurabekM/Myrep`, papka `epiradar/`. Bu yo'riqnoma Windows 10/11 kompyuterda
yig'ish, testlash, emulyatorda ishga tushirish va Claude Code bilan lokal ishlash uchun.

## 1. Kerakli dasturlar (bir marta)

| Dastur | Versiya | Izoh |
|---|---|---|
| Git for Windows | oxirgi | Git Bash ham o'rnatiladi (emulyator skripti uchun) |
| Android Studio | oxirgi | ichida JDK 21 (`jbr`) va Android SDK |
| Flutter | **3.47.6** (aniq shu versiya — CI bilan bir xil) | `C:\dev\flutter` kabi bo'sh joysiz yo'lga |

**Android Studio → Settings → Languages & Frameworks → Android SDK** da belgilang:
- SDK Platforms: **Android 16 (API 36)**
- SDK Tools: **Android SDK Build-Tools 36**, **Platform-Tools**, **Emulator**, **Command-line Tools (latest)**

NDK va CMake'ni Gradle birinchi yig'ishda o'zi yuklaydi.

**Flutter (PowerShell):**

```powershell
git clone https://github.com/flutter/flutter.git -b 3.47.6 C:\dev\flutter
```

Keyin `C:\dev\flutter\bin` ni **PATH** ga qo'shing (Windows qidiruvi → «Environment Variables»).
Shu yerda yana ikkita o'zgaruvchi:
- `JAVA_HOME` = `C:\Program Files\Android\Android Studio\jbr`
- PATH ga `%LOCALAPPDATA%\Android\Sdk\platform-tools` (adb uchun)

Yangi PowerShell oynasida tekshiring:

```powershell
flutter doctor --android-licenses
```

```powershell
flutter doctor
```

«Android toolchain» va «Android Studio» yonida ✓ bo'lishi kerak (Windows desktop/Chrome qatorlari shart emas).

## 2. Emulyator

1. Windows'da apparat tezlashtirish: **«Turn Windows features on or off» → Windows Hypervisor Platform** ni
   yoqing va kompyuterni qayta yuklang (BIOS'da virtualizatsiya — Intel VT-x / AMD-V — yoqilgan bo'lsin).
2. Android Studio → **Device Manager → Create Virtual Device** → Pixel 8 → **API 36, x86_64, Google APIs**.
3. Ishga tushiring (▶). Bildirishnoma ruxsati bo'lmagan eski Android'ni sinash uchun ikkinchi qurilma: API 29.

## 3. Loyihani olish

```powershell
git clone https://github.com/JurabekM/Myrep.git C:\dev\Myrep
```

Yoki mavjud nusxada eng so'nggi o'zgarishlar:

```powershell
cd C:\dev\Myrep
```

```powershell
git pull
```

PR hali birlashtirilmagan bo'lsa, ish branch'i: `git checkout claude/beautiful-feynman-81p1kv`.

## 4. Yig'ish va testlar (PowerShell, `C:\dev\Myrep\epiradar` ichida)

Kotlin yadro testlari (Gradle wrapper o'zi yuklanadi):

```powershell
cd engine; .\gradlew.bat test; cd ..
```

Flutter:

```powershell
flutter pub get
```

```powershell
flutter analyze
```

```powershell
flutter test
```

Emulyatorda ishga tushirish (emulyator yoqilgan bo'lsin):

```powershell
flutter run
```

Ishlayotgan ilovada `r` — tezkor qayta yuklash (hot reload), `q` — chiqish.

Telefonda sinash: telefonda **Dasturchi sozlamalari → USB debugging** ni yoqing, USB bilan ulang,
`flutter devices` da ko'rinsin, keyin `flutter run`. Yoki APK:

```powershell
flutter build apk --release --split-per-abi
```

Natija: `build\app\outputs\flutter-apk\app-arm64-v8a-release.apk` (zamonaviy telefonlar uchun).
Kalitsiz bu APK debug kalit bilan imzolanadi — faqat o'zingiz sinash uchun (Play uchun: [RELEASE.md](RELEASE.md)).

## 5. To'liq emulyator tekshiruvi

Git Bash'da (emulyator yoqilgan holda):

```bash
cd /c/dev/Myrep/epiradar && ./tool/emulator_test.sh
```

Skript: Kotlin instrumental testlar (fon sinxronlash jonli internet bilan, bildirishnomalar, WorkManager) →
Flutter `integration_test` (to'liq UI oqimi) → ilovani foydalanuvchidek ochib ekran matni, skrinshot
(`build/device/`) va crash tekshiruvi. Emulyator nomi boshqacha bo'lsa: `DEVICE=emulator-5556 ./tool/emulator_test.sh`.

## 6. Fonda ishlashni sinash (qo'lda)

- Ilovani oching, onboarding'dan o'ting, keyin yoping.
- Fon sinxronlashni kutmasdan ishga tushirish: avval WorkManager vazifasining raqamini toping
  (`JobInfo #<raqam>/... uz.epiradar.app/androidx.work...` qatoridagi raqam):

```bash
adb shell dumpsys jobscheduler | grep "uz.epiradar.app/androidx.work"
```

  keyin shu raqam bilan:

```bash
adb shell cmd jobscheduler run -f uz.epiradar.app RAQAM
```

  Bunisiz ham bo'ladi: Sozlamalar'da yangilash chastotasini 1 soatga qo'ying va kuting.
- Bosh ekranga vidjet qo'shing: uzoq bosish → Widgets → EpiRadar.
- Xiaomi/Samsung kabi telefonlarda: Sozlamalar → Batareya → EpiRadar → «Cheklovsiz», aks holda tizim fon
  ishini to'xtatishi mumkin.

## 7. Claude Code bilan lokal ishlash

Claude desktop ilovasini (yoki `claude` CLI) o'rnating va **`C:\dev\Myrep` papkasini oching**. Myrep va
`epiradar/` dagi `CLAUDE.md` fayllari loyiha qoidalari va buyruqlarini o'zi o'qiydi. Lokal sessiyada Claude
emulyator, `adb`, `flutter run` va telefoningiz bilan to'g'ridan-to'g'ri ishlay oladi.

Birinchi so'rov uchun namuna:

> epiradar: emulyatorda `./tool/emulator_test.sh` ni ishga tushir, natijalarni tahlil qil va topilgan
> muammolarni tuzat.

## Muammolar

| Belgi | Yechim |
|---|---|
| `flutter doctor`: «cmdline-tools component is missing» | SDK Tools'da Command-line Tools (latest) ni o'rnating |
| Gradle: «JAVA_HOME is not set» | `JAVA_HOME` ni Android Studio `jbr` papkasiga qo'ying, yangi terminal oching |
| Emulyator juda sekin / ishga tushmaydi | Windows Hypervisor Platform va BIOS virtualizatsiyasini tekshiring |
| `adb: command not found` (Git Bash) | PATH ga `platform-tools`; Git Bash'ni qayta oching |
| Yo'lda bo'sh joy yoki kirill harflari bilan xatolar | Loyiha va Flutter'ni `C:\dev\...` kabi oddiy yo'lga qo'ying |
