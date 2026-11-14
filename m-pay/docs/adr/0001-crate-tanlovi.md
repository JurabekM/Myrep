# ADR-0001: Asosiy crate'lar va versiyalar

* Holat: qabul qilingan (2026-10-23)

## Kontekst

Kriptografiya, tarmoq va saqlash uchun barqaror, xavfsiz, iloji boricha sof Rust kutubxonalari kerak.
Versiyalar crates.io'dan 2026-10-23 da tekshirildi. RustCrypto yaqinda yangi avlodga o'tgan
(`digest 0.11`, `rand_core 0.10`, `signature 3`, `crypto-common 0.2`) — barcha kripto crate'lar
shu avloddan olinadi, aks holda bir crate'ning ikki versiyasi grafga tushadi.

## Qaror

| Crate | Versiya | Sabab |
|---|---|---|
| `ml-kem` | 0.3.3 | RustCrypto, FIPS 203 final, sof Rust, `zeroize`; NIST ACVP vektorlari |
| `ml-dsa` | 0.1.1 | RustCrypto, FIPS 204; birinchi pre-release bo'lmagan versiya. **Audit qilinmagan** — ACVP vektorlarini o'zimiz tekshiramiz |
| `cryptoki` | 0.12.1 | Parsec loyihasi, PKCS#11 ustidagi xavfsiz o'ram; bizning kodimizda `unsafe` yo'q |
| `x25519-dalek`, `ed25519-dalek` | 3.0.0 | dalek, yangi RustCrypto avlodi bilan mos |
| `aes`, `cmac`, `aes-gcm` | 0.9.3, 0.8.0, 0.11.1 | RustCrypto |
| `hkdf`, `hmac`, `sha2` | 0.13.0, 0.13.0, 0.11.1 | RustCrypto |
| `chacha20poly1305` | 0.11.0 | RustCrypto AEAD |
| `p256`, `x509-cert`, `der` | 0.14.0, 0.3.0, 0.8.2 | attestatsiya zanjirini tekshirish |
| `zeroize`, `subtle` | 1.9.1, 2.6.1 | sirlarni tozalash, constant-time |
| `getrandom` | 0.4.3 | OS CSPRNG |
| `tokio`, `axum` | 1.54, 0.8.9 | async runtime, HTTP |
| `rustls` (+`ring`) | 0.23.46 | TLS; `aws-lc-rs` cmake/NASM talab qiladi (Windows build muhitida yo'q) |
| `sqlx` | 0.9.0 | SQLite (sandbox), keyin PostgreSQL; makrosiz so'rovlar |
| `rcgen` | 0.14.10 | sandbox attestatsiya CA va TLS sertifikatlari |
| `proptest` | 1.12.0 | xususiyatga asoslangan testlar |
| `tracing` | 0.1.44 | strukturali log |

Toolchain: Rust 1.97.1 (`rust-toolchain.toml`), edition 2021.

## Oqibatlar

* `ml-dsa` 0.x — API o'zgarishi mumkin; `mpay-crypto` ichida yupqa o'ram orqali ishlatiladi.
* `ort` 2.0 hali RC — ADR-0005.
* FIPS-validatsiyalangan modul kerak bo'lsa (bank talabi), `aws-lc-rs` ML-KEM/ML-DSA ga o'tish
  `KeyStore`/PQ o'ramlari orqali mahalliy o'zgarish bo'ladi.

## Ko'rib chiqilgan muqobillar

* `oqs` (liboqs FFI) — C kod va `unsafe`; sof Rust afzal.
* `aws-lc-rs` — FIPS yo'li bor, lekin build talablari og'ir; kelajakdagi variant.
