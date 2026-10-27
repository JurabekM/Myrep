# H2 — 20 saytlik pilot (dala ko'rsatmasi)

**Maqsad:** ilovani haqiqiy saytlarda sinash va standart chegaralarni haqiqiy ma'lumot bilan kalibrlash.

| Mezon | Talab | Qanday o'lchanadi |
|---|---|---|
| **AC-08** almashinuvni aniqlash | pilotda tasdiqlangan almashinuvlarning **100%** | ZIP'lar + `ground_truth.csv` → `sv-replay calibrate` |
| **AC-09** bitta sessiya vaqti | **≤ 25 daqiqa** | `log.csv` dagi `start_time` / `end_time` |
| **AC-06** batareya, 30 daqiqa | **≤ 15%** | `log.csv` dagi `battery_start` / `battery_end` (`docs/BATTERY_TEST.md`) |
| Kalibrlash sharti | noto'g'ri FAIL **≤ 3%** (sog'lom cell'lar orasida) | `calibrate` → `calibration-report.md` |

**Oldin:** H1 bajarilgan bo'lsin (`docs/H1_DEVICE_TEST.md`) — pilotni H1 da yaxshi natija bergan telefon(lar)da o'tkazing.
**Vaqt:** bitta sayt ~30–40 daqiqa (yo'l hisobga olinmagan); kuniga 5–8 sayt → 3–4 ish kuni.

---

## 1. Rollar

| Rol | Vazifa |
|---|---|
| **Koordinator** | saytlarni tanlaydi, reja CSV'ni tayyorlaydi (ataylab buzilgan saytlar bilan), `ground_truth.csv` ni yuritadi |
| **Muhandis** (1–2 kishi) | saytda o'lchaydi, `log.csv` ni to'ldiradi. **Qaysi saytlar buzilganini bilmaydi** (ko'r sinov) |
| **Azimut o'lchovchi** | antennalarning haqiqiy azimutini o'lchaydi (muhandis bilan bir odam bo'lishi mumkin, lekin natijani muhandisga ko'rsatmaydi) |

## 2. Saytlarni tanlash (koordinator)

| Toifa | Soni | Preset (Sozlamalar → Tahlil preseti) |
|---|---|---|
| Shahar (zich bino) | ~8 | **Shahar (rMax 600 m)** |
| Shahar atrofi | ~6 | **Shahar atrofi (standart)** |
| Qishloq | ~6 | **Qishloq (n = 3.0)** |

- Hammasi **3 va undan ko'p sektorli**; kamida **5 ta saytda 2–3 band** (har sektorda bir nechta ARFCN).
- **Ataylab buzilgan reja — kamida 3 sayt** (4–5 bo'lsa yaxshiroq): reja CSV'da ikki sektorning `pci` qiymatlarini
  almashtiring (masalan, S1 ↔ S2). Ko'p bandli saytda: **barcha bandlarda** almashtirish → `CELL_CONFIG_SWAP`;
  **faqat bitta bandda** → `BAND_PORT_SWAP`. Ikkala turdan ham bo'lsin.
- Imkon bo'lsa, **haqiqiy nosozligi ma'lum** saytlar (tuzatilishidan oldin): almashgan kabel, burilgan antenna — eng qimmatli ma'lumot.
- Atrofida 150–400 m (shaharda 100–300 m) radiusda aylanib yurish mumkin bo'lsin; kamida 270° halqa.

## 3. Ground truth (koordinator + azimut o'lchovchi)

Fayl: **`field-data/pilot/ground_truth.csv`** — reja CSV'dagi **har bir cell uchun bitta qator**:

```
site_code,rat,arfcn,pci,true_azimuth_deg,has_fault,fault_type
NAV-0123,LTE,1300,141,0,0,NONE
NAV-0123,LTE,1300,142,120,0,NONE
NAV-0123,LTE,1300,143,240,0,NONE
SAM-0456,LTE,1300,201,10,1,CELL_CONFIG_SWAP
SAM-0456,LTE,1300,202,130,1,CELL_CONFIG_SWAP
SAM-0456,LTE,1300,203,250,0,NONE
```

| Ustun | Qoida |
|---|---|
| `site_code` | reja CSV'dagi kod bilan **aynan bir xil** (moslash shu orqali) |
| `rat`, `arfcn`, `pci` | **ilovaga berilgan reja CSV'dagidek** (buzilgan saytda — buzilgan qiymat) |
| `true_azimuth_deg` | shu PCI'ni **haqiqatda nurlatayotgan** antennaning azimuti, 0–359°, **geografik shimoldan** |
| `has_fault` | `1` — ilova uchun bu cell xato (ataylab buzilgan yoki haqiqiy nosozlik), aks holda `0` |
| `fault_type` | `NONE`, `CELL_CONFIG_SWAP`, `BAND_PORT_SWAP`, `SWAP` (turi noma'lum), `ANTENNA_ROTATED`, `PCI_MISSING` |

**Azimutni o'lchash:** antenna old tomonida, uning yo'nalishi bo'ylab kompas yoki azimut o'lchagich bilan
(metall konstruksiyadan ≥ 5 m uzoqda), yoki dron/foto bilan. Magnit og'ishini tuzating (O'zbekistonda ≈ +5…+6° sharqqa;
aniq qiymatni NOAA kalkulyatoridan oling). O'lchab bo'lmasa — **bo'sh qoldiring** (taxmin yozmang).

> Buzilgan rejada PCI'lar almashgan bo'lsa ham `true_azimuth_deg` — **PCI'ning haqiqiy** yo'nalishi
> (yuqoridagi misolda reja S1=202 desa ham, 202 haqiqatda 130° da nurlanadi).

## 4. Muhandis uchun tayyorgarlik (bir marta)

1. H1 dagi telefon(lar): batareya tejash o'chiq, ilovaga fonda cheklovsiz ishlash ruxsati (`H1_DEVICE_TEST.md`, 4-bo'lim).
2. **Sozlamalar:** muhandis ismi, **Trafik URL** (HTTPS, masalan `https://www.google.com/generate_204`), **Saqlash**.
3. **Sozlamalar → Qurilma probe (60 s)** — har telefon uchun bir marta, ochiq joyda.
4. **Saytlar → CSV reja import** — koordinator bergan **pilot reja CSV**'si (barcha 20 sayt, buzilganlari bilan).
5. Kerakli narsalar: zaryadlangan telefon(lar), quvvat banki (batareya o'lchanmaydigan sessiyalar uchun), `log.csv` (qog'oz yoki telefonda).

## 5. Har bir saytda (muhandis)

1. **Preset**ni sayt toifasiga moslang (2-bo'limdagi jadval) — Sozlamalar → Tahlil preseti. Config sessiyaga yoziladi.
2. Saytga 150–400 m masofada ochiq joyda to'xtang. **`start_time`** — shu vaqtni yozing (AC-09 shu yerdan hisoblanadi).
3. **Saytlar** → sayt → **Oldindan tekshiruv**. Barcha qatorlar yashil/sariq bo'lsin; qizil bo'lsa — 8-bo'lim.
   *"Rejadagi PCI'lar: ko'rinmoqda X / Y"* — buzilgan saytlarda ham normal, e'tibor bermang.
4. Batareya o'lchanadigan sessiyada (6-bo'lim) — `battery_start`.
5. **Boshlash** → sayt atrofida bir tekis piyoda aylaning (~4–5 km/soat). Ekranni vaqti-vaqti bilan yoqib
   qamrov radarini ko'ring: bo'sh yo'nalishlar tomonga boring.
6. **"Natija tayyor"** chiqqach → **Tugatish**. 25 daqiqa o'tsa-yu chiqmasa — baribir **Tugatish** (`notes` ga yozing).
7. **Natija** ekrani chiqqan vaqt — **`end_time`**. Verdiktni `log.csv` ga yozing (PASS/WARN/FAIL/INCONCLUSIVE).
8. **Hisobot (PDF, ZIP)** → **Hisobotni yaratish** → **ZIP eksport** → faylni o'zingizga yuboring.
   Nomi: **`<sayt>_<YYYYMMDD>.zip`**, masalan `NAV-0123_20261105.zip`.
9. Natija ekranidagi verdikt va topilmalar haqida **koordinatorga hech narsa demang** va undan buzilgan saytlarni so'ramang.

**Qayta o'lchash:** agar sessiya buzilsa (yiqilish, GPS yo'q, yo'l yopiq) — yana bir marta o'lchang va eski ZIP'ni
`field-data/pilot/rejected/` ga qo'ying (`calibrate` faqat asosiy papkadagi ZIP'larni o'qiydi). Bitta sayt
uchun asosiy papkada **bitta ZIP** bo'lsin. **Qayta tekshiruv** (nosozlik tuzatilgandan keyin) ZIP'larini ham
`rejected/` emas, `field-data/pilot/recheck/` ga qo'ying — ular kalibrlashga kirmaydi.

## 6. Batareya sinovi (AC-06)

Kamida **2 sessiyada** (har chipset oilasi uchun bittadan bo'lsa yaxshi): `docs/BATTERY_TEST.md` tartibida —
batareya 80–100%, quvvatlagichsiz, **30 daqiqa** yurish, boshida va oxirida foizni yozing.
Bu sessiyada "Natija tayyor" chiqsa ham 30-daqiqagacha davom eting (`notes`: `battery-30min`).

## 7. Yozuvlar va qaytarish

**`field-data/pilot/log.csv`** — har sessiya uchun bitta qator:

```
site_code,start_time,end_time,battery_start,battery_end,device,notes
NAV-0123,2026-11-05 10:05,2026-11-05 10:27,,,galaxy-a54,PASS; shahar; preset URBAN
SAM-0456,2026-11-05 11:10,2026-11-05 11:40,96,88,redmi-note-12,FAIL; battery-30min
```

- Vaqt: `YYYY-MM-DD HH:MM` (mahalliy vaqt). Batareya o'lchanmasa — bo'sh.
- `notes`: ilova verdikti, muhit, g'ayrioddiy holat (yomg'ir, yo'l yopiq, GPS sakrashi, ilova yiqilishi).

| Fayl | Qayerga | Kim |
|---|---|---|
| Sessiya ZIP'lari (20 ta) | `field-data/pilot/` | muhandis |
| `log.csv` | `field-data/pilot/` | muhandis |
| `ground_truth.csv` | `field-data/pilot/` | koordinator (pilot tugagach) |
| Rad etilgan / qayta tekshiruv ZIP'lari | `field-data/pilot/rejected/`, `recheck/` | muhandis |
| Crash loglar (bo'lsa) | `field-data/pilot/` | muhandis (Sozlamalar → Crash loglarini eksport) |

So'ng barcha fayllarni **Claude sessiyasiga yuklang** (chatga biriktiring).

> **Maxfiylik:** ZIP'larda GPS izi bor. `field-data/**/*.zip` gitignore qilingan — commit qilmang, ochiq kanallarga yubormang.
> `ground_truth.csv` ni muhandisga pilot tugaguncha ko'rsatmang.

## 8. Muammolar

| Belgi | Nima qilish |
|---|---|
| "MCC/MNC … ga mos SIM yo'q" | to'g'ri operator SIM'i; reja CSV'dagi `mcc_mnc` ni tekshiring |
| "Serving LTE/NR cell hali ko'rinmadi" | Mobil tarmoq → 4G/5G rejimi |
| GPS aniqligi > 15 m | ochiq joyga chiqing, 1–2 daqiqa kuting |
| Yo'l yopiq, halqa yarim | bor joyini yuring; "Natija tayyor" chiqmasa ham 25-daqiqada **Tugatish**, `notes` ga yozing |
| Ilova yiqildi | qayta oching → "Tugallanmagan o'lchov" → **Davom ettirish**; crash logni eksport qiling |
| INCONCLUSIVE ko'p | normal bo'lishi mumkin (qamrov kam); `notes` ga sababni yozing — kalibrlash shuni hal qiladi |

## 9. Ma'lumot kelgach (men)

```
sv-replay calibrate field-data/pilot field-data/pilot/ground_truth.csv --out field-data/pilot/calibration
```

1. `recommended-config.json` va `calibration-report.md`: AC-08 aniqlash, noto'g'ri FAIL, azimut xatosi medianasi.
2. Shart (noto'g'ri FAIL ≤ 3%) bajarilsa — standart `AnalysisConfig` ni yangilayman (ADR bilan), bajarilmasa —
   qaysi saytlar xalaqit berganini ko'rsataman va qo'shimcha saytlar so'rayman.
3. `log.csv` dan AC-09 va AC-06 ni hisoblayman; hammasini `docs/PILOT_REPORT.md` ga yozaman, `RELEASE_CHECKLIST.md` ni yangilayman.
4. Tavsiya etilgan config'ni ilovaga darhol ham yuklash mumkin: **Sozlamalar → Config JSON import (kalibrlash)**.
