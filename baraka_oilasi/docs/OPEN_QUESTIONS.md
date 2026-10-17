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

### OQ-P10. Ko'rik va hodisalar boshqa tomonning qurilmasida
- **Masala:** U13 da ko'rik belgilari (`AGREE` / `OBJECT`) va «bajara olmayapman» xabari hisob yurituvchining qurilmasida yoziladi (jurnalni faqat shu qurilma yuritadi, 6.6). Ikkinchi tomon belgini o'zi, o'z qurilmasida qo'yishi kerakmi?
- **Taklif:** U14 sinxronizatsiyasida ikkinchi tomon imzolangan «belgi paketi»ni yuboradi, hisob yurituvchi uni jurnalga qo'shadi.
- **U14 dan keyin:** `.baraka` transporti tayyor, lekin jurnalga faqat hisob yurituvchi qurilma yozadi — boshqa qurilma jurnalga yozgan fayl `NOT_KEEPER_WRITE` bilan to'xtatiladi. «Belgi paketi» alohida yozuv turi sifatida qo'shilishi kerak (jurnalga emas, keyin yurituvchi tasdiqlaydi).
- **To'sadi:** ikkinchi tomonning o'z qurilmasida belgi qo'yishi. **Holat:** OCHIQ.

### OQ-P11. «Katta foyda»: reja manbai
- **Hozirgi standart (U13):** reja — shartnomadagi buyout'dagi «kutilgan davr foydasi»; buyout bo'lmasa, faqat tarix (oxirgi 3 davr o'rtachasidan 200%). Chegaralar: rejadan 150%, tarixdan 200% (`SpikePolicy`).
- **Savol:** shartnomaga alohida «kutilgan oylik foyda» maydoni qo'shamizmi (buyout'siz sheriklik uchun ham)? «Hunardan ishga» stsenariysidagi «o'rtacha» foyda reja bo'la oladimi?
- **To'sadi:** — (ishlaydi). **Holat:** OCHIQ.

### OQ-P12. U3–U7 bajarilmagan; yakuniy E2E qisqartirilgan
- **Masala:** ish rejasida U3 (kontent dvigateli), U4 (havas chegarasi, vidjet, oila kengashi), U5 (obunalar, konvertlar, «Qutqarilgan pul», CSV), U6 (qorovul pul, narx daftari, darvoza, ribo filtri) va U7 ning UI qismi hali qilinmagan — ishlar U8 dan boshlangan. Shuning uchun D15 / V15 dagi Anvar ssenariysining «havas chegarasi → obuna bekor qilish → qutqarilgan pul → darvoza ochilishi» qismlari E2E'da yo'q (mahsulot egasi qarori, 2026-10-16: U15 mavjud funksiyalar bilan).
- **Taklif:** keyingi sessiyalarda U3–U7 (har biri a/b/c), keyin `02-anvar` E2E to'liq ssenariyga kengaytiriladi.
- **To'sadi:** 1-reliz. **Holat:** OCHIQ.

### OQ-P13. Bosh sahifa eslatmalari: chegaralar
- **Hozirgi standart (U15):** kunlik naqd — bugun daromad yozilmagan bo'lsa; buyurtma bo'yicha — 14 kun jimlik; oylik maosh — oy boshlanish kunidan 3 kun ichida, shu davrda daromad yo'q bo'lsa; zaxira nusxa — oxirgi to'liq eksport (yoki xonadon yaratilganidan) 30 kun. Eslatmalar faqat bosh sahifada (tizim bildirishnomasi — `tauri-plugin-notification` — hali yo'q).
- **Savol:** chegaralar to'g'rimi? Kunlik eslatma kechqurun (masalan, 18:00 dan) chiqsinmi? Tizim bildirishnomasi kerakmi?
- **To'sadi:** — (ishlaydi). **Holat:** OCHIQ.

### OQ-P14. Onboarding'dan keyin oila a'zolarini o'zgartirish
- **Masala:** a'zolar faqat onboarding'da qo'shiladi; keyin qo'shish, nomini o'zgartirish yoki «katta/bola» rolini almashtirish (bola katta bo'ldi) uchun ekran yo'q.
- **Taklif:** «Sozlamalar → Oila» bo'limi; rol o'zgarishi kelishuv roziliklariga ta'sir qiladi (OQ-M1 bilan birga).
- **To'sadi:** — . **Holat:** OCHIQ.

## Kasb-kor (mahsulot egasi uchun; `docs/kasbkor/SPEC.md`)

### OQ-K1. Tannarx usuli
- **Taklif:** standart — o'rtacha tortilgan; FIFO — tovar bo'yicha ixtiyoriy (muddati bor tovarlar). Ikkalasi ham vektor bilan (`kk_cogs`).
- **Savol:** kichik do'kon uchun bitta usul yetarlimi yoki tanlov kerakmi? «Asosiy tovarlar» rejimi (20–30 pozitsiya) standart bo'lsinmi?
- **To'sadi:** K5. **Holat:** OCHIQ.

### OQ-K2. Egasi maoshi Uy makonida qanday daromad?
- **Masala:** `BARAKA_OILASI.md` 4.6 da «egasi maoshi Uy'da `MOL | TAVAKKAL`» deyilgan. Lekin maosh — egasining mehnati uchun (`TER`), foyda ulushi esa kapital va tavakkal uchun (`MOL` / `TAVAKKAL`).
- **Taklif:** maosh → `TER`; «Hisob kuni»da egasiga foyda ulushi o'tkazilsa → `MOL`. 4.6 matni shunga moslanadi.
- **Vaqtinchalik qaror (K1):** kodda maosh → `TER` (`kasbkor.rs`, `SALARY_SOURCE_TYPE` — bitta joy). `BARAKA_OILASI.md` 4.6 matni (3-bo'lim emas) mahsulot egasi tasdig'idan keyin moslanadi.
- **To'sadi:** K3 (foyda ulushi). **Holat:** VAQTINCHA YECHILGAN — tasdiq kutilmoqda.

### OQ-K3. Soliq zaxirasi qoidasi
- **Taklif:** egasi o'zi kiritadi: baza (tushum yoki foyda) va foiz yoki qat'iy summa. Ilova rejim va stavka tavsiya qilmaydi («soliq maslahati emas»).
- **Savol:** onboarding'da shu qadam bo'lsinmi yoki birinchi «Hisob kuni»da?
- **To'sadi:** K3. **Holat:** OCHIQ.

### OQ-K4. «Muzlagan tovar» chegarasi
- **Taklif:** oxirgi sotuvdan 90 kun, tovar bo'yicha o'zgartiriladi. Muzlagan tovar qayta tiklash narxida ko'rsatiladi.
- **To'sadi:** K5. **Holat:** OCHIQ.

### OQ-K5. «O'z mehnati bahosi»
- **Masala:** haqiqiy foyda egasi kiritgan bahoga bog'liq. Juda past yozilsa — tashxis yo'qoladi, juda baland — doim «zarar».
- **Taklif:** egasi kiritadi; ilova savol bilan yordam beradi («shu ishni yollanma usta qancha oladi?»), mintaqaviy narx bazasi yo'q.
- **To'sadi:** K2. **Holat:** OCHIQ.

### OQ-K6. Kengayish darvozasi chegaralari
- **Taklif:** zaxira ≥ 3 oylik operatsion xarajat; oxirgi 3 «Hisob kuni»da haqiqiy foyda > 0; 90+ kunlik nasiya ≤ 10%; foizli qarz yo'q yoki reja bilan; yozilgan kengayish rejasi.
- **Savol:** chegaralar to'g'rimi? Mavsumiy biznes (masalan, to'y libosi) uchun «3 oy» qanday hisoblanadi?
- **To'sadi:** K7. **Holat:** OCHIQ.

## Oila va maxfiylik

### OQ-M1. Bitta qurilmada rozilik
- **Masala:** «har bir ADULT tasdiqlaydi» oqimi bitta telefonda rozilik teatriga aylanishi mumkin. Ko'p avlodli xonadonlarda qaror qiluvchi har doim `ADULT` emas (kelin, boshqa xonadondagi ota-ona).
- **Taklif:** shaxsiy PIN bilan tasdiq standart; «kengash a'zosi» alohida rol.
- **To'sadi:** U4, U10. **Holat:** OCHIQ.

### OQ-M2. Shaxsiy jamg'arma
- **Masala:** Nilufarning «qora kun» uchun yashirin zaxirasi. Oilaviy shaffoflik moliyaviy zo'ravonlik sharoitida ayolning xavfsizlik zaxirasini yo'q qilishi mumkin.
- **Taklif:** a'zoning shaxsiy PIN bilan himoyalangan, boshqalarga ko'rinmaydigan jamg'armasi (`visibility = PRIVATE`). Sxemada maydon hozirdan bor.
- **To'sadi:** U1 (UI), U4. **Holat:** OCHIQ.

### OQ-M3. Ikki xonadonni birlashtirish
- **Masala:** U14 boshqa xonadonning faylini rad etadi (`INTERCHANGE_WRONG_HOUSEHOLD`). Ikki kishi alohida daftar boshlab, keyin bitta oilaga qo'shilmoqchi bo'lsa (yangi kelin, ajralib chiqqan o'g'il) nima qilinadi?
- **Taklif:** MVP'da yo'q (D14). Keyin — «import qilib yangi xonadonga ko'chirish» ustasi: kategoriyalarni moslashtirish, a'zolarni birlashtirish, kelishuv jurnallari alohida qoladi.
- **To'sadi:** — . **Holat:** OCHIQ (mahsulot egasi).

## Ulamo uchun

### OQ-D1. Mudorabada zararni keyingi foydadan qoplash
- **Savol:** davr zarari kapital egasiga yozilgandan keyin, keyingi davr foydasi avval kapitalni tiklashga ketadimi?
- **Misol:** 1-oy zarar 2 mln, 2-oy foyda 3 mln, ulush 50/50. Spec bo'yicha: ishchi 1,5 mln. Klassik qoida bo'yicha: 2 mln kapitalga, qolgan 1 mln → har biriga 0,5 mln.
- **To'sadi:** U11, U12. **Holat:** OCHIQ.
- **U11 da:** davr natijasini taqsimlash U12 (venture ledger) da; U11 da faqat shartnoma, zarar qoidasi va zarar ulushlari. Qaror U12 dan oldin kerak.
- **U12 da qilingan (vaqtinchalik):** standart — klassik qoida (`CAPITAL_FIRST`): keyingi foyda avval o'tgan zarar bilan kamaygan kapitalni tiklaydi (zararni ko'targanlarga, ularning ulushiga mutanosib), qolgani foyda ulushlari bo'yicha. Siyosat har bir yopilgan davrda saqlanadi; «har davr alohida» (`PER_PERIOD`) ham tayyor — ulamo qaroridan keyin standartni almashtirish bir qator (`LossPolicy::default`). Beparvolik zarari tiklanmaydi (ishchi qoplaydi). Vektorlar: `vp-003`, `vp-004`, `vp-011`, `vp-012`.

### OQ-D2. Musharakada ishlamaydigan sherik
- **Savol:** Hanafiy mazhabida ishlamaydigan sherikning foyda ulushi kapital ulushidan oshmasligi kerakmi? Validator sifatida qo'shiladimi?
- **To'sadi:** U11. **Holat:** OCHIQ.
- **U11 da qilingan (vaqtinchalik):** validator emas, **ogohlantirish** — musharakada ishlamaydigan sherik (`CAPITAL_PROVIDER`) ulushi kapital ulushidan katta bo'lsa, `SILENT_PARTNER_SHARE_ABOVE_CAPITAL` chiqadi, imzolashni to'smaydi. Ulamo qaroridan keyin xatoga aylantirish bir qatorlik o'zgarish (`domain-uy::partnership::check_rules`).

### OQ-D3. Qarz bo'yicha jarima va valyuta
- **Savol:** (1) tilxatdagi «bajarilmasa» bandida kreditor foydasiga pul jarimasi taqiqlanadimi (validator)? (2) dollarda olingan qarz so'mda qaytarilsa, qaysi kurs bo'yicha joiz? Standart: qaytarish valyutasi = qarz valyutasi.
- **To'sadi:** U8. **Holat:** OCHIQ.

### OQ-D4. Tayyorgarlik darvozasi: «yoki reja bor»
- **Savol:** foizli qarzi bor, lekin chiqish rejasi bor foydalanuvchi sheriklikka kapital bera oladimi? (`DEBT_RECOVERY` dagi 20% qarzga ketishi kerak.)
- **Taklif:** foizli qarz bor ekan, kapital kiritish yopiq; foizsiz qarz va reja bo'lsa — ochiq.
- **To'sadi:** U6. **Holat:** OCHIQ.
- **U11 da:** darvoza SPEC dagi standart siyosat bilan ishlaydi (`AllowWithPlan`: foizli qarz bo'lsa ham, «Qarzdan chiqish» rejimi yoqilgan bo'lsa ochiq). Qorovul pul hozircha «Kelajagim» balansi (U6 da QOROVUL alohida bo'ladi), o'rtacha zarur xarajat — oxirgi 3 to'liq davrdagi ZARUR + KERAK (xarajat yozilmagan davrlar hisobga olinmaydi).

### OQ-D5. Muzoraa, nasiya narxi, savdo mollari zakoti
- **Savollar:** (1) nasiyada narxni oldindan qotirib sotish (bay' muajjal) va kechikish uchun ustama taqiqi; (2) savdo mollari zakotini bozor narxida baholash; (3) xodim bilan foyda ulushi asosidagi kelishuv; (4) konsignatsiya.
- **K0 da (SPEC 5.2, 7.1, 8.3):** nasiya narxi kelishuvda qotiriladi va keyin oshirilmaydi, ustama/jarima maydoni yo'q; zakot bazasidagi tovar baholash usuli (xarid, qayta tiklash yoki sotuv narxi) ochiq — SPEC'dagi misol shartli.
- **To'sadi:** K4, K6, K7. **Holat:** OCHIQ.

### OQ-D7. Savdo mollari zakoti: nisob, nasiya, oilaviy mehnat, oldindan to'lov
- **Savollar:** (1) nisob oltin (85 g) yoki kumush bo'yicha hisoblanadimi, kim tanlaydi? (2) umidli nasiya bazaga kiradi, umidsiz (90+ va egasi belgilagan) kirmaydi — to'g'rimi; umidsiz nasiya keyin qaytsa? (3) yaqin muddatli qarzlar (ta'minotchiga) bazadan ayiriladimi? (4) nasiyani muddatidan oldin to'lagan mijozga chegirma berish (da' va ta'ajjal) joizmi — ilovada bunday tugma bo'lsinmi? (5) oilaviy mehnatni tannarxga «bahosi» bilan kiritish — bu faqat hisob usuli, fiqhiy masala emas deb tushunamiz; to'g'rimi?
- **K0 da:** formula `docs/kasbkor/SPEC.md` 8.3 (2,5% = 250 bp, hawl va nisob sharti); natija «hisob, fatvo emas».
- **To'sadi:** K7. **Holat:** OCHIQ.

### OQ-D6. Kamayib boruvchi musharakada ulush narxi
- **Savol:** mehnat egasi kapital egasining ulushini bosqichma-bosqich sotib olganda, har bir qism narxini **oldindan qotirib** (masalan, 30 mln / 20 = 1,5 mln) va'da qilish joizmi? Bizning tushunishimizcha, AAOIFI shariat standartida (12, sheriklik) ulushni asl (nominal) qiymatda sotib olish majburiyati kapitalni kafolatlaydi va qarzga o'xshab qoladi, shuning uchun sotilgan kundagi bozor yoki o'sha kuni kelishilgan qiymat ko'rsatiladi — ulamo tasdiqlashi kerak.
- **U11 da qilingan:** jadval «taxminiy» deb belgilanadi, shartnoma va PDF da «har bir qism sotilgan kuni kelishilgan qiymatda baholanadi, kapitalni to'liq qaytarish oldindan va'da qilinmaydi» bandi bor. Foyda ulushlari ulush o'zgarishi bilan avtomatik o'zgarmaydi (yangi versiyada kelishiladi).
- **To'sadi:** U12 (buyout to'lovini taqsimotdan ayirish). **Holat:** OCHIQ.
- **U12 da:** davr yopilganda har bir muddati kelgan bosqich narxi shu kuni kiritiladi (standart — jadvaldagi qiymat); o'tadigan kapital — jadval bo'yicha. To'lov xaridorning shu davrdagi foyda ulushidan, bosqichlar tartib bilan va faqat to'liq to'lanadi; yetmasa yoki zarar bo'lsa — keyingi davrga qoladi (majburiy to'lov emas). Buyout bilan kapital olgan xaridor keyingi zararlarni ham kapitaliga mutanosib ko'taradi.

## Yurist uchun

### OQ-Y1. Qarz shartnomasi
- **Savol:** Fuqarolik kodeksi bo'yicha fuqarolar o'rtasidagi qarz sukut bo'yicha foizli hisoblanadimi? Qaysi summadan yozma shakl majburiy? Agar sukut bo'yicha foizli bo'lsa, tilxatda «foizsiz» bandi majburiy.
- **To'sadi:** U8. **Holat:** OCHIQ.

### OQ-Y2. Ekranda chizilgan imzo
- **Savol:** ekranda chizilgan imzoli PDF qanday dalil kuchiga ega (ERI emas)? Qaysi summadan «chop etib qo'lda imzolash» standart bo'lishi kerak?
- **To'sadi:** U7, U8. **Holat:** OCHIQ.
- **U11 da:** sheriklik shartnomasi tomonlar, guvohlar va hakam tomonidan shu qurilmada chiziladi (raqamli chiziqlar, SVG); har bir versiya va imzo DB darajasida o'zgarmas. PDF da imzolanmaganlar uchun chiziq qoladi — «chop etib qo'lda imzolash» ham mumkin.

### OQ-Y3. Kasb-kor: mijozlarning shaxsiy ma'lumotlari
- **Savol:** nasiya olgan mijozlarning ism va telefonlarini saqlaganda do'kondor operator hisoblanadimi? Qanday rozilik shakli kerak?
- **K0 da (SPEC 5.2, 11):** telefon ixtiyoriy, saqlanganda rozilik belgisi; ma'lumot faqat qurilmada shifrlangan; eslatmani ilova o'zi yubormaydi (matn nusxalanadi). Xodim ma'lumotlari ham minimal (7.2).
- **To'sadi:** K4, K6. **Holat:** OCHIQ.

### OQ-Y4. Sheriklik shartnomasi shakli
- **Savol:** mudoraba/musharaka kelishuvi Fuqarolik kodeksidagi oddiy shirkat (birgalikdagi faoliyat) shartnomasiga qanday mos keladi?
- **To'sadi:** U11. **Holat:** OCHIQ.
- **U11 da:** shablon `reviewStatus = PENDING` — ilovada va PDF da «yurist va ulamo tekshirmagan» ogohlantirishi chiqadi.

### OQ-Y5. Hakam qarori va ish papkasi
- **Savol:** tomonlar tanlagan hakam (mahalla oqsoqoli va h.k.) qarori qanday huquqiy kuchga ega? Hakam qarorni ilovada chizilgan imzo bilan tasdiqlashi kerakmi yoki qog'ozdagi qarorning nusxasi (rasm) ilova qilinadimi?
- **U13 da:** qaror sanasi, mazmuni va natijasi (`RESUME` / `AMEND`) o'zgarmas yozuv sifatida saqlanadi; ish papkasi PDF «ilova yuridik maslahat bermaydi» bandi bilan.
- **To'sadi:** — . **Holat:** OCHIQ.

### OQ-Y6. Xodim, ta'minotchi va nasiya kelishuvlari
- **Savol:** `EMPLOYMENT`, `SUPPLY`, `CREDIT_SALE` shablonlari (9 savol asosida) qanday ko'rinishda bo'lishi kerak, rasmiy mehnat shartnomasi va oldi-sotdi shartnomasidan qanday ajratiladi? Ilova bu hujjatlarni «ichki kelishuv» deb ataydimi?
- **To'sadi:** K4, K6. **Holat:** OCHIQ.

### OQ-Y7. Fiskal talablar va «boshqaruv hisobi» chegarasi
- **Savol:** ilova onlayn-kassa (fiskal) va soliq hisobotlari o'rnini bosmaydi, egasi o'zi uchun hisob yuritadi. Kunlik kassa yopish va nasiya daftari qanday ifodalanishi kerakki, foydalanuvchi uni rasmiy hujjat deb o'ylamasin? Qanday disklеymer kerak?
- **To'sadi:** K1, K4. **Holat:** OCHIQ.

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
- **U15 da:** `apps/desktop/e2e` — `tauri-driver` + WebdriverIO (klassik rejim), Linux'da (WebKitWebDriver, Xvfb) avtomatik va CI'da tungi job. Har bir ekran haqiqiy webview'da axe-core bilan. Windows'da `msedgedriver` WebView2 versiyasiga mos tanlanishi kerak — CI job hali yo'q.
- **Qaror qachon:** Windows job — reliz oldidan. **Holat:** QISMAN.

### OQ-T6. `.baraka` formati Android'da (Dart) va QR skanerlash
- **Masala:** Android ilovasi formatni FRB orqali Rust yadrosidan oladi — sxema va xeshlar bitta. Test strategiyasida «barcha vektorlar Dart'dan ham ishga tushiriladi» — `spec/interchange/vectors.json` ni FRB orqali Dart testidan o'tkazish yetarlimi yoki Dart'da sarlavha va QR payload uchun alohida parser ham kerakmi? QR skaneri uchun kamera ruxsati va qaysi kutubxona (ML Kit — Google Play xizmatlarisiz qurilmalarda ishlamaydi)?
- **Taklif:** vektorlar FRB orqali Dart testida; Dart'da faqat QR payload (`BARAKA-PAIR:{…}`) parseri; shifrlash va birlashtirish — faqat yadroda. Skaner: `zxing` asosidagi offline kutubxona.
- **To'sadi:** Android UI. **Holat:** OCHIQ.

### OQ-T7. Eksport KDF parametrlari va ishlatilmagan ulash fayllari
- **Masala:** fayl kaliti Argon2id 64 MiB, t = 3 — arzon Android telefonda ~1–2 s bo'lishi mumkin. Ishlatilmagan «Yangi qurilmani ulash» fayllarining «kutilmoqda» yozuvlari (`sync_pending`) hech qachon tasdiqlanmaydi va bazada qoladi (har biri daftar hajmiga mutanosib, kichik).
- **Taklif:** KDF'ni haqiqiy qurilmada o'lchab, kerak bo'lsa `mKib` ni 32 MiB ga tushirish (sarlavhada saqlanadi — eski fayllar ochilaveradi); 30 kundan eski tasdiqlanmagan ulash eksportlarini tozalash.
- **To'sadi:** — (ishlaydi). **Holat:** OCHIQ.

### OQ-T8. Avtomatik yangilash (updater)
- **Masala:** D15 «imzolangan updater manifesti»ni talab qiladi. `tauri-plugin-updater` internetdan manifest so'raydi — bu «ma'lumot bulutga chiqmaydi» va'dasiga zid emas (faqat versiya so'raladi), lekin ilova birinchi marta tarmoqqa chiqadi (CSP `connect-src` kengayadi), manifest uchun hosting va minisign kaliti kerak.
- **Variantlar:** (a) updater yo'q — yangi o'rnatuvchi qo'lda yuklanadi (hozir shunday); (b) GitHub Releases'dagi statik `latest.json` + minisign, tekshirish faqat foydalanuvchi «Yangilanishni tekshirish» bosganda; (c) avtomatik fon tekshiruvi.
- **Taklif:** (b). Qaror chiqmaguncha updater qo'shilmadi (`RELEASE_CHECKLIST.md` 3).
- **Kimga:** mahsulot egasi. **Holat:** OCHIQ.
