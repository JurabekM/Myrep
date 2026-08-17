# Smart Moliya — Core Backend (FastAPI)

## Ishga tushirish

```bash
cd backend
python -m venv venv
venv\Scripts\activate          # Windows
pip install -r requirements.txt
copy .env.example .env         # DATABASE_URL, JWT_SECRET_KEY ni sozlang
alembic upgrade head           # PostgreSQL sxemasini yaratish
uvicorn app.main:app --reload
```

Swagger UI: http://localhost:8000/docs

## Testlar

```bash
pip install -r requirements-dev.txt
pytest                    # pytest.ini orqali avtomatik coverage hisoboti chiqadi
```

Joriy holat: **41 test**, ~78% coverage (`htmlcov/index.html` — batafsil hisobot). Servis qatlamining bir qismi past coverage'ga ega, chunki hozirgi testlar fake repository'lar bilan yoziladi (haqiqiy Postgres talab qilmaydi) — DB bilan bog'liq branch'lar (masalan xatolik holatlari) haqiqiy integratsion test muhitida (11-bosqich, Docker Compose) qo'shiladi.

### Stress test (Locust)

```bash
pip install -r requirements-dev.txt
uvicorn app.main:app          # backend ishga tushirilgan bo'lishi kerak
locust -f locustfile.py --host http://localhost:8000
```

`http://localhost:8089` da virtual foydalanuvchilar sonini belgilab boshlang — `locustfile.py` register→login→wallet yaratish→tranzaksiya qo'shish oqimini simulyatsiya qiladi.

## API endpointlari (v1)

| Router | Prefix | Tavsif |
|---|---|---|
| auth | `/api/v1/auth` | register, login, refresh, me; `otp/request`+`otp/verify` (SMS kod, dev'da kod javobda qaytadi); `google` (ID token, GOOGLE_CLIENT_ID sozlanmagan dev'da `mock-google:<email>:<ism>` qabul qilinadi) |
| categories | `/api/v1/categories` | tizim + foydalanuvchi kategoriyalari |
| wallets | `/api/v1/wallets` | CRUD, balans avtomatik tranzaksiyadan yangilanadi |
| transactions | `/api/v1/transactions` | yaratish/o'chirish, wallet balansini yangilaydi |
| budgets | `/api/v1/budgets` | limit + real-vaqt sarflangan/qolgan hisob |
| goals | `/api/v1/goals` | progress %, oylik zarur tejash |
| loans | `/api/v1/loans` | joriy penalty, muddati o'tganligi |
| debts | `/api/v1/debts` | lent/borrowed, settle |
| sync | `/api/v1/sync` | push (offline'dan) / pull (`since_version` cursor) |
| payments | `/api/v1/payments` | Click/Payme/UzumBank orqali hamyon to'ldirish (mock) — create/webhook/list, `{id}/simulate` (faqat non-production: mock to'lovni yakunlaydi) |
| banks | `/api/v1/banks` | Universal Bank API Layer (mock) — 8 bank ro'yxati, link, sync (tranzaksiyalarni import qilish) |
| reports | `/api/v1/reports` | `summary` (JSON), `export.pdf` (reportlab), `export.xlsx` (openpyxl, 3 sahifa) |
| gamification | `/api/v1/gamification` | `me` (XP/level/streak), `leaderboard`, `badges` (katalog) |
| challenges | `/api/v1/challenges` | faol challenge'lar, `join`, `mine`, `refresh` (progressni tranzaksiyalardan qayta hisoblaydi) |
| family | `/api/v1/family` | guruh yaratish/qo'shilish, a'zolar, `allowance` (pocket money), `tasks` (ro'yxat/yaratish/bajarish/tasdiqlash) |

Barchasi `Authorization: Bearer <access_token>` talab qiladi (auth va `/payments/webhook` router'laridan tashqari — webhook real hayotda provayderdan keladi va imzo bilan tekshiriladi).

## Mock to'lov oqimini sinash

```bash
# 1. Payment yaratish (checkout_url va payment id qaytadi)
curl -X POST localhost:8000/api/v1/payments -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"wallet_id":"<uuid>","provider":"click","amount":50000}'

# 2. Real provayder webhook signature generatsiya qilmaydi - test uchun
# MockPaymentProvider.sign() Python konsolida chaqirilishi mumkin, keyin:
curl -X POST localhost:8000/api/v1/payments/webhook -H "Content-Type: application/json" \
  -d '{"payment_id":"<uuid>","amount":50000,"signature":"<hisoblangan-imzo>"}'
```
