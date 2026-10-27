# H1 — real telefonlarda qurilma sinovi (dala ko'rsatmasi)

**Maqsad:** ilova turli chipsetli telefonlarda CellInfo va GPS'ni barqaror yig'ishini tasdiqlash (**AC-05**: 3 chipset
oilasida ≥ 0.5 Hz) va `docs/DEVICES.md` (qo'llab-quvvatlanadigan qurilmalar) jadvalini to'ldirish.

**Vaqt:** bitta telefon uchun ~40 daqiqa (tayyorgarlik 10 + o'lchov 15 + eksport 5 + zaxira). 3 telefon bir saytda
ketma-ket yoki parallel (har birini alohida odam ko'tarsa) — yarim kun.

---

## 1. Kerakli narsalar

| # | Nima | Izoh |
|---|---|---|
| 1 | **Qualcomm Snapdragon** telefon | masalan Galaxy S2x (Snapdragon versiyasi), Xiaomi, OnePlus |
| 2 | **Samsung Exynos** telefon | masalan Galaxy A5x / S2x (Exynos versiyasi) |
| 3 | **MediaTek** telefon | masalan Redmi Note, Tecno, Infinix, Realme |
| 4 | (ixtiyoriy) **Android 16** telefon | ilova targetSdk 36 — Android 16 xatti-harakatini tekshirish uchun |
| 5 | (ixtiyoriy) **dual-SIM** telefon | mos SIM 2-slotda — SIM tanlashni tekshirish |
| 6 | Har telefonda faol SIM | MCC/MNC rejadagidek (masalan `43405`), mobil internet yoqilgan |
| 7 | Sinov saytining RF reja CSV fayli | format: `docs/samples/plan-example.csv` (§5.3) |
| 8 | Kompyuter + USB kabel | APK o'rnatish uchun (yoki APK faylni Telegram orqali yuborish) |
| 9 | Quvvat banki | ixtiyoriy; batareyani o'lchaydigan telefonni zaryadlamang |

Chipsetni bilish: **Sozlamalar → Telefon haqida → Protsessor**, yoki ilovadagi probe natijasi (6-qadam).
Barcha telefonlar Android 10+ (API 29+) bo'lsin.

## 2. APK tayyorlash (bir marta, kompyuterda)

```
cd sector-verify
.\gradlew.bat :app:assembleDebug
```

Natija: `app\build\outputs\apk\debug\app-debug.apk`. Debug build kerak — unda qo'shimcha **Debug: yig'ish ekrani** bor.

O'rnatish: `adb install -r app\build\outputs\apk\debug\app-debug.apk` (telefonda **USB debugging** yoqilgan bo'lsin),
yoki APK faylni telefonga yuborib, "Noma'lum manbalardan o'rnatish"ga ruxsat bering.

## 3. Saytni tanlash

- Rejadagi operatorning LTE (imkoni bo'lsa NR ham) sayti, **3 sektorli**.
- Atrofida **150–400 m radiusda aylanib yurish mumkin** bo'lgan yo'l (to'liq halqa ideal; kamida 270°).
- Ochiq osmon (GPS aniqligi ≤ 15 m — bundan yomon bo'lsa oldindan tekshiruv sariq ogohlantiradi). Baland binolar orasida emas.

## 4. Har bir telefonda — tayyorgarlik (saytga yetmasdan)

1. **Batareya tejash rejimini o'chiring** va ilovaga cheklovsiz fon ishlashiga ruxsat bering:
   - Samsung: Sozlamalar → Ilovalar → Sector Verify → Batareya → **Cheklanmagan**.
   - Xiaomi/Redmi/POCO: Ilova ma'lumoti → Batareya tejash → **Cheklovlar yo'q**; **Avto-ishga tushirish** yoqilsin.
   - Tecno/Infinix/Realme: Ilova → Batareya → **Fonda ishlashga ruxsat**.
   > Bu sinovning bir qismi: yozib qo'ying — bu sozlamasiz yig'ish to'xtadimi (keyingi telefonda tekshirish mumkin).
2. Tarmoq rejimi: **4G/5G (LTE/NR)** — 2G/3G emas.
3. Ilovani oching → **Sozlamalar**:
   - **Muhandis ismi** — ismingiz (hisobotga yoziladi).
   - **Trafik URL** — HTTPS manzil, so'rov parametrlarisiz, masalan `https://www.google.com/generate_204`.
     Bu TA (timing advance) kelishi uchun kerak: telefon tarmoq bilan faol ulanishda bo'lishi lozim.
   - **Saqlash**.
4. **Saytlar → CSV reja import** → sinov saytining CSV faylini tanlang. "Import qilindi: N ta sayt" chiqishi kerak.

## 5. Saytda — o'lchov

### 5.1. Probe (har telefon uchun bir marta)
5. Saytdan 150–400 m uzoqda, ochiq joyda turing. GPS'ni yoqing, 1–2 daqiqa kuting.
6. **Sozlamalar → Qurilma probe (60 s)** — 60 soniya telefonni qimirlatmang.
   Natija: `<model> · <Hz> · qo'shni RSRP: ha/yo'q · TA: ha/yo'q · NR SA: ha/yo'q`. **Skrinshot oling.**
7. (ixtiyoriy) **Sozlamalar → Debug: yig'ish ekrani** — "Ko'rinayotgan" qatorida qaysi PCI'lar ko'rinayotgani. **Skrinshot.**

### 5.2. Oldindan tekshiruv
8. **Saytlar** → saytni bosing → **Oldindan tekshiruv** → **Ruxsatlarni berish**: aniq joylashuv, telefon holati,
   bildirishnomalar — barchasiga **ruxsat bering**.
9. Barcha qatorlar yashil yoki sariq bo'lishi kerak. **Skrinshot oling.** Qizil bo'lsa — 8-bo'lim (muammolar).
10. Batareya foizini yozing (`battery_start`).

### 5.3. Yig'ish va sinov holatlari
11. **Boshlash** → jonli ekran ochiladi (xarita, qamrov radari, `Namunalar · GNSS · Hz`). Soatni yozing (`start_time`).
12. Sayt atrofida piyoda aylaning (~4–5 km/soat). Yo'lda quyidagi holatlarni **tartib bilan** bajaring:

| Holat | Qachon | Nima qilish | Nimani tekshirish |
|---|---|---|---|
| **T1** ekran yoqiq | 0–3 daq | jonli ekranga qarab yuring | `Hz` ≥ 0.5, namunalar har soniyada oshadi |
| **T2** ekran qulflangan | 3–7 daq | ekranni o'chiring, cho'ntakka soling | bildirishnomada namunalar soni oshib boradi |
| **T3** boshqa ilova | 7–9 daq | Telegram/kamera'ni oching, 2 daqiqa ishlating | qaytganda namunalar uzilmagan |
| **T4** ilovani "yopish" | 9–10 daq | so'nggi ilovalar ro'yxatidan ilovani surib yoping | bildirishnoma qoladi, yig'ish davom etadi |
| **T5** qaytish | 10 daq | bildirishnomani bosib ilovani oching | "o'lchov hozir ham yozilmoqda" → **O'lchovni ochish** — namunalar soni uzilmagan |

13. **"Natija tayyor"** bildirishnomasi chiqqach yoki 15 daqiqa o'tgach → **Tugatish**. Soat va batareyani yozing.
14. **Natija** ekrani → **skrinshot** → **Hisobot (PDF, ZIP)** → **Hisobotni yaratish** → **ZIP eksport** →
    faylni o'zingizga yuboring (Telegram "Saqlangan xabarlar", e-pochta yoki USB).

### 5.4. Faqat Android 16 telefonda (bo'lsa)
- Har ekranda matn/tugma status bar yoki navigatsiya paneli **ostida qolmaganini** tekshiring (edge-to-edge).
- Orqaga qaytish ishorasi (ekran chetidan surish) har ekranda to'g'ri ishlashi va oldindan ko'rish animatsiyasi.
- Telefonni yon tomonga burish (planshet/katlanadigan bo'lsa — ochish): ekran buzilmasligi.

## 6. Har telefon uchun yozuv

`field-data/h1/devices.csv` — har telefon uchun bitta qator:

```
device_id,model,chipset,android,operator,sim_slot,probe_hz,neighbor_rsrp,ta,nr_sa,start_time,end_time,battery_start,battery_end,t2_screen_off,t3_background,t4_swipe,crash,notes
galaxy-a54,SM-A546E,Exynos 1380,14,Ucell,1,0.98,ha,ha,yo'q,10:05,10:21,86,79,ok,ok,ok,yo'q,
redmi-note-12,23021RAA2Y,Snapdragon 685,13,Ucell,2,0.51,ha,yo'q,yo'q,10:40,10:56,92,84,ok,ok,to'xtadi,yo'q,MIUI tejash yoqilgan edi
```

- `t2_screen_off`, `t3_background`, `t4_swipe`: `ok` / `to'xtadi` / `sinalmadi`.
- `crash`: ilova yiqildimi. Yiqilgan bo'lsa: **Sozlamalar → Crash loglarini eksport** — faylni ham yuboring.
- `notes`: batareya sozlamasi, GPS muammosi, g'alati holatlar.

## 7. Qaytarish

| Fayl | Nomi | Qayerga |
|---|---|---|
| Sessiya ZIP | `<sayt>_<device_id>.zip`, masalan `NAV-0123_galaxy-a54.zip` | `field-data/h1/` |
| Yozuv jadvali | `devices.csv` | `field-data/h1/` |
| Skrinshotlar | `<device_id>_probe.png`, `<device_id>_precheck.png`, `<device_id>_result.png` | `field-data/h1/` |
| Crash log (bo'lsa) | `<device_id>_crash.txt` | `field-data/h1/` |

So'ng fayllarni **Claude sessiyasiga yuklang** (chatga biriktiring) — men ularni shu yerdan olaman.

> **Maxfiylik:** ZIP ichida yurgan yo'lingiz (GPS izi) bor. `field-data/**/*.zip` gitignore qilingan — ZIP'larni
> commit qilmang va ochiq kanallarga yubormang.

## 8. Muammolar

| Belgi | Sabab | Nima qilish |
|---|---|---|
| "MCC/MNC … ga mos SIM yo'q" | SIM boshqa operatorniki yoki reja CSV'da `mcc_mnc` xato | to'g'ri SIM qo'ying yoki CSV'ni tekshiring |
| "Serving LTE/NR cell hali ko'rinmadi" | tarmoq rejimi 2G/3G | Sozlamalar → Mobil tarmoq → 4G/5G |
| GPS aniqligi > 15 m | bino ichida / osmon yopiq | ochiq joyga chiqing, 2 daqiqa kuting |
| Probe < 0.5 Hz | telefon CellInfo'ni kam yangilaydi | yozib qo'ying (bu ham natija); sessiyani baribir o'tkazing |
| "Trafik generatori o'chiq" | Trafik URL bo'sh | Sozlamalar → Trafik URL |
| Ekran o'chganda namunalar to'xtaydi | batareya tejash | 4-bo'lim, 1-band; `notes` ga yozing |
| Ilova yiqildi | — | qayta oching ("Tugallanmagan o'lchov" → Davom ettirish), crash logni eksport qiling |

## 9. Natijani baholash (men ZIP'lardan tekshiraman)

**Qabul mezoni — AC-05:** uchala chipset oilasida o'lchangan chastota **≥ 0.5 Hz** (3/3). Manba: ZIP'dagi
`session.json` → `measuredRateHz` (`sv-replay analyze` ham ko'rsatadi).

Qo'shimcha kuzatuvlar (`DEVICES.md` ga yoziladi, alohida chegara emas):
- GNSS ~1 Hz bo'yicha keldimi, qayerda uzildi;
- T2–T4 holatlarida namunalar orasida uzilish bo'ldimi (`cell_samples.csv` vaqt belgilaridan);
- yiqilish bo'ldimi, tiklash ishladimi;
- qo'shni cell'lar RSRP bilan keldimi; TA (serving uchun) va NR SA maydonlari bor-yo'qligi.

Natijalar kelgach men: `sv-replay verify` va `sv-replay analyze` bilan har ZIP'ni tekshiraman, `docs/DEVICES.md` ni
to'ldiraman va kerak bo'lsa yig'ishni (masalan, ma'lum chipset uchun) tuzataman.
