# CHANGELOG

## D1 + D2 — Poydevor (desktop)
- Cargo workspace (`desktop/`), `money` va `vectors` crate'lari, `src-tauri` (Tauri 2 + tauri-specta), `ui` (React 18 + Vite + TS strict + Tailwind 4 + i18next uz/ru + TanStack Query).
- `money`: `Money`, `Currency`, `allocate` (largest remainder), `percent_of`, `round_half_up`, `FxRate`, `format_money`. `float_arithmetic`, `unwrap_used`, `expect_used` — `deny`.
- `spec/test-vectors`: `allocate`, `percent_of`, `fx_convert`, `money_format`. Runner: `cargo test -p vectors`.
- CSP qat'iy (`unsafe-eval`/`unsafe-inline` yo'q), capabilities faqat `core:default`, shell/http/fs pluginlari yo'q.
- CI: `.github/workflows/baraka-desktop.yml` (fmt → clippy → test → vektorlar → frontend → build, qamrov ≥95%, NSIS).
- Kechiktirildi (keyingi vazifalar): `amortization.json` (D10), `profit_distribution.json` (D12) va boshqa suite'lar.

## D3 — Xavfsizlik va shifrlangan baza
- `security`: Argon2id (PIN) + OS keyring qurilma siri → HKDF → XChaCha20-Poly1305 bilan DB kalitini o'rash. Ikki omil: keyring o'chsa PIN bilan ochilmaydi, keyring bo'lsa ham PIN'siz ochilmaydi. Lockout (3-xatodan keyin 30 s, ikki baravar o'sadi, ≤1 soat, qayta ishga tushganda ham saqlanadi), `AutoLock` (5 daqiqa, sozlanadi), `zeroize`.
- `storage`: SQLCipher (`bundled-sqlcipher-vendored-openssl`), `rusqlite_migration`, sxema v1 (households, members, categories, incomes, expenses, assets + asset_snapshots, vault_transactions, allocation_rules, obligations, fx_rates), umumiy `Record` repository (insert/get/list/update/soft_delete, optimistik `version`).
- `domain`: `Meta`, `Clock`, `IdGen` (UUIDv7), enumlar va sxema v1 entity'lari.
- Tauri: `vault_state`, `setup_pin`, `unlock`, `lock`, `activity` commandlari; 5 soniyalik avto-qulf oqimi; `contentProtected` oynada yoqilgan.
- UI: `Gate` (qulfda kontent render qilinmaydi), `LockScreen` (PIN o'rnatish/ochish, kutish soniyalari), `Ctrl+L`.
- Kechiktirildi: Windows Hello (ixtiyoriy, OPEN_QUESTIONS), PIN almashtirish, tashqi keyring o'zgarishi bilan tiklash oqimi.
