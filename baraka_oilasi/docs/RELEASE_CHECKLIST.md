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
- [ ] Tiklash kodi bilan ochish va PIN almashtirish ishlaydi. (qo'lda)

## 7. Android
- [ ] `cargo xtask codegen && git diff --exit-code` — FRB va Pigeon generatsiyasi yangi.
- [ ] `flutter analyze` — 0 ta izoh; `flutter test` (host'da yig'ilgan haqiqiy yadro bilan: 51 vektor suite FFI orqali, Uy / sheriklik / Kasb-kor / sotuvchi qurilmasi / Musofir va «Ikki qirg'oq» oqimlari) yashil. CI'dagi `android` job.
- [ ] Skrinshotlar (`BARAKA_SHOTS=1 flutter test --update-goldens`) ko'rib chiqildi: dark mavzu, matn kesilmaydi, gorizontal aylantirish yo'q.
- [ ] Release: `flutter build appbundle --release --obfuscate --split-debug-info=build/symbols` (R8 yoqilgan); `key.properties` va keystore repodan tashqarida, imzo `apksigner verify` bilan; simvollar arxivlangan.
- [ ] Hajm byudjeti (OQ-T1): arm64 yuklab olish ≤ 40 MB (1.0.0: ≈ 30,8 MB — `--split-per-abi` APK'ni siqib o'lchash).
- [ ] Haqiqiy qurilmada (qo'lda, Android 8 va eng yangi versiya): adaptiv ikonka, ishga tushishda oq chaqnash yo'q, `FLAG_SECURE` (skrinshot qora), fonga o'tgandan 2 daqiqa keyin qulf, Keystore platforma siri (ilova qayta o'rnatilganda eski baza ochilmaydi — kutilgan), PDF va `.baraka` ulashish oynasi, fayl tanlash (chek rasmi, `.baraka`), TalkBack bilan onboarding.
- [ ] Ikki qurilma (qo'lda): desktop ↔ telefon `.baraka` almashish; sotuvchi va uydagi oila qurilmasini ulash (kod bilan).

## 8. Koddan tashqari (`BARAKA_OILASI.md` 18)
- [ ] Kontent va brend litsenziyasi; qissa matnlari placeholder emas yoki placeholder ekani aniq.
- [ ] Ulamo ko'rigi: diniy matnlar va sheriklik shablonlari `APPROVED`; aks holda release'da ko'rsatilmaydi.
- [ ] Yurist ko'rigi: tilxat va shartnoma shablonlari.
- [ ] Maxfiylik siyosati (shaxsga doir ma'lumotlar to'g'risidagi qonun).
