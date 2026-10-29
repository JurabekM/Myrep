# Algoritm (`:core:analysis`, versiya 1.0.0)

Barcha raqamlar `AnalysisConfig` da; quyidagilar standart (prompt §6). Tasodifiylik faqat `Random(seed)`; seed natijaga yoziladi.
Talqinlar: `docs/DECISIONS.md` ADR-008; 1.0.0-rc1 dagi tuzatishlar — ADR-016.

**Takrorlanuvchanlik:** har sessiya o'z `AnalysisConfig` nusxasini (`session.config_json`) va RF reja nusxasini
(`session.plan_json`) saqlaydi. Yakuniy tahlil, hisobot, ZIP va `sv-replay analyze` shu nusxalar bilan ishlaydi — keyin
sozlamalar o'zgarsa yoki reja qayta import qilinsa ham natija bir xil qayta hosil bo'ladi.

| Preset | Farqi standartdan |
|---|---|
| `SUBURBAN` (standart) | — |
| `URBAN` | `rMaxM = 600` |
| `RURAL` | `n = 3.0` |

## 1. Tozalash (§6.1)
1. `rsrp == null` → tashlanadi.
2. Yosh `rxNanos − tNanos > 3000 ms` → tashlanadi.
3. GNSS fix'lar: `accM > 15` yoki `speed > 8 m/s` bo'lganlari olib tashlanadi. Namuna vaqti uchun joylashuv:
   - eng yaqin fix > 2000 ms (`maxFixGapMs`) uzoqda bo'lsa — namuna tashlanadi;
   - ikkala qo'shni fix ham ≤ 2000 ms ichida bo'lsa — ular orasida vaqt bo'yicha chiziqli interpolyatsiya;
   - qo'shnilardan biri > 2000 ms (GNSS uzilishi chetida) yoki faqat bitta tomonda fix bor bo'lsa — **interpolyatsiya qilinmaydi**,
     eng yaqin fix olinadi (uzilish ustidan "to'g'ri chiziq" chizilmaydi; jonli inkremental tozalash ham shu tufayli to'liq
     qayta hisoblash bilan aynan teng qoladi — ADR-015, ADR-016).
4. Saytdan masofa `d` (haversine) va yo'nalish `φ` (great-circle initial bearing).
5. `100 m ≤ d ≤ 1500 m` (shahar: 600 m).
6. LTE TA filtri: `|ta·78.12 − d| > 2·78.12` → boshqa sayt, tashlanadi.

## 2. Normallashtirish va binlash (§6.2)
`y = rsrp + 10·n·log10(d/300)`, `n = 3.5` (qishloq 3.0). Har cell uchun 36 ta 10° bin (markaz `(i+0.5)·10°`),
bin qiymati — `y` ning medianasi; `n_b < 3` bo'lsa bin hisobga olinmaydi.

## 3. Azimut, A usul (§6.3)
`A(Δ) = −min(12·(Δ/θ)², 30)`, θ — HPBW. α = 0…359° (1°) bo'yicha `w_b = √n_b`, `P0 = Σw(ȳ−A)/Σw`,
`J(α) = Σw(ȳ − P0 − A(φ_b − α))²`, `α̂ = argmin J`, `rmse = √(J/Σw)`. Bin < 6 bo'lsa baholanmaydi.

## 4. Ishonch oralig'i (§6.4)
Binlarni qaytarib tanlab 200 marta qayta moslash (Monte-Karlo testlarida 50). δ = α_i − α̂ ∈ [−180, 180),
2.5/97.5 persentillar (R type 7) → `ciLow`, `ciHigh`; `ciHalf = max(|lo|, |hi|)`.

## 5. B usul (§6.5)
`p_b = 10^(ȳ_b/10)`, `α_B = atan2(Σp·sin φ, Σp·cos φ)`. `|α̂ − α_B| > 30°` → `unreliable`.

## 6. Qamrov (§6.6)
- Umumiy: 36 binning ≥ 70% ida istalgan rejadagi PCI ≥ 3 namuna.
- Sektor: reja ± 90° dagi 18 binning ≥ 60% ida shu ARFCN'dagi rejadagi PCI ≥ 3 namuna; aks holda INCONCLUSIVE/LOW_COVERAGE va
  yetishmayotgan yo'nalishlar ko'rsatiladi. Almashgan sektor uchun oyna — u haqiqatda nurlanayotgan sektor rejasi atrofida.

## 7. Almashinuv (§6.7)
Har **(RAT, ARFCN)** bo'yicha baholangan sektorlar uchun barcha permutatsiyalar (≤ 6 → ≤ 720, Heap algoritmi); LTE va NR
bir xil raqamli ARFCN'ga ega bo'lsa ham aralashtirilmaydi. Almashinuv nishoni (haqiqiy sektor) ham shu (RAT, ARFCN) ichidan olinadi.
`cost(π) = Σδ(α̂_k, α_plan[π(k)])²`. Almashinuv: `π* ≠ id`, π* ostida har `|δ| ≤ 30°`, `cost(id) ≥ 4·cost(π*) + 1`.
Umumiy qamrov yetarli bo'lmasa qidirilmaydi. Topilma: `SWAP`, CRITICAL, `pci → haqiqiy sektor`.

## 8. Sabab (§6.8) va verdikt (§6.9)
| Sabab | Shart |
|---|---|
| CELL_CONFIG_SWAP | label'ning barcha ARFCN'larida bir xil almashgan (yoki yagona ARFCN) |
| BAND_PORT_SWAP | faqat bitta ARFCN'da almashgan, qolganlari PASS (aralash holat ham) |
| ANTENNA_ROTATED | barcha baholangan ARFCN'larda bir xil ishorali 20 < \|δ\| ≤ 45°, farq ≤ 10° |
| PCI_MISSING | rejadagi PCI < 20 namuna, umumiy qamrov yetarli → FAIL |
| PCI_UNEXPECTED | rejada yo'q PCI, ≤ 300 m da ≥ 20 namuna, ≥ 30% `registered` → INFO |

Verdikt ustuvorligi INCONCLUSIVE > FAIL > WARN > PASS; PASS: |δ| ≤ 20, ciHalf ≤ 20; WARN: 20 < |δ| ≤ 45 yoki 20 < ciHalf ≤ 35;
FAIL: |δ| > 45, almashinuv yoki PCI_MISSING; INCONCLUSIVE: qamrov, ciHalf > 35, unreliable, bin < 6.
Sayt: FAIL (biror FAIL yoki CRITICAL) > INCONCLUSIVE > WARN > PASS.

## 9. Jonli rejim (§6.10)
Har 5 s: B usul va bootstrap'siz A usul; inkremental tozalash (ADR-015) — eng og'ir holatda ~10 ms (JVM).

## 10. Simulyatsiya natijalari (Monte-Karlo)
| AC | 200 iter. | 1000 iter. | Maqsad |
|---|---|---|---|
| AC-01 almashinuvni aniqlash (qamrov ≥ 70%) | 99.0% | 98.1% | ≥ 95% |
| AC-02 noto'g'ri FAIL (xatosiz) | 0.0% | 0.0% | ≤ 3% |
| AC-03 azimut xatosi medianasi | 4.6° | 4.6° | ≤ 10° |
| AC-04 qamrov 30–60% → INCONCLUSIVE | 100% | 100% | 100% |

Simulyator: 3–6 sektor, 1–3 ARFCN, halqa/to'rtburchak 150–400 m, soya σ 6–8 dB (Gudmundson, 50 m), Rayleigh (4 RE), GNSS σ 4 m.
To'liq jadval: `docs/reports/montecarlo-*.md`.

## 11. Kalibrlash
`sv-replay calibrate <zip-papka> ground_truth.csv` — ADR-014, ADR-016.
- **Grid:** `n` ∈ {3.0, 3.5, 4.0} × PASS chegarasi {15, 20, 25}° × WARN {40, 45, 50}° × swap xatosi {25, 30, 35}° ×
  sektor qamrovi {0.5, 0.6} = 162 konfiguratsiya (`--quick` — kichikroq grid).
- **Har sessiya o'z yozilgan config'i bilan** baholanadi: griddan faqat shu parametrlar (va bootstrap soni) almashtiriladi,
  qolganlari (preset, `rMax`, …) sessiyaniki qoladi. Tavsiya eng ko'p ishlatilgan sessiya config'i ustiga quriladi.
- **Moslash:** ground truth bilan `site_code` + (RAT, ARFCN, PCI) bo'yicha; SWAP topilmasi ham RAT bo'yicha tekshiriladi.
- **Tanlash:** noto'g'ri FAIL ≤ 3% bo'lganlar orasida — AC-08 aniqlash eng yuqori, keyin noto'g'ri FAIL eng past, PASS ulushi
  eng yuqori, asos config'dan eng kam farq. Hech biri ≤ 3% bo'lmasa — ogohlantirish (chiqish kodi 1).
- Natija: `recommended-config.json` (ilovaga *Sozlamalar → Config JSON import*), `calibration-report.md`.

Simulyatsiyadagi namoyish: `docs/reports/calibration-sim-demo.md`.
**Pilot (H2) natijalari:** kutilmoqda — kelgach shu bo'limga va `docs/PILOT_REPORT.md` ga yoziladi; standart config faqat shundan keyin o'zgaradi.
