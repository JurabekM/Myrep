# AI Business Advisor Uzbekistan — Standalone

O'zbekiston tadbirkorlari uchun **mutlaqo mustaqil** (standalone) AI biznes-maslahatchi
desktop ilovasi. Faqat Python, **Docker yo'q**, tashqi baza yo'q, yagona `python main.py`.

## Imkoniyatlar

- 💬 **AI Chat** — jonli oqim (streaming), Markdown, suhbat xotirasi (SQLite)
- 📋 **Konsultant** — biznes-reja, SWOT, PESTEL, BMC, pitch deck, grant arizasi (17 framework)
- ⚖️ **Huquq** — lex.uz RAG savol-javob (manba havolalari bilan), shartnoma tahlili
- 🧮 **Soliq** — deterministik kalkulyator (QQS, aylanma, YTT/MChJ taqqoslash) + AI tushuntirish
- 💰 **Moliya** — kredit jadvali, break-even, NPV/IRR (sof Python, aniq)
- 📣 **Marketing** — kontent-plan, reklama matni, SMM, funnel
- 📄 **Hujjatlar** — PDF/DOCX/XLSX/CSV/rasm (OCR) o'qish va AI tahlil
- 📊 **Dashboard** — matplotlib grafiklar, biznes salomatligi
- ⚙️ **Sozlamalar** — bepul AI kalitlar, biznes profili

Hammasi **Ultra Dark** premium interfeys (PyQt6).

## Ishga tushirish

```bash
cd advisor
pip install -r requirements.txt
python main.py
```

Windows'da: `py -m pip install -r requirements.txt` so'ng `py main.py`.

Ilova birinchi ishga tushganda `~/.ai_advisor/` papkasida baza, loglar va sozlamalarni
yaratadi.

## AI'ni sozlash (bepul, karta shart emas)

Ilova ochilгач **Sozlamalar** sahifasiga o'ting va kamida bittasini kiriting:

| Provayder | Bepul kalit | Izoh |
|---|---|---|
| **Groq** | https://console.groq.com/keys | Eng tez, tavsiya etiladi |
| **Google Gemini** | https://aistudio.google.com/app/apikey | Sifatli, katta kontekst |
| **OpenRouter** | https://openrouter.ai/keys | `:free` modellar |

Router ularni ketma-ket sinaydi — biri limitga yetsa yoki ishlamasa, avtomatik
keyingisiga o'tadi.

### Oflayn rejim (internetsiz, kalitsiz)

`~/.ai_advisor/models/` papkasiga GGUF model faylini (masalan
`qwen2.5-3b-instruct-q4_k_m.gguf`) joylashtiring va `pip install llama-cpp-python`
o'rnating. Router internetdagi provayderlar ishlamasa shu lokal modelga tushadi.

> **Eslatma:** Soliq va moliya kalkulyatorlari AI'siz ham **to'liq ishlaydi** —
> ular sof Python formulalar.

## Arxitektura

Batafsil: [ARCHITECTURE.md](ARCHITECTURE.md). Qisqacha — Clean Architecture qatlamlari:

```
main.py                 # yagona kirish nuqtasi
app/
├── core/               # config, logging, exceptions, bootstrap
├── data/               # SQLite + repozitoriylar + migratsiya
├── rag/                # chunking + TF-IDF cosine vektor qidiruv (Docker'siz!)
├── ai/                 # provayder abstraksiyasi, gibrid router, safety
├── services/           # chat, consultant, legal, tax, finance, marketing, documents
│   └── calculators/    # sof Python soliq/moliya formulalari
├── workers/            # ThreadPoolExecutor fon vazifalari (Celery o'rniga)
├── ui/                 # PyQt6 Ultra Dark (tema, sahifalar, widgetlar)
└── container.py        # Composition Root (DI)
tests/                  # 43 test (unit + integration + UI smoke)
```

## Testlar

```bash
cd advisor
python -m pytest tests -q
```

43 test: soliq/moliya kalkulyatorlari, RAG chunking, vektor qidiruv, AI safety,
router fallback, SQLite data layer va butun UI qurilishi (offscreen smoke).

## Texnik cheklovlarga muvofiqlik

| Talab | Bajarilishi |
|---|---|
| Faqat Python | ✅ Butun stack Python; UI — PyQt6 |
| Kalitsiz/tekin AI | ✅ Bepul rasmiy tariflar + oflayn lokal model (g4f emas — qonuniy) |
| Docker/tashqi baza yo'q | ✅ SQLite fayl + TF-IDF lokal vektor + ThreadPoolExecutor |
| Yagona run skript | ✅ `python main.py` hammasini ko'taradi |
| Clean Architecture / SOLID | ✅ Qatlamli, DI konteyner, service layer |
