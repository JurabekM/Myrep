# Reliz tekshiruvi (Baraka Dastur desktop)

Bu ro'yxat har reliz oldidan bajariladi. Avtomatik qismlar CI va mahalliy buyruqlar bilan; qo'lda qismlar
o'rnatuvchini haqiqiy Windows mashinasida sinashni talab qiladi.

## 1. Avtomatik tekshiruvlar

- [x] `pnpm lint && pnpm typecheck && pnpm test` — yashil (2026-10-20: lint 0 xato, vitest 23 fayl / 93 test).
- [x] `cargo test --workspace` — yashil (bindinglar ham yangilanadi; `git diff ui/src/bindings` bo'sh bo'lishi kerak). (2026-10-20: 368 test; birinchi yurishda vektor qoplanish testi yiqildi — D16 suite'lari ro'yxatga qo'shildi.)
- [x] `cargo clippy --workspace --all-targets -- -D warnings` — yashil (2026-10-20).
- [x] Vektorlar: `spec/test-vectors/SHA256SUMS` testi (`mobil_bilan_umumiy_vektorlar_manifestga_mos`) yashil (2026-10-20, 22 suite).
- [x] `pnpm format:check` — yashil (2026-10-20; mobildan ko'chirilgan `spec/content/content_schema.json` CRLF bilan kelgan edi — formatlandi).

## 2. O'rnatuvchi

- [x] `pnpm build` — NSIS o'rnatuvchisi `<CARGO_TARGET_DIR>/release/bundle/nsis/` da chiqadi (2026-10-16: `Baraka Dastur_0.1.0_x64-setup.exe`, 16,9 MiB).
- [x] Silent o'rnatish (`/S`) ishlaydi (2026-10-16, exit 0, `%LOCALAPPDATA%\Baraka Dastur`, reestr `Uninstall\Baraka Dastur` 0.1.0); `uninstall.exe /S` ham. **Eslatma:** `displayLanguageSelector` yoqiq bo'lsa `/S` til dialogida qotadi — o'chirilgan.
- [x] O'rnatuvchi hajmi va versiyasi `CHANGELOG` dagi raqamga mos (2026-10-20: `Baraka Dastur_0.1.0_x64-setup.exe`, 17 898 989 bayt, SHA-256 `98851128…08E1`; `/S` o'rnatish, `uninstall.exe /S` va qayta o'rnatish exit 0).

## 3. Qo'lda sinov (haqiqiy Windows, o'rnatilgan ilova)

- [x] Birinchi ishga tushirish: PIN o'rnatiladi, qulf ekrani ishlaydi, noto'g'ri PIN'da kechikish bor. _(2026-10-20, dev build, toza profil: mos kelmagan PIN rad; 3-noto'g'ri urinishda ~30 s kutish, ortga sanash.)_
- [x] Har bir menyu bandi bosiladi; ishlamaydigan tugma yo'q (CLAUDE.md, «Tugma ish bajarsin»). _(2026-10-20, dev build: 11 band, RU tili ham.)_
- [x] Byudjet: obuna qo'shish, «ishlatdim», bekor qilish; konvert qo'shish, hafta yakuni; «Kelajagim»ga o'tkazish (ortiqcha summa rad etilishi). _(2026-10-20, dev build.)_
- [x] Xarajatlar: oy xulosasi, toifa o'zgartirish, havas chegarasi va rozilik, bayonnoma PDF (o'zbekcha belgilar to'g'ri). _(2026-10-20, dev build; toifa o'zgarishi oldingi xarajatga ta'sir qilmaydi — OPEN_QUESTIONS.)_
- [x] Kelajagim, audit, qarzlar — ma'lumot saqlanib qoladi (ilovani qayta ishga tushirgandan keyin). _(2026-10-20, dev build.)_
- [ ] Zamonaviy DPI (150%, 200%) va High Contrast rejimida matn kesilmaydi. _(2026-10-20: DPI tizim sozlamasini o'zgartirmasdan, 760 px oyna bilan taqlid qilindi — 6 ta ustma-ust tushish tuzatildi. Haqiqiy 150/200 % va High Contrast — **foydalanuvchi**, tizim sozlamasi.)_
- [x] Oyna yopilgach jarayon to'liq tugaydi (fon jarayon qolmaydi). _(2026-10-20, o'rnatilgan build: WebView2 ham tugaydi. Topilgan xato: `Ctrl+Alt+B` mini oynasi ochilgan bo'lsa jarayon qolardi — tuzatildi va tuzatishsiz/bilan solishtirildi.)_

## 4. Ma'lumot xavfsizligi

- [x] Loglarda summa, ism yoki izoh yo'q (`CLAUDE.md`). _(2026-10-20: kodda 15 ta log chaqiruvi ko'rildi; dev sessiyasi logida kiritilgan 8 summa, 4 nom va 2 PIN qidirildi — 0 ta.)_
- [x] Baza fayli kalitsiz ochilmaydi; kalit fayli bazadan ajratilgan. _(2026-10-20: oddiy sqlite3 — «file is not a database», sarlavha `SQLite format 3` emas; `keys.bin` alohida, 208 bayt.)_
- [x] Jurnal (`journal_entries`) `UPDATE`/`DELETE` ni rad etadi (sxema v8 triggerlari). _(2026-10-20: v14 da qayta yaratilgan; `journal_flows` testi yashil.)_

## 5. Kod imzolash (tashqi shart — to'xtaydigan joy)

- [ ] Windows kod imzolash sertifikati olingan va `tauri.conf.json` ga ulangan. **Hozircha yo'q** —
      imzolanmagan o'rnatuvchida SmartScreen ogohlantirishi chiqadi. Sertifikat kelguncha bu reliz «ichki sinov» darajasida.
- [ ] Imzolangan updater manifesti yaratilgan (sertifikat bilan birga).

## 6. Hujjat

- [x] `docs/CHANGELOG.md` shu reliz uchun yangilangan (2026-10-20, «Reliz tekshiruvi 0.1.0»).
- [ ] `docs/OPEN_QUESTIONS.md` — ochiq bandlar ko'rib chiqilgan (mahsulot qarorlari «Hal qilingan» bo'limida). _(2026-10-20: yangi bandlar qo'shildi; mahsulot qarorlari — **foydalanuvchi**.)_
- [x] Ma'lum cheklovlar foydalanuvchiga aytilgan (CHANGELOG'dagi «Ma'lum cheklovlar» bo'limlari). _(2026-10-20: CHANGELOG «Reliz tekshiruvi 0.1.0» da jamlangan ro'yxat.)_

## 7. D11–D15 qo'shimchalari

- [x] Onboarding: birinchi ochilishda 5 qadam ko'rinadi, «O'tkazib yuborish» va Esc ishlaydi, qayta ochilganda chiqmaydi (`localStorage: baraka.onboarding`). _(dev build, 2026-10-16)_
- [x] Accessibility: `Tab` bilan birinchi fokus — «Asosiy mazmunga o'tish» havolasi; har bir tugma va maydon klaviaturadan yetib boriladi; fokus halqasi ko'rinadi. _(2026-10-20, dev build: skip-link, menyu `Tab`+`Enter`, halqa ko'rinadi.)_
- [ ] Windows High Contrast (`forced-colors`): chegaralar va fokus ko'rinadi; `prefers-reduced-motion` da animatsiya yo'q; 125 %, 150 %, 200 % DPI da matn kesilmaydi, jadvallar gorizontal aylanadi.
- [x] Marosimlar: stsenariy taqqoslash, qarzli reja muhokamasiz tasdiqlanmaydi, smeta PDF ochiladi.
- [x] Sheriklik: darvoza yopiq — kapital kirituvchi yaratolmaydi; rozilik; buyout jadvali; kassa daftari davr yopish va taqsimot; davr hisoboti PDF.
- [x] Kelishuvlar markazi: jadval filtri, hodisa bandi, ko'rik sessiyasi va bayonnoma PDF (`chain_head`), nizo → taqsimot bloklanadi, hakam papkasi PDF (mundarija bor), oilaviy shablon PIN bilan.
- [x] `.baraka`: eksport → fayl bor; boshqa profilga import → ko'rik → qo'llash; noto'g'ri parol aniq xabar; jurnal fork ssenariysi (ikki qurilmada farqli yozuv) bloklanadi.
- [x] Sovuq start < 1,5 s (release): 2026-10-16, o'rnatilgan `baraka-daftari.exe`, jarayon boshlanishidan asosiy oyna dastagigacha **216 ms** (`Start-Process` + `MainWindowHandle` kutish; SSD, Windows 10). Oyna mazmuni (WebView2) bundan bir oz keyin chiziladi.
- [x] E2E (`e2e/asosiy.e2e.ts`, 2026-10-23 gacha `anvar.e2e.ts`; tauri-driver): yashil — yoki qo'lda o'tilgani sana bilan qayd etilgan: **2026-10-20, qo'lda, dev build, 6 qadam** (PIN → daromad+ulush → xarajat/byudjet → payoff → sheriklik ustasi → `.baraka` eksport). tauri-driver o'rnatilmagan (yuklab olish kerak); skeletdagi 2 eskirgan selektor tuzatildi.
- [ ] Kod imzolash: sertifikat bo'lsa `bundle.windows.certificateThumbprint` (yoki `signCommand`) `tauri.conf.json` da; `signtool verify /pa` yashil; updater manifesti (`tauri-plugin-updater` kiritilganda) imzolangan. **Sertifikat yo'q — bu band to'xtab turibdi.**

## 8. Reliz 0.1.0 «Baraka Dastur» (2026-10-23, imzolanmagan)

- [x] Avtomatik: `cargo test` 368, clippy toza, vitest 23 fayl / 93 test, typecheck, lint (0 xato, 2 ta ma'lum
      `react-hooks/incompatible-library` ogohlantirishi), prettier; `git diff ui/src/bindings` — faqat izohlardagi
      atamalar (qo'lda kiritilgan bilan bir xil).
- [x] Kontent: `spec/content/chapters.json` mobil `assets/content/chapters.json` bilan bayt-bir xil (`cmp`).
- [x] Logotip: `scripts/baraka_logo.py` mobil launcher ikonkasi bilan piksel-bir xil (48 va 192 px). O'rnatilgan
      exe ikonkasi yangi belgi ekani `ExtractAssociatedIcon` bilan tekshirildi. **Topilgan xato:** ikonka
      o'zgargandan keyingi birinchi build exe ichiga eski ikonkani qo'ydi (`tauri-build` qayta yurmadi) —
      `touch src-tauri/build.rs` bilan qayta qurildi.
- [x] O'rnatuvchi: `Baraka Dastur_0.1.0_x64-setup.exe`, 17 919 938 bayt,
      SHA-256 `C1401D80D40461153DC50BEF4BDDF2765567DCAA1EFE91089C4E60376697899C`.
- [x] `/S` o'rnatish (eski 0.1.0 ustidan), `uninstall.exe /S` (exe va Start menyu yorlig'i qolmadi), qayta
      o'rnatish — hammasi exit 0. Ishga tushirish 3 marta: asosiy oyna 52–88 ms, `WM_CLOSE` dan keyin jarayon
      to'liq tugadi (fon jarayon 0).
- [x] GUI (dev build): yangi belgi yon panel va qulf ekranida, 7 bob yangi sarlavhalar bilan, 1-bob matni,
      «Oilaviy zaxira» kartasi — «Taqsimlash» to'g'ri hisobladi (1 000 $ × 12 650).
- [ ] Kod imzolash — sertifikat yo'q (5-bo'lim). SmartScreen ogohlantirishi chiqadi.
- [ ] Haqiqiy 150/200 % DPI va High Contrast — **foydalanuvchi** (3- va 7-bo'lim).
