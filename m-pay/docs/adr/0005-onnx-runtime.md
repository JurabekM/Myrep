# ADR-0005: ONNX runtime — `tract` default, `ort` feature

* Holat: qabul qilingan (2026-10-23), amalga oshirilgan (M5, 2026-10-24)

## Kontekst

Shield ML skori Python'da o'qitilgan LightGBM → ONNX modelidan keladi. `ort` 2.0 hali RC
(2.0.0-rc.15) va onnxruntime native kutubxonasini talab qiladi (build paytida yuklab olinadi) —
on-prem va `cargo deny` uchun noqulay.

## Qaror

`MlScorer` trait. Standart implementatsiya — `tract-onnx` (sof Rust, ONNX-ML `TreeEnsemble`
operatorlari). `ort` — ixtiyoriy `ort` feature.

## Oqibatlar

* Default build'da native bog'liqlik yo'q. p99 < 50 ms benchmark ikkala backend bilan o'lchanadi.

## Amalga oshirish (M5)

* `tract-onnx` 0.23.9 (`default-features = false`) — LightGBM'dan `onnxmltools` 1.16 eksport qilgan
  `TreeEnsembleClassifier` (LOGISTIC) ni yuklaydi; model binarga joylangan (157 KiB).
* Rust (tract) ↔ Python (onnxruntime) parity: 500 qatorda maksimal farq 1,5·10⁻⁷.
* p99 = 1,94 ms (belgilar + qoidalar + ONNX) — talabdan 25× tez. Shu sababli `ort` backend
  **qo'shilmadi**: native onnxruntime bog'liqligini oqlaydigan ehtiyoj yo'q. `MlScorer` trait
  saqlanadi — kerak bo'lsa `ort` feature mahalliy o'zgarish bilan qo'shiladi.
* Yig'ish narxi: tract debug profilda xotiraga og'ir (24 GB mashinada, boshqa og'ir jarayonlar bilan parallel yig'ishda rustc OOM) —
  `[profile.dev.package."*"] debug = false`.
