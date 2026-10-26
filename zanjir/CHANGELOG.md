# CHANGELOG

Format: [Keep a Changelog](https://keepachangelog.com/), versiyalash: [SemVer](https://semver.org/).

## [Unreleased]

### Qo'shildi
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
