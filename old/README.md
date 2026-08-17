# AI Business Advisor Uzbekistan

O'zbekistondagi kichik biznes, tadbirkorlar va startaplar uchun AI asosidagi
biznes-maslahat SaaS platformasi: strategiya, marketing, soliq, huquq (lex.uz
RAG), moliya, hujjat tahlili va boshqalar.

## Arxitektura

Modular Monolith (Clean Architecture) — batafsil: [docs/02-ARCHITECTURE.md](docs/02-ARCHITECTURE.md)

| Qatlam | Texnologiya |
|---|---|
| Frontend | Next.js 14, TypeScript, TailwindCSS, Zustand, Recharts, PWA |
| Backend | FastAPI (async), Celery + RabbitMQ, WebSocket/SSE streaming |
| Ma'lumotlar | MongoDB (+GridFS), Redis, Qdrant (vektor) |
| AI | 8 provider (OpenAI, Claude, Gemini, DeepSeek, Mistral, Llama, Qwen, Ollama), fallback chain, RAG (hybrid search), safety pipeline |
| Deploy | Docker Compose, Nginx, GitHub Actions, Prometheus + Grafana, Sentry |

## Tez boshlash

**Windows:** `.\run.ps1` — hammasini o'zi qiladi (batafsil: [docs/03-RUN-GUIDE.md](docs/03-RUN-GUIDE.md)).

**Linux/Mac:**

```bash
cp .env.example .env       # SECRET_KEY va kamida bitta AI API kalitini kiriting
docker compose up --build
```

- Frontend: http://localhost:3000
- API (Swagger): http://localhost:8000/docs
- Grafana: http://localhost:3001

## Lokal development (Dockersiz)

```bash
# Backend
cd backend
pip install -e ".[dev]"
uvicorn app.main:app --reload

# Celery worker (alohida terminal)
celery -A app.infrastructure.queue.celery_app worker -l info

# Frontend
cd frontend
npm install && npm run dev
```

Mongo, Redis, Qdrant, RabbitMQ servislarini `docker compose up mongo redis qdrant rabbitmq` bilan ko'tarish mumkin.

## Testlar

```bash
cd backend
pytest                     # 95% coverage gate (to'liq suite CI servislari bilan)
pytest tests/unit -q       # tez unit testlar
```

## Loyiha tuzilishi

```
backend/app/
  core/            # config, security (JWT/2FA), middleware, DI
  domain/          # entitylar, value objectlar, repository interfeyslari
  infrastructure/  # Mongo, Redis, Qdrant, GridFS, Celery, repositorylar
  ai/              # provider abstraction, ModelRouter, safety, promptlar
  rag/             # chunking, hybrid retrieval, lex.uz ingestion
  modules/         # auth, chat, consultant, legal, tax, marketing,
                   # documents, finance, dashboard, admin
  adapters/        # flask_compat (Flask varianti)
frontend/src/
  app/             # Next.js App Router (auth, chat, dashboard, BFF routes)
  components/      # ChatWindow va boshqalar
  hooks/ stores/ lib/
docs/              # BRD, arxitektura
deploy/ monitoring/ .github/workflows/
```

## AI Safety

Har bir javob: prompt-injection skrining → LLM → hallucination/grounding
baholash → confidence score → kategoriya → huquq/soliq javoblariga majburiy
disclaimer. Soliq/moliya raqamlari AI emas, deterministik kalkulyatorlar
orqali hisoblanadi.

## Hujjatlar

- [Business Requirements](docs/01-BUSINESS-REQUIREMENTS.md)
- [Architecture](docs/02-ARCHITECTURE.md)
- API hujjati: ishga tushgach `/docs` (Swagger UI) va `/api/v1/openapi.json`
