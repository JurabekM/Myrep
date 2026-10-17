# Reliz tekshiruvi (Baraka Daftari desktop)

Bu ro'yxat har reliz oldidan bajariladi. Avtomatik qismlar CI va mahalliy buyruqlar bilan; qo'lda qismlar
o'rnatuvchini haqiqiy Windows mashinasida sinashni talab qiladi.

## 1. Avtomatik tekshiruvlar

- [ ] `pnpm lint && pnpm typecheck && pnpm test` — yashil.
- [ ] `cargo test --workspace` — yashil (bindinglar ham yangilanadi; `git diff ui/src/bindings` bo'sh bo'lishi kerak).
- [ ] `cargo clippy --workspace --all-targets -- -D warnings` — yashil.
- [ ] Vektorlar: `spec/test-vectors/SHA256SUMS` testi (`mobil_bilan_umumiy_vektorlar_manifestga_mos`) yashil.
- [ ] `pnpm format:check` — yashil.

## 2. O'rnatuvchi

- [x] `pnpm build` — NSIS o'rnatuvchisi `<CARGO_TARGET_DIR>/release/bundle/nsis/` da chiqadi (2026-10-16: `Baraka Daftari_0.1.0_x64-setup.exe`, 16,9 MiB).
- [x] Silent o'rnatish (`/S`) ishlaydi (2026-10-16, exit 0, `%LOCALAPPDATA%\Baraka Daftari`, reestr `Uninstall\Baraka Daftari` 0.1.0); `uninstall.exe /S` ham. **Eslatma:** `displayLanguageSelector` yoqiq bo'lsa `/S` til dialogida qotadi — o'chirilgan.
- [ ] O'rnatuvchi hajmi va versiyasi `CHANGELOG` dagi raqamga mos.

## 3. Qo'lda sinov (haqiqiy Windows, o'rnatilgan ilova)

- [ ] Birinchi ishga tushirish: PIN o'rnatiladi, qulf ekrani ishlaydi, noto'g'ri PIN'da kechikish bor.
- [ ] Har bir menyu bandi bosiladi; ishlamaydigan tugma yo'q (CLAUDE.md, «Tugma ish bajarsin»).
- [ ] Byudjet: obuna qo'shish, «ishlatdim», bekor qilish; konvert qo'shish, hafta yakuni; «Kelajagim»ga o'tkazish (ortiqcha summa rad etilishi).
- [ ] Xarajatlar: oy xulosasi, toifa o'zgartirish, havas chegarasi va rozilik, bayonnoma PDF (o'zbekcha belgilar to'g'ri).
- [ ] Kelajagim, audit, qarzlar — ma'lumot saqlanib qoladi (ilovani qayta ishga tushirgandan keyin).
- [ ] Zamonaviy DPI (150%, 200%) va High Contrast rejimida matn kesilmaydi.
- [ ] Oyna yopilgach jarayon to'liq tugaydi (fon jarayon qolmaydi).

## 4. Ma'lumot xavfsizligi

- [ ] Loglarda summa, ism yoki izoh yo'q (`CLAUDE.md`).
- [ ] Baza fayli kalitsiz ochilmaydi; kalit fayli bazadan ajratilgan.
- [ ] Jurnal (`journal_entries`) `UPDATE`/`DELETE` ni rad etadi (sxema v8 triggerlari).

## 5. Kod imzolash (tashqi shart — to'xtaydigan joy)

- [ ] Windows kod imzolash sertifikati olingan va `tauri.conf.json` ga ulangan. **Hozircha yo'q** —
      imzolanmagan o'rnatuvchida SmartScreen ogohlantirishi chiqadi. Sertifikat kelguncha bu reliz «ichki sinov» darajasida.
- [ ] Imzolangan updater manifesti yaratilgan (sertifikat bilan birga).

## 6. Hujjat

- [ ] `docs/CHANGELOG.md` shu reliz uchun yangilangan.
- [ ] `docs/OPEN_QUESTIONS.md` — ochiq bandlar ko'rib chiqilgan (mahsulot qarorlari «Hal qilingan» bo'limida).
- [ ] Ma'lum cheklovlar foydalanuvchiga aytilgan (CHANGELOG'dagi «Ma'lum cheklovlar» bo'limlari).

## 7. D11–D15 qo'shimchalari

- [x] Onboarding: birinchi ochilishda 5 qadam ko'rinadi, «O'tkazib yuborish» va Esc ishlaydi, qayta ochilganda chiqmaydi (`localStorage: baraka.onboarding`). _(dev build, 2026-10-16)_
- [ ] Accessibility: `Tab` bilan birinchi fokus — «Asosiy mazmunga o'tish» havolasi; har bir tugma va maydon klaviaturadan yetib boriladi; fokus halqasi ko'rinadi.
- [ ] Windows High Contrast (`forced-colors`): chegaralar va fokus ko'rinadi; `prefers-reduced-motion` da animatsiya yo'q; 125 %, 150 %, 200 % DPI da matn kesilmaydi, jadvallar gorizontal aylanadi.
- [x] Marosimlar: stsenariy taqqoslash, qarzli reja muhokamasiz tasdiqlanmaydi, smeta PDF ochiladi.
- [x] Sheriklik: darvoza yopiq — kapital kirituvchi yaratolmaydi; rozilik; buyout jadvali; kassa daftari davr yopish va taqsimot; davr hisoboti PDF.
- [x] Kelishuvlar markazi: jadval filtri, hodisa bandi, ko'rik sessiyasi va bayonnoma PDF (`chain_head`), nizo → taqsimot bloklanadi, hakam papkasi PDF (mundarija bor), oilaviy shablon PIN bilan.
- [x] `.baraka`: eksport → fayl bor; boshqa profilga import → ko'rik → qo'llash; noto'g'ri parol aniq xabar; jurnal fork ssenariysi (ikki qurilmada farqli yozuv) bloklanadi.
- [x] Sovuq start < 1,5 s (release): 2026-10-16, o'rnatilgan `baraka-daftari.exe`, jarayon boshlanishidan asosiy oyna dastagigacha **216 ms** (`Start-Process` + `MainWindowHandle` kutish; SSD, Windows 10). Oyna mazmuni (WebView2) bundan bir oz keyin chiziladi.
- [ ] E2E (`e2e/anvar.e2e.ts`, tauri-driver): yashil — yoki qo'lda o'tilgani sana bilan qayd etilgan: ______.
- [ ] Kod imzolash: sertifikat bo'lsa `bundle.windows.certificateThumbprint` (yoki `signCommand`) `tauri.conf.json` da; `signtool verify /pa` yashil; updater manifesti (`tauri-plugin-updater` kiritilganda) imzolangan. **Sertifikat yo'q — bu band to'xtab turibdi.**
