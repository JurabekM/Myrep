# Inson vazifalari

## H1 — real telefonlarda sinov (2-bosqichdan keyin) — KUTILMOQDA

**Maqsad:** AC-05 (3 chipset oilasida ≥ 0.5 Hz barqaror yig'ish) va qurilmalar ro'yxati (`docs/DEVICES.md`).
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
