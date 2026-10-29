# Batareya sinovi (AC-06: 30 daqiqalik sessiyada ≤ 15%)

Inson tomonidan bajariladi — H1 (`docs/H1_DEVICE_TEST.md`) yoki H2 (`docs/H2_PILOT_GUIDE.md`, 6-bo'lim) vaqtida.
**Har bir chipset oilasi uchun kamida 1 ta telefon** (Qualcomm, Exynos, MediaTek).

## O'lchov vaqtida ilova nima ishlatadi
| Manba | Chastota | Kod |
|---|---|---|
| GPS (`GPS_PROVIDER`) | 1 Hz | `GnssCollector` |
| CellInfo (`requestCellInfoUpdate` + API 31+ listener) | 1 Hz | `CellCollector` |
| Trafik generatori (HTTPS HEAD, Trafik URL to'ldirilgan bo'lsa) | har 2 s | `TrafficGenerator` |
| Jonli tahlil | har 5 s | `LiveAnalyzer` |
| Bazaga yozish (bitta tranzaksiya) | har 1 s | `BufferedSampleWriter` |
| Partial WakeLock (CPU uyg'oq, ekran emas) | sessiya davomida, ko'pi bilan 3 soat | `SurveyForegroundService` |

Trafik URL to'ldirilgan holat — **eng yomon holat** (radio doim faol); AC-06 shu holatda o'lchanadi.

## Shartlar
- Batareya **80–100%**, quvvatlagich va USB kabel **ulanmagan** (USB ham zaryadlaydi).
- Telefonning umumiy **batareya tejash rejimi o'chiq**; ilova uchun ham cheklov yo'q — OEM sozlamalari: `docs/H1_DEVICE_TEST.md`, 4-bo'lim.
  (Tejash yoqilgan bo'lsa sarf kamroq ko'rinadi, lekin yig'ish uzilishi mumkin — natija noto'g'ri bo'ladi.)
- Ekran yorqinligi **avtomatik**. Fonda navigatsiya, video va musiqa ilovalari yopiq.
- Mobil internet yoqilgan, **Wi-Fi o'chiq**, Bluetooth o'chiq.
- Sozlamalarda **Trafik URL** to'ldirilgan (masalan `https://www.google.com/generate_204`).
- Havo harorati yozing (`notes`): sovuqda va issiqda Li-ion sarfi o'zgaradi.

## Tartib
1. (Ixtiyoriy, aniqroq natija uchun) telefon USB orqali ulangan holda: `adb shell dumpsys batterystats --reset`, so'ng **kabelni uzing**.
2. Batareya foizini va vaqtni yozing (`battery_start`, `start_time`).
3. Saytda **Oldindan tekshiruv → Boshlash**. **30 daqiqa** yuring: ekranni ~5 daqiqada bir yoqib qamrov radarini ko'ring,
   qolgan vaqtda ekran o'chiq (cho'ntakda). **«Natija tayyor» chiqsa ham 30-daqiqagacha davom eting.**
4. Aynan 30-daqiqada **Tugatish** → batareya foizi va vaqtni yozing (`battery_end`, `end_time`).
5. (Ixtiyoriy) kabelni ulab: `adb shell dumpsys batterystats uz.sectorverify > <device_id>_batterystats.txt` —
   1-qadamdan beri ilova sarfi (CPU, GPS, radio, WakeLock vaqti).

## Natijani yozish
`field-data/pilot/log.csv` ga bitta qator (H1 da — `field-data/h1/devices.csv` dagi `battery_start`/`battery_end` ustunlari):

```
site_code,start_time,end_time,battery_start,battery_end,device,notes
SAM-0456,2026-11-05 11:10,2026-11-05 11:40,96,88,redmi-note-12,battery-30min; +18 °C; trafik URL bor
```

- Vaqt `YYYY-MM-DD HH:MM`, batareya — butun foiz.
- `notes` ga albatta `battery-30min` yozing — boshqa sessiyalardan ajratish uchun.
- `batterystats.txt` bo'lsa — shu papkaga.

## Mezon va hisobot
**AC-06:** `battery_start − battery_end ≤ 15` (foiz punkt) — har bir sinalgan chipset oilasida.
Natija `docs/RELEASE_CHECKLIST.md` dagi AC-06 qatoriga va `docs/DEVICES.md` dagi "Batareya" ustuniga yoziladi.
Chegara oshsa: `batterystats` bo'yicha qaysi manba ko'p yeyotganini aniqlab (odatda GPS yoki radio), tuzatish taklif qilinadi —
chegara yumshatilmaydi.
