# OCHIQ SAVOLLAR

1. **Half-up va manfiy qiymatlar.** Spetsifikatsiya faqat musbat misollarni beradi. Desktopda `round_half_up(-1/2) = 0` (+∞ tomon, `floor(x+½)`). Mobil (Dart) ham shunday qilishi kerak; kerak bo'lsa manfiy vektor qo'shamiz.
2. **Manfiy `total` bilan `allocate`.** Desktop modul bo'yicha taqsimlab, ishorani qaytaradi (`-100 / [1,1,1] → -34,-33,-33`). Mobil bilan tasdiqlash kerak.
3. **`format_money` qoidalari** (probel guruhlash — oddiy probel, vergulli kasr, nol kasr tushiriladi, `ru` da `сум`, boshqa valyutalarda kod) spetsifikatsiyada faqat `"8 000 000 so'm"` misoli bilan berilgan; qolganini biz tanladik. Mobil jamoa tasdiqlashi kerak. NBSP ishlatilmaydi.
4. **`FxRate` yo'nalishi:** `rate_num/rate_den` = `from` ning 1 minor birligi `to` ning nechta minor birligiga teng.
5. **Papka joylashuvi:** spetsifikatsiya `baraka-desktop/` ildizini nazarda tutadi; monorepoda `baraka_daftari/desktop/` ostida, `spec/` esa mobil bilan umumiy bo'lishi uchun `baraka_daftari/spec/` da.
6. **`ʻ` (U+02BB) / `ʼ` (U+02BC)** belgilari: `format_money` hozircha ASCII `'` ishlatadi (`so'm`). Spetsifikatsiya misoli ham shunday.
7. Ikonlar vaqtinchalik bir rangli placeholder; brend ikonlari kerak.
