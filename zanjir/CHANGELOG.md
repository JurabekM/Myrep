# CHANGELOG

Format: [Keep a Changelog](https://keepachangelog.com/), versiyalash: [SemVer](https://semver.org/).

## [Unreleased]

### Qo'shildi
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
