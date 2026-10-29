# Qo'llab-quvvatlanadigan qurilmalar

> **Holat: H1 kutilmoqda — ilova hali birorta haqiqiy telefonda sinalmagan.** CI'da ilova API 34 va API 36
> emulyatorlarida ishlaydi va testlardan o'tadi, lekin emulyator haqiqiy CellInfo (RSRP, PCI, TA) bermaydi — shuning uchun
> emulyator natijasi qurilma qo'llab-quvvatlashini isbotlamaydi. Jadval `field-data/h1/` dagi ZIP'lar va `devices.csv`
> asosida to'ldiriladi (sinov tartibi: `docs/H1_DEVICE_TEST.md`).

## Minimal talab
- Android 10+ (API 29); ilova targetSdk 36 (Android 16) uchun yig'ilgan.
- GPS (`GPS_PROVIDER`, Play Services kerak emas), LTE yoki NR, rejadagi operatorning SIM kartasi (dual-SIM'da o'zi tanlanadi).
- O'lchangan CellInfo chastotasi **≥ 0.5 Hz** (AC-05, `AnalysisConfig.minDeviceRateHz`) va qo'shni cell'lar **RSRP bilan**.

## Natijalar (H1)

| Qurilma | Chipset | Android | Chastota, Hz | Qo'shni RSRP | TA | NR SA | Ekran o'chiq / fon / yopish | Batareya, %/30 daq | Holat |
|---|---|---|---|---|---|---|---|---|---|
| — | Qualcomm | — | — | — | — | — | — | — | ⏳ |
| — | Exynos | — | — | — | — | — | — | — | ⏳ |
| — | MediaTek | — | — | — | — | — | — | — | ⏳ |

Ixtiyoriy qatorlar: Android 16 telefon, dual-SIM (mos SIM 2-slotda).

**Holat belgilari:**
- ✅ **tavsiya etiladi** — chastota ≥ 0.5 Hz, qo'shni RSRP bor, T2–T4 sinovlarida (ekran o'chiq, fon, ilovani yopish) yig'ish uzilmagan, yiqilish yo'q;
- ⚠️ **cheklov bilan** — asosiy talablar bajarilgan, lekin TA yoki NR SA maydonlari yo'q, yoki yig'ish faqat batareya tejash
  o'chirilganda uzilmaydi (izohda yoziladi);
- ❌ **tavsiya etilmaydi** — chastota < 0.5 Hz yoki qo'shni RSRP yo'q;
- ⏳ **sinalmagan**.

## Ustunlar qanday o'lchanadi
| Ustun | Manba | Izoh |
|---|---|---|
| Chastota | Sozlamalar → **Qurilma probe (60 s)**; sessiyada `session.json` → `measuredRateHz` | serving cell'ning **alohida CellInfo vaqt belgilari** soni / vaqt — modem haqiqatda nechta yangi o'lchov berganini ko'rsatadi, ilova so'rash tezligini emas |
| Qo'shni RSRP | probe: `neighborRsrpReported` | registered bo'lmagan cell'lar RSRP bilan keldimi |
| TA | probe: `timingAdvanceReported` | faqat LTE serving cell; telefon tarmoq bilan faol ulanishda bo'lganda keladi (Trafik URL) |
| NR SA | probe: `nrSaFieldsReported` | NR serving cell RSRP bilan keldimi (NSA'da serving odatda LTE) |
| Ekran o'chiq / fon / yopish | `devices.csv`: `t2_screen_off`, `t3_background`, `t4_swipe` | `ok` / `to'xtadi`; ZIP'dagi `cell_samples.csv` vaqt belgilaridagi uzilishlar bilan tekshiriladi |
| Batareya | `devices.csv` / `field-data/pilot/log.csv` | 30 daqiqalik sessiyada ≤ 15% (AC-06, `docs/BATTERY_TEST.md`) |

Yig'ish: `CellCollector` har 1 s da `requestCellInfoUpdate()` chaqiradi, API 31+ da `CellInfoListener` ham tinglaydi; ikkala
oqim (cell, vaqt belgisi) bo'yicha takrorlardan tozalanadi. Modem yangi o'lchov bermasa, eski vaqt belgili ma'lumot takror
sifatida tashlanadi — shuning uchun chastota 1 Hz dan oshmaydi va qurilmaga bog'liq.

## Maydon yo'q bo'lsa nima bo'ladi
| Yo'q maydon | Tahlilga ta'siri |
|---|---|
| Chastota < 0.5 Hz | binlarda namuna kam, ko'p sektor INCONCLUSIVE bo'ladi; oldindan tekshiruv sariq ogohlantiradi |
| Qo'shni RSRP | har sektor faqat o'zi serving bo'lgan hududda ko'rinadi — sektor qamrovi va baho sifati pasayadi; oldindan tekshiruv sariq ogohlantiradi |
| TA | boshqa saytdan kelgan (masofaga mos kelmaydigan) LTE namunalari TA filtri bilan tashlanmaydi (§6.1) — filtr faqat TA bor namunalarga qo'llanadi |
| NR SA | NR sektorlari baholanmaydi (faqat LTE) |

## Ma'lum telefon sozlamalari
Ba'zi ishlab chiqaruvchilar ekran o'chganda fon ishini cheklaydi. Ilova uchun batareya tejashni o'chirish tartibi (Samsung,
Xiaomi/Redmi/POCO, Tecno/Infinix/Realme): `docs/H1_DEVICE_TEST.md`, 4-bo'lim va foydalanuvchi qo'llanmasining 1-bo'limi.
Qaysi model bu sozlamani talab qilishi H1 natijasidan keyin jadvaldagi izohga yoziladi.
