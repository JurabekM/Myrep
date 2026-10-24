# M-Pay — Pay Sandbox (0-faza)

M-Pay — banklar, to'lov tashkilotlari va milliy to'lov tizimlari uchun B2B infratuzilma:
tokenizatsiya (**Vault**), real-time fraud/AML va ID&V (**Shield**), post-kvant gibrid kalit
kanali (**PQ Link**) va bank ilovalari uchun HCE tap-to-pay (**Wallet SDK**).
M-Pay pulni o'tkazmaydi va saqlamaydi; mijoz serverida (on-prem) ishlaydi.

Pay Sandbox — haqiqiy pulsiz, to'liq ishlaydigan demo.

## Qat'iy chegaralar

1. Faqat soxta test PAN'lar: BIN `990000`–`990099` (FPAN `990000`–`990049`, DPAN `990050`–`990099`).
2. "M-Pay Test Scheme" — o'zimizning profil (`docs/specs/emv-profile.md`), real scheme emas.
3. Sirlar repoga tushmaydi; kalitlar faqat `KeyStore` orqali; `.env.example` — faqat namuna.
4. PAN, kalit, LUK, kriptogramma logga yozilmaydi — faqat maskalangan PAN va token ID.
5. Dashboard yo'q: HTTP API va CLI; server — bitta binar `mpay-server`.
6. Barcha crate'larda `#![forbid(unsafe_code)]`.

## Tuzilma

| Yo'l | Tavsif |
|---|---|
| `crates/mpay-common` | TLV, ISO 8583, PAN/Luhn, maskalash, konfiguratsiya, port trait'lari |
| `crates/mpay-crypto` | KeyStore (memory + PKCS#11), kalit ierarxiyasi, ARQC/ARPC, envelope |
| `crates/mpay-pqlink` | PQ Link gibrid handshake (server + client) |
| `crates/mpay-vault` | Token Vault: provisioning, lifecycle, LUK, detokenizatsiya, audit |
| `crates/mpay-shield` | risk engine: feature store, qurilma–karta grafi, TOML qoidalar, ONNX (tract) |
| `shield-ml/` | sintetik fraud ma'lumotlari, LightGBM → ONNX (Python, uv) |
| `crates/mpay-issuer` | emitent emulyatori (ISO 8583 subset, UZS test hisoblar) |
| `crates/mpay-terminal-sim` | dasturiy terminal + loopback soft-karta + soft-wallet, `mpay-tsim` CLI |
| `crates/mpay-server` | monolit binar, axum API |
| `tests/e2e` | to'liq stsenariylar |
| `android/` | `mpay-core` (Kotlin yadro), `wallet-sdk`, `wallet-demo`, `terminal-app` |
| `docs/` | arxitektura, tahdid modeli, spetsifikatsiyalar, ADR, PROGRESS |

## Tez boshlash

```bash
cargo test --workspace
```

Telefonsiz namoyish (sandbox, TLS):

```bash
cargo run -p mpay-server -- init --dir .mpay --tls
```

```bash
cargo run -p mpay-server -- serve --config .mpay/mpay.toml
```

Boshqa terminalda (`.mpay/mpay.toml` dagi `[[issuer.accounts]]` PAN'laridan biri bilan):

```bash
cargo run -p mpay-terminal-sim --bin mpay-tsim -- --server https://localhost:8080 provision --pan <FPAN> --expiry 3112
```

```bash
cargo run -p mpay-terminal-sim --bin mpay-tsim -- --server https://localhost:8080 tap --amount 12500.00
```

To'liq avtomatik smoke (haqiqiy binarlar): `bash scripts/smoke-e2e.sh`.
10 daqiqalik bank namoyishi: `bash scripts/demo.sh` (ssenariy — `docs/demo-script.md`;
`DEMO_AUTO=1` — avtomatik tekshiruv bilan).
Yuk sinovi: `bash scripts/load-test.sh` (`docs/load-report.md`); fuzz kampaniyasi:
`bash scripts/fuzz-campaign.sh [soniya]` (`docs/fuzz-report.md`).
SoftHSM2 testlari (Docker): `bash scripts/softhsm-test.sh` va `bash scripts/softhsm-test.sh e2e`.

Android ilovalari va telefonda sinash: `android/README.md`, `docs/android-testing.md`.

Batafsil: `docs/PROGRESS.md`, `docs/specs/`, har crate'ning `README.md` fayli.
