# Reliz tekshiruv ro'yxati (MVP-1)

Har bir reliz (ichki sinov, yopiq beta, Play Market) oldidan ketma-ket bajariladi.
Belgilanmagan band — reliz yo'q.

## 1. Koddan tashqarida hal qilinadigan masalalar (MVP_PLAN)

- [x] Kontent va brend: tashqi litsenziya kerak emas — mustaqil kontent (2026-10-23).
- [ ] Diniy matnlar va sheriklik shablonlarini ulamo tekshirgan
      (`religiousReviewStatus` / `reviewStatus` → `APPROVED`).
- [ ] Tilxat va shartnoma shablonlarini yurist ko'rgan.
- [ ] Maxfiylik siyosati (shaxsiy ma'lumotlar to'g'risidagi qonun) va Play Market
      moliyaviy ilovalar talablari (Data safety shakli: ma'lumot qurilmadan chiqmaydi,
      tarmoq ruxsati yo'q).
- [x] Vaqtinchalik `applicationId` yakuniy nomga almashtirilgan: `uz.barakadastur.app` (2026-10-23).
      Play'ga birinchi yuklashdan keyin o'zgartirib bo'lmaydi. Eski `uz.barakadaftari.app` o'rnatmasi
      yangilanmaydi — alohida ilova; ma'lumotni zaxira nusxa orqali ko'chirish kerak.

## 2. Imzolash (repodan TASHQARIDA)

Kalit va parollar repoda saqlanmaydi (`android/.gitignore`: `key.properties`, `*.jks`,
`*.keystore`).

1. Kalit bir marta yaratiladi va **ikki joyda** zaxiralanadi (kalit yo'qolsa ilovani
   yangilab bo'lmaydi):

   ```
   keytool -genkeypair -v -keystore C:\keys\baraka\upload.jks -alias baraka ^
     -keyalg RSA -keysize 4096 -validity 10000
   ```

2. `C:\keys\baraka\key.properties` (repodan tashqarida):

   ```
   storeFile=C:/keys/baraka/upload.jks
   storePassword=...
   keyAlias=baraka
   keyPassword=...
   ```

3. Yo'l `BARAKA_SIGNING_PROPERTIES` muhit o'zgaruvchisi, `-PsigningProperties=` yoki
   `tools/build_release.ps1 -SigningProperties ...` orqali beriladi. Fayl bo'lmasa
   release **debug kaliti** bilan imzolanadi — bunday APK faqat sinov uchun.
4. Imzo xeshi (`apksigner verify --print-certs`) yaxlitlik tekshiruviga beriladi:
   `-PexpectedSignatureSha256=<SHA-256>` (aks holda «imzo sozlanmagan» signali).

> **Diqqat:** debug kaliti bilan o'rnatilgan ilovani release kaliti bilan imzolangan
> versiya ustidan yangilab bo'lmaydi — avval ilova o'chiriladi. Ma'lumotni saqlash
> uchun oldin **Sozlamalar → Zaxira nusxa** bilan eksport qiling, keyin tiklang.

## 3. Yig'ish

```
powershell -File tools/build_release.ps1 -SigningProperties C:\keys\baraka\key.properties
```

Skript ABI bo'yicha APK'lar va Play uchun AAB ni yig'adi; natija `build/release/<versiya>/` da
(`-NoBundle` — faqat APK).

- [ ] Dart `--obfuscate`; belgilar har build uchun alohida (`symbols-apk.zip`, `symbols-aab.zip`) —
      **har reliz uchun arxivlanadi** (crash stack'ini `flutter symbolize -i <stack> -d <symbols>`
      bilan ochish uchun).
- [ ] Android R8: `isMinifyEnabled` + `isShrinkResources`; `mapping-apk.txt` / `mapping-aab.txt`
      ham arxivlanadi (`retrace`; Play Console'ga AAB bilan `mapping-aab.txt` yuklanadi).
- [ ] `SHA256SUMS.txt` — barcha artefaktlar xeshi.
- [ ] `pubspec.yaml` dagi `version` oshirilgan (`versionCode` har yuklashda +1).

## 4. Avtomatik tekshiruvlar (CI bilan bir xil)

- [ ] Pigeon, gen-l10n, build_runner, make-migrations — qayta generatsiya farq bermaydi.
- [ ] `dart format --set-exit-if-changed` (generatsiya qilinganlardan tashqari).
- [ ] `flutter analyze --fatal-infos`, `python tools/uz_orthography.py --check`.
- [ ] `flutter test --coverage`; `python tools/coverage_report.py lib/core/money --min 95`.
- [ ] Kotlin JUnit: `cd android && ./gradlew :app:testDebugUnitTest` (JDK 21).
- [ ] Yakuniy E2E qurilmada (`integration_test/full_e2e_test.dart`, release x64):
      logcat'da «All tests passed!».
- [ ] Shifrlangan baza testi qurilmada (`integration_test/encrypted_db_test.dart`).

## 5. Release APK qurilmada (qo'lda)

- [ ] Ishga tushadi, logcat'da `FATAL EXCEPTION` yo'q (R8 qoidalari: yangi plagin
      qo'shilganda albatta tekshiring — Vazifa 15 da `file_selector` release'ni
      ishga tushishda yiqitgan, olib tashlangan).
- [ ] Obfuskatsiya: `libapp.so` da Dart sinf nomlari yo'q (masalan `BackupService`),
      `classes.dex` da Kotlin klasslari qisqargan (WorkManager ishchilari bundan
      mustasno — nomi bilan topiladi).
- [ ] `FLAG_SECURE`: moliyaviy ekranlarda `adb exec-out screencap` qora; «So'nggi
      ilovalar» ko'rinishida mazmun yashirin.
- [ ] Qulf: sovuq start → PIN; fonga o'tib qaytganda qulf; biometrika (bo'lsa).
- [ ] Yangi o'rnatish: PIN → onboarding (5 ekran) → qarz bor → «Qarzlar».
- [ ] Eski versiya ustidan yangilash: migratsiya, ma'lumotlar joyida, onboarding
      chiqmaydi.
- [ ] Zaxira: eksport (ulashish oynasi, `.bkd`), import — noto'g'ri parol, boshqa fayl,
      boshqa sxema xatolari; to'g'ri parol bilan to'liq tiklash.
- [ ] Bildirishnoma ruxsati so'raladi; majburiyat va daromad eslatmalari keladi.
- [ ] Kelishuv imzolangach yillik yangilash eslatmasi rejalashtiriladi va qurilma
      qayta yoqilgandan keyin ham saqlanadi (`dumpsys jobscheduler`, ~30 s kuting).
- [ ] 7-qonun: taklif tekshiruvi (besh belgi, toifalar, piramida), «pul qo'yaman»
      maslahatchisiz va 24 soatdan oldin o'chiq; «Katta summa tushdimi?» — devor va
      hunar taqsimoti, qorovulga qo'yish.
- [ ] Sovuq start: `adb shell am start -W -n uz.barakadastur.app/uz.barakadaftari.app.MainActivity`
      (`TotalTime`, o'rnatishdan keyingi birinchisi hisobga olinmaydi) — o'rta segment
      telefonda < 2 s.
- [ ] Katta shrift (Sozlamalar → Shrift o'lchami eng katta) va TalkBack bilan asosiy
      oqim: daromad, xarajat, qulf.
- [ ] Grafika va ikonkalar `docs/DESIGN_GUIDELINES.md` ga mos (cho'chqa-banka, jonzot,
      qimor/alkogol yo'q) — `test/design/` testlari yashil.

## 6. Hujjatlar

- [ ] `docs/CHANGELOG.md`, `docs/MVP_PLAN_STATUS.md`, `docs/OPEN_QUESTIONS.md` yangilangan.
- [ ] Reliz yozuvi: versiya, commit, APK SHA-256, belgilar va `mapping.txt` arxivi joyi.

## 7. Sinov natijalari (2026-10-13, emulyator — tuzatishdan oldin)

Artefakt: `build/app/outputs/flutter-apk/app-arm64-v8a-release.apk` (30,2 MB, 13.10.2026 19:00).
Kod: commit `177b018`; sinovda ishchi nusxada faqat hujjat va integratsiya testi o'zgardi.
Imzo: `CN=Android Debug` — **reliz bloker** (OPEN 97, 122). Qurilma: Android 16 (API 36)
emulyator, x86_64, ARM tarjima bilan (arm64 APK). Haqiqiy telefon sinalmagan.

| Band | Natija | Izoh |
|---|---|---|
| Ishga tushish, FATAL/ANR (butun sessiya) | PASS | `FATAL EXCEPTION` = 0, `ANR` = 0 |
| Emulyator ogohlantirishi | PASS | «Qurilmada xavf belgilari» — emulyator aniqlanadi |
| Qulf: fonda 2+ daqiqa | PASS | Qulf ekrani, PIN bilan ochildi |
| Kelajagim pul olish (friction + PIN) | PASS | 23 000 → 18 000 soʻm |
| Noto'g'ri PIN xabari | NOT TESTED | oldingi test kutilgan matn noto'g'ri edi (ARB: «Kod mos kelmadi…») |
| Kelishuv: 9/9, uch imzo, kelishuv PDF | PASS | `kelishuv.pdf` ulashish oynasida |
| Kelishuv tahriri: 6- va 7-savol | FAIL | OPEN 113, 114 — matn yo'qoladi |
| Qarz tilxati PDF | PASS | `qarz_tilxati.pdf` |
| Tilxat va kelishuv imzolari sinxron emas | FAIL | OPEN 116 |
| Sherikchilik: yaratish (6/6), 3 imzo, boshlash, davr yopish 50/50 | PASS | `sheriklik_hisoboti.pdf` ham chiqdi |
| Imzolangan tomon qayta imzolay oladi | FAIL | OPEN 117 |
| Bo'sh imzo bilan «Imzolash» | FAIL (UX) | OPEN 118 |
| Buyout to'lovi | PASS / FAIL | jurnalda ko'rindi; kassada ko'rinmadi (OPEN 123) |
| Kassa: yozuv qo'shish | PASS | Kirim 200 000 soʻm, sof foyda ko'rsatildi |
| Bosh sahifa placeholder matni | FAIL | OPEN 119 |
| «Tez yozish» kartasi | FAIL | OPEN 120 — tasdiqsiz takroriy xarajat |
| Zaxira: eksport (`.bkd`) | PASS | ulashish oynasi |
| Zaxira: backup emas fayl; noto'g'ri parol | PASS | «Bu Baraka Dastur zaxira nusxasi emas.»; «Parol notoʻgʻri yoki fayl buzilgan.» |
| Zaxira: to'g'ri parol bilan tiklash | NOT TESTED | OPEN 124 |
| Til uz ↔ ru | PASS | bosh sahifa to'liq tarjima bo'ladi |
| Mavzu tugmasi | PASS | yorug' mavzu; qorong'i rejim vizual tekshirilmadi |
| Bo'limlar ochilishi (11 ta) | PASS | Xarajatlar, Marosimlar, Kelishuvlar, Hunardan ishga, Havas va odatlar, Obunalar, Konvertlar, Qutqarilgan pul, Narx daftari, Bugungi tushum, Oy yakuni |
| Katta shrift (2.0) | PASS | kartalar moslashdi, matn kesilmadi |
| Landscape | PASS | crash yo'q; vizual tekshiruv cheklangan |
| Logcat maxfiylik | PASS | ism, PIN, parol topilmadi |
| Xotira (PSS) | 243 MB | emulyator va ARM tarjima ustida; telefonda o'lchanmagan |
| `test/design` (grafika, ikonka taqiqi) | PASS | +6 |
| `uz_orthography.py --check` | PASS | 0 ta tuzatish |
| E2E `full_e2e_test.dart` (x64 release) | PASS | `+3: All tests passed!` |
| E2E `encrypted_db_test.dart` (x64 release) | PASS | `+8: All tests passed!`. Birinchi yugurishda 1 ta test yiqildi: kutilma 11 ta kategoriya edi, ilova 13 ta (`CategoryKey`, v6 dan beri) beradi. Test `CategoryKey.values.length` ga o'zgartirildi (`integration_test/encrypted_db_test.dart`) |
| FLAG_SECURE (moliyaviy ekran) | PASS | qulf ekrani va bosh sahifa oynasida `SECURE`; ekran surati to'liq qora |
| Sovuq start (`am start -W`) | 3,1–3,3 s | emulyator, ARM tarjima; birinchi start 6,2 s. Telefonda o'lchanmagan (talab < 2 s) |
| Xotira emulyatordan keyin | erkin RAM 13,3 → 15,5 GB; pagefile 1,35 → 1,21 GB | `qemu` va `emulator` jarayonlari to'xtatildi |
| Bildirishnoma, TalkBack, eski versiya ustidan yangilash, haqiqiy telefon | NOT TESTED | sinov rejasida yo'q yoki qurilma yo'q |

## 8. Tuzatishdan keyingi qayta sinov (2026-10-14)

Artefakt: `build/app/outputs/flutter-apk/app-arm64-v8a-release.apk` — 28,8 MB,
14.10.2026 03:34:48, `versionName 0.1.0`, `versionCode 1`.
SHA-256: `6445bcade628afc626144ee0342ecad7165d17681de189b8a0b079bda9369756`.
Kod: commit `177b018` + ishchi nusxadagi o'zgarishlar (commit qilinmagan).
Imzo: hali `CN=Android Debug` — reliz kaliti kerak (OPEN 122).

| Band | Natija | Izoh |
|---|---|---|
| Kelishuv 4-savol: ikki ulush bitta sessiyada | PASS | «Akmal 60 %, Bahodir 40 %» |
| Kelishuv 6-savol: matn, keyin taraf tanlanadi | PASS | «Naqd · Akmal · Oyiga bir marta» |
| Kelishuv 7-savol: qiymat va to'lov bitta sessiyada | PASS | «Bozor narxi · Naqd pul» |
| Sherikchilik: imzolangan tomonda «Imzolash» yo'q | PASS | uchala tomon «Imzolangan» |
| Ishga tushish, PIN, FATAL/ANR | PASS | FATAL = 0, ANR = 0 |
| Test to'plami (`flutter test`) | PASS | 686 o'tdi, 5 o'tkazib yuborildi |
| `flutter analyze --fatal-infos` | PASS | xato yo'q |

Tekshirilmagan (kodi o'zgarmagan): zaxiradan to'g'ri parol bilan tiklash, bildirishnoma,
TalkBack, eski versiya ustidan yangilash, haqiqiy telefon.

Xotira: emulyatordan keyin erkin RAM 15,1 GB, pagefile 1,2 GB (oldin 13,3 GB / 1,35 GB).

## 9. Yakuniy reliz sinovi (2026-10-14)

Artefakt: `build/app/outputs/flutter-apk/app-arm64-v8a-release.apk` — 28,8 MB,
14.10.2026 09:17:48, `versionName 0.1.0`, `versionCode 1`.
SHA-256: `68a29b0686a8b1f5d91ad993d22e856ece19c6da4af2ef01f9d0e5143b7107a4`.
Kod: commit `177b018` + ishchi nusxadagi o'zgarishlar (commit qilinmagan).
Imzo: `CN=Android Debug` — reliz bloker (OPEN 122).

Avtomatik tekshiruvlar:
- `flutter test`: 689 o'tdi, 5 o'tkazib yuborildi.
- `flutter analyze --fatal-infos`: xato yo'q. `test/design`: o'tdi. `uz_orthography --check`: 0 xato.
- E2E `full_e2e_test.dart` (x64 release, yakuniy kod): «All tests passed!» (shifrlangan zaxira → 1:1 tiklash ham shu ssenariyda).
- E2E `encrypted_db_test.dart` (x64 release): «All tests passed!».

Qurilmada (emulyator, arm64 APK):

| Band | Natija | Izoh |
|---|---|---|
| Ishga tushish, PIN, emulyator ogohlantirishi | PASS | |
| Qulf: qisqa fon (12 s) / uzoq fon (130 s) | PASS | uzoq fondan keyin qulf ekrani, PIN bilan ochildi |
| FLAG_SECURE (bosh sahifa, sozlamalar) | PASS | ekran surati qora |
| Bosh sahifa va 11 ta bo'lim | PASS | xato yo'q |
| Tez yozish: takrorlash va «Bekor qilish» | PASS | «Takrorlandi: 12 000 soʻm» |
| Kelajagim: pul olish (sabab, PIN) | PASS | 23 000 → 18 000; qorovul reja «Har oy 834 soʻm» (OPEN 121) |
| Xarajat: suring bilan o'chirish, «Bekor qilish» | PASS | jami 39 000 → 24 000 → 39 000 (OPEN 120) |
| Bugungi tushum va «Ajratish» | PASS | 300 000 kiritildi, Kelajagim +25 000 |
| Oy yakuni taqsimoti | PASS | «Doʻkondorniki» = oziq-ovqat xarajatlari |
| Bob sarlavhasi | PASS | «(placeholder)» yo'q (OPEN 119) |
| Kelishuv 4/6/7-savol, bitta sessiyada | PASS | «Akmal 60 %, Bahodir 40 %»; «Naqd · Akmal · Oyiga bir marta»; «Bozor narxi · Naqd pul» (OPEN 113–115) |
| Tilxat: imzolangan tomonda «Imzolash» yo'q | PASS | OPEN 117 |
| Tilxat ↔ kelishuv sinxron | PASS | hakam tilxatda ko'rinadi (OPEN 116) |
| Imzolangan kelishuvga guvoh qo'shish | PASS | «Imzolangan versiya oʻzgarmaydi — yangi versiya yarating.» |
| Sherikchilik: buyout toʻlovlari kartasi | PASS | alohida karta (OPEN 123) |
| Sherikchilik: imzolangan tomonda «Imzolash» yo'q | PASS | |
| Zaxira: bo'sh yukli fayl, to'g'ri parol | PASS (tuzatildi) | avval baza o'chdi; endi «Bu Baraka Dastur zaxira nusxasi emas.», ma'lumot saqlanadi |
| Zaxira: noto'g'ri parol, boshqa fayl | PASS | |
| Zaxira: to'liq tiklash | PASS (E2E) | qo'lda saqlash joyi emulyatorda yo'q (OPEN 127) |
| Til uz↔ru, mavzu tugmasi | PASS | mavzu vizual tekshirilmadi (FLAG_SECURE) |
| Katta shrift 2.0 | PASS | oldingi sessiya, o'zgarmagan |
| FATAL/ANR (butun sessiya) | PASS | 0 / 0 |
| Logda maxfiy ma'lumot | PASS | |
| Xotira (PSS) | ~219 MB | emulyator va ARM tarjima |
| Sovuq start | 3,7–4,7 s | emulyator; telefonda o'lchanmagan |
| Haqiqiy telefon, bildirishnoma, TalkBack, eski versiyadan yangilash | NOT TESTED | |

Sinov davomida topilib tuzatilgan defektlar:
1. **Zaxira tiklash (kritik):** bo'sh yukli fayl to'g'ri parol bilan bazani butunlay o'chirardi. Tuzatildi: uy xo'jaligi yo'q yuk o'chirishdan oldin rad etiladi (`backup_service.dart`, regressiya testi).
2. **Tilxatda imzolangan tomon qayta imzolanardi:** tugma qolardi. Tuzatildi (`receipt_screen.dart`).
3. **Kelishuvda qayta imzo rad etilmasdi:** tuzatildi (`agreement_service.dart`, `agreement_already_signed`).
4. **Tilxat ekrani kelishuvdan keyin eski holatni ko'rsatardi;** guvoh alohida do'konga yozilardi. Tuzatildi (OPEN 116).

## 10. 14A tuzatishi va 14B (7-qonun) sinovi (2026-10-20, emulyator)

Artefakt: `build/app/outputs/flutter-apk/app-arm64-v8a-release.apk` — 29,1 MB,
20.10.2026 11:50:47, `versionName 0.1.0`, `versionCode 1`.
SHA-256: `88a8153120eacb3319990614b91ea95ea391688e5ee6798f9676dde57b73feda`.
Kod: commit `177b018` + ishchi nusxadagi o'zgarishlar (14A va 14B commit qilinmagan).
Imzo: `CN=Android Debug` — reliz bloker (OPEN 122).

Avtomatik tekshiruvlar:
- `flutter test`: 756 o'tdi, 4 o'tkazib yuborildi.
- `flutter analyze --fatal-infos`: xato yo'q. `uz_orthography --check`: 0 xato. Format (CI ro'yxati): o'zgarish yo'q.
- E2E `full_e2e_test.dart` (x64 release): «All tests passed!»; logda 14A (oylik ko'rik, zanjir butun) va 14B («Bekzod: taklif qizil (4 belgi), rad etildi; devor to'la — hunarga») qadamlari.

Qurilmada (emulyator API 36, arm64 APK):

| Band | Natija | Izoh |
|---|---|---|
| Yillik yangilash ishi rejalashtiriladi | PASS (tuzatildi) | kelishuv yaratilib, ilova qayta ochilgach WorkManager ishi +334 kun 21 soat — 2027-09-20 09:00 (Toshkent), `reviewDate` dan 30 kun oldin. Tuzatishdan oldin hech qachon paydo bo'lmasdi (9-bo'lim) |
| Ish `adb reboot` dan keyin | PASS | 4 ish ham joyida, muddat o'sha (+334 kun 21 soat 36 daq); boot'dan ~60 s keyin o'qildi |
| Ish APK ustidan qayta o'rnatish va `force-stop` dan keyin | PASS | yillik ish saqlandi |
| Taklif tekshiruvi: 9 savol, «o'z ko'zim bilan» ro'yxati | PASS | |
| «Tez Foyda»: oyiga 35 % | PASS | «5,2 / 36,6 barobar» ogohlantirishi; qizil, 4 belgi, RIBO / G'ARAR / QIMOR |
| «Pul qo'yaman» | PASS | o'chiq, «21.10.2026 11:26 dan keyin ochiladi»; maslahatchi ismi yozilgach «Rad etdim» → tarixda «Qizil · Rad etildi» |
| Piramida (k = 5, 1 mln) | PASS | 10-qavat, pastda 51,2 % |
| «Bilmayman» bayroqlari | PASS (tuzatildi) | avval bir xil qator 3 marta; endi har qator savolni aytadi |
| Katta summa: 18 000 $ × 12 650 | PASS | 18 000 000 zaxiraga, 209 700 000 hunarga; «Oilaviy zaxiraga qo'yildi», keyin «devor to'la — 227 700 000 hunarga», tugma o'chdi |
| Katta summa: zaxira maqsadi yo'q | PASS (tuzatildi) | avval faqat «avval belgilang»; endi shu yerda «Taxminiy summani kiritish» |
| Hunar shabloni | PASS (tuzatildi) | nom chipda kesilardi; endi to'liq, 5 ta CAPEX tavsiyasi |
| FATAL / ANR | PASS | 0 / 0 |
| Sovuq start (`force-stop` keyin) | 2,9 s | 3 marta: 2913 / 2888 / 2893 ms; o'rnatishdan keyingi birinchisi 6,8 s (hisobga olinmaydi) |
| Xotira (PSS) | ~224 MB | emulyator va ARM tarjima |
| Haqiqiy telefon, bildirishnoma kelishi, TalkBack, eski versiyadan yangilash | NOT TESTED | |

Kuzatuvlar (defekt emas): PIN klaviaturasidagi o'chirish tugmasi `uiautomator` da yorliqsiz ko'rinadi — yorliq `tooltip` orqali beriladi, TalkBack o'qiydi (telefonda tekshirilsin). Pastki oyna ortidagi fon TalkBack'da «Kanop» deb o'qiladi — bu Flutter'ning o'zbekcha tarjimasi (`scrimLabel`), ilovaniki emas.

## 11. Rebrend sinovi: «Baraka Dastur» (2026-10-23, emulyator)

Artefakt: `build/app/outputs/flutter-apk/app-arm64-v8a-release.apk` — 29,1 MB,
23.10.2026 14:07:57, `versionName 0.1.0`, `versionCode 1`, `applicationId uz.barakadastur.app`.
SHA-256: `7b04f0874286ea5333be07b0d7fc737270f648ab49918fa1a9b047c4decbac8e`.
Kod: commit `a311f95` + ishchi nusxadagi rebrend o'zgarishlari (commit qilinmagan).
Imzo: `CN=Android Debug` — reliz nomzodi, Play'ga yuklab bo'lmaydi (upload kaliti yo'q, OPEN 122).

Avtomatik tekshiruvlar:
- `flutter test`: 764 o'tdi, 4 o'tkazib yuborildi. `test/vectors`: 117/117. Kotlin JUnit: 46/46.
- `flutter analyze --fatal-infos`, format (CI ro'yxati), `uz_orthography --check`: toza.
- E2E `full_e2e_test.dart` (x64 release): «All tests passed!»; qadamlar yangi shartli ismlar bilan
  («davr yopildi: Akmal 3 mln…», «Bekzod: taklif qizil (4 belgi), rad etildi; zaxira to'la — hunarga»), zaxira → 1:1 tiklash.

Qurilmada (emulyator API 36, arm64 APK, yangi o'rnatish):

| Band | Natija | Izoh |
|---|---|---|
| Launcher: nom va ikonka | PASS | «Baraka Dastur», yashil fonda «B» + bug'doy boshog'i; eski «Baraka daftari» sinov o'rnatmasi alohida ilova bo'lib qoldi |
| PIN o'rnatish → onboarding | PASS | «Assalomu alaykum! Baraka Dasturga xush kelibsiz»; 5 qadam |
| Boblar ro'yxati | PASS | 1–7 yangi sarlavhalar («1-bob. Avval o'zingga to'la» … «7-bob. Tekshirmagan ishga pul tikma»), odat qoidasi bilan yopiq |
| 1-bob ichi | PASS | o'z matnimiz, «Maslahatchi» bloki, 1-qonun; PENDING diniy blok release'da ko'rinmaydi |
| Kelajagim atamalari | PASS | «Favqulodda zaxira», «O'sadigan pul», «Inflyatsiya ta'siri», «Katta summa tushdimi?» |
| Ilova ichidagi nishon (qulf, onboarding) | PASS (widget testi) | qurilmada ko'z bilan ko'rilmadi: FLAG_SECURE ekranini oyna surati bilan olishda foydalanuvchi ish stoli ustida edi |
| FATAL / ANR | PASS | 0 / 0 |
| Sovuq start | 6–11 s | emulyatorning shu kungi holati: 20-oktabrdagi eski build ham hozir 10,7 s (o'shanda 2,9 s); telefonda o'lchanmagan |
| Haqiqiy telefon, bildirishnoma, TalkBack, eski versiyadan yangilash | NOT TESTED | eski `uz.barakadaftari.app` dan yangilanish bo'lmaydi — alohida ilova |

## 12. Reliz nomzodi 1.0.0 (2026-10-23)

Versiya: `1.0.0+2` (`versionName 1.0.0`, `versionCode 2` — 0.1.0 sinov o'rnatmasi ustidan yangilanadi).
Artefaktlar: `build/release/1.0.0+2/` (`tools/build_release.ps1`), 23.10.2026 15:36–15:38.
Imzo: `CN=Android Debug` — **reliz nomzodi, Play'ga yuklab bo'lmaydi**. Upload kaliti
(2-bo'lim) yaratilgach skript `-SigningProperties` bilan qayta ishga tushiriladi.

| Fayl | Hajm | SHA-256 |
|---|---|---|
| `app-release.aab` (Play; arm, arm64, x64) | 57,3 MB | `f0e1f2d1bd9341019d5bddd6b82a3e61862a0d22b29c2a4d0b498397d1ece707` |
| `app-arm64-v8a-release.apk` (telefon) | 29,1 MB | `592f7b97dc853aa6ff7a534ddf266697ff5a88ca05485127828f828aeba03042` |
| `app-armeabi-v7a-release.apk` | 25,5 MB | `5b8cae628e89fd30ef5313c94efa72759de6c95edcbda2f299a509a58f1deb7a` |
| `app-x86_64-release.apk` | 30,8 MB | `aea3af5504972c77d11ddcb2ab50128a9bae3c7398294dfb44f644431a50c9a0` |
| `mapping-aab.txt` / `mapping-apk.txt` (bir xil — Kotlin/Java kodi bir) | 15,7 MB | `5fec90980c58370445f45b7e23efc48d5bdfb7e2dd15ce284e673899d0185945` |
| `symbols-aab.zip` | 4,6 MB | `66e932deaedb163aa94ccbd9631570cb0f21e08964bc5865857da1aec1597b34` |
| `symbols-apk.zip` | 4,6 MB | `67a7786293d6eab08c2b189f2a42a4b0ca505cef4aacbc9ef4fa99a47bdfe7bb` |

Tekshiruvlar:
- `aapt2 dump badging` (arm64 APK): `package uz.barakadastur.app`, `versionCode 2`, `versionName 1.0.0`,
  yorliq «Baraka Dastur», `targetSdk 35`. AAB manifestida ham paket, versiya va yorliq bor;
  `jarsigner -verify`: imzo `CN=Android Debug`.
- `flutter test`: 764 o'tdi, 4 o'tkazib yuborildi; `flutter analyze --fatal-infos`: toza.
- Emulyatorda 0.1.0 → 1.0.0 yangilanish (`adb install -r`, arm64 APK): onboarding qayta chiqmadi, qulf
  ekrani → PIN bilan ochildi, bosh sahifa; FATAL / crash 0. (Emulyatorning System UI'si yuklanish paytida
  bir marta «isn't responding» berdi — ilovaga aloqasi yo'q.)
- Kod 11-bo'limdagi rebrend sinovidan keyin faqat versiya bilan farq qiladi.

Qolgan (reliz bloker): upload kaliti va imzoli AAB; haqiqiy telefonda 5-bo'lim; Play Console: maxfiylik
siyosati, Data safety, kontent reytingi, do'kon sahifasi (`tools/store/play_icon_512.png`,
`tools/store/feature_graphic_1024x500.png`); «Baraka» savdo belgisi bo'yicha yurist xulosasi.

## 13. 1.0.0+3: «Ilova haqida», LICENSE va demo (2026-10-25)

Artefaktlar: `release/1.0.0+3/` (`tools/build_release.ps1`), debug imzo — reliz nomzodi.

| Fayl | SHA-256 |
|---|---|
| `app-release.aab` | `c04a9e559de118141cf065d42a43224529f315b731424363027305f398bcd320` |
| `app-arm64-v8a-release.apk` | `36c520177ba82894f21145a00badd02c3e8b72b809addb95e24be0cf609adc63` |
| Demo `release/demo/baraka-dastur-demo-1.0.0-2026-11-24.apk` (barcha ABI) | `b0cb7a7a1e78c86483e428a0182cf80f7fdb6a5895d8440fe135b14c01e48728` |

- `aapt2`: reliz — `uz.barakadastur.app`, `versionCode 3`, `versionName 1.0.0`, «Baraka Dastur»; demo — `uz.barakadastur.demo`, «DEMO Baraka Dastur», `apksigner`: `CN=Android Debug`.
- `flutter test`: 770 o'tdi, 4 o'tkazib yuborildi; `flutter analyze --fatal-infos`: toza.

Demo qurilmada (alohida `Baraka_Demo` AVD, API 36 x86_64, 2026-10-25; umumiy emulyator 94 % to'la edi):

| Band | Natija | Izoh |
|---|---|---|
| O'rnatish, PIN, onboarding | PASS | `versionCode 3`; har ekranda pastda «Demo versiya · © 2026 JurabekM · nashr qilish va tarqatish taqiqlanadi» |
| «DEMO» lentasi | PASS | yuqori o'ng burchakda (oyna surati bilan ko'rildi; holat paneli ustida) |
| «Ilova haqida» | PASS | «Versiya 1.0.0 (3)», «Demo versiya: 24.11.2026 gacha ishlaydi», muallif, ©, taqiq, maxfiylik; litsenziyalar sahifasi ochiladi |
| Muddat chegarasi (Toshkent vaqti) | PASS | 24.11 23:00 — ochiladi; 25.11 00:30 va 25.11 15:00 — «Demo muddati tugadi», ilovaga kirib bo'lmaydi |
| Haqiqiy ilova bilan yonma-yon | PASS | `uz.barakadastur.app` va `.demo` ikkalasi o'rnatildi; haqiqiy ilovada demo yozuvi yo'q |
| Launcher nomi | PASS (tuzatildi) | avval «Baraka Dastur DEMO» → «Baraka Dast…» bo'lib kesilib, haqiqiy ilovadan farqlanmasdi; endi «DEMO Baraka Dastur» → «DEMO Bara…» |
| FATAL / crash | PASS | 0 |
