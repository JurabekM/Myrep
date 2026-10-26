# CHANGELOG

Format: [Keep a Changelog](https://keepachangelog.com/), versiyalash: [SemVer](https://semver.org/).

## [Unreleased]

### Qo'shildi
- 5-faza — ilova UI (ADR-0009): oflayn laboratoriya profili, kirish ekrani (server 7-fazada), obyektlar, graf (daraxt/graf),
  tugun formasi va kartasi (QR `zanjir://app/n/<id>`, nusxalash), sessiya, tez o'lchov kiritish (rangli natija, avtomatik
  keyingi nuqta, qayta o'lchash), sessiya xulosasi va yopish, ajratish rejasi ko'rinishi, sozlamalar (til uz/ru, katta shrift,
  asboblar, normalar holati, LEAD uchun `k_corr`/zaxira); 255+ l10n kalit; Noto Sans; widget va asosiy oqim testlari,
  emulyator integration jobi.
- `EvalSettings.marginPct` — laboratoriya zaxirasi (effektiv = max); `zanjir_data` sxemasi v2 (`org_setting`, `local_pref`).
- 4-faza — `packages/zanjir_data` (ADR-0008): Drift sxemasi (13 jadval), append-only triggerlar, eksport qilingan sxema va
  migratsiya testlari, org bo'yicha filtrlangan repozitoriylar (obyekt, graf, asbob, sessiya, o'lchov + baholash + audit,
  normalar to'plami, protokol, ajratish rejasi holatlari va STALE), apparatni nusxalash (QF1 → QF2).
- 3-faza — kanonik JSON (RFC 8785), audit hash-zanjiri va Ed25519 imzo Dart va Python'da (ADR-0007):
  `tools/vectors/` umumiy vektorlari (RFC 8785 va RFC 8032 rasmiy natijalari bilan tekshirilgan generator, CI `--check`),
  zanjirni davom ettirish (anchor), 12 ta buzish holati, PDF/imzoning har bir bayti o'zgarishi aniqlanadi.
- 2-faza — ajratish solveri (`planIsolation`, ADR-0006): tugunlarni bo'lish + Edmonds–Karp, zonaga eng yaqin minimal kesim,
  mustaqil BFS tekshiruvi, 5 ta texnik tadbir tartibidagi qadamlar, ogohlantirishlar, `graph_snapshot_hash` va STALE;
  7 ta stsenariy, 1000 ta tasodifiy grafda brute force bilan property test, 2000 tugunli unumdorlik testi va benchmark.
- Kanonik JSON (RFC 8785) va SHA-256 — Dart qismi (Python va umumiy vektorlar — 3-fazada).
- Coverage darvozasi evaluator, solver va crypto uchun (100% qator va branch).
- 1-faza — `zanjir_core`:
  - domen modellari (enumlar, Site/Node/Edge/MeasurementSession/Measurement, UUIDv7);
  - o'zgarmas graf va BFS: yuqoridagi himoya apparati, UZO barcha ta'minot yo'llaridami, bog'langan komponent;
  - normalar modeli va qat'iy YAML yuklovchi (`NormSet.fromYaml`);
  - `evaluate()`: izolyatsiya, sirtmoq, UZO, yerga ulash, metallik bog'lanish (ADR-0005);
  - 147 ta golden holat (har normaga ≥ 3), evaluator uchun 100% qator va branch coverage darvozasi (`tool/check_coverage.dart`).
- `docs/NORMS_REVIEW.md` — muhandis tekshiruv varag'i (M1–M10 savollar, imzo bloki).
- 0-faza — monorepo skeleti (`app/`, `packages/zanjir_core/`, `server/`, `norms/`, `tools/`, `deploy/`, `docs/`),
  `docs/PROMPT.md`, `CLAUDE.md`, `docs/PROGRESS.md`, `docs/DECISIONS.md` (ADR-0001…0005).
- CI: `.github/workflows/zanjir.yml` — Dart analyze/test/coverage, Flutter analyze/test, ruff/mypy/pytest,
  normalar schema tekshiruvi, release darvozasi.

### O'zgardi
- `norms/v0.yaml`: izolyatsiya normasini tanlash uchun yagona `circuit_class` atributi; INS-SECONDARY faqat CABLE uchun.
