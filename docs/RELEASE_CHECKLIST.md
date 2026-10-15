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

- [ ] `pnpm build` — NSIS o'rnatuvchisi `src-tauri/target/release/bundle/nsis/` da chiqadi.
- [ ] O'rnatuvchi sessiyasi jurnalida xato yo'q; silent o'rnatish (`/S`) ishlaydi.
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
