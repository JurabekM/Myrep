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

## D4 — Daromad, «Kelajagim», audit, «Kimning puli?», bosh sahifa
- **Vektorlar (avval vektor, keyin kod):** `unexplained_gap`, `streak`, `share_suggestion`, `money_parse` (+ runner'lar). Barchasi yashil.
- `money::parse_amount`: foydalanuvchi matni (`8 000 000`, `1500,50`) → minor; frontend pulni hisoblamaydi va parse qilmaydi.
- `domain` (sof): `suggest_share` (foiz / oylik aniq summa), `suggest_rate_increase` (progressiv: 4 hafta streak + 4 hafta shu stavkada → +1%), `compute_streak` (hafta jumadan boshlanadi), `unexplained_gap`, `month_result`, `whose_money`, pul olish pauzasi (`check_confirm`, 24 soat).
- **Sxema v2** (faqat `ADD COLUMN` + 1 jadval; v1 ma'lumotlari saqlanishi testlangan): `vault_transactions.source/income_id`, `obligations.kind/owner/creditor/remaining_minor`, `categories.owner`, `expenses.audit_month`, `withdrawal_requests`.
- Yangi `services` crate: `setup` (xonadon, a'zo, 11 standart kategoriya, «Kelajagim», 5% qoidasi), `income` (taklif + daromad va ajratma bitta tranzaksiyada), `rules`, `vault` (ro'molcha/boshlang'ich balans — bir marta, «o'zingizga to'langan»ga kirmaydi; pauzali pul olish), `audit` (oylik jami almashtiriladi, ikki marta hisoblanmaydi), `obligations` (doimiy to'lovlar + nasiya daftari), `home`.
- Tauri: 17 ta yangi command (`ledger.rs`), sessiya endi `Ctx` va barqaror `device_id` saqlaydi.
- UI: ilova qobig'i + navigatsiya, **bosh sahifa slot arxitekturasi** (birinchi slot — «o'zingizga to'ladingiz»), `Ctrl+N` tez kiritish (summa → Enter), Kelajagim sahifasi, Byudjet sahifasi va audit ustasi (faqat klaviatura: Enter/Shift+Enter/Esc), «Kimning puli?», majburiyatlar va nasiya. i18n kalitlari testi (uz/ru).
- Kechiktirildi / ataylab qilinmadi: daromadni tahrirlash/o'chirish, oila a'zosini tanlash (D6 oila rejimi), oylik davr boshlanish kuni sozlamasi, haftalik vazifa va juma bobi (D5), tauri-driver E2E (D15).
