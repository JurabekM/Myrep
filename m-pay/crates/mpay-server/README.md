# mpay-server

M-Pay monolit binari: axum HTTP API, barcha modullarni port trait'lari orqali yig'adi (ADR-0002).
API: `docs/specs/api.md`.

## Sandbox'ni ishga tushirish

```bash
cargo run -p mpay-server -- init --dir .mpay --tls
```

`init` `.mpay/` papkasini yaratadi (git'ga tushmaydi): `mpay.toml`, dev-urug', KEK bilan o'ralgan
ML-DSA-65 urug'i, sandbox attestatsiya CA, TLS sertifikati, API kalitlari (`dev-credentials.env`).
Server barmoq izi va API kalitlari ekranga bir marta chiqadi.

```bash
cargo run -p mpay-server -- serve --config .mpay/mpay.toml
```

```bash
cargo run -p mpay-server -- audit-verify --config .mpay/mpay.toml
```

## Konfiguratsiya

`mpay.toml` bo'limlari: `sandbox`, `[http]` (listen, TLS), `[database]`, `[keystore]`
(`memory` — faqat sandbox; `pkcs11` — `--features pkcs11` va `MPAY_PKCS11_*` muhit o'zgaruvchilari),
`[pqlink]` (ML-DSA blob, attestatsiya ildizlari, minimal xavfsizlik darajasi), `[vault]`,
`[vault.luk]`, `[shield]`, `[shield_stub]`, `[issuer]`, `[sandbox_api]`, `[rate_limit]`,
`[[auth.keys]]` (faqat SHA-256 xesh). `[database]`: `synchronous`, `max_connections` (ADR-0009).
Nisbiy yo'llar konfiguratsiya fayli papkasiga nisbatan.

Himoyalar: `memory` KeyStore va sandbox endpointlari faqat `sandbox = true` bilan; production'da
TLS majburiy. Loglar: metod, marshrut shabloni, status, davomiylik — tanalar hech qachon logga
yozilmaydi (`RUST_LOG`, `--log-json`).

* **So'rovlar chegarasi** (`ratelimit.rs`, `[rate_limit]`): IP / API kaliti / qurilma bo'yicha token
  bucket (429 + `Retry-After`) va bir vaqtdagi PQ Link handshake'lari semafori (503 `BUSY`).
* **Takroriy avtorizatsiyalar** (`dedup.rs`, `migrations/3001_acquirer_requests.sql`, ADR-0010):
  bir xil so'rov — avvalgi javob; shu STAN boshqa mazmun bilan — `94`.
