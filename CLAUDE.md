# Baraka Dastur — AI-dasturchi uchun

Har sessiya boshida `docs/SPEC.md` ning 3, 4, 5, 6, 12-bo'limlarini va `docs/MVP_PLAN.md` ning 0-bo'limini o'qi. SPEC 4-bo'lim (ADR) qat'iy.

- Vazifalar va qabul mezonlari: `docs/MVP_PLAN.md` (17 vazifa: 1–15 + 9A, 14A; 1–6-qonunlar; `docs/MVP1_KICKOFF.md` o'rnini bosadi — tarix uchun qoldirilgan). Holat: `docs/MVP_PLAN_STATUS.md`. Har sessiyada faqat bitta vazifa.
- Pul algoritmlari va umumiy oltin test vektorlari (`spec/test-vectors/`, desktop bilan bitma-bit): `docs/DESKTOP_PROMPT.md` 4–5-bo'limlar — mobil CI uchun ham majburiy.
- Yangi jadval kerak bo'lsa — Drift sxema versiyasini oshir va migratsiya testini yoz. Pul hisoblari faqat `core/money` orqali.
- Kod, identifikatorlar va commit xabarlari inglizcha; izohlar, hujjatlar va UI matnlari o'zbekcha.
- UI matnlari faqat ARB orqali (`lib/app/l10n/arb/app_uz.arb` — shablon, `app_ru.arb`).
- Grafika va ikonkalar islom tamoyillariga mos: `docs/DESIGN_GUIDELINES.md` (piggy bank, jonzot tasviri, qimor/alkogol — taqiq).
- Har vazifa oxirida `docs/CHANGELOG.md` va `docs/OPEN_QUESTIONS.md` yangilanadi.

## Buyruqlar (Windows: Flutter 3.32.5, JDK 21 — Android Studio JBR)

```
flutter pub get
dart run pigeon --input pigeons/security_api.dart      # Pigeon kontrakti o'zgarsa
dart run pigeon --input pigeons/reminder_api.dart
dart run pigeon --input pigeons/widget_api.dart
dart run build_runner build --delete-conflicting-outputs
flutter analyze
flutter test
flutter test test/vectors                               # umumiy oltin vektorlar (spec/test-vectors)
flutter build apk --debug
cd android && ./gradlew :app:testDebugUnitTest          # Kotlin JUnit (JAVA_HOME = JDK 21)
```

Host testlari Drift uchun SQLite kutubxonasini talab qiladi: Windows'da PATH'dagi `sqlite3.dll`
yoki Python o'rnatmasidagi `DLLs/sqlite3.dll` avtomatik topiladi (`test/flutter_test_config.dart`),
kerak bo'lsa `SQLITE3_LIBRARY` muhit o'zgaruvchisi bilan beriladi.

`core/money` qamrovi: `flutter test --coverage && python tools/coverage_report.py lib/core/money --min 95`.

Sxema o'zgarsa: `schemaVersion` +1 → `dart run drift_dev make-migrations` → `onUpgrade` qadami →
`test/drift/default/migration_test.dart` dagi `upgradePaths` ga juftlik.

Yangi modul bosh ekranga kartani `lib/features/home/presentation/home_slots.dart` dagi
`homeCardSlots` / `homeSections` ro'yxatiga qo'shadi. Yangi ilova hodisasi: `TaskTrigger` ga kod
qo'shiladi (+ `docs/content_schema.json`), hodisa joyida `recordTaskEvent(ref, …)` chaqiriladi.

O'zbekcha matn (ARB, kontent JSON, testlar): `oʻ/gʻ` — U+02BB, tutuq — U+02BC, ASCII `'` emas.
Tekshirish/tuzatish: `python tools/uz_orthography.py [--check]`.

Widget testlarida drift: bazaga `tester.runAsync` ICHIDA murojaat qilmang (ijrochi real zonaga
bog'lanib, keyingi so'rovlar osiladi). Xizmatlarni test zonasida to'g'ridan-to'g'ri `await` qiling.
`enterText` dan keyin tugmani bosishdan oldin `pump()` qiling (aks holda tugma hali o'chiq).

Generatsiya qilingan fayllar (`*.g.dart`, `*.freezed.dart`, `*.pigeon.dart`, `SecurityApi.g.kt`,
`lib/app/l10n/gen/`) repoda saqlanadi; CI ularning dolzarbligini tekshiradi. Ularni `dart format`
qilma — CI format qadami ularni chetlab o'tadi.

## Emulyator

`powershell -File tools/start_emulator.ps1` bilan ishga tushir (oyna ekranga sig'ishini o'lchaydi).
Emulyatorda joy kam bo'lsa, debug APK (~200 MB) o'rnatilmaydi —
`flutter build apk --release --target-platform android-x64` (~36 MB) ishlat.
Integration testni ham shunday: `flutter build apk --release --target-platform android-x64 -t integration_test/<fayl>.dart`,
o'rnatib ishga tushir va natijani `adb logcat -s flutter:I` dan o'qi («All tests passed!»).
