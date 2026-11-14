# mpay-terminal-sim

Telefonsiz e2e uchun dasturiy komponentlar va `mpay-tsim` CLI.

| Modul | Vazifasi |
|---|---|
| `apdu` | ISO 7816-4 qisqa APDU, `ApduHandler` (karta), `ApduTransport` trait; `Loopback` — shu jarayondagi kartaga. Keyin PC/SC (ACR122U) transporti shu trait ortida. |
| `card` | `SoftCard` — M-Pay Test Scheme applet'i: SELECT PPSE / AID, GPO (ATC++, LUK tanlash, ARQC), CDCVM siyosati (`6986`), ARPC tekshiruvi. Android HCE (M6) shu mantiqni takrorlaydi. |
| `terminal` | Terminal yadrosi: PPSE → AID → PDOL → GPO, avtorizatsiya uchun ICC teglari. |
| `http`, `wallet` | `mpay-server` client va soft-wallet (PQ Link, provisioning, OTP, LUK to'ldirish). |
| `state` | `mpay-tsim` hamyon fayli (**sandbox**: ichida qurilma kaliti va LUK'lar). |

## mpay-tsim

Avval server: `mpay-server init --dir .mpay --tls` va `mpay-server serve --config .mpay/mpay.toml`.
`init` demo hisoblarini `mpay.toml` dagi `[[issuer.accounts]]` ga yozadi.

```bash
cargo run -p mpay-terminal-sim --bin mpay-tsim -- --server https://localhost:8080 provision --pan <FPAN> --expiry 3112
```

```bash
cargo run -p mpay-terminal-sim --bin mpay-tsim -- --server https://localhost:8080 tap --amount 12500.00
```

`tap` opsiyalari: `--merchant RISKY000000001` (59), `--cdcvm` (biometriya simulyatsiyasi,
1 000 000 UZS dan yuqori summalar uchun), `--token tok_…`. Boshqa buyruqlar: `replenish`, `status`.

To'liq avtomatik smoke (haqiqiy binarlar, TLS):

```bash
bash scripts/smoke-e2e.sh
```
