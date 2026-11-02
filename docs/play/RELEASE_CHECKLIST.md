# ROSTOR-2 — reliz chek-listi (Google Play)

Har reliz shu tartibda. ✋ — faqat siz bajarasiz (parol, akkaunt, to'lov); qolganini Claude bajarishi mumkin.

## 0. Kod tayyor

- [ ] `cd app && flutter analyze && flutter test`
- [ ] `cd app/android && ./gradlew :app:testDebugUnitTest` (`JAVA_HOME` = Android Studio JBR)
- [ ] `py tools/rostor_report/test_rostor_report.py`
- [ ] `py tools/store/check_listing.py`
- [ ] `app/pubspec.yaml` da `version` oshirilgan (versionCode har yuklashda kattaroq bo'lishi shart)
- [ ] Baza o'zgargan bo'lsa: `registry/registry.json` da `db_version` oshirilgan va `py tools/rostor_db/rostor_db.py build`

## 1. ✋ Upload kaliti (bir marta)

```powershell
powershell -ExecutionPolicy Bypass -File tools/create_upload_key.ps1
```

Natija `C:\keys\rostor2\upload\` da: `upload.jks`, `key.properties` (parol — ochiq matn, papka repodan tashqarida),
`upload-cert-sha256.txt`. Papkani ikki joyga zaxiralang, parolni alohida saqlang. `key.properties` ni chatga,
repoga yoki skrinshotga qo'ymang.

## 2. Imzolangan reliz yig'ish

```powershell
powershell -ExecutionPolicy Bypass -File tools/build_release.ps1 -SigningProperties C:\keys\rostor2\upload\key.properties
```

Natija `release/<versiya>/`: `ROSTOR-2-<versiya>.aab` (Play), ABI bo'yicha APK'lar (sinov), `mapping-*.txt`,
`symbols-*.zip` (crash'ni ochish uchun — saqlang), `SHA256SUMS.txt`. Skript oxirida har APK
`tools/check_release.py` dan o'tadi: INTERNET yo'q, kutilgan ruxsatlar, baza imzosi, debuggable emas, debug kaliti emas.

## 3. Qurilmada sinov

- [ ] arm64 APK'ni haqiqiy telefonga o'rnatib: bosh ekran, audit, APK Qalqon (Telegram'dan fayl), Qo'ng'iroq Qalqoni
      (rolni yoqish, haqiqiy qo'ng'iroq), xabar tekshiruvi ("Ulashish"), hisobot yaratish va yuborish, test, "haqiqiymi?"

## 4. ✋ Play Console

- [ ] Ilova yaratish (paket `uz.rostor.rostor2`), Play App Signing'ni qabul qilish
- [ ] [PLAY_LISTING.md](PLAY_LISTING.md): matnlar (uz asosiy, ru, en), `tools/store/play_icon_512.png`,
      `tools/store/feature_graphic_1024x500.png`, `tools/store/screenshots/uz/*.png`
- [ ] Maxfiylik siyosati URL ([PRIVACY_POLICY.md](PRIVACY_POLICY.md) to'ldirilib, ommaviy joyda)
- [ ] [PLAY_CONSOLE.md](PLAY_CONSOLE.md): Data safety, QUERY_ALL_PACKAGES deklaratsiyasi, kontent reytingi,
      maqsadli auditoriya (18+), boshqa deklaratsiyalar
- [ ] AAB'ni avval **Internal testing** ga yuklash, keyin Production

## 5. Rasmiy imzo izini e'lon qilish (birinchi yuklashdan keyin)

- [ ] Console → App integrity → App signing key certificate → SHA-256 ni oling
- [ ] README "Rasmiy imzo izi" bandiga va reliz eslatmasiga yozing
- [ ] Play uchun AAB'ni `-NoApk -ExpectedSignatureSha256 <shu xesh>` bilan yig'ing ("haqiqiymi?" ekranidagi ichki
      tekshiruv). APK'lar upload kaliti bilan imzolanadi — ular uchun bu xesh mos kelmaydi, shuning uchun sinov
      APK'larini xeshsiz (yoki `upload-cert-sha256.txt` bilan) alohida yig'ing
- [ ] Internal testing'dan o'rnatilgan nusxada "haqiqiymi?" ekranidagi iz shu xeshga tengligini tekshiring

## 6. Tozalash

- [ ] `cd app && flutter clean`; eski `release/<versiya>/` papkalarini faqat zaxiradan keyin o'chiring
