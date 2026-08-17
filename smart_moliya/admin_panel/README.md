# Smart Moliya — Admin Panel

FastAPI + Jinja2 server-rendered boshqaruv paneli. Asosiy backend bilan **bir xil
PostgreSQL bazasiga** ulanadi, lekin alohida xizmat sifatida ishlaydi (ORM modellari
import qilinmaydi — to'g'ridan-to'g'ri SQL, ikki xizmat bir-biriga bog'lanmagan).

## Bo'limlar

| Sahifa | Vazifa |
|---|---|
| Dashboard | Foydalanuvchilar/tranzaksiyalar soni, MAU, xarajatlar hajmi, so'nggi tranzaksiyalar |
| Foydalanuvchilar | Ro'yxat + bloklash/faollashtirish |
| Tranzaksiyalar | So'nggi 100 ta, foydalanuvchi telefon raqami bilan |
| Fraud Detection | Foydalanuvchi+kategoriya o'rtachasidan 2.5+ sigma chetlangan xarajatlar (SQL window stats) |
| Analitika | DAU grafigi (so'nggi 14 kun) |
| Xabarlar markazi | Bitta foydalanuvchiga yoki barchaga notification yuborish (`ADMIN_MESSAGE` turi) |

## Ishga tushirish (lokal)

```bash
cd admin_panel
python -m venv venv && venv\Scripts\activate
pip install -r requirements.txt
# .env: DATABASE_URL, ADMIN_USERNAME, ADMIN_PASSWORD, ADMIN_SECRET_KEY
uvicorn app.main:app --reload --port 8200
```

Brauzer: http://localhost:8200 (standart login: `admin` / `admin123` — **production'da .env orqali majburiy almashtiriladi**).

Docker Compose bilan butun tizim ichida: `docker compose -f infra/docker-compose.yml up` → http://localhost:8081

## Xavfsizlik

- Kirish: login/parol (constant-time solishtirish) → imzolangan sessiya cookie (JWT, httponly, 8 soat)
- Swagger/OpenAPI o'chirilgan (`docs_url=None`)
- Eslatma: `ADMIN_MESSAGE` notification turi backend'ning `0004` migratsiyasini talab qiladi (`alembic upgrade head`)

## Testlar

```bash
pip install pytest httpx
pytest    # 8 test - fake repository bilan, DB talab qilinmaydi
```
