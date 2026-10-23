# mpay-shield

Risk engine va ID&V. **M3–M4 holati:** faqat deterministik `StubShield` — `IdvDecider` va
`RiskScorer` port'larini test PAN stsenariy kodi va merchant ID bo'yicha bajaradi
(`docs/test-data.md`). Haqiqiy qoidalar (TOML), tezlik va graf belgilari, ML skor (`tract`/`ort`) — M5.

```bash
cargo test -p mpay-shield
```
