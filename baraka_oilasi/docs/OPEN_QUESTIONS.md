# OCHIQ SAVOLLAR

> Har bir savolning egasi, holati va qaysi vazifani to'sib turgani ko'rsatiladi.
> Qaror chiqqach: «Qaror» qatori to'ldiriladi, tegishli SPEC yoki `BARAKA_OILASI.md` yangilanadi, holat `HAL QILINDI` ga o'tadi.
> Prefikslar: **P** — mahsulot, **M** — oila va maxfiylik, **D** — diniy (ulamo), **Y** — yuridik (yurist), **T** — texnik.

## Mahsulot egasi

### OQ-P1. «To'yona daftari»
- **Masala:** to'yona sovg'a emas, qaytariladigan ijtimoiy majburiyat. `EXPECTED_GIFTS` manbasi aslida kelajakdagi yashirin majburiyat.
- **Taklif:** marosim rejalovchisiga «To'yona daftari» (berilgan/olingan, kimga, qancha) qo'shish. Olingan to'yona kelajakdagi kutilayotgan majburiyat sifatida ko'rsatiladi (foizsiz, ayblovsiz).
- **To'sadi:** U10 (to'liq). **Holat:** OCHIQ.
- **U10 da qilingan (vaqtinchalik):** daftar yo'q; `EXPECTED_GIFTS` manbali qator bo'lsa, marosim kartasida «kutilayotgan to'yona — kelajakda qaytariladigan majburiyat» ogohlantirishi chiqadi (`CeremonyDto.giftsWarning`), smetada manba alohida ko'rsatiladi. Qaror kerak: daftar marosimga bog'lanadimi yoki alohida bo'limmi; olingan to'yona qarzlar yukiga (`debt_load`) kiradimi.

### OQ-P2. Bitta ilova, uchta makon
- **Masala:** uchta mahsulot alohida ilova bo'ladimi yoki bitta ilova ichidagi makonlarmi?
- **Taklif:** bitta «Baraka» ilovasi, uchta makon (`BARAKA_OILASI.md` 2.2). Brend sifatida uch nom saqlanadi.
- **To'sadi:** Y5. **Holat:** TAVSIYA QABUL QILINDI (tasdiqlash kerak).

### OQ-P3. «Qutqarilgan pul» bazaviy davri
- **Masala:** foydalanuvchi xarajatni qanchalik to'liq yozsa, shuncha ko'p havas ko'rinadi va «qutqarilgan» summa kamayadi (teskari rag'bat).
- **Taklif:** bazaviy davr = audit oyi emas, balki «to'liq yozilgan dastlabki 4 hafta».
- **To'sadi:** U5. **Holat:** OCHIQ.

### OQ-P4. Streak'da «dam haftasi»
- **Masala:** notekis daromadli foydalanuvchida (taksichi) bitta bo'sh hafta butun streakni yo'qqa chiqaradi.
- **Taklif:** har 4 haftada 1 ta «dam haftasi» streakni uzmaydi.
- **To'sadi:** U1. **Holat:** OCHIQ.

### OQ-P5. Qorovul pul maqsadi va qiziqishni yo'qotish xavfi
- **Masala:** 6 oylik zaxira o'rta segment uchun ~3 yil yig'iladi. Shu davrda 5-qonun qulflangan turadi.
- **Taklif:** 3 oylik milestone'da «Hunardan ishga» rejalovchisi (pul kiritmasdan, faqat reja) ochiladi; kapital kiritish 6 oyda.
- **To'sadi:** U6. **Holat:** OCHIQ.

### OQ-P6. Bob ochilish qoidasi
- **Masala:** `uy/SPEC.md` 2C.6 («3 haftada 2 tasi») va `uy/MVP_PLAN.md` V6 («2 vazifa + 7 kun») har xil; 1.1-bo'limdagi «har juma yangi bob» ham bunga zid.
- **Taklif:** `uy/MVP_PLAN.md` V6 qoidasi standart, sozlanadi.
- **To'sadi:** U3. **Holat:** OCHIQ.

### OQ-P7. Mahsulot ta'sirini o'lchash
- **Masala:** offline va telemetriyasiz ilova odatlarni o'zgartiryaptimi, buni qanday bilamiz? (`uy/SPEC.md` 2C.4 dagi «analitikada qayd etiladi» bilan zid.)
- **Taklif:** ixtiyoriy, anonim, foydalanuvchi o'zi yuboradigan oylik «odat hisoboti» + test guruhi bilan intervyular.
- **To'sadi:** U15. **Holat:** OCHIQ.

### OQ-P8. «To'xta va o'yla»: oylik qarz yukining chegarasi va ta'rifi
- **Masala:** SPEC 2D.6 yukni so'raydi, lekin chegara bermaydi. Oylik yuk qanday hisoblanadi?
- **Hozirgi standart (U8):** yuk = shu oy davridagi reja to'lovlari / oylik daromad (oxirgi 3 to'liq oy o'rtachasi, u 0 bo'lsa — shu oy). Yangi qarz uchun: joriy yuk + yangi rejaning o'rtacha to'lovi. **30% dan oshsa** — ogohlantirish (`LOAD_HIGH_BP`). Taqiqlamaydi.
- **Savol:** 30% to'g'rimi (bank amaliyotida 50% gacha)? Birinchi to'lovi keyingi oyda bo'lgan qarz shu oy yukida 0 ko'rinadi — «keyingi 30 kun» ta'rifi yaxshiroqmi?
- **To'sadi:** U9 (DEBT_RECOVERY rejimi taklifi). **Holat:** OCHIQ (U9 30% bilan qilindi; o'zgartirish — bitta konstanta).

### OQ-P9. Bank qarzida muddatidan oldingi to'lov: muddatni qisqartirishmi yoki to'lovni kamaytirishmi?
- **Hozirgi standart (U9):** «muddatni qisqartirish» (oylik to'lov o'zgarmaydi) — `BARAKA_OILASI.md` 5.8 bo'yicha. Komissiya — qo'shimcha to'lovdan bp (`prepayment_fee_bp`), ustiga qo'shiladi.
- **Savol:** O'zbekiston banklarida ko'pincha mijoz tanlaydi. Har bir qarzga «to'lovni kamaytirish» variantini qo'shamizmi? Komissiya qat'iy summa bo'lgan holatlar uchrayaptimi?
- **To'sadi:** keyingi bank integratsiyasi. **Holat:** OCHIQ.

## Oila va maxfiylik

### OQ-M1. Bitta qurilmada rozilik
- **Masala:** «har bir ADULT tasdiqlaydi» oqimi bitta telefonda rozilik teatriga aylanishi mumkin. Ko'p avlodli xonadonlarda qaror qiluvchi har doim `ADULT` emas (kelin, boshqa xonadondagi ota-ona).
- **Taklif:** shaxsiy PIN bilan tasdiq standart; «kengash a'zosi» alohida rol.
- **To'sadi:** U4, U10. **Holat:** OCHIQ.

### OQ-M2. Shaxsiy jamg'arma
- **Masala:** Nilufarning «qora kun» uchun yashirin zaxirasi. Oilaviy shaffoflik moliyaviy zo'ravonlik sharoitida ayolning xavfsizlik zaxirasini yo'q qilishi mumkin.
- **Taklif:** a'zoning shaxsiy PIN bilan himoyalangan, boshqalarga ko'rinmaydigan jamg'armasi (`visibility = PRIVATE`). Sxemada maydon hozirdan bor.
- **To'sadi:** U1 (UI), U4. **Holat:** OCHIQ.

## Ulamo uchun

### OQ-D1. Mudorabada zararni keyingi foydadan qoplash
- **Savol:** davr zarari kapital egasiga yozilgandan keyin, keyingi davr foydasi avval kapitalni tiklashga ketadimi?
- **Misol:** 1-oy zarar 2 mln, 2-oy foyda 3 mln, ulush 50/50. Spec bo'yicha: ishchi 1,5 mln. Klassik qoida bo'yicha: 2 mln kapitalga, qolgan 1 mln → har biriga 0,5 mln.
- **To'sadi:** U11, U12. **Holat:** OCHIQ.

### OQ-D2. Musharakada ishlamaydigan sherik
- **Savol:** Hanafiy mazhabida ishlamaydigan sherikning foyda ulushi kapital ulushidan oshmasligi kerakmi? Validator sifatida qo'shiladimi?
- **To'sadi:** U11. **Holat:** OCHIQ.

### OQ-D3. Qarz bo'yicha jarima va valyuta
- **Savol:** (1) tilxatdagi «bajarilmasa» bandida kreditor foydasiga pul jarimasi taqiqlanadimi (validator)? (2) dollarda olingan qarz so'mda qaytarilsa, qaysi kurs bo'yicha joiz? Standart: qaytarish valyutasi = qarz valyutasi.
- **To'sadi:** U8. **Holat:** OCHIQ.

### OQ-D4. Tayyorgarlik darvozasi: «yoki reja bor»
- **Savol:** foizli qarzi bor, lekin chiqish rejasi bor foydalanuvchi sheriklikka kapital bera oladimi? (`DEBT_RECOVERY` dagi 20% qarzga ketishi kerak.)
- **Taklif:** foizli qarz bor ekan, kapital kiritish yopiq; foizsiz qarz va reja bo'lsa — ochiq.
- **To'sadi:** U6. **Holat:** OCHIQ.

### OQ-D5. Muzoraa, nasiya narxi, savdo mollari zakoti
- **Savollar:** (1) nasiyada narxni oldindan qotirib sotish (bay' muajjal) va kechikish uchun ustama taqiqi; (2) savdo mollari zakotini bozor narxida baholash; (3) xodim bilan foyda ulushi asosidagi kelishuv; (4) konsignatsiya.
- **To'sadi:** K0. **Holat:** OCHIQ.

## Yurist uchun

### OQ-Y1. Qarz shartnomasi
- **Savol:** Fuqarolik kodeksi bo'yicha fuqarolar o'rtasidagi qarz sukut bo'yicha foizli hisoblanadimi? Qaysi summadan yozma shakl majburiy? Agar sukut bo'yicha foizli bo'lsa, tilxatda «foizsiz» bandi majburiy.
- **To'sadi:** U8. **Holat:** OCHIQ.

### OQ-Y2. Ekranda chizilgan imzo
- **Savol:** ekranda chizilgan imzoli PDF qanday dalil kuchiga ega (ERI emas)? Qaysi summadan «chop etib qo'lda imzolash» standart bo'lishi kerak?
- **To'sadi:** U7, U8. **Holat:** OCHIQ.

### OQ-Y3. Kasb-kor: mijozlarning shaxsiy ma'lumotlari
- **Savol:** nasiya olgan mijozlarning ism va telefonlarini saqlaganda do'kondor operator hisoblanadimi? Qanday rozilik shakli kerak?
- **To'sadi:** K0, K4. **Holat:** OCHIQ.

### OQ-Y4. Sheriklik shartnomasi shakli
- **Savol:** mudoraba/musharaka kelishuvi Fuqarolik kodeksidagi oddiy shirkat (birgalikdagi faoliyat) shartnomasiga qanday mos keladi?
- **To'sadi:** U11. **Holat:** OCHIQ.

## Texnik

### OQ-T1. APK hajm byudjeti
- **Masala:** typst, SQLCipher va shriftlar bilan arm64 yuklanadigan hajm ≤ 40 MB bo'ladimi?
- **Qaror qachon:** Y6 dan keyin o'lchanadi; oshsa — shriftlarni qisqartirish yoki typst'ni alohida yuklanadigan modul qilish (ADR).
- **Holat:** OCHIQ.

### OQ-T2. `tauri-specta` barqaror versiyasi
- **Masala:** barqaror versiya bo'lmasa, RC'ni qotirib ishlatish ADR bilan qilinadi.
- **Qaror:** `=2.0.0-rc.25` qotirildi (ADR-0002). Barqaror versiya chiqqanda yangilanadi. **Holat:** HAL QILINDI.

### OQ-T3. Sana-vaqt crate'i
- **Masala:** `time` + `time-tz` yoki `chrono` + `chrono-tz`.
- **Qaror:** `chrono` + `chrono-tz` (ADR-0002). **Holat:** HAL QILINDI.

### OQ-T4. Android platforma siri va avto-qulf
- **Masala:** `BarakaCore` (FRB) platforma sirini Dart orqali bayt sifatida oladi. Kotlin `PlatformSecretApi` uni Keystore bilan wrap qilib saqlashi va har chaqiruvdan keyin xotiradan tozalashi kerak; Rust tomoni baytlarni `zeroize` qiladi.
- **Qaror qachon:** Android Y4(b). **Holat:** OCHIQ.

### OQ-T5. Desktop E2E (tauri-driver)
- **Masala:** hozircha haqiqiy ilova Xvfb + xdotool bilan qo'lda tekshirildi (sozlash → daromad → ulush → qulf). Windows'da `tauri-driver` + WebdriverIO bilan avtomatlashtirish kerak.
- **Qaror qachon:** U15. **Holat:** OCHIQ.
