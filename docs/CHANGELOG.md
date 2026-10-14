# O'zgarishlar tarixi

Format: [Keep a Changelog](https://keepachangelog.com/uz/1.1.0/) ruhida. Versiya: [SemVer](https://semver.org/lang/uz/).

## [Unreleased]

### D2 — `money` crate va test vektorlari runner'i (2026-10-14)

**Qo'shildi**

- `crates/money` (paket `baraka-money`, kodda `money`):
  - `Money` — butun minor birliklar (tiyin, sent) va valyuta; `checked_add`/`checked_sub` valyuta aralashuvini va chegaradan oshishni xato bilan qaytaradi.
  - `Currency` — UZS, USD, EUR, RUB; minor birlik ikki xonali.
  - `round_half_up_div` — loyihadagi yagona yaxlitlash joyi (yarmi noldan uzoqqa).
  - `allocate` — largest remainder usuli: qismlar yig'indisi aniq teng, teng kasrda kichik indeks ustun, manfiy summa simmetrik.
  - `percent_of` — basis points (1 % = 100 bp) bo'yicha foiz.
  - `FxRate` + `convert` — kurs kasr sifatida (`rate_num / rate_den`), yarmi noldan uzoqqa yaxlitlanadi.
  - `format_money` — `uz` va `ru` lokallari: guruhlash bo'linmas bo'sh joy bilan, kasr faqat tiyin nolga teng bo'lmasa, `soʻm` (U+02BB) / `сум`, `$`, `€`, `₽`.
  - `MoneyError::code()` — barqaror kodlar (`CURRENCY_MISMATCH`, `OVERFLOW` va hokazo).
- `crates/vectors` (paket `baraka-vectors`, kodda `vectors`):
  - suite yuklovchi: `spec/test-vectors/*.json` ni o'qiydi;
  - pul runner'lari: `allocate` (5 ta), `percent_of` (2 ta), `fx_convert` (5 ta), `money_format` (8 ta) — jami 20 ta vektor. Har bir natija `expected` bilan TO'LIQ solishtiriladi;
  - qoplanmagan vektor fayli bo'lsa, `har_bir_vektor_fayli_runner_bilan_qoplangan` testi qizil bo'ladi.
- `spec/test-vectors/` — to'rtta D2 suite (`allocate`, `percent_of`, `fx_convert`, `money_format`) mobil repo'dagi fayllarning bayt-bayt nusxasi (sha256 mos).
- Xususiyat testlari (proptest, har biri 256 ta tasodifiy holat): taqsimot yig'indisi aniq teng; ishora saqlanadi; har bir qism aniq ulushdan bir minor birlikdan ko'p og'maydi; nisbati nol bo'lgan qism nolga teng; `percent_of` = `allocate([bp, 10000 − bp])[0]`; yaxlitlash simmetrik.
- CI: alohida «Pul vektorlari» qadami va `coverage` job (`baraka-money` qamrovi ≥ 95 %).
- README: tekshiruv buyruqlari va qamrov o'lchash.

**Natijalar**

- Testlar: 32 ta unit, 6 ta xususiyat, 5 ta runner — hammasi o'tdi.
- Qamrov: `baraka-money` satrlari 99,80 % (talab ≥ 95 %).
- Mutatsiya sinovi: tie-break qoidasi ataylab buzildi — `alloc-001`, `alloc-003`, `alloc-004` qizil bo'ldi. Qoida qaytarilgach, hammasi yana yashil.
- `cargo fmt --check`, `clippy -D warnings`, Prettier — toza.

**Qarorlar va sabablar**

- **Yaxlitlash — yarmi noldan uzoqqa, manfiy uchun ham.** Vektor `fx-004` talab qiladi: −12 650,5 → −12 651. Mobil `MoneyRounding.defaultMode` bilan bir xil.
- **Manfiy summa.** `allocate` modulni taqsimlaydi va ishorani qo'yadi (`dist-003`: −300 000 000 kapital bo'yicha → −225 000 000 / −75 000 000).
- **`percent_of` oraliqdan tashqarida** (masalan, 120 % ustama): `round_half_up(amount × bp / 10 000)`. Desktop spec'da bu holat yo'q; mobil ilova xuddi shunday qiladi. 0..=10 000 oralig'ida ikkala ta'rif teng — xususiyat testi buni tasdiqlaydi.
- **Vektorlar nusxasi.** Ikki repo bitta vektor to'plamini ishlatadi (DESKTOP_PROMPT.md 5.1). Hozircha nusxa; sinxronlash usuli ochiq (docs/OPEN_QUESTIONS.md, 2-band).
- **Bog'liqlik yo'nalishi.** `money` vektorlarga bog'lanmaydi; runner `vectors` da. Shu sababli tsikl va ikki nusxadagi tiplar yo'q.
- **Yangi crate'lar** (ADR bo'yicha sabablari): `thiserror` — xatolar (ADR: xatolar); `time` — `FxRate.date` kurs sanasi (ADR: sana); `proptest` — xususiyat testlari (ADR: testlar); `serde`, `serde_json` — vektor JSON'ini o'qish (faqat `vectors`).
- **Vositalar.** `cargo-llvm-cov` — qamrov o'lchash (bog'liqlik emas, CI'da o'rnatiladi).

**Hali yo'q (keyingi bosqichlar)**

- Kiritilgan matnni summaga aylantirish (`MoneyParser`) — D4 (forma kiritish) da.
- `Money` DTO (`{ minor: string, currency, formatted }`) — `src-tauri` commandlarida, D4 da.
- Qolgan 10 ta vektor suite'i (`amortization`, `personal_inflation`, `emergency_target`, `readiness_gate`, `journal_chain`, `profit_spike`, `profit_distribution`, `agreement_completeness`, `debt_recovery_split`, `unexplained_gap`) — mos vazifalarda runner bilan birga qo'shiladi.
- CODEOWNERS — vektor o'zgarishi ikki platforma egasining ma'qulligini talab qiladi (DESKTOP_PROMPT.md 5.4); egalar aniqlangach.

### D1 — Workspace, Tauri skeleti, CI (2026-10-14)

**Qo'shildi**

- Cargo workspace (Rust 1.97.1, `rust-toolchain.toml`) va pnpm workspace (pnpm 12.11.2, Node 24).
- Tauri 2.12 ilova skeleti (`src-tauri/`): asosiy oyna, `get_app_info` command, NSIS o'rnatuvchisi (`currentUser` — administrator huquqi shart emas).
- TypeScript bindinglari tauri-specta orqali (`ui/src/bindings/bindings.ts`). `cargo test` va debug ishga tushirish ularni yangilaydi; CI farqni tekshiradi.
- React 19 + TypeScript (strict) + Vite 8 + Tailwind CSS 4 + Radix UI (ToggleGroup, Tooltip) + i18next (`uz` asosiy, `ru`).
- Qorong'i tema (Claude Code desktop uslubi). Noto Sans shrifti ilova ichida — `ʻ` (U+02BB) va `ʼ` (U+02BC) belgilari to'g'ri chiqadi.
- Navigatsiya: 11 ta bo'lim. Tayyori ikkita — «Bosh sahifa» va «Sozlamalar». Qolganlari o'chirilgan, sababi (keyingi bosqichda qo'shiladi) tooltip'da ko'rsatiladi.
- Ilova ikonkasi: `scripts/make_icon.py` (Pillow) — krem «daftar» va geometrik sakkiz burchakli yulduz. 16–256 px uchun alohida chiziladi.
- Xavfsizlik: qat'iy CSP (`script-src 'self'`, tashqi manba yo'q), minimal capabilities (`core:default` va faqat `allow-get-app-info`), release'da DevTools yo'q.
- Testlar: Rust — 3 ta (JSON kontrakt, yig'ish profili, bindinglar). Frontend — 11 ta (ilova qobig'i, tooltip, til almashinuvi, xato holati, tarjima kalitlari bir xilligi, ikonka siyosati).
- CI (`.github/workflows/ci.yml`): frontend (format, lint, typecheck, test); Rust — Windows, macOS, Ubuntu (fmt, clippy `-D warnings`, test, bindinglar farqi); Windows NSIS build (artifact).
- Hujjatlar: `docs/SPEC.md`, `docs/DESKTOP_PROMPT.md`, `docs/MVP_PLAN.md`, `CLAUDE.md`, `README.md`, `docs/CHANGELOG.md`, `docs/OPEN_QUESTIONS.md`.

**Qarorlar va sabablar**

- **Tauri 2.12** (ADR). Tauri 3 alpha ishlatilmaydi.
- **TypeScript 6.0.3**, 7.0 emas: TypeScript 7 `typescript-eslint` bilan mos emas.
- **ESLint 10**, `eslint-plugin-jsx-a11y`siz: a11y plagini ESLint 10 bilan mos emas. A11y tekshiruvi Testing Library'ning rol bo'yicha so'rovlari orqali.
- **`common-controls-v6` o'chirildi** (`default-features = false`): test binary'lari `STATUS_ENTRYPOINT_NOT_FOUND` bilan yiqilardi. Ilova binary'si manifestni baribir oladi.
- **`style-src 'unsafe-inline'`**: Radix va popper komponentlari inline uslub qo'yadi. `script-src` qat'iy.
- **NSIS tillari**: `Uzbek`, `Russian`, `English`. NSIS 3.11 da `Uzbek.nlf` bor.
- **pnpm 12 minimal chiqarilish yoshi**: yangi chiqqan ikki paket (`lucide-react@1.56.0`, `@testing-library/user-event@14.6.8`) istisnoga qo'shildi (`pnpm-workspace.yaml`). Keyinroq tekshiriladi (docs/OPEN_QUESTIONS.md, 8-band).
- **Ikonkalarda** odam, hayvon, cho'chqa, qimor, alkogol, bank binosi va foiz belgisi ishlatilmaydi. Taqiq `icon-policy.test.ts` da tekshiriladi.

**Bog'liqliklar va sabablari**

- Rust: `tauri` 2.12, `tauri-build` (ilova build skripti), `tauri-specta` + `specta` (`=2.0.0-rc.25`, TS bindinglari — ADR), `specta-typescript` 0.0.12 (bindinglarni yozish), `serde` (DTO), `tracing` + `tracing-subscriber` (log — ADR), `serde_json` (faqat testlar).
- npm: `react`, `react-dom` 19 (ADR: React 18+); `vite` 8, `@vitejs/plugin-react`; `typescript` 6.0 (strict); `tailwindcss` 4 + `@tailwindcss/vite`; `@radix-ui/react-toggle-group`, `@radix-ui/react-tooltip` (ADR: Radix primitivlari); `i18next`, `react-i18next` (ADR); `@tanstack/react-query` (ADR); `zustand` (ADR: faqat UI holati); `@tauri-apps/api` (bindinglar uchun) va `@tauri-apps/cli` (ADR: Tauri); `lucide-react` (ikonkalar — ADR'da yo'q, qo'shildi, ikonka siyosati bilan); `@fontsource-variable/noto-sans` (shrift ilova ichida); `vitest`, `jsdom`, `@testing-library/*`; `eslint`, `typescript-eslint`, `eslint-plugin-react-hooks`, `globals`, `@eslint/js`; `prettier` (ADR).
- Python (faqat ikonka uchun): `Pillow`.

**Ma'lum cheklovlar**

- GitHub Actions CI hali GitHub'da ishga tushirilmagan: repo'da push qilinmagan. Uning qadamlari mahalliy Windows muhitida qo'lda takrorlangan.
- O'rnatuvchi kod imzolanmagan — SmartScreen ogohlantirishi chiqishi mumkin.
- Silent o'rnatish sinalgan (`/S`). Interaktiv o'rnatish va til tanlovi oynasi qo'lda sinalmagan.
- Haqiqiy oynada til almashinuvi tugmasi sichqoncha avtomatizatsiyasi bilan to'liq tasdiqlanmadi. Bu jsdom testlari bilan qoplangan; E2E (WebDriver) keyingi bosqichda.
- Mobil (Flutter) loyiha bu repo'da yo'q; `spec/test-vectors/` faqat to'rtta D2 suite'iga ega (docs/OPEN_QUESTIONS.md, 1–2-bandlar).
