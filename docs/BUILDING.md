# Yig'ish qo'llanmasi

## Talablar

| Nima | Versiya | Izoh |
|---|---|---|
| Python | 3.13+ | Desktop |
| JDK | **21** | Android. JDK 25 da Kotlin/Gradle tushunarsiz xato bilan yiqiladi |
| Android SDK | 36 | `compileSdk`/`targetSdk` |
| Inno Setup | 6 | Windows installer (ixtiyoriy) |

JDK 21 alohida o'rnatilmagan bo'lsa, Android Studio'niki ishlatiladi:

```bash
export JAVA_HOME="C:/Program Files/Android/Android Studio/jbr"
```

---

## Desktop

### Bog'liqliklar

```bash
pip install -e ".[dev]"
```

### Ishga tushirish

```bash
python run.py
```

### Testlar

```bash
python -m pytest
```

### Installer

```bash
python packaging/build_windows.py
```

Bosqichlar: exe → **smoke test** → installer → manifest.

Smoke test exe'ni **vaqtinchalik papkaga ko'chirib** bajaradi. Bu ataylab:
avval test `dist/` ichidan yugurardi va resurs yo'li xatosini o'tkazib
yuborardi, chunki `dist/` repo ichida va noto'g'ri hisoblangan yo'l ham
tasodifan to'g'ri faylga tushardi.

Faqat exe kerak bo'lsa:

```bash
python packaging/build_windows.py --exe-only
```

---

## Android

### Modul tuzilmasi

| Modul | Turi | Nega shunday |
|---|---|---|
| `:crypto` | Kotlin/JVM | KAT testi emulyatorsiz, soniyalar ichida yuradi |
| `:domain` | Kotlin/JVM | Qoidalar Android SDK'ga bog'liq emas |
| `:core` | Kotlin/JVM | Formatlash |
| `:data` | Android kutubxona | Room |
| `:sync` | Android kutubxona | MQTT, Keystore |
| `:app` | Android ilova | Compose UI |

### Debug build

```bash
cd apps/android
./gradlew :app:assembleDebug
```

Debug build'da **namuna ma'lumot** avtomatik yoziladi (`DemoData`) —
reliz build'da bu kod umuman chaqirilmaydi.

### Reliz build

Avval imzo kaliti kerak:

```bash
keytool -genkeypair -v -keystore distribos-release.keystore \
  -alias distribos -keyalg RSA -keysize 4096 -validity 10000
```

Keyin `apps/android/keystore.properties`:

```properties
storeFile=distribos-release.keystore
storePassword=<parol>
keyAlias=distribos
keyPassword=<parol>
```

```bash
./gradlew :app:assembleRelease :app:bundleRelease
```

> **Kalitsiz reliz build ATAYLAB yiqiladi.** Aks holda debug kalit bilan
> imzolangan APK «reliz» deb tarqalib ketishi mumkin — u Play'ga
> yuklanmaydi va xavfsiz emas.

> **Kalitni yo'qotmang.** Uni yo'qotish ilovani Play'da **yangilab
> bo'lmasligini** anglatadi. Kalit va parol repositoryda YO'Q va hech
> qachon bo'lmasligi kerak.

### Testlar

```bash
./gradlew :crypto:test :domain:test
```

`:crypto` testlari Python bilan **baytma-bayt** moslikni tekshiradi.
Ular yiqilsa — telefon desktop yuborgan xabarni ocholmaydi.

---

## Moslik vektorlarini yangilash

Python tomonida kripto yoki qoidalar o'zgarsa, vektorlarni qayta
generatsiya qiling va Kotlin testini yuriting:

```bash
python tools/gen_des1_kat.py
python tools/gen_rules_parity.py
cd apps/android && ./gradlew :crypto:test :domain:test
```

Vektorlar ikkala tomon uchun **bitta manba** — ular
`tests/interoperability/` da yotadi va Android resurslariga nusxalanadi.

---

## Ekran suratlari

```bash
python tools/capture_screens.py
```

> Bu skript `QT_QPA_PLATFORM=offscreen` ni **majburlamaydi**. Windows'da
> offscreen platformasida `QFontDatabase` BO'SH bo'ladi (0 shrift oilasi)
> va butun matn «tofu» kvadratchalarga aylanadi — ya'ni surat vizual
> tekshiruv uchun yaroqsiz.

---

## Tez-tez uchraydigan muammolar

| Alomat | Sabab |
|---|---|
| Kotlin: `What went wrong: 25.0.2` | JDK 25 ishlatilyapti, 21 kerak |
| `Invalid file path` (Gradle) | `local.properties` da teskari chiziq — oldinga chiziq ishlating |
| Configuration cache xatosi | AGP 8.13 bilan to'qnashadi; `gradle.properties` da o'chirilgan |
| exe ishga tushmaydi, xato ham yo'q | `--windowed` build'da istisno ko'rinmas dialogga aylanadi; `logs/distribos.log` ni qarang |
| Vendor manifest testi toza klonda yiqiladi | `.gitattributes` da `-text` yo'q — CRLF konvertatsiyasi baytlarni o'zgartirgan |
