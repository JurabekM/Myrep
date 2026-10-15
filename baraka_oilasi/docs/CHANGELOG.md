# CHANGELOG

## [Unreleased] — 2-sessiya

### O'zgardi
- **Dizayn:** standart mavzu — Claude Code dark theme uslubi (foydalanuvchi qarori): `tokens.json` da `defaultTheme: "dark"`, yangi `sidebar` va `accentText` tokenlari, barcha juftliklar WCAG AA bo'yicha hisoblangan; light — `data-theme="light"`. Tauri oynasi `theme: Dark` va `#262624` fon (oq chaqnashsiz), ikonka to'q rangda.
- Qoida Myrep ildizidagi `CLAUDE.md` ga yozildi — keyingi barcha loyihalar uchun.

### Qo'shildi — U9: «Qarzdan chiqish» 70/20/10, rejalovchi, «Qarzsiz kun» (V11 / D10)
- **Vektorlar (avval oracle):** `payoff_projection` (11 case: Anvar avtokrediti odatiy/1,6 mln/2,4 mln + 1% komissiya, to'lovlar tarixidan holat, kechikkan oylar, differensial, ustamali nasiya, foizsiz reja, 0% stavka, salbiy holatlar) va `payoff_plan` (bir nechta qarz: standart va qo'lda tartib). Yangi prognoz eski `amortization` vektorlari bilan bir xil natija berishi oracle selftest'ida tekshiriladi (qoldiq aniq 0). `debt_status` ga muddatidan oldingi to'lov case'lari qo'shildi.
- **`domain-uy::payoff`:** holat to'lovlar tarixidan qayta hisoblanadi — bank qarzida muddatidan oldingi to'lov o'z sanasida asosiy qarzni kamaytiradi («muddatni qisqartirish»), ustamali/foizsiz rejada reja oxiridan yopiladi (ustama tejalmaydi — buni ochiq ko'rsatamiz). Kalendar oylari bo'yicha prognoz, jarima/komissiya (`fee_bp`), bir nechta qarzning umumiy rejasi (qo'shimcha to'lov tartib bo'yicha birinchi ochiq qarzga), oylik yig'indilar (grafik va jadval uchun), yopish tartibi: qo'lda → foizli (eng qimmati) → foizsiz (muddati yaqini).
- **U8 holati endi shu modeldan:** qoldiq, keyingi to'lov, kechikkan summa, «Qarzsiz kun» va haqiqiy narx bank qarzida muddatidan oldingi to'lovni hisobga oladi (tejalgan foiz haqiqiy narxdan ayriladi).
- **Sxema v3 (`003_recovery.sql`):** `budget_settings` (makon rejimi, ulushlar yig'indisi 100% va jamg'arma ≥ 1% — DB CHECK bilan ham), `debt_contributors`, `sellable_items`, `debts.prepayment_fee_bp`, `repayments.contributor_id`.
- **Use-case'lar:** `budget_mode` / `set_budget_mode` (70/20/10, sozlanadi; jamg'arma 0 bo'lmaydi; faol qarzsiz yoqilmaydi; majburiy qarz to'lovlari ro'zg'or ulushi ichida ko'rsatiladi), `payoff_planner` (odatiy va tezlashtirilgan «Qarzsiz kun», «N oy erta», tejalgan foiz − komissiya, har bir qarz, grafik nuqtalari, oyma-oy jadval; qo'shimcha to'lov — rejimdagi 20% ulush yoki qo'lda), `set_debt_order` / `reset_debt_order`, `add_contributor` (to'lovda kim to'lagani), `sellable_items` / `add_sellable_item` / `sell_item` (pul bir bosishda qarzga — bitta tranzaksiyada). `record_repayment` endi `RepaymentResultDto` qaytaradi: qarz yopildimi, oxirgi qarzmi, rejim **avtomatik `STANDARD` ga qaytdimi** (o'sha tranzaksiyada), bo'shagan oylik to'lov.
- **Desktop:** «Qarzdan chiqish» ekrani qayta yozildi — rejim kartasi (70/20/10 tahrirlanadi), «Qarzsiz kun» KPI'lari, umumiy qoldiq grafigi (bitta o'q, ikki chiziq, crosshair tooltip; ranglar dataviz validatoridan o'tgan `chart1/chart2` tokenlari), yopish tartibi (↑/↓, «Standart tartib»), oyma-oy jadval, sotiladigan buyumlar. «Qarzlar» ekranida to'lovchilar va «Kim to'ladi», bank qarziga komissiya (bp). Qarz yopilganda nishonlash oynasi va bo'shagan summani «Kelajagim»ga o'tkazish. Bosh sahifada «Qarzsiz kun» kartasi (rejim bilan sanasi ham).
- **Android (FRB):** 9 ta yangi metod.
- **E2E (haqiqiy ilova, Linux):** daromad → avtokredit (1% komissiya) + to'y qarzi → rejim taklifi → yoqish → rejalovchi (6 oy erta) → grafik tooltip → tartibni qo'lda o'zgartirish → buyum sotilib to'y qarziga → to'lovchi Sanjar to'lab qarzni yopdi → nishonlash → «Kelajagim»ga o'tkazish → bosh sahifa «Qarzsiz kun» → qayta ochilganda hammasi joyida.
- **Hali qilinmagan:** «qutqarilgan pul» manbasi (U5 bilan keladi), Dart'dan amortizatsiya vektorlari (Android sessiyasida), to'lovchini ilovaga taklif qilish (MVP'dan keyin).

### Qo'shildi — U8: qarz inventari, haqiqiy narx, friction, tilxat (V10 / D9)
- **Vektorlar (avval oracle, keyin kod):** `debt_plan` (4 xil reja turi + haqiqiy narx, Karim aka misoli: 40 mln → 60 mln, ortiqcha 20 mln = 33,33%), `debt_status` (keyingi to'lov, kechikkan, eslatma ≤ 3 kun), `debt_load`. Rust natijalari oracle bilan birinchi urinishda mos keldi.
- **`domain-uy::debt`:** `build_plan` (`ANNUITY | DIFFERENTIATED | FIXED_MARKUP | MANUAL`; bo'sh reja — `SCHEDULE_REQUIRED`), `true_cost` (jami = ilovagacha to'langan + reja), `goal_coverage_bp` (imkoniyat narxi), `plan_status`, `debt_load_bp`, `evaluate_borrow` («to'xta va o'yla»: `RIBO`, `LUXURY`, `ALTERNATIVE_AVAILABLE`, `LOAD_HIGH`, `LOAD_UNKNOWN` — taqiqlamaydi). `Receivable` da foiz maydoni yo'q: to'liq ochish testi kompilyatsiya darajasida ushlaydi, DTO esa `deny_unknown_fields` bilan `interestBp` ni rad etadi.
- **Sxema v2 (`002_debts.sql`):** `debts`, `receivables` (foiz ustuni yo'q), `repayment_plan_lines`, `repayments` (`journal_entry_id`), `goals`; `agreements.payload_json`.
- **Use-case'lar:** `add_debt`, `preview_borrow_check`, `add_receivable`, `record_repayment`, `debts_overview`, `add_goal`/`delete_goal`. Yangi qarzda (`isNew`) «to'xta va o'yla» javoblari majburiy va qarz yozuvida saqlanadi.
- **Tilxat = `Agreement(type = LOAN)`:** `issue_loan_receipt` bitta tranzaksiyada kelishuv, jurnal `OPENING_BALANCE` (reja qatorlari `refs` da — reja ham xeshlanadi), qarz yoki bergan qarz yozuvini yaratadi. Tilxatga bog'langan to'lovlar jurnalga `REPAYMENT` sifatida yoziladi; qoldiq 0 bo'lsa, qarz va kelishuv yopiladi. `loan_receipt_pdf` — joriy jurnal boshi (QR va qisqa kod) bilan; bazadagi reja jurnaldagidan farq qilsa, chop etilmaydi (`PLAN_JOURNAL_MISMATCH`).
- **Desktop:** yangi «Qarzlar» ekrani (jami qoldiq, oylik yuk, ribo banneri, haqiqiy narx, maqsadga nisbat, to'lov yozish, tilxat PDF, maqsadlar), qarz qo'shish formasi «to'xta va o'yla» bosqichi bilan, «Bergan qarz» formasi (foiz maydonisiz). «Qarz tilxati» ekrani: «Men qarz oldim / berdim», saqlash → «Saqlash» oynasi → tekshirish kodi.
- **Android (FRB):** xuddi shu 9 ta metod `BarakaCore` da.
- **Test:** `every_command_is_permitted` — `bindings.ts` dagi har bir command `build.rs` va `capabilities/main.json` da borligini tekshiradi (E2E paytida topilgan xato: yangi command'lar ruxsat ro'yxatida yo'q edi).
- **E2E (haqiqiy ilova, Linux):** maqsad → Karim akaning to'y qarzi (tarix bilan) → daromad → yangi avtokredit «to'xta va o'yla» bilan → bergan qarz tilxati → PDF → qaytarilgan pul jurnalga → PDF'dagi kod yangilandi → qayta ochilganda ma'lumot joyida.
- Ochiq savol: OQ-P8 (oylik yuk chegarasi 30% va ta'rifi).
- **Hali qilinmagan (U8 doirasida):** ekranda imzo chizish (hozircha «chop etib qo'lda imzolash» rejimi), ikkinchi tomonning o'z telefonida tasdiqlashi (MVP'dan keyin), xato kiritilgan qarzni o'chirish/tuzatish, U6 darvozasiga ulash (U6 da `hasRiboDebt` dan foydalaniladi).

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
