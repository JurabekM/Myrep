# O'zgarishlar tarixi

Format: [Keep a Changelog](https://keepachangelog.com/uz/1.1.0/) ruhida. Versiya: [SemVer](https://semver.org/lang/uz/).

## [Unreleased]

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
- Mobil (Flutter) va `spec/test-vectors/` bu bosqichda yo'q — keyingi bosqichlar (docs/OPEN_QUESTIONS.md, 1–2-bandlar).
