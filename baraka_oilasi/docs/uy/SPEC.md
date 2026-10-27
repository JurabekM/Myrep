# LOYIHA PROMPTI — «BARAKA DASTUR» (UY MAKONI)
### O'zbekiston o'rta qatlami uchun ribosiz (islom moliyasi tamoyillaridagi) shaxsiy moliya Android ilovasi

> Versiya: v0.9 · Ilhom manbasi: halol boylik haqidagi «qonunlar» suhbatlarining ma'nosi (`docs/BARAKA_OILASI.md` 2.1). Boshqa mualliflarning matni, personajlari va brendi ishlatilmaydi.
> Bu prompt AI-dasturchi (Claude Code va h.k.) uchun yozilgan. Har bir yangi matndan keyin yangilanadi.

---

## 0. ROL
Sen — senior mobil va backend dasturchisan, FinTech, xavfsizlik va Android platformasi bo'yicha chuqur tajribaga egasan. Kodni production-sifatda, testlar bilan, xavfsizlikni birinchi o'ringa qo'ygan holda yozasan.

## 1. MAHSULOT MOHIYATI
**«Baraka Dastur»** (Uy makoni) — ta'lim va amaliyotni birlashtirgan ilova. Foydalanuvchi qisqa darslar orqali **halol boylikning 7 tamoyili**ni o'rganadi va har birini shu haftaning o'zida ilovadagi vositalar bilan amalda bajaradi.

- **Asosiy muammo:** odamlar halol va ko'p ishlaydi, lekin oy oxirida pul qolmaydi. Sababi daromad kamligida emas. Xarajatlar hisobi yuritilmaydi va «o'zingga to'lash» odati yo'q.
- **Falsafa:** ribo (foiz) yo'q. Boylik jamg'arish, xarajatni jilovlash, qarzdan qochish, sherikchilik (mudoraba/mushoraka) va zakot orqali keladi.
- **Bu ilova nima EMAS:** tez boyish vositasi ham, kredit yoki qarz platformasi ham, fatvo yoki moliyaviy maslahat ham emas.
- **Asosiy tamoyil:** «Ilm o'qiganniki emas, amal qilganniki». Har bir bob ichida bajariladigan amallar bor. Miqdordan ko'ra odat muhimroq.

### 1.1. Kontent tuzilmasi
- Qisqa darslar (boblar) 8 ta tamoyilni ochib beradi. Matnlar — o'zimiz yozganlari.
- Har bir bob ichida quyidagilar bo'ladi:
  - qisqa hikoya yoki misol (o'zimiz yozgan; matn va ixtiyoriy audio);
  - «Daftar sahifasi», ya'ni foydalanuvchi tamoyilni o'z qo'li bilan yozadigan raqamli sahifa;
  - shu haftalik 3 ta amaliy vazifa.
- Ritm haftalik, juma kunlari. Har juma yangi bob ochiladi va o'tgan haftadagi vazifalar tekshiriladi.
- Kontent: o'zimiz yozgan matnlar. G'oya «qonunlar» suhbatlarining ma'nosidan ilhomlangan (`BARAKA_OILASI.md` 2.1).

### 1.2. Personajlar (persona = foydalanuvchi segmenti)
| Personaj | Segment | Moliyaviy xulq | Ilova nimani yechishi kerak |
|---|---|---|---|
| **Bekzod** — taksichi | Kunlik naqd daromad oladi, daromadi notekis | Avtokredit, ijara va nasiya daftari bor. Mayda xarajatlari hisobsiz | Kunlik daromadni tez kiritish, majburiyatlarni ko'rsatish, «oqib ketayotgan» pullarni topish |
| **Feruza** — tikuvchi | Har buyurtma uchun daromad oladi | Tejamkor, yashirincha «qora kun»ga pul yig'adi | Har buyurtmadan avtomatik ulush ajratish va oilaviy byudjet |
| **Sherzod** — dasturchi | Daromadi yuqori | Puli tez «erib ketadi», kripto/treyding signallariga aldanadi | Impulsiv xarajat nazorati va firibgarlik/«tez boyish» ogohlantirishlari |
| **Ravshan aka** — 52 yosh, mahalla faoli | Ijtimoiy majburiyatlar qarzidagi oila boshlig'i | O'g'lining to'yidan qolgan qarzni 6 yildan beri to'lay olmayapti, qo'shnilardan mayda qarz oladi | Qarzlar xaritasi, qarzdan chiqish rejasi, to'y va marosim xarajatlarini oldindan rejalash |
| **Moliyaviy maslahatchi** | Ilovadagi yo'l ko'rsatuvchi ovoz (ismsiz, personaj emas) | — | Savol beradi, hisoblatadi, ayblamaydi |

## 2. 1-TAMOYIL: «AVVAL O'ZINGGA TO'LA» — FUNKSIONAL TALABLAR
Tamoyilning mazmuni: har bir halol daromadning kamida 1/10 qismi «kelajakdagi o'zingniki» bo'ladi va unga tegilmaydi.

### 2.1. Daromadni kiritish
- Kiritish juda tez bo'lishi kerak: bir qo'l bilan, 2–3 bosishda. Taksichi kun oxirida naqd pulni kiritadi.
- Har bir daromadda quyidagilar bo'ladi: manba (kunlik ish, buyurtma, oylik), kanal (naqd yoki karta), sana va oila a'zosi.
- Har daromad kiritilganda ilova darhol ulushni taklif qiladi: «Shundan X so'm — kelajagingiz uchun».

### 2.2. «Kelajagim» jamg'armasi (virtual qizil qopcha)
- Bu alohida jamg'arma bo'lib, unga «tegilmaydi»: undan pul chiqarish uchun qo'shimcha tasdiqlash so'raladi va pauza qo'yiladi.
- Ulushni sozlash mumkin: 5% (boshlang'ich), 10% (maqsad) yoki aniq summa (masalan, oyiga 300 000 so'm).
- **Progressiv rejim:** kichik ulushdan boshlanadi va ilova vaqti-vaqti bilan uni oshirishni taklif qiladi.
- Miqdordan ko'ra **odatni kuzatish** muhim: ketma-ketlik (streak), «ajratilgan kunlar soni» va haftalik bajarilish.
- «Ro'molcha» stsenariysi: ilovadan oldin yig'ilgan naqd jamg'armani boshlang'ich balans sifatida kiritish imkoni bo'lsin.

### 2.3. «Pul qayerga ketdi?» — xarajat auditi
- O'tgan oy uchun yo'naltirilgan audit ustasi (wizard): foydalanuvchi xarajatlarni kategoriyalar bo'yicha bosqichma-bosqich kiritadi.
- **Oilaviy rejim:** byudjetni er va xotin birga to'ldiradi (2+ a'zo, umumiy byudjet). «Yolg'iz yozmang» tamoyili.
- **«Oqib ketish» detektori:** daromad, majburiyatlar va kiritilgan xarajatlar orasidagi farq «izohsiz qolgan summa» sifatida ajratib ko'rsatiladi (hikoyadagi «somsaga bir million» holati).
- Mayda kundalik xarajatlar (gazak, ichimlik, o'yin to'lovlari, bolaga shirinlik) alohida kategoriyada yuritiladi.

### 2.4. «Kimning puli?» ekrani
- Oylik daromad egalarga bo'lib vizual ko'rsatiladi: uy egasiniki, bankniki, do'kondorniki, davlatniki, yoqilg'iniki va **o'zingizniki**.
- Asosiy KPI: **«O'zingizga qancha to'ladingiz?»**. Bu bosh ekrandagi birinchi raqam bo'ladi.
- Oy yakuni plyus yoki minus bo'lib, aniq ko'rsatiladi.

### 2.5. Majburiyatlar
- Doimiy to'lovlar: ijara, kredit to'lovi, kommunal xizmatlar, telefon, benzin.
- **Nasiya daftari:** do'kondagi qarzlar alohida modul bo'lib, kimga va qancha qarzdorligi ko'rinadi.
- To'lov sanalari uchun eslatmalar bo'ladi.

## 2B. 2-TAMOYIL: «XARAJATNI YOZING» — FUNKSIONAL TALABLAR
Tamoyilning mazmuni: xarajatni yozmaguningcha uni boshqara olmaysan. Ilova ikki chekkani ajratib ko'rsatadi: isrof (teshik) va baxillik (bo'g'ilgan buloq). Maqsad ular o'rtasidagi iqtisod, ya'ni pulga egalik.
Muammoning mohiyati: pul katta xarajatlarga emas, **ko'plab mayda va «arzimagan» xarajatlarga** ketadi. Bu xarajatlar alohida ko'rinmaydi, faqat jamlanganda ko'zga tashlanadi.

### 2B.1. Har bir xarajatni yozish
- Har bir xarajatni oxirgi so'migacha yozish bu haftaning asosiy odati. Kiritish 1 ekranda, 3 soniyadan kam vaqtda bo'lishi kerak.
- **Tez kiritish usullari:**
  - takrorlanadigan xarajatlar uchun shablonlar (somsa, ichimlik, benzin, choyxona);
  - bosh ekran vidjeti (home screen widget);
  - oxirgi xarajatlardan bir bosishda nusxa olish.
- **Jamlash effekti:** har bir mayda kategoriya uchun «haftada / oyda / yilda» jami ko'rsatiladi. Masalan: «Kuniga 2 ta ichimlik = oyiga X, yiliga Y».
- **Ekvivalent bilan taqqoslash:** oqib ketgan summa foydalanuvchining o'z majburiyatlari bilan solishtiriladi. Masalan: «Bu summa ijarangizning 40%i».

### 2B.2. Uch toifali tasnif: Zarur / Kerak / Havas
Har bir xarajat (va kategoriya) majburiy ravishda 3 ta `Necessity` darajasidan biriga bog'lanadi:

| Daraja | Ta'rif | Misollar |
|---|---|---|
| `ZARUR` | Usiz yashab bo'lmaydi | non, dori, ijara, kredit to'lovi, yo'lkira |
| `KERAK` | Usiz yashasa bo'ladi, lekin qiyin | qishki kiyim, bolaning kitobi yoki to'garagi (bola tarbiyasi = `KERAK`) |
| `HAVAS` | Usiz bemalol yashasa bo'ladi | yangi telefon, ulfatchilik, ortiqcha ichimliklar, o'yinlar, gullar |

- Ustuvorlik tartibi qat'iy: avval `ZARUR`, keyin `KERAK`, eng oxirida `HAVAS`. Byudjet taqsimoti ham shu tartibda hisoblanadi.
- Har bir kategoriyaning standart toifasi bor, lekin oila uni o'zgartira oladi. Toifa o'zgartirilganda kim va qachon o'zgartirgani tarixda saqlanadi.
- **«Havasni o'ldirma, navbatga qo'y».** Havas taqiqlanmaydi, unga oylik chegara qo'yiladi.

### 2B.3. Havas uchun oylik chegara (oilaviy kelishuv)
- `HavasLimit`: oylik summa uchun oiladagi barcha kattalar rozilik berishi kerak (consent / kelishuv tasdig'i). Bir tomonlama o'rnatilgan chegara «zulm» deb qabul qilinishi mumkin.
- Chegaraga yaqinlashganda (masalan, 80%) va undan oshganda yumshoq ogohlantirish chiqadi. Bloklash yo'q.
- Oila a'zolarining har biri uchun shaxsiy havas ulushi belgilanishi mumkin. «Siz olib kelsangiz hisobga kirmaydi» kabi o'zaro sovg'alar uchun `gift` belgisi bo'ladi.

### 2B.4. «Juma shirinligi» — havasni ritualga aylantirish
- Kundalik havas xarajatini **rejalashtirilgan davriy ritual**ga aylantirish funksiyasi. Masalan: har kungi shokolad → haftalik «juma shirinligi».
- `ScheduledTreat`: nomi, davriyligi, summasi. Shu kuni ilova bola yoki oila uchun eslatma va quvonchli bildirishnoma yuboradi.

### 2B.5. Obunalar va avtomatik to'lovlar auditi («tuynuk» qidirish)
- Barcha takroriy to'lovlar (obunalar, avtoto'lovlar) alohida ro'yxatda turadi. Har biri uchun oylik va **yillik** narx, oxirgi ishlatilgan sana va «kerakmi?» savoli ko'rsatiladi.
- **Unutilgan obuna detektori:** takroriy yechib olish bor, lekin foydalanuvchi uni uzoq vaqt «ishlatdim» deb belgilamagan bo'lsa, ilova ogohlantiradi.
- MVP'da obunalar qo'lda kiritiladi. Keyingi bosqichda bank yoki karta tranzaksiyalaridan takroriy to'lovlar avtomatik aniqlanadi.
- Har bir bekor qilingan obuna «qutqarilgan pul» hisobiga yoziladi.

### 2B.6. Konvert byudjeti (naqd pul uchun)
- Haftalik **konvertlar:** «Bozor», «Yo'lkira», «Havas» kabi virtual konvertlar, har biri o'z limiti bilan.
- Naqd rejim qo'llab-quvvatlanadi: ilova jismoniy konvertga qancha naqd pul solish kerakligini aytadi, hafta oxirida esa qoldiq kiritiladi.
- Asos: karta bilan to'lanadigan pul «sezilmay» ketadi. Ilova kartadagi xarajatlarni ham konvertdan ayiradi.

### 2B.7. «Qutqarilgan pul» metrikasi
- Bu bobning asosiy KPI'si: **teshikdan qutqarilgan summa**. U o'tgan davrdagi havas va oqib ketgan xarajatlarni joriy davr bilan taqqoslab hisoblanadi.
- Qutqarilgan summani «Kelajagim» jamg'armasiga o'tkazish bir bosishda taklif qilinadi. 1-tamoyil bilan bog'lanish shunday: rejada 300 000 bo'lgan oylik o'tkazma shu tarzda 1 100 000 ga yetishi mumkin.
- Haftalik juma hisobotida murabbiy bitta raqamni so'raydi: «Bu hafta qancha qutqardingiz?»

### 2B.8. Isrof va saxovatni ajratish
- `SADAQA` (xayriya, yordam) alohida kategoriya. U **havas emas** va «oqib ketish» hisobiga kirmaydi.
- **Obro' xarajatlari:** ko'rinish uchun qilinadigan xarajatlar (ko'p to'yona, hammaga osh buyurish, tez-tez yangi telefon yoki g'ildirak) uchun ixtiyoriy `ostentation` belgisi bor. Bu xarajatlar isrof tahlilida alohida ko'rsatiladi.
- **Qarz bilan qilingan havas** (masalan, qarzga olib to'yona qilish) qizil bayroq bilan belgilanadi.

### 2B.9. Odatlar (ixtiyoriy, yumshoq)
- Foydalanuvchi o'zi tanlagan zararli yoki qimmat odatlarni (masalan, chekish) xarajat sifatida kuzatish mumkin. Faqat statistika ko'rsatiladi: «oyiga X, yiliga Y».
- Majburlash, ayblash yoki uyaltirish yo'q. Kamaytirish rejasi faqat foydalanuvchi so'rasa taklif qilinadi.

### 2B.10. Persona bo'yicha eslatmalar
- **Bekzod:** naqd va mayda xarajatlar, yo'l-yo'lakay xaridlar. Shablonlar va vidjet unga eng muhim vositalar.
- **Sherzod:** obunalar, kafe va qahva, taksi. Obunalar auditi va yillik jami summa uni «uyg'otadi» (uning sanamaydigan mayda xarajatlari oyiga 3 mln+ bo'lgan).

## 2C. 3-TAMOYIL: «PULNI ISHLATING» — FUNKSIONAL TALABLAR
Tamoyilning mazmuni:
- **Yotgan pul**ni inflyatsiya (narx-navo, «omborga kirmay donni yeydigan sichqon») sezdirmasdan yeydi.
- **Ishlayotgan pul** o'zini o'zi ko'paytiradi.
- Pul puldan tug'ilmasligi kerak (ribo yo'q). U mehnatdan, savdodan va sherikchilikdan tug'iladi.
- **Halol foyda testi:** foydaning tagida uchtadan biri bo'lishi shart: **ter (mehnat), mol yoki tavakkal**. Uchalasi ham bo'lmasa, u ribo hisoblanadi.

### 2C.1. «Narx daftari» — shaxsiy inflyatsiya kuzatuvi
- Foydalanuvchi o'zi uchun muhim mahsulotlar savatini tuzadi: go'sht, non, un, benzin va hokazo. So'ng ularning narxini vaqti-vaqti bilan kiritadi.
- `PricePoint`: mahsulot, narx (tiyinda), sana, joy (ixtiyoriy).
- Tarixiy taqqoslash ko'rsatiladi: «3 yil oldin → bugun». Masalan, go'sht 80 000 → 130 000 (+62,5%), non 2 000 → 3 000 (+50%).
- Bu ma'lumotlardan **shaxsiy inflyatsiya indeksi** hisoblanadi (savatdagi og'irliklar bo'yicha). Rasmiy statistika bilan taqqoslash ixtiyoriy.
- Narx kiritish odati uchun haftalik eslatma va streak bo'ladi.
- ⚠️ Rasmiy CPI ma'lumotlarining manbasi va litsenziyasi aniqlanadi (Statistika agentligi). MVP faqat foydalanuvchi kiritgan narxlar bilan ishlaydi.

### 2C.2. «Sichqon kemirgani» — xarid qobiliyati kalkulyatori
- Yotgan jamg'armaning real qiymati ko'rsatiladi: nominal balans va «bugungi narxlarda u nimaga teng».
- «N yildan keyin shu pulga nechta kilo go'sht olish mumkin bo'ladi» kabi aniq va tushunarli misollar keltiriladi.
- Bu ekranning maqsadi qo'rqitish emas, tushuntirish. Shu sababli har doim keyingi qadam (zaxira pul / o'sadigan pul) bilan yakunlanadi.

### 2C.3. Jamg'armani ikkiga bo'lish
«Kelajagim» jamg'armasi endi `VaultType` bo'yicha ikkiga bo'linadi:

| Turi | Vazifasi | Qoidalar |
|---|---|---|
| `QOROVUL` (zaxira pul / favqulodda zaxira) | Qora kunda qarz eshigiga yugurmaslik | **Maqsadli summa avtomatik hisoblanadi:** oylik `ZARUR` + `KERAK` xarajatlarining o'rtachasi × N oy. Bosqichlar: 3 oy (birinchi milestone) va **6 oy (to'liq maqsad, standart)**. Bu summa hech qayerga sarflanmaydi, qarzga ham, sheriklikka ham. Pul tez olinadigan (likvid) joyda turadi. «O'smadi» deb baholanmaydi |
| `OSADIGAN` (ishlayotgan pul) | Inflyatsiyadan oldinda yurish | Faqat halol (ribosiz) yo'nalishlar uchun. Funksiyalar keyingi boblarda ochiladi |

- **Taqsimot ustuvorligi:** avval zaxira pul maqsadiga yetkaziladi, keyin o'sadigan qismga o'tiladi. Progress bar «necha oylik zaxira bor» ko'rinishida bo'ladi (masalan, «1,4 / 3 oy»).
- Zaxira puldan pul olishda «bu haqiqatan favqulodda holatmi?» degan tasdiq so'raladi va ishlatilgan summani qayta to'ldirish rejasi taklif qilinadi.

### 2C.4. «Jangga yarador askar yuborilmaydi» — tayyorgarlik darvozasi (readiness gate)
- O'sadigan pul, sherikchilik va investitsiya bo'limlari **qulflangan** holda turadi. Ular ikki shart bajarilganda ochiladi:
  1. zaxira pul ≥ 6 oylik zaxira (5-bobda 3 oydan 6 oyga oshirildi);
  2. yuqori xavfli qarzlar yopilgan yoki faol qarzdan chiqish rejasi bor (4-tamoyil).
- Qulflangan ekranda shartlar va har biri bo'yicha progress ko'rsatiladi. Taqiq yo'q, tushuntirish bor.
- Foydalanuvchi qulfni ongli ravishda chetlab o'tishi mumkin, lekin ogohlantirish va tasdiq bilan. Bu holat analitikada qayd etiladi.

### 2C.5. Ribo filtri
- Ilovada foizli omonat, foizli obligatsiya yoki «kafolatlangan foiz» mahsulotlari **tavsiya ham, reklama ham qilinmaydi**.
- Foydalanuvchi daromad manbasini kiritganda uni «ter / mol / tavakkal» testi bo'yicha belgilash ixtiyoriy. Foizli daromad manbasi alohida ko'rsatiladi (tozalash yoki sadaqa masalasi keyingi boblarda).
- Islomiy moliyaviy xizmatlar haqida hozircha faqat ta'limiy ma'lumot beriladi. Integratsiya keyinroq va faqat sertifikatlangan hamkorlar bilan qilinadi.

### 2C.6. Odat ritmi: «Shoshilmang»
- **Bosqichma-bosqich ochilish:** keyingi bob yoki tamoyil faqat vaqt o'tgani uchun emas, oldingi bobning asosiy odatlari kamida minimal darajada bajarilgan bo'lsa ochiladi. Masalan, 3 hafta ichida 2 tasida vazifalar bajarilgan bo'lishi kerak. Bu shartni sozlash mumkin.
- Yangi ma'lumotlar bilan ortiqcha yuklamaslik: bir haftada bitta asosiy yangi odat bo'ladi.

### 2C.7. Qarzlar ro'yxati (4-tamoyilga tayyorgarlik)
- **To'liq qarz inventari** — «yaraning hajmi». Unda hech qanday qarz tashlab ketilmaydi:
  - `BANK` — kredit va avtokredit (masalan: 39 mln, 14 oy qoldi);
  - `SHOP` — nasiya daftari;
  - `RELATIVE / FRIEND` — qarindosh va do'stlardan olingan norasmiy qarzlar;
  - `OTHER` — boshqa qarzlar.
- Har bir qarz uchun: kreditor, qolgan summa, oylik to'lov, muddat, ustama yoki foiz bor-yo'qligi va **sababi** (masalan, «to'y», «mashina», «ro'zg'or»).
- **Qarz bergan tomon sifatida:** foydalanuvchi bergan qarzlar (`Receivable`) ham kuziladi. Masalan, qo'shniga oy oxirigacha 200 000. Muddat kelganda xushmuomala eslatma chiqadi, majburlash yo'q.
- Umumiy ko'rsatkichlar: jami qarz, oylik qarz yuki (daromadga nisbatan %) va «qarzsiz kun»gacha qolgan prognoz.
- Asosiy fikr: «Qarz — teshik emas, yara». Qarz ekrani byudjet va jamg'arma ekranlaridan ustun turadi.

## 2D. 4-TAMOYIL: «RIBODAN SAQLANING, QARZDAN REJA BILAN CHIQING» — FUNKSIONAL TALABLAR
Tamoyilning mazmuni:
- Foizli qarz olinmaydi va berilmaydi.
- Zarurat uchun qarz olinsa, u **foizsiz, yozma va to'lash niyati bilan** olinadi.
- Qarzga botgan odam undan **reja bilan** chiqadi.
- Bobning asosiy saboqlari:
  - qarz — o'z qo'li bilan taqilgan «qog'oz kishan»;
  - «El nima deydi» bosimi bilan qilinadigan dabdaba (to'y) qarzning eng katta manbai;
  - qarzning **haqiqiy narxi** asosiy summadan ancha katta bo'ladi. Misol: qarzga qilingan 40 mln lik to'y uchun yillar davomida 60+ mln to'lanishi va qarz hali ham qolishi mumkin.

### 2D.1. Byudjet rejimlari: `STANDARD` va `DEBT_RECOVERY`
- Faol qarzi bor foydalanuvchi uchun ilova **«Qarzdan chiqish» rejimi**ni (`DEBT_RECOVERY`) taklif qiladi. Bu rejim **70 / 20 / 10** qoidasiga asoslanadi:
  - **70%** — ro'zg'or (`ZARUR` + `KERAK` + `HAVAS` chegarasi shu ichida);
  - **20%** — odatiy to'lovdan **tashqari** qarzni tezroq uzish uchun qo'shimcha to'lov;
  - **10%** — baribir «Kelajagim» jamg'armasiga. Bu ulush **0 ga tushirilmaydi**.
- 10% ulushning mantig'i UI'da tushuntiriladi: «Qarz — o'tmishga to'lov, jamg'arma — kelajakka to'lov». Jamg'armasiz qarzdan chiqqan odam birinchi tashvishda yana qarz oladi.
- Majburiy oylik qarz to'lovlari 70% ichida `ZARUR` sifatida hisoblanadi. 20% — sof qo'shimcha to'lov.
- Foizlarni oila sozlay oladi, lekin standart qiymat 70/20/10. Jamg'arma ulushi 0 bo'lsa, ilova ogohlantiradi.
- Barcha qarzlar yopilganda rejim avtomatik `STANDARD` ga qaytadi. Bo'shagan 20% ni zaxira pul va o'sadigan pulga yo'naltirish taklif qilinadi.

### 2D.2. Qarzdan chiqish rejalovchisi (payoff planner)
- Har bir qarz uchun ikki jadval yonma-yon ko'rsatiladi: **odatiy grafik** va **qo'shimcha to'lovli grafik**.
- Natija aniq raqamlarda beriladi: necha oy erta tugaydi va qancha foiz yoki ustama tejaladi. Masalan: avtokredit 39 mln, 14 oy → 8–9 oy.
- Qo'shimcha to'lov manbalari rejaga ulanadi: 20% ulush, «qutqarilgan pul» (2-tamoyil) va buyum sotishdan tushgan pul (2D.6).
- **Qarzlarni yopish tartibi.** Standart strategiya — mahsulot taklifi, tasdiqlanishi kerak:
  1. foizli (ribo) qarzlar — avval, eng yuqori ustamalisidan;
  2. keyin qarindosh va do'stlardan olingan foizsiz qarzlar, muddati yaqinidan.
  Foydalanuvchi tartibni qo'lda o'zgartira oladi.
- ⚠️ Bank kreditini muddatidan oldin to'lash shartlari (jarima, komissiya, qayta hisoblash) kredit shartnomasiga bog'liq. Ilova foydalanuvchidan bu ma'lumotni so'raydi va hisob-kitobda inobatga oladi. Kalkulyator faqat taxminiy natija beradi va buni ochiq aytadi.

### 2D.3. Qarzning haqiqiy narxi
- Har bir qarz uchun «Asosiy summa → Jami to'langan → Ortiqcha to'lov» ko'rsatiladi. Masalan: 1,5 mln oylik to'lovning 600 mingi foizga ketayotgan bo'lsa, ilova buni ochiq ko'rsatadi.
- **Imkoniyat narxi:** ortiqcha to'langan summa foydalanuvchining o'z maqsadlari bilan taqqoslanadi. Masalan: «bu summa qizingizning N yillik kontraktiga teng». Maqsadlar ro'yxati foydalanuvchidan olinadi.

### 2D.4. Qarzni bir necha kishi to'lashi (oilaviy yelkadoshlik)
- Bitta qarzga bir nechta to'lovchi (`DebtContributor`) biriktiriladi: boshqa oila a'zosi yoki alohida xonadondagi farzand (masalan, o'g'il Sanjar).
- Har bir to'lovchining oylik ulushi va to'lov tarixi yuritiladi. Ishtirokchi taklif havolasi orqali ilovaga qo'shiladi va unga faqat o'sha qarz ko'rinadi.

### 2D.5. Halol qarz qoidalari: raqamli «qarz tilxati»
> 6-tamoyildan keyin: tilxat — `Agreement(type = LOAN)`, ya'ni 2F dagi umumiy dvigatelning bir turi.
Qarz olish yoki berishda (`Debt` / `Receivable`) uchta shart UI darajasida qo'llab-quvvatlanadi:
1. **Foizsiz.** «Ustama / foiz» maydoni to'ldirilsa, qizil ogohlantirish chiqadi. Foydalanuvchi o'zi **foizli qarz bermoqchi** bo'lsa, ilova bunga yo'l qo'ymaydi: `Receivable` da foiz maydoni umuman yo'q. «Qarzi hasana» standart tur hisoblanadi.
2. **Yozma va guvohli.** Ilova qarz tilxati hujjatini yaratadi: kim kimdan, qancha, qachongacha, guvoh(lar) va sana. Hujjat PDF yoki rasm sifatida ulashiladi. Ikkinchi tomon havola orqali ilovada **tasdiqlashi** mumkin, shunda ikki tomonda bir xil yozuv saqlanadi.
3. **To'lash niyati.** Qarz kiritishda to'lash rejasini (sanalar va summalar) yaratish majburiy. Rejasiz qarzni saqlab bo'lmaydi.
- ⚠️ Tilxatning yuridik kuchi borasida ilova hech qanday va'da bermaydi. Matnda bu «shaxsiy hisob uchun yozuv» ekani ko'rsatiladi. Yuridik shakl kerak bo'lsa, buni yurist bilan alohida aniqlashtiramiz.

### 2D.6. Yangi qarz oldidan «to'xta va o'yla» (friction)
- Yangi qarz qo'shilayotganda qisqa tekshiruv so'rovi chiqadi:
  - zaruratmi yoki hashamatmi;
  - foizsiz muqobil bormi (zaxira pul, qarindosh, buyum sotish);
  - oylik yuk daromadning necha foiziga yetadi.
- So'rov maqsadi qarz olishni taqiqlash emas, ongli qaror qabul qilishga yordam berish. Natija qarz yozuvida saqlanadi.

### 2D.7. «Sotiladigan buyumlar» ro'yxati
- Uyda 6 oydan beri ishlatilmayotgan qimmatbaho buyumlar ro'yxati yuritiladi: nomi, taxminiy narxi va holati (`LISTED / SOLD`).
- Sotilgan buyumdan tushgan pul bir bosishda tanlangan qarzga qo'shimcha to'lov sifatida yo'naltiriladi.
- Keyingi bosqichda e'lon saytlariga eksport qilish mumkin (masalan, OLX.uz). Bu hozircha faqat g'oya.

### 2D.8. To'y va marosimlarni rejalash (`CeremonyPlan`)
- Marosim turlari: to'y, beshik to'y, sunnat to'y, ma'raka va hokazo. Har biri uchun **byudjet qatorlari** bo'ladi: mehmonlar × kishi boshiga narx, osh, xonanda yoki musiqa, kiyim-kechak, sarpo va boshqalar.
- Har bir qator uchun **moliyalash manbasi** belgilanadi: jamg'arma, oila hissasi, kutilayotgan to'yona yoki qarz.
- **Asosiy qoida:** qarz bilan moliyalashtirilgan qatorlar bo'lsa, ilova marosim **sanasini «tasdiqlangan» holatga o'tkazishdan oldin** «Buni qarzsiz qanday o'tkazamiz?» degan oilaviy muhokama bosqichini taklif qiladi.
- **Stsenariylarni taqqoslash:** masalan, «3 kunlik, 200 kishi» va «1 kunlik, 100 kishi, ixcham». Taqqoslash umumiy narx, qarz, to'lash muddati va shu pulga erishiladigan muqobil maqsadlar (o'qish, boshpana, farzandga ish boshlab berish) bo'yicha qilinadi.
- **To'yona o'rniga jamg'arma:** yosh oila uchun maqsadli jamg'arma (`Goal`) ochish va unga mehmonlar hissa qo'shishi uchun ulashiladigan havola. Bu MVP'da virtual, keyinroq hamkor bank orqali bo'ladi.
- Ijtimoiy bosimga qarshi kontent: «El uch kun gapiradi, to'rtinchi kuni o'z dardi bilan ovora bo'ladi».

### 2D.9. «Qarzsiz kun» va motivatsiya
- Har bir qarz va barcha qarzlar uchun prognozli «qarzsiz kun» sanasi hisoblanadi. Har oy qo'shimcha to'lovdan keyin bu sana yangilanadi.
- Qarz yopilganda milestone nishonlanadi. Bo'shagan to'lov summasini jamg'armaga yo'naltirish taklif qilinadi.

## 2E. 5-TAMOYIL: «PULNI HALOL ISHGA SOL» — FUNKSIONAL TALABLAR
Tamoyilning mazmuni:
- Yotgan pul kamayib boradi, ishlagan pul egasini boqadi.
- Pulni halol ishlatishning yo'li **savdo va sheriklik**.
- Bob tezisi: bir odamning puli bekor yotadi, boshqasining hunari pulsizlikdan bekor turadi. Ular ko'pincha bir mahallada yashaydi.
- Sheriklik **sadaqa ham, qarz ham emas**. Bu teng huquqli kelishuv bo'lib, unda tavakkal (risk) bo'lishiladi.

### 2E.1. Sheriklik turlari (domen qoidalari)
| Tur | Kim nima kiritadi | Foyda | Zarar |
|---|---|---|---|
| `MUDARABA` | Kapital — bir tomondan (`CAPITAL_PROVIDER`), mehnat — ikkinchi tomondan (`WORKER`) | Kelishilgan **ulush (%)** bo'yicha | Moliyaviy zarar kapital egasining zimmasida, mehnat egasi esa mehnatidan ayriladi. Istisno: mehnat egasining beparvoligi yoki shart buzilishi (`negligence` bayrog'i) |
| `MUSHARAKA` | Ikkala tomon kapital (va/yoki mehnat) kiritadi | Kelishilgan ulush (%) bo'yicha | Har kim kiritgan **kapitaliga mutanosib** ko'taradi |

**Validatsiya qoidalari.** Bular kod darajasida majburiy va unit-test bilan qoplanadi:
- Foyda faqat **sof foydaning foizi** sifatida belgilanadi. Kapital egasiga **qat'iy summa yoki kafolatlangan daromad** belgilashni kiritib bo'lmaydi. Bunday urinishda «Bu sheriklik emas — ribo yoki qarz» degan tushuntirish chiqadi.
- `MUDARABA` da `WORKER` ga kapital zararini yuklash faqat `negligence = true` bo'lganda va uning izohi bilan mumkin.
- `MUSHARAKA` da zarar taqsimoti avtomatik hisoblanadi: `lossShare_i = capital_i / Σcapital`.
- Ulushlar yig'indisi 100% bo'lishi shart.

### 2E.2. Sheriklik shartnomasi («bandma-band, guvohlar bilan»)
> 6-tamoyildan keyin: sheriklik shartnomasi — `Agreement(type = PARTNERSHIP)`. U 2F dagi 9 savol strukturasidan foydalanadi va 2E.1 qoidalari bilan validatsiya qilinadi.
- Tamoyil: **«Shartnoma ishonmaydiganlar uchun emas, ishonchni asrab qolmoqchi bo'lganlar uchun yoziladi»**. Shuning uchun shartnomasiz sheriklik yaratib bo'lmaydi.
- Shartnoma ustasi (wizard) quyidagilarni yig'adi:
  - tomonlar va ularning rollari;
  - tur (`MUDARABA` / `MUSHARAKA`);
  - kiritilgan kapital (pul va/yoki uskuna ro'yxati, narxlari bilan);
  - foyda ulushlari va zarar qoidalari;
  - **muddat** (masalan, 1 yil);
  - hisobot davriyligi;
  - muddat tugaganda nima bo'lishi;
  - nizolarni hal qilish tartibi;
  - guvohlar.
- Natijada PDF yaratiladi va har bir tomon (hamda guvoh) ilovada **tasdiqlaydi**. Shartnomaga keyin kiritilgan o'zgarishlar versiyalanadi va qayta tasdiqlanadi.
- **Bosqichma-bosqich sotib olish (buyout):** mehnat egasi uskunalarni foyda ulushidan oz-ozdan to'lab, kapital egasining ulushini sotib oladi va oxirida mustaqil bo'ladi. Bu kamayib boruvchi sheriklik (`diminishing musharaka`). Jadval va qolgan ulush vizual ko'rsatiladi.
- ⚠️ 2D.5 dagi kabi: shartnomaning yuridik kuchi va islomiy muvofiqligi yurist va ulamo tomonidan ko'rib chiqiladi. Shablonlar faqat tasdiqlangandan keyin production'ga chiqadi.

### 2E.3. Sheriklik kassa daftari (venture ledger)
- Har bir sheriklik uchun **alohida hisob**: kirim (buyurtmalar), xarajatlar (mato, ip, ish haqi, masalan yordamchi Kamola uchun), sof foyda (davr bo'yicha).
- **Biznes pulini uy pulidan ajratish shart.** Sheriklik daftari xonadon byudjetiga faqat taqsimlangan foyda ulushi orqali bog'lanadi.
- Davr oxirida foyda yoki zarar 2E.1 qoidalari bo'yicha avtomatik taqsimlanadi. Taqsimot yozuvi ikkala tomonga ko'rinadi.
- **Shaffoflik:** kapital egasi ledgerni faqat o'qish (read-only) rejimida ko'radi. Har bir yozuvga chek yoki rasm biriktirish mumkin.
- **Fors-major hodisalari:** masalan, «omborni suv bosdi». Hodisa izohi va dalillar bilan qayd etiladi, zarar qoidaga ko'ra taqsimlanadi.

### 2E.4. «Hunardan ishga» rejalovchisi
- Oiladagi **bekor yotgan hunarlar** ro'yxati: tikuvchilik, pazandachilik, ta'mirlash, til bilish va hokazo.
- Har bir g'oya uchun mini biznes-hisob:
  - boshlang'ich xarajat (CAPEX) ro'yxati (masalan: overlock + bichish stoli + 2 o'ram mato = 8 mln);
  - kutilayotgan oylik kirim va xarajat;
  - sof foyda va qoplanish muddati (payback);
  - sheriklik bo'lsa, ulushlardan keyingi foyda.
- Uch stsenariy: pessimistik, o'rtacha va optimistik («hisob-kitobni uch marta qildim»).
- Natijadan bir bosishda sheriklik shartnomasi qoralamasini yaratish mumkin.

### 2E.5. «Kafolatlangan foyda» detektori (firibgarlikdan himoya)
- Qoida: **tavakkalsiz, kafolatlangan foyda va'da qilinsa — u yerda yo ribo, yo firibgarlik bor.**
- Foydalanuvchi o'ziga kelgan taklifni tekshiruv ro'yxati orqali baholaydi:
  - foyda kafolatlanganmi;
  - zarar bo'lishiladimi;
  - real mol yoki ish bormi;
  - yangi a'zo jalb qilish talab qilinadimi;
  - shoshiltirish bormi;
  - yozma shartnoma bormi.
- Natija «yashil / sariq / qizil» ko'rinishida chiqadi va har bir bayroq izohlanadi.
- Sherzod segmenti (kripto/treyding signallari) uchun asosiy himoya vositasi shu. Batafsil kengaytmasi keyingi boblarda bo'lishi mumkin.

### 2E.6. Gate va ruxsatlar bilan bog'liqlik
- **Kapital kiritish** (o'z pulini sheriklikka berish) 2C.4 tayyorgarlik darvozasiga bo'ysunadi: ≥6 oylik zaxira pul va faol qarz rejasi bo'lishi kerak.
- **Kapital qabul qilish** (mehnat egasi sifatida) darvozaga bo'ysunmaydi. Sababi: mudarabada kapital qarz emas, uni qaytarish majburiyati yo'q (beparvolik bundan mustasno). Lekin ilova buni foydalanuvchiga aniq tushuntiradi va oilaviy rozilikni (er va xotin) so'raydi.

### 2E.7. Regulyativ chegara
- ⚠️ **Ilova sheriklarni bir-biriga «tanishtiradigan» yoki pul yig'adigan platforma (P2P / kraudfanding / investitsiya marketplace) EMAS.** Bunday faoliyat O'zbekistonda alohida litsenziya va regulyatsiya talab qiladi.
- MVP'da ilova faqat **o'zaro tanish tomonlar** o'rtasidagi kelishuvni yozish, hisoblash va kuzatish vositasi. Pul ilova orqali o'tmaydi.
- Kelajakdagi «sheriklik bozori» faqat litsenziyali hamkor bilan va huquqiy tahlildan keyin ko'rib chiqiladi.

### 2E.8. UX tone
- Sheriklik sadaqa yoki minnat sifatida ko'rsatilmaydi. U teng huquqli ish sifatida ko'rsatiladi: «Ot bilan omoch — ikkalasi birga yer haydaydi».
- «El nima deydi» qo'rquviga qarshi kontent bo'ladi. Erkak yoki oila boshlig'i rozilik bosqichida g'ururni hurmat qiladigan matnlar ishlatiladi.

## 2F. 6-TAMOYIL: «KELISHUVNI YOZING» — FUNKSIONAL TALABLAR
Tamoyilning mazmuni:
- **Og'zaki kelishuv — qumga qurilgan uy.** Havo ochiq paytda turadi, birinchi sinovda qulaydi.
- Yozish ishonchsizlik belgisi emas. U **ishonchni asrash vositasi** va diniy ko'rsatma (Baqara 282).
- «Qog'ozda qattiq bo'lmaganlar keyin bir-biriga qattiq gapiradi.»

Dasturchi uchun bobning asosiy saboqlari:
1. Har bir tomon og'zaki kelishuvni **o'z foydasiga moslab eslaydi**. Bu yolg'on emas, xotiraning xususiyati. Bunga yechim — yozilgan shartlar va **o'zgarmas hisob yozuvlari**.
2. Sheriklikning eng xavfli payti **zarar emas, katta foyda** kelgan payt.
3. Nizoni **daftar**, ya'ni tiklanadigan aniq raqamlar to'xtatadi.
4. Yozilgan band nizo chiqqanda emas, **muammo chiqqan kuni** ishlaydi. Misol: Sherzod kasal bo'lib, bot ishdan chiqdi → 3-band bo'yicha harakat qilindi → janjal chiqmadi.

### 2F.1. Umumiy «Kelishuv» dvigateli (Agreement engine)
- 2D.5 dagi qarz tilxati va 2E.2 dagi sheriklik shartnomasi endi **bitta umumiy `Agreement` modelining turlari** bo'ladi (refaktor):
  `AgreementType`: `PARTNERSHIP | LOAN | RENT (ijara) | SERVICE (xizmat yoki ish) | FAMILY (oilaviy kelishuv) | OTHER`.
- Har bir tur uchun **«9 savollik kelishuv»** asosiy struktura bo'ladi. Tur faqat qo'shimcha maxsus maydonlar va validatsiyalarni beradi (masalan, `PARTNERSHIP` → 2E.1 qoidalari).
- Hujjat oddiy tilda yoziladi, rasmiy yuridik til shart emas. «Asosiysi — mag'zi.»

### 2F.2. 9 savol → majburiy bo'limlar
| # | Savol | Ilovadagi bo'lim | Validatsiya |
|---|---|---|---|
| 1 | Kim bilan kim? | `parties[]`: to'liq ism-sharif, roli, aloqasi | Kamida 2 tomon |
| 2 | Kim nima qo'shyapti? | `contributions[]`: pul, mol, mehnat, tanish-bilish — miqdori yoki tavsifi bilan | Har bir tomonda kamida bitta hissa |
| 3 | Kim nima qiladi? | `duties[]`: vazifa → **yagona mas'ul** tomon. Har bir vazifa uchun **«bajarilmasa»** bandi (masalan: «1 kun ichida xabar beradi va o'rniga yechim topadi») | Egasiz yoki «hamma» ga yozilgan vazifa **qabul qilinmaydi** («hamma hamma narsani qilsa — hech kim hech narsa qilmaydi») |
| 4 | Foyda qanday bo'linadi? | `profitRule`: faqat **foiz (bp)** | So'mdagi qat'iy summa taqiqlanadi (2E.1) |
| 5 | Zarar ko'rilsa nima bo'ladi? | `lossRule`: tur bo'yicha avtomatik taklif qilinadi (mudoraba / musharaka) | 2E.1 bilan mos |
| 6 | Pul qayerda, hisobni kim yuritadi, ikkinchi tomon qachon ko'radi? | `custody`: pul turgan joy, hisob yurituvchi, **ko'rib chiqish davriyligi** (standart — oyiga 1 marta) | Davriylik oyiga 1 martadan siyrak bo'lsa, ogohlantirish chiqadi |
| 7 | Qanday ajralib chiqiladi? | `exitClause`: oldindan ogohlantirish muddati, ulushni baholash usuli, to'lash muddati va tartibi, mol-mulk qanday bo'linadi | Majburiy |
| 8 | Kelisha olmasangiz, kim hakam? | `arbiter`: ism-sharif, roli, ikki tomon tomonidan tasdiqlanadi | Majburiy. Hakam tomonlardan biri bo'lishi mumkin emas |
| 9 | Qachon yangilanadi? | `term` + `reviewDate`: standart holatda yiliga 1 marta | Majburiy |

- **To'liqlik indikatori:** «9 / 9 savolga javob berildi». Barcha 9 bo'lim to'ldirilmaguncha yoki asosli ravishda «tegishli emas» deb belgilanmaguncha **imzolash bosqichi ochilmaydi**. «Tegishli emas» belgisi qo'yish uchun izoh yozish majburiy.
- Turga qarab ba'zi savollar soddalashtiriladi. Masalan, `LOAN` uchun 3-savol = «qaytarish jadvali», 4–5-savollar = «foiz yo'q» (avtomatik qo'yiladi). Biroq savollar ro'yxati hamma turda bir xil qoladi.
- «Noqulay» bandlarni ham yozish rag'batlantiriladi. Masalan, «Agar X o'z vazifasini bir hafta bajarmasa...». UI'da maslahatchi kartasi chiqadi: «Qog'ozda aniq yozilsa, keyin bir-biringizga qattiq gapirishga hojat qolmaydi».

### 2F.3. Imzolash, guvohlar va versiyalar
- Imzolash, guvohlar va versiyalash 2D.5 va 2E.2 dagi tartib bilan bir xil. MVP'da tomonlar shu qurilmada imzo chizadi.
- **Hakam ham** shartnomani tasdiqlaydi: hakamlikka roziligini imzo bilan bildiradi.
- **Yillik yangilash:** `reviewDate` dan 30 kun oldin eslatma keladi. Yangilash yangi versiya yaratadi, hech narsa o'zgarmagan bo'lsa ham. Bu holda versiyaga «o'zgarishsiz tasdiqlandi» degan yozuv qo'shiladi.

### 2F.4. Vazifalar va «bajarilmadi» oqimi
- `duties[]` ning har biri kuzatiladigan majburiyat sifatida saqlanadi.
- Har bir tomon «vazifamni bajara olmayapman» deb xabar berishi mumkin (`DutyIncident`): sababi, sanasi va o'rniga taklif qilingan yechim.
- Ilova shartnomaning tegishli bandini darhol ko'rsatadi: «3-band: 1 kun ichida xabar berasiz va o'rnini to'ldirasiz». Hodisa ikkala tomonning tarixida qoladi.
- Maqsad aybdor qidirish emas. Maqsad — kelishilgan qoidaga qaytish.

### 2F.5. Oylik ochiq hisob ko'rigi (6-savolning ijrosi)
- Shartnomada belgilangan davriylikda (standart — oyiga 1 marta) **«Hisobni ochiq ko'rish»** sessiyasi o'tkaziladi. Ilova uni o'zi rejalashtiradi.
- Sessiyada quyidagilar ko'rib chiqiladi: ledger yoki qarz to'lovlari, davr yakuni, ochiq vazifa hodisalari.
- Har bir tomon ko'rilgan raqamlarni **«ko'rdim, roziman»** yoki **«e'tirozim bor + izoh»** deb tasdiqlaydi.
- Natijada **ko'rik bayonnomasi** (PDF) chiqadi. U kelajakda nizo chiqqanda asosiy dalil bo'ladi (Usta buvaning daftari kabi).

### 2F.6. O'zgarmas hisob yozuvlari (dalil sifatida)
- Kelishuvga bog'langan barcha moliyaviy yozuvlar (venture ledger, qarz to'lovlari, taqsimotlar, ko'rik bayonnomalari) **faqat qo'shiladigan (append-only)** jurnal sifatida saqlanadi.
- Yozuvni tuzatish faqat yangi tuzatuvchi yozuv bilan qilinadi. Eski yozuv o'chirilmaydi va tahrirlanmaydi.
- **Taklif (muhandislik):** jurnal yozuvlari **xesh-zanjir** bilan bog'lanadi: `hash_n = H(hash_{n-1} ‖ canonical(entry_n))`. Har bir ko'rik bayonnomasida o'sha paytdagi zanjir boshi (`chainHead`) qayd etiladi. Shu tufayli bayonnomadan keyin o'tmishdagi yozuvni sezdirmasdan o'zgartirib bo'lmaydi. Bu MVP'da offline ishlaydi va server talab qilmaydi.
- **Aniq algoritm** (mobil va desktop bir xil xesh chiqarishi uchun):
  - `canonical` = RFC 8785 (JCS) bo'yicha JSON. Barcha pul va son qiymatlari **string** ko'rinishida yoziladi;
  - `H` = SHA-256 (hex, kichik harflarda);
  - `hash_n = SHA256(prevHashHex + "\n" + canonical(entry_n))`;
  - genesis uchun `prevHash` = 64 ta `0`;
  - har bir kelishuvning **o'z zanjiri** bo'ladi.
  - Test vektori: `spec/test-vectors/journal_chain.json` (`DESKTOP_PROMPT.md` 5.3).
- **Bitta hisob yurituvchi:** har bir kelishuvning jurnaliga faqat **bitta qurilma** yozuv qo'shadi (`custody.keeperDeviceId` — 6-savoldagi «hisobni kim yuritadi» javobi). Boshqa qurilmalarda jurnal faqat o'qish uchun turadi. Import paytida zanjir ayrilib ketgan bo'lsa (fork), u avtomatik birlashtirilmaydi, foydalanuvchiga hisobot ko'rsatiladi.

### 2F.7. «Katta foyda» ogohlantirishi
- Bobning saboqlaridan biri: **katta foyda kelganda xotira «o'yin» ko'rsatadi**.
- Davr foydasi rejadagidan sezilarli darajada oshsa (standart chegara: kutilgandan ≥ 150% yoki o'tgan 3 davr o'rtachasidan ≥ 200%, sozlanadi), ilova taqsimotdan **oldin** quyidagilarni taklif qiladi:
  - shartnomaning 4–5-bandlarini ikkala tomon qayta o'qib chiqishi;
  - navbatdan tashqari ochiq hisob ko'rigi o'tkazish.
- Ohang: tabriklash + ehtiyot. «Barakali foyda — tabriklaymiz! Endi kelishuvni birga qayta o'qib chiqaylik.»

### 2F.8. Nizo va hakam oqimi
- Har bir tomon `Dispute` ochishi mumkin: mavzu, tegishli bandlar va o'z talabi.
- Ilova **«hakam uchun ish papkasi»**ni (PDF) avtomatik yig'adi. Unga kiradi:
  - shartnomaning amaldagi versiyasi va versiyalar tarixi;
  - tegishli davrlar bo'yicha hisob yozuvlari va zanjir tekshiruvi natijasi;
  - ko'rik bayonnomalari;
  - vazifa hodisalari;
  - ikkala tomonning talablari.
- Hakam qarorini yozib qo'yish mumkin. Qaror kelishuv tarixiga qo'shiladi. Agar kerak bo'lsa, shartnomaning yangi versiyasi yaratiladi.
- Maqsad: ishni sudgacha olib bormaslik. Ilova sudga taalluqli yuridik maslahat bermaydi.

### 2F.9. Mavjud og'zaki kelishuvni yozib olish
- Bu haftaning 1-vazifasi: «Hozir og'zaki davom etayotgan sheriklik, ijara yoki qarz kelishuvini qog'ozga tushiring».
- Buning uchun alohida tez **ustasi** bo'ladi:
  - kelishuv o'tgan sanadan boshlangan bo'lishi mumkin (`effectiveFrom` o'tmishda);
  - shu kungacha bo'lgan holat bitta «boshlang'ich holat» yozuvi sifatida kiritiladi (kim qancha qo'shgan, qancha bo'lingan, qancha qarz qolgan);
  - tomonlar shu boshlang'ich holatni ham imzolab tasdiqlaydi.

### 2F.10. Oilaviy kelishuvlar (`FAMILY`)
- Yengil format: guvoh va hakam ixtiyoriy, imzo o'rniga oiladagi `ADULT` a'zolarning tasdig'i yetarli.
- Namunaviy shablonlar:
  - «Uyda kim nima qiladi»;
  - «Pul qayerda turadi va kim yuritadi»;
  - «Havas chegarasi» (2B.3 bilan bog'lanadi);
  - «Oylik oila kengashi qachon o'tadi».
- Ohang: odob va hurmat doirasida, buyruq yoki nazorat ohangisiz.

### 2F.11. Kontent eslatmasi
- Bobda Qur'on oyati (Baqara 282, mazmunan tarjima) va hadis («Musulmonlar o'z shartlari ustida turadilar») keltirilgan. Ular `religiousReviewStatus` jarayonidan o'tadi: manba, tarjima matni va ulamo tasdig'i talab qilinadi.

## 2G. 8-TAMOYIL: «O'ZINGIZGA SARMOYA QILING» — FUNKSIONAL TALABLAR (U16)
> Mahsulot egasi qarori, 2026-10-27: uchala makonda (Uy — U16, Kasb-kor — K9, Musofir — M6); oylik daromad avtomatik taklif qilinadi va tahrirlanadi; o'qish xarajati «Sarmoya» belgisi bilan; kurs tekshiruvi, «Ilm zakoti» yozuvi va natijani o'lchash kiradi.

Tamoyilning mazmuni: mehnat soatlarini cheksiz ko'paytirib bo'lmaydi — kunda soat ham, kuch ham chegaralangan. Daromadni oshirishning chegarasi yo'q yo'li — **bir soat mehnatning qiymatini oshirish**, ya'ni bilim va malaka. Bilim olish uchun sarflangan pul iste'mol emas, **o'zingizga sarmoya**; uni hech kim tortib ololmaydi va narx oshganda ham yechim topishga yordam beradi. O'rganganingizni boshqaga o'rgatish — bilimning «zakoti»: o'rgatgan odamning o'z bilimi ham mustahkamlanadi. Pul faqat haqiqiy hunar va bilim uchun to'lanadi, «tez boyish» orzusini sotadiganlarga emas.

### 2G.1. «Bir soatim qancha?» (`HourValue`)
- Har bir a'zo uchun hisoblanadi: **oylik halol daromad ÷ oylik ish soatlari**.
- Oylik daromad: ilova shu a'zoning oxirgi 3 to'liq oydagi daromad yozuvlari o'rtachasini **taklif qiladi** (yozuv kamroq oyda bo'lsa — borlarining o'rtachasi, umuman bo'lmasa — bo'sh). Foydalanuvchi qiymatni o'zgartira oladi; qaysi manba ishlatilgani saqlanadi (`AUTO` / `MANUAL`).
- Ish vaqti: kuniga soat (daqiqa aniqligida) × oyda ish kunlari (1–31). Yadro daqiqalarda hisoblaydi.
- Natija: 1 soat qiymati (tiyingacha, yaxlitlash qoidasi vektor bilan qotiriladi) va **«ikki barobar maqsad»** — shu qiymatning 2 hissasi.
- **Soat chegarasi** eslatmasi: kuniga 10 soatdan ko'p yoki oyiga 260 soatdan ko'p ishlansa, maslahatchi soatni yana oshirish o'rniga soat qiymatini oshirish yo'lini taklif qiladi (ayblamasdan).
- Daromad yoki vaqt 0 bo'lsa natija chiqmaydi va sababi aytiladi.

### 2G.2. «Bilim rejasi» (`LearningPlan`)
- Maydonlar: a'zo; ko'nikma; u qaysi ishni yoki soatni qimmatlashtirishi; yo'l (`BOOK` kitob, `MENTOR` ustoz, `COURSE` kurs, `PRACTICE` amaliyot — bir nechtasi); byudjet (`Money`, ixtiyoriy); haftalik o'qish vaqti; boshlanish sanasi; ko'rik sanasi (standart: +3 oy); holat (`ACTIVE`, `PAUSED`, `DONE`, `DROPPED`).
- Reja ochilganda 2G.1 dagi soat qiymati **boshlang'ich nuqta** sifatida saqlanadi (2G.5 uchun).
- Diqqat tarqalmasligi uchun bir a'zoda bir vaqtda ko'pi bilan **2 ta faol reja**.
- Juma ritmi: «Bu hafta necha soat o'qidingiz?» — o'qish vaqti yozuvi (daqiqa). Reja kartasida jami vaqt va byudjetdan sarflangani ko'rinadi.
- Pul manbasi: «Kelajagim» va zaxira pulga tegilmaydi; o'qish puli joriy byudjetdan yoki «o'sadigan pul» ulushidan (2C.3). O'qish uchun qarz olish rag'batlantirilmaydi — 2D.6 friction so'rovi amal qiladi.

### 2G.3. «Sarmoya» belgisi
- Xarajat toifasi (Zarur / Kerak / Havas) o'zgarmaydi; xarajatga qo'shimcha **«O'zimga sarmoya»** belgisi qo'yiladi va u bilim rejasiga bog'lanishi mumkin.
- Belgili xarajat **havas chegarasiga** (2B.3) kirmaydi.
- Oylik hisobotda alohida qator: «O'zimga sarmoya: X so'm — daromadning Y %» (bazis punktlarda, vektor bilan).
- Tavsiya qilingan majburiy foiz yo'q; ilova o'qishdan keyin daromad oshishini **va'da qilmaydi**.

### 2G.4. Kurs yoki ustoz taklifini tekshirish
- 2E.5 taklif detektorining kurs turi (`COURSE`). Tekshiruv belgilari:
  - `FAST_RICH` — qisqa muddatda boylik yoki katta daromad va'dasi;
  - `SECRET_FORMULA` — «sir», «hech kim aytmaydigan usul» kabi da'vo;
  - `INCOME_GUARANTEE` — kursdan keyin daromad yoki ish kafolati;
  - `NO_SYLLABUS` — dastur va amaliy natija (nimani qila olishingiz) yozilmagan;
  - `UNVERIFIABLE_TEACHER` — o'qituvchining amaliy ishini ko'rib, tekshirib bo'lmaydi;
  - `PRESSURE` — «bugun oxirgi kun», shoshiltiruvchi chegirma;
  - `RECRUIT` — boshqalarni olib kelsangiz pulingiz qaytadi;
  - `NO_TRIAL_OR_REFUND` — sinov darsi ham, pulni qaytarish sharti ham yo'q.
- Natija: belgi yo'q — yashil; bitta belgi — sariq («aniqlashtiring»); 2 va undan ko'p belgi yoki `INCOME_GUARANTEE` / `RECRUIT` ning o'zi — qizil («pul to'lamang»). Har bir belgi izohlanadi. Qaror jadvali vektor bilan qotiriladi.
- Bilim rejasida `COURSE` yo'li tanlansa, tekshiruv taklif qilinadi.

### 2G.5. Natijani o'lchash
- Ko'rik sanasida (yoki foydalanuvchi istagan paytda) soat qiymati 2G.1 bo'yicha qayta hisoblanadi va boshlang'ich nuqta bilan solishtiriladi: farq so'mda va bazis punktlarda (vektor bilan).
- O'sish bo'lmasa yoki pasaysa, uyaltirilmaydi: rejani davom ettirish, o'zgartirish yoki yopish taklif qilinadi.
- Boshlang'ich qiymat 0 bo'lsa foiz chiqmaydi, faqat yangi qiymat ko'rsatiladi.

### 2G.6. «Ilm zakoti» — o'rgatish yozuvi (`TeachingLog`)
- Yozuv: sana, kimga (ixtiyoriy, ism yoki «qo'shni», «xodim»), nimani o'rgatdi, qancha vaqt.
- Juma ritmida eslatma: «Bu hafta bilganingizdan biror narsani kimgadir o'rgatdingizmi?» Oylik hisobotda soni ko'rinadi. Pul hisobi yo'q.

### 2G.7. Bob va haftalik vazifalar
- Bob matni, misollari va hikoyasi — o'zimiz yozganlari (personaj — mavjud persona: taksichi, tikuvchi va h.k.).
- Haftalik 3 vazifa:
  1. Bir soatingiz qiymatini hisoblang va uni ikki barobar qila oladigan bitta ko'nikmani yozing.
  2. Shu ko'nikmaga olib boradigan bitta yo'lni tanlang; pullik kurs bo'lsa — avval tekshiruvdan o'tkazing.
  3. Bilganingizdan bir narsani shu hafta bir kishiga o'rgating va yozib qo'ying.

### 2G.8. Kontent eslatmasi
- Bobda ilm o'rganish va ishni puxta bajarish haqidagi diniy matnlar keltirilsa, ular `religiousReviewStatus` jarayonidan o'tadi (manba, tarjima, ulamo tasdig'i).

## 3. MAHSULOT CHEKLOVLARI (qat'iy)
- Ilovada foizli kredit, mikroqarz yoki «tez pul» reklamalari va integratsiyalari **bo'lmaydi**.
- Kreditlar faqat qarzdan chiqish maqsadida kuzatiladi. Yangi qarz olish rag'batlantirilmaydi.
- Tone of voice — moliyaviy maslahatchi uslubida: iliq, ayblamaydigan, savol orqali o'ylashga undaydigan. Uyaltirish yoki qo'rqitish taqiqlanadi.
- Har bir ta'limiy ekranda disklеymer bo'ladi: «Ta'limiy material. Fatvo yoki moliyaviy maslahat emas».
- Va'da yo'q: «X oyda mashina» kabi gaplar taqiqlanadi.
- Ilovadagi hech bir hisob-kitob, prognoz yoki taqqoslash foiz stavkasini «muqobil daromad» sifatida ishlatmaydi. «Bankda tursa X% olardingiz» kabi matnlar taqiqlanadi.
- Ilovada foizli qarz **berish**ni qayd etish imkoni yo'q.
- **Diniy matnlar** (oyat, hadis, rivoyat) faqat malakali ulamo tomonidan tekshirilgan va manbasi ko'rsatilgan holda chiqariladi. Ular kontentdagi `religiousReviewStatus` maydoni orqali boshqariladi. Tasdiqlanmagan diniy matn production'ga chiqmaydi.
- Kelishuv hujjatlarida ilova **yuridik kafolat bermaydi** va yuridik maslahat ko'rsatmaydi. Shablonlar yurist ko'rigidan o'tadi (`reviewStatus`).
- Hisob jurnalidagi yozuvlar (2F.6) hech qanday holatda tahrirlanmaydi va o'chirilmaydi, faqat tuzatuvchi yozuv qo'shiladi.
- Ilova baxillikka undamaydi. Tejash ko'rsatkichlari sadaqa yoki zarur xarajatlarni kamaytirishni hech qachon «yutuq» deb ko'rsatmaydi.

## 4. TEXNOLOGIK STEK — QAT'IY QARORLAR (0-bosqich, ADR)
> Bu bo'limdagi qarorlar **o'zgarmaydi**. AI-dasturchi ularni o'z bilganicha almashtirmaydi. O'zgartirish zarur bo'lsa, avval sababini yozib, ruxsat so'raydi.

### 4.1. Stek
| Qatlam | Tanlov |
|---|---|
| UI | Flutter stable (versiya `.fvmrc` orqali qotiriladi), Dart 3 |
| State management | **Riverpod 2** (`riverpod_generator` + `riverpod_annotation`) |
| Navigatsiya | **go_router** |
| Modellar | `freezed` + `json_serializable` |
| Lokal baza | **Drift + SQLCipher** (`sqlcipher_flutter_libs`). Isar va Hive ishlatilmaydi |
| Native qatlam | **Kotlin**: Android Keystore, `androidx.biometric`, root va emulyator evristikalari, `FLAG_SECURE`, WorkManager, bildirishnomalar |
| Flutter ↔ Kotlin | **Pigeon** (type-safe kontrakt; qo'lda yozilgan `MethodChannel` taqiqlanadi) |
| Lokalizatsiya | `flutter gen-l10n`, ARB: `uz` (asosiy, lotin), `ru` |
| Lint | `very_good_analysis` (yoki shunga teng qat'iy lint), `strict-casts`, `strict-raw-types` |
| Testlar | `flutter_test`, `mocktail`, in-memory Drift; Kotlin uchun JUnit |
| CI | GitHub Actions: `format → analyze → test → build apk` |
| Android | **minSdk 26**, targetSdk eng so'nggi barqaror versiya |
| Backend | **MVP-1 da backend yo'q** (to'liq offline). Oilaviy sinxronlash bosqichida **Kotlin + Ktor + PostgreSQL** ishlatiladi va server O'zbekiston hududida joylashadi |

### 4.2. Pul modeli (`Money`)
- `Money(int minorUnits, CurrencyCode currency)` immutable value-object bo'ladi. `double` va `num` pul uchun **taqiqlanadi**.
- Valyutalar: `UZS` (minor = tiyin, 2 xona), `USD` (cent), `EUR` va `RUB`. Asosiy valyuta `UZS`.
- Har xil valyutadagi summalarni to'g'ridan-to'g'ri qo'shish **mumkin emas**. Konvertatsiya faqat `FxRate(from, to, rate, date, source)` snapshoti orqali qilinadi. MVP'da kursni foydalanuvchi qo'lda kiritadi.
- Ulushlarga bo'lish (10%, 70/20/10, foyda taqsimoti) **largest remainder** usuli bilan qilinadi: qismlar yig'indisi har doim butun summaga aniq teng chiqadi. Bu property-based testlar bilan tekshiriladi.
- Yaxlitlash qoidasi markazlashgan bo'ladi (`MoneyRounding`), kod bo'ylab tarqoq yaxlitlash taqiqlanadi.
- **Desktop ilova bilan moslik:** pul algoritmlarining aniq ta'rifi va umumiy oltin test vektorlari `spec/test-vectors/` da (`DESKTOP_PROMPT.md` 4–5-bo'limlar). Ular mobil ilova uchun ham **majburiy**: largest remainder'da teng kasr bo'lsa kichik indeks ustun; `percentOf = allocate([bp, 10000−bp])[0]`; amortizatsiyada half-up. Mobil CI ham shu vektorlardan o'tishi shart. Eksport formati (`spec/interchange/`) ham umumiy.

### 4.3. Aktivlar abstraksiyasi (`Asset`) — 7-tamoyil (zakot) uchun zaxira
- Har bir qiymat saqlovchi narsa `Asset` hisoblanadi: `type` (`CASH | BANK_CARD | VAULT | GOLD | SILVER | FOREIGN_CURRENCY | RECEIVABLE | TRADE_GOODS | BUSINESS_SHARE`), `quantity` (integer, minor birlikda; oltin uchun milligramm), `unit`, `currency?`, `acquiredAt`.
- MVP-1 da faqat `CASH` va `VAULT` ishlatiladi, lekin jadval va interfeys **boshidan** shu ko'rinishda quriladi. Keyingi bosqichlarda migratsiya kerak bo'lmasligi uchun.
- Har bir `Asset` uchun «balans tarixi» (snapshotlar) saqlanadi. Bu zakotdagi hawl (1 yil) hisobi uchun kerak bo'ladi.

### 4.4. Ma'lumotlar konvensiyalari (kelajakdagi sinxronlash uchun)
- Barcha ID'lar **UUIDv7** (string). Autoincrement ID ishlatilmaydi.
- Har bir jadvalda quyidagi maydonlar bo'ladi: `householdId`, `createdAt`, `updatedAt` (UTC), `deletedAt?` (soft delete), `version` (int).
- Vaqt UTC instant sifatida saqlanadi. Byudjet davrlari esa **lokal sana** bo'yicha hisoblanadi (`Asia/Tashkent`).
- Haftalik sikl jumadan boshlanadi (`weekAnchor = FRIDAY`) va sozlanadi. Oylik davrning boshlanish kuni ham sozlanadi (oylik kuni).
- Kelajak bosqichlardagi maydonlar (masalan, `Expense.necessity`) jadvalga **hozirdan nullable** qilib qo'shiladi.
- Drift sxemasi versiyalanadi va har bir migratsiya test bilan qoplanadi.

### 4.5. Kalitlar va shifrlash
- DB kaliti 256-bit tasodifiy qilib yaratiladi va Android Keystore'dagi AES-GCM kalit bilan **wrap** qilinadi (Kotlin tomonda). Wrap qilingan blob ilovaning private storage'ida saqlanadi.
- Keystore kalit qurilmada StrongBox mavjud bo'lsa, StrongBox'da yaratiladi.
- PIN to'g'ridan-to'g'ri saqlanmaydi. Undan Argon2id (yoki PBKDF2-SHA256, ≥310k iteratsiya) orqali hosila olinadi va faqat tekshiruv uchun ishlatiladi.

## 5. ARXITEKTURA VA DOMEN MODELI
- Clean Architecture (`presentation / domain / data`) va feature-first modul tuzilmasi.
- Offline-first: barcha asosiy funksiyalar internetsiz ishlaydi.
- Pul faqat `Money(minorUnits, currency)` ko'rinishida saqlanadi (4.2). `double` taqiqlanadi.
- Barcha qiymat saqlovchilar `Asset` orqali modellashtiriladi (4.3).
- Dastlabki entitylar:
  `Household`, `Member`, `Income`, `Expense`, `Category`, `Obligation`, `NasiyaDebt`, `Vault` («Kelajagim»), `AllocationRule`, `VaultTransaction`, `MonthlyReport`, `Chapter`, `Law`, `DaftarPage` (foydalanuvchi yozgan qonun), `WeeklyTask`, `TaskCompletion`, `Streak`.
- 2-tamoyil bilan qo'shilganlar:
  `Necessity` (enum: `ZARUR | KERAK | HAVAS`), `ExpenseTemplate`, `HavasLimit` + `LimitConsent`, `Envelope` + `EnvelopePeriod`, `Subscription` (recurring), `ScheduledTreat`, `Habit`, `SavingsRescue` (qutqarilgan pul yozuvi).
- 3-tamoyil bilan qo'shilganlar:
  `VaultType` (enum: `QOROVUL | OSADIGAN`), `EmergencyTarget` (hisoblangan), `PriceBasket`, `BasketItem`, `PricePoint`, `PersonalInflationIndex`, `ReadinessGate`, `Debt` (`creditorType`: `BANK | SHOP | RELATIVE | FRIEND | OTHER`; `reason`, `hasMarkup`, `monthlyPayment`, `dueDate`), `Receivable` (foydalanuvchi bergan qarz), `IncomeSourceType` (`TER | MOL | TAVAKKAL | RIBO`).
- `NasiyaDebt` endi `Debt` ning `SHOP` turiga birlashtiriladi.
- 4-tamoyil bilan qo'shilganlar:
  `BudgetMode` (enum: `STANDARD | DEBT_RECOVERY`), `AllocationSplit` (masalan, 70/20/10), `PayoffPlan`, `PayoffStrategy`, `Prepayment`, `DebtContributor`, `LoanReceipt` (tilxat: tomonlar, `witnesses[]`, `confirmedByCounterparty`), `RepaymentSchedule`, `BorrowCheck` (friction so'rovi natijasi), `SellableItem`, `CeremonyPlan`, `CeremonyBudgetLine`, `FundingSource` (`SAVINGS | FAMILY | EXPECTED_GIFTS | DEBT`), `CeremonyScenario`, `Goal`.
- `Debt` qo'shimcha maydonlari: `principal`, `totalPaid`, `markupAmount`, `earlyRepaymentTerms`, `priority`.
- 5-tamoyil bilan qo'shilganlar:
  `Partnership` (`type`: `MUDARABA | MUSHARAKA`; `term`, `status`), `PartnerRole` (`CAPITAL_PROVIDER | WORKER | BOTH`), `CapitalContribution` (pul yoki uskuna), `ProfitShareRule`, `LossRule`, `PartnershipContract` (versiyalangan, `signatures[]`, `witnesses[]`), `BuyoutSchedule`, `VentureLedger`, `VentureEntry`, `ProfitDistribution`, `ForceMajeureEvent` (`negligence` bayrog'i bilan), `Skill`, `VentureIdea` (CAPEX, stsenariylar), `OfferCheck` (kafolatlangan foyda detektori natijasi).
- 6-tamoyil bilan qo'shilganlar:
  `Agreement` (`type`: `PARTNERSHIP | LOAN | RENT | SERVICE | FAMILY | OTHER`; `effectiveFrom`, `term`, `reviewDate`, `status`: `DRAFT | SIGNED | ACTIVE | IN_DISPUTE | CLOSED`), `AgreementVersion`, `AgreementParty`, `Contribution`, `Duty` (`ownerPartyId` — yagona mas'ul, `breachClause`), `DutyIncident`, `CustodyRule` (`reviewEvery`), `ExitClause`, `Arbiter`, `Signature` (`role`: `PARTY | WITNESS | ARBITER`), `QuestionStatus` (9 savol bo'yicha: `ANSWERED | NOT_APPLICABLE + reason`), `OpeningBalance` (og'zaki kelishuvni yozish uchun), `AccountReview` + `ReviewAck` (`AGREE | OBJECT + note`, `chainHead`), `JournalEntry` (append-only, `prevHash`, `hash`), `ProfitSpikeAlert`, `Dispute`, `ArbiterDecision`.
- **Refaktor:** `LoanReceipt` → `Agreement(type = LOAN)`, `PartnershipContract` → `Agreement(type = PARTNERSHIP)` + `Partnership` (2E.1 qoidalari). `VentureEntry` va `DebtPayment` `JournalEntry` orqali yoziladi.
- `Expense` qo'shimcha maydonlari: `necessity`, `paymentChannel` (`CASH | CARD`), `envelopeId?`, `isGift`, `isOstentation`, `fundedByDebt`, `memberId`.

## 6. XAVFSIZLIK TALABLARI
- Maxfiy kalitlar faqat Android Keystore'da saqlanadi. Ilova ichida hardcode qilingan kalit bo'lmaydi.
- TLS va certificate pinning.
- Biometrik yoki PIN orqali kirish, sessiya timeout.
- Root, emulyator, debugger va qayta imzolashni aniqlash.
- Moliyaviy ekranlarda `FLAG_SECURE` yoqiladi.
- Lokal baza Drift + SQLCipher bilan shifrlanadi, kalit 4.5 dagi tartibda boshqariladi.
- Loglarda summa, ism yoki boshqa shaxsiy ma'lumot chiqarilmaydi. Release build'da `print` va `debugPrint` o'chiriladi.
- Backup: `android:allowBackup="false"`. Eksport qilish faqat foydalanuvchi tanlagan parol bilan shifrlangan fayl orqali mumkin.

## 7. REGULYATIV CHEKLOVLAR (O'zbekiston)
- Shaxsiy ma'lumotlar O'zbekiston hududidagi serverlarda saqlanadi.
- MVP **haqiqiy pulni saqlamaydi va o'tkazmaydi**: «Kelajagim» virtual jamg'arma sifatida ishlaydi. Shu sababli Markaziy bank litsenziyasi kerak emas. Haqiqiy alohida karta yoki hamyon keyinchalik faqat litsenziyali bank yoki to'lov tashkiloti bilan hamkorlikda qo'shiladi.
- «Baraka daftari» nomi va boshqa mualliflarning kontenti ishlatilmaydi; ilova nomi — «Baraka Dastur» (`BARAKA_OILASI.md` 2.1).

## 8. INTEGRATSIYALAR
_[keyingi matnlardan to'ldiriladi]_ — ehtimoliy: bank kartasi orqali avtomatik ajratish (hamkor bank), UzCard/HUMO tranzaksiya importi.

## 9. UI/UX
- Til: o'zbek (lotin) asosiy, rus ikkinchi.
- Metafora — **daftar**: qog'oz teksturasi, qo'lda yozilgan tamoyillar, «daftar sahifasi».
- Bosh ekranda: «O'zingizga to'langan» summa, «Kelajagim» balansi, streak, shu haftaning 3 vazifasi va juma bobi.
- Moliyaviy maslahatchi maslahatlari kontekstga mos holda chiqadi.
- Xarajatlar Zarur / Kerak / Havas ranglari bilan ajratiladi. Havas uchun qizil emas, neytral rang ishlatiladi (havas «gunoh» emas).
- Oila kengashi ekrani: kategoriyalarni toifalarga ajratish va havas chegarasini birgalikda tasdiqlash.

## 10. 8 TAMOYIL — HOLAT
| # | Tamoyil | Holat |
|---|---|---|
| 1 | O'zingizga avval to'lang — har daromaddan ulush | ✅ Spetsifikatsiya yozildi |
| 2 | Xarajatni yozing — pul qayerga oqayotganini toping | ✅ Spetsifikatsiya yozildi |
| 3 | Pulni ishlating — zaxira va o'sadigan pul | ✅ Spetsifikatsiya yozildi |
| 4 | Ribodan saqlaning — qarzdan reja bilan chiqing | ✅ Spetsifikatsiya yozildi |
| 5 | Pulni halol ishga soling — savdo va sheriklik | ✅ Spetsifikatsiya yozildi |
| 6 | Kelishuvni yozing — 9 savollik shartnoma | ✅ Spetsifikatsiya yozildi |
| 7 | Firibgarlik va shoshilinch katta qarorlardan saqlaning | ✅ Musofir makonida (M3, M5): sovutish davri, besh xavf belgisi; Uy U12 «Taklifni tekshirish» bilan umumiy |
| 8 | O'zingizga sarmoya qiling — soat qiymatini bilim bilan oshiring | 📝 Spetsifikatsiya yozildi (2G); reja: U16a/b/c, K9, M6 |

## 11. ISHLAB CHIQISH BOSQICHLARI
- **MVP-1:** daromad va xarajatni kiritish, «Kelajagim» virtual jamg'armasi va avto-ulush, «Kimning puli?», oylik audit, 1-bob kontenti va haftalik vazifalar.
- **MVP-2:** Zarur/Kerak/Havas tasnifi, xarajat shablonlari va vidjet, havas chegarasi (oilaviy kelishuv bilan), konvertlar, obunalar ro'yxati (qo'lda kiritiladi), «Qutqarilgan pul» metrikasi va uni «Kelajagim»ga o'tkazish, «Juma shirinligi», 2-bob kontenti.
- **MVP-3:** «Narx daftari» va shaxsiy inflyatsiya indeksi, «Sichqon kemirgani» kalkulyatori, zaxira pul / o'sadigan pul ajratmasi va avtomatik zaxira maqsadi, tayyorgarlik darvozasi, to'liq qarz inventari va bergan qarzlar ro'yxati, 3-bob kontenti, odat asosida bob ochilishi.
- **MVP-4:** `DEBT_RECOVERY` rejimi (70/20/10), payoff planner (odatiy va tezlashtirilgan grafik), qarzning haqiqiy narxi, qarz tilxati (PDF va ikki tomonlama tasdiq), yangi qarz oldidan friction so'rovi, sotiladigan buyumlar, marosim rejalovchisi va stsenariylarni taqqoslash, «qarzsiz kun», 4-bob kontenti.
- **MVP-5:** sheriklik moduli (mudoraba / musharaka validatsiyasi bilan), shartnoma ustasi (PDF va ko'p tomonlama tasdiq), venture ledger va avtomatik foyda/zarar taqsimoti, buyout jadvali, «Hunardan ishga» rejalovchisi, «kafolatlangan foyda» detektori, zaxira pul maqsadi 6 oyga oshirildi, 5-bob kontenti.
- **MVP-6:** umumiy kelishuv dvigateli (9 savol, to'liqlik indikatori, turlar), tilxat va sheriklik shartnomasini shu dvigatelga ko'chirish, vazifalar va «bajarilmadi» oqimi, oylik ochiq hisob ko'rigi va bayonnomalar, append-only jurnal va xesh-zanjir, «katta foyda» ogohlantirishi, nizo va hakam papkasi, og'zaki kelishuvni yozib olish, oilaviy kelishuvlar, 6-bob kontenti.
- **Keyinroq:** bank tranzaksiyalaridan obunalarni avtomatik aniqlash, rasmiy CPI bilan taqqoslash, sertifikatlangan islomiy moliya hamkorlari, yosh oila jamg'armasiga real pul o'tkazmalari (hamkor bank), e'lon saytlariga eksport.
- **MVP-8 (U16):** «Bir soatim qancha?», bilim rejasi, «Sarmoya» belgisi, kurs tekshiruvi, natijani o'lchash, «Ilm zakoti» yozuvi, 8-bob kontenti.
- **Keyingi bosqichlar:** keyingi tamoyillar bo'yicha qo'shiladi.
- **Amaliy reja:** MVP-1…6 offline holatda birlashtirilib, 17 ta vazifaga bo'lingan (6-tamoyil uchun 9A va 14A vazifalari qo'shilgan). Batafsil reja `docs/MVP_PLAN.md` da (`MVP_5_QONUN.md`). Backend talab qiladigan funksiyalar MVP'da qurilma ichidagi muqobil bilan almashtiriladi: ikkinchi tomonning tasdig'i (2D.5), to'lovchini taklif qilish (2D.4) va sherik uchun read-only ko'rinish (2E.3).

## 12. AI-DASTURCHI UCHUN QOIDALAR
- Har bir modulni alohida va testlari bilan yoz.
- Pul hisob-kitoblari uchun unit-testlar majburiy: ulush, yaxlitlash va oy yakuni.
- Noaniq joy bo'lsa, taxmin qilishdan oldin so'ra.
- 4-bo'lim (ADR) qarorlarini ruxsatsiz o'zgartirma. Yangi paket qo'shishdan oldin uning sababini yoz.
- Har bir sessiyada faqat berilgan bosqich yoki vazifa ustida ishla. Keyingi bosqich funksiyalarini «qo'shimcha» sifatida yozma.
- Ta'limiy matnlar — faqat o'zimiz yozganlari. Boshqa mualliflarning qissa matnlarini repoga ham, ilovaga ham ko'chirma.
- Kod, identifikatorlar va buyruqlar inglizcha. Izohlar, hujjatlar va UI matnlari o'zbekcha.
