# mpay-crypto

M-Pay kriptografiya qatlami: HSM abstraksiyasi, kalit ierarxiyasi, ARQC/ARPC, envelope encryption.

| Modul | Vazifasi |
|---|---|
| `keystore` | `KeyStore` trait — kalit materialini qaytarmaydi, faqat operatsiyalar: AES-CMAC, AES-256-GCM, HMAC-SHA256, Ed25519. Backend'lar: `MemoryKeyStore` (tasodifiy yoki dev-urug'dan deterministik), `Pkcs11KeyStore` (`pkcs11` feature, `cryptoki`). |
| `keystore::conformance` | Har backend uchun ochiq standart KAT'lar: RFC 4493, RFC 4231 #6–7, GCM TC13/14, RFC 8032. |
| `kdf` | NIST SP 800-108r1 counter KDF, PRF = AES-128-CMAC. |
| `scheme` | `CryptogramScheme` trait va `MPAY-AES128-CMAC-V1`: MK_tok → LUK → SK → ARQC/ARPC (ADR-0004). |
| `envelope` | KEK → DEK (AES-256-GCM o'rash), DEK → ma'lumot (AES-256-GCM, kontekst AAD bilan). |
| `index` | PAN HMAC indeksi (`PanFingerprint`). |
| `secret`, `rng` | `SecretKey16/32` (`Zeroizing`, `Debug` yashirilgan), constant-time `ct_eq`, OS CSPRNG. |

Standart kalit yorliqlari: `mpay.imk-ac.v1`, `mpay.kek.v1`, `mpay.pan-idx.v1`, `mpay.srv-ed25519.v1`.

## Testlar

```bash
cargo test -p mpay-crypto
```

* `tests/memory_kat.rs` — `MemoryKeyStore` muvofiqligi;
* `tests/emv_kat.rs` — `testvectors/emv-kat.json` (mustaqil Python implementatsiyasi
  `scripts/gen_emv_kat.py`) bilan barcha oraliq qiymatlar;
* `tests/pkcs11.rs` — SoftHSM2 integratsion testi (`#[ignore]`): KAT, saqlanish, sessiyalar pool'i,
  login tushib qolgandan keyin tiklanish (ADR-0017).

SoftHSM2 testi (Windows'da Docker orqali):

```bash
bash scripts/softhsm-test.sh
```

Linux'da to'g'ridan-to'g'ri: `MPAY_PKCS11_LIB`, `MPAY_PKCS11_TOKEN_LABEL`, `MPAY_PKCS11_PIN`
o'rnating va ishga tushiring:

```bash
cargo test -p mpay-crypto --features pkcs11 -- --include-ignored pkcs11
```
