# Loyihani ishga tushirish qo'llanmasi

## Eng oson yo'l — `run.ps1` skripti (tavsiya)

Loyiha ildizida PowerShell oching va:

```powershell
.\run.ps1
```

Skript o'zi:
1. Docker borligini tekshiradi (yo'q bo'lsa — o'rnatish yo'lini ko'rsatadi)
2. `.env` faylni yaratadi, xavfsiz `SECRET_KEY` generatsiya qiladi
3. OpenAI API kalitini so'raydi (bo'sh qoldirish mumkin, keyin `.env`ga yozasiz)
4. Butun stackni quradi va ishga tushiradi
5. Backend "tayyor" bo'lguncha kutadi va manzillarni chiqaradi

Boshqaruv:

```powershell
.\run.ps1 -Status   # servislar holati
.\run.ps1 -Logs     # jonli loglar (chiqish: Ctrl+C)
.\run.ps1 -Stop     # hammasini to'xtatish
```

> **Eslatma:** agar `.\run.ps1` "execution policy" xatosini bersa:
> `powershell -ExecutionPolicy Bypass -File .\run.ps1`

## Talab: Docker Desktop

Loyiha 4 ta infratuzilma servisiga muhtoj — **MongoDB, Redis, Qdrant, RabbitMQ**.
Ularni birma-bir o'rnatmaslik uchun Docker ishlatiladi.

O'rnatish (bir marta):

```powershell
winget install Docker.DockerDesktop
```

yoki https://www.docker.com/products/docker-desktop/ dan yuklab oling.
O'rnatgach kompyuterni qayta yoqing va Docker Desktop ilovasini oching
(pastki chap burchakda yashil "Engine running" ko'rinishi kerak).

## Ishga tushgach — manzillar

| Nima | Manzil | Izoh |
|---|---|---|
| **Ilova** | http://localhost:3000 | Ro'yxatdan o'ting → chat, konsultant, soliq... |
| API hujjati (Swagger) | http://localhost:8000/docs | Barcha endpointlarni sinash mumkin |
| Grafana | http://localhost:3001 | Monitoring (admin/admin) |
| RabbitMQ paneli | http://localhost:15672 | Navbatlar holati (guest/guest) |

Birinchi foydalanuvchini http://localhost:3000/register orqali yarating.
Admin qilish uchun (Mongo ichida rolni ko'tarish):

```powershell
docker compose exec mongo mongosh ai_advisor --eval "db.users.updateOne({email:'sizning@email.uz'},{`$set:{role:'admin'}})"
```

## AI API kaliti

AI javob berishi uchun `.env` faylida kamida bitta kalit bo'lishi shart:

```
OPENAI_API_KEY=sk-...        # https://platform.openai.com/api-keys
# yoki
ANTHROPIC_API_KEY=sk-ant-... # https://console.anthropic.com
# yoki arzonroq variant:
DEEPSEEK_API_KEY=sk-...      # https://platform.deepseek.com
```

DeepSeek ishlatsangiz `.env`da defaultni ham o'zgartiring:
`DEFAULT_CHAT_MODEL=deepseek:deepseek-chat`
(Embedding uchun baribir OpenAI kaliti kerak — RAG/legal qidiruv shunga tayanadi.)

Kalitni o'zgartirgach qayta ishga tushiring: `docker compose restart backend celery-worker`

## Docker'siz (developer rejimi)

Faqat kod ustida ishlayotganda qulay: bazalar Dockerda, kod lokal.

```powershell
# 1. Faqat infratuzilmani ko'tarish
docker compose up -d mongo redis qdrant rabbitmq

# 2. Backend (alohida terminal)
cd backend
pip install -e ".[dev]"
uvicorn app.main:app --reload          # http://localhost:8000

# 3. Celery worker (alohida terminal, hujjat tahlili uchun)
cd backend
celery -A app.infrastructure.queue.celery_app worker -l info --pool=solo

# 4. Frontend (alohida terminal)
cd frontend
npm install
npm run dev                            # http://localhost:3000
```

`.env` fayl loyiha ildizida bo'lishi kerak (backend uni o'qiydi).

## Tez-tez uchraydigan muammolar

| Muammo | Yechim |
|---|---|
| `port is already allocated` | Portni band qilgan dasturni yoping yoki `docker-compose.yml`da portni o'zgartiring |
| Backend `unhealthy` | `docker compose logs backend` — odatda `.env`da SECRET_KEY yo'q |
| Chat "Hech bir AI provider javob bermadi" | `.env`da API kalit noto'g'ri/yo'q; `docker compose restart backend` |
| Hujjat `processing`da qotib qoldi | Celery worker ishlayaptimi: `docker compose logs celery-worker` |
| Birinchi build juda sekin | Normal — image'lar yuklanadi (~2-3 GB). Keyingi safar tez. |
