# Plaginlar

Namuna: [`plugins/hello/`](../plugins/hello/__init__.py) — yangi plagin uchun shundan nusxa oling.

## Tuzilma

```
<plaginlar papkasi>/<nom>/
  plugin.toml     # manifest
  __init__.py     # @hookimpl funksiyalar
  ...             # ichki modullar (nisbiy import ishlaydi)
```

Plaginlar uch joydan qidiriladi; bir xil nomda birinchi topilgani ustun:

1. `builtin` — repozitoriydagi `plugins/` (`plugins.load_builtin = true` bo'lsa)
2. `extra` — `config.toml` dagi `plugins.dirs`
3. `user` — `<ma'lumotlar>/plugins/`

`plugin.toml` yo'q papka e'tiborga olinmaydi. Plaginning ish papkasi har doim
`<ma'lumotlar>/plugins/<nom>/data/`.

## Manifest (`plugin.toml`)

```toml
name = "hello"                 # papka nomi bilan bir xil; [a-z][a-z0-9_]{1,31}
version = "0.1.0"
description = "..."
mode = "inprocess"             # yoki "subprocess"
heavy = false                  # true bo'lsa: standart o'chiq, faqat subprocess
memory_limit_mb = 256          # faqat subprocess; 64..4096

[permissions]
paths = ["C:/data/in"]         # mutlaq papkalar
ports = [9000, "9010-9019"]
serial = ["COM3"]
spawn = false                  # jarayon ishga tushirish (ctx.spawn)
projects = false               # umumiy <ma'lumotlar>/projects papkasi
```

Noma'lum kalit — xato. Yaroqsiz manifest yadroni to'xtatmaydi: plagin ro'yxatda
`invalid` holatida va xato matni bilan ko'rinadi.

## Hook'lar

Hammasi ixtiyoriy; `ctx` — `PluginContext`.

| Hook | Qaytaradi | Izoh |
|------|-----------|------|
| `srv1_start(ctx)` | — | yoqilganda; `async def` bo'lishi mumkin |
| `srv1_stop(ctx)` | — | o'chirilganda yoki yadro to'xtaganda |
| `srv1_router(ctx)` | `APIRouter` | `/api/v1/plugins/<nom>/api/...` ostida |
| `srv1_subscriptions(ctx)` | `[EventHandler]` | to'liq mavzu naqshi + `async` ishlovchi |
| `srv1_jobs(ctx)` | `[Job]` | `interval_s` yoki `cron` (5 maydon, mahalliy vaqt) |
| `srv1_panel(ctx)` | `PanelSpec` | shell shu tavsif bo'yicha chizadi |

## `PluginContext`

| A'zo | Vazifa |
|------|--------|
| `ctx.data_path(*parts)` | o'z ish papkasi ichidagi yo'l |
| `ctx.resolve_path(path)` | yo'lni tekshiradi: faqat o'z papkasi va `permissions.paths` |
| `ctx.check_port(n)`, `ctx.check_serial("COM3")` | manifestda bo'lmasa `PermissionDenied` |
| `ctx.projects_dir` | umumiy loyihalar papkasi (`permissions.projects`) |
| `await ctx.spawn(args, cwd=, env=, memory_limit_mb=, on_line=)` | jarayonni `shell`siz, Job Object ichida ishga tushiradi; auditga yozadi (`permissions.spawn`) |
| `ctx.publish(topic, data)` | `plugin.<nom>.<topic>` ga nashr; boshqa mavzuga yoza olmaydi |
| `await ctx.audit(action, target, ok=, detail=)` | audit jurnali, `actor = plugin:<nom>` |
| `ctx.log(level, event, **fields)` | yadro jurnaliga |

Router ichida `PermissionDenied` ushlanmasa, klientga 403 qaytadi va jurnalga
`permission_denied` yoziladi.

### Ruxsatlar nimani kafolatlaydi, nimani yo'q

Tekshiruv **`PluginContext` ichida**. Plagin kodi `open()` yoki `socket` ni
to'g'ridan-to'g'ri chaqirsa, uni hech narsa to'xtatmaydi — `inprocess` rejimida
ham, `subprocess` rejimida ham. Ya'ni ruxsatlar halol plaginni xatodan
saqlaydi, yovuz plaginni emas. `subprocess` rejimi beradigan narsa: RAM limiti
va qulashdan izolyatsiya (plagin yiqilsa yadro ishlayveradi). Ishonchsiz
manbadan plagin o'rnatmang.

## Rejimlar

| | `inprocess` | `subprocess` |
|---|---|---|
| Qayerda ishlaydi | yadro jarayonida | `python -m srv1_sdk.host` bola jarayonida |
| RAM (o'lchangan, `hello`) | yadroga +3,4 MB | alohida 43,3 MB |
| RAM limiti | yo'q | Job Object, `memory_limit_mb` |
| Plagin yiqilsa | xato logga tushadi; event loop'ni band qilsa yadro qotadi | yadro ishlayveradi, holat `crashed` |
| Yadro o'lsa | — | bola ham o'ladi (Job Object) |
| API | to'liq FastAPI router | xuddi shu router; oqimli javob yo'q |

**Qaysi rejimni tanlash.** Har bola jarayon ≈ 45–50 MB turadi (Python +
FastAPI), shuning uchun standart tanlov — `inprocess`. `subprocess` faqat
talab bo'yicha yoqiladigan og'ir (`heavy`) plaginlar uchun. `inprocess`
plagin bloklovchi ishni `asyncio.to_thread` ga chiqarishi shart; tashqi
dasturlarni esa `ctx.spawn` bilan alohida jarayonda ishlatadi (`hosting`
shunday qiladi).

Plagin kodi ikkala rejimda bir xil: `hello` ni `mode = "subprocess"` ga
o'zgartirish kifoya (testda tekshirilgan).

### Subprocess cheklovlari

- So'rov tanasi ≤ 1 MiB (413), javob ≤ 8 MiB (502), javob kutish 30 s (504).
- Plaginga faqat `content-type` va `accept` sarlavhalari uzatiladi; token uzatilmaydi.
- Limitdan oshgan xotira ajratish `MemoryError` beradi; host uni ushlab, 70 kodi
  bilan chiqadi va plagin `crashed` («xotira limiti oshdi») bo'ladi.
- Yiqilgan plagin o'zi qayta ishga tushmaydi — `enable` ni qayta chaqirish kerak.
- Protokol: stdin/stdout orqali JSON qatorlar (`srv1_sdk/protocol.py`).
  Plaginning `print()` chiqishi stderr'ga yo'naltiriladi va yadro jurnaliga
  `plugin_stderr` bo'lib tushadi.

## API

Hammasi token talab qiladi.

| Yo'l | Javob |
|------|-------|
| `GET /api/v1/plugins` | plaginlar ro'yxati |
| `GET /api/v1/plugins/{nom}` | bitta plagin |
| `POST /api/v1/plugins/{nom}/enable` | yoqadi (holat bazada saqlanadi) |
| `POST /api/v1/plugins/{nom}/disable` | o'chiradi |
| `GET /api/v1/plugins/{nom}/panel` | panel tavsifi |
| `* /api/v1/plugins/{nom}/api/...` | plaginning o'z API'si |

Xatolar: noma'lum plagin — 404; ishlamayotgan plagin API'si yoki paneli, yaroqsiz
manifestni yoqish — 409.

Holatlar: `stopped`, `running`, `error` (ishga tushmadi), `crashed`
(ishlab turib yiqildi), `invalid` (manifest yaroqsiz).

Hodisa: har holat o'zgarishida `plugins.state` — `{name, status, error}`.

Audit: `plugin.enable`, `plugin.disable`, `plugin.crashed`, `process.spawn`
(har bola jarayon uchun).

## Panel tavsifi

`PanelSpec = {title, widgets[]}`; vidjet turlari (`srv1_sdk/panel.py`):

| `type` | Maydonlar |
|--------|-----------|
| `label` | `text` |
| `value` | `label`, `source`, `field`, `refresh_s` |
| `button` | `label`, `method`, `path`, `confirm` |
| `form` | `label`, `method`, `path`, `fields[]` (`name`, `label`, `kind`, `choices`, `required`), `confirm` — xavfli amal: shell yuborishdan oldin tasdiq so'raydi |
| `table` | `label`, `source`, `columns[]`, `refresh_s`, `auto_refresh`, `filters[]`, `row_actions[]` |
| `chart` | `label`, `topic`, `field`, `window` |
| `log` | `label`, `source`, `refresh_s`, `filters[]` — `source` satrlar ro'yxatini qaytaradi |
| `query` | `label`, `path`, `field`, `placeholder` — ko'p qatorli matn `POST {field: matn}` bo'lib ketadi; javob `{columns[], rows[][], truncated, seconds}` |

Jadval kengaytmalari:

- `columns[].format`: `text` (standart), `size` (baytlar → `1,2 MB`),
  `datetime` (Unix vaqti → mahalliy sana-vaqt).
- `filters[]`: maydonlar jadval ustida chiqadi va `source` ga so'rov parametri
  bo'lib yuboriladi (qidiruv jadvali).
- `row_actions[]`: `{label, method, path, params[], confirm}` — tanlangan
  qatordan `params` dagi kalitlar olinib, JSON tana bo'lib yuboriladi.

Ko'rinadigan har matn (`title`, `text`, `label`) ikki xil berilishi mumkin: oddiy
satr (hamma tilda bir xil) yoki `{"uz": ..., "ru": ..., "en": ...}`. Shell joriy
tilni tanlaydi; u yo'q bo'lsa `en`, so'ng `uz`. Boshqa til kaliti — xato.
Manifestdagi `description` hozircha bir tilli.

`source`/`path` — plaginning o'z API'siga nisbatan (`/stats`); tashqi URL rad
etiladi. `topic` — `plugin.<nom>.` dan keyingi qism.
