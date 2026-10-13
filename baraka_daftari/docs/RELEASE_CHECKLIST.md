# Reliz tekshiruv ro'yxati

Belgilar: ✅ shu repoda avtomatik tekshiriladi · 🟡 qisman · ⬜ qo'lda/tashqi, hali bajarilmagan.

## A. Avtomatik (har commitda)
- ✅ `cargo fmt --all --check`, `cargo clippy --workspace --all-targets -- -D warnings`
- ✅ `cargo test --workspace` (golden vektorlar `spec/test-vectors/` — barcha pul funksiyalari; servis testlari; round-trip eksport/import; «Anvar» zanjiri)
- ✅ `pnpm --dir desktop/ui typecheck && lint && test && build` (jumladan i18n kalitlari uz/ru, taqiqlangan iboralar filtri, axe)
- ✅ Frontendda pul hisobi yo'q; `f64` pul uchun yo'q (clippy `float_arithmetic`)
- ✅ Yopilgan davr o'zgarmasligi (servis + DB triggeri), shifrlangan baza (fayl SQLite sarlavhasiga ega emas)

## B. Reliz to'siqlari (kod bilan hal bo'lmaydi)
- ⬜ **Sheriklik shartnomasi shabloni yurist va ulamo tasdig'i** → `pdf::TEMPLATES_APPROVED = true`; tekshiruv: `cargo test -p services --test release_gate -- --ignored` (hozir **qizil — atayin**).
- ⬜ Diniy matnlar (`review_status = APPROVED`), tilxat/shartnoma shablonlarining yurist ko'rigi.
- ⬜ Kontent va brend litsenziyasi («Asaxiy Invest» × Abdukarim Mirzayev); qissa matnlari hozir placeholder.
- ⬜ Windows kod imzolash sertifikati (OV/EV) — `docs/SIGNING_AND_UPDATER.md`.
- ⬜ Yangilash kalit juftligi va manifest serveri; updater plaginini ulash.
- ⬜ Maxfiylik siyosati (O'zbekistonning shaxsiy ma'lumotlar to'g'risidagi qonuni).
- ⬜ Mobil ilova bilan `.baraka` mosligi: umumiy fayl bilan o'zaro sinov (OPEN_QUESTIONS 71).
- ⬜ Sobir hoji maslahatlari (uz/ru) yurist va ulamo ko'rigidan o'tishi (OPEN_QUESTIONS 106); önizleme darvozasi relizda shablon tasdig'i bilan birga ochiladi (107).

## C. Windows'da qo'lda tekshiriladi (bu sessiyada Linux konteyner — bajarilmagan)
- ⬜ NSIS installer toza Windows 10/11 da administratorsiz o'rnatiladi; o'chirish ma'lumotni o'chirmaydi (yoki so'raydi).
- ⬜ Imzolangan installer SmartScreen ogohlantirishisiz (sertifikat bo'lgach).
- ⬜ Sovuq start < 1,5 s (qulf ekrani ko'rinishigacha): Rust qismi (baza ochish + migratsiya) `tests/startup_budget.rs` da ~40 ms (debug, Linux); oyna + WebView2 o'lchanmagan.
- ⬜ `tauri-driver` E2E (`desktop/e2e`) yashil: `anvar` va `musharaka` (Anvar × Dilshod) spetsifikatsiyalari yozilgan va TypeScript bo'yicha tekshirilgan, lekin Windows'da hali ishga tushirilmagan.
- ⬜ DPI 100/125/150/200% — hech bir matn kesilmaydi, jadval va dialoglar sig'adi.
- ⬜ Windows High Contrast (Aeroning 4 mavzusi): fokus ko'rinadi, tugma/maydon chegaralari, svetofor hukmi matn bilan o'qiladi (`index.css` `forced-colors` bloki yozilgan, sinalmagan).
- ⬜ Klaviatura: Tab tartibi, `Ctrl+N/L/K/P`, `Esc`; Narrator (ekran o'quvchi) bilan asosiy oqimlar.
- ⬜ Rang kontrasti (WCAG AA) ikkala mavzuda — axe jsdom'da kontrastni hisoblamaydi.
- ⬜ Tray, global hotkey `Ctrl+Alt+B`, bildirishnomalar; qulfli holatda summa ko'rinmasligi; ekran yozib olishdan himoya (`contentProtected`).
- ⬜ OS dialoglari: PDF (shartnoma, tilxat, smeta, davr hisoboti) va `.baraka` saqlash/ochish; chop etish.
- ⬜ Kelishuv PDF'lari: shartnoma, ko'rik bayonnomasi («Bayonnoma PDF»), hakam ish papkasi («Hakam ish papkasi (PDF)») — OS «saqlash» oynasi va PDF mundarijasi (sahifa raqamlari) ochiladi.
- ⬜ Sheriklik ustasi jonli önizlemasi (`iframe`, PDF blob-URL) WebView2 da ko'rinadi; 150% DPI da forma va o'ng ustun sig'adi (OPEN_QUESTIONS 108).
- ⬜ Import: zanjiri ayrilgan (fork) `.baraka` fayl rad etiladi va hisobot ko'rinadi; buzilgan jurnal fayli rad etiladi (D14).
- ⬜ «Katta foyda» tasdig'i va nizo bloki (davr yopish, taqsimot) qo'lda sinaladi: ogohlantirish matni, katakcha, tugma holati.
- ⬜ Oilaviy kelishuv: shablon tanlash, kattalarning PIN bilan tasdig'i (bola va PIN'siz kattalar tasdiqlay olmasligi), faollashtirish — WebView2 da qo'lda sinaladi.
- ⬜ Yillik yangilash: 30 kunlik eslatma va «O'zgarishsiz tasdiqlash» — tomonlar qayta imzolashi va sheriklikning qoralamaga qaytishi qo'lda tekshiriladi.
- ⬜ Rus tili: barcha ekranlar ko'zdan kechiriladi (kalit to'liqligi avtomatik, uslub — qo'lda).
- ⬜ Accessibility: axe faqat ba'zi sahifalarda (Almashish, Hunardan ishga, Sheriklik, Onboarding); qolgan sahifalar qo'lda.

## D. Reliz amallari
1. `docs/CHANGELOG.md`, versiya (`tauri.conf.json`, `Cargo.toml`).
2. Toza clone'da A bo'limi.
3. B bo'limi to'siqlari yopilganini tasdiqlash (`--ignored` test yashil).
4. Imzolash va manifest (`docs/SIGNING_AND_UPDATER.md`).
5. C bo'limi Windows'da; natijalarni shu faylga yozish.
