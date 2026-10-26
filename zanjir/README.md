# ZANJIR

Elektrolaboratoriyalar va elektriklar uchun offline-first mobil ilova: obyektning elektr grafi, dala o'lchovlari,
normaga avtomatik solishtirish, imzolangan PDF protokol va QR tekshiruv, ajratish rejasi tavsiyasi.

> ⚠️ Ilova faqat **tavsiya** beradi. Ishga ruxsat va xavfsizlik uchun javobgarlik naryad beruvchi va ish rahbari zimmasida.

| Papka | Mazmuni |
|---|---|
| `app/` | Flutter ilova (uz/ru) |
| `packages/zanjir_core/` | Sof Dart yadro: graf, baholash, solver, kanonik JSON, hash-zanjir |
| `server/` | FastAPI server |
| `norms/` | Normalar (YAML) va JSON Schema |
| `tools/` | Normalar tekshiruvi, umumiy kripto test vektorlari |
| `deploy/` | Docker, compose, Caddy, zaxira skriptlari |
| `docs/` | Topshiriq, progress, ADR, xavfsizlik, deploy |

Buyruqlar va qoidalar — [`CLAUDE.md`](CLAUDE.md), holat — [`docs/PROGRESS.md`](docs/PROGRESS.md).
