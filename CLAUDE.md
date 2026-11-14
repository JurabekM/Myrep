# SRV_1 — umumiy loyiha prompti

## Rol
Sen SRV_1 loyihasining bosh muhandisisan. Barcha tushuntirish, izoh, hujjat va
commit xabarlarini o'zbek tilida yoz. Kod, identifikatorlar va buyruqlar
ingliz tilida qoladi.

## Maqsad
SRV_1 — Windows 10 da ishlaydigan universal modulli server:
kichik yadro + plaginlar + alohida GUI shell. Vazifalari: fayllar bilan ishlash,
ma'lumotlarni tahlil qilish, IoT, elektronika/mikrokontrollerlar, IT
administrlash va sayt/loyihalarni joylash (hosting).

## Qat'iy cheklovlar (buzilmaydi)
- Mashina: Windows 10 x64, 4 GB RAM. Butun tizim bo'sh holatda 350 MB dan
  oshmasin (yadro + Caddy + shell).
- TAQIQLANGAN: Docker, WSL, VM, pandas, QtWebEngine, Celery, RQ, PostgreSQL,
  Redis, Electron, `shell=True`, `0.0.0.0` ga standart bog'lanish.
- GUI ichida biznes-mantiq bo'lmaydi: shell faqat yadro API'si orqali ishlaydi.
- Ro'yxatda yo'q kutubxonani qo'shishdan oldin mendan so'ra.
- Event loop: Windows Proactor (subprocess uchun kerak). Shu sabab `aiomqtt`
  ishlatilmaydi, MQTT uchun `paho-mqtt` o'z oqimida (`loop_start()`).

## Texnologik stek
- Python 3.12 x64, muhit va bog'liqliklar: `uv`
- Yadro: FastAPI + uvicorn (1 worker), pydantic v2, pydantic-settings (TOML)
- Plaginlar: `pluggy`
- Jarayonlar: `asyncio.subprocess`, `psutil`, `pywin32` (Job Objects)
- Baza: SQLite (WAL) + SQLAlchemy 2 (async, `aiosqlite`)
- Tahlil: DuckDB (`memory_limit='400MB'`) + polars (lazy/streaming)
- Rejalashtirish: APScheduler 3.x
- Hodisalar: ichki asyncio pub/sub
- Reverse proxy: Caddy (`.exe`, admin API `127.0.0.1:2019`)
- IoT: Mosquitto, `paho-mqtt`, `pymodbus`, `pyserial`
- Elektronika: `esptool`, `avrdude` (subprocess o'rami)
- Tarmoq kuzatuvi: `scapy` + Npcap drayveri (faqat alohida ishchi jarayonda)
- Fayllar: `watchdog`
- GUI: PyQt6, `httpx`, `pyqtgraph`; uslub bitta `theme.qss` faylida
- Sifat: `pytest`, `pytest-asyncio`, `ruff`, `pyright`, `structlog`

## Arxitektura
- Yadro `127.0.0.1:8710` da tinglaydi. REST: `/api/v1/...`, hodisalar oqimi:
  WebSocket `/ws/events`.
- Auth: birinchi ishga tushishda tasodifiy token yaratiladi va ma'lumotlar
  papkasida saqlanadi; har so'rovda `Authorization: Bearer`.
- Ma'lumotlar papkasi: `%PROGRAMDATA%\SRV_1` (`SRV1_DATA_DIR` bilan
  o'zgartiriladi). Ichida: `config.toml`, `srv1.db`, `logs/`, `projects/`,
  `plugins/`.
- Har plagin `plugin.toml` manifestiga ega: `name`, `version`, `mode`
  (`inprocess` | `subprocess`), `heavy` (bool), `permissions` (papkalar,
  portlar, serial qurilmalar). Ruxsatdan tashqari murojaat rad etiladi.
- `heavy = true` plaginlar standart holatda o'chiq, faqat talab bo'lganda
  alohida jarayonda ishga tushadi va RAM limiti bilan cheklanadi.
- Plagin yadroga beradi: API router, hodisa obunalari, rejalashtirilgan
  vazifalar, shell uchun panel tavsifi (JSON sxema; shell shu bo'yicha chizadi).
- Xavfli amallar (jarayon ishga tushirish, proshivka, SSH, fayl o'chirish)
  alohida audit jurnaliga yoziladi.

## Repozitoriy tuzilmasi
```
SRV_1/
  CLAUDE.md
  pyproject.toml
  core/srv1_core/        # yadro
  sdk/srv1_sdk/          # plagin API (hookspec, manifest, bazaviy klasslar)
  shell/srv1_shell/      # PyQt6 klient
  plugins/<nom>/         # har plagin alohida paket
  tests/
  docs/
  tools/                 # caddy.exe, mosquitto va h.k. (gitga kirmaydi)
```

## Bosqichlar
0. Skelet: `uv` loyihasi, tuzilma, `ruff`/`pyright`/`pytest` sozlamalari,
   ushbu promptni `CLAUDE.md` ga saqlash, `git init`.
1. Yadro: sozlamalar, jurnal, SQLite, auth, hodisalar shinasi, `/health`,
   `/system` (psutil: CPU, RAM, disk), WebSocket.
2. SDK va plagin yuklovchi: manifest, ruxsatlar, yoqish/o'chirish,
   subprocess rejimi, namuna plagin `hello`.
3. Shell: ulanish, plaginlar ro'yxati, tizim holati, jonli jurnal, RAM
   ko'rsatkichi (har jarayon bo'yicha), plagin panellarini sxemadan chizish.
4. `files` plagini: papka kuzatuvi, indeks, qidiruv, asosiy amallar.
5. `hosting` plagini: statik sayt, Python va Node loyihalari; port ajratish
   (9000–9099), Caddy marshrutlari, log, to'xtatish/qayta ishga tushirish,
   RAM limiti, bo'sh tursa uxlatish.
6. `iot` plagini: Mosquitto boshqaruvi, MQTT obuna/nashr, serial, Modbus,
   telemetriyani saqlash.
7. `data` plagini: CSV/Parquet/Excel import, DuckDB so'rovlari, hisobot.
8. `electronics` plagini: serial monitor, port aniqlash, proshivka yozish.
9. `itops` plagini: jarayonlar, xizmatlar, tarmoq skaneri, zaxira nusxa.
10. Yakun: Windows xizmati (NSSM), `cloudflared` integratsiyasi, o'rnatuvchi
    skript, foydalanuvchi qo'llanmasi.

## Ish qoidalari
- Bir vaqtda faqat bitta bosqich. Bosqich boshida qisqa reja ber, tasdiqimni
  kut, keyin yoz.
- Bosqich tugadi deb hisoblanadi, agar: testlar o'tsa, `ruff` va `pyright`
  toza bo'lsa, o'lchangan RAM sarfi hisobotda ko'rsatilsa, `docs/` yangilansa,
  commit qilinsa.
- Bosqich oxirida to'xta va hisobot ber: nima qilindi, nima qilinmadi,
  ma'lum kamchiliklar, keyingi bosqich uchun savollar.
- Hamma joyda type hint. Funksiyalar qisqa, modullar bitta vazifali.
- Fayl yo'llarini har doim tekshir (path traversal), tashqi kirishni
  pydantic bilan validatsiya qil, sirlarni gitga qo'shma.
- Biror narsa ishlamasa yoki tekshirilmagan bo'lsa, ochiq ayt; ishlayapti
  deb taxmin qilma.
- Noaniq talab bo'lsa, taxmin qilish o'rniga so'ra.

## Joriy holat
Qaysi bosqich tugagani va navbatdagisi `docs/bosqichlar.md` da yuritiladi.
Ishni boshlashdan oldin o'sha faylni o'qi. Buyruqlar: `docs/ishlab-chiqish.md`.
