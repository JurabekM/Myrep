# mpay-pqlink

PQ Link v1 — server va qurilma orasidagi post-kvant gibrid kanal. Spetsifikatsiya:
`docs/specs/pqlink.md`.

| Modul | Vazifasi |
|---|---|
| `wire` | Xabarlar kodlashi (ClientHello, ServerHello, Sealed, ichki tarkiblar), qat'iy parserlar |
| `crypto` | X25519 + ML-KEM-768 gibrid KEM, transkript xeshlari, HKDF kalit jadvali, finished MAC, ChaCha20-Poly1305 yozuvlar |
| `identity` | `ServerIdentity` (pinlanadigan), `ServerSigner`, `KeyStoreServerSigner` (Ed25519 HSM'da, ML-DSA-65 urug'i KEK bilan o'ralgan `MlDsaSeedBlob`) |
| `attestation` | Android Key Attestation zanjiri tekshiruvi, KeyDescription tahlili, `AttestationPolicy` |
| `device` | `DeviceSigner` trait (Android: StrongBox; Rust: `SoftDeviceKey`) |
| `server` | `PqLinkServer`: `handle_hello`, `handle_finish`, `open`, `seal`; sessiyalar TTL va limit bilan |
| `client` | `ClientHandshake` → `PendingClient` → `ClientSession` |
| `sandbox` | (`sandbox-attestation` feature) sandbox attestatsiya CA va dasturiy qurilma kaliti — **faqat sandbox/testlar** |

## Foydalanish (qisqa)

```rust,ignore
let (hs, ch) = ClientHandshake::start(pinned_identity)?;
let sh = server.handle_hello(&ch)?;
let (pending, cf) = hs.on_server_hello(&sh, &device_key)?;
let (_info, sa) = server.handle_finish(&cf)?;
let mut session = pending.on_accept(&sa)?;
let (info, plaintext) = server.open(&session.seal(b"so'rov")?)?;
```

## Testlar

```bash
cargo test -p mpay-pqlink
```

* `tests/acvp.rs` — NIST ACVP vektorlari (ML-KEM-768, ML-DSA-65), `testvectors/acvp/`;
* `tests/handshake.rs` — handshake, replay, buzilgan imzo/MAC/yozuv, attestatsiya rad holatlari;
* fuzz: `cargo +nightly fuzz run pqlink_decode` (`m-pay/fuzz`).

ACVP qismini yangilash: NIST ACVP-Server'dan `internalProjection.json` fayllarini yuklab oling va

```bash
python scripts/trim_acvp.py <yuklangan-papka> testvectors/acvp
```
