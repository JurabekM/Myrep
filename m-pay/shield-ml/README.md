# shield-ml

M-Pay Shield uchun sintetik fraud ma'lumotlari, LightGBM o'qitish va ONNX eksport.

## Train/serve parity

Python **faqat xom hodisalarni** generatsiya qiladi. Belgilarni Rust'dagi o'sha feature store
(`crates/mpay-shield/src/features.rs`) hisoblaydi — `shield-replay featurize`. Shu tufayli model
o'qitilgan belgilar onlayn skoringdagi belgilar bilan aynan bir xil (alohida Python implementatsiyasi
yo'q, drift bo'lmaydi). Model metadatasidagi belgi nomlari Rust'dagi ro'yxatga mos kelmasa, server
modelni yuklamaydi.

## Quvur

```bash
uv sync
```

```bash
uv run python generate.py --seed 1 --out data/events_train.csv
```

```bash
uv run python generate.py --seed 2 --out data/events_test.csv
```

```bash
cargo run --release -p mpay-shield --bin shield-replay -- featurize shield-ml/data/events_train.csv shield-ml/data/train
```

```bash
cargo run --release -p mpay-shield --bin shield-replay -- featurize shield-ml/data/events_test.csv shield-ml/data/test
```

```bash
uv run python train.py
```

`train.py` `crates/mpay-shield/models/shield_v0.onnx` va `shield_v0.json` ni yozadi, ONNX va
LightGBM ehtimollarini solishtiradi (farq < 1e-4) va `data/parity.csv` ni chiqaradi
(Rust testi uchun `crates/mpay-shield/tests/data/parity.csv` ga nusxalanadi).

Baholash va benchmark (Rust dvigateli: qoidalar + ML):

```bash
cargo run --release -p mpay-shield --bin shield-replay -- parity shield-ml/data/parity.csv
```

```bash
cargo run --release -p mpay-shield --bin shield-replay -- evaluate shield-ml/data/events_test.csv shield-ml/data/eval_test.json
```

```bash
cargo run --release -p mpay-shield --bin shield-replay -- bench shield-ml/data/events_train.csv shield-ml/data/events_test.csv
```

## Stsenariylar (`generate.py`)

| Stsenariy | Mohiyati |
|---|---|
| `account_takeover` | hujumchi qurilmasi qurbon kartasini tokenlashtiradi; odatdan 5–20× katta summalar, ko'pincha tunda, P2P/onlayn |
| `card_testing` | o'g'irlangan kartalar qurilmalarda, onlayn merchantlarda tez-tez kichik summalar |
| `mule_network` | qurilma–karta halqalari (har karta 2–3 qurilmada), muntazam P2P yechib olish |
| `device_farm` | bitta qurilmada 10–25 karta qisqa vaqtda |
| `p2p_wave` | buzilgan ilova orqali 60–120 kartadan 10 daqiqa ichida P2P yechib olish |
| `legit_*` | qiyin legit holatlar: yangi telefon, sayohat, yirik xarid, oylik kuni P2P |

Natijalar: `docs/shield-report.md`.
