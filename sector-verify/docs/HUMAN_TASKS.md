# Inson vazifalari

## H1 — real telefonlarda sinov (2-bosqichdan keyin) — KUTILMOQDA

**Maqsad:** AC-05 (3 chipset oilasida ≥ 0.5 Hz barqaror yig'ish) va qurilmalar ro'yxati (`docs/DEVICES.md`).

> **To'liq dala ko'rsatmasi (joriy UI bo'yicha):** [`docs/H1_DEVICE_TEST.md`](H1_DEVICE_TEST.md) — sinov holatlari T1–T5,
> yozuv jadvali `devices.csv`, muammolar va baholash. Quyidagi qisqa ro'yxat — umumiy ko'rinish.
Bu vaqtda men 3-bosqichni (UI, hisobot) davom ettiraman.

### Kerakli qurilmalar
Kamida 3 ta Android 10+ (API 29+) telefon, har biri boshqa chipset oilasidan:
1. **Qualcomm Snapdragon** (masalan, Samsung Galaxy S/A seriyasining Snapdragon versiyasi, Xiaomi, OnePlus),
2. **Samsung Exynos** (masalan, Galaxy A5x/S2x Exynos versiyasi),
3. **MediaTek** (masalan, Xiaomi Redmi Note, Tecno, Infinix, Realme).
Har birida reja operatoriga tegishli faol SIM (MCC/MNC rejadagidek, masalan `43405`) bo'lsin.

### 1. Debug APK yig'ish
```
cd sector-verify
.\gradlew.bat :app:assembleDebug
```
Natija: `app\build\outputs\apk\debug\app-debug.apk`. Telefonga o'rnating (`adb install -r app-debug.apk` yoki faylni ko'chirib).

### 2. Har bir telefonda
1. Ilovani oching → **Ruxsatlarni so'rash** → joylashuv (aniq), telefon holati, bildirishnomalar — barchasiga ruxsat bering.
2. GPS'ni yoqing, telefonni ochiq osmon ostida 1–2 daqiqa ushlang.
3. **Qurilma probe (60 s)** — 60 soniya kuting; ekranda chastota (Hz), qo'shni RSRP, TA chiqadi. Skrinshot oling.
4. **Reja CSV import** — sinov saytining reja faylini tanlang (namuna: `docs/samples/plan-example.csv`; ustunlar §5.3).
5. Saytga boring (baza stansiyasidan 150–400 m). **Boshlash: <sayt kodi>** ni bosing.
6. Sayt atrofida **10–15 daqiqa** piyoda aylaning (iloji boricha to'liq halqa). Ekran o'chiq bo'lsa ham yig'ish davom etadi (bildirishnomada namunalar soni).
7. **Tugatish** → **ZIP eksport** → ZIP'ni o'zingizga yuboring (Telegram, e-pochta, USB).

### 3. Qaytarish
- ZIP fayllarni **`sector-verify/field-data/h1/`** papkasiga qo'ying (fayl nomi: `<sayt>_<qurilma>.zip`, masalan `NAV-0123_galaxy-a54.zip`).
- Har bir telefon uchun `field-data/h1/devices.txt` ga bir qator: model, chipset, Android versiyasi, operator, izoh
  (masalan: ekran o'chganda yig'ish to'xtadimi, ilova yopilib qoldimi).
- Probe skrinshotlari ham shu papkaga.

> Eslatma: ZIP ichida joylashuv izi bor. `field-data/**/*.zip` gitignore qilingan — ularni commit qilmang.

### Men ZIP'lar kelgach nima qilaman
ZIP'larni `:tools:replay` bilan tahlil qilaman, haqiqiy chastota va maydonlarni tekshiraman, `docs/DEVICES.md`
(qo'llab-quvvatlanadigan qurilmalar) ni yarataman va kerak bo'lsa yig'ishni tuzataman.

---

## H2 — 20 saytlik pilot (4-bosqichdan keyin) — KUTILMOQDA

**Maqsad:** AC-08 (pilotda tasdiqlangan almashinuvlarni aniqlash — 100%), AC-09 (bitta sessiya ≤ 25 daqiqa),
AC-06 (30 daqiqada batareya ≤ 15%), standart configni haqiqiy ma'lumot bilan kalibrlash.

> **To'liq dala ko'rsatmasi:** [`docs/H2_PILOT_GUIDE.md`](H2_PILOT_GUIDE.md) — rollar (ko'r sinov), sayt tanlash va presetlar,
> ground truth va azimut o'lchash, har saytdagi qadamlar, `log.csv`, qaytarish va baholash. Quyidagi ro'yxat — umumiy ko'rinish.
Bu vaqtda men 5-bosqichni (release, xavfsizlik, hujjatlar) davom ettiraman.

### 1. Saytlarni tanlash (20 ta)
- **Aralash muhit:** ~8 ta shahar (zich bino, rMax 600 m preset), ~6 ta shahar atrofi, ~6 ta qishloq.
- **Turli konfiguratsiya:** 3 va undan ko'p sektorli; kamida 5 ta saytda 2–3 band (ARFCN).
- **Ataylab "xato" reja — kamida 3 sayt:** RF reja CSV'sida ikkita sektorning PCI yoki azimutini almashtiring
  (masalan, S1 ↔ S2 qatorlaridagi `pci` qiymatlarini almashtirish). Bu sinov "almashinuv"ni haqiqiy saytda tekshiradi.
  Qaysi saytda nima o'zgartirilganini **faqat ground truth faylga** yozing — muhandis bilmasin (ko'r sinov).
- Imkon bo'lsa, haqiqatan almashinuv/burilish topilgan (tuzatishdan oldingi) saytlar — eng qimmatli ma'lumot.

### 2. Ground truth olish
Har bir rejadagi cell uchun bitta qator, fayl: **`field-data/pilot/ground_truth.csv`**
```
site_code,rat,arfcn,pci,true_azimuth_deg,has_fault,fault_type
NAV-0123,LTE,1300,141,0,0,NONE
NAV-0123,LTE,1300,142,240,1,CELL_CONFIG_SWAP
```
- `true_azimuth_deg` — haqiqiy azimut: antenna oldida **kompas/azimut o'lchagich** (yoki dron foto) bilan o'lchanadi,
  magnit og'ishi tuzatilgan (geografik shimol). Noma'lum bo'lsa bo'sh qoldiring.
- `has_fault` — 1/0. `fault_type`: `NONE`, `CELL_CONFIG_SWAP` (barcha bandlarda almashgan), `BAND_PORT_SWAP`
  (bitta bandda), `SWAP` (turi noma'lum), `ANTENNA_ROTATED`, `PCI_MISSING`.
- Ataylab buzilgan rejada: haqiqiy holat to'g'ri bo'lsa ham, ilova uchun bu almashinuv — `has_fault=1`, `fault_type=CELL_CONFIG_SWAP`.

### 3. Har bir saytda
1. Release-kandidat yoki debug APK, **Sozlamalar → Qurilma probe** (bir marta har telefon uchun).
2. Sayt kartasi → **Oldindan tekshiruv** → hammasi yashil/sariq bo'lsa **Boshlash**.
3. Halqa bo'ylab yuring, **"Natija tayyor"** chiqqach **Tugatish**. Boshlash va tugatish vaqtini yozib boring (AC-09).
4. **Hisobot (PDF, ZIP)** → **ZIP eksport** → ZIP'ni oling.
5. Kamida 2 ta saytda: sessiya boshida va 30 daqiqadan keyin batareya % ni yozing (AC-06, `docs/BATTERY_TEST.md`).

### 4. Qaytarish
- Barcha ZIP'lar → **`field-data/pilot/`** (nomi: `<sayt>_<sana>.zip`).
- `field-data/pilot/ground_truth.csv` (yuqoridagi format).
- `field-data/pilot/log.csv`: `site_code,start_time,end_time,battery_start,battery_end,device,notes`.

### Men ma'lumot kelgach nima qilaman
```
sv-replay calibrate field-data/pilot field-data/pilot/ground_truth.csv --out field-data/pilot/calibration
```
Natija: `recommended-config.json` va `calibration-report.md`. Agar shart (noto'g'ri FAIL ≤ 3%) bajarilsa — standart
`AnalysisConfig` ni yangilayman (ADR bilan), AC-08/AC-09 hisobotini `docs/PILOT_REPORT.md` ga yozaman.
Tavsiya etilgan configni ilovaga **Sozlamalar → Config JSON import** orqali ham yuklash mumkin.
