# Reliz checklist — Sector Verify 1.0.0

## 1. Qabul mezonlari (§10) holati — 2026-10-26
| ID | Mezon | Maqsad | Natija | Holat |
|---|---|---|---|---|
| AC-01 | Almashinuvni aniqlash, qamrov ≥ 70% | ≥ 95% | 99.0% (200), 98.1% (1000) simulyatsiya | ✅ |
| AC-02 | Noto'g'ri FAIL (xato yo'q) | ≤ 3% | 0.0% (200 va 1000) | ✅ |
| AC-03 | Azimut xatosi medianasi, qamrov ≥ 70% | ≤ 10° | 4.6° | ✅ |
| AC-04 | Qamrov yetarli emas → INCONCLUSIVE | 100% | 100% | ✅ |
| AC-05 | 3 chipset oilasida barqaror yig'ish | ≥ 0.5 Hz, 3/3 | — | ⏳ inson tasdig'i kutilmoqda (H1) |
| AC-06 | 30 daqiqalik sessiyada batareya | ≤ 15% | — | ⏳ inson tasdig'i kutilmoqda (H1/H2, `docs/BATTERY_TEST.md`) |
| AC-07 | Majburiy to'xtatishda yo'qolgan ma'lumot | ≤ 2 s | emulyatorda ✅ (`EncryptedDatabaseTest.forcedStopLosesAtMostTwoSeconds`), JVM ✅ | ✅ |
| AC-08 | Pilotda tasdiqlangan almashinuvlarni aniqlash | 100% | simulyatsiya namoyishi 100% (22/22); pilot — | ⏳ inson tasdig'i kutilmoqda (H2) |
| AC-09 | Bitta sessiyaning to'liq vaqti | ≤ 25 daqiqa | simulyator: halqa 275 m ≈ 20 daqiqa; pilot — | ⏳ inson tasdig'i kutilmoqda (H2) |
| AC-10 | `:core:analysis` qator qamrovi | ≥ 90% | 99.7% (Kover, `check` ichida `koverVerify`) | ✅ |
| AC-11 | Release build, Lint, detekt, CI | Yashil | `check`, `bundleRelease`, `assembleRelease`, `lintRelease` (0 muammo), detekt toza, CI yashil | ✅ |

## 2. Texnik tekshiruvlar (5–6-bosqich)
- [x] R8 minify + shrinkResources; ProGuard qoidalari (SQLCipher, kotlinx.serialization, enum'lar); release smoke test emulyatorda (CI).
- [x] 64-bit native kutubxonalar 16 KB sahifaga tekislangan (sqlcipher, graphics.path, datastore).
- [x] Imzolash: `keystore.properties` yoki `SV_KEYSTORE_*`; kalit repoda yo'q; kalitsiz release imzosiz va ogohlantirish bilan.
- [x] `versionName` git tag'dan (`sector-verify/v*`), `versionCode` = commit soni.
- [x] `allowBackup=false`, `dataExtractionRules` + `fullBackupContent` (hammasi chiqarilgan), cleartext taqiqlangan.
- [x] SQLCipher, 32 bayt parol Keystore AES-GCM bilan o'ralgan (`noBackupFilesDir`).
- [x] Eksport faqat FileProvider (`cache/exports`); loglarda koordinata/IMSI yo'q (ilova `Log` ishlatmaydi).
- [x] Lokal crash log + eksport; StrictMode debug'da; og'ir ishlar Default/IO da (yakuniy tahlil ~0.5 s, jonli ~10 ms JVM).
- [x] Ruxsatlar: §7 ro'yxati, `ACCESS_BACKGROUND_LOCATION` yo'q; har ruxsat uchun izoh, rad etilganda sozlamalarga o'tish.
- [x] Ilova ichida til almashtirish uchun AAB til bo'linishi o'chirilgan.
- [x] TODO/FIXME yo'q; qattiq kodlangan UI matni yo'q (texnik birliklar va raqam formatlaridan tashqari).
- [x] Hujjatlar: README, USER_GUIDE_uz/ru, ARCHITECTURE, ALGORITHM, PLAY_STORE, DISTRIBUTION_APK, privacy uz/ru/en, CHANGELOG.

## 3. Ochiq savollar / xavflar
1. **targetSdk 36** — Play 2026-08-31 dan talab qiladi; prompt 35 deydi. Play'ga chiqishdan oldin ko'tarish (yangi xatti-harakatlarni sinash bilan).
2. **Haqiqiy qurilmalar** (AC-05) — ba'zi chipsetlar qo'shni RSRP yoki TA bermasligi mumkin; `docs/DEVICES.md` H1 dan keyin to'ldiriladi.
3. **Kalibrlash** — standart chegaralar faqat simulyatsiyada tasdiqlangan; pilotdan (H2) keyin `sv-replay calibrate`.
4. Xatosiz simulyatsiyalarda sayt PASS ≈ 40% (sektor PASS ≈ 81%) — qolganlari INCONCLUSIVE; pilotda kuzatish kerak.

## 4. H3 — imzolash va tarqatish (faqat inson)
1. Release kalitini yarating va saqlang (`docs/DISTRIBUTION_APK.md` 1-qadam).
2. `keystore.properties` → `.\gradlew.bat clean check :app:bundleRelease :app:assembleRelease`.
3. `apksigner verify --print-certs app\build\outputs\apk\release\app-release.apk`; R8 `mapping.txt` ni arxivlang.
4. Kamida bitta haqiqiy telefonda release APK: import → o'lchov → hisobot → `sv-replay verify`.
5. Play: `docs/PLAY_STORE.md` (FGS deklaratsiyasi, Data safety, maxfiylik URL). Yoki APK: `docs/DISTRIBUTION_APK.md`.
6. Tag: `git tag sector-verify/v1.0.0 && git push origin sector-verify/v1.0.0`.
