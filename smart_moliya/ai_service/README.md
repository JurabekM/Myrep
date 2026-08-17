# Smart Moliya — AI Service (PyTorch + FastAPI)

Core Backend'dan mustaqil mikroservis. Og'ir PyTorch inferensi asosiy API'ni bloklamasligi
uchun alohida ishga tushiriladi (ichki tarmoq orqali chaqiriladi).

## Ishga tushirish

```bash
cd ai_service
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8100
```

Swagger UI: http://localhost:8100/docs

## Testlar

```bash
pip install pytest httpx
pytest
```

Joriy holat: **15 test** — haqiqiy PyTorch o'qitish/inferensi, forecast/anomaly/chatbot barcha holatlar, va edge-case/robustness testlar (bo'sh input, qisqa tarix, inferensiya tezligi < 1s).

## Modellar va endpointlar

| Endpoint | Model | Tavsif |
|---|---|---|
| `POST /api/v1/classify` | `CategoryClassifier` (PyTorch, bag-of-words + linear) | Tranzaksiya matnidan kategoriya bashorati (uz/ru kalit so'zlar bilan seed o'qitilgan) |
| `POST /api/v1/forecast/spending` | `LinearTrendModel` (PyTorch, gradient-descent linear regression) | Kunlik xarajat tarixidan kelasi 30 kunlik bashorat |
| `POST /api/v1/forecast/runout` | Xuddi shu trend modeli | Balans va daromad/xarajat trendidan "pul tugash" kunini hisoblaydi |
| `POST /api/v1/anomaly` | Z-score statistik model | Kategoriya tarixidan keskin chetlanган tranzaksiyani (potentsial xato/firibgar) belgilaydi |
| `POST /api/v1/chatbot` | Intent-based (kalit so'z) | uz/ru/en tilida moliyaviy savollarga javob |

## Muhim eslatma — production yo'l xaritasi

- **Classifier**: hozirgi model kichik seed to'plamda (`app/models/seed_data.py`) o'qitilgan baseline. Production'da `app/training/train_classifier.py` orqali haqiqiy foydalanuvchi tranzaksiyalari bilan qayta o'qitiladi va vazn fayli `app/models/weights/`ga saqlanadi (hozircha runtime'da xotirada o'qitiladi — instant, GPU shart emas).
- **Chatbot**: hozirgi implementatsiya kalit so'z asosidagi deterministik javob beruvchi (LLM API kaliti talab qilinmaydi, offline ishlaydi). `ChatbotService.reply()` interfeysi o'zgarmasdan, ichki implementatsiya haqiqiy LLM (RAG bilan tranzaksiya kontekstidan foydalangan holda) bilan almashtirilishi mumkin — buning uchun API kaliti va qaysi provayder ishlatilishi kerakligini alohida kelishish talab qilinadi.
- **Forecast**: chiziqli trend - oddiy va tushunarli baseline. Murakkab mavsumiylikni (masalan, oy boshida ko'p xarajat) hisobga olish uchun kelgusida ARIMA/Prophet yoki LSTM'ga almashtirish mumkin.
