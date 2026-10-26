# mpay-e2e

To'liq stsenariylar: `mpay-server` jarayon ichida (`Sandbox`), soft-wallet (PQ Link) va loopback
soft-karta orqali.

| Test | Nima tekshiriladi |
|---|---|
| `tests/m3_provisioning.rs` | PQ Link + provisioning, OTP, lifecycle, audit, DB'da ochiq PAN yo'q |
| `tests/m4_tap_to_pay.rs` | tap → ISO 8583 → emitent: `00`, `05`, `51`, `91`, `Q1`, CDCVM, ARPC |
| `tests/m5_shield.rs` | Shield dvigateli HTTP orqali: qurilma fermasi, YELLOW/OTP, `59` |
| `tests/pkcs11_e2e.rs` | SoftHSM2 bilan to'liq oqim (`--features pkcs11`, Docker: `scripts/softhsm-test.sh e2e`) |

```bash
cargo test -p mpay-e2e
```

## mpay-load (yuk generatori)

Alohida jarayondagi release `mpay-server` ga: `prepare` (yuk hisoblari), `run` (provisioning +
avtorizatsiya, kechikish foizliklari va javob kodlari). Odatda skript orqali:

```bash
bash scripts/load-test.sh 200 32 60 engine full
```

Natijalar va tahlil: `docs/load-report.md`.
