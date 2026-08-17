# AI Business Advisor Uzbekistan — Standalone Architecture

**Versiya:** 2.0 (standalone) | **Sana:** 2026-07-10

Mutlaqo mustaqil (standalone), faqat **Python**, **Docker'siz**, yagona `python main.py`
bilan ishga tushadigan desktop platforma.

## 1. Asosiy tamoyillar (prompt cheklovlariga muvofiqlik)

| Talab | Yechim |
|---|---|
| Faqat Python | Butun stack Python 3.10+; UI — PyQt6 (Node/JS yo'q) |
| Kalitsiz / tekin AI | Gibrid router: bepul rasmiy API'lar (Gemini/Groq/OpenRouter free tier) + lokal GGUF model (`llama-cpp-python`) oflayn fallback. **g4f/reverse-engineered emas** — qonuniy va barqaror |
| Zero infra / Docker yo'q | SQLite (`.db` fayl), lokal TF-IDF cosine vektor qidiruv (scikit-learn), `queue.Queue` + `ThreadPoolExecutor` navbatlar |
| Yagona run skript | `python main.py` — deps tekshiradi, bazani ko'taradi, workerlarni ishga tushiradi, UI ochadi |
| FAANG standartlari | Clean Architecture, SOLID, DRY, KISS, Service Layer |

## 2. Qatlamli arxitektura

```
main.py                          # Yagona kirish nuqtasi (orkestrator)
requirements.txt
app/
├── core/
│   ├── config.py                # Lokal config (JSON fayl + env), yo'llar
│   ├── logging_setup.py         # Fayl + konsol audit loglari
│   ├── exceptions.py            # Domen xatolari
│   └── bootstrap.py             # Deps tekshiruvi, papka/DB init
├── data/                        # DATA LAYER (2-bosqich)
│   ├── database.py              # SQLite ulanish (WAL, thread-safe)
│   ├── schema.py                # Jadval sxemalari + migratsiya
│   └── repositories/            # conversation, message, document, kb, settings, usage
├── rag/                         # LOKAL RAG (2-bosqich)
│   ├── chunking.py              # Strukturaviy (qonun moddasi) + rekursiv chunking
│   ├── vector_store.py          # TF-IDF + cosine similarity (sklearn), SQLite'da saqlash
│   └── retriever.py             # Qidiruv + kontekst formatlash + citation
├── ai/                          # AI ENGINE (3-bosqich)
│   ├── base.py                  # LLMProvider ABC (chat, stream)
│   ├── providers/
│   │   ├── gemini_free.py       # Google Gemini bepul tarif
│   │   ├── groq_free.py         # Groq bepul tarif
│   │   ├── openrouter_free.py   # OpenRouter :free modellari
│   │   └── local_llama.py       # llama-cpp-python (oflayn GGUF)
│   ├── router.py                # Gibrid router + fallback chain + usage tracking
│   ├── safety.py                # Prompt-injection, confidence, hallucination, disclaimer
│   └── prompts.py               # Tizim va modul promptlari (o'zbekcha)
├── services/                    # SERVICE LAYER (4-bosqich)
│   ├── chat_service.py          # Suhbat, xotira (rolling summary)
│   ├── consultant_service.py    # Biznes hujjatlari generatsiyasi
│   ├── legal_service.py         # Lex.uz RAG + shartnoma tahlili
│   ├── tax_service.py           # Soliq tushuntirish (kalkulyator ustida)
│   ├── finance_service.py       # Moliya tushuntirish (kalkulyator ustida)
│   ├── marketing_service.py     # Marketing generatsiya
│   ├── document_service.py      # Fayl o'qish (pdf/docx/xlsx/csv/OCR)
│   ├── voice_service.py         # STT/TTS (lokal/bepul)
│   ├── calculators/
│   │   ├── tax_calculator.py    # Sof Python soliq formulalari
│   │   └── finance_calculator.py# NPV, IRR, ROI, break-even, kredit
│   └── lex_scraper.py           # Lex.uz scraping (ehtiyotkor, allowlist)
├── workers/
│   └── task_manager.py          # queue.Queue + ThreadPoolExecutor fon vazifalari
└── ui/                          # UI (5-bosqich)
    ├── theme/
    │   ├── dark.qss             # Ultra Dark QSS
    │   └── palette.py           # Rang konstantalari
    ├── main_window.py           # Sidebar + stacked sahifalar
    ├── widgets/                 # ChatBubble, Markdown viewer, Toast, Chart canvas
    └── pages/                   # chat, consultant, legal, tax, finance,
                                 # marketing, documents, dashboard, settings
tests/                          # unit + integration (7-bosqich)
```

## 3. Ma'lumotlar oqimi (chat misolida)

```
UI (chat page) → ChatService → RAG retriever (agar legal/kb) →
→ ModelRouter (bepul API → fallback → lokal model) → SafetyPipeline
(injection filtri, confidence, disclaimer) → SQLite (message saqlash) → UI
```

Barcha AI chaqiruvlar UI thread'ini bloklamaslik uchun `TaskManager` (ThreadPoolExecutor)
orqali fon oqimida bajariladi; natija Qt signal orqali UI'ga qaytariladi.

## 4. Lokal ma'lumotlar bazasi (SQLite jadvallari)

| Jadval | Maqsad |
|---|---|
| `conversations` | Suhbatlar (title, module, summary/memory) |
| `messages` | Xabarlar (role, content, sources, confidence, category) |
| `documents` | Yuklangan fayllar (yo'l, ajratilgan matn, holat) |
| `kb_chunks` | RAG chunklari (matn, embedding-vektor JSON, manba, modda) |
| `settings` | Foydalanuvchi sozlamalari (biznes profili, tanlangan model) |
| `usage_stats` | AI foydalanish statistikasi (dashboard uchun) |

## 5. AI gibrid strategiya

`ModelRouter` provayderlarni **ustuvorlik bo'yicha** sinaydi; biri ishlamasa (limit,
internet yo'q, xato) keyingisiga o'tadi:

```
1. Groq free        (tez, agar GROQ_API_KEY sozlangan bo'lsa)
2. Gemini free      (sifatli, GEMINI_API_KEY)
3. OpenRouter free  (:free modellar, OPENROUTER_API_KEY)
4. Local llama-cpp  (oflayn, kalitsiz — har doim mavjud fallback)
```

Kalitlar `config.json` yoki muhit o'zgaruvchilaridan olinadi. Hech biri sozlanmasa,
tizim faqat lokal model bilan ishlaydi (birinchi ishga tushishda GGUF yuklab olinadi
yoki foydalanuvchi qo'lda joylashtiradi). Kalit olish bepul va karta talab qilmaydi —
Settings sahifasida yo'riqnoma beriladi.

## 6. Xavfsizlik va guardraillar

- **Prompt injection**: kirish matnida hujjum naqshlari (uz/ru/en) skrining qilinadi
- **Confidence score**: har javob ishonchlilik darajasi bilan belgilanadi
- **Hallucination check**: RAG kontekstiga asoslanish tekshiriladi (grounding)
- **Disclaimer**: huquq/soliq javoblariga majburiy ogohlantirish
- **Audit log**: barcha muhim amallar lokal fayl logiga yoziladi
- **Localhost-only**: agar FastAPI ishlatilsa ham, faqat 127.0.0.1'ga bog'lanadi (bu
  loyihada UI to'g'ridan-to'g'ri desktop, tashqi port ochilmaydi)

## 7. Bosqichlar

1. ✅ Arxitektura + core + bootstrap
2. Data layer (SQLite + lokal vektor)
3. AI engine (gibrid router + safety + lex scraper)
4. Biznes logika (kalkulyatorlar + service layer)
5. UI/UX (PyQt6 Ultra Dark + chartlar)
6. main.py orkestratsiya + workerlar
7. Testlar
