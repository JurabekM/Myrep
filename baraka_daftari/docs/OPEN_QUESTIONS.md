# OCHIQ SAVOLLAR

1. **Half-up va manfiy qiymatlar.** Spetsifikatsiya faqat musbat misollarni beradi. Desktopda `round_half_up(-1/2) = 0` (+∞ tomon, `floor(x+½)`). Mobil (Dart) ham shunday qilishi kerak; kerak bo'lsa manfiy vektor qo'shamiz.
2. **Manfiy `total` bilan `allocate`.** Desktop modul bo'yicha taqsimlab, ishorani qaytaradi (`-100 / [1,1,1] → -34,-33,-33`). Mobil bilan tasdiqlash kerak.
3. **`format_money` qoidalari** (probel guruhlash — oddiy probel, vergulli kasr, nol kasr tushiriladi, `ru` da `сум`, boshqa valyutalarda kod) spetsifikatsiyada faqat `"8 000 000 so'm"` misoli bilan berilgan; qolganini biz tanladik. Mobil jamoa tasdiqlashi kerak. NBSP ishlatilmaydi.
4. **`FxRate` yo'nalishi:** `rate_num/rate_den` = `from` ning 1 minor birligi `to` ning nechta minor birligiga teng.
5. **Papka joylashuvi:** spetsifikatsiya `baraka-desktop/` ildizini nazarda tutadi; monorepoda `baraka_daftari/desktop/` ostida, `spec/` esa mobil bilan umumiy bo'lishi uchun `baraka_daftari/spec/` da.
6. **`ʻ` (U+02BB) / `ʼ` (U+02BC)** belgilari: `format_money` hozircha ASCII `'` ishlatadi (`so'm`). Spetsifikatsiya misoli ham shunday.
7. Ikonlar vaqtinchalik bir rangli placeholder; brend ikonlari kerak.
8. **Windows Hello** (`UserConsentVerifier`) D3 da qilinmadi: ixtiyoriy, `unsafe` va WinRT bog'liqliklarini talab qiladi. Alohida vazifa sifatida qo'shamizmi?
9. **Keyring yo'qolsa** (Windows profili tiklangan, boshqa kompyuterga ko'chirilgan) baza faqat `.baraka` zaxira fayldan (D14) tiklanadi. UI hozircha shuni aytadi; tiklash oqimi D14 da.
10. **PIN unutilsa** tiklash yo'li yo'q (ataylab). Onboarding (D15) da bu ochiq ogohlantirilishi kerak.
11. **Lockout fayli** (`vault.json`) hujumchi tomonidan tahrirlanishi mumkin; lekin fayl bor hujumchi baribir Argon2id + keyring sirini buzishi kerak. Lockout faqat onlayn taxminlardan himoya.
12. **Ekran qulfi bilan qulflash** (Windows sessiya qulfi hodisasi) hali ulanmagan — hozir faqat harakatsizlik taymeri va `Ctrl+L`.
13. **Nasiya modeli vaqtinchalik.** SPEC bo'yicha nasiya `Debt (SHOP)` ga birlashadi (D9). Hozir `obligations` (`kind = NASIYA`) da turadi; D9 migratsiyasi uni `debts` ga ko'chiradi. Tasdiqlang.
14. **Oy yakuni va izohsiz summa ta'rifi.** `oy yakuni = daromad − majburiyat − xarajat` (jamg'arma egasida qoladi), `izohsiz = oy yakuni − jamg'arma`. Vektor `unexplained_gap` shu ta'rifda. Mobil bilan tasdiqlash kerak.
15. **Streak ta'rifi:** hafta "bajarilgan" — unda kamida bitta `ALLOCATION` bor; joriy (tugamagan) hafta ketma-ketlikni uzmaydi. Boshlang'ich balans va qo'lda olish/qo'yish hisobga kirmaydi. Mobil bilan tasdiqlash kerak (`streak.json`).
16. **Audit va oddiy xarajat** bir oyda ikkalasi kiritilsa yig'iladi (audit — kiritilmagan oy uchun mo'ljallangan). Kerak bo'lsa kategoriya bo'yicha "audit oddiy xarajatni almashtiradi" qoidasini qo'shamiz.
17. **Doimiy majburiyatlar har oy to'langan deb hisoblanadi** (alohida to'lov yozuvi yo'q). To'lov tarixi va eslatmalar D7 da (bildirishnomalar).
18. **Toshkent vaqti** = UTC+5 qat'iy ofset (`chrono-tz` kerak emas). O'zbekistonda yozgi vaqt yo'q; qoida o'zgarsa `TASHKENT_OFFSET_HOURS` yagona joyda.
19. **Pul olish pauzasi 24 soat** (spetsifikatsiyada raqam yo'q — biz tanladik). «Bu haqiqatan favqulodda holatmi?» savoli D8 (qorovul pul) da qo'shiladi.
20. **Server xabarlari o'zbekcha** (`Invalid.message`), rus tilida ham o'zbekcha ko'rinadi; kodlangan xato turlari ikkala tilda tarjima qilingan.
