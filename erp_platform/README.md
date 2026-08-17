# UzERP — Enterprise Resource Planning (100% Python)

Kichik va o'rta biznes uchun zamonaviy, mahalliylashtirilgan ERP platformasi —
**1C ning zamonaviy muqobili**. Butun tizim faqat Python'da yozilgan:
backend, web-interfeys va desktop GUI. JavaScript, Node.js, Docker,
Redis va boshqa tashqi serverlar **KERAK EMAS**.

```
┌──────────────────────────────────────────────────────────────┐
│  Desktop GUI (PyQt6)  │  Web (Flask, localhost:8000)  │ REST  │
│  ribbon · sidebar     │  dark theme · JS'siz          │ API   │
│  QtCharts · WebView   │  SVG grafiklar                │ +docs │
├──────────────────────────────────────────────────────────────┤
│         Servis qatlami (Service Layer + DI konteyner)         │
│  Sales · Inventory · Purchases · CRM · Accounting · HR ·      │
│  Payroll · Reports · Analytics · Export · Backup · Plugins    │
├──────────────────────────────────────────────────────────────┤
│    Repository · Migrations · SQLite/PostgreSQL (auto-detect)  │
└──────────────────────────────────────────────────────────────┘
```

---

## Ishga tushirish

Faqat Python (3.10+) o'rnatilgan bo'lsa kifoya:

```bash
python run.py
```

Yoki bir faylli monolit versiya:

```bash
python ERP_MONOLITH.py
```

Shu **bitta buyruq** avtomatik ravishda:
- kerakli papkalarni yaratadi (`data/`, `logs/`, `backups/`, `exports/`, `plugins/`)
- `config.yaml` ni generatsiya qiladi
- ma'lumotlar bazasini yaratadi va migratsiyalarni bajaradi
- admin foydalanuvchini yaratadi (parol `data/admin_credentials.txt` da)
- yetishmagan Python paketlarini o'zi o'rnatadi
- web-serverni ishga tushiradi → http://127.0.0.1:8000
- desktop GUI oynasini ochadi

**Hech qanday qo'lda sozlash talab qilinmaydi.**

### Ishga tushirish parametrlari

| Buyruq | Tavsif |
|---|---|
| `python run.py` | web-server + desktop GUI |
| `python run.py --web-only` | faqat web-server |
| `python run.py --desktop-only` | faqat desktop GUI |
| `python run.py --selfcheck` | tizim salomatligini tekshirish |
| `python run.py --demo` | namunaviy ma'lumotlar bilan |
| `python run.py --port 8080` | boshqa port |
| `python run.py --no-install` | avto-o'rnatishni o'chirish |

---

## Ikki ko'rinish: Enterprise struktura + Monolit

Loyiha **ikki xil, funksional jihatdan teng** ko'rinishda mavjud:

1. **Professional Enterprise strukturasi** — `src/` ichida modulli, qatlamli
   arxitektura (Clean Architecture, SOLID, Repository/Service/Factory pattern).

2. **`ERP_MONOLITH.py`** — bitta fayldagi butun ERP. `tools/build_monolith.py`
   Enterprise strukturadan avtomatik generatsiya qiladi: har bir modul manbasi
   fayl ichiga joylashtiriladi va maxsus import-loader orqali ishlatiladi.
   Natijada monolit **aynan bir xil kodni** ishlatadi — yagona faylni ko'chirib,
   `python ERP_MONOLITH.py` bilan ishga tushirsa bo'ladi.

Monolitni qayta generatsiya qilish:

```bash
python tools/build_monolith.py
```

---

## Modullar

**Savdo** — taklif (quotation), buyurtma (order), hisob-faktura (invoice),
POS kassa, qaytarish (return); konvertatsiya zanjiri, chegirmalar, shtrix-kod,
avtomatik QQS hisobi, to'lov holatlari.

**Ombor** — ko'p omborli qoldiqlar, kirim/chiqim/ko'chirish/tuzatish (jurnal
izli), inventarizatsiya (sanoq → farq → avto-tuzatish), o'rtacha tannarx
(weighted average), minimal zaxira nazorati.

**Xarid** — ta'minotchilar, xarid hujjatlari, qabul qilish, o'rtacha tannarx
yangilanishi, to'lovlar.

**Buxgalteriya** — hisoblar rejasi (O'zbekiston NAS-21), **dvoyna zapis**
jurnali (debet=kredit majburiy), savdo/xarid/to'lovlar bo'yicha avtomatik
o'tkazmalar, kassa/bank, QQS (12%), balans, foyda-zarar, aylanma qaydnoma,
pul oqimi, asosiy vositalar + amortizatsiya.

**HR + Payroll** — bo'limlar, xodimlar, davomat, ta'til, ish haqi
(daromad solig'i 12% + INPS badali), tasdiqlash va to'lash.

**CRM** — leadlar (savdo voronkasi, yutilganda avto-mijoz), faoliyatlar
(qo'ng'iroq/uchrashuv/vazifa), eslatmalar, mijoz tarixi.

**Hisobotlar** — dashboard, savdo/ombor/soliq/HR hisobotlari.

**Analitika** — KPI, prognoz (chiziqli regressiya), TOP mijoz/mahsulot,
ABC va XYZ tahlillari.

---

## Imkoniyatlar

| Kategoriya | Tafsilot |
|---|---|
| **Auth** | 9 rol, Permission Matrix (RBAC), sessiya timeout, hisob blokirovkasi |
| **Xavfsizlik** | PBKDF2 parol xesh, CSRF, rate-limit, XSS/SQL-injection himoya, audit trail, CSP |
| **Eksport** | PDF, Excel, CSV, Word, JSON |
| **Import** | CSV, Excel, JSON (o'zbek/rus ustun nomlari avto-taniladi, upsert) |
| **Backup** | Bir tugmali backup/restore, avto-backup, butunlik tekshiruvi |
| **Qidiruv** | Global qidiruv (Ctrl+K / Alt+K) |
| **REST API** | `/api/v1/*`, Bearer token, OpenAPI 3.0, `/api/docs` |
| **Pluginlar** | `plugins/` papkasi, `register(api)` interfeysi |
| **Integratsiya** | Click, Payme, Uzum Bank, Telegram, Email, SMS, Soliq, 1C — kalitsiz ishlaydi |
| **Database** | SQLite (standart) yoki PostgreSQL (avtomatik aniqlanadi) |

---

## Loyiha strukturasi

```
erp_platform/
├── run.py                    # yagona kirish nuqtasi (auto-installer)
├── ERP_MONOLITH.py           # bir faylli versiya (generatsiya qilingan)
├── config.yaml               # avtomatik yaratiladi
├── requirements.txt
├── src/
│   ├── app.py                # orkestrator
│   ├── core/                 # config, logger, security, cache, events,
│   │                         #   container (DI), audit, bootstrap
│   ├── database/             # connection, schema, migrations, repository
│   ├── auth/                 # rbac, service (sessiyalar)
│   ├── modules/              # sales, inventory, accounting, hr, crm,
│   │                         #   reports, analytics (biznes servislar)
│   ├── services/             # export, import, backup, search, plugin,
│   │                         #   integration
│   ├── web/                  # Flask server, theme, SVG grafiklar,
│   │   ├── views/            #   sahifalar (JS'siz HTML)
│   │   └── api/              #   REST API + OpenAPI
│   └── ui/                   # PyQt6 desktop GUI
├── tests/                    # unittest to'plami (68 test)
├── tools/build_monolith.py   # monolit generatori
└── plugins/                  # foydalanuvchi pluginlari
```

---

## Testlar

```bash
python -m unittest discover -s tests -p "test_*.py"
```

68 ta unit va integratsion test: core (xavfsizlik, utils, kesh), RBAC,
savdo/ombor, buxgalteriya (dvoyna zapis, balans), payroll, web va REST API,
monolit generatori.

---

## Texnologiyalar

- **Python 3.10+** (yagona talab)
- **Flask** — web-server (JavaScript ishlatilmaydi, sof server-rendered HTML)
- **PyQt6** (yoki PySide6) — desktop GUI, QtCharts, WebView
- **SQLite** (standart) / **PostgreSQL** (ixtiyoriy)
- **openpyxl, fpdf2, python-docx** — eksport (ixtiyoriy)

Kodlash uslubi: PEP8, SOLID, DRY, KISS, Clean Architecture, Repository +
Service Layer + Factory + Strategy + Observer + Dependency Injection pattern'lari.
Barcha moliyaviy hisob-kitoblar `decimal.Decimal` bilan (float xatolarisiz).

---

*UzERP v1.0.0 — Enterprise ERP · 100% Python*
