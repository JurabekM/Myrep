# M-Pay Pay Sandbox — bosqichlar hisoboti

## M0 — repo skeleti, CI, hujjat qoralamalari (2026-10-23)

**Nima qilindi**

* Cargo workspace (`m-pay/`): 8 ta crate + `tests/e2e`, `workspace.dependencies` da barcha
  tanlangan versiyalar (ADR-0001), `[workspace.lints]` da `unsafe_code = "forbid"`.
* `rust-toolchain.toml` (1.97.1), `rustfmt.toml`, `clippy.toml`, `deny.toml`, `.gitignore`, `.env.example`.
* CI: `.github/workflows/mpay-ci.yml` — fmt, clippy `-D warnings`, test (Ubuntu + Windows),
  SoftHSM2 integratsion testi (Ubuntu), `cargo deny`, `cargo audit`.
* Hujjatlar: `architecture.md`, `threat-model.md` (STRIDE), `specs/emv-profile.md`,
  `specs/pqlink.md`, `specs/api.md` qoralamalari; ADR-0001…0007 (tasdiqlangan qarorlar).

**Qanday tekshirildi**

* `cargo build --workspace`, `cargo test --workspace` — o'tdi.
* `cargo fmt --check`, `cargo clippy --workspace --all-targets -D warnings` — toza.
* `cargo deny check` — advisories/bans/licenses/sources ok; `cargo audit` — zaiflik yo'q.
* CI workflow hali GitHub'da ishga tushirilmagan (push qilinmagan).

**Ochiq savollar** — yo'q (M0 oldidan berilgan 8 savolga javob olingan).

**Keyingi bosqich (M1)**: `mpay-common` (TLV, ISO 8583, PAN/Luhn, maskalash, portlar) va
`mpay-crypto` (KeyStore memory + PKCS#11, KDF, ARQC/ARPC, envelope), KAT + proptest,
SoftHSM2 integratsion testi Docker'da.
