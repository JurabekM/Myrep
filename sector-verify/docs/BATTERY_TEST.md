# Batareya sinovi (AC-06: 30 daqiqalik sessiyada ≤ 15%)

Inson tomonidan bajariladi (H1/H2). Har bir chipset oilasi uchun kamida 1 ta telefon.

## Shartlar
- Batareya 80–100%, quvvatlagichsiz; batareya tejash rejimi **o'chiq**; ekran yorqinligi avtomatik.
- Fonda boshqa navigatsiya/video ilovalari yopiq. Mobil internet yoqilgan, Wi-Fi o'chiq.
- Sozlamalarda **Trafik URL** to'ldirilgan (HEAD har 2 s — eng yomon holat).

## Tartib
1. Batareya % ni yozing (`battery_start`), vaqtni yozing.
2. Saytda **Boshlash** → 30 daqiqa yuring; ekranni 5 daqiqada bir yoqib qamrovni ko'ring, qolgan vaqtda ekran o'chiq.
3. 30-daqiqada **Tugatish** → `battery_end` va vaqtni yozing.
4. (Ixtiyoriy) `adb shell dumpsys batterystats --charged uz.sectorverify > batterystats.txt`.

## Natija
`field-data/pilot/log.csv` ga: `site_code,start_time,end_time,battery_start,battery_end,device,notes`.
**Mezon:** `battery_start − battery_end ≤ 15` (foiz punkt). Natija `docs/RELEASE_CHECKLIST.md` dagi AC-06 qatoriga yoziladi.
