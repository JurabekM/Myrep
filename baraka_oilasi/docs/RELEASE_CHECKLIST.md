# Reliz cheklisti — «Baraka oilasi» (1.0.0: Uy, Kasb-kor, Musofir)

Har bir reliz oldidan ketma-ket bajariladi. Belgilanmagan band — reliz yo'q.
Avtomatik tekshiruvlar CI'da; qo'lda tekshiriladiganlar `(qo'lda)` deb belgilangan.

## 1. Kod va testlar
- [ ] `baraka-oilasi` workflow'ining barcha job'lari oxirgi commit'da yashil (core ubuntu/windows, oracle, codegen, desktop-ui, desktop-tauri windows/ubuntu).
- [ ] `desktop-e2e` (tungi yoki qo'lda `workflow_dispatch`) yashil; `baraka-e2e-screenshots` artefakti ko'rib chiqildi.
- [ ] Mahalliy: `cargo fmt --check && cargo clippy --workspace --all-targets --all-features -- -D warnings && cargo test --workspace`.
- [ ] Oracle'lar: `python3 -I spec/oracle/oracle.py --selftest && --check spec/test-vectors`; `python3 -I spec/interchange/oracle.py --selftest && --check spec/interchange/vectors.json`.
- [ ] `cargo xtask all` — i18n lint (taqiqlangan iboralar) va **WCAG kontrast** (`tokens.json` → `contrast.pairs`, ikkala mavzu), `git diff --exit-code`.
- [ ] `pnpm --dir apps/desktop/ui lint && pnpm --dir apps/desktop/ui test` (axe-core tekshiruvlari bilan).
- [ ] `CHANGELOG.md` da reliz bo'limi; `tauri.conf.json` va `Cargo.toml` versiyalari bir xil.

## 2. Xavfsizlik
- [ ] Release build'da quyidagilar ishlamasligi tekshirildi (barchasi `cfg(debug_assertions)` ortida): `BARAKA_INSECURE_DEV_SECRET`, `BARAKA_DEV_SHIFT_DAYS`, `BARAKA_E2E_FILES`. (qo'lda: release ilovani shu o'zgaruvchilar bilan ishga tushirib, keyring so'ralishi va «Saqlash» oynasi ochilishini ko'rish)
- [ ] CSP o'zgarmagan (`script-src 'self'`, `unsafe-eval` yo'q); `devtools: false`; `contentProtected: true` — skrinshot qora. (qo'lda, Windows)
- [ ] Yangi Tauri buyruqlari uchun `capabilities/main.json` da aniq ruxsat; ortiqcha ruxsat yo'q.
- [ ] Loglarda shaxsiy yoki moliyaviy ma'lumot yo'q (`app.log` ni ko'rib chiqish).
- [ ] Imzolash kalitlari va sertifikat faqat CI secret'larida; repoda yo'q.

## 3. Windows o'rnatuvchi va imzo
- [ ] OV/EV kod imzolash sertifikati bor (koddan tashqari masala — `BARAKA_OILASI.md` 18).
- [ ] `bundle.windows.certificateThumbprint` (yoki `signCommand`) va `timestampUrl` CI'da secret'dan beriladi; `signtool verify /pa` muvaffaqiyatli.
- [ ] Toza Windows 10/11 da o'rnatuvchi SmartScreen ogohlantirishisiz ochiladi (sertifikat bo'lsa). (qo'lda)
- [ ] WebView2 o'rnatilmagan mashinada `embedBootstrapper` ishlaydi. (qo'lda)
- [ ] Yangilash: OQ-T8 qarori chiqmaguncha avtomatik updater yo'q; yangi versiya ustidan o'rnatilganda baza va kalitlar saqlanadi. (qo'lda)

## 4. Ishlash
- [ ] Sovuq start < 1,5 s (release build, PIN ekrani ko'ringuncha). O'lchov: `apps/desktop/e2e/README.md` → «Sovuq start». Natija CHANGELOG'ga yoziladi.
- [ ] 1 yillik ma'lumot bilan (~5 000 yozuv) asosiy ekranlar sezilarli kechikmasdan ochiladi. (qo'lda)

## 5. Accessibility
- [ ] E2E'da har bir ko'rilgan ekran haqiqiy webview'da axe-core (WCAG 2.2 A/AA, kontrast bilan) — 0 ta xato.
- [ ] Faqat klaviatura bilan: onboarding → daromad (`Ctrl+N`) → qulflash (`Ctrl+L`) → ochish; barcha oynalar `Esc` bilan yopiladi, fokus ko'rinadi. (qo'lda)
- [ ] Windows «Yuqori kontrast» (Aquatic, Desert) — chegaralar, tugmalar va fokus ko'rinadi. (qo'lda)
- [ ] DPI 125 %, 150 %, 200 % va ilova ichidagi shrift 100–150 % — matn kesilmaydi, gorizontal aylantirish yo'q. (qo'lda)
- [ ] Ekran o'quvchi (NVDA): onboarding qadamlari, bosh sahifa eslatmalari va dialoglar o'qiladi. (qo'lda)

## 6. Ma'lumotlar
- [ ] Eksport → yangi profil → «Mavjud xonadonga qo'shilish» (zaxira nusxa) → ma'lumotlar 1:1 (E2E `03-restore`).
- [ ] Oldingi relizning bazasi yangi versiyada ochiladi (migratsiyalar), jurnal zanjiri butun. (qo'lda: eski profil nusxasi bilan)
  - Avtomatik: `cargo test -p baraka-app --test upgrade_1_1` — 1.1.0 sxemasidagi (v22, 001–022) shifrlangan baza Uy, Kasb-kor (`v: 1` «Hisob kuni» bayonnomasi bilan), Musofir va jurnal yozuvlari bilan to'ldiriladi, hozirgi ilova ochadi (023–025): sxema versiyasi, eski jadvallardagi har bir qiymat, jurnal zanjiri, bo'sh yangi jadvallar, xarajatdagi yangi ustunlar (0 / NULL) va asosiy use-case'lar tekshiriladi. Keyingi relizda shu test yangi «oldingi» versiya uchun takrorlanadi (`Database::create_at_version`, `test-support`).
- [ ] Tiklash kodi bilan ochish va PIN almashtirish ishlaydi. (qo'lda)

## 7. Android
- [ ] `cargo xtask codegen && git diff --exit-code` — FRB va Pigeon generatsiyasi yangi.
- [ ] `flutter analyze` — 0 ta izoh; `flutter test` (host'da yig'ilgan haqiqiy yadro bilan: 51 vektor suite FFI orqali, Uy / sheriklik / Kasb-kor / sotuvchi qurilmasi / Musofir va «Ikki qirg'oq» oqimlari) yashil. CI'dagi `android` job.
- [ ] Skrinshotlar (`BARAKA_SHOTS=1 flutter test --update-goldens`) ko'rib chiqildi: dark mavzu, matn kesilmaydi, gorizontal aylantirish yo'q.
- [ ] Release: `flutter build appbundle --release --obfuscate --split-debug-info=build/symbols` (R8 yoqilgan) — `BARAKA_REQUIRE_RELEASE_SIGNING=1` bilan (kalitsiz yig'ilmaydi); imzo `apksigner verify --print-certs` bilan, sertifikat SHA-256 kutilgani bilan bir xil; simvollar arxivlangan (7.1).
- [ ] Hajm byudjeti (OQ-T1): arm64 yuklab olish ≤ 40 MB (1.0.0: ≈ 30,8 MB — `--split-per-abi` APK'ni siqib o'lchash).
- [ ] Haqiqiy qurilmada (qo'lda, Android 8 va eng yangi versiya; reja — 7.2): adaptiv ikonka, ishga tushishda oq chaqnash yo'q, `FLAG_SECURE` (skrinshot qora), fonga o'tgandan 2 daqiqa keyin qulf, Keystore platforma siri (ilova qayta o'rnatilganda eski baza ochilmaydi — kutilgan), PDF va `.baraka` ulashish oynasi, fayl tanlash (chek rasmi, `.baraka`), TalkBack bilan onboarding.
- [ ] Ikki qurilma (qo'lda): desktop ↔ telefon `.baraka` almashish; sotuvchi va uydagi oila qurilmasini ulash (kod bilan).

### 7.1. Imzolash (Play App Signing)
- Yuklash kaliti (upload key) — PKCS12 `.jks`, RSA 4096, alias `upload`. Repoda yo'q: mahalliy yig'ishda `apps/android/android/key.properties` (namuna — `key.properties.example`), CI'da secret'lar.
- GitHub → Settings → Secrets and variables → Actions: `BARAKA_UPLOAD_KEYSTORE_B64` (`base64 -w0 baraka-upload.jks`), `BARAKA_KEYSTORE_PASSWORD`, `BARAKA_KEY_ALIAS` (`upload`), `BARAKA_KEY_PASSWORD`.
- Reliz: `git tag baraka-v1.0.0 && git push origin baraka-v1.0.0` (yoki «Run workflow») → `android-release` job → `baraka-android-release` artefakti (AAB + APK) va `baraka-android-symbols` (obfuskatsiya simvollari — Play Console'ga yuklanadi).
- Play Console: ilova yaratish → «Play App Signing» (Google ilova kalitini saqlaydi, biz faqat yuklash kalitini) → Internal testing'ga AAB. Yuklash kaliti yo'qolsa — Play Console orqali almashtiriladi.
- Kalit va parol ikki joyda saqlanadi (parol menejeri + oflayn nusxa).

### 7.2. Qurilmada sinov rejasi (≈ 30 daqiqa, qo'lda)
O'rnatish: `adb install -r app-arm64-v8a-release.apk` (yoki faylni telefonga yuborib ochish, «Noma'lum manbalar»ga ruxsat).
1. Birinchi ochilish: oq chaqnash yo'q (dark fon), ikonka — daftar va xatcho'p. Onboarding 5 qadam → tiklash kodi ko'rsatiladi.
2. Daromad → «Ajratish» → bosh sahifa KPI yangilanadi. Xarajat, qarz va to'lov.
3. Qarz tilxati → PDF ulashish oynasi ochiladi (Telegram/Fayllar), PDF to'g'ri ochiladi.
4. Ekran rasmi olishga urinish — qora/taqiqlangan (`FLAG_SECURE`). «So'nggi ilovalar» oynasida mazmun ko'rinmaydi.
5. Ilovani fonga o'tkazib 2 daqiqadan keyin qaytish → PIN so'raladi; noto'g'ri PIN → kutish.
6. Sheriklik: imzoni barmoq bilan chizish (4 kishi), kassa daftariga chek rasmini galereyadan qo'shish, davrni yopish, hisobot PDF.
7. Kasb-kor: tushum/chiqim, kassa kuni, nasiya. Musofir: maosh, uyga yuborish; Uy → «Ikki qirg'oq»da qabul qilish.
8. Sinxronlash: zaxira `.baraka` saqlash → boshqa telefonda «Mavjud xonadonga qo'shilish» (fayl + parol) yoki desktop bilan almashish.
9. Sozlamalar: til (uz / uz-Cyrl / ru), shrift 150 % — matn kesilmaydi; TalkBack bilan onboarding o'qiladi.
10. Ilovani o'chirib qayta o'rnatish: eski ma'lumot yo'q (Keystore siri qurilmadan chiqmaydi, `allowBackup=false`) — kutilgan; zaxira fayldan tiklash ishlaydi.
Topilgan xato: qurilma modeli, Android versiyasi, qadam va skrinshot (agar ruxsat bo'lsa) bilan yoziladi.

## 8. Koddan tashqari (`BARAKA_OILASI.md` 18)
- [x] Boshqa mualliflarning matni, personajlari va brendi ishlatilmaydi; ilova nomi — «Baraka Dastur» (`BARAKA_OILASI.md` 2.1).
- [ ] Ulamo ko'rigi: diniy matnlar va sheriklik shablonlari `APPROVED`; aks holda release'da ko'rsatilmaydi.
- [ ] Yurist ko'rigi: tilxat va shartnoma shablonlari.
- [ ] Maxfiylik siyosati (shaxsga doir ma'lumotlar to'g'risidagi qonun).
