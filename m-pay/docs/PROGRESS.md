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

## M2 — mpay-pqlink (2026-10-23)

**Nima qilindi**

* `mpay-pqlink`: PQ Link v1 server va client holat mashinalari — X25519 + ML-KEM-768 gibrid KEM,
  `HKDF-SHA256(ss_x25519 ‖ ss_mlkem, salt = th1)`, gibrid server imzosi Ed25519 (HSM) + ML-DSA-65
  (KEK bilan o'ralgan urug'), `s_finished`/`c_finished`, Android Key Attestation zanjiri tekshiruvi
  (KeyDescription, xavfsizlik darajasi siyosati), ChaCha20-Poly1305 yozuvlar (yo'nalish bo'yicha kalit,
  monoton `seq`, replay rad, AEAD xatosida sessiya yopiladi), sessiya TTL va limit.
* `sandbox-attestation` feature: sandbox attestatsiya CA (`rcgen`) va `SoftDeviceKey` (soft-wallet uchun).
* NIST ACVP: `scripts/trim_acvp.py` usnistgov/ACVP-Server'dan ML-KEM-768 va ML-DSA-65 qismini
  `testvectors/acvp/` ga ajratadi (1,5 MB).
* `docs/specs/pqlink.md` — **v1 yakunlangan**: maydonlar va hajmlar, tekshirish tartibi, cheklovlar,
  xatolar, tekshiruv qamrovi.
* Fuzz maqsadi `pqlink_decode`.

**Qanday tekshirildi**

* `cargo test --workspace` — 93 test o'tdi.
* ACVP: 110 NIST vektori — ML-KEM-768 keyGen 10, encaps 10, decaps 10, ek/dk tekshiruvi 20;
  ML-DSA-65 keyGen 10, sigGen 20 (tashqi/ichki × deterministik/hedged), sigVer 30 (to'g'ri va noto'g'ri).
  FIPS 204 Algorithm 2 dagi `M' = 0 ‖ |ctx| ‖ ctx ‖ M` qurilishimiz hedged vektorlar bilan tasdiqlandi.
* Handshake testlari (13): to'liq oqim; replay va tartibsiz yozuv (sessiya saqlanadi); buzilgan yozuv
  (sessiya yopiladi); buzilgan Ed25519 / ML-DSA / `s_finished`; pinlanmagan server; faqat Ed25519 to'g'ri
  bo'lgan aralash identifikator; begona CA; TEE < StrongBox; ko'chirilgan attestatsiya zanjiri;
  ClientFinished buzilishi va takrori; sessiya/handshake muddati; sessiya limiti; tasodifiy kirishlar.
* Fuzz `pqlink_decode` 60 s — 746 544 yugurish, crash yo'q.
* clippy `-D warnings` (barcha feature'lar bilan), fmt, `cargo deny` (faqat `syn`, `getrandom`
  dublikat ogohlantirishlari), `cargo audit` — toza.

**Ochiq savollar** (M2 ni bloklamaydi, `pqlink.md` §9 da):

* attestatsiya challenge'ini enrollment bilan bog'lash, Google ildizlari (RSA/P-384), server kalit
  rotatsiyasi, Kotlin uchun deterministik handshake vektori — M6.

**Keyingi bosqich (M3)**: `mpay-vault` (SQLite, envelope-shifrlangan PAN/DPAN, provisioning
GREEN/YELLOW/RED, LUK berish va to'ldirish, lifecycle, xesh-zanjirli audit) va `mpay-server` API
(axum, PQ Link endpointlari, operator/terminal autentifikatsiyasi), Shield stub.

## M3 — mpay-vault + mpay-server API (2026-10-23)

**Nima qilindi**

* `mpay-vault`: SQLite sxemasi (`1001_vault_init.sql`); PAN/DPAN faqat envelope-shifrlangan
  (KEK → DEK, kontekst AAD), HMAC barmoq izi bo'yicha qidiruv; provisioning GREEN/YELLOW/RED
  (`IdvDecider` porti), OTP-simulyatsiya (saqlanmaydi, HMAC'dan hosil qilinadi; 5 daqiqa, 3 urinish),
  LUK partiyalari va to'ldirish, lifecycle (`PENDING_IDV/ACTIVE/SUSPENDED/DELETED`), ichki
  `VaultDetokenizer` (lookup + atomar consume: LUK hisoblagichi, ATC monotonligi), append-only
  xesh-zanjirli audit (trigger'lar + `verify`).
* `mpay-shield::stub` — deterministik ID&V va risk (`docs/test-data.md`).
* `mpay-common::api` — yagona JSON DTO'lar (maxfiy maydonlar `Zeroizing`, `Debug` yashirilgan).
* `mpay-server`: axum router (PQ Link handshake, sealed qurilma endpointlari, operator API,
  audit, sandbox OTP), Bearer rollar (SHA-256 xesh, constant-time), TLS (rustls/ring), so'rov logi
  (tanasiz), `init` (dev-urug', ML-DSA blob, sandbox CA, TLS, API kalitlari, `mpay.toml`), `serve`,
  `audit-verify`, `identity`.
* `mpay-terminal-sim`: HTTP client (rustls) va soft-wallet (PQ Link sessiyasi, provisioning, OTP, LUK).
* Hujjatlar: `specs/api.md` (M3 qismi yakunlangan), `test-data.md`, crate README'lari, architecture grafi.

**Qanday tekshirildi**

* `cargo test --workspace` — 109 test o'tdi.
* Vault integratsion testlari (10): har bir provisioning shoxobchasi, OTP lockout/muddat, holat
  o'tishlari, detokenizatsiya qoidalari, **DB fayli (asosiy + WAL) baytlarida ochiq FPAN/DPAN
  (ASCII va BCD) va LUK yo'q**, audit buzilishi aniqlanadi, dev-urug' bilan qayta ochish.
* E2E (`tests/e2e/tests/m3_provisioning.rs`, server jarayon ichida, **haqiqiy TCP/HTTP**):
  provisioning → LUK → to'ldirish → suspend/resume/delete; YELLOW OTP (rol tekshiruvi bilan), RED;
  HTTP darajasida replay (`PQLINK_REPLAY`); begona CA va TEE qurilma rad; boshqa qurilma LUK ololmaydi;
  operator API kalitlari; server qayta ishga tushganda tokenlar o'qiladi; **debug darajasidagi
  loglarda FPAN, DPAN va LUK yo'q**.
* Haqiqiy binar smoke: `mpay-server init --tls` → `serve` → curl TLS orqali `/healthz`,
  `/v1/pqlink/identity`, operator `/v1/audit/verify` (kalitsiz 401, kalit bilan 200); TLS portiga oddiy
  HTTP ulanmaydi.
* clippy `-D warnings`, fmt, `cargo deny` (ok; `sha2`/`digest` 0.10 dublikati `sqlx-core` migratsiya
  checksum'idan — bizning kripto yo'lida ishlatilmaydi), `cargo audit` — zaiflik yo'q.

**Ochiq savollar**

* `TODO(spec):` token muddati: hozir `min(karta muddati, hozir + 36 oy)`; real sxema qoidasi kerak.
* `TODO(spec):` bir karta bir nechta qurilmada — hozir cheklanmagan (Shield M5 da `existing_tokens_for_pan`
  bo'yicha qaror qiladi).
* `TODO(spec):` OTP kanali (SMS/push/bank ilovasi) — sandbox'da faqat operator endpointi.

**Keyingi bosqich (M4)**: `mpay-issuer` (ISO 8583 `0100`/`0110`, ARQC/ARPC, UZS test hisoblar,
javob kodlari), `mpay-terminal-sim` (APDU transport trait, loopback soft-karta, terminal yadrosi,
`mpay-tsim` CLI), `/v1/authorizations`, telefonsiz e2e: provisioning → tap → `0110` (tasdiq va har
bir rad kodi).
