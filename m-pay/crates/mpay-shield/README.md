# mpay-shield

Real-time risk engine va ID&V: `RiskScorer` va `IdvDecider` port'lari.

```text
belgilar (feature store) → qoidalar (TOML) → ML (ONNX, tract) → skor 0–1000 → qaror
skor = min(1000, p_ml × 1000 × ml_weight + Σ qoida ballari)
```

| Modul | Vazifasi |
|---|---|
| `features` | Sirpanuvchi oynalar (karta/qurilma/merchant/global P2P), summa z-skori, soat noyobligi, graf belgilar; 27 tranzaksiya va 9 ID&V belgisi |
| `graph` | Qurilma–karta bipartit grafi: union-find komponentlar, darajalar, yangi qirralar; kalit almashtirilgan qurilma — asl tugunning taxallusi (ADR-0015) |
| `rules` | Deklarativ TOML qoidalar (`rules/default.toml`), belgi nomlari yuklashda tekshiriladi |
| `model` | `MlScorer` trait, `TractScorer` (sof Rust ONNX, `models/shield_v0.onnx` binarga joylangan) |
| `engine` | `Shield` — port'lar implementatsiyasi; qaror: max(qoida harakati, chegara) |
| `replay` + `bin/shield_replay` | sintetik hodisalar: featurize / evaluate / bench / parity |
| `stub` | deterministik test stub (M3–M4 testlari) |
| `snapshot` | Belgilar omborining snapshot'i (ADR-0026): versiyalangan, deterministik, SHA-256; qat'iy tiklash (`FeatureStore::snapshot/restore`, `Shield::snapshot/restore`) |

Qarorlar: tranzaksiya `APPROVE` / `REVIEW` (≥ 500) / `DECLINE` (≥ 800, emitent `59`);
provisioning `GREEN` / `YELLOW` (≥ 400, OTP) / `RED` (≥ 750).

Server: `mpay.toml` → `[shield] engine = "engine" | "stub"`, ixtiyoriy `rules_file`,
`model_file` + `model_meta_file`, `disable_ml`.

## Testlar va baholash

```bash
cargo test -p mpay-shield
```

`tests/model_parity.rs` — tract ↔ onnxruntime (500 qator), metadata drift rad etilishi, port'lar.
Sintetik baholash va benchmark: `shield-ml/README.md`, natijalar: `docs/shield-report.md`.
