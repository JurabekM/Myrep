# HavoRadar — reliz yo'riqnomasi

## 1. Yuklash kaliti (upload key) — bir marta

Kalit **faqat sizda** saqlanadi: repoga, chatga yoki bulutga yuklanmaydi.

```bash
keytool -genkeypair -v -keystore havoradar-upload.jks -alias upload -keyalg RSA -keysize 4096 -validity 10000 -dname "CN=HavoRadar, O=JurabekM, C=UZ"
```

Google Play'da **Play App Signing** yoqilgan bo'lsin (yangi ilovalarda standart).

## 2. Lokal reliz

`havoradar/android/key.properties` yarating (namuna: `key.properties.example`, fayl gitignore'da):

```properties
storeFile=/mutlaq/yo'l/havoradar-upload.jks
storePassword=...
keyAlias=upload
keyPassword=...
```

```bash
cd havoradar && HAVORADAR_REQUIRE_RELEASE_SIGNING=1 flutter build appbundle --release --obfuscate --split-debug-info=build/symbols
```

`HAVORADAR_REQUIRE_RELEASE_SIGNING=1` — kalit topilmasa yig'ish to'xtaydi (debug kalit bilan imzolangan faylni
tasodifan Play'ga yuklamaslik uchun). CI'da kalit muhit o'zgaruvchilaridan olinadi: `HAVORADAR_KEYSTORE_FILE`,
`HAVORADAR_KEYSTORE_PASSWORD`, `HAVORADAR_KEY_ALIAS`, `HAVORADAR_KEY_PASSWORD`.

## 3. CI orqali reliz (tavsiya etiladi)

GitHub → Settings → Secrets and variables → Actions'ga qo'shing:

| Secret | Qiymat |
|---|---|
| `HAVORADAR_UPLOAD_KEYSTORE_B64` | `base64 -w0 havoradar-upload.jks` natijasi |
| `HAVORADAR_KEYSTORE_PASSWORD` | keystore paroli |
| `HAVORADAR_KEY_ALIAS` | `upload` |
| `HAVORADAR_KEY_PASSWORD` | kalit paroli |

Keyin `pubspec.yaml` dagi `version` ni oshiring (masalan `1.0.1+2`: `+` dan keyingi son har relizda o'sishi shart),
commit qiling va teg qo'ying. Teg pubspec versiyasiga mos bo'lishi kerak, aks holda workflow to'xtaydi:

```bash
git tag havoradar-v1.0.1 && git push origin havoradar-v1.0.1
```

`havoradar-release` workflow'i testlarni o'tkazadi, imzolangan AAB va APK'larni (arm64, armv7) yig'adi, debug kalit
bilan imzolanmaganini tekshiradi va `havoradar-release` artefaktiga joylaydi (Actions → run → Artifacts).
Obfuskatsiya belgilari `havoradar-symbols` artefaktida — Play Console'dagi crash'larni o'qish uchun saqlang.

## 4. Play Console

Do'kon matnlari, grafika, Data safety javoblari va deklaratsiyalar: [PLAY_STORE.md](PLAY_STORE.md).

- Maxfiylik siyosati: https://github.com/JurabekM/Myrep/blob/master/havoradar/docs/PRIVACY.md
- Data safety: ma'lumot yig'ilmaydi va uzatilmaydi; shahar koordinatasi prognoz uchun Open-Meteo'ga yuboriladi
  (foydalanuvchi joylashuvi emas).
- Health apps deklaratsiyasi: ilova tashxis qo'ymaydi, faqat ochiq prognoz asosida ma'lumot beradi.
