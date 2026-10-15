# CHANGELOG

## [Unreleased] — 1-sessiya: poydevor va Uy makoni yadrosi

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
