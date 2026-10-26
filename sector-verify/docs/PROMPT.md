# SECTOR VERIFY — Claude Code uchun bosh prompt (noldan production'gacha)

> **Inson uchun (Claude, bu blokni faqat ma'lumot sifatida o'qi):**
> 1. Android Studio'da bo'sh loyiha yarating: *Empty Activity*, Kotlin DSL, package `uz.sectorverify`, minSdk 29.
>    Papka: `C:\Users\comp_2.1\Downloads\claude_cowork\sector-verify`
> 2. Shu faylni loyihaga `docs/PROMPT.md` nomi bilan qo'ying.
> 3. Claude Code'ni shu papkada oching va yozing: **"docs/PROMPT.md ni to'liq o'qi va bajar."**
> 4. Keyingi har bir sessiyada: **"docs/PROMPT.md va PROGRESS.md ni o'qi, to'xtagan joydan davom et."**
> 5. Claude "INSON DARVOZASI" deb to'xtasa — u yozgan ko'rsatmani bajaring va natija fayllarini bering.

---

## 1. Rol va missiya

Sen tajribali Android/Kotlin muhandisi, RF/telekom algoritmlari mutaxassisi va release muhandisisan.
Vazifang — **Sector Verify** ilovasini noldan **production-ready** holatga yetkazish: imzolashga tayyor
release AAB, to'liq testlar, CI, hujjatlar va reliz checklist.

Ishni **avtonom** bajarasan, bosqichma-bosqich, har bir darvozada isbot (test natijasi) bilan.
To'xtaysan faqat ikki holatda: **INSON DARVOZASI**ga yetganda yoki haqiqatan bloklanganda.

## 2. Mahsulot (qisqacha)

Baza stansiyalarini montaj qiluvchi muhandislar uchun Android ilova. Oddiy telefon bilan — root,
diag port va vendor ruxsatisiz — muhandis sayt atrofida 150–400 m radiusda aylanadi. Ilova har bir
(ARFCN, PCI) qaysi yo'nalishda nurlanayotganini baholaydi va RF rejaga solishtiradi. Natijada
**sektor almashinuvi** (cross-feeder, CPRI yoki konfiguratsiya), yo'q PCI va antenna burilishini
brigada saytdan ketmasidan oldin topadi.

- **Aniqlaydi:** sektor almashinuvi (~120°), bitta band almashinuvi, yo'q PCI, 20–45° burilish (WARN).
- **Aniqlamaydi (qamrovdan tashqari):** tilt, MIMO branch almashinuvi, 5° dan aniq azimut, VSWR/PIM.
- **Maqsadli aniqlik:** azimut ±15–20°, almashinuvni aniqlash ≥ 95%.
- **To'liq offline.** Ma'lumot qurilmadan chiqmaydi. Telemetriya, analitika, Firebase yo'q.

## 3. Ish uslubi (MAJBURIY)

### 3.1 Holatni saqlash
- Loyiha ildizida **`PROGRESS.md`** yurit: joriy bosqich, bajarilgan vazifalar (✅), qolganlari,
  oxirgi test natijalari, ochiq savollar, kutilayotgan inson darvozasi.
- **`docs/DECISIONS.md`** — har bir muhim qaror qisqa ADR shaklida (kontekst → qaror → sabab).
  Ayniqsa shu promptdan chetga chiqsang, albatta yoz.
- **`CLAUDE.md`** — kelajakdagi sessiyalar uchun qisqa konventsiyalar: build buyruqlari, modullar,
  qoidalar. 0-bosqichda yarat va yangilab bor.
- Har sessiya boshida: `PROGRESS.md`, `CLAUDE.md`, `docs/DECISIONS.md` ni o'qi, keyin davom et.

### 3.2 Darvozalar
- Har bir bosqich oxirida **"Done" mezonlari** bor. Ular bajarilmaguncha keyingi bosqichga o'tma.
- Darvozada: `.\gradlew.bat check` (va bosqichga xos testlar) ishga tushiriladi. Natija `PROGRESS.md` ga
  yoziladi, git commit qilinadi va tag qo'yiladi: `phase-N-done`.

### 3.3 Inson darvozalari
- **H1** (2-bosqichdan keyin): real telefonlarda sinov. Kutish paytida 3-bosqichni davom ettirish mumkin.
- **H2** (4-bosqichdan keyin): 20 saytlik pilot. Kutish paytida 5-bosqichni davom ettirish mumkin.
- **H3** (6-bosqichdan keyin): release imzolash va tarqatish — faqat inson qiladi.

Inson darvozasiga yetganda `docs/HUMAN_TASKS.md` ga o'zbek tilida aniq ko'rsatma yoz: nima qilish
kerak, qaysi qurilmada, qaysi fayllarni qaytarish kerak va ularni qaysi papkaga qo'yish kerak. So'ng
menga qisqa xabar ber.

### 3.4 Halollik
- Test natijasini o'ylab topma. Testni o'tkazish uchun chegarani yumshatma yoki testni o'chirma.
- Mezon bajarilmasa, sababini tahlil qilib yoz, tuzatishga urin. Uddalay olmasang — menga ayt.
- Android API haqida ishonching komil bo'lmasa, rasmiy hujjatni tekshir. Hidden API, reflection, root ishlatma.

## 4. Texnik stek va arxitektura

- Kotlin 2.x, Gradle Kotlin DSL, version catalog (`gradle/libs.versions.toml`), JDK 17.
- minSdk 29, targetSdk 35, compileSdk 35. Package: `uz.sectorverify`.
- UI: Jetpack Compose (BOM), Material 3, Navigation Compose. DI: Hilt.
- Ma'lumot: Room + SQLCipher for Android, DataStore. Seriyalash: kotlinx.serialization.
- Asinxronlik: Coroutines/Flow.
- Test: JUnit 5, Kotest (property testlar), Turbine, Kover (qamrov), AndroidX Test (instrumental).
- Sifat: detekt + ktlint, Android Lint (`abortOnError = true`).
- PDF: `android.graphics.pdf.PdfDocument`. Grafiklar Compose `Canvas` va PDF `Canvas` da qo'lda chiziladi.
- Tarmoq: faqat trafik generatori (`HttpURLConnection`, qo'shimcha kutubxonasiz).

### 4.1 Modullar

| Modul | Turi | Mas'uliyat | Bog'liqlik |
|---|---|---|---|
| `:app` | Android app | Navigatsiya, Hilt, tema, Application | barcha feature |
| `:feature:plan` | Android lib | CSV import, validatsiya, saytlar ro'yxati, sayt kartasi | data, model |
| `:feature:survey` | Android lib | Oldindan tekshiruv, jonli ekran, servisni boshqarish | data, analysis, telephony, location |
| `:feature:report` | Android lib | Natija ekrani, PDF/JSON/CSV, imzo, sessiya eksporti | data, analysis |
| `:feature:settings` | Android lib | Chegaralar, trafik URL, til, config JSON import | data |
| `:core:telephony` | Android lib | CellCollector, CellNormalizer, DeviceCapabilityProbe, TrafficGenerator | model |
| `:core:location` | Android lib | GnssCollector (LocationManager GPS_PROVIDER, 1 Hz) | model |
| `:core:data` | Android lib | Room, DAO, repozitoriylar, DataStore, kalit boshqaruvi | model |
| `:core:analysis` | **sof Kotlin/JVM** | Geo, tozalash, binlash, fit, bootstrap, swap, verdikt, simulyator | faqat model |
| `:core:model` | **sof Kotlin/JVM** | Domen modellari | yo'q |
| `:tools:replay` | **JVM CLI** | Sessiyani qayta tahlil qilish, kalibrlash | analysis, model |

`:core:analysis` va `:core:model` da Android'ga bog'liqlik bo'lishi **taqiqlanadi**.

## 5. Domen modeli va ma'lumot sxemasi

### 5.1 Domen (`:core:model`)
`Rat { LTE, NR }`, `CellKey(rat, arfcn, pci)`,
`Sector(label, rat, band, arfcn, pci, azimuthDeg, hpbwDeg=65.0, mechTiltDeg?, elecTiltDeg?, heightM?)`,
`SitePlan(code, name, lat, lon, mccMnc, sectors)`,
`CellSample(tNanos, rat, arfcn, pci, registered, rsrp?, rsrq?, sinr?, ta?, ci?, tac?)`,
`GnssFix(tNanos, utcMs, lat, lon, accM, speedMps?, bearingDeg?)`,
`AzimuthEstimate(alphaDeg, ciLowDeg, ciHighDeg, ciHalfDeg, alphaBDeg, rmseDb, nSamples, nBins, unreliable)`,
`Verdict { PASS, WARN, FAIL, INCONCLUSIVE }`,
`CauseCode { NONE, BAND_PORT_SWAP, CELL_CONFIG_SWAP, ANTENNA_ROTATED, PCI_MISSING, PCI_UNEXPECTED, LOW_COVERAGE }`,
`SectorResult`, `Finding(type, severity {INFO, WARN, CRITICAL}, detail)`, `SessionResult`,
`AnalysisConfig` (barcha chegaralar, 6-bo'limga qarang).

### 5.2 Room jadvallari (`:core:data`)

| Jadval | Maydonlar |
|---|---|
| `site` | id PK, code UNIQUE, name, lat, lon, mcc_mnc, imported_at |
| `sector` | id PK, site_id FK, label, rat, band, arfcn, pci, azimuth_deg, hpbw_deg, mech_tilt_deg?, elec_tilt_deg?, height_m?; UNIQUE(site_id, rat, arfcn, pci) |
| `session` | id PK (UUID), site_id FK, mode (FULL/RECHECK), started_at, ended_at?, device_model, api_level, baseband?, app_version, algo_version, config_json, measured_rate_hz?, status (RUNNING/DONE/ABORTED) |
| `gnss_fix` | id PK, session_id FK, t_nanos, utc_ms, lat, lon, acc_m, speed_mps?, bearing_deg?; INDEX(session_id, t_nanos) |
| `cell_sample` | id PK, session_id FK, t_nanos, rat, arfcn, pci, registered, rsrp?, rsrq?, sinr?, ta?, ci?, tac?; INDEX(session_id, arfcn, pci) |
| `sector_result` | id PK, session_id FK, sector_id FK?, rat, arfcn, pci, azimuth_est, ci_low, ci_high, azimuth_b, error_deg?, n_samples, n_bins, rmse_db, verdict, cause_code |
| `finding` | id PK, session_id FK, type, severity, detail_json |
| `report` | id PK, session_id FK, pdf_path, json_path, zip_path, sha256, signature_b64, created_at |

- Xom jadvallar (`gnss_fix`, `cell_sample`) **hech qachon o'zgartirilmaydi**.
- `session.config_json` — tahlil paytidagi `AnalysisConfig` ning to'liq nusxasi (takrorlanuvchanlik uchun).
- Room migratsiyalari: `exportSchema = true`, sxemalar `core/data/schemas/` da, har bir versiya uchun migratsiya testi.

### 5.3 Reja import formati (CSV, UTF-8, sarlavha majburiy)

```
site_code,site_name,lat,lon,mcc_mnc,sector,rat,band,arfcn,pci,azimuth_deg,hpbw_deg,mech_tilt_deg,elec_tilt_deg,height_m
NAV-0123,Navoiy Markaz,40.1032,65.3685,43405,S1,LTE,B3,1300,141,0,65,2,4,30
```

Validatsiya: lat −90..90, lon −180..180; LTE PCI 0..503, NR PCI 0..1007; azimut 0..359.9;
HPBW 20..120 (bo'sh bo'lsa 65); bir saytda (rat, arfcn, pci) takrorlanmaydi; bir saytning barcha
qatorlarida koordinata bir xil. Xatolar qator raqami bilan o'zbek tilida ko'rsatiladi.
Ajratuvchi: vergul yoki nuqta-vergul (avtomatik aniqlanadi).

### 5.4 Sessiya eksporti (ZIP)
`plan.csv`, `cell_samples.csv`, `gnss_fixes.csv`, `session.json` (metadata + config), `report.json`,
`report.pdf`, `capabilities.json`. Shu ZIP `:tools:replay` ga to'g'ridan-to'g'ri kiradi.

### 5.5 `report.json` (schema `sector-verify/report/v1`)
`site{code, lat, lon}`, `session{id, mode, startedAt, endedAt, device, apiLevel, appVersion,
algoVersion, measuredRateHz, coveragePct}`, `sectors[{label, rat, arfcn, pci, planAzimuth,
estAzimuth, ci95[lo, hi], azimuthB, errorDeg, nSamples, nBins, rmseDb, verdict, cause}]`,
`findings[{type, severity, detail}]`, `config{…}`,
`integrity{sha256, signature, keyAlg: "EC-P256/SHA256withECDSA", attestationChain[]}`.

## 6. Algoritm spetsifikatsiyasi (`:core:analysis`)

Barcha raqamli parametrlar `AnalysisConfig` da, quyidagi qiymatlar — standart.
Tasodifiylik faqat `Random(seed)` orqali; seed natijaga yoziladi.

### 6.1 Tozalash
1. `rsrp == null` bo'lgan namunani tashla.
2. Namuna yoshi > `maxSampleAgeMs = 3000` bo'lsa tashla (CellInfo vaqt belgisi va yig'ish vaqti farqi).
3. GNSS pozitsiyasini vaqt bo'yicha chiziqli interpolyatsiya qil; eng yaqin fix > `maxFixGapMs = 2000` bo'lsa tashla.
4. `accM > 15` yoki `speedMps > 8` bo'lsa tashla.
5. Saytdan masofa `d` (haversine) va yo'nalish `phi` (great-circle initial bearing, 0..360) hisobla.
6. `rMin = 100 m ≤ d ≤ rMax = 1500 m` (preset "shahar": rMax = 600) bo'lmasa tashla.
7. TA filtri (LTE): `ta != null` va `|ta * 78.12 − d| > 2 * 78.12` bo'lsa — boshqa sayt, tashla.

### 6.2 Normallashtirish va binlash
- `y = rsrp + 10 * n * log10(d / dRef)`; `n = 3.5` (preset qishloq 3.0), `dRef = 300 m`.
- Har bir CellKey uchun `binDeg = 10` (36 bin). Bin qiymati — y ning **medianasi**, `n_b` — namunalar soni.
- `n_b < minPerBin = 3` bo'lsa bin hisobga olinmaydi.

### 6.3 Azimut — A usul (asosiy)
- Diagramma: `A(Δ) = −min(12 * (Δ/θ)², Am)`; `θ` — sektor HPBW, `Am = 30 dB`; Δ [-180, 180] ga keltiriladi.
- α = 0..359, qadam `1°`. Har α uchun `w_b = sqrt(n_b)`, `P0 = Σw(ȳ − A) / Σw`,
  `J(α) = Σ w (ȳ − P0 − A(φ_b − α))²`. `α̂ = argmin J`. `rmseDb = sqrt(J / Σw)`.
- Bin soni < `minBinsForFit = 6` bo'lsa baholama (INCONCLUSIVE).

### 6.4 Ishonch oralig'i
- Bootstrap: binlarni qaytarib tanlab `bootstrapIterations = 200` marta qayta moslash.
  **Monte-Karlo testlarida 50** (tezlik uchun, config orqali).
- Har iteratsiya natijasining α̂ ga nisbatan farqi δ ∈ [-180, 180]; 2.5 va 97.5 persentillar → `ciLow`, `ciHigh`.
- `ciHalfDeg = max(|lo|, |hi|)`.

### 6.5 Azimut — B usul (tekshiruv)
- `p_b = 10^(ȳ_b / 10)`, `α_B = atan2(Σ p sin φ_b, Σ p cos φ_b)`.
- `|α̂ − α_B| > unreliableDiffDeg = 30` → `unreliable = true`.

### 6.6 Qamrov
- **Umumiy:** 36 binning ≥ `minOverallCoverage = 0.70` qismida saytning istalgan rejadagi PCI bo'yicha ≥ 3 namuna.
- **Sektor:** `α_plan ± 90°` dagi 18 binning ≥ `minSectorCoverage = 0.60` qismida **shu ARFCN'dagi istalgan
  rejadagi PCI** bo'yicha ≥ 3 namuna. Aks holda shu sektor INCONCLUSIVE, cause `LOW_COVERAGE`,
  hamda UI yetishmayotgan yo'nalishlarni ko'rsatadi.

### 6.7 Almashinuvni aniqlash
- Har bir ARFCN bo'yicha alohida: bahosi bor sektorlar uchun barcha permutatsiyalar (≤ 6 sektor → ≤ 720).
- `cost(π) = Σ_k δ(α̂_k, α_plan[π(k)])²`.
- Almashinuv: `π* ≠ id`, π* ostida har bir `|δ| ≤ swapMaxErrDeg = 30` va
  `cost(id) ≥ swapMinGain = 4 * cost(π*) + 1`.
- Finding: `SWAP`, CRITICAL, `mapping {pci → haqiqatda nurlanayotgan sektor label}`.

### 6.8 Sabab klassifikatsiyasi (bir sektor label'i bo'yicha barcha ARFCN'larni solishtirish)
- Faqat bitta ARFCN'da almashgan, qolganlari PASS → `BAND_PORT_SWAP`.
- Barcha ARFCN'larda bir xil almashgan → `CELL_CONFIG_SWAP`.
- Barcha ARFCN'larda bir xil ishorali 20–45° siljish, o'zaro farq ≤ 10° → `ANTENNA_ROTATED`.
- Rejadagi PCI'da `< minSamplesPresent = 20` namuna, umumiy qamrov yetarli → `PCI_MISSING`.
- Rejada yo'q PCI, shu ARFCN'da, saytdan ≤ 300 m da namunalarning ≥ 30% ida `registered = true` →
  `PCI_UNEXPECTED`, **severity INFO** (verdiktga ta'sir qilmaydi; qo'shni saytlar bo'lishi mumkin).

### 6.9 Verdikt
| Verdikt | Shart |
|---|---|
| PASS | `|δ| ≤ 20`, `ciHalfDeg ≤ 20`, qamrov OK, almashinuv yo'q, `unreliable = false` |
| WARN | `20 < |δ| ≤ 45` yoki `20 < ciHalfDeg ≤ 35` |
| FAIL | `|δ| > 45` yoki almashinuv yoki `PCI_MISSING` |
| INCONCLUSIVE | qamrov yetarli emas, yoki `ciHalfDeg > 35`, yoki `unreliable`, yoki bin < 6 |

Ustuvorlik: INCONCLUSIVE > FAIL > WARN > PASS (qamrov yo'q bo'lsa FAIL berilmaydi).

### 6.10 Jonli rejim
Har `liveIntervalMs = 5000` da oxirgi holat bo'yicha B usul va bootstrap'siz A usul bajariladi.
Yakuniy tahlil sessiya oxirida to'liq bajariladi.

### 6.11 Simulyator (`:core:analysis`, paket `uz.sectorverify.analysis.sim`)
- Sayt + 3–6 sektor, 1–3 ARFCN.
- Marshrut: halqa (radius 150–400 m) + Gauss shovqini σ = 15 m, yoki shovqinli to'rtburchak.
  Qamrov 50–100% (yoylar kesib tashlanadi). Tezlik 1.4 m/s (piyoda) yoki 5 m/s, namuna 1 Hz.
- RSRP: `−80 dBm (300 m da) − 10 n log10(d/300) + A(φ − α_true) + S + F`.
  - S — log-normal soya, σ = 6–8 dB, Gudmundson AR(1): `ρ = exp(−Δd / 50 m)`.
  - F — Rayleigh: 4 ta eksponensial (o'rtacha 1) yig'indisining o'rtachasi, 10log10.
- GNSS shovqini: σ = 4 m. Ehtimollik `pNeighbor` (0..1) bilan qo'shnilar ko'rinadi (idle rejimni modellash);
  serving — eng kuchli PCI, histerezis 3 dB.
- Xato ssenariylari: yo'q, to'liq almashinuv (2 yoki 3 sektor aylanmasi), bitta band almashinuvi,
  20–45° burilish, o'chiq sektor, PCI qayta ishlatuvchi qo'shni sayt.
- To'liq deterministik (seed).

## 7. Android yig'ish (`:core:telephony`, `:core:location`, servis)

- **Ruxsatlar:** `ACCESS_FINE_LOCATION`, `ACCESS_COARSE_LOCATION`, `READ_PHONE_STATE`,
  `FOREGROUND_SERVICE`, `FOREGROUND_SERVICE_LOCATION`, `POST_NOTIFICATIONS`, `WAKE_LOCK`, `INTERNET`.
  `ACCESS_BACKGROUND_LOCATION` — **kerak emas**.
- **CellCollector:** `TelephonyManager.createForSubscriptionId(subId).requestCellInfoUpdate()` har 1000 ms;
  API 31+ da qo'shimcha `TelephonyCallback.CellInfoListener`. Ikki oqim takrorlar olib tashlangan holda birlashtiriladi.
- **CellNormalizer:** `CellInfo.UNAVAILABLE` → null; diapazonlar: LTE RSRP −140..−44, RSRQ −34..3,
  NR SS-RSRP −156..−31; noto'g'ri PCI → null (namuna tashlanadi). Vaqt: `getTimestampMillis()` (API 30+),
  aks holda `getTimeStamp()`.
- **GnssCollector:** `LocationManager.GPS_PROVIDER`, 1000 ms, 0 m. Play Services ishlatilmaydi.
- **SurveyForegroundService:** `foregroundServiceType="location"`, partial WakeLock, doimiy bildirishnoma
  (namunalar soni, qamrov %). Ikkala oqim 1 soniyalik bufer bilan bitta Room tranzaksiyasida yoziladi.
  Jarayon o'ldirilsa, keyingi ishga tushishda RUNNING sessiya topilib davom ettirish taklif qilinadi.
- **TrafficGenerator:** har 2000 ms da sozlamalardagi URL'ga HEAD so'rov (UE ulangan rejimda qolishi va TA
  kelishi uchun). URL bo'sh bo'lsa o'chiq va oldindan tekshiruvda ogohlantirish. Faqat HTTPS
  (`networkSecurityConfig`: cleartext taqiqlangan). Hech qanday foydalanuvchi ma'lumoti yuborilmaydi.
- **DeviceCapabilityProbe:** 60 soniya o'lchaydi: haqiqiy chastota, qo'shnilar keladimi, ularda RSRP bormi,
  TA bormi, NR SA maydonlari bormi. Natija → DataStore va `capabilities.json`.
- **Dual-SIM:** rejadagi MCC/MNC ga mos subscription avtomatik tanlanadi; mos SIM bo'lmasa sessiya boshlanmaydi.

## 8. UI va hisobot

- Til: o'zbek (lotin, standart), rus, ingliz — barcha satrlar `strings.xml` da, qattiq kodlangan matn yo'q.
- Dala sharoiti: tugma ≥ 56 dp, yuqori kontrastli "quyosh" rejimi, katta shrift masshtabini qo'llab-quvvatlash,
  barcha ikonlarda `contentDescription`.
- **Xarita qarori:** bulk tile yuklab olish OSM tile siyosatiga zid. Shuning uchun MVP'da asosiy xarita
  qatlami **yo'q**. Canvas'da sayt, halqa, iz (rang = serving PCI), shimol strelkasi va masshtab chiziladi.
  Foydalanuvchi bergan MBTiles faylini import qilish — v1.1. Buni `DECISIONS.md` ga yoz.

### 8.1 Ekranlar
1. **Saytlar** — ro'yxat, qidiruv, oxirgi verdikt, CSV import tugmasi.
2. **Sayt kartasi** — reja jadvali va rejadagi azimutlar polar diagrammasi.
3. **Oldindan tekshiruv** — ruxsatlar, operator/SIM, tarmoq rejimi, GPS aniqligi, qurilma imkoniyatlari,
   rejadagi PCI'lardan ko'rinayotganlari, trafik URL holati. Muammo bo'lsa "Boshlash" o'chiq va sababi yoziladi.
4. **Jonli o'lchov** — xarita canvas'i, 36 binli qamrov radari, har bir PCI uchun karta (RSRP, taxminiy va
   rejadagi azimut, holat rangi), "Natija tayyor" bildirishnomasi, "Tugatish" tugmasi.
5. **Natija** — har bir ARFCN uchun polar diagramma: reja — shtrix chiziq, o'lchov — 95% yoy bilan.
   Verdikt jadvali, topilmalar va tavsiya etilgan harakat (o'zbekcha), "Qayta tekshiruv" tugmasi.
6. **Hisobot** — PDF ko'rish, ulashish (share sheet), ZIP eksporti.
7. **Sozlamalar** — tahlil preset (shahar/shahar atrofi/qishloq), qo'lda chegaralar, trafik URL,
   ilova tili, hisobot tili, config JSON import (kalibrlash natijasi).

### 8.2 PDF hisobot
Sarlavha (sayt, sana, muhandis ismi — sozlamalardan, qurilma, versiyalar), umumiy verdikt, sektorlar jadvali,
har bir ARFCN uchun polar diagramma, marshrut va qamrov, topilmalar va tavsiyalar, ilova (config, chastota,
SHA-256, imzo). Hisobot tili ilova tilidan mustaqil (uz/ru/en).

### 8.3 Imzo
O'rnatishga bitta Keystore EC P-256 kaliti (StrongBox bo'lsa StrongBox). Kalit yaratilayotganda
attestation challenge = install UUID. `report.json` ning kanonik shakli (kalitlar tartiblangan,
`integrity` maydonisiz) → SHA-256 → `SHA256withECDSA` imzo. Attestation zanjiri `report.json` ga yoziladi.
`:tools:replay` da `verify` buyrug'i imzoni tekshiradi.

## 9. Bosqichlar

### 0-bosqich — Skelet va infratuzilma
- Muhitni tekshir: `java -version` (17+), `$env:ANDROID_HOME`, `adb version`, `git --version`.
  Biror narsa yo'q bo'lsa — `HUMAN_TASKS.md` ga o'rnatish ko'rsatmasini yoz va to'xta.
- `gradlew.bat` bo'lmasa: `gradle` o'rnatilgan bo'lsa `gradle wrapper`, aks holda to'xta (inson Android Studio'da yaratadi).
- 4.1 dagi barcha modullar, version catalog, detekt, ktlint, Kover, Lint sozlamalari.
- `.gitignore` (`keystore.properties`, `*.jks`, `local.properties`, `build/`).
- `.github/workflows/ci.yml`: JDK 17, `./gradlew check`, Kover hisoboti, artefakt sifatida test hisobotlari.
  Remote'ni o'zing yaratma va push qilma — faqat fayl.
- `CLAUDE.md`, `PROGRESS.md`, `docs/DECISIONS.md`, `README.md` (o'zbekcha).
- **Done:** `.\gradlew.bat check` yashil, git'da commit, tag `phase-0-done`.

### 1-bosqich — Model, algoritm, simulyator
- `:core:model` — 5.1. `:core:analysis` — 6-bo'lim to'liq, simulyator — 6.11.
- Testlar:
  - Geo: ma'lum koordinatalar uchun yo'nalish va masofa (±0.1°, ±1 m).
  - Har bir Verdikt va har bir CauseCode uchun kamida bitta deterministik ssenariy testi.
  - Property testlar: α̂ ning burchakni aylantirishga invariantligi (barcha azimutlar +θ → α̂ + θ).
  - Monte-Karlo: CI'da 200 iteratsiya; `@Tag("slow")` bilan 1000 iteratsiya.
    Natijalar jadvali `build/reports/montecarlo.md` ga va qisqasi `PROGRESS.md` ga yoziladi.
- **Done (G1):** AC-01…AC-04 bajarilgan, `:core:analysis` uchun Kover qator qamrovi ≥ 90%, tag `phase-1-done`.
  AC bajarilmasa — algoritmni tahlil qil, `DECISIONS.md` ga yoz, tuzat. 2-bosqichga **o'tma**.

### 2-bosqich — Android yig'ish va ma'lumot
- `:core:telephony`, `:core:location`, `:core:data` (Room + SQLCipher; kalit 5.2 va 11-bo'lim bo'yicha),
  SurveyForegroundService, TrafficGenerator, DeviceCapabilityProbe.
- Vaqtinchalik debug ekran: chastota, namunalar soni, ko'rinayotgan PCI'lar, "ZIP eksport".
- Testlar: Normalizer unit testlari (soxta CellInfo builderlar bilan), Room DAO va migratsiya instrumental
  testlari, sessiyani tiklash testi (AC-07).
- **Done:** instrumental testlar emulyatorda yoki ulangan qurilmada yashil (`adb devices` bo'yicha);
  qurilma yo'q bo'lsa unit testlar yashil va instrumental testlar H1 ga qoldiriladi. Tag `phase-2-done`.
- **→ INSON DARVOZASI H1:** kamida 3 xil chipsetli telefonda (Qualcomm, Exynos, MediaTek) debug APK bilan:
  probe + saytda 10–15 daqiqalik sessiya. ZIP'larni `field-data/h1/` ga qo'yish. Kutish paytida 3-bosqichga o't.
  ZIP'lar kelgach: tahlil qil, `docs/DEVICES.md` (qo'llab-quvvatlanadigan qurilmalar) yarat, kerak bo'lsa tuzat.

### 3-bosqich — UI, jonli tahlil, hisobot
- 8-bo'lim to'liq: 7 ekran, jonli tahlil, PDF, `report.json`, ZIP, imzo, 3 til.
- Debug ekranni faqat `debug` build'da qoldir.
- Testlar: ViewModel testlari (Turbine), Compose UI testlari (import → sessiya → natija oqimi soxta
  repozitoriy bilan), PDF generatsiyasi testi (fayl yaratiladi, sahifalar soni > 0), imzo round-trip testi.
- **Done (G3):** `assembleDebug` + barcha testlar yashil, to'liq oqim soxta ma'lumot bilan ishlaydi, tag `phase-3-done`.

### 4-bosqich — Replay va kalibrlash vositasi
- `:tools:replay` CLI:
  - `analyze <session.zip> [--config cfg.json]` → konsolga va `report.json` ga;
  - `calibrate <dir-of-zips> <ground_truth.csv>` → chegaralar va `n` bo'yicha grid-search,
    maqsad: AC-08 ni maksimallashtirish, noto'g'ri FAIL ≤ 3%; natija `recommended-config.json`
    va `calibration-report.md`;
  - `verify <session.zip>` → imzo va xeshni tekshirish.
- `ground_truth.csv` formati: `site_code,rat,arfcn,pci,true_azimuth_deg,has_fault,fault_type`.
- Ilovada sozlamalar orqali config JSON import.
- **Done:** simulyator yaratgan ZIP'lar ustida `calibrate` ishlaydi va testlangan; tag `phase-4-done`.
- **→ INSON DARVOZASI H2:** 20 saytlik pilot. `HUMAN_TASKS.md` da: sayt tanlash mezonlari
  (shahar/qishloq aralash, kamida 2–3 saytda reja ataylab almashtirilgan), ground truth olish usuli,
  ZIP'larni `field-data/pilot/` ga qo'yish. Kutish paytida 5-bosqichga o't.
  Ma'lumot kelgach: `calibrate`, standart configni yangilash, AC-08/AC-09 hisoboti `docs/PILOT_REPORT.md`.

### 5-bosqich — Production'ga tayyorlash
- **Release build:** R8 minify + shrinkResources; Room, kotlinx.serialization, SQLCipher, Hilt uchun
  ProGuard qoidalari; release build emulyatorda smoke test.
- **Imzolash:** `keystore.properties` (gitignore) yoki env (`SV_KEYSTORE_PATH`, `SV_KEYSTORE_PASSWORD`,
  `SV_KEY_ALIAS`, `SV_KEY_PASSWORD`). Real keystore **yaratma va commit qilma**; yo'q bo'lsa release
  imzosiz yig'iladi va ogohlantiradi.
- **Versiyalash:** `versionName` git tag'dan, `versionCode` = commit soni; `CHANGELOG.md`.
- **Xavfsizlik:** `allowBackup=false` + `dataExtractionRules` (hamma narsa chiqarib tashlanadi);
  SQLCipher paroli — 32 tasodifiy bayt, Keystore AES-GCM kaliti bilan o'ralgan; cleartext taqiqlangan;
  eksport qilingan fayllar faqat `FileProvider` orqali; loglarda koordinata yoki IMSI yo'q.
- **Barqarorlik:** lokal crash log (UncaughtExceptionHandler → fayl, sozlamalardan eksport); ANR'siz:
  og'ir ishlar faqat `Dispatchers.Default/IO` da; StrictMode debug'da yoqilgan.
- **Ruxsatlar UX:** har bir ruxsat uchun izoh ekrani, rad etilganda tushunarli holat va sozlamalarga o'tish.
- **Ishlash:** jonli tahlil bitta yangilanishi < 300 ms (o'rta telefon), yakuniy tahlil < 10 s;
  batareya o'lchash tartibi `docs/BATTERY_TEST.md` da (AC-06 inson tomonidan tasdiqlanadi).
- **Google Play talablari (agar Play orqali tarqatilsa):** FGS location deklaratsiyasi va video tavsifi
  matni, Data safety javoblari (ma'lumot to'planmaydi va ulashilmaydi), maxfiylik siyosati
  (`docs/privacy/` uz/ru/en). APK orqali to'g'ridan-to'g'ri tarqatish yo'riqnomasi ham.
- **Hujjatlar:** `README.md` (uz), `docs/USER_GUIDE_uz.md`, `docs/USER_GUIDE_ru.md`, `docs/ARCHITECTURE.md`,
  `docs/ALGORITHM.md` (6-bo'lim + kalibrlash natijalari), `docs/RELEASE_CHECKLIST.md`.
- **Done:** `.\gradlew.bat clean check :app:bundleRelease :app:assembleRelease` yashil, Lint'da xato yo'q,
  detekt toza, CI yashil; tag `v1.0.0-rc1`.

### 6-bosqich — Yakuniy audit
- Butun kod bazasini ko'rib chiq: o'lik kod, TODO'lar, qattiq kodlangan matnlar, xavfsizlik (11-bo'lim), ruxsatlar.
- 10-bo'limdagi barcha AC'lar holati jadvali `docs/RELEASE_CHECKLIST.md` da (✅ / inson tasdig'i kutilmoqda).
- **→ INSON DARVOZASI H3:** imzolash, tarqatish, `v1.0.0` tag.

## 10. Qabul mezonlari

| ID | Mezon | Maqsad | Qayerda |
|---|---|---|---|
| AC-01 | Almashinuvni aniqlash, qamrov ≥ 70% | ≥ 95% | Simulyatsiya |
| AC-02 | Noto'g'ri FAIL (aslida xato yo'q) | ≤ 3% | Simulyatsiya |
| AC-03 | Azimut xatosi medianasi, qamrov ≥ 70% | ≤ 10° | Simulyatsiya |
| AC-04 | Qamrov yetarli emas → INCONCLUSIVE | 100% | Simulyatsiya |
| AC-05 | 3 chipset oilasida barqaror yig'ish | ≥ 0.5 Hz, 3/3 | H1 |
| AC-06 | 30 daqiqalik sessiyada batareya | ≤ 15% | H1/H2 |
| AC-07 | Majburiy to'xtatishda yo'qolgan ma'lumot | ≤ 2 s | Instrumental test |
| AC-08 | Pilotda tasdiqlangan almashinuvlarni aniqlash | 100% | H2 |
| AC-09 | Bitta sessiyaning to'liq vaqti | ≤ 25 daqiqa | H2 |
| AC-10 | `:core:analysis` qator qamrovi | ≥ 90% | Kover |
| AC-11 | Release build, Lint, detekt, CI | Yashil | 5-bosqich |

## 11. Qat'iy qoidalar

- Chegaralarni kodga qattiq yozma — faqat `AnalysisConfig`.
- `:core:analysis` ga Android importi qo'shma.
- Root, hidden API, reflection, `READ_PRIVILEGED_PHONE_STATE` ishlatma.
- Tarmoqqa faqat TrafficGenerator chiqadi; boshqa hech qanday tarmoq so'rovi yo'q.
- Kalit, parol, keystore'ni commit qilma.
- Har bir tugallangan vazifa = alohida git commit (ingliz tilida, Conventional Commits).
- Testni o'tkazish uchun testni o'chirish yoki chegarani yumshatish **taqiqlanadi**. Chegarani o'zgartirish
  faqat kalibrlash ma'lumoti asosida va `DECISIONS.md` ga yozilgan holda.
- Kod va identifikatorlar — ingliz tilida. README, foydalanuvchi qo'llanmasi, `PROGRESS.md`,
  `HUMAN_TASKS.md` va menga hisobotlar — o'zbek tilida.
- Shu prompt va kod bazasidagi haqiqat zid kelsa yoki talab noaniq bo'lsa — `PROGRESS.md` ga ochiq savol
  yoz va oqilona standart bilan davom et. Faqat qaytarib bo'lmaydigan qarorda to'xta va so'ra.

## 12. Menga hisobot (har bosqich oxirida va har to'xtashda)

O'zbek tilida, qisqa:
1. Qaysi bosqich tugadi, qaysi tag qo'yildi.
2. Test va AC natijalari (raqamlar bilan).
3. `DECISIONS.md` ga qo'shilgan qarorlar (bir qatordan).
4. Ochiq savollar va xavflar.
5. Keyingi qadam yoki kutilayotgan inson darvozasi va undan nima kerakligi.

**Boshla: 0-bosqichdan.** Avval `PROGRESS.md` mavjudligini tekshir — mavjud bo'lsa, to'xtagan joydan davom et.
