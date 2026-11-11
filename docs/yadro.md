# Yadro (`srv1_core`)

## Ishga tushirish

```powershell
$env:SRV1_DATA_DIR = "$PWD\.srv1-data"   # ishlab chiqishda; berilmasa %PROGRAMDATA%\SRV_1
uv run python -m srv1_core
```

Birinchi ishga tushishda ma'lumotlar papkasida yaratiladi:

| Fayl | Vazifa |
|------|--------|
| `config.toml` | sozlamalar (izohli standart nusxa) |
| `auth.token` | Bearer token; ACL faqat joriy foydalanuvchi, SYSTEM, Administrators |
| `srv1.db` | SQLite (WAL): `schema_version`, `audit_log` |
| `logs/srv1.log` | JSON qatorlar, aylanuvchi (5 MB × 3) |
| `projects/`, `plugins/` | keyingi bosqichlar uchun |

## Sozlamalar

Ustuvorlik: `SRV1_*` muhit o'zgaruvchilari > `config.toml` > standart qiymat.
Ichki kalit ikki pastki chiziq bilan: `SRV1_SERVER__PORT=8711`.

| Kalit | Standart | Izoh |
|-------|----------|------|
| `server.host` | `127.0.0.1` | loopback bo'lmasa ishga tushmaydi |
| `server.port` | `8710` | |
| `server.allow_non_loopback` | `false` | tashqi manzilga faqat shu `true` bo'lsa |
| `logging.level` | `INFO` | `DEBUG`/`INFO`/`WARNING`/`ERROR` |
| `logging.max_bytes`, `logging.backup_count` | 5 000 000, 3 | log aylanishi |
| `events.queue_size` | 256 | har obunachi navbati |
| `events.stats_interval_s` | 5.0 | `system.stats` oralig'i |
| `plugins.load_builtin` | `true` | repozitoriydagi `plugins/` ni yuklash |
| `plugins.dirs` | `[]` | qo'shimcha plagin papkalari |

Bo'lim ichidagi noma'lum kalit — xato (imlo xatosi jim o'tmaydi).

## API

Hamma so'rovda `Authorization: Bearer <token>` (faqat `/health` tokensiz).
`Host` sarlavhasi `127.0.0.1`, `localhost`, `[::1]` yoki `server.host` bo'lishi shart
(DNS rebinding'ga qarshi), aks holda 400.

| Yo'l | Auth | Javob |
|------|------|-------|
| `GET /api/v1/health` | yo'q | `{status, version, uptime_s}` |
| `GET /api/v1/system` | token | `{ts, cpu, memory, disks[], process}` |
| `GET /api/v1/system/processes` | token | yadro va bola plaginlar xotirasi, 350 MB chegarasi |
| `GET /api/v1/logs?tail=N` | token | oxirgi log yozuvlari (1–500, INFO va yuqori) |
| `WS /ws/events?topics=a.*,b` | token (sarlavhada) | hodisalar oqimi |
| `/api/v1/plugins...` | token | [plaginlar.md](plaginlar.md) |

`/system`: `disks` faqat qattiq disklar (tarmoq/olinadigan disklar so'rovni osib
qo'ymasligi uchun); `process` — yadro jarayonining `rss`, `private`, `threads`.

`/docs`, `/redoc`, `/openapi.json` yopiq.

## Hodisalar

- `EventBus.publish(topic, data)` — sinxron, hech qachon bloklamaydi.
- Naqshlar `fnmatch` uslubida: `system.*`, `audit`, `*`.
- Sekin obunachi: navbat to'lsa eng eski hodisa tashlanadi; WebSocket klientga
  `{"topic": "bus.dropped", "data": {"count": N}}` xabari boradi.
- WebSocket xabari: `{"topic", "data", "ts", "seq"}`.
- `topics` parametri: ko'pi bilan 16 naqsh, belgilar `[a-z0-9_.*-]`.
- Token so'rov parametrida (`?token=`) **qabul qilinmaydi** — loglarga tushmasligi uchun.
- Rad etilgan ulanish: HTTP 403 (handshake bosqichida).

Hozirgi mavzular:

| Mavzu | Qachon |
|-------|--------|
| `system.stats` | har `stats_interval_s` da, faqat obunachi bo'lsa |
| `audit` | har audit yozuvida |
| `log` | har log yozuvida (INFO va yuqori) |
| `plugins.state` | plagin holati o'zgarganda |
| `plugin.<nom>.*` | plaginlar nashr qiladi |

`publish` faqat event loop oqimidan chaqiriladi. Boshqa oqimdan nashr
(`paho-mqtt` uchun) 6-bosqichda qo'shiladi.

## Audit

`AuditLogger.record(action, target, actor=, ok=, detail=)` — bazaga
(`audit_log`), log fayliga va `audit` mavzusiga yozadi. Vaqt har doim UTC,
naive `datetime` rad etiladi. Hozircha yagona yozuv: `auth.token_created`.

## Yo'l xavfsizligi

`paths.safe_join(base, *parts)` — plaginlar fayl yo'lini faqat shu orqali
yig'adi. Rad etadi: `..` bilan chiqish, mutlaq yo'l, disk harfi (`C:foo`),
NTFS oqimi (`a.txt:s`), qurilma nomlari (`NUL`, `COM1`, `nul.txt`), nuqta yoki
bo'shliq bilan tugaydigan nom, NUL bayt.

## Event loop

`__main__` uvicorn'ni `asyncio.run(..., loop_factory=asyncio.ProactorEventLoop)`
bilan ishga tushiradi; lifespan boshida loop turi tekshiriladi va Proactor
bo'lmasa yadro ishga tushmaydi.

## Baza sxemasi

`Base.metadata.create_all` + `schema_version` jadvali (hozir v2). Faqat yangi
jadval qo'shadigan versiyalar o'zi yangilanadi. Versiya mos
kelmasa yadro `SchemaMismatchError` bilan to'xtaydi. Migratsiya vositasi yo'q —
sxema birinchi marta o'zgarganda hal qilinadi.
