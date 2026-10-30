# ZANJIR

Elektrolaboratoriyalar va elektriklar uchun **to'liq oflayn** mobil ilova (internet va server yo'q, ADR-0017): obyektning elektr grafi, dala o'lchovlari,
normaga avtomatik solishtirish, imzolangan PDF protokol va QR tekshiruv, ajratish rejasi tavsiyasi.

> ⚠️ Ilova faqat **tavsiya** beradi. Ishga ruxsat va xavfsizlik uchun javobgarlik naryad beruvchi va ish rahbari zimmasida.

| Papka | Mazmuni |
|---|---|
| `app/` | Flutter ilova (uz/ru) |
| `packages/zanjir_core/` | Sof Dart yadro: graf, baholash, solver, kanonik JSON, hash-zanjir |
| `packages/zanjir_data/` | Lokal baza (Drift), repozitoriylar, protokol imzolash, zaxira va fayl almashish |
| `packages/zanjir_protocol/` | Deterministik PDF protokol (QR bilan) |
| `norms/` | Normalar (YAML) va JSON Schema |
| `tools/` | Normalar tekshiruvi, kripto test vektorlari (mustaqil Python implementatsiyasi), bog'liqliklar auditi |
| `docs/` | Topshiriq, progress, ADR, xavfsizlik, release, pilot |

Buyruqlar va qoidalar — [`CLAUDE.md`](CLAUDE.md), holat — [`docs/PROGRESS.md`](docs/PROGRESS.md).
