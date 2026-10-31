# O'zgarishlar tarixi

## 1.0.0 — 2026-10-31
Birinchi versiya.

- Matn tahlili: `docs/TAHLIL.md` — metodning 8 g'oyasi, to'g'ri / aniqlashtirilgan / olinmagan qismlar, funksiya xaritasi.
- Yadro (`android/core`): `MoneyMath`, `MoneyFormat`, `Debt` va A/B tasnif, `FxRates`, `Budget` (70/30, xavfsiz ulush),
  `Planner` (ikki qavatli to'lov, 4 strategiya, yopilmaydigan qarzni aniqlash), `Installment` (yashirin yillik foiz),
  `OverviewCalc`, `Ledger`, `Scripts` (halol muzokara matni, restrukturizatsiya arizasi), `Habits`, `DueDates`, `UzDates`.
- Python oracle va 32 ta oltin vektor (5 suite); Kotlin yadro ularni aynan takrorlaydi.
- Android ilova (Compose, dark theme): onboarding, bosh sahifa, qarzlar, qarz kartochkasi (to'lov, kelishuv, ariza),
  reja 70/30 va usullarni taqqoslash, nasiya kalkulyatori, yo'l xaritasi, kun tartibi, yordam, valyuta kurslari,
  zaxira nusxa, maxfiylik sozlamasi.
- Maxfiylik: `INTERNET` ruxsati yo'q, AES-256-GCM + Android Keystore, `FLAG_SECURE`, bulutli zaxira o'chiq.
- Testlar: yadro 20 ta (vektorlar bilan), Robolectric + Roborazzi ekran testlari 7 ta (21 skrinshot).
- Kirill yozuvi: `Translit` (yadro, 3 ta test), yozuv tanlovi onboarding va «Yana»da, barcha UI matni,
  toast va ulashiladigan matnlar tanlangan yozuvda; foydalanuvchi izohlari va o'z odatlari o'zgarmaydi.
  Kirillda 2 ta ekran testi.
- CI: `.github/workflows/qarzsiz.yml` — oracle, testlar, release APK, `INTERNET` yo'qligini tekshirish.
