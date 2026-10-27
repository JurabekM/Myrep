# Ochiq savollar

## Vazifa 1 dan

1. **Shrift.** Placeholder mavzuda tizim shrifti (Android'da Roboto) kattaroq o'lcham va qator oralig'i bilan ishlatilgan. Brend shrifti (masalan, lotin va kirillni qo'llaydigan Noto Serif / PT Serif) tanlansa, TTF ilovaga joylanadi — tarmoqdan yuklanmaydi. Qaysi shrift?
2. **Flutter versiyasi.** 3.32.5 qotirildi (mashinadagi o'rnatilgan versiya). Yangi stable'ga o'tish kerakmi?
3. **Riverpod.** ADR Riverpod 2 ni talab qiladi; 3.x chiqqan. Hozircha 2.6.1 da qolamiz — o'tish faqat ruxsat bilan.
4. ~~**applicationId** `uz.barakadaftari.app` vaqtinchalik.~~ Hal qilindi (2026-10-23): `uz.barakadastur.app` — pastdagi «Nom va mustaqil kontent» bo'limiga qarang.
5. **Til tanlovi saqlanmaydi.** Hozircha xotirada; shifrlangan baza (Vazifa 3) tayyor bo'lgach saqlanadi. Tizim tili `ru` bo'lsa, birinchi ishga tushishda avtomatik `ru` tanlansinmi?
6. **CI** hali haqiqiy GitHub'da ishga tushirilmagan (remote yo'q). Lokal ravishda har bir qadam alohida bajarilib tekshirildi.

## Vazifa 2 dan

7. **PIN'ni unutish.** Hozir tiklash yo'li yo'q (ma'lumotlar faqat qurilmada). Tiklash = ilova ma'lumotlarini o'chirish. Shunday qoladimi yoki eksport/zaxira (SPEC 6: parolli fayl) bilan bog'lanadimi?
8. **Imzo xeshi.** Release kaliti hali yo'q — `expectedSignatureSha256` bo'sh, imzo tekshiruvi «sozlanmagan» holatda. Release imzosi tayyor bo'lganda CI'ga qo'shiladi.
9. **Biometriya qurilmada sinalmagan.** Emulyatorda ekran qulfi yo'q (uni o'zgartirish qurilma xavfsizlik sozlamasi bo'lgani uchun qilmadim). Mantiq testlar bilan qoplangan; haqiqiy telefonda qo'lda tekshirish kerak.
10. **Lockout siyosati** (5 ta bepul urinish, 30 s dan 1 soatgacha ikki baravar) — mahsulot jihatidan tasdiqlansinmi? Masalan, bank ilovalari kabi N ta xatodan keyin ma'lumotni o'chirish kerakmi (hozir yo'q)?
11. **Integrity ogohlantirishi** har ishga tushishda chiqadi (sessiya ichida yopiladi). «Boshqa ko'rsatma» varianti kerakmi?
12. **Lockdan keyingi navigatsiya.** Qulf ochilgach push qilingan ekranga emas, asosiy marshrutga (masalan, `/home`) qaytiladi; ichki stek tiklanmaydi.

## Vazifa 3 dan

13. **Yaxlitlash standarti.** Pul uchun `halfEven` (bank yaxlitlashi) tanlandi. Ulush taklifida (Vazifa 4) summani 1 000 so'mgacha yaxlitlash kerakmi va qaysi tomonga (foydalanuvchi foydasiga — yuqoriga)?
14. **Tiyin.** UZS minor birligi tiyin (2 xona, SPEC 4.2). Amalda tiyin ishlatilmaydi — kiritishda faqat butun so'm qabul qilaylikmi?
15. **APK hajmi** SQLCipher sababli ~36 MB (x64). `--split-per-abi` bilan har ABI uchun alohida chiqarish (Play'da AAB) — ma'qulmi?
16. **Kategoriya nomlari** bazada kalit (`groceries`), nomi ARB'dan. Foydalanuvchi standart kategoriya nomini o'zgartirsa, `name` ustuni kalitdan ustun turadi — shunday qoladimi?
17. **Shifrlash testi host'da** faqat Linux CI'da (libsqlcipher) ishlaydi; Windows'da qurilmadagi integration test bilan tekshiriladi.

## Vazifa 4 dan

18. **Qarorlar (tasdiqlang):** kiritish faqat butun so'mda; ulush taklifi 1 000 so'mgacha **yuqoriga** yaxlitlanadi (jamg'arma foydasiga), daromaddan oshmaydi. Progressiv ulush 10 % da to'xtaydi.
19. **Pul olish pauzasi** 5 soniya. SPEC «pauza qo'yiladi» deydi — uzunroq (masalan, 24 soat «sovish» muddati) kerakmi?
20. **«Bu safar emas»** bosilganda hech narsa yozilmaydi. Analitika uchun «rad etildi» hodisasini saqlash kerakmi (keyinchalik «qutqarilgan pul» hisobi uchun)?
21. **«Kelajagim»ga qo'lda qo'shish** tugmasi yo'q (faqat daromad ulushi va avval yig'ilgan pul). MVP-2 dagi «qutqarilgan pulni o'tkazish» bilan birga qo'shilsinmi?
22. **Pul olishdan keyin «o'rnini to'ldirish rejasi»** (SPEC 2C.3 favqulodda zaxira uchun) — MVP-3 da.

## Vazifa 5 dan

23. **Majburiyat va xarajat munosabati.** Majburiyat o'z kategoriyasida yozilgan xarajat bilan «qoplangan» hisoblanadi; yozilmagan qismi to'langan deb faraz qilinadi (oy yakuni va auditda). Shu qoida ma'qulmi yoki majburiyatlarga alohida «To'landi» belgisi kerakmi?
24. **Oy o'rtasida qo'shilgan majburiyat** shu oyda to'liq hisoblanadi; o'tgan oy auditiga esa kirmaydi (yaratilgan sanadan keyin). To'g'rimi?
25. **«Kimning puli?» foizlari** chiqim daromaddan ko'p bo'lsa jami chiqimga nisbatan ko'rsatiladi (ogohlantirish bilan). Daromadga nisbatan ko'rsatish (100 % dan oshishi mumkin) afzalmi?
26. **Bildirishnoma belgisi** hozircha tizimning standart «eslatma» ikonkasi. Monoxrom loyiha ikonkasi (daftar) kerak — dizayn tasdig'i bilan.
27. **Eslatma vaqti** — 09:00 qat'iy. Foydalanuvchi sozlay olishi kerakmi?
28. **Oila a'zolarining huquqlari** (masalan, bola yozuvlarni ko'rmasligi) — MVP-1 da yo'q, barcha a'zolar bitta qurilmada teng.

## Vazifa 6 dan

29. **[Hal qilindi, 2026-10-23] Kontent manbasi.** Bob matnlari va maslahatlarni loyiha jamoasi yozadi (SPEC boshidagi mustaqillik qarori); `chapters.json` da faqat diniy bloklar ulamo tekshiruvini kutadi. Audio fayllar qayerda saqlanadi (CDN)? MVP-1 da audio pleyer yo'q — model tayyor.
30. **Diniy matnlar** uchun ulamo kim va tasdiq jarayoni qanday (kim `APPROVED` qiladi, qanday qayd etiladi)?
31. **Vazifalar matni** (1-bob) men tomonimdan yozildi — kontent muallifi tasdiqlashi kerak.
32. **Bob ochilishi** dastur boshlangan haftadan sanaladi (uy xo'jaligi yaratilgan sana). Har kim o'z «1-hafta»sidan boshlaydimi yoki barcha foydalanuvchilar uchun umumiy taqvim (masalan, kampaniya sanasi) bo'ladimi?
33. **Juma bildirishnomasi vaqti** — 09:00 qat'iy; juma namozi vaqtini hisobga olib boshqa vaqt afzalmi?
34. **Qo'lda belgilangan avto-vazifa** — foydalanuvchi o'zi belgilashi ham mumkin (ishonch tamoyili). Faqat ilova tasdiqlasin deyish kerakmi?

## 0-vazifadan

35. **2–5-boblar vazifalari** men tomonimdan yozildi (placeholder) — kontent muallifi tasdiqlashi kerak. Hozircha har bobdagi triggerli vazifalarni qo'lda ham belgilash mumkin, aks holda modullar tayyor bo'lguncha (7–14-vazifalar) odat qoidasi keyingi bobni ochmasdi.
36. **Odat qoidasi chegaralari** — 2 vazifa va 7 kun. SPEC 2C.6 «3 haftadan 2 tasida» deydi; reja «≥2 vazifa + ≥7 kun» deydi. Rejadagisi amalga oshirildi (sozlanadi). Qaysi biri yakuniy?
37. **`VAULT_FIRST_DEPOSIT`** har «Kelajagim»ga qo'yishda yuboriladi (vazifa haftada bir marta belgilanadi). Aks holda bob ochilishidan oldin pul qo'ygan foydalanuvchi bu vazifani hech qachon bajara olmasdi. Ma'qulmi?
38. **Shaxsiy PIN'siz a'zo** oilaviy rozilikni bir bosish bilan tasdiqlaydi. To'g'rimi yoki kattalar uchun PIN majburiy bo'lsinmi?

## Vazifa 7 dan

39. **Standart toifalar** men tomonimdan belgilandi: telefon, benzin, mayda kundalik va «Boshqa» — `KERAK`; yo'lkira — `ZARUR`; ichimlik/kafe — `HAVAS`. Oila o'zgartira oladi, lekin standartni kontent muallifi/iqtisodchi tasdiqlashi kerak.
40. **Shaxsiy havas ulushi** (SPEC 2B.3: «har bir a'zo uchun shaxsiy havas ulushi belgilanishi mumkin») MVP'da yo'q — faqat oilaviy umumiy chegara. Kerakmi?
41. **Vidjet summasini yashirish vaqti.** Ilova fonga o'tgach summalar qulf vaqti (standart 2 daqiqa) tugaguncha ko'rinadi; yashirish WorkManager bilan — emulyatorda ~3,5 daqiqada yashirildi (JobScheduler kechiktirishi). Aniq vaqt uchun `AlarmManager` exact alarm kerak (Android 13+ da `SCHEDULE_EXACT_ALARM` ruxsati). Yoki qat'iyroq variant: fonga o'tishi bilan darhol yashirish (lekin unda vidjetda summa deyarli hech qachon ko'rinmaydi). Qaysi biri?
42. **«Mayda xarajat» ta'rifi**: majburiyat kategoriyalari (ijara, kredit, kommunal), oziq-ovqat va sadaqadan tashqari hammasi jamlanadi. Prognoz oxirgi 30 kun bo'yicha. Bu ma'qulmi?
43. **Vidjetda 4 ta shablon** ko'rsatiladi (birinchi to'rttasi). Tartibni foydalanuvchi o'zgartira olishi kerakmi?
44. **Shirinlik eslatmasi vaqti** — tanlangan kuni 09:00 qat'iy (majburiyat va juma bildirishnomasi bilan bir xil).

## Vazifa 8 dan

45. **«Oqib ketish» ta'rifi.** Qutqarilgan pul hisobida «oqib ketgan» = amaldagi toifasi havas bo'lgan xarajatlar (sovg'a va sadaqasiz). Mayda «kerak» xarajatlar (masalan, mayda kundalik) ham qo'shilsinmi?
46. **Unutilgan obuna chegarasi** — 30 kun. Sozlanadigan bo'lsinmi?
47. **Obuna to'lovlari xarajat sifatida** avtomatik yozilmaydi (majburiyatlardek eslatma ham yo'q). Obunani majburiyatga aylantirish yoki to'lov kunida eslatish kerakmi?
48. **Konvert va kategoriya**: bitta kategoriya faqat bitta konvertga tegishli. Konvert kategoriyalari o'zgartirilsa, joriy hafta xarajatlari qayta hisoblanadi (yopilgan haftalar o'zgarmaydi). Xarajat kiritishda konvertni qo'lda tanlash kerakmi?
49. **Ilova ochilmagan haftalar**: konvert davri ilova ochilganda yaratiladi; umuman ochilmagan hafta uchun qoldiq yozilmaydi. Ma'qulmi?
50. **Qutqarilgan pulni o'tkazish** faqat haftalik mavjud qismdan (bosh ekran va «Qutqarilgan pul» ekranida). Oylik qismdan ham o'tkazish kerakmi?

## Vazifa 9 dan

51. **Zaxira maqsadidagi xarajatlar**: faqat yozilgan xarajatlar (amaldagi toifa ZARUR + KERAK). Yozilmagan majburiyatlar (ijara va h.k. — auditda «faraz qilingan» qism) qo'shilsinmi? Hozir qo'shilmaydi, ya'ni majburiyatni xarajat sifatida yozmagan oilada maqsad kamroq chiqadi.
52. **Qayta to'ldirish rejasi** faqat taklif (6 oy, 1 000 soʻmgacha yuqoriga) — saqlanmaydi va eslatilmaydi. Rejani saqlab, oylik eslatma qilish kerakmi?
53. **O'sadigan pulga avtomatik o'tish**: qorovul maqsadga yetgach ulushning ortiqchasi avtomatik o'sadiganga o'tadi (qarz sharti bajarilsa). Foydalanuvchidan har safar so'rash kerakmi?
54. **Darvozani chetlab o'tish** bir marta qayd etiladi va keyin darvoza ochiq turadi. Har safar (har kiritishda) so'ralsinmi yoki muddatli (masalan, 30 kun) bo'lsinmi?
55. **Narx eslatmasi** — har shanba 09:00. Bozor kuni oilaga qarab farq qiladi; sozlanadigan bo'lsinmi?
56. **«Inflyatsiya ta'siri»** favqulodda zaxira bo'yicha hisoblaydi va taqqoslash uchun savatdagi eng «og'ir» mahsulotni (oylik miqdor × narx) oladi. Mahsulotni foydalanuvchi tanlasinmi?
57. **Foizli daromadni tozalash** (sadaqa qilish) — SPEC «keyingi boblarda» deydi. Hozircha faqat alohida ko'rsatiladi.

## Vazifa 10 dan

58. **Bergan qarz eslatmasi** faqat ilova ichida (bosh ekran kartasi, muddatga 3 kun qolganda). Bildirishnoma (WorkManager) ham kerakmi? Eslatma matni qarzdorga yuboriladigan xabar sifatida (SMS/Telegram) taklif qilinsinmi?
59. **`share_plus` qo'shildi** (tilxat PDF'ini ulashish uchun). PDF vaqtincha ilova keshiga yoziladi va ulashish oynasi orqali beriladi. Ma'qulmi yoki faqat «Fayllarga saqlash» yetarlimi?
60. **Yillik stavka** faqat hisob uchun kiritiladi (haqiqiy narx va jadval). Bank grafigi biroz farq qilishi mumkin (kunlar soni, komissiyalar) — «taxminiy» deb yoziladi. Bank grafigini qo'lda kiritish («o'zim yozaman») yetarlimi?
61. **Qarzga hissa qo'shuvchi a'zolar** (SPEC 2D.4, `DebtContributor`) bu vazifada yo'q — Vazifa 11 (payoff planner) bilan qilinsinmi?
62. **Tilxatdagi imzolar** ilova bazasida (shifrlangan) PNG sifatida saqlanadi; imzolangan tilxatni keyin o'zgartirib bo'lmasligi (muhrlash) kerakmi? Hozir imzoni qayta chizish mumkin.
63. **Summa oynasi butun so'mda**: bank jadvalidagi tiyinli to'lov butun so'mga yuqoriga yaxlitlab taklif qilinadi va saqlashda aynan reja summasiga moslanadi. Tiyinni ham kiritish imkoniyati kerakmi?
64. **Emulyator /data tozalanib qolgan** edi (yangi o'rnatish holati) — v8 → v9 migratsiyasi qurilmadagi haqiqiy bazada emas, faqat migratsiya testlarida tekshirildi.

## Vazifa 11 dan

65. **Yopilgan qarzning oylik to'lovi** planner'da keyingi qarzga **qo'shilmaydi** («qor ko'chkisi» usuli emas) — SPEC 2D.9 bo'yicha u jamg'armaga taklif qilinadi. Planner'da «bo'shagan to'lovni ham keyingi qarzga» varianti kerakmi?
66. **Qo'shimcha to'lov — muddatni qisqartirish** (oylik to'lov o'zgarmaydi). Banklar «oylik to'lovni kamaytirish» variantini ham beradi. Qarzga qarab tanlash kerakmi?
67. **Planner vaqt o'qi**: har qarzning k-oyi — uning k-chi to'lov sanasi (qarzlarning to'lov kunlari har xil bo'lsa — taxminiy). Ma'qulmi?
68. **Darvoza**: «Qarzdan chiqish» rejimi yoqilgan bo'lsa qarz sharti bajarilgan hisoblanadi (foizli qarz bo'lsa ham). Rejim + kamida bitta qo'shimcha to'lov talab qilinsinmi?
69. **Rejim yoqilganda «Kelajagim» ulushi** foiz qoidasida 10 % dan kam bo'lsa 10 % ga ko'tariladi; qat'iy summa qoidasi o'zgartirilmaydi. Rejim o'chirilganda eski ulushga qaytarish kerakmi?
70. **Bo'shagan to'lovni yo'naltirish**: foiz qoidasida daromadga nisbatan butun foizgacha yuqoriga qo'shiladi; daromad yozilmagan bo'lsa avtomatik qilinmaydi (izoh chiqadi). Ma'qulmi?
71. **Qutqarilgan pulni qarzga** — planner'da yopish tartibidagi birinchi qarzga (tanlovsiz). Qarzni tanlash kerakmi?
72. **Sotiladigan buyumlar**: «6 oydan beri ishlatilmayotgan» sharti faqat izohda, tekshirilmaydi. Buyumdan tushgan pul qarzdan ortsa, ortgani yo'naltirilmaydi (faqat qarz qoldig'igacha).
73. **Yelkadosh** faqat ism bilan yoziladi; oila a'zosiga bog'lash (`member_id`) maydoni bor, lekin UI'da hali yo'q.
74. **Vazifa 10 tiyin xatosidan qolgan ma'lumot**: emulyatorda bitta to'lov 945 595 so'm bo'lib yozilgani uchun navbatdagi qatorda 0,97 so'm qoldi. Foydalanuvchiga yuborilgan APK'da bu xato bo'lmagan (tuzatishdan keyin yig'ilgan) — migratsiyada tuzatish shart emas deb hisoblandi.

## Vazifa 12 dan

75. **To'yona jamg'armasi uchun QR** qilinmadi — faqat ulashiladigan matn (plan «matn yoki QR» deydi). QR kerakmi (yangi paket `qr_flutter`)?
76. **Muhokama savollari** — 5 ta qat'iy savol; javoblar yozilmaydi, faqat har bir kattaning belgisi. Javoblarni ham yozib borish kerakmi?
77. **Kishi boshiga narx** mehmonlar soniga ko'paytiriladi; kunlar soni alohida maydon emas («3 kunlik» stsenariy nomida). Kunlarni ham ko'paytiruvchi qilish kerakmi?
78. **Qarzning to'lash muddati** marosim sanasidan keyingi oydan hisoblanadi (sana yo'q bo'lsa — bugundan). Tasdiqlangan marosim qarzi avtomatik «Qarzlar» ro'yxatiga qo'shilsinmi?
79. **Oylik to'lov standarti** — daromadning «Qarzdan chiqish» ulushi (20 %); daromad yo'q bo'lsa foydalanuvchi kiritadi.
80. **Kutilayotgan to'yona** manbasi qarzdek xavfli emas deb hisoblanadi (muhokama talab qilinmaydi), garchi u kelmasligi mumkin. Unga ham ogohlantirish kerakmi?

## Vazifa 13 dan

81. **Usta faqat ikki tomon** uchun (men + bitta sherik). Domen ko'p sherikni qo'llaydi — uchinchi sherik kerakmi?
82. **Shartnomadagi o'zgarishlar** UI'da faqat muddat; ulushlar, hisobot davri, muddat tugashi va nizolar matni servisda bor, lekin ekranda hali yo'q.
83. **Buyout** faqat kapital egalari ulushi bo'yicha (uskuna narxi) va qo'lda to'lov yozish; foydadan avtomatik ajratish Vazifa 14 (venture ledger) bilan bog'lanadi.
84. **Darvozani chetlab o'tish** sheriklikda ham `households.gate_bypassed_at` ga yoziladi (o'sadigan pul bilan umumiy). Alohida qayd kerakmi?
85. **Imzo chizishning oxirgi qadami** (PNG yaratish) widget testida sinalmaydi (soxta vaqt) — qurilmada tekshirildi.
86. **Shablon matnlari** (bandlar) hozircha ilovaning o'z ARB matnlari; yurist va ulamo tekshiruvidan keyin `approved` qilinadi va ogohlantirish yo'qoladi.

## Vazifa 14 dan

87. **Kapital egasi daftarni faqat ko'radi** — MVP'da backend yo'q, shuning uchun kapital egasi (boshqa telefonda) faqat PDF hisobot oladi; o'z telefonida mudaraba kapital egasi sifatida daftar bo'sh qoladi. Kapital egasi o'zi ham yozib borishi kerakmi?
88. **Davrga buyout** = oylik buyout × hisobot davri oylari (oylik — 1, chorak — 3, yil — 12), mehnat egasi ulushidan oshmaydi. Foyda bo'lmagan davrda buyout to'lanmaydi (keyingi davrga ko'chirilmaydi). Ko'chirish kerakmi?
89. **Taqsimlangan ulush** uy daromadiga «Boshqa / naqd / tavakkal» bo'lib yoziladi va avto-ulush (`Kelajagim`) taklifi oddiy daromaddagidek ishlamaydi. Ulush taklifi chiqsinmi?
90. **Stsenariylar** standart ±30 %; pessimistik va optimistik kirimni qo'lda o'zgartirish domen va bazada bor, ekranda hali yo'q.
91. **Chek rasmlari** bazada (1280 px, 70 % sifat); ko'p rasm bazani kattalashtiradi. Hajm chegarasi yoki eksportda alohida fayl kerakmi?
92. **Taklif detektori** natijasi faqat tarixga yoziladi; «qizil» bo'lsa oila a'zolariga ham ko'rsatish yoki eslatish kerakmi?

## Vazifa 15 dan

93. **Til tanlovi saqlanmaydi** — `SettingsController` hali xotirada (Vazifa 3 dan beri TODO): onboarding'da tanlangan til ilova qayta ochilganda o'zbekchaga qaytadi. Shifrlangan bazaga yoki `SecureBlobStore` ga yozish kerak.
94. **Zaxira faylida parol tiklanmaydi** — parol unutilsa nusxa ochilmaydi (ataylab). Parol eslatmasi (hint) yoki oila a'zosi bilan bo'lingan tiklash kodi kerakmi?
95. **Avtomatik davriy zaxira** yo'q — faqat qo'lda. Haftalik eslatma («nusxa olinmaganiga 30 kun bo'ldi») qo'shilsinmi?
96. **Chek rasmlari** zaxira faylida base64 — hajmni ~33 % oshiradi (gzip qisman qaytaradi). Ko'p rasmli daftarda fayl katta bo'ladi (91-savol bilan bog'liq).
97. **Imzo kaliti** hali yaratilmagan: hozirgi APK'lar debug kaliti bilan. Release kalitiga o'tishda telefondagi ilovani o'chirish kerak bo'ladi — oldin zaxira nusxa olinadi (`RELEASE_CHECKLIST` 2).
98. **Sovuq start** emulyatorda 2,0–2,4 s (< 2 s talabi telefonda tekshiriladi). Oshib ketsa: SQLCipher kalitini olish va bazani ochishni qulf ekrani chizilgandan keyinga surish.
99. **Daromad eslatmasi vaqti** qat'iy (20:00 / shanba / maosh kuni 10:00). Foydalanuvchi o'zi tanlashi kerakmi?

## Umumiy vektorlar (v0.8) dan

100. **`money_format` vektorlari** mobil natijasidan yozildi: guruhlash va valyuta oldida bo'linmas bo'sh joy (U+00A0), «soʻm» — U+02BB (DESKTOP_PROMPT misolida oddiy bo'sh joy va `'`). Desktop shu ko'rinishni qabul qiladimi?
101. **`readiness_gate`** kirishi «qorovul oylari» o'ndan birlarda (`reserveMonthsTenths`, 60 = 6,0 oy) va sabab kodlari (`RESERVE_BELOW_TARGET`, `INTEREST_DEBT_WITHOUT_PLAN`), `debt_recovery_split` xato kodlari (`SAVINGS_BELOW_MINIMUM`, `SPLIT_NOT_100_PERCENT`), `CURRENCY_MISMATCH` — mobil tomonidan taklif qilingan; desktop bilan kelishish kerak (CODEOWNERS).
102. **Vektorlarni ulashish** — hozircha mobil repoda (`spec/test-vectors/`). Alohida `baraka-spec` repo yoki submodule'ga ko'chirish desktop loyihasi boshlanganda.
103. **`agreement_completeness.json`** — spec'da aniq case'lar yo'q (faqat xato kodlari); 9A da yoziladi.

## Vazifa 9A dan

104. **Kanonik jurnal yozuvi**: `null` maydonlar kiritilmaydi, manba yozuvi ID si `ref` kalitida. Spec vektorida bu holatlar yo'q — desktop bilan kelishish (`journal_chain.json` ga `ref` va `null` li case qo'shish).
105. **`custody.keeperDeviceId`** (yagona hisob yurituvchi qurilma) saqlanadi, lekin hozir tekshirilmaydi — qurilmalararo almashish (D14 / `.baraka`) bilan birga.
106. **Javoblar JSON'i** (`AgreementAnswers`) `agreement_completeness.json` kirishi sifatida desktop bilan umumiy format bo'ladi — `spec/interchange/` ga sxema sifatida ko'chirilsinmi?
107. **Legacy hujjatlar** (9A dan oldin to'liq imzolangan tilxat / shartnoma) 9 savolsiz o'z kuchida; keyingi versiyada to'ldiriladi. Eslatma chiqarilsinmi?
108. **Bergan qarz** to'lovlari alohida yozilmagan edi — migratsiyada qaytgan jami bitta `LOAN_PAYMENT` (oxirgi o'zgarish sanasi bilan).
109. **Hakam imzosi** ixtiyoriy shart emas: hakam 8-savolda yozilsa imzolovchi bo'ladi va hamma imzolamaguncha `SIGNED` bo'lmaydi.

## Qayta o'rganishdan (2026-10-13) keyin

110. **Zaxira nusxa sxema versiyasiga bog'liq (xavf).** Hozir `schemaVersion` mos kelmasa nusxa rad etiladi (`backup_schema_mismatch`). Foydalanuvchi odatda avval ilovani yangilaydi, keyin nusxadan tiklaydi — shunda eski (v14) nusxa v15 da ochilmaydi. Yechim kerak: (a) eski sxemali nusxani migratsiya zanjiri orqali qabul qilish yoki (b) nusxada sxema versiyasini saqlab, tiklashda shu versiyadan joriyga migratsiya. Bu alohida vazifa; hozircha foydalanuvchiga «eski ilovada tiklang» degan aniq xabar kerak.
111. **[Tuzatildi, 2026-10-15]** Kelishuv moduli presentation qatlamidan ikki yordamchi funksiya oladi** (`percentLabel` — `budget`, `parsePercentBp` — `debts`). Ularni `app/widgets/labels.dart` ga ko'chirish kerak (funksional o'zgarishsiz refaktor).
112. **[Tuzatildi, 2026-10-15]** `lib/features/offers/` va `lib/features/ventures/` bo'sh papkalar** (git'da yo'q, faqat mahalliy). MVP_PLAN arxitekturasidagi bu modullarning kodi `partnerships/` da — hujjat yoki tuzilma bir xil qilinsin, papkalar o'chirilsin.

## Release APK sinovidan (2026-10-13) keyin

113. **[Tuzatildi, 2026-10-14]** Kelishuv, 6-savol (hisob): yozilgan matn yo'qolardi. `question_editor.dart` `_custody` endi `next()` da joriy `_a.custody` dan o'qiydi. Regressiya testi: `test/features/agreements/question_fields_test.dart`.
114. **[Tuzatildi, 2026-10-14]** Kelishuv, 7-savol (chiqish): bitta sessiyada maydonlar bir-birini o'chirardi. `_exit` ham joriy holatdan o'qiydi; bo'sh raqam endi «yo'q» deb saqlanadi. Regressiya testi tuzatishsiz versiyada yiqiladi (tekshirilgan).
115. **[Tuzatildi, 2026-10-14]** Kelishuv, 4-savol (ulush): har sherik ulushi eski nusxadan olinardi (`_profit`). Endi joriy holatdan. Muddat (`_term`) ham shu naqsh bilan tuzatildi. Regressiya testi tuzatishsiz versiyada yiqiladi (tekshirilgan).
116. **[Tuzatildi, 2026-10-14 - qaror: ikkalasi ham]** Tilxat va kelishuv bitta imzo manbaidan (kelishuv imzolari) o'qiydi. Tilxat ekrani kelishuv o'zgarishini kuzatadi va imzo/guvoh qo'shilganda yangilanadi; guvoh endi kelishuv javoblariga yoziladi (tilxatdagi eski alohida guvohlar do'koni ishlatilmaydi). Qurilmada tekshirilishi kerak (yangi qarz).
117. **[Tuzatildi, 2026-10-14]** Sherikchilik: imzolangan tomon qayta imzolay olardi (tugma qolardi, servis rad etmasdi, imzo tasviri jim almashardi). Endi tugma imzolangan qatorda yashirilgan, servis imzoni bazadan tekshiradi va `partnership_already_signed` bilan rad etadi. Testlar: `partnership_test.dart`, `partnership_flows_test.dart`.
118. **[Chiqarib tashlandi]** Bo'sh imzo: «Imzolash» tugmasi chizilmaguncha o'chiq turadi (`signature_pad.dart`, `onPressed: ready ? _done : null`) — bu standart holat. Imzo maydoni ustidagi «Shu yerga barmoq bilan imzo chizing» matni sababni ko'rsatadi. Tuzatish shart emas.
119. **[Tuzatildi, 2026-10-14 - qaror: ha]** Bob sarlavhasidagi "(placeholder)" belgisi `chapters.json` dan olib tashlandi. Tana matnidagi "[Placeholder]" belgilari qoldi (kontent litsenziyasi hal bo'lguncha) - alohida so'raladi.
120. **[Tuzatildi, 2026-10-14 - qaror: Bekor qilish]** Suring bilan o'chirilgan xarajat endi «Bekor qilish» SnackBar'i bilan qaytariladi (`expenses_screen.dart`). «Oxirgisini takrorlash» tasdiqsiz qoladi, uning SnackBar'ida ham «Bekor qilish» bor (SPEC 2B.1).
121. **[Qaror: yuqoriga yaxlitlash, SPEC 2.2 ga yozildi]** Ulush taklifi va qorovul qayta to'ldirish rejasi yuqoriga yaxlitlanadi: 1 000 so'mgacha (katta), butun so'mgacha (kichik). Kasrli so'm (833,34) endi 834 so'm ko'rsatiladi.
122. **[Foydalanuvchi harakati]** Reliz kaliti yaratilib `key.properties` orqali berilishi kerak. Hozirgi APK debug kaliti bilan (RELEASE_CHECKLIST, 2-bo'lim). Kalit yaratish foydalanuvchida.
123. **[Tuzatildi, 2026-10-14 - qaror: alohida joyda]** Buyout to'lovlari sherikchilik ekranida alohida «Buyout toʻlovlari» kartasida ko'rinadi (kassa daftaridan tashqari).
124. **[Tuzatildi / qisman, 2026-10-14]** Zaxira: sinovda bo'sh yukli (`tables: {}`) fayl to'g'ri parol bilan tiklanganda butun baza o'chib ketgan edi (import tekshiruvidan oldin `DELETE`, tranzaksiya commit bo'lgan). Tuzatildi: uy xo'jaligi yo'q yuk rad etiladi («Bu Baraka Dastur zaxira nusxasi emas.»), regressiya testi bor, qurilmada tasdiqlandi. To'liq tiklash (ilova eksporti → 1:1 tiklash) shifrlangan E2E testi bilan tasdiqlandi (`full_e2e_test.dart`, release x64). Qolgan: ilova eksporti faylini qurilmada saqlab, qo'lda tiklash (saqlash joyi emulyatorda yo'q — OPEN 127).

125. **Buyout to'lovi oylik summa belgilanmasdan yoziladi.** Sinovda oylik summa belgilanmasdan 100 000 soʻmlik to'lov saqlandi («Buyout toʻlovlari» kartasida ko'rinadi). Ruxsat berilsinmi (hozir faqat qoldiq bilan cheklangan), yoki avval oylik summa talab qilinsinmi?
126. **Xarajat ro'yxatida tahrirlash yo'q.** Ro'yxat qatori bosilmaydi, faqat suring bilan o'chiriladi (endi «Bekor qilish» bilan). Noto'g'ri summani tahrirlash kerakmi?
127. **Zaxira faylini saqlash joyi.** Eksport faylini faqat ulashish oynasi beradi (emulyatorda Drive/Gmail/Messages/Bluetooth). Haqiqiy telefonda «Yuklab olish» yoki Fayllar'ga saqlash mavjudligini va qo'lda tiklashni tekshirish kerak.

## Vazifa 14A (2026-10-15) dan keyin

128. **[Qaror, 2026-10-15] Ko'rik, hodisa, nizo va bayonnoma — jurnal yozuvlari sifatida.** SPEC 2F.1 dagi `DutyIncident`, `AccountReview` + `ReviewAck`, `ProfitSpikeAlert`, `Dispute`, `ArbiterDecision` alohida jadval o'rniga `journal_entries` ga yangi `JournalKind` turlari sifatida yoziladi. Sabab: append-only va xesh-zanjir bir joyda, sxema v15 o'zgarmadi (migratsiya kerak emas). Shu yo'l tasdiqlanadimi?
129. **«Katta foyda» — reja (plan) maydoni yo'q.** Sheriklikda oylik reja kiritilmagan: A sharti (rejadan 150 %) ishlamaydi, faqat oxirgi 3 yopilgan davr (B sharti, o'rtachadan 200 %). Birinchi uch davrda ogohlantirish chiqmaydi. Sheriklikka reja maydoni qo'shilsinmi?
130. **6-qonun matni — qoralama.** 6-bob («Sheriklik odobi») uchun 6-qonun jumlasi (`assets/content/chapters.json`) qoralama sifatida yozildi; muallif tasdig'i kerak. Bob tanasi hali placeholder (kontent litsenziyasi).
131. **Oilaviy shablonlar — hozircha sarlavha va izoh.** Shablon tanlanganda nomi va izohi qo'yiladi. Javoblar (uy ishlari ro'yxati, pul qayerda turadi, havas chegarasi bilan bog'lanish 2B.3, kengash kuni) oldindan to'ldirilmaydi. Keyingi bosqich.
132. **Oilaviy kelishuv imzosi.** SPEC: imzo o'rniga oiladagi `ADULT` a'zolarning tasdig'i. MVP'da tomonlar oddiy imzo chizadi (kanvas); oila a'zolarini avtomatik imzolovchi qilish keyingi bosqich.
133. **[Tuzatildi, 2026-10-20] Yillik eslatma.** Qurilmada (14A release sinovi) eslatma umuman rejalashtirilmagani topildi. Ikki sabab tuzatildi: (1) `syncAgreementRenewals` autoDispose `agreementsProvider.future` ni tinglovchisiz o'qirdi — natija kelmasdan yopilib, xato jim yutilardi (endi keepAlive `agreementServiceProvider`); (2) `AgreementService.create()` kelishuvning `reviewDate` ini o'rnatmasdi (faqat 9-savol javobida edi). Regressiya testi: `renewal_reminders_test.dart` (ikkala sabab bilan yiqilgani tekshirilgan). Qurilmada `adb reboot` dan keyin ilovaning WorkManager ishlari qaytdi (3 tadan 2 tasi, uchinchisi muddati o'tgan qisqa ish); tuzatishdan keyin release APK'da yillik ish paydo bo'ldi (+334 kun, 2027-09-20 09:00) va `adb reboot`, qayta o'rnatish, `force-stop` dan keyin saqlandi (RELEASE_CHECKLIST, 10-bo'lim). Haqiqiy telefonda bildirishnoma kelishi hali tekshirilmagan.
134. **Ko'rik davomida muzlatish.** Ko'rik ochilganda kesim sanasigacha (shu kun ham) moliyaviy yozuv qo'shilmaydi; bayonnomadan keyin ham shu sanagacha faqat tuzatuvchi yozuv. Shu qoida qoladimi, yoki bugungi kunni ochiq qoldirish kerakmi?
135. **Hakam qarori va yangi versiya.** Qaror kelishuvni `ACTIVE` ga qaytaradi. Matn o'zgarsa — «Yangi versiya» orqali alohida qayta imzolanadi (versiya avtomatik faollashmaydi). SPEC 2F.8 «ACTIVE ga qaytadi» va yangi versiya qayta imzo talab qilishi o'rtasidagi ziddiyatni shu yechim hal qiladi. Tasdiqlaysizmi?
136. **Tilxat imzolovchi rollari (legacy `signers()`).** Tilxat hali `lender`/`borrower` rollarini `loan_signers` da yaratadi; `loanReceiptService.signers()` chaqiruvi shu uchun qoldi (olib tashlansa, imzolovchilar roli `party` bo'lib qoladi). Olib tashlash uchun rollarni migratsiya qilish kerak.
137. **Hakam papkasi — davr filtri.** Papkada hozir kelishuvning butun jurnali (barcha moliyaviy yozuvlar va bayonnomalar) bor; SPEC 2F.8 dagi «tegishli davrlar» bo'yicha filtr qo'shilmagan. Qo'shilsinmi?

## Vazifa 14B (7-qonun, 2026-10-20) dan keyin

138. **7-qonun jumlasi — tasdiq kerak.** SPEC 2G sarlavhasi va `chapters.json` dagi 7-qonun jumlasini loyiha jamoasi yozgan: «Tekshirmagan ishga pul tikma… avval oilaviy zaxira, keyin hunar». Yakuniy tahrir foydalanuvchida.
139. **Zakot qaysi qonunda?** SPEC 4.3 da `Asset` abstraksiyasi zakot uchun ajratilgan. 7-qonun zakot haqida emas — abstraksiya zaxirada qoladi. Zakot qaysi bobda bo'lishi aniqlansin.
140. **Kafolat bitta o'zi qizil.** Hojining qoidasi «bitta belgi — hushyor, ikkitasi — qoch», lekin 2E.5 bo'yicha kafolatli foyda o'zi ribo yoki firibgarlik (qizil). Hozir umumiy baho ikkalasining eng og'iri: faqat kafolat bo'lsa ham qizil (vektor sc-006). Shu qoladimi?
141. **«To'xta, maslahatlash» hamma takliflarga.** 24 soat va maslahatchi summadan qat'i nazar har bir «pul qo'yaman» qaroriga qo'llanadi. Kichik summalar uchun chegara (masalan, favqulodda zaxirasining ma'lum ulushidan kam) kerakmi?
142. **Piramida modeli soddalashtirilgan.** Har ishtirokchi bir xil `k` odam olib keladi, aholi `N` da to'xtaydi; faqat ta'limiy. Haqiqiy sxemalardagi (yarim yo'lda chiqib ketganlar, qayta kirganlar) holatlar hisobga olinmaydi.
143. **Dollardagi jamg'arma.** «Katta summa» ekrani dollarni foydalanuvchi kiritgan kurs bilan so'mga aylantirib favqulodda zaxiraga qo'yadi (internetsiz, kurs qo'lda). Dollarni dollarda alohida aktiv (`FOREIGN_CURRENCY`, SPEC 4.3) sifatida saqlash kerakmi?
144. **Hunar shablonlari.** Hozircha bitta: payvandlash ustaxonasi. Boshqa hunarlar (tikuvchilik, pazandachilik, ta'mirlash) uchun shablon qo'shilsinmi? CAPEX narxlari o'ylab topilmaydi — foydalanuvchi yozadi.
145. **Desktop: 4 yangi umumiy suite.** `scam_signals`, `promised_return`, `pyramid_levels`, `lump_sum_split` (`spec/test-vectors/`, `DESKTOP_PROMPT.md` 5.3). Desktop runner noma'lum suite'da yiqiladi — desktop jamoasi runner qo'shishi kerak (5.4: vektor o'zgarishiga ikkala egasining ma'quli).
146. **7-bob vazifalari mavjud triggerlar bilan.** `OFFER_CHECKED`, `EMERGENCY_TARGET_SET`, `VENTURE_IDEA_CREATED` — 5-bob bilan umumiy. Har bob faqat ochiq haftada belgilanadi; agar alohida trigger (masalan, `SCAM_CHECK_FLEE`) kerak bo'lsa — aytilsin.
147. **[Hal qilindi, 2026-10-23] Homiy va reklama.** Ilova hech qanday investitsiya platformasi, kompaniya yoki homiyni ko'rsatmaydi va tavsiya etmaydi (SPEC 3-bo'lim).
148. **Yillik eslatma qoralamaga ham.** `syncAgreementRenewals` holati `closed` bo'lmagan har kelishuvga (qoralama ham) `reviewDate` dan 30 kun oldin eslatma qo'yadi; bosh ekrandagi «Yaqinlashayotgan ko'rik / yangilash» kartasi ham qoralamani sanaydi. Imzolanmagan qoralama uchun «yangilang» eslatmasi kerakmi yoki faqat `signed | active | inDispute`? Shuningdek eslatma yangi kelishuv yaratilganda emas, keyingi ilova ochilishida rejalashtiriladi.

## Vazifa 14C (8-qonun, 2026-10-27) dan keyin

149. **Kunlik jismoniy chegara standarti.** Kalkulyatorda 12 soat (foydalanuvchi o'zgartiradi). Bu tibbiy me'yor emas, faqat boshlang'ich qiymat. Boshqa standart (masalan, 10 soat) kerakmi?
150. **Soat qiymati oila a'zosi bo'yicha.** Jadvallarda `memberId` bor, lekin UI hozircha bitta (uy egasi) hisobini yuritadi. Er-xotin ikkalasi ishlasa, har biri uchun alohida soat qiymati va maqsad kerakmi?
151. **Qoplanish taxmini.** O'qish vaqti joriy soat qiymati bo'yicha baholanadi (`timeCost`). Oylik daqiqa — oxirgi hisobdan. Matn shartli («soatingiz shunga yetsa…») va va'da emas. Qoplanishni maqsad ekranida ko'rsatish yetarlimi yoki bosh ekranga ham chiqarilsinmi?
152. **Kurs tekshiruvi savollari.** 7 savol 2G.1 besh belgisiga moslab yozildi. «Daromad kafolati» bitta o'zi qizil emas, sariq (2G.1 qoidasi). Taklif tekshiruvida esa kafolatli foyda darhol qizil (2E.5). Kurs uchun ham kafolat darhol qizil bo'lsinmi?
153. **Kurs tekshiruvi va `OFFER_CHECKED`.** Kurs tekshiruvi 7-bobning «taklifni tekshiring» vazifasini belgilamaydi (alohida modul). Kerak bo'lsa, ulanadi.
154. **Diniy matnlar (8-bob).** Bilim olish va ishni puxta qilish haqidagi oyat va hadislar `PENDING` blokda — hozircha matnsiz. Ulamo tekshiruvi va manbalar kerak (SPEC 3-bo'lim).
155. **Desktop: 3 yangi umumiy suite.** `hourly_value`, `skill_payback`, `course_check` (`DESKTOP_PROMPT.md` 5.3). Desktop runner noma'lum suite'da yiqiladi — desktop jamoasi runner qo'shishi kerak.
156. **Mavjud «Hunarlar» (`Skill`, 5-qonun) bilan bog'lash.** O'qish maqsadi hozircha erkin matn. Uni «Hunardan ishga» dagi hunar ro'yxatiga bog'lash kerakmi (masalan, o'rganilgan mahoratdan keyin g'oya yozish)?

## Nom va mustaqil kontent (2026-10-23)

- **Android `applicationId` yangilandi: `uz.barakadastur.app`** (Play identifikatori; birinchi yuklashdan keyin o'zgartirib bo'lmaydi). Oqibat: telefonga oldin o'rnatilgan «Baraka daftari» yangilanmaydi — yangi ilova alohida o'rnatiladi va eski ma'lumotlar o'z-o'zidan ko'chmaydi (kerak bo'lsa, eski ilovadan zaxira nusxa olib, yangisiga tiklash). Ichki nomlar o'zgarmadi: Kotlin `namespace` `uz.barakadaftari.app`, Dart paketi `baraka_daftari`, Tauri `identifier` `uz.barakadaftari.desktop` (desktop ma'lumotlar papkasi), keyring `BarakaDaftari`, `.baraka` kengaytmasi, crate nomlari — ular foydalanuvchiga ko'rinmaydi.
- **Qolgan mahsulot atamalari.** «Kelajagim», «Kimning puli?», «Juma shirinligi», «Hunardan ishga», «Narx daftari», «Daftar sahifasi», 9 savolli kelishuv, besh xavf belgisi, 70/20/10 — umumiy so'zlar va g'oyalar sifatida qoldi. Qissa matnlari bilan solishtirib, yana qaysi biri aynan qissadan ekanini muallif matnlarini bilgan odam ko'rib chiqishi kerak.
- **Kelishuv ustasidagi maslahat matnlari.** Mobil ilovada 9 savolning izohlari (`agQ*Hint`) va kelishuv ekranidagi «Maslahat: …» (`agAdvisorTip`) o'z so'zlarimiz bilan; bob ichidagi maslahat bloki «Maslahatchi» belgisi bilan. Iqtibos ko'rinishidagi iboralar («…») bittalab tekshirildi; matnlarni asl qissani bilgan odam yana bir bor ko'rib chiqishi kerak.
- **«Maslahatchi» va disklеymer.** Ilova «Moliyaviy maslahat emas» deydi; «Maslahatchi» obrazi ta'limiy savollar beradi, shaxsiy tavsiya bermaydi. Nomini «Murabbiy» ga almashtirish kerakmi — qaror kutilmoqda.
- **«Baraka» savdo belgisi.** Google Play'da moliya toifasida «baraka» (Baraka Financial Limited, investitsiya ilovasi) bor. «Baraka Dastur» nomida ham asosiy so'z «Baraka» — adashtirish va savdo belgisi xavfi qoldi. Play'ga chiqishdan oldin yurist (savdo belgisi qidiruvi) ko'rib chiqishi kerak; foydalanuvchi xavfni bilgan holda shu nomni tanladi (2026-10-23).
- **Ichki nomlar.** Dart paketi `baraka_daftari`, Kotlin `namespace` `uz.barakadaftari.app`, zaxira formati `baraka-daftari-backup` foydalanuvchiga ko'rinmaydi va o'zgartirilmadi (o'zgartirish yuzlab importlarni va eski zaxira mosligini buzadi). APK ichida Activity nomi `uz.barakadaftari.app.MainActivity` bo'lib qoladi. O'zgartirish kerakmi?
- **Logotip tasdig'i.** «B» + bug'doy boshog'i (ikki ilovada bir xil). Foydalanuvchi ko'rib, tasdiqlashi yoki o'zgartirish so'rashi kerak; Play banneridagi shior «Ribosiz shaxsiy moliya» — vaqtinchalik.

## Mualliflik himoyasi (2026-10-25)

- **Muallif ismi.** LICENSE, «Ilova haqida» va shartnoma loyihasida taxallus «JurabekM» ishlatilgan (foydalanuvchi tanlovi). Huquqiy dalil uchun pasport bo'yicha to'liq ism kuchliroq — shartnomada `[pasport bo'yicha F.I.Sh.]` joyi qoldirilgan.
- **[Hal qilindi, 2026-10-27] Taqiqlangan iboralar ro'yxati.** Endi faqat xesh ko'rinishida. `baraka-dastur-mobile` tarixi bitta parentsiz commit'ga qisqartirildi (force-push). Eski 4 snapshot (`f9a377f5` … `5eed45dd`) va GitHub server hodisalari (branch yaratilishi 2026-10-24 09:45 UTC) mualliflik arxivida saqlandi. GitHub uzilgan commitlarni SHA bo'yicha bir muddat ko'rsatishi mumkin. Butunlay o'chirish uchun GitHub Support'ga murojaat kerak.
- **Boshqa ommaviy branch'larda ochiq nomlar (2026-10-27).** `JurabekM/Myrep` ning oxirgi holatida tashqi manba nomlari hali bor:
  - `claude/baraka-daftari-v3-70d513` (desktop): `crates/domain/src/content.rs`, `spec/content/chapters.json`, `docs/SPEC.md`, `docs/MVP_PLAN.md`, `docs/DESKTOP_PROMPT.md`, `docs/OPEN_QUESTIONS.md`;
  - `claude/baraka-daftari-d6-inline`: `docs/CHANGELOG.md`, `docs/OPEN_QUESTIONS.md`;
  - `master`: `baraka_oilasi/docs/*`, shuningdek boshqa loyihalar (bir qismi tasodifiy moslik bo'lishi mumkin).
  
  Bu branch'larning tarixida ham iz bo'lishi mumkin. Hozircha tegilmadi: ularni tahlil qilib tozalash — alohida qaror.
- **Ommaviy repo.** `JurabekM/Myrep` PUBLIC: kod LICENSE bilan ham ko'rinadi va nusxa olish oson. Mobil kodni yopiq repoga ko'chirish yoki repoga LICENSE'ni push qilish — foydalanuvchi qarori.
- **Demo muddati.** Muddat qurilma sanasiga tayanadi (internet yo'q): telefon soatini orqaga surib aylanib o'tish mumkin. Asosiy himoya — alohida paket, debug imzo va ko'rinadigan «DEMO» yozuvi.
- **[Hal qilindi] Demo qurilmada.** Alohida `Baraka_Demo` AVD'da sinaldi (RELEASE_CHECKLIST 13). Umumiy emulyator 94 % to'la — boshqa loyihalar ilovalari; Baraka sinovlari uchun `Baraka_Demo` AVD (o'chirish — foydalanuvchi qarori).
- **Demo ikonkasi.** Hozir haqiqiy ilova bilan bir xil ikonka (farq — nomdagi «DEMO» va ilova ichidagi lenta). Ikonkaga ham «DEMO» belgisi kerakmi?
- **Rasmiy ro'yxatdan o'tkazish.** EHM dasturi sifatida Adliya vazirligi huzuridagi Intellektual mulk agentligida ro'yxatdan o'tkazish tartibi va narxi aniqlanmagan; `release/mualliflik-2026-10-25/` arxivi ariza uchun tayyor.
