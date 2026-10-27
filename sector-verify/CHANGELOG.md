# O'zgarishlar tarixi

Format: [Keep a Changelog](https://keepachangelog.com/), versiyalash: SemVer (tag `sector-verify/vX.Y.Z`).

## [Unreleased]
### O'zgardi
- targetSdk va compileSdk 36 (Google Play talabi), AGP 8.10.1; instrumental testlar API 34 va 36 emulyatorlarida (ADR-017).

### Qo'shildi
- CI'da imzolangan reliz: `sector-verify/v*` tag → tekshirilgan APK/AAB va draft GitHub Release (ADR-019).

## [1.0.0-rc1] — 2026-10-26
### Qo'shildi
- RF reja CSV importi (validatsiya, o'zbekcha/ruscha/inglizcha xatolar, qator raqami bilan).
- Oldindan tekshiruv, foreground service bilan o'lchov (GPS 1 Hz, CellInfo 1 Hz + API 31+ listener), jonli tahlil (5 s).
- Tahlil algoritmi 1.0.0: tozalash, binlash, diagramma moslash (A), bootstrap CI, centroid (B), qamrov, almashinuv (permutatsiya),
  sabab (CELL_CONFIG_SWAP, BAND_PORT_SWAP, ANTENNA_ROTATED, PCI_MISSING, PCI_UNEXPECTED, LOW_COVERAGE), verdikt.
- Natija ekrani (polar diagrammalar, tavsiyalar), imzolangan `report.json` (EC P-256), PDF hisobot (uz/ru/en), sessiya ZIP.
- Sozlamalar: presetlar, qo'lda chegaralar, config JSON import, trafik URL, ilova va hisobot tili, dark/light/quyosh mavzulari.
- `sv-replay` CLI: `analyze`, `calibrate`, `verify`, `simulate`.
- Xavfsizlik: SQLCipher (Keystore bilan o'ralgan kalit), backup taqiqi, faqat HTTPS, FileProvider, lokal crash log.
