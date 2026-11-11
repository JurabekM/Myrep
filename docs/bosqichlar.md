# Bosqichlar holati

| # | Bosqich | Holat | Sana |
|---|---------|-------|------|
| 0 | Skelet | ✅ tugadi | 2026-11-11 |
| 1 | Yadro | ✅ tugadi | 2026-11-11 |
| 2 | SDK va plagin yuklovchi | ✅ tugadi | 2026-11-11 |
| 3 | Shell | ⏳ reja tasdiqlanishi kutilmoqda | — |
| 4 | `files` | — | — |
| 5 | `hosting` | — | — |
| 6 | `iot` | — | — |
| 7 | `data` | — | — |
| 8 | `electronics` | — | — |
| 9 | `itops` | — | — |
| 10 | Yakun | — | — |

## 0-bosqich — Skelet

**Qilindi**

- Bitta `uv` loyihasi (`srv1`, Python 3.12), uch paket: `srv1_core`, `srv1_sdk`,
  `srv1_shell` (hozircha faqat `__init__.py` va `__version__`).
- `ruff` (E/W/F/I/UP/B/S/ASYNC/ANN/SIM/PTH/RUF), `pyright` (strict),
  `pytest` + `pytest-asyncio` (`asyncio_mode = "auto"`) sozlamalari.
- `tests/test_skeleton.py` — 13 test: import, versiya mosligi, Python 3.12,
  papka tuzilmasi, taqiqlangan bog'liqliklar qo'riqchisi.
- `CLAUDE.md` (loyiha prompti), `docs/`, `tools/README.md`, `.gitignore`.

**Tekshiruv natijasi (2026-11-11)**

- `uv run pytest` — 13 passed
- `uv run ruff check .` va `ruff format --check .` — toza
- `uv run pyright` — 0 xato

**O'lchangan RAM** (Working Set, `Get-Process`, bir marta o'lchangan)

| Jarayon | WS, MB | Private, MB |
|---------|--------|-------------|
| `python.exe` (3.12, uch paket import qilingan, bo'sh turibdi) | 10,0 | 6,0 |
| `python.exe` (venv ishga tushirgichi) | 4,0 | 0,8 |

Bu faqat bo'sh interpretator bazasi: yadro, Caddy va shell hali yo'q, shuning
uchun 350 MB chegarasiga nisbatan hech narsa isbotlanmagan. Chegara birinchi
marta 1-bosqichda (yadro), to'liq holda 5-bosqichda (Caddy bilan) o'lchanadi.

**Qilinmadi / ma'lum kamchiliklar**

- Stekdagi ish vaqti kutubxonalari (FastAPI, PyQt6, DuckDB va h.k.) hali
  o'rnatilmagan — har biri o'z bosqichida qo'shiladi.
- `git init` bajarilmadi: papka allaqachon git repozitoriy (worktree) edi.
- CI yo'q (so'ralmagan).
- `tools/` bo'sh: binarlar 5, 6, 8, 10-bosqichlarda kerak bo'ladi.

## 1-bosqich — Yadro

Tafsilot: [yadro.md](yadro.md).

**Qilindi**

- `paths` (ma'lumotlar papkasi, `safe_join`), `settings` (TOML + muhit),
  `log_setup` (structlog JSON), `db` (SQLite WAL, `audit_log`, `schema_version`),
  `auth` (token + `icacls` ACL), `events` (pub/sub), `audit`, `system` (psutil).
- API: `GET /api/v1/health`, `GET /api/v1/system`, `WS /ws/events`.
- `python -m srv1_core` — uvicorn, 1 worker, Proactor loop.
- Rozilik bilan qo'shilgan, ro'yxatda bo'lmagan kutubxonalar: `websockets`
  (uvicorn WebSocket uchun), `types-psutil` (faqat dev).

**Tekshiruv natijasi (2026-11-11)**

- `uv run pytest` — 101 passed (8,8 s). Shundan 5 tasi alohida jarayondagi
  haqiqiy `python -m srv1_core` ga, 17 tasi test jarayoni ichidagi haqiqiy
  uvicorn'ga HTTP/WebSocket orqali ulanadi.
- `uv run ruff check .`, `ruff format --check .` — toza; `uv run pyright` — 0 xato.

**O'lchangan RAM** (`Get-Process`, bitta yugurish, obunachisiz bo'sh holat)

| Vaqt | Jarayon | Working Set, MB | Private, MB |
|------|---------|-----------------|-------------|
| 5 s | yadro `python.exe` | 74,8 | 62,8 |
| 65 s | yadro `python.exe` | 77,9 | 64,5 |
| 65 s | venv ishga tushirgichi `python.exe` | 3,9 | 0,8 |

Jami 65 s da: 81,8 MB Working Set. 350 MB chegarasining 23 %. Reja oldidan
aytilgan «80 MB dan kam» mo'ljali ishga tushirgich bilan birga 1,8 MB ga
oshdi. Yuk ostida va uzoq muddatda (soatlab) o'lchanmagan.

**Qilinmadi / ma'lum kamchiliklar**

- Toza to'xtatish (Ctrl+C, xizmat signali) sinalmagan: testlar jarayonni
  `kill` qiladi. WAL tufayli baza buzilmaydi, lekin `core_stopped` log yozuvi
  va lifespan tozalashi haqiqiy jarayonda tekshirilmagan.
- Ishlab chiqishda standart papka hamon `%PROGRAMDATA%\SRV_1`; repo ichida
  ishlash uchun `SRV1_DATA_DIR` ni qo'lda berish kerak.
- Tokenni almashtirish (rotatsiya) yo'q: faylni o'chirib, qayta ishga tushirish kerak.
- `icacls` muvaffaqiyatsiz bo'lsa yadro to'xtamaydi, faqat ogohlantiradi va
  auditga `ok=false` yozadi.
- `config.toml` dagi noma'lum *bo'lim* nomi (masalan `[servr]`) jim e'tiborsiz
  qoladi; bo'lim ichidagi noma'lum kalit esa xato beradi.
- So'rovlar jurnali (access log) o'chiq; so'rov tezligini cheklash yo'q.
- Log yozuvlari hodisalar shinasiga chiqmaydi — shell'ning «jonli jurnal»i
  uchun 3-bosqichda kerak bo'ladi.
- Bog'liqliklar orasida `opentelemetry-api` tranzitiv keladi (FastAPI
  orqali); RAM'ga ta'siri alohida o'lchanmagan.

## 2-bosqich — SDK va plagin yuklovchi

Tafsilot: [plaginlar.md](plaginlar.md).

**Qilindi**

- SDK (`srv1_sdk`): `manifest`, `hookspec` (pluggy), `context` (ruxsat
  tekshiruvi), `panel` (shell uchun sxema), `runtime` (yuklash), `asgi`
  (tarmoqsiz chaqirish), `protocol` + `host` (bola jarayon).
- Yadro (`srv1_core/plugins`): `registry` (topish, holat, yoqish/o'chirish,
  qulashni qayd etish), `runners` (jarayon ichida / bola jarayonda),
  `jobobject` (RAM limiti), `scheduler` (APScheduler).
- API: `/api/v1/plugins...` (ro'yxat, yoqish/o'chirish, panel, dispetcher).
- Baza sxemasi v2 (`plugin_state`); v1 baza ochilganda o'zi yangilanadi.
- Namuna plagin `plugins/hello` — ikkala rejimda bir xil kod bilan ishlaydi.
- Yangi kutubxonalar (ro'yxatdan): `pluggy`, `pywin32`, `apscheduler` 3.11.

**Tekshiruv natijasi (2026-11-11)**

- `uv run pytest` — 152 passed (≈29 s), uch marta ketma-ket barqaror.
- `uv run ruff check .`, `ruff format --check .` — toza; `uv run pyright` — 0 xato.

**O'lchangan RAM** (`Get-Process`, bitta yugurish, bo'sh holat, 68 s)

| Jarayon | Working Set, MB | Private, MB |
|---------|-----------------|-------------|
| yadro + `hello` (inprocess) + rejalashtiruvchi | 81,3 | 67,1 |
| `hello` nusxasi `subprocess` rejimida (bola) | 43,3 | 35,5 |
| venv ishga tushirgichi | 3,9 | 0,8 |

Yadro 1-bosqichga nisbatan +3,4 MB. Jami bola plagin bilan 128,5 MB, bolasiz
85,2 MB (350 MB chegarasining 37 % va 24 %). Yuk ostida o'lchanmagan.

**Rejadan chetlanish va topilmalar**

- venv'dagi `python.exe` ishga tushirgich ekan (haqiqiy Python — uning bolasi).
  Bola plagin endi asosiy interpretator bilan to'g'ridan-to'g'ri ishga
  tushiriladi (`__PYVENV_LAUNCHER__`), aks holda Job Object noto'g'ri jarayonga
  biriktirilardi.
- Reja oldidan «haqiqiy izolyatsiya faqat subprocess rejimida» deyilgan edi —
  bu noto'g'ri: subprocess faqat RAM limiti va qulashdan izolyatsiya beradi.
  Fayl/port ruxsatlari ikkala rejimda ham faqat `PluginContext` orqali ishlaydi.
- RAM limitidan oshgan plagin «o'ldirilmaydi», balki ajratish rad etiladi
  (`MemoryError`) va host o'zi chiqadi. Natija bir xil: holat `crashed`.

**Qilinmadi / ma'lum kamchiliklar**

- `cron` vazifalari ishga tushishi sinalmagan (faqat yaroqsiz ifoda rad
  etilishi va `interval_s` sinalgan).
- Bola jarayon ishga tushishi bilan Job Object'ga biriktirilishi orasida
  qisqa oraliq bor (limitsiz).
- Yiqilgan plagin avtomatik qayta ishga tushmaydi.
- `inprocess` plagin event loop'ni band qilsa, butun yadro qotadi; uni
  o'chirganda xotirasi bo'shashi kafolatlanmagan.
- Subprocess plagin API'sida oqimli javob va WebSocket yo'q.
- `builtin` plaginlar papkasi repozitoriy joylashuviga bog'liq; o'rnatilgan
  holat uchun 10-bosqichda hal qilinadi.
- `pywin32` va `apscheduler` tip ma'lumotisiz: ikkalasi bittadan faylga
  o'ralgan va o'sha fayllarda pyright qoidalari yumshatilgan.
- Haqiqiy jarayonda toza to'xtatish (Ctrl+C) hamon sinalmagan; uvicorn'ning
  jarayon ichidagi to'xtashi sinalgan (bola plaginlar to'xtaydi).
