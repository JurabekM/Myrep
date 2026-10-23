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

## M1 — mpay-common + mpay-crypto (2026-10-23)

**Nima qilindi**

* `mpay-common`: `Pan` (faqat test BIN, Luhn, maskalash, zeroize), BER-TLV parser/encoder va DOL,
  ISO 8583 subset packer (14 maydon, qat'iy unpack, kanonik bitmap), M-Pay Test Scheme profili
  (PDOL/CDOL/IAD/Track 2/BCD), port trait'lari (`IdvDecider`, `RiskScorer`, `Detokenizer`),
  `TokenId`/`DeviceId`/`PanFingerprint`, `Clock`, `LukPolicy`.
* `mpay-crypto`: `KeyStore` trait; `MemoryKeyStore` (tasodifiy / dev-urug'dan deterministik);
  `Pkcs11KeyStore` (`pkcs11` feature, SoftHSM2 bilan sinalgan, jarayon bo'yicha yagona
  `C_Initialize`); SP 800-108 KDF; `MPAY-AES128-CMAC-V1` (MK_tok → LUK → SK → ARQC/ARPC);
  envelope encryption (KEK → DEK → AES-256-GCM, kontekst AAD); PAN HMAC indeksi.
* KAT: `scripts/gen_emv_kat.py` — Rust'dan **mustaqil** Python implementatsiyasi spetsifikatsiyadan
  `testvectors/emv-kat.json` ni generatsiya qiladi (3 holat); jadval `emv-profile.md` §9 da.
* `cargo-fuzz` maqsadlari: `tlv_parse`, `iso8583_unpack`, `emv_parse` (`m-pay/fuzz`).
* `scripts/softhsm-test.sh` — SoftHSM2 testlari Docker'da (`rust:1.97.1-bookworm`, SoftHSM 2.6.1).

**Qanday tekshirildi**

* `cargo test --workspace` — 60 test o'tdi (proptest'lar bilan).
* EMV KAT: Rust va mustaqil Python implementatsiyasi barcha 3 holatda har oraliq qiymatda mos.
* Primitiv KAT'lar (RFC 4493, RFC 4231 #6–7, GCM TC13/14, RFC 8032 #1–2) Python `cryptography`
  49.0 bilan qayta tekshirildi va memory **hamda SoftHSM2** backend'ida o'tdi.
* SoftHSM2 (Docker): 4/4 test — muvofiqlik KAT, kalitlarning token'da saqlanishi, memory bilan bir xil
  LUK, HSM KEK bilan envelope, standart kalitlar (Ed25519 HSM ichida).
* Fuzz (Windows, nightly + ASan, har biri 40 s): tlv 345 316, iso8583 1 032 409, emv 1 285 326
  yugurish — crash yo'q.
* `cargo clippy --workspace --all-targets --features mpay-crypto/pkcs11 -D warnings`, `cargo fmt`,
  `cargo deny` (faqat `syn` 2/3 dublikati ogohlantirish), `cargo audit` — toza.

**Topilgan va tuzatilgan muammolar**

* Parallel testlarda SoftHSM SIGSEGV: har `open()` `C_Initialize` chaqirardi → jarayon bo'yicha
  umumiy kontekst + `CKR_USER_ALREADY_LOGGED_IN` ni normal holat deb qabul qilish.
* SoftHSM2 32 baytdan qisqa HMAC kalitini rad etadi → siyosat: HMAC kaliti 32–256 bayt; KAT
  RFC 4231 #6–7 ga o'tkazildi.
* Fuzz invarianti `pack(unpack(x)) == x` bo'sh ikkilamchi bitmap'da buzilishi mumkin edi →
  unpack endi kanonik bo'lmagan bitmap'ni rad etadi.

**Ochiq savollar** — yo'q.

**Keyingi bosqich (M2)**: `mpay-pqlink` — gibrid handshake (X25519 + ML-KEM-768, Ed25519 + ML-DSA-65),
attestatsiya zanjiri tekshiruvi, ChaCha20-Poly1305 yozuvlar, replay himoyasi, NIST ACVP
vektorlari (ML-KEM/ML-DSA), `pqlink.md` yakuniy versiyasi.
