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

## M4 — mpay-issuer + mpay-terminal-sim (2026-10-23)

**Nima qilindi**

* `mpay-issuer`: ISO 8583 `0100` → `0110` (ikkilik packer orqali), qaror zanjiri: format va
  CDOL ↔ maydon 4/49 → detokenizatsiya → LUK holati → ARQC (constant-time) → token holati →
  atomar LUK/ATC qaydi → emitent mavjudligi → Shield → hisob/qoldiq (atomar debet);
  ARPC (`91` = ARPC ‖ ARC, `8A`) faqat ARQC to'g'ri bo'lganda (replay'da yo'q); javob kodlari
  `00`/`05`/`51`/`59`/`91`/`Q1` (ADR-0007) va ichki sabab kodlari; UZS test hisoblari (PAN barmoq izi
  bo'yicha, PAN saqlanmaydi); avtorizatsiya qaydnomasi.
* `mpay-terminal-sim`: `ApduTransport` trait + `Loopback`; `SoftCard` (SELECT PPSE/AID, GPO,
  LUK tanlash, CDCVM `6986`, ARPC tekshiruvi); terminal yadrosi (PPSE → AID → PDOL → GPO);
  `mpay-tsim` CLI (`provision` — YELLOW'da sandbox OTP avtomatik, `tap`, `replenish`, `status`;
  hamyon fayli, monoton STAN).
* `mpay-server`: acquirer shlyuzi `POST /v1/authorizations` (terminal roli), `GET /v1/sandbox/accounts`;
  `init` demo test hisoblarini yozadi va `--keystore pkcs11` ni qo'llaydi.
* Skriptlar: `scripts/smoke-e2e.sh` (haqiqiy binarlar), `scripts/softhsm-test.sh e2e`.
  CI: SoftHSM to'liq oqim va smoke job'lari qo'shildi.
* Hujjatlar: `api.md` (yakuniy), `emv-profile.md` v1 (CDCVM §8.1), README'lar.

**Qanday tekshirildi**

* `cargo test --workspace` — 119 test o'tdi.
* **Telefonsiz e2e** (`tests/e2e/tests/m4_tap_to_pay.rs`, haqiqiy TCP/HTTP): provisioning → loopback
  tap → `0110`:
  * `00` — qoldiq aniq summaga kamaydi, ARPC karta tomonida tasdiqlandi (soxta ARPC rad);
  * `59` (RISKY merchant), REVIEW → `00 APPROVED_AFTER_REVIEW`;
  * `Q1` — buzilgan ARQC, o'zgartirilgan summa, ATC replay, LUK limiti tugagan, LUK muddati o'tgan
    (karta lokal limitlari o'chirilgan holda — server himoyasi alohida sinaldi);
  * `05` — to'xtatilgan token (resume'dan keyin yana `00`), noma'lum token;
  * `51` — qoldiq o'zgarmaydi; `91` — offline emitent BIN;
  * CDCVM: limitdan yuqori summa biometriyasiz `6986`, bir martalik;
  * terminal roli, noto'g'ri ICC; loglarda PAN/DPAN/LUK/ARQC yo'q.
* Emitent ISO testlari: maydon 4/49 va Track 2 nomuvofiqligi, ICC yo'qligi, noma'lum sxema,
  noto'g'ri MTI, tasodifiy baytlar (proptest).
* **Haqiqiy binarlar smoke** (`scripts/smoke-e2e.sh`, TLS): `init` → `serve` → `mpay-tsim`:
  GREEN/YELLOW/RED, `00`/`59`/`51`/`91`, `6986` → `--cdcvm` bilan `00`, LUK to'ldirish, `audit-verify`
  (23 yozuv), server logida ochiq PAN/DPAN yo'q — **SMOKE OK**.
* **SoftHSM2 (Docker)**: crypto 4/4 (3 marta ketma-ket barqaror) va to'liq oqim
  `pkcs11_provisioning_and_tap` — IMK, KEK, PAN-IDX, Ed25519 HSM'da; tap `00`, ARPC to'g'ri.
* clippy `-D warnings` (shu jumladan `mpay-server --features pkcs11`), fmt, `cargo deny`, `cargo audit` — toza.

**Topilgan va tuzatilgan muammolar**

* Smoke: bir soniya ichidagi taplarda STAN/RRN takrorlanardi (vaqtdan olingan) → hamyonda monoton STAN.
* SoftHSM2: parallel sessiyalardan bir vaqtda `C_GenerateKey` ba'zan `CKR_GENERAL_ERROR` → PKCS#11
  testlari ketma-ket (server bitta sessiyani `Mutex` ostida ishlatadi — bu holat unda yuzaga kelmaydi).
* `init` faqat `memory` KeyStore'ni qo'llardi → `--keystore pkcs11` (ML-DSA urug'i HSM KEK bilan o'raladi).

**Ochiq savollar**

* `TODO(spec):` issuer tomonidagi CVM siyosati (CDCVM bo'lmagan yuqori summalar) — M6.
* `TODO(spec):` takroriy STAN/RRN ni acquirer darajasida rad etish (hozir faqat ATC replay himoyasi).
* `TODO(spec):` REVIEW uchun standart siyosat (hozir `approve`, konfiguratsiyada `decline`).

## M0–M4 yakuni

Telefonsiz to'liq demo ishlaydi: qurilma PQ Link (X25519 + ML-KEM-768, Ed25519 + ML-DSA-65,
Android Key Attestation simulyatsiyasi) orqali tokenlashtiradi, soft-karta EMV-ga o'xshash APDU
oqimida ARQC hisoblaydi, emitent emulyatori ISO 8583 orqali tekshirib `0110` va ARPC qaytaradi;
barcha javob kodlari e2e va haqiqiy binarlar bilan sinalgan, PAN DB'da faqat shifrlangan va loglarda yo'q.

**Keyingi bosqich (M5)**: `mpay-shield` v0 (TOML qoidalar, tezlik va graf belgilari, `tract` ONNX skor,
p99 < 50 ms benchmark) va `shield-ml` (sintetik fraud stsenariylari, LightGBM → ONNX). Tasdig'ingizni kutaman.

## M5 — mpay-shield v0 + shield-ml (2026-10-24)

**Nima qilindi**

* `mpay-shield`: feature store (karta/qurilma/merchant/global P2P sirpanuvchi oynalari, summa z-skori,
  soat noyobligi), qurilma–karta grafi (union-find komponentlar, darajalar, yangi qirralar);
  27 tranzaksiya va 9 ID&V belgisi; deklarativ TOML qoidalar (8 + 8, belgi nomlari yuklashda tekshiriladi);
  `MlScorer` + `TractScorer` (sof Rust ONNX, model binarga joylangan); `Shield` dvigateli
  (`RiskScorer` va `IdvDecider` port'lari, skor 0–1000, APPROVE/REVIEW/DECLINE, GREEN/YELLOW/RED,
  sabab kodlari); `shield-replay` (featurize / evaluate / bench / parity).
* `shield-ml/` (uv, Python 3.13): `generate.py` — 5 fraud stsenariysi (ATO, card testing, mule tarmog'i,
  qurilma fermasi, P2P to'lqini) va 4 qiyin legit holat; `train.py` — LightGBM → ONNX, onnxruntime
  tekshiruvi, parity vektorlari. **Train/serve parity**: belgilarni faqat Rust hisoblaydi.
* Server: `[shield] engine = "engine" | "stub"`, ixtiyoriy qoidalar/model fayllari; `init` standarti — `engine`.
  ID&V provisioningga, risk skori emitentga port'lar orqali ulangan.
* Hujjatlar: `docs/shield-report.md`, `shield-ml/README.md`, `test-data.md` §3, ADR-0005 yangilandi.

**Qanday tekshirildi**

* `cargo test --workspace` — 134 test o'tdi (`tests/e2e/tests/m5_shield.rs`: real HTTP orqali qurilma
  fermasi GREEN×3 → YELLOW → RED, ikkinchi qurilma → YELLOW → OTP, tezkor taplar → `59`).
* Sintetik test to'plami (mustaqil seed): tranzaksiya fraud'i 97,2–100 % REVIEW+, legit 0,0 %
  (qiyin legit 0–4,1 %); ID&V: ATO 100 %, ferma 93 %, mule 71 % YELLOW+; legit RED 0 % — `docs/shield-report.md`.
* Model: tract ↔ onnxruntime farqi 1,5·10⁻⁷ (500 qator, crate testida ham); ONNX ↔ LightGBM 8,7·10⁻⁶.
* **Benchmark** (release, 45 390 hodisa bilan qizdirilgan, 41 694 tranzaksiya): p50 1,04 ms,
  p95 1,66 ms, **p99 1,94 ms**, max 8,58 ms — talab < 50 ms.
* Haqiqiy binarlar smoke (Shield dvigateli bilan): `00`, CDCVM, `59` (skor 957), `51`, YELLOW/OTP,
  RED (`IDV_DEVICE_FARM`), `91`, audit 37 yozuv — **SMOKE OK**.
* clippy `-D warnings`, fmt, `cargo deny`, `cargo audit` — toza.

**Topilgan va tuzatilgan muammolar**

* Yangi advisory RUSTSEC-2026-0387 (`crypto-bigint` 0.7.5, constant-time buzilishi; p256 orqali) →
  0.7.6 ga yangilandi.
* Bo'sh xotira yetmay rustc `tract-core` ni yig'ishda yiqildi (LLVM OOM) → bog'liqliklarda debuginfo
  o'chirildi, SoftHSM uchun ishga tushirilgan Docker to'xtatildi.
* ID&V'da ATO faqat 28 % aniqlanardi → "mavjud karta + yangi qurilma" qoidasi YELLOW (step-up OTP) ga
  ko'tarildi: ATO 100 %, legit'da kartani ikkinchi qurilmaga qo'shish ham OTP so'raydi (kutilgan xatti-harakat).

**Ochiq savollar**

* `TODO(spec):` real ma'lumotlar bilan qayta o'qitish va chegaralarni kalibrlash; sintetik natijalar
  optimistik (`shield-report.md` §3).
* `TODO(spec):` taqsimlangan feature store/graf (ko'p instansiya), MCC va terminal geo-koordinatalari.

**Keyingi bosqich (M6)**: Android `wallet-sdk`, `wallet-demo`, `terminal-app`.

## M6 — Android: wallet-sdk, wallet-demo, terminal-app (2026-10-24)

**Nima qilindi**

* `android/` Gradle loyihasi (AGP 8.13, Kotlin 2.2, Compose, minSdk 26) — ADR-0008.
* `mpay-core` (Kotlin/JVM): TLV, EMV profili, `MpayScheme` (KDF, ARQC/ARPC), `CardApplet`
  (HCE applet: PPSE/AID/GPO, LUK tanlash, CDCVM `6986`, ARPC), `TerminalKernel`, PQ Link v1
  client (BouncyCastle 1.86: ML-KEM-768, ML-DSA-65, X25519, Ed25519), `MpayClient`.
* `wallet-sdk`: `MpayWallet` fasadi (TOFU pinlash, provisioning, OTP, LUK to'ldirish),
  `MpayHceService` (payment kategoriyasi, PPSE + AID), `AndroidDeviceKey` (Keystore/StrongBox
  + attestatsiya challenge), `WalletStore` (Keystore AES-GCM), `CdcvmState` + `BiometricGate`
  (60 s oyna, ekran yoniq, bir martalik), `IntegrityProvider` stub.
* `wallet-demo` ("M-Pay Hamyon") va `terminal-app` ("M-Pay Terminal": NFC reader mode →
  `IsoDep` → `TerminalKernel.tap` → `/v1/authorizations`, STAN hisoblagichi) — qorong'i Compose UI.
* Rust: attestatsiya zanjirida P-384 va RSA oraliq/ildiz sertifikatlari (Google "Key Attestation CA1"
  va RSA-4096 ildizlari, `config/google-attestation-roots.pem`); TLV umumiy test vektorlari
  (`testvectors/tlv-vectors.json`) Rust va Kotlin'da.
* Hujjatlar: `android/README.md`, `docs/android-testing.md`, ADR-0008; ADR-0005 RAM ma'lumoti tuzatildi.

**Qanday tekshirildi**

* `./gradlew assembleDebug` — uchala ilova/kutubxona yig'iladi; `:mpay-core:test` — 5 test
  (TLV vektorlari, EMV KAT Rust/Python bilan bir xil, applet ARQC va CDCVM).
* `scripts/android-interop.sh` — Kotlin client ↔ haqiqiy Rust `mpay-server`: PQ Link handshake,
  GREEN provisioning, Kotlin ARQC → Rust emitent `00`, ARPC kartada tasdiqlandi, CDCVM `6986` → `00`,
  replay `Q1`, LUK to'ldirish, YELLOW/OTP, TEE darajali qurilma `PQLINK_ATTESTATION` — **INTEROP OK**.
* Emulyator (Medium Phone API 36), `wallet-demo` ↔ xostdagi `mpay-server`:
  standart siyosatda emulyator attestatsiyasi rad etildi (ishonchsiz ildiz, so'ng `SOFTWARE` < talab);
  emulyator test ildizi bilan: ulanish, provisioning → YELLOW → sandbox OTP → token faol
  (`990077******2765`, 5 LUK), LUK to'ldirish (10), barmoq izi → "To'lovga tayyor: 55 s".
  Server logida 7 marshrut 200, ochiq PAN 0. `terminal-app`: NFC'siz qurilmada to'g'ri xato,
  terminal kaliti maskalangan.
* `cargo test --workspace` — 138 test; clippy `-D warnings`, fmt — toza.

**Topilgan va tuzatilgan muammolar**

* targetSdk 36 da edge-to-edge majburiy — sarlavha status bar ostida qolardi → `safeDrawing` insets.
* Karta komponentining qat'iy balandligi CDCVM qatorini kesardi → `heightIn(min)`.
* Provisioningdan keyin FPAN maydonda qolardi → server javobidan so'ng tozalanadi.
* BouncyCastle 1.86 da PQ klasslari paketi o'zgargan; emulyator attestatsiya ildizi
  "Droid Unregistered Device CA" (Google Test LLC), xavfsizlik darajasi `SOFTWARE`.

**Ochiq / bajarilmagan**

* **Qabul mezoni — ikki haqiqiy telefon o'rtasida NFC tap — hali bajarilmagan**: ishlab chiqish
  muhitida NFC'li telefonlar yo'q, emulyator HCE'ni qo'llamaydi. Tap mantiqi JVM'da loopback orqali
  Rust emitentiga qarshi sinalgan; `IsoDep`/`HostApduService` qatlami sinalmagan.
  Qo'lda sinov tartibi: `docs/android-testing.md` §3.
* `terminal-app` `/v1/authorizations` ni sandbox'da ochiq HTTP orqali yuboradi (terminal kaliti
  tarmoqda ko'rinadi). `TODO(spec):` TLS + pinlash, terminal kalitini Keystore'da saqlash.
* `TODO(spec):` Play Integrity, bank ilovasida build vaqtida pinlangan server barmoq izi (TOFU o'rniga).

## M7 — fuzz kampaniyasi, yuk sinovi, bank namoyishi (2026-10-24)

**Nima qilindi**

* Fuzz: 3 yangi maqsad — `apdu_card` (soft-karta applet'iga ixtiyoriy APDU ketma-ketligi),
  `issuer_parse` (emitent `0100` tahlilchisi; buning uchun `mpay_issuer::validate_request`),
  `pqlink_session` (o'rnatilgan sessiya yozuviga bit-flip/kesish). EMV lug'ati `fuzz/emv.dict`,
  boshlang'ich kirishlar `fuzz/seeds/`, `scripts/fuzz-campaign.sh` (jadval bilan), CI `fuzz` job'i.
* Yuk: `mpay-load` (`tests/e2e/src/bin/mpay_load.rs`) va `scripts/load-test.sh` — release server
  alohida jarayonda, 200 karta PQ Link provisioning, haqiqiy ARQC bilan avtorizatsiyalar, keep-alive.
* Namoyish: `docs/demo-script.md` (10 daqiqa, vaqt jadvali, savollar) va `scripts/demo.sh`
  (interaktiv / `DEMO_AUTO=1` tekshiruvli); CI smoke job'iga qo'shildi.
* SQLite: yozuvchi tranzaksiyalar `BEGIN IMMEDIATE`, hovuz standarti 1 ulanish,
  `[database] synchronous` / `max_connections` sozlamalari — ADR-0009.
* `mpay-tsim`: `6986` endi "karta: … telefonda tasdiqlang" (avval noto'g'ri "konfiguratsiya" turkumi).
* Skriptlar `python`/`python3` ni avtomatik tanlaydi (Ubuntu CI).
* Hujjatlar: `docs/fuzz-report.md`, `docs/load-report.md`, `docs/demo-script.md`, ADR-0009,
  `tests/e2e/README.md`; vault/issuer README'lari.

**Qanday tekshirildi**

* Fuzz (ASan, Windows): 7 maqsad × 300 s — jami ≈ 24,1 mln yugurish, crash yo'q; `pqlink_session` qo'shimcha 1 800 s — 81 291 yugurish, crash yo'q.
  `apdu_card` seed'lari GPO `9000`, CDCVM `6986`, LUK limiti `6985` ga yetishi kuzatildi.
* Yuk (`docs/load-report.md`): 32 parallel — 238 avtorizatsiya/s, p99 155 ms; 8 parallel — p99 46 ms;
  provisioning 630+ karta/s; xato 0; server logida ochiq PAN yo'q.
* `DEMO_AUTO=1 bash scripts/demo.sh` — **DEMO OK** (TLS, Shield dvigateli: `00`+ARPC, `6986`→CDCVM `00`,
  `59`, YELLOW/OTP, RED ferma, `51`, `91`, DB'da ochiq PAN yo'q, audit trigger rad etadi,
  buzilgan yozuv `seq 2` aniqlanadi). `smoke-e2e.sh` — SMOKE OK; `android-interop.sh` — INTEROP OK.
* `cargo test --workspace` — 138 test; clippy `-D warnings`, fmt, `cargo deny`, `cargo audit` — toza.

**Topilgan va tuzatilgan muammolar**

* **Yuk ostida `91 ISSUER_OFFLINE` (7 %)** — aslida SQLite `SQLITE_BUSY` (deferred tranzaksiya
  o'qishdan yozishga o'tganda `busy_timeout` ishlamaydi) → `BEGIN IMMEDIATE`.
* Shundan keyin p99 ~1 s: 8 ulanish yozish qulfini SQLite busy-handler'ida uxlab kutardi → hovuz
  1 ulanish: p99 1 046 → 155 ms, 83 → 238 so'rov/s.
* Python bilan skript tahririda `\n` haqiqiy qatorga aylandi (`load-test.sh` sed) — Edit bilan tuzatildi.

**Ochiq / bajarilmagan**

* **M6 qabul mezoni — ikki telefon orasida haqiqiy NFC tap — sinalmagan** (qurilmalar yo'q);
  namoyishning telefon qismi ixtiyoriy va oldindan repetitsiya talab qiladi.
* CI'dagi yangi `fuzz` job'i va demo qadami hali GitHub'da yugurtirilmagan (branch push qilinmagan).
* `TODO(spec):` production DB va TPS/SLA talablari; HSM kechikishi bilan yuk sinovi;
  HTTP API fuzzing; Kotlin tomoni uchun Jazzer.

## Phase 0 (M0–M7) yakuni

Pay Sandbox telefonsiz to'liq ishlaydi va 10 daqiqalik namoyish skripti avtomatik tekshiriladi:
PQ Link (gibrid post-kvant) orqali tokenizatsiya, Vault (envelope shifrlash, audit zanjiri),
EMV-ga o'xshash tap-to-pay (LUK, ARQC/ARPC, CDCVM), Shield (qoidalar + ONNX, p99 < 2 ms),
emitent emulyatori (ISO 8583), Android SDK va ikki ilova (emulyatorda provisioning/OTP/LUK/biometriya
sinalgan). Haqiqiy NFC tap — yagona sinalmagan qabul mezoni.

## 1-faza — xavfsizlikni kuchaytirish (boshlandi 2026-10-24)

Reja: `docs/roadmap.md`. Branch: `claude/mpay-faza1`.

### P1.1 + P1.2 (2026-10-24)

**Nima qilindi**

* **P1.1 rate-limit** (`crates/mpay-server/src/ratelimit.rs`, `[rate_limit]`): IP bo'yicha handshake
  (300/daqiqa, burst 60 — CGNAT uchun yumshoq), bir vaqtdagi handshake hisoblashlari semafori
  (CPU × 2, oshsa 503 `BUSY`), API kaliti bo'yicha (500/s), qurilma bo'yicha muhrlangan so'rovlar
  (60/daqiqa). 429/503 javoblarda `Retry-After`. Qurilma chegarasi javobi muhrlanadi — sessiya ketma-ketligi
  buzilmaydi. Mijoz IP'si TLS va oddiy HTTP yo'lida `ConnectInfo` orqali.
* **P1.2 takroriy STAN** (`dedup.rs`, migratsiya `3001`, ADR-0010): bir xil so'rov — avvalgi javob
  (timeout'dan keyingi qayta yuborish endi noto'g'ri `Q1` bermaydi), shu STAN boshqa mazmun bilan — `94`,
  ishlanayotgan — `409 REQUEST_IN_PROGRESS`. `mpay-tsim` STAN'i terminal fayliga ko'chirildi.
* Hujjatlar: ADR-0010, ADR-0007 (`94`), `specs/api.md` §4–6, tahdid modeli D2 va E4, yuk hisoboti §6.

**Qanday tekshirildi**

* `cargo test --workspace` — 145 test (yangi: `ratelimit` 3 unit, `p1_rate_limit.rs` 3, `p1_duplicate_stan.rs` 1:
  qayta yuborishda bir xil javob va bitta yechim, `94` balansni o'zgartirmaydi, o'sha tap yangi STAN bilan `00`).
* Smoke, demo (`DEMO OK`), Kotlin↔Rust interop — o'tdi; clippy, fmt — toza.
* Yuk: 171–175 so'rov/s, p99 ~200 ms (32 parallel), xato 0 — `docs/load-report.md` §6.

**Ochiq**

* `TODO(spec):` teskari proksi ortida `X-Forwarded-For` uchun ishonchli proksi ro'yxati.
* O'tkazuvchanlik −27 % — 2-fazada (bitta tranzaksiya / PostgreSQL).

### P1.3 — ichki API uchun mTLS (2026-10-24)

**Nima qilindi**

* Server: `[http] client_ca` (mijoz sertifikati so'raladi, majburiy emas — hamyonlar PQ Link bilan),
  sertifikat CN'i `PeerCert` sifatida so'rovga; `[auth] require_mtls` — operator/terminal endpointlarida
  `CN == API kaliti id`, aks holda `403 MTLS_REQUIRED`; konfiguratsiya tekshiruvi.
* `init --tls`: mijoz CA'si (`mtls-client-ca.pem`, kaliti saqlanmaydi), `operator-1` va `terminal-1`
  sertifikatlari (EKU clientAuth), `require_mtls = true`.
* `ServerClient::with_identity`; `mpay-tsim` sandbox'dagi `<id>.crt.pem` ni avtomatik ko'rsatadi
  (operator OTP so'rovi — `operator-1`, avtorizatsiya — `terminal-1`).
* Hujjatlar: ADR-0011, tahdid modeli S3, `api.md` (`MTLS_REQUIRED`), server README.

**Qanday tekshirildi**

* `tests/e2e/tests/p1_mtls.rs` (3): sertifikatsiz → 403; boshqa CN → 403; to'g'ri juftlik → 200;
  Bearer'siz → 401; hamyon sertifikatsiz TLS ichida provisioning; terminal sertifikati bilan `00`;
  begona CA sertifikati TLS handshake'da rad.
* `cargo test --workspace` — 148 test; smoke va demo (`--tls`, endi mTLS bilan) — OK; interop — OK.

**Ochiq**

* `TODO(spec):` sertifikat bekor qilish (CRL/OCSP) — bank PKI'si (2-faza).
* Android `terminal-app` hali mTLS'siz — P1.4.

### P1.4 — terminal-app: TLS + mTLS, kalitlar Keystore'da (2026-10-24)

**Nima qilindi**

* Server: `mpay-server terminal-bundle --url https://…` — paket (`mpay-terminal-bundle/1`): server TLS
  sertifikati va SHA-256 pini, mTLS mijoz sertifikati/kaliti, terminal API kaliti; `GET /v1/terminal/ping`
  (kalit + mTLS + chegaralar diagnostikasi).
* `mpay-core`: `TlsConfig` (server sertifikati pinlanadi — tizim CA'lariga ishonilmaydi, xost nomi
  tekshiruvi ham pin bilan), `Pem` yordamchilari, `TerminalBundle.parse` (pin sertifikatga mosligini
  tekshiradi), `MpayClient(tls = …)`, `terminalPing`.
* `terminal-app`: `TerminalVault` — mTLS kaliti Android Keystore'ga import (imzo Keystore'da,
  `X509ExtendedKeyManager`), terminal kaliti/URL/pin Keystore AES-256-GCM bilan shifrlangan; paket
  ilova papkasidan (adb push) yoki fayl tanlash oynasidan import qilinadi va **o'chiriladi**;
  "Ulanishni tekshirish", "Paketni o'chirish". Qo'lda rejim (HTTP) kalitni endi saqlamaydi; 0-fazadagi
  ochiq saqlangan kalit ishga tushishda o'chiriladi.

**Qanday tekshirildi**

* JVM interop (`InteropTest.pinnedTlsAndMtlsAgainstRustServer`, haqiqiy Rust server `--tls`):
  noto'g'ri pin → `SSLHandshakeException`; sertifikatsiz → `MTLS_REQUIRED`; mTLS bilan ping →
  `terminal-1`, mTLS; TLS ustida hamyon provisioning + terminal avtorizatsiyasi `00`, ARPC tasdiqlandi;
  takroriy yuborish → aynan o'sha javob. **INTEROP OK**.
* Emulyator (API 36) ↔ `mpay-server --tls` (`https://10.0.2.2:8443`): paket import qilindi va fayl
  o'chirildi; "Ulanish ishlaydi — TLS: server pinlangan, mTLS sertifikati qabul qilindi" (server logida
  `/v1/terminal/ping` 200); ilova qayta ishga tushgach ham ishlaydi (Keystore'dan ochildi); paketsiz
  qo'lda `https` → `SSLHandshakeException` (serverga yetmaydi).
* `cargo test --workspace` — 148; smoke, demo — OK; clippy, fmt — toza.

**Ochiq**

* Hamyon (`wallet-demo`) hali TLS pinlashsiz — `--tls` server bilan ulanmaydi; P1.5 da (build vaqtida
  pinlangan PQ Link barmoq izi + TLS pin).
* NFC tap orqali to'liq to'lov TLS ustida faqat JVM interop'da sinalgan (emulyatorda NFC yo'q) — P1.8.
