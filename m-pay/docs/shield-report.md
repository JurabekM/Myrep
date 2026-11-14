# Shield v0 — sintetik baholash hisoboti

> Sana: 2026-10-24. Model `shield-lgbm-v0`, qoidalar `shield-rules-v0`.
> Qayta ishlab chiqarish: `shield-ml/README.md`.

## 1. Ma'lumotlar

| To'plam | Seed | Hodisalar | Tranzaksiyalar | Provisioning |
|---|---|---|---|---|
| train | 1 | 45 390 | 41 769 | 3 621 |
| test | 2 | 45 309 | 41 694 | 3 615 |

2 500 legit karta egasi, 7 kun, 400 do'kon + 30 onlayn + 15 P2P merchant; 5 ta fraud stsenariysi va
4 ta "qiyin legit" holat (`shield-ml/generate.py`). Train va test mustaqil seed'lar bilan.

## 2. O'lchangan natijalar (test to'plami, Rust dvigateli: qoidalar + ONNX)

### 2.1 Tranzaksiyalar

| Stsenariy | n | REVIEW yoki DECLINE | DECLINE (javob `59`) |
|---|---|---|---|
| account_takeover | 213 | 100,0 % | 99,1 % |
| card_testing | 511 | 100,0 % | 100,0 % |
| device_farm | 94 | 100,0 % | 100,0 % |
| mule_network | 507 | 100,0 % | 100,0 % |
| p2p_wave | 321 | 97,2 % | 95,3 % |
| legit | 38 368 | 0,0 % | 0,0 % |
| legit_big_purchase | 396 | 1,3 % | 0,8 % |
| legit_new_device | 532 | 4,1 % | 2,8 % |
| legit_salary_p2p | 640 | 0,8 % | 0,2 % |
| legit_travel | 112 | 0,0 % | 0,0 % |

### 2.2 Provisioning (ID&V)

| Stsenariy | n | YELLOW yoki RED | RED |
|---|---|---|---|
| account_takeover | 60 | 100,0 % | 28,3 % |
| card_testing | 148 | 69,6 % | 49,3 % |
| device_farm | 176 | 93,2 % | 77,8 % |
| mule_network | 112 | 71,4 % | 33,0 % |
| legit | 3 036 | 4,1 % | 0,0 % |
| legit_new_device | 83 | 80,7 % | 3,6 % |

Legit YELLOW holatlari — kartani **ikkinchi** qurilmaga qo'shish (`IDV_NEW_DEVICE_EXISTING_CARD`).
Bu holatda step-up OTP odatiy bank amaliyoti. Fermadagi va karta testlashdagi birinchi 1–3 karta
tabiiy ravishda GREEN (hali signal yo'q).

### 2.3 Model (faqat ML, test, `shield_v0.json`)

| Metrika | p ≥ 0,5 | p ≥ 0,8 |
|---|---|---|
| precision | 0,981 | 0,988 |
| recall | 0,995 | 0,989 |
| FPR | 0,080 % | 0,047 % |

ONNX ↔ LightGBM maksimal farq 8,7·10⁻⁶; Rust (tract) ↔ Python (onnxruntime) — 1,5·10⁻⁷ (500 qator).

### 2.4 Kechikish (release, Windows, bitta oqim)

`shield-replay bench`: 45 390 hodisa bilan qizdirilgan omborda 41 694 tranzaksiya (belgilar + qoidalar + ONNX):

| p50 | p95 | p99 | max |
|---|---|---|---|
| 1,04 ms | 1,66 ms | **1,94 ms** | 8,58 ms |

Talab: p99 < 50 ms — bajarildi.

## 3. Cheklovlar (halol baho)

* Ma'lumotlar **sintetik** va stsenariylar generator qoidalari bilan aniq ajraladi — real
  ma'lumotlarda natijalar sezilarli past bo'ladi. Bu raqamlar dvigatel va quvur to'g'ri ishlashining
  isboti, real samaradorlikning bahosi emas.
* Belgilar ombori va graf xotirada, bitta instansiya uchun (`TODO(spec):` taqsimlangan ombor).
* Geo-anomaliya faqat mamlakat darajasida (terminal koordinatalari ISO 8583 subsetida yo'q).
* Merchant toifasi (P2P) prefiks bo'yicha; production'da MCC kerak.
* `ort` backend (ADR-0005) qo'shilmagan: tract p99 talabini 25× zaxira bilan bajaradi.
