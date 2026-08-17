# AETHER-Q v4 — Kross-platforma Kripto-SDK

`AETHER_Q_V4_ENGINEERING_SPEC.md` spetsifikatsiyasining Rust reference implementatsiyasi:
hybrid post-kvant KEM protokoli (5 profil), PQDoubleRatchet va AEAD record layer, hamda
Python/Kotlin/Swift uchun UniFFI orqali avtomatik generatsiya qilingan binding'lar.

## Arxitektura

```
crates/
  aether-primitives/   kripto-primitivlar (X25519, ML-KEM-768, ML-DSA-65, Ed25519, HQC-192,
                        SHA3-256/SHAKE-256, ChaCha20-Poly1305/AES-256-GCM) — audited
                        tashqi crate'lar ustidan bayt-yo'naltirilgan `Kem`/`Signer` trait'lari
  aether-core/          protokol mantig'i: profil, combiner, AUTH-AKEM, Compress-KEM
                        ratchet, replay-himoya, record layer (spec 3,4,5,7-bo'limlar)
  aether-ffi/           UniFFI orqali Python/Kotlin/Swift'ga eksport (hozircha DEFAULT
                        profil handshake'i + record layer)
bindings/
  python/               generatsiya qilingan `aether_ffi.py`
  kotlin/               generatsiya qilingan `uniffi/aether_ffi/aether_ffi.kt`
  swift/                generatsiya qilingan `aether_ffi.swift` + C header/modulemap
```

Har bir profil qanday amalga oshirilgani haqida: `crates/aether-core/src/combiner.rs`,
`akem.rs`, `ratchet.rs`, `record.rs` — har biri spec bo'limiga havola bilan izohlangan.

## Talab qilinadigan asboblar

- Rust stable toolchain (`rustup`)
- Windows'da GNU host (`x86_64-pc-windows-gnu`) ishlatilmoqda, chunki MSVC Build Tools
  o'rnatilmagan muhitda linker sifatida to'liq mingw-w64 (masalan
  [winlibs](https://winlibs.com/)) kerak bo'ladi. Loyiha ildizida
  `rustup override set stable-x86_64-pc-windows-gnu` bajarilgan.

## Qurish va tekshirish

```sh
cargo build --workspace
cargo test --workspace
cargo clippy --workspace --all-targets -- -D warnings
```

Barcha uch crate ham muvaffaqiyatli quriladi, jami 28+ ta test (unit + KAT + interop)
o'tadi va clippy'da ogohlantirish yo'q.

## Profillar

| `profile_id` | Nomi | Tarkib |
| :--- | :--- | :--- |
| `0x01` | DEFAULT | X25519 + ML-KEM-768 (X-Wing combiner) |
| `0x02` | PARANOID | X25519 + ML-KEM-768 + HQC-192 (Triple-Hybrid) |
| `0x03` | MINIMAL | ML-KEM-768 standalone |
| `0x04` | COMPRESS | Stateful delta-compression ratchet (77-baytli frame) |
| `0x05` | AUTH_AKEM | Single-pass authenticated KEM (imzo + implicit rejection) |

Har bir profil uchun to'liq round-trip misoli:
`crates/aether-core/tests/interop.rs`.

## UniFFI binding'larni qayta generatsiya qilish

```sh
cargo build -p aether-ffi --release
./target/release/uniffi-bindgen generate \
  --library ./target/release/aether_ffi.dll \
  --language python --out-dir bindings/python
# --language kotlin / --language swift uchun xuddi shunday
```

Python bindingi haqiqiy native kutubxona bilan tekshirilgan:

```python
import aether_ffi as af

mlkem_kp = af.generate_mlkem768_keypair()
x_kp = af.generate_x25519_keypair()
encaps = af.default_encapsulate(mlkem_kp.public_key, x_kp.public_key)
shared = af.default_decapsulate(
    mlkem_kp.secret_key, x_kp.secret_key, x_kp.public_key,
    encaps.ct_mlkem, encaps.ct_x25519,
)
assert bytes(encaps.shared_secret) == bytes(shared)
```

(Ishlashi uchun `aether_ffi.dll`/`.so`/`.dylib` `aether_ffi.py` bilan bir papkada
yoki tizim kutubxona yo'lida bo'lishi kerak.)

Kotlin/Swift binding'lari generatsiya qilingan va kompilyatsiya uchun tayyor, lekin
to'liq Android/iOS build muhiti talab qilingani uchun bu bosqichda faqat generatsiya
tekshirildi (mobil loyihaga integratsiya keyingi bosqich).

## Ma'lum cheklovlar / keyingi bosqich

- `aether-ffi` hozircha faqat DEFAULT (0x01) profil handshake'i va record layer'ni
  qamrab oladi. PARANOID, MINIMAL, COMPRESS, AUTH-AKEM `aether-core`da to'liq
  implementatsiya qilingan va test qilingan, lekin FFI qatlamiga hali eksport
  qilinmagan.
- FFI chegarasida maxfiy baytlar (`Vec<u8>`) sifatida uzatiladi — `Zeroizing`
  himoyasi faqat Rust tomonida ishlaydi; chaqiruvchi tilda (Python/Kotlin/Swift)
  qo'lda tozalash zarur bo'lishi mumkin.
- ML-KEM/ML-DSA rasmiy NIST KAT vektorlariga solishtirilmagan (bu crate'lar
  ichki tasodifiylikka tayanadi); `tests/kat.rs`dagi testlar faqat protokol
  mantig'ining deterministik qismlarini (combiner, AAD, label'lar) qamrab oladi.
