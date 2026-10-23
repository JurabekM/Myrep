# ADR-0005: ONNX runtime — `tract` default, `ort` feature

* Holat: qabul qilingan (2026-10-23), M5 da amalga oshiriladi

## Kontekst

Shield ML skori Python'da o'qitilgan LightGBM → ONNX modelidan keladi. `ort` 2.0 hali RC
(2.0.0-rc.15) va onnxruntime native kutubxonasini talab qiladi (build paytida yuklab olinadi) —
on-prem va `cargo deny` uchun noqulay.

## Qaror

`MlScorer` trait. Standart implementatsiya — `tract-onnx` (sof Rust, ONNX-ML `TreeEnsemble`
operatorlari). `ort` — ixtiyoriy `ort` feature.

## Oqibatlar

* Default build'da native bog'liqlik yo'q. p99 < 50 ms benchmark ikkala backend bilan o'lchanadi.
