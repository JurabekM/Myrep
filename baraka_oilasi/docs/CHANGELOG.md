# CHANGELOG

## [Unreleased] — 2-sessiya

### O'zgardi
- **Dizayn:** standart mavzu — Claude Code dark theme uslubi (foydalanuvchi qarori): `tokens.json` da `defaultTheme: "dark"`, yangi `sidebar` va `accentText` tokenlari, barcha juftliklar WCAG AA bo'yicha hisoblangan; light — `data-theme="light"`. Tauri oynasi `theme: Dark` va `#262624` fon (oq chaqnashsiz), ikonka to'q rangda.
- Qoida Myrep ildizidagi `CLAUDE.md` ga yozildi — keyingi barcha loyihalar uchun.

### Qo'shildi
- **Y6 `baraka-pdf`:** typst 0.15 kutubxona sifatida, o'rnatilgan Noto Sans/Serif (OFL), ma'lumot faqat `data.json` orqali (typst kod in'eksiyasi yo'q — test bilan), deterministik chiqish (sana, ident, yaratuvchi qotirilgan), chainHead QR (SVG) va qisqa kod bloki, uz/uz-Cyrl/ru matnlari `cargo xtask i18n` dan; PNG snapshot'lar `target/pdf-snapshots/`.
- **Qarz tilxati** (U8 ning birinchi qismi): `App::render_loan_receipt` — foizsiz, to'lov rejasi majburiy, jadval yig'indisi = summa, sanalar tartibi, bir tomon ikki marta bo'lmaydi; sana `15.11.2026` yoki `2026-11-15` (yadroda o'qiladi). Desktop: «Qarz tilxati» ekrani, `export_loan_receipt` — PDF tizimning «Saqlash» oynasi orqali (fayl yo'li frontendga berilmaydi). Android: `BarakaCore::render_loan_receipt`.
- Desktop workspace build artefaktlari umumiy `target/` da (yadro ikki marta qurilmaydi).

### Tuzatildi
- WebKitGTK'da `type="date"` maydoni kalendar ochib, klaviatura kiritishini to'sar edi → sana matn maydoni, o'qish yadroda.
- CI (Windows core): `openssl-src` Git Bash perl'i bilan yig'ilmas edi → `OPENSSL_SRC_PERL` Strawberry Perl'ga yo'naltirildi.

## 1-sessiya: poydevor va Uy makoni yadrosi

### Qo'shildi — hujjatlar
- `docs/BARAKA_OILASI.md` v1.0 — bosh loyiha prompti; `docs/adr/0001` (umumiy Rust yadro), `docs/adr/0002` (versiyalar).
- `docs/OPEN_QUESTIONS.md` — mahsulot, oila va maxfiylik, diniy, yuridik va texnik savollar.
- `docs/uy/` — «Baraka daftari» SPEC v0.8, MVP rejasi va desktop prompti (legacy, o'zgarishsiz).

### Qo'shildi — yadro (`core/`)
- **Y1:** Cargo workspace (Rust 1.97, qat'iy lint'lar), `cargo xtask` (i18n → ARB + i18next, lotin→kirill transliteratsiya, taqiqlangan iboralar linteri, dizayn tokenlari → CSS/Tailwind + Dart, oracle tekshiruvi), CI workflow.
- **Y2 `baraka-money` (no_std):** valyuta exponent'lari (KRW = 0), `round_half_up` (simmetrik), `allocate` (manfiy summa simmetriyasi), `percent_of`, FX, NBSP formatlash, `format_plain`, `format_percent_bp`, kiritishni parse qilish; proptest invariantlari.
- **Y3 `baraka-journal` (no_std):** RFC 8785 JCS, whitelist v1, SHA-256 zanjiri, `verify_chain`, qisqa kod.
- **Y4 `baraka-security`:** DB kaliti PIN/RECOVERY/BIO slotlarida (XChaCha20-Poly1305), KEK = HKDF(platforma siri ‖ Argon2id), tiklash kodi, saqlanadigan o'sib boruvchi qulflash, `zeroize`.
- **Y5 `baraka-storage`:** SQLCipher, sxema v1 (17 jadval), jurnal triggerlari, makon bo'yicha majburiy repository'lar, soft delete.
- **`baraka-app`:** sessiya (o'rnatish, ochish, tiklash, avto-qulf), bootstrap, daromad + ulush taklifi + progressiv rejim, «Kelajagim» (friction bilan pul olish), xarajatlar, oylik audit (qoldiqni hisobga oladigan izohsiz summa, sadaqa havasdan tashqari), kelishuvlar, faqat keeper yozadigan jurnal (NFC), zanjir tekshiruvi, qarz simulyatori, o'zgarish hodisalari.
- **Domen:** `baraka-domain-uy` (ulush, streak, audit, qorovul pul, inflyatsiya, darvoza, amortizatsiya, 70/20/10, sheriklik taqsimoti, katta foyda, qutqarilgan pul), `baraka-agreements` (9 savol to'liqligi va validatsiya kodlari).
- **Vektorlar:** 16 suite, 81 case; raqamli suite'lar mustaqil Python oracle bilan generatsiya va tekshiriladi.

### Qo'shildi — ilovalar
- **Desktop (`apps/desktop`):** Tauri 2 adapteri (19 command, har biri uchun aniq capability), qat'iy CSP, `contentProtected`, keyring, avto-qulf hodisasi; `tauri-specta` bilan generatsiya qilingan `bindings.ts`; React 19 + TanStack Query + Tailwind v4 UI: sozlash (tiklash kodi), qulf, bosh sahifa, daromad (Ctrl+N, ulush taklifi), Kelajagim, xarajatlar, oylik audit, qarzdan chiqish; Ctrl+L. Linux'da yig'ildi va Xvfb'da haqiqiy oqim tekshirildi.
- **Android (`core/bindings/flutter`):** FRB uchun `BarakaCore` API sirti (desktop bilan bir xil use-case'lar). Flutter ilovasi va Kotlin qismi — keyingi sessiya (bu muhitda Flutter SDK yo'q). `apps/android/lib/l10n/*.arb` va `tokens.g.dart` allaqachon generatsiya qilinadi.

### Hal qilindi
- OQ-T2 (`tauri-specta` RC qotirildi), OQ-T3 (`chrono`).
