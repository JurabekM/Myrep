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
