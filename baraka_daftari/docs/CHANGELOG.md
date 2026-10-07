# CHANGELOG

## D1 + D2 — Poydevor (desktop)
- Cargo workspace (`desktop/`), `money` va `vectors` crate'lari, `src-tauri` (Tauri 2 + tauri-specta), `ui` (React 18 + Vite + TS strict + Tailwind 4 + i18next uz/ru + TanStack Query).
- `money`: `Money`, `Currency`, `allocate` (largest remainder), `percent_of`, `round_half_up`, `FxRate`, `format_money`. `float_arithmetic`, `unwrap_used`, `expect_used` — `deny`.
- `spec/test-vectors`: `allocate`, `percent_of`, `fx_convert`, `money_format`. Runner: `cargo test -p vectors`.
- CSP qat'iy (`unsafe-eval`/`unsafe-inline` yo'q), capabilities faqat `core:default`, shell/http/fs pluginlari yo'q.
- CI: `.github/workflows/baraka-desktop.yml` (fmt → clippy → test → vektorlar → frontend → build, qamrov ≥95%, NSIS).
- Kechiktirildi (keyingi vazifalar): `amortization.json` (D10), `profit_distribution.json` (D12) va boshqa suite'lar.
