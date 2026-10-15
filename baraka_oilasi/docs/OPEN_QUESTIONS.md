# OCHIQ SAVOLLAR

> Har bir savolning egasi, holati va qaysi vazifani to'sib turgani ko'rsatiladi.
> Qaror chiqqach: «Qaror» qatori to'ldiriladi, tegishli SPEC yoki `BARAKA_OILASI.md` yangilanadi, holat `HAL QILINDI` ga o'tadi.
> Prefikslar: **P** — mahsulot, **M** — oila va maxfiylik, **D** — diniy (ulamo), **Y** — yuridik (yurist), **T** — texnik.

## Mahsulot egasi

### OQ-P1. «To'yona daftari»
- **Masala:** to'yona sovg'a emas, qaytariladigan ijtimoiy majburiyat. `EXPECTED_GIFTS` manbasi aslida kelajakdagi yashirin majburiyat.
- **Taklif:** marosim rejalovchisiga «To'yona daftari» (berilgan/olingan, kimga, qancha) qo'shish. Olingan to'yona kelajakdagi kutilayotgan majburiyat sifatida ko'rsatiladi (foizsiz, ayblovsiz).
- **To'sadi:** U10. **Holat:** OCHIQ.

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
- **Qaror qachon:** Y1. **Holat:** OCHIQ.

### OQ-T3. Sana-vaqt crate'i
- **Masala:** `time` + `time-tz` yoki `chrono` + `chrono-tz`.
- **Qaror qachon:** Y1 (ADR-0002). **Holat:** OCHIQ.
