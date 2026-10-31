# O'zgarishlar tarixi

## 1.0.0 — 2026-10-31
Birinchi versiya.

- Matn tahlili: `docs/TAHLIL.md` — metodning 8 g'oyasi, to'g'ri / aniqlashtirilgan / olinmagan qismlar, funksiya xaritasi.
- Yadro (`android/core`): `MoneyMath`, `MoneyFormat`, `Debt` va A/B tasnif, `FxRates`, `Budget` (70/30, xavfsiz ulush),
  `Planner` (ikki qavatli to'lov, 4 strategiya, yopilmaydigan qarzni aniqlash), `Installment` (yashirin yillik foiz),
  `OverviewCalc`, `Ledger`, `Scripts` (halol muzokara matni, restrukturizatsiya arizasi), `Habits`, `DueDates`, `UzDates`.
- Python oracle va 35 ta oltin vektor (5 suite); Kotlin yadro ularni aynan takrorlaydi.
- Android ilova (Compose, dark theme): onboarding, bosh sahifa, qarzlar, qarz kartochkasi (to'lov, kelishuv, ariza),
  reja 70/30 va usullarni taqqoslash, nasiya kalkulyatori, yo'l xaritasi, kun tartibi, yordam, valyuta kurslari,
  zaxira nusxa, maxfiylik sozlamasi.
- Maxfiylik: `INTERNET` ruxsati yo'q, AES-256-GCM + Android Keystore, `FLAG_SECURE`, bulutli zaxira o'chiq.
- Testlar: yadro 29 ta (vektorlar bilan), Robolectric: 8 ekran testi + 7 PIN testi + 6 eslatma testi (26 skrinshot).
- Kirill yozuvi: `Translit` (yadro, 3 ta test), yozuv tanlovi onboarding va «Yana»da, barcha UI matni,
  toast va ulashiladigan matnlar tanlangan yozuvda; foydalanuvchi izohlari va o'z odatlari o'zgarmaydi.
  Kirillda 2 ta ekran testi.
- To'lov kuni eslatmalari: `core/Reminders` (qaysi qarz, qachon; to'langan muddat o'tkaziladi; 4 test),
  `AlarmManager` signali + `ReminderReceiver` (kunlik, qayta yuklanish / vaqt / mintaqa o'zgarishida tiklanadi),
  qulflangan ekranda yashirin bildirishnoma, lotin/kirill; sozlamalar ekrani (Android 13+ ruxsat so'rash,
  necha kun oldin, soat, «Sinab ko'rish»), bosh sahifada taklif. Robolectric: 6 receiver testi + ekran testi.
  Kalit qatorlari endi to'liq bosiladi (`SwitchRow`).
- PIN-kod qulfi: `core/Pin` (PBKDF2-HMAC-SHA256, tuz, doimiy vaqtda solishtirish, oson PIN rad etish,
  kutish jadvali va soat orqaga surilishiga chidamlilik; 4 test, `hashlib` vektorlari bilan), qulf ekrani
  (o'z raqamli klaviaturasi, kutish hisoblagichi, «unutdingizmi?» → ma'lumotni o'chirish), «Yana → PIN-kod»
  (o'rnatish, o'zgartirish, o'chirish, fonda kutish muddati), fondan qaytganda qulf (ekran burilishi hisobga
  olinmaydi), PIN yoqilganda bildirishnomada tafsilot yo'q, zaxira nusxada PIN yo'q. Robolectric: 7 test.
  `toast` endi istalgan oqimdan xavfsiz.
- PR self-review tuzatishlari: umumiy progress yopilgan qarzlarni ham hisoblaydi; `Budget.suggestedShareBp`
  (yadro + oracle + 3 yangi vektor) onboarding va rejada yagona taklif; nasiya kalkulyatori va umumiy hisob
  UI oqimidan tashqarida; to'lovi bor qarzda valyuta qulflangan; kurs maydonida 0 — kursni o'chiradi;
  transliteratsiyada qo'shimcha qoidasi faqat oylar va bir nechta o'zak uchun.
- CI: `.github/workflows/qarzsiz.yml` — oracle, testlar, release APK, `INTERNET` yo'qligini tekshirish.
