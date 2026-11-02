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

## 3. Play Console

- Maxfiylik siyosati: https://github.com/JurabekM/Myrep/blob/master/havoradar/docs/PRIVACY.md
- Data safety: ma'lumot yig'ilmaydi va uzatilmaydi; shahar koordinatasi prognoz uchun Open-Meteo'ga yuboriladi
  (foydalanuvchi joylashuvi emas).
- Health apps deklaratsiyasi: ilova tashxis qo'ymaydi, faqat ochiq prognoz asosida ma'lumot beradi.
