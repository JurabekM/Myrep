# AI Business Advisor Uzbekistan — Technical Architecture

**Versiya:** 1.0 | **Sana:** 2026-07-10 | **Bosqich:** 2 — Architecture

---

## 1. Yuqori darajali arxitektura

```
                        ┌─────────────────────────────────────┐
                        │            NGINX (TLS, LB)          │
                        └──────────┬──────────────┬───────────┘
                                   │              │
                    ┌──────────────▼───┐   ┌──────▼──────────────┐
                    │  Next.js 14 App  │   │   FastAPI Backend    │
                    │  (React, TS,     │   │   REST + WebSocket   │
                    │   Tailwind,      │   │   JWT/OAuth2, RBAC   │
                    │   ShadCN, PWA)   │   └──┬────┬────┬────┬───┘
                    └──────────────────┘      │    │    │    │
                          ┌───────────────────┘    │    │    └──────────────┐
                          ▼                        ▼    ▼                   ▼
                  ┌───────────────┐   ┌─────────────┐ ┌──────────┐  ┌──────────────┐
                  │   MongoDB     │   │    Redis    │ │  Qdrant  │  │  RabbitMQ    │
                  │ (+ GridFS)    │   │ cache/rate/ │ │ vectors  │  │  → Celery    │
                  │ users, chats, │   │ sessions/   │ │ RAG      │  │  workers     │
                  │ docs, audit   │   │ pubsub      │ │          │  │ (OCR, embed, │
                  └───────────────┘   └─────────────┘ └──────────┘  │  ingest, TTS)│
                                                                    └──────────────┘
                          ┌─────────────────────────────────────┐
                          │        AI Provider Layer            │
                          │ OpenAI │ Anthropic │ Gemini │ DeepSeek │
                          │ Mistral │ Llama │ Qwen │ Local (Ollama)│
                          └─────────────────────────────────────┘
```

**Uslub:** Modular Monolith (Clean Architecture) — mikroservis emas.
**Sabab:** MVP bosqichida bitta deploy birligi tezroq ishlab chiqiladi va debug qilinadi;
modullar orasidagi chegara qat'iy (har modul: router → service → repository), shuning
uchun kelajakda istalgan modulni alohida servisga ajratish oson. Celery og'ir ishlarni
(OCR, embedding, hujjat ingest) allaqachon alohida jarayonga chiqaradi.

## 2. Backend — Clean Architecture qatlamlari

```
backend/
├── app/
│   ├── main.py                    # FastAPI app factory, lifespan, DI container
│   ├── core/                      # Kesishuvchi infratuzilma
│   │   ├── config.py              # Pydantic Settings (env-based, secrets)
│   │   ├── security.py            # JWT, password hashing, 2FA (TOTP)
│   │   ├── dependencies.py        # DI providers (get_db, get_current_user, RBAC)
│   │   ├── middleware.py          # CORS, rate limit, request-id, audit
│   │   ├── exceptions.py          # Domain exception → HTTP mapping
│   │   └── logging.py             # Structured JSON logging
│   ├── domain/                    # Sof biznes-logika (framework-siz)
│   │   ├── entities/              # User, Conversation, Message, Document, ...
│   │   ├── value_objects/         # TaxRegime, Money, ConfidenceScore, ...
│   │   └── interfaces/            # Repository & service abstraksiyalari (ABC)
│   ├── infrastructure/
│   │   ├── database/              # Mongo (motor), indexes, migrations
│   │   ├── cache/                 # Redis client, cache decorators
│   │   ├── vector/                # Qdrant client
│   │   ├── storage/               # GridFS fayl saqlash
│   │   ├── queue/                 # Celery app + tasks
│   │   └── repositories/          # Interfeyslarning Mongo implementatsiyalari
│   ├── ai/                        # AI Provider abstraction
│   │   ├── base.py                # LLMProvider ABC: complete(), stream(), embed()
│   │   ├── providers/             # openai_, anthropic_, gemini_, deepseek_,
│   │   │                          # mistral_, llama_, qwen_, local_ollama_
│   │   ├── router.py              # Model tanlash, fallback chain, cost tracking
│   │   ├── safety/                # confidence, hallucination, prompt-injection
│   │   └── prompts/               # Versiyalangan prompt library (YAML)
│   ├── rag/
│   │   ├── ingestion.py           # lex.uz scraper + hujjat pipeline
│   │   ├── chunking.py            # Semantic + recursive chunking
│   │   ├── embeddings.py          # Embedding service (provider-agnostic)
│   │   ├── retrieval.py           # Hybrid search (dense + BM25) + rerank
│   │   └── citation.py            # Manba havolalari
│   └── modules/                   # 10 feature-modul, har biri bir xil tuzilishda:
│       ├── auth/                  #   router.py  → HTTP layer (thin)
│       ├── chat/                  #   service.py → biznes-logika
│       ├── consultant/            #   schemas.py → Pydantic request/response
│       ├── legal/                 #   repository.py → data access
│       ├── tax/
│       ├── marketing/
│       ├── documents/
│       ├── finance/
│       ├── dashboard/
│       └── admin/
├── tests/                         # unit / integration / api / security / ai
├── alembic-mongo/                 # Migration skriptlari (mongodb-migrations)
├── Dockerfile
└── pyproject.toml
```

**Flask haqida:** asosiy backend — FastAPI (async, WebSocket, OpenAPI avtomatik).
Flask varianti `adapters/flask_compat/` moduli sifatida qo'shiladi — service layer
framework-agnostic bo'lgani uchun bir xil servislar Flask blueprintlari orqali ham
ochilishi mumkin (talabda ko'rsatilgani uchun; production tavsiyasi FastAPI).

## 3. Frontend

```
frontend/
├── src/
│   ├── app/                       # Next.js App Router
│   │   ├── (auth)/                # login, register, 2fa
│   │   ├── (app)/                 # chat, consultant, legal, tax, marketing,
│   │   │                          # documents, finance, dashboard, profile
│   │   ├── (admin)/               # admin panel
│   │   └── api/                   # BFF route handlers (token refresh proxy)
│   ├── components/
│   │   ├── ui/                    # ShadCN primitivlari
│   │   ├── chat/                  # MessageList, Composer (voice, file), Markdown
│   │   ├── charts/                # Recharts wrapperlar (dashboard)
│   │   └── shared/
│   ├── lib/                       # api-client (typed, OpenAPI-generated), ws, i18n
│   ├── hooks/                     # useChat (SSE/WS streaming), useAuth, ...
│   ├── stores/                    # Zustand (session, chat state)
│   └── styles/
├── public/                        # PWA manifest, icons
└── e2e/                           # Playwright testlar
```

- **i18n:** next-intl — uz-Latn, uz-Cyrl, ru, en
- **Streaming:** WebSocket (chat) + SSE fallback
- **Dark mode:** `next-themes`, WCAG AA accessibility

## 4. Ma'lumotlar bazasi dizayni (MongoDB kolleksiyalari)

| Kolleksiya | Asosiy maydonlar | Indexlar |
|---|---|---|
| `users` | email, phone, password_hash, role, plan, 2fa_secret, profile{industry, business_type, goals, revenue, employees, location} | email(uniq), phone(uniq) |
| `conversations` | user_id, title, module, model, summary(memory), created_at | user_id+updated_at |
| `messages` | conversation_id, role, content, attachments[], tokens, confidence, sources[], feedback | conversation_id+created_at |
| `documents` | user_id, gridfs_id, type, ocr_text, analysis{}, status | user_id, status |
| `kb_sources` | type(lex.uz/manual), url, version, checksum, chunks_count | url(uniq) |
| `payments` | user_id, provider, amount, plan, status, external_id | user_id, external_id(uniq) |
| `audit_logs` | actor_id, action, resource, ip, ua, before/after | actor_id+ts, TTL(1 yil) |
| `prompt_templates` | key, version, locale, content, active | key+version(uniq) |
| `feature_flags` | key, enabled, rollout_pct, plans[] | key(uniq) |
| `usage_stats` | user_id, date, tokens, cost, module | user_id+date(uniq) |

**Redis:** sessiyalar, rate-limit hisoblagichlar, javob keshi, Celery broker natijalar, WS pub/sub.
**Qdrant:** `legal_uz` (lex.uz), `knowledge_base`, `user_documents` kolleksiyalari — har biri
payload filtri bilan (user_id izolatsiyasi).

## 5. AI qatlami

### 5.1 Provider abstraction

```python
class LLMProvider(ABC):
    async def complete(self, req: CompletionRequest) -> CompletionResponse: ...
    async def stream(self, req: CompletionRequest) -> AsyncIterator[Chunk]: ...
    async def embed(self, texts: list[str]) -> list[Vector]: ...
    @property
    def capabilities(self) -> ProviderCapabilities: ...  # vision, tools, max_ctx
```

- **ModelRouter:** modul + tarif + capability bo'yicha model tanlaydi; xato bo'lsa
  fallback chain (masalan: Claude → GPT → DeepSeek → Local).
- Har chaqiriq narxi `usage_stats` ga yoziladi (token-level cost tracking).
- Admin paneldan model konfiguratsiyasi (default model, temperature, limits) o'zgartiriladi.

### 5.2 AI Safety pipeline (har javob uchun)

```
user input → [prompt-injection filter] → [PII masking] → LLM →
→ [hallucination check: RAG grounding score] → [confidence score] →
→ [category classifier] → [disclaimer injector (legal/tax)] → response
```

Disclaimer (huquq/soliq): *"Bu AI asosidagi ma'lumot bo'lib, yakuniy qaror uchun
malakali yurist/soliq maslahatchisi bilan maslahatlashing."*

### 5.3 RAG

1. **Ingestion:** lex.uz scraper (hujjat versiyalari kuzatiladi) + admin KB upload → Celery
2. **Chunking:** strukturaviy (modda/band bo'yicha) + recursive fallback, 512–1024 token
3. **Hybrid retrieval:** Qdrant dense + BM25 (Mongo text index) → RRF birlashtirish → rerank
4. **Citation:** har chunk manbasi (qonun nomi, modda, URL) javobga biriktiriladi

## 6. Xavfsizlik

- **Auth:** JWT access (15 min) + refresh rotation (Redis blocklist), OAuth2 (Google), 2FA TOTP
- **RBAC:** `user`, `pro`, `business`, `moderator`, `admin` — permission-based dekoratorlar
- **Rate limit:** Redis sliding window — tarif bo'yicha (IP + user darajasida)
- **Input validation:** Pydantic strict mode; fayl: MIME + magic bytes + hajm cheklovi
- **OWASP:** XSS (CSP, sanitize markdown), CSRF (SameSite + token BFF da), NoSQL injection (Pydantic + motor param.), SSRF (scraper allowlist)
- **Secrets:** env + Docker secrets; production'da Vault-ready interface
- **Audit:** har mutatsiya `audit_logs` ga (before/after diff)

## 7. Deployment

```
docker-compose.yml        # dev: backend, frontend, mongo, redis, qdrant, rabbitmq,
                          #      celery-worker, celery-beat, nginx
docker-compose.prod.yml   # prod override: replicas, healthchecks, secrets
k8s/                      # Kubernetes manifestlar (Kustomize) — ready
.github/workflows/
  ├── ci.yml              # lint (ruff, eslint) → typecheck (mypy, tsc) → tests → coverage gate 95%
  ├── security.yml        # bandit, npm audit, trivy image scan
  └── deploy.yml          # build → push registry → deploy (SSH/K8s)
monitoring/               # prometheus.yml, grafana dashboards, sentry init
```

## 8. Texnologik qarorlar va asoslar

| Qaror | Tanlov | Nima uchun |
|---|---|---|
| Backend framework | FastAPI | Async (LLM streaming), avtomatik OpenAPI, Pydantic validation, WebSocket |
| Arxitektura uslubi | Modular Monolith | MVP tezligi + keyin servislarga ajratish oson; Celery og'ir ishlarni ajratadi |
| DB | MongoDB | Chat/hujjat kabi yarim-strukturali ma'lumotlar; GridFS fayllar uchun |
| Vector DB | Qdrant | Self-hosted, payload filtering (multi-tenant izolatsiya), hybrid-ga tayyor |
| Queue | RabbitMQ + Celery | OCR/embedding/ingest — sekundlab davom etadigan ishlar API dan ajratiladi |
| Frontend | Next.js App Router | SSR (SEO landing), RSC, BFF pattern (tokenlarni brauzerdan yashirish) |
| State | Zustand + TanStack Query | Redux'dan yengil, server-state alohida |
| Charts | Recharts | ShadCN bilan mos, deklarativ |
| OCR | Tesseract (uz/ru/en) + vision-LLM fallback | Bepul lokal OCR + murakkab rasmlar uchun LLM |

## 9. Bosqichma-bosqich ishlab chiqish rejasi

| Bosqich | Natija | Taxminiy hajm |
|---|---|---|
| 3. Database | Mongo modellari, indexlar, migratsiya, Redis/Qdrant klientlar | ~15 fayl |
| 4. Backend | Core + auth + 10 modul routerlari/servislari, Swagger | ~80 fayl |
| 5. Frontend | Next.js app, chat UI, dashboard, admin, i18n | ~90 fayl |
| 6. AI | 8 provider, router, safety pipeline, prompt library | ~25 fayl |
| 7. RAG | lex.uz ingestion, hybrid search, citation | ~15 fayl |
| 8. Testing | Unit/integration/API/security/AI testlar, 95% gate | ~60 fayl |
| 9. Deployment | Docker, K8s, CI/CD, monitoring | ~25 fayl |
