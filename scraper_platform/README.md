# 🕸️ Universal Web Scraping Platform (ScrapePro)

Python'da yozilgan professional darajadagi **universal web scraping**
platformasi. Oddiy HTML saytlardan tortib JavaScript (SPA), AJAX,
Cloudflare himoyali, infinite-scroll va e-commerce saytlargacha
ma'lumotlarni avtomatik yig'adi, tahlil qiladi, saqlaydi va eksport
qiladi.

Zamonaviy **PyQt6 Dark Theme** GUI va **CLI** rejimlarida ishlaydi.

---

## ✨ Asosiy imkoniyatlar

| Modul | Imkoniyat |
|-------|-----------|
| **Scraping Engine** | Sayt turini avtomatik aniqlash (requests / Playwright / cloudscraper / undetected-chromedriver) |
| **JS render** | Playwright orqali SPA, AJAX, infinite scroll |
| **Anti-bot** | Cloudflare aniqlash va aylanib o'tish |
| **Crawler** | BFS/DFS, sitemap.xml, robots.txt, depth/domain cheklovi |
| **Ekstraktor** | Matn, linklar, media, fayllar, meta, JSON-LD, OpenGraph, microdata, jadvallar |
| **Filtrlash** | CSS selector, XPath, Regex |
| **AI moduli** | Sahifa turini aniqlash, klassifikatsiya, kalit iboralar, qisqacha mazmun, dublikat aniqlash |
| **Eksport** | CSV, XLSX, JSON, SQLite, PostgreSQL |
| **Baza** | SQLAlchemy ORM (SQLite default), SQL Injection'dan himoyalangan |
| **Proxy** | HTTP/HTTPS/SOCKS5, rotatsiya, health-check, dead proxy'ni o'chirish |
| **User-Agent** | Chrome/Firefox/Edge/Safari avtomatik aylantirish |
| **Scheduler** | once / hourly / daily / cron |
| **Plugin tizimi** | `plugins/` ga fayl tashlansa avtomatik yuklanadi |
| **Performance** | Async (aiohttp) — minglab URL, multi-threading |
| **Xavfsizlik** | Shifrlangan config (Fernet), input validatsiya, parametrlashtirilgan SQL |
| **Loglar** | INFO/WARNING/ERROR/DEBUG, fayl rotatsiyasi, GUI real-time |

---

## 📁 Loyiha strukturasi

```
scraper_platform/
├── gui/            # PyQt6 interfeys (dashboard, task, scheduler, results, logs)
├── scraper/        # engine, fetcher, crawler, async_engine, task_runner
├── parsers/        # extractor (barcha ma'lumot turlari)
├── exporters/      # CSV / XLSX / JSON / SQLite / PostgreSQL
├── database/       # SQLAlchemy modellar va DB menejer
├── scheduler/      # APScheduler asosidagi rejalashtiruvchi
├── browser/        # Playwright / undetected-chromedriver renderer
├── proxy/          # proxy menejer + user-agent menejer
├── ai/             # kontent tahlili va dublikat aniqlash
├── plugins/        # kengaytmalar (avtomatik yuklanadi)
├── config/         # sozlamalar + shifrlangan maxfiy do'kon
├── logs/           # logger + log fayllar
├── data/           # baza va eksport natijalari (avtomatik)
├── requirements.txt
└── main.py         # kirish nuqtasi (GUI + CLI)
```

---

## 🚀 O'rnatish

### 1. Talablar
- Python **3.10+** (3.13 da sinovdan o'tgan)

### 2. Virtual muhit yaratish (tavsiya etiladi)
```bash
python -m venv venv
# Windows:
venv\Scripts\activate
# Linux/macOS:
source venv/bin/activate
```

### 3. Bog'liqliklarni o'rnatish
```bash
pip install -r requirements.txt
```

### 4. Playwright brauzerlarini o'rnatish (JS saytlar uchun)
```bash
playwright install chromium
```

> **Eslatma:** Platforma modulli. Agar Playwright yoki cloudscraper
> o'rnatilmagan bo'lsa ham, statik saytlar uchun to'liq ishlaydi —
> tegishli modullar "lazy" yuklanadi.

---

## 💻 Foydalanish

### GUI rejimi (standart)
```bash
python main.py
```
Ochilgan oynada:
- **Dashboard** — umumiy statistika va oxirgi sessiyalar
- **Yangi vazifa** — URL, dvigatel, eksport, CSS selektorlar, crawl/scroll
- **Rejalashtirish** — once/hourly/daily/cron vazifalar
- **Natijalar** — qidirish, ko'rish, eksport
- **Loglar** — real-time loglar

### CLI rejimi
```bash
# Bitta sahifa (avtomatik aniqlash + JSON eksport)
python main.py --cli https://example.com --export json

# Saytni aylanib chiqish (crawl) + CSV
python main.py --cli https://example.com --crawl --export csv

# Aniq dvigatel bilan
python main.py --cli https://spa-site.com --engine playwright --scroll

# Proxy'larni tekshirish
python main.py --check-proxies
```

---

## 🔧 Konfiguratsiya

Sozlamalar `config/config.json` faylida saqlanadi (birinchi ishga
tushishda avtomatik yaratiladi). Namuna: `config/config.example.json`.

Asosiy parametrlar:
- `scraper.default_engine`: `auto` | `requests` | `playwright` | `cloudscraper`
- `scraper.concurrency`: async so'rovlar soni (default 50)
- `crawler.max_depth` / `max_pages`: crawl cheklovlari
- `database.engine`: `sqlite` | `postgresql`
- `proxy.enabled`: proxy'ni yoqish

**Maxfiy ma'lumotlar** (PostgreSQL paroli va h.k.) `config/.secrets.enc`
faylida **shifrlangan** holda saqlanadi (Fernet/AES).

---

## 🧩 Plugin yozish

`plugins/` papkasiga yangi `.py` fayl tashlang. Namuna:
`plugins/example_plugin.py`.

```python
from plugins.plugin_manager import BasePlugin
from parsers.extractor import Extractor

class MyPlugin(BasePlugin):
    name = "my_parser"

    def matches(self, url, html):
        return "example.com" in url

    def parse(self, url, html):
        ext = Extractor(html, url)
        return [{"sarlavha": ext.get_title()}]
```
Dastur qayta ishga tushganda plugin avtomatik yuklanadi.

---

## 🔌 Proxy sozlash

`proxy/proxies.txt` fayliga har qatorda bitta proxy qo'shing:
```
http://user:pass@1.2.3.4:8080
socks5://1.2.3.4:1080
```
So'ng `config.json` da `proxy.enabled = true` qiling.

---

## 🗄️ Ma'lumotlar bazasi sxemasi

| Jadval | Tavsif |
|--------|--------|
| `sessions` | Har bir scraping sessiyasi (URL, holat, statistika) |
| `pages` | So'ralgan har bir sahifa (status kod, vaqt, xato) |
| `items` | Ajratib olingan ma'lumot yozuvlari (JSON + dublikat hash) |
| `scheduled_jobs` | Rejalashtirilgan vazifalar |

SQLite default; PostgreSQL ham qo'llab-quvvatlanadi.

---

## ⚡ Unumdorlik

- **Async** (`scraper/async_engine.py`): `AsyncScraper().scrape_many(urls)`
  — bir vaqtda minglab statik URL.
- **Threading**: GUI vazifalari alohida `QThread` da ishlaydi.
- Retry (`tenacity`): timeout, connection, DNS, 429, 5xx.

---

## 🛡️ Xavfsizlik

- SQL Injection'dan himoya: barcha so'rovlar SQLAlchemy ORM orqali
  parametrlashtirilgan.
- Input validatsiya: URL va JSON selektorlar tekshiriladi.
- Shifrlangan config: `cryptography.Fernet`.
- `robots.txt` ga rioya (o'chirib qo'yish mumkin).

---

## 📜 Litsenziya va mas'uliyat

Ushbu platforma **ta'lim va qonuniy** maqsadlarda ishlatilishi uchun
mo'ljallangan. Saytlarni scrape qilishda ularning `robots.txt`,
foydalanish shartlari va mahalliy qonunlarga rioya qiling. Muallif
noqonuniy foydalanish uchun javobgar emas.

---

## 🧪 Sinovdan o'tkazilgan

- ✅ Statik HTML ekstraksiya (books.toscrape.com)
- ✅ Crawl (BFS) + CSS selektorlar
- ✅ CSV / JSON / XLSX eksport
- ✅ AI sahifa turini aniqlash (e-commerce)
- ✅ Plugin avtomatik yuklash
- ✅ SQLite saqlash + dublikat aniqlash
