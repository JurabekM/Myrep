# EpiRadar — reliz yo'riqnomasi

## 1. Yuklash kaliti (upload key) — bir marta

Kalit **faqat sizda** saqlanadi: repoga, chatga yoki bulutga yuklanmaydi. Uni yo'qotsangiz, Play App Signing
orqali tiklash mumkin, lekin parolni va faylni xavfsiz joyda (parol menejeri + zaxira) saqlang.

```bash
keytool -genkeypair -v -keystore epiradar-upload.jks -alias upload -keyalg RSA -keysize 4096 -validity 10000 -dname "CN=EpiRadar, O=JurabekM, C=UZ"
```

Google Play'da **Play App Signing** yoqilgan bo'lsin (yangi ilovalarda standart): Google ilovani o'z kaliti bilan
imzolaydi, siz faqat yuklash kalitini saqlaysiz.

## 2. Lokal reliz

`epiradar/android/key.properties` yarating (namuna: `key.properties.example`, fayl gitignore'da):

```properties
storeFile=/mutlaq/yo'l/epiradar-upload.jks
storePassword=...
keyAlias=upload
keyPassword=...
```

```bash
cd epiradar && EPIRADAR_REQUIRE_RELEASE_SIGNING=1 flutter build appbundle --release --obfuscate --split-debug-info=build/symbols
```

`EPIRADAR_REQUIRE_RELEASE_SIGNING=1` — kalit topilmasa yig'ish to'xtaydi (debug kalit bilan imzolangan faylni
tasodifan Play'ga yuklamaslik uchun). Natija: `build/app/outputs/bundle/release/app-release.aab`.
`build/symbols/` ni saqlab qo'ying — Play Console'dagi crash'larni o'qish uchun kerak.

## 3. CI orqali reliz (tavsiya etiladi)

GitHub → Settings → Secrets and variables → Actions'ga qo'shing:

| Secret | Qiymat |
|---|---|
| `EPIRADAR_UPLOAD_KEYSTORE_B64` | `base64 -w0 epiradar-upload.jks` natijasi |
| `EPIRADAR_KEYSTORE_PASSWORD` | keystore paroli |
| `EPIRADAR_KEY_ALIAS` | `upload` |
| `EPIRADAR_KEY_PASSWORD` | kalit paroli |

Keyin `pubspec.yaml` dagi `version` ni oshiring (masalan `1.0.1+2` — `+` dan keyingi son har relizda o'sishi shart)
va teg qo'ying:

```bash
git tag epiradar-v1.0.1 && git push origin epiradar-v1.0.1
```

`epiradar` workflow'idagi `release` job imzolangan AAB va APK'larni yig'adi, imzoni tekshiradi va
`epiradar-release` artefaktiga joylaydi (Actions → run → Artifacts).

## 4. Play Console

Do'kon matnlari, Data safety javoblari va deklaratsiyalar: [PLAY_STORE.md](PLAY_STORE.md).
Maxfiylik siyosati havolasi: https://github.com/JurabekM/Myrep/blob/master/epiradar/docs/PRIVACY.md

Tavsiya etilgan tartib: **Internal testing** (o'zingiz va 2–3 kishi, real telefonlar) → **Closed testing** →
**Production**. Yangi shaxsiy dasturchi akkauntlari uchun Google production'dan oldin yopiq testni talab qilishi
mumkin — Play Console ko'rsatmalariga qarang.
