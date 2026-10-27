# «KASB-KOR» MAKONI — SPETSIFIKATSIYA
### O'zini o'zi band qilganlar, kichik va o'rta biznes egalari uchun ribosiz hisob va odatlar daftari

> Versiya: **v0.1 — QORALAMA (K0)**; K1 (2-bo'lim), K2 (3-bo'lim), K3 (4.5), K4 (5-bo'lim), K5 (4.1–4.4), K6 (7-bo'lim), K7 (6, 8-bo'limlar) va K8 (12-bo'lim, ADR-0003) amalga oshirildi — farqlari 2.4, 3.4, 4.6, 4.7, 5.4, 6.3, 7.3, 8.5 va 12.1 da. Android UI — A3 da qilindi (1.0.0). Holat: mahsulot egasi tasdig'i kutilmoqda; ulamo va yurist savollari `docs/OPEN_QUESTIONS.md` da (OQ-K*, OQ-D5, OQ-D7, OQ-Y3, OQ-Y6, OQ-Y7).
> Manba: `docs/BARAKA_OILASI.md` 2.2 («Kasb-kor — qisqa karta»). Format — `docs/uy/SPEC.md` kabi.
> Bu hujjat **mahsulot va qoidalarni** belgilaydi. Texnik qarorlar (stek, saqlash, shifrlash, sinxronlash, PDF, i18n) — `docs/BARAKA_OILASI.md` (3–13-bo'limlar); bu yerda ularga faqat havola qilinadi.

---

## 0. HUJJAT HAQIDA
- Kasb-kor — bitta «Baraka» ilovasidagi ikkinchi makon (`SpaceKind::KASBKOR`). Uy makoni (`docs/uy/SPEC.md`) bilan bir xonadon, bir baza, bir PIN, bir jurnal dvigateli; chegarasi — 1-tamoyilning o'zi («ikki cho'ntak»).
- Hamma pul hisoblari faqat yadroda (`core/`), `Money` va `round_half_up` bilan (`BARAKA_OILASI.md` 5). Har bir yangi pul funksiyasi uchun avval `spec/test-vectors/` ga oracle bilan hisoblangan vektor yoziladi (9-bo'limdagi suite'lar).
- Miqdorlar (kg, litr, dona, metr) **butun sonda, eng kichik birlikda** saqlanadi (gramm, millilitr, dona, millimetr) — `f64` yo'q.
- Uy makonida tayyor bo'lgan mexanizmlar qayta ishlatiladi: kelishuv dvigateli va 9 savol (U7/U11), o'zgarmas jurnal va bayonnoma (U12/U13), qarz inventari va «to'xta va o'yla» (U8), `allocate` (largest remainder), tayyorgarlik darvozasi (U6/U11), «Hunardan ishga» stsenariylari (U12), `.baraka` almashish (U14), PDF (Y6).

## 1. MAHSULOT MOHIYATI
**Asosiy tashxis:** «Aylanma bor, egasi boyimaydi». Pul ko'p aylanadi, lekin:
- **cho'ntak bitta** — do'kon kassasi oilaning hamyoni ham, egasi kerak bo'lganda oladi va yozmaydi;
- **foyda aslida maosh** — egasining o'z mehnati, oila a'zolarining yordami va uskunaning eskirishi hisobga olinmaydi, «foyda» degan narsa egasining ish haqidan kam bo'lib chiqadi;
- **kapitalni inflyatsiya yeydi** — tovar eski narxda hisoblanib sotiladi, qayta olishga pul yetmaydi;
- **nasiya yig'ilmaydi** — kim, qancha, qachongacha — yozilmagan; yozilgan bo'lsa ham ko'rib chiqilmaydi.

**Falsafa:** ribo yo'q; kengayish — jamg'arma, sheriklik va reja bilan. Soliq to'lash — halollikning bir qismi, yashirish vositasi emas.

**Odat ritmi:** har kuni kassa yopish (5 daqiqa) → har hafta nasiya ko'rigi → har oy «Hisob kuni» → har yil inventarizatsiya va zakot.

**Bosh ekran:** 1-raqam — **«Haqiqiy foyda (shu oy)»**; 2-raqam — **«Egasiga to'langan maosh (shu oy)»**. Keyin: kassa holati (bugun yopilganmi), mijozlardagi pul (nasiya), muzlagan tovar, keyingi «Hisob kuni».

**Bu makon nima EMAS:** ERP, buxgalteriya yoki 1C o'rnini bosuvchi tizim; onlayn (fiskal) kassa; soliq hisobotini tayyorlovchi yoki topshiruvchi; «ikkinchi daftar» — daromadni yashirish vositasi; kredit, investor yoki sheriklar bozori; bank yoki to'lov integratsiyasi (CSV importdan tashqari). Ilova **boshqaruv hisobi** (egasi o'zi uchun) yuritadi; qonun talab qiladigan fiskal qurilmalar va hisobotlar o'rnini bosmaydi.

### 1.1. Kontent tuzilmasi
- Kasb-kor darslari 8 tamoyilni ochadi (har tamoyil — 1–2 bob). Bob tuzilmasi Uy makonidagidek: o'zimiz yozgan qisqa hikoya yoki misol, «Daftar sahifasi», 3 ta haftalik amaliy vazifa (`docs/uy/SPEC.md` 1.1). Kontent dvigateli — U3.
- Kontent: faqat o'zimiz yozgan matnlar; boshqa mualliflarning qissalari, personajlari va brendi ishlatilmaydi (`BARAKA_OILASI.md` 2.1).
- Har bir ta'limiy ekranda: «Ta'limiy material. Fatvo, moliyaviy, soliq yoki yuridik maslahat emas».

### 1.2. Personajlar
| Personaj | Segment | Moliyaviy xulq | Ilova nimani yechishi kerak |
|---|---|---|---|
| **Feruza** — atelye (3 tikuvchi) | Buyurtma bo'yicha xizmat, mato va furnitura xaridi | Uy daftarini yuritadi, lekin atelye puli bilan aralashib ketadi; qizi bepul yordam beradi | Ikki cho'ntak, egasi maoshi, o'z mehnati va oilaviy mehnat tannarxda, buyurtma bo'yicha haqiqiy foyda |
| **Bahodir aka** — mahalla do'koni | Kundalik savdo, ko'p tovar, naqd va karta | Kassadan kerak bo'lganda oladi, nasiya daftari qog'ozda, tovar «turibdi» | Kunlik kassa yopish, «egasi oldi», nasiya daftari va haftalik ko'rik, tovar qoldig'i va qayta tiklash narxi |
| **Jasur** — usta (santexnik) | Xizmat + material, buyurtmalar notekis | Avansni olib, materialga yetmay qoladi; asboblari eskiradi | Buyurtma kalkulyatori (mehnat, material, yo'l, eskirish), avans va material puli ajratilishi |
| **Malika** — Instagram do'kon | Onlayn savdo, yetkazib berish, qaytarishlar | Reklama va yetkazishni hisoblamaydi, nasiyaga (bo'lib to'lash) sotadi | Kanal xarajatlari, qaytarishlar, nasiya narxini qotirish va jadval |
| **Olim va Odil** — aka-uka choyxonasi | Oilaviy sheriklik | Kim qancha qo'ygani va olgani yozilmagan, xodim avanslari og'zaki | Sheriklik shartnomasi (U11), kassa daftari (U12), xodim va avans kelishuvi |
| **Moliyaviy maslahatchi** | Ilovadagi yo'l ko'rsatuvchi ovoz (ismsiz, personaj emas) | — | Savol beradi, hisoblatadi, ayblamaydi |

## 2. 1-TAMOYIL: «IKKI CHO'NTAK» — FUNKSIONAL TALABLAR (K1)
Tamoyilning mazmuni: biznes puli — **omonat**. Egasi undan o'zboshimchalik bilan olmaydi; o'ziga **qat'iy maosh** belgilaydi va uni Uy cho'ntagiga o'tkazadi.

### 2.1. Tushum va chiqim
- Tushum: summa, kanal (naqd, karta, o'tkazma), sana, ixtiyoriy buyurtma/mijoz, ixtiyoriy tovarlar (2.3 va 4-bo'lim bilan bog'lanadi). Kiritish — 2–3 bosishda; desktopda `Ctrl+N`, kunlik jadvalda Excel uslubida (`DESKTOP_PROMPT.md` 7).
- Chiqim turlari: **tovar xaridi** (zaxiraga kiradi, xarajat emas — 4-bo'lim), **operatsion xarajat** (ijara, kommunal, ish haqi, yo'l, reklama, soliq, uskuna ta'miri), **uskuna sotib olish** (aktiv — 3.3).
- Standart kategoriyalar allaqachon bor (`category.kk.*`: material, ijara, ish haqi, transport, marketing, soliq, uskuna, boshqa).

### 2.2. «Egasi oldi» va egasi maoshi
- **«Egasi oldi»** (`OWNER_DRAW`) — biznes kassasidan egasining shaxsiy ehtiyoji uchun olingan har bir pul. Xarajat emas, foydani kamaytirmaydi, lekin **shu oy maoshidan avans** sifatida hisoblanadi.
- **Egasi maoshi** — oylik qat'iy summa (onboarding'da va sozlamalarda). «Hisob kuni»da yoki qo'lda: maosh − shu oy «egasi oldi» = Uy'ga o'tkaziladigan qoldiq.
- O'tkazma — makonlararo (`BARAKA_OILASI.md` 4.6): bitta tranzaksiyada Kasb-kor'da chiqim (`OWNER_SALARY`) va Uy'da daromad; Uy tomonida 1-tamoyil ulushi taklif qilinadi. Uy'dagi `sourceType` — OQ-K2.
- «Egasi oldi» maoshdan oshsa — ayblamasdan, savol bilan: «Bu oy maoshdan X so'm ko'p olindi. Keyingi oy maoshidan ushlab qolamizmi yoki maoshni qayta ko'rib chiqamizmi?».
- Bosh ekran 2-raqami: «Egasiga to'langan maosh (shu oy)» = Uy'ga o'tkazilgan maosh + shu oy «egasi oldi».

### 2.3. Biznes qoldiqlari
- Naqd kassa, karta/hisob raqami — alohida «hamyonlar» (`Asset`, `asset_type = CASH | BANK`), Uy makonidagi pul bilan aralashmaydi.
- Biznesga egasining shaxsiy pulidan qo'shilgan mablag' — **kapital kiritish** (`OWNER_CONTRIBUTION`), qarz emas va tushum emas.

### 2.4. K1 da qanday qilindi (farqlar)
- Hamyonlar alohida `Asset` yozuvi emas: `kk_moves.wallet` / `incomes.channel` / `expenses.channel` = `CASH | CARD`; boshlang'ich qoldiq — `OPENING` harakati. Bank hisob raqami — hozircha «karta».
- Tushum kanali: naqd yoki karta («o'tkazma» — karta sifatida).
- Maosh sozlamalarda emas, Kasb-kor bosh sahifasidagi «Egasining maoshi» kartasida belgilanadi; onboarding'da so'ralmaydi.
- «Maoshdan ko'p olindi» — savol ko'rsatiladi; keyingi oy maoshidan ushlab qolish «Hisob kuni» bilan (K3).
- Uy'dagi `sourceType` — vaqtincha `TER` (OQ-K2).

## 3. 2-TAMOYIL: «HAQIQIY FOYDANI BIL» — FUNKSIONAL TALABLAR (K2)
Tamoyilning mazmuni: egasining mehnati, oila a'zolarining yordami va uskunaning eskirishi tannarxga kirmaguncha «foyda» — aslida maosh.

### 3.1. Haqiqiy foyda formulasi
```
Ko'rinadigan foyda = Tushum − Sotilgan tovar tannarxi − Operatsion xarajatlar
Haqiqiy foyda      = Ko'rinadigan foyda − O'z mehnati bahosi − Oilaviy mehnat bahosi − Eskirish
```
- **O'z mehnati bahosi** — egasi o'z ishini yollanma odamga topshirsa, unga oyiga qancha to'lardi (foydalanuvchi kiritadi; OQ-K5). Egasi maoshi (2.2) undan farq qilishi mumkin — ekran ikkalasini yonma-yon ko'rsatadi.
- **Oilaviy mehnat** — a'zo, soat, soat bahosi; pul to'lanmasa ham tannarxga kiradi («qizingizning 80 soati ham xarajat»). To'langan bo'lsa — operatsion xarajat (ikki marta hisoblanmaydi).
- **Eskirish** — uskuna narxi (minus qoldiq qiymati) foydali muddat oylariga `allocate` bilan teng bo'linadi (qoldiq tiyinlar birinchi oylarga); yig'indi aniq narxga teng.

**Misol (Feruza, oy):** tushum 18 000 000; mato va furnitura 6 000 000; ijara 2 000 000; kommunal 500 000 → ko'rinadigan foyda **9 500 000**. O'z mehnati 5 000 000; qizining yordami 80 soat × 15 000 = 1 200 000; 2 ta tikuv mashinasi 12 000 000, 60 oy → eskirish 200 000. **Haqiqiy foyda = 3 100 000 so'm.**

**Eskirish yaxlitlash misoli:** 7 000 000 so'm, 36 oy → 700 000 000 tiyin / 36 = 19 444 444, qoldiq 16 → 16 oy 194 444,45 so'm, 20 oy 194 444,44 so'm; jami 7 000 000,00.

### 3.2. Buyurtma kalkulyatori (xizmat ko'rsatuvchilar uchun)
- Material + mehnat soati × soat bahosi + yo'l + eskirish ulushi + (ixtiyoriy) zaxira foizi = **tannarx**; narx taklifi tannarxdan past bo'lsa — ogohlantirish («bu buyurtmada siz o'z mehnatingizga X so'm to'lab ishlaysiz»).
- Jasur ssenariysi: avans olinganda material puli **alohida belgilanadi** (avansdan materialga yetadimi — ko'rsatiladi).

### 3.3. Uskunalar
- Uskuna — `Asset(asset_type = EQUIPMENT)`: narx, sana, foydali muddat (oy), qoldiq qiymati. Eskirish oyma-oy avtomatik (pul harakati emas).
- Uskuna sotilsa yoki yaroqsiz bo'lsa — qolgan qiymat bir martalik xarajat.

### 3.4. K2 da qanday qilindi (farqlar)
- Uskuna — `assets` emas, alohida `kk_equipment` jadvali (`assets.type` ro'yxatida `EQUIPMENT` yo'q, SQLite CHECK'ni o'zgartirmaydi). Uskuna xaridi va sotuvi hamyonga ta'sir qiladi, pul oqimiga (tushum − chiqim) kirmaydi.
- Eskirish xarid oyidan boshlanadi (0-oy). Chiqib ketish oyida oddiy eskirish yo'q; balans − sotilgan narx shu oy bir martalik (manfiy bo'lsa — foyda).
- Sotilgan tovar tannarxi K5 gacha 0; barcha chiqimlar operatsion.
- Oilaviy mehnat — ism bilan (xonadon a'zosiga bog'lash keyin), soat ko'pi bilan 2 kasr raqam.
- Buyurtma kalkulyatori saqlanmaydi; eskirish ulushini egasi o'zi kiritadi. Zaxira foizi — mehnat, material, yo'l va eskirish yig'indisidan.
- O'z mehnati bahosi — OQ-K5 taklifi bo'yicha (egasi kiritadi; kiritilmasa ogohlantirish).

## 4. 3-TAMOYIL: «TOVAR HAM PUL — U HAM YOTADI» — FUNKSIONAL TALABLAR (K3, K5)
Tamoyilning mazmuni: javondagi tovar — muzlagan pul. Uni eski narxda hisoblash kapitalni sezdirmay yeydi; foydani esa qoida bo'yicha taqsimlash kerak.

### 4.1. Tovar kartochkasi va harakatlar (K5)
- Tovar: nom, birlik (g, ml, dona, mm), xarid narxi, sotuv narxi, ixtiyoriy minimal qoldiq.
- Harakatlar: **xarid** (+), **sotuv** (−), **hisobdan chiqarish** (buzilgan, muddati o'tgan — izoh majburiy), **inventarizatsiya tuzatishi** (sanalgan − hisobdagi; izoh bilan).
- Kichik do'kon hamma tovarni yozishga majbur emas: «asosiy tovarlar» rejimi (20–30 ta eng ko'p pul bog'laydigan pozitsiya) standart.

### 4.2. Tannarx usuli
- Standart — **o'rtacha tortilgan** (har xariddan keyin qayta hisoblanadi); ixtiyoriy — **FIFO** (muddati bor tovarlar uchun). Tanlov tovar bo'yicha (OQ-K1).
- Driftsiz hisob: tannarx = `round_half_up(qoldiq qiymati × sotilgan miqdor / qoldiq miqdor)`, yangi qoldiq qiymati = eski − tannarx (oxirgi birlik sotilganda qiymat aniq 0).

**Misol (Bahodir aka, shakar):** qoldiq 50 kg × 11 000 = 550 000; xarid 100 kg × 12 500 = 1 250 000 → 150 kg, 1 800 000. 80 kg × 14 000 = 1 120 000 ga sotildi.
| Usul | Tannarx | Yalpi foyda | Qolgan 70 kg qiymati |
|---|---|---|---|
| O'rtacha (12 000/kg) | 960 000 | 160 000 | 840 000 |
| FIFO | 925 000 | 195 000 | 875 000 |

### 4.3. Qayta tiklash narxi (K5)
- Har bir tovar uchun oxirgi (yoki qo'lda kiritilgan joriy) xarid narxi — **qayta tiklash narxi**. Qoldiqning ikki qiymati yonma-yon: hisobdagi va qayta tiklash bo'yicha; farq — «inflyatsiya yegan kapital».
- Sotuv narxi qayta tiklash narxidan past bo'lsa — ogohlantirish: «Shu narxda sotsangiz, bu tovarni qayta ololmaysiz».
- Misol: 70 kg shakar hisobda 840 000, joriy xarid narxi 13 500 → 945 000; farq **105 000**. 13 000 ga sotish — ogohlantirish.

### 4.4. Muzlagan tovar (K5)
- Oxirgi sotuvdan beri N kun (standart 90; OQ-K4) sotilmagan tovar — «muzlagan». Bosh ekranda: muzlagan tovarlar jami qiymati (qayta tiklash narxida).
- Taklif (ayblamasdan): chegirma bilan sotish, almashtirish, sadaqa — har biri yozuv bilan.

### 4.5. Taqsimot qoidasi va «Hisob kuni» (K3)
- Oyda bir marta (egasi tanlagan kun) **«Hisob kuni»** ustasi: oy yakunlari → haqiqiy foyda → egasi maoshi → taqsimot → bayonnoma (o'zgarmas, `MonthClose`).
- Tartib: (1) **soliq zaxirasi** — egasi kiritgan qoida bo'yicha (tushumdan yoki foydadan, foiz yoki summa; OQ-K3); (2) **egasi maoshi** (2.2); (3) qolgan pul **taqsimot qoidasi** bo'yicha: zaxira, aylanma (tovar), kengayish, (ixtiyoriy) sadaqa — bp bilan, `allocate` (largest remainder). Eskirish summasidan kam bo'lmagan qismi zaxiraga tavsiya qilinadi («uskunani almashtirish puli»).
- Qolgan pul manfiy bo'lsa — taqsimot yo'q; «nima bo'ldi?» audit qadami (Uy'dagi «izohsiz summa» analogi).

**Misol (Feruza, oy):** tushum 18 000 000; soliq zaxirasi (foydalanuvchi kiritgan 4% tushumdan — misol, soliq maslahati emas) 720 000; to'langan xarajatlar 8 500 000; qizining yordami uchun to'langan 1 200 000; egasi maoshi 5 000 000 → qolgan **2 580 000**. Qoida 30/50/20 → zaxira 774 000, aylanma 1 290 000, kengayish 516 000.

### 4.6. K3 da qanday qilindi (farqlar)
- «Qolgan pul» — naqd asosida: tushum − soliq zaxirasi − chiqimlar − egasi maoshi (haqiqiy foyda bayonnomada ma'lumot uchun). Uskuna xaridi ayirilmaydi.
- Egasi maoshi — belgilangan maosh; olingan (o'tkazma + «egasi oldi») undan ko'p bo'lsa — olingani. Maosh belgilanmagan bo'lsa — olingani. Ortig'ini keyingi oy maoshidan ushlash — egasi tanlaydi.
- Soliq «foydadan» — tushum − chiqim (manfiy bo'lsa 0).
- Zaxira ulushi eskirishdan kam bo'lsa — faqat ogohlantirish (qoida avtomatik o'zgartirilmaydi).
- «Hisob kuni» egasi tanlagan kunda emas: o'tgan oy tugagach istalgan payt, bosh sahifada eslatma bilan. Oylar tartib bilan yopiladi (keyingisi yopilgan bo'lsa, oldingisi yopilmaydi).
- Bayonnoma `kk_month_closes` da; zanjir — har bayonnoma xeshi oldingisinikini o'z ichiga oladi. Yopilgan kungacha sanaga yozuv qo'shilmaydi va o'chirilmaydi.
- Taqsimot «hamyonlari» (zaxira, aylanma, kengayish qoldig'i) hali yo'q — bayonnomada summalar saqlanadi, K7 darvozasi shulardan foydalanadi.

### 4.7. K5 da qanday qilindi (farqlar)
- Miqdorlar butun sonda, asosiy birlikda: g, ml, mm, dona; ekranda kg, l, m (3 xonagacha kasr) yoki dona. Narxlar — ko'rsatish birligiga (1 kg, 1 l, 1 m, 1 dona).
- Tovar kartochkasida «xarid narxi» alohida maydon emas: tannarx xaridlardan; «joriy xarid narxi» ixtiyoriy (bo'lmasa — oxirgi xarid narxi = qayta tiklash narxi).
- Boshlang'ich qoldiq — «ilovagacha bor edi» belgili xarid (hamyonsiz). Hamyondan to'langan xarid kassa/kartadan chiqadi, lekin pul oqimiga kirmaydi; tannarx sotilganda foydadan ayiriladi.
- Sotuv «Tovarlar»dan yozilsa — bitta tranzaksiyada Kasb-kor tushumi (manba — tovar nomi). Oddiy «Tushum» tovarsiz qoladi (xizmat, tovari yozilmagan savdo).
- Inventarizatsiya: sanalgan miqdor kiritiladi, farqni yadro hisoblaydi; kamomad — o'rtacha (FIFO da eng eski) tannarxda yo'qotish, ortiqcha — kiritilgan qiymatda, bo'lmasa o'rtacha tannarx (qoldiq yo'q bo'lsa qayta tiklash narxi) bo'yicha. Hisobdan chiqarish va sanoq farqi — «tovar yo'qotishlari» qatori (operatsion chiqimdan alohida).
- Muzlagan tovar takliflari (chegirma, almashtirish, sadaqa) — matn; yozuv oddiy sotuv yoki hisobdan chiqarish (sabab bilan) orqali.
- «Hisob kuni»: chiqim = operatsion chiqim + sotilgan tovar tannarxi + tovar yo'qotishlari (manfiy bo'lsa 0); tovar xaridi ayirilmaydi — u aylanma (tovar) ulushidan qoplanadi.
- Har harakatdan keyin qayta hisob: barcha harakatlar sana tartibida qayta o'ynaladi. Orqa sanadagi harakat keyingi chiqimni qoldiqdan oshirsa — rad etiladi; yopilgan oyga yozilmaydi.

## 5. 4-TAMOYIL: «NASIYANI ADOLAT BILAN YURIT» — FUNKSIONAL TALABLAR (K4)
Tamoyilning mazmuni: nasiya — kelishuv. Narx savdo paytida qotiriladi; kechikkan uchun ustama yo'q; yozilmagan nasiya — yo'qolgan nasiya.

### 5.1. Kunlik kassa yopish
```
Kutilgan qoldiq = Ochilish qoldig'i + Naqd tushum − Naqd chiqim − «Egasi oldi» (naqd) − Bankka/kartaga topshirildi
Kassa farqi     = Sanalgan − Kutilgan
```
- 5 daqiqalik ustadan: tushumlar ro'yxati → chiqimlar → «egasi oldi» → topshirilgan → sanalgan summa → farq.
- Farq nol bo'lmasa — izoh tanlanadi (yozilmagan xarajat, qaytim xatosi, nasiyaga berilgan, egasi oldi, noma'lum); yopilgan kun o'zgarmaydi, tuzatish — keyingi kunga yozuv.
- Takrorlanuvchi kamomad (masalan, 4 haftada 3+ marta) — «xato qidirish» taklifi; hech qachon ayblov emas.

**Misol (Bahodir aka):** ochilish 500 000; naqd sotuv 3 200 000; naqd chiqim (non) 400 000; egasi oldi 300 000; kartaga topshirildi 1 500 000 → kutilgan **1 500 000**; sanalgan 1 450 000 → farq **−50 000**.

### 5.2. Nasiya daftari
- Nasiya — **mijoz bilan savdo kelishuvi** (`Agreement(type = CREDIT_SALE)`): tovar/xizmat, naqd narxi (ma'lumot uchun), **nasiya narxi (qotirilgan)**, to'lov jadvali, ixtiyoriy guvoh. Yaratilgandan keyin narx oshirilmaydi; faqat to'lov, muddatni uzaytirish (narx o'zgarmasdan) yoki kechirish (to'liq/qisman) yozuvlari.
- **Kechikish uchun ustama, jarima yoki «foiz» maydoni yo'q** (domen darajasida — `Receivable` kabi). Nasiya narxi va naqd narx farqi — OQ-D5 (bay' muajjal).
- Mijoz: ism, ixtiyoriy telefon; telefon saqlanganda — rozilik belgisi (OQ-Y3). Mijozlar ro'yxati xonadon bazasida shifrlangan, sinxronlash va eksport — `.baraka` qoidalari bo'yicha.
- **Haftalik nasiya ko'rigi** (juma): muddati o'tganlar, eslatma matni (iliq, nusxalanadi — ilova o'zi xabar yubormaydi), «bu hafta kim bilan gaplashaman» belgisi.
- Yoshi bo'yicha guruhlar: 0–30, 31–60, 61–90, 90+ kun (oxirgi kelishilgan to'lov sanasidan). 90+ — «umidsiz bo'lishi mumkin» (zakot va kengayish darvozasida hisobga olinadi).
- Malika misoli: ko'ylak, naqd narx 600 000, nasiya narxi 660 000 — 3 × 220 000, oylik. Ikkinchi to'lov 20 kun kechikdi → status «kechikkan», summa o'zgarmaydi.

### 5.3. Ta'minotchiga qarz
- Tovarni nasiyaga olish — Uy makonidagi qarz inventari mexanizmi bilan (`docs/uy/SPEC.md` 2C.7, U8), lekin Kasb-kor makonida va `SUPPLY` kelishuviga bog'lanadi (6-bo'lim).

### 5.4. K4 da qanday qilindi (farqlar)
- Kassa farqi naqd kassani tuzatadi (pul oqimiga kirmaydi); keyingi kun ochilishi = sanalgan summa. Kunlar tartib bilan yopiladi (oxirgi yopilgandan keyingi kun); kunni o'tkazib yuborish mumkin.
- Yopilgan kunga faqat **naqd** yozuvlar to'xtatiladi; karta yozuvlari ochiq.
- Ochilish qoldig'i manfiy bo'lsa kun yopilmaydi — avval boshlang'ich qoldiq yoki yozuvlar tekshiriladi.
- Nasiya — `Agreement(CREDIT_SALE)` emas, alohida jadvallar (`kk_credit_sales`, `kk_credit_events`); narx va jadval trigger bilan qotirilgan. Hisob naqd asosida: savdo paytida tushum yo'q, har bir to'lov — tushum.
- To'lovlar oylik, teng (qoldiq tiyinlar birinchi to'lovlarga); uzaytirish — yopilmagan to'lovlarni N oyga surish. Kechikish — eng birinchi yopilmagan va muddati o'tgan to'lov sanasidan; «muddati kelmagan» guruh ham ko'rsatiladi.
- Haftalik ko'rik — muddati o'tganlar va «bu hafta gaplashaman» belgilanganlar; hafta boshi — juma.

## 6. 5-TAMOYIL: «KENGAYISHGA REJA BILAN CHIQ» — FUNKSIONAL TALABLAR (K7)
Tamoyilning mazmuni: kengayish — tayyorgarlik bilan; foizli kredit o'rniga halol yo'llar.

### 6.1. Kengayish darvozasi
Darvoza ochiq bo'ladi, agar **hammasi** bajarilsa (chegaralar sozlanadi, standart qiymatlar — OQ-K6):
1. biznes zaxirasi ≥ 3 oylik operatsion xarajat (oxirgi 3 to'liq oy o'rtachasi);
2. oxirgi 3 «Hisob kuni»da haqiqiy foyda > 0;
3. 90+ kunlik nasiya ≤ jami nasiyaning 10%;
4. foizli qarz yo'q yoki «Qarzdan chiqish» rejasi bor (Uy darvozasi bilan bir xil qoida);
5. kengayish rejasi yozilgan: CAPEX, uch stsenariy, payback («Hunardan ishga» kalkulyatori, U12).

Yopiq bo'lsa — sabablar ro'yxati va har biri uchun keyingi qadam.

### 6.2. Foizli kreditga halol muqobillar
- Jamg'arma bilan bosqichma-bosqich; **sheriklik** (mudoraba/musharaka, U11–U13); ta'minotchidan qotirilgan narxda bo'lib to'lash; foizsiz qarz (U8 tilxati bilan).
- Ilova moliyaviy tashkilotlarni tavsiya qilmaydi va reklama qilmaydi; «islomiy mahsulot» deb atalgan takliflar uchun — «Taklifni tekshirish» (U12) savollari.

### 6.3. K7 da qanday qilindi (farqlar)
- Zaxira — «Hisob kuni» taqsimotidagi zaxira konverti qoldig'i (bayonnomalar qo'shadi, egasi qayd etgan foydalanish ayiradi), kassa qoldig'i emas. Konvertlar «virtual»: pul hamyonlarda, konvert — uning qaysi qismi nima uchun ajratilgani.
- Operatsion xarajat — oxirgi 3 to'liq oyning (yozuvi borlarining) Kasb-kor chiqimlari o'rtachasi; tarix yo'q bo'lsa 1-shart bajarilmagan. 2-shart — oxirgi 3 bayonnoma; 3 tadan kam bo'lsa bajarilmagan.
- 4-shart — xonadondagi Uy makonlari va shu makondagi faol foizli qarzlar va «Qarzdan chiqish» rejimi.
- 5-shart — «Hunardan ishga»da kamida bitta yozilgan g'oya (CAPEX va stsenariylar o'sha kalkulyatorda); reja tugmasi shu bo'limga olib boradi.
- Chegaralar (OQ-K6) darvoza ekranida o'zgartiriladi; boshqa sozlamalarga tegmaydi.

## 7. 6-TAMOYIL: «KELISHUVNI YOZING» — FUNKSIONAL TALABLAR (K6)
Tamoyilning mazmuni: sherik, xodim, ta'minotchi, mijoz — hamma kelishuv yoziladi (9 savol, `docs/uy/SPEC.md` 2F).

### 7.1. Kelishuv turlari
| Tur | Kim bilan | Asosiy bandlar |
|---|---|---|
| `PARTNERSHIP` | sherik | U11–U13 (tayyor) |
| `EMPLOYMENT` | xodim | vazifa, ish vaqti, haq (qat'iy yoki foyda ulushi — OQ-D5), to'lov kuni, avans qoidasi, ajralish |
| `SUPPLY` | ta'minotchi | tovar, narx (qotirilgan), yetkazish, to'lov muddati, qaytarish, konsignatsiya (OQ-D5) |
| `CREDIT_SALE` | mijoz | 5.2 |

- Kelishuv dvigateli, versiyalar, imzolar, jurnal, PDF — mavjud (U7, U11). Yangi turlar uchun 9 savolning majburiy bandlari va shablon matnlari yurist ko'rigidan o'tadi (`reviewStatus`; OQ-Y6). Ilova mehnat shartnomasi yoki boshqa rasmiy hujjat o'rnini bosmaydi.

### 7.2. Xodimlar va avans
- Xodim: ism, lavozim, haq turi, to'lov kuni; shaxsiy ma'lumotlar — minimal (OQ-Y3 bilan birga).
- **Avans** — foizsiz; keyingi to'lovlardan kelishilgan jadval bo'yicha ushlanadi; jarima yo'q. Avans yozuvi xodim kelishuvi jurnaliga tushadi.
- Oylik «xodimlar bilan hisob» — to'langan, ushlangan, qoldiq; PDF varaqcha (imzo joyi bilan).

### 7.3. K6 da qanday qilindi (farqlar)
- `EMPLOYMENT` va `SUPPLY` umumiy `agreements` jadvalida emas: uning turlari CHECK bilan qotirilgan (SQLite'da o'zgartirish — jadvalni qayta qurish, FK'lar bilan xavfli), shuning uchun alohida jadvallar (`kk_agreements`, imzolangan versiyalar — `kk_agreement_versions`), K4 dagi nasiya kabi. Kelishuvlar markaziga (D13A) va umumiy jurnalga ko'chirish — keyin.
- 9 savol shablon bandlari sifatida (`shared/content/templates/*.json`, `reviewStatus`); imzolash uchun majburiy: xodimda — lavozim va vazifalar, ta'minotchida — tovar. Hakam ixtiyoriy (bo'lmasa — «tomonlar birga tanlagan ishonchli kishi»), qayta ko'rish — standart bir yildan keyin.
- Imzo — raqamli emas: PDF chop etiladi, ikki tomon qog'ozda imzolaydi, ilovada imzolangan sana yoziladi va shartlar o'zgarmas versiya sifatida qotiriladi (xesh bilan). Hisob faqat imzolangan shartlar bo'yicha; o'zgarish yangi versiya imzolanguncha amal qilmaydi (`effectiveFrom`).
- Haq — faqat oylik qat'iy (foyda ulushi — OQ-D5). Oy davri — makonning oy boshi kuni bo'yicha; birinchi oy haqi to'liq (kunlarga bo'linmaydi). «Hozir to'lanadigani» — o'tgan oylar qoldig'i; shu oy haqi oy tugagach.
- Avans va haq to'lovi — naqd asosida Kasb-kor chiqimi (`category.kk.wages`): avans berilganda chiqim, keyin haqdan ushlangani to'lovni kamaytiradi (jami chiqim = jami haq). Avans qoidasi: qoldiq chegarasi va eng ko'p necha oyda; ushlash avans berilgan oydan (yoki tanlangan oydan) boshlanadi.
- Ta'minot: tovar bog'langan bo'lsa — yetkazish hamyonsiz xarid sifatida tovar qoldig'iga kiradi (narx — qotirilgan narx × miqdor), to'lov — tovar xaridi kabi (pul oqimiga kirmaydi); tovarsiz bo'lsa — to'lov chiqim (`category.kk.materials`). Oldindan to'lov, qaytarish va konsignatsiya — hali yo'q.
- Yozuvlar o'zgarmas: noto'g'ri avans yoki to'lov o'chirilmaydi (keyingi to'lov bilan tuzatiladi); bog'langan chiqim «Chiqimlar»dan alohida o'chirilmaydi.

## 8. 7-TAMOYIL: «TAROZINGNI TO'G'RI TUT» — FUNKSIONAL TALABLAR (K7)
Tamoyilning mazmuni: halol o'lchov, halol hisob, soliq va zakot — barakaning sharti.

### 8.1. Halol o'lchov
- Oylik «tarozi tekshiruvi» eslatmasi: etalon og'irlik bilan tekshirildi — natija va sana jurnalga yoziladi (ilova tarozini o'lchamaydi; faqat odatni eslatadi va qayd etadi).

### 8.2. Soliq zaxirasi
- 4.5 dagi qoida; zaxira alohida ko'rsatiladi va «Hisob kuni»da to'ldiriladi. To'langan soliq — operatsion xarajat (`category.kk.tax`) zaxiradan.
- Ilova soliq rejimini aniqlamaydi, stavka tavsiya qilmaydi: «Soliq maslahati emas. Rejim va stavkani soliq maslahatchisi bilan aniqlang».

### 8.3. Savdo mollari zakoti
- Yillik «Zakot kuni» ustasi (egasi tanlagan qamariy sana; eslatma 30 kun oldin):
```
Baza  = Tovar qoldig'i (baholash — OQ-D5) + Naqd va hisobdagi pul + Umidli nasiya − Yaqin muddatli qarzlar
Zakot = percent_of(Baza, 250 bp)   — agar Baza ≥ nisob va hawl to'lgan bo'lsa
```
- Nisob — foydalanuvchi kiritgan oltin narxi × 85 g (yoki kumush — ulamo qaroriga ko'ra). Umidsiz nasiya (90+ va egasi «umidsiz» deb belgilagan) bazaga kirmaydi.
- **Misol (Bahodir aka; barcha raqamlar va qoidalar ulamo tasdig'igacha shartli):** tovar 90 000 000, naqd 12 000 000, umidli nasiya 8 000 000, ta'minotchiga qarz 10 000 000 → baza **100 000 000**; oltin 1 100 000/g × 85 = nisob 93 500 000 → zakot **2 500 000 so'm**.
- Natija — hisob, fatvo emas; diniy matnlar `religiousReviewStatus = APPROVED` bo'lmaguncha release'da ko'rsatilmaydi. Hisob snapshot sifatida saqlanadi (`asset_snapshots`).

### 8.4. Yillik inventarizatsiya
- Ustasi: tovarlar ro'yxati → sanalgan miqdor → farqlar (izoh bilan) → yangilangan qoldiq → zakot kuniga tayyor baza.

### 8.5. K7 da qanday qilindi (farqlar)
- **Tarozi:** eslatma ixtiyoriy (egasi «tarozida sotaman» deb yoqadi); oxirgi tekshiruvdan 30 kun o'tsa bosh sahifada eslatma. Natija: to'g'ri / sozlandi / nosoz; oxirgi ikkisida izoh majburiy. Yozuvlar o'zgarmas.
- **Soliq zaxirasi:** «Hisob kuni»dagi soliq summasi konvertga qo'shiladi; `category.kk.tax` chiqimlari zaxiradan ayiriladi (zaxira yetgancha; ortig'i — zaxirasiz to'langan soliq, xato emas).
- **Zakot:** «Zakot kuni» — egasi tanlagan hijriy oy va kun; hijriy sana jadvalli kalendar bo'yicha (kuzatilgan oydan ±1–2 kun farq qilishi mumkin — ekranda aytiladi); eslatma 30 kun oldin. Baza = tovar (standart — qayta tiklash narxida, OQ-D5) + naqd kassa va karta (manfiylari 0) + umidli nasiya − ta'minotchilarga qarz − xodimlarga hozir to'lanadigan haq (OQ-D7). Oltin narxi kiritilmasa zakot hisoblanmaydi (`GOLD_PRICE_MISSING`). Hawl ilova tomonidan taklif qilinadi (oxirgi saqlangan hisobdan yoki birinchi yozuvdan bir qamariy yil), egasi tasdiqlaydi. Saqlangan hisob — `kk_zakat_calcs` dagi o'zgarmas snapshot (umumiy `asset_snapshots` emas: Kasb-kor makoniga bog'liq kiritmalar bilan). Diniy izoh — `shared/content/religious/kk_zakat.json`, `APPROVED` bo'lmaguncha ko'rsatilmaydi.
- **Inventarizatsiya:** bitta forma — har tovar uchun sanalgan miqdor (bo'sh — sanalmadi) va umumiy sabab; farqi borlari bitta tranzaksiyada K5 dagi `COUNT` harakati bo'ladi, yozuvda tovarlar soni, farqlilar soni va qiymat oldin/keyin saqlanadi.

## 8A. 8-TAMOYIL: «O'ZINGIZGA SARMOYA QILING» — FUNKSIONAL TALABLAR (K9)
> Mahsulot egasi qarori, 2026-10-27. Umumiy mazmun — `docs/uy/SPEC.md` 2G.

### 8A.1. Egasining soat qiymati
- Egasi topgani = o'z mehnati bahosi + haqiqiy foyda (3.1), ya'ni ko'rinadigan foyda − oilaviy mehnat bahosi − eskirish; manfiy bo'lsa 0. Haqiqiy foydada egasiga **haqiqatda to'langan** maosh (2.2) emas, o'z mehnati bahosi ayiriladi — shuning uchun maosh qo'shilmaydi. Oxirgi 3 yopilgan oy («Hisob kuni») o'rtachasi taklif qilinadi, egasi o'zgartira oladi.
- *Misol (3.1 dagi Feruza):* 5 000 000 + 3 100 000 = **8 100 000** so'm (egasi oyiga 2 mln maosh olgan bo'lsa ham).
- Egasining oylik ish vaqti (kuniga soat × kun) kiritiladi. Natija — egasining 1 soati qiymati va «ikki barobar maqsad» (Uy 2G.1 bilan bir xil formula va yaxlitlash).

### 8A.2. «O'zim qilaymi yoki o'rgatib topshiraymi?»
- Kiritiladi: ish turi, unga oyiga ketadigan egasining soatlari, yordamchi yoki xodimning 1 soati narxi, bir martalik o'rgatish xarajati (pul) va o'rgatishga ketadigan egasining soatlari.
- Hisob: oylik naf = soatlar × (egasining soat qiymati − yordamchi soat narxi); o'rgatishning to'liq narxi = pul + o'rgatish soatlari × egasining soat qiymati; qoplanish muddati = to'liq narx ÷ oylik naf (oy, yuqoriga yaxlitlanadi). Naf 0 yoki manfiy bo'lsa — «hozircha o'zingiz qilganingiz arzon». Vektor: `kk_delegate`.
- Qaror xodim kartochkasiga (K6) bog'lanishi mumkin; ilova ish haqi miqdorini tavsiya qilmaydi.

### 8A.3. Biznes uchun o'qish va o'rgatish
- Biznes chiqimiga «Sarmoya (o'qish)» belgisi: chiqim haqiqiy foydani baribir kamaytiradi, lekin «Hisob kuni»da alohida qator bo'lib ko'rinadi.
- Xodimga hunar o'rgatish — «Ilm zakoti» yozuvi (Uy 2G.6) bilan bir xil, «kimga» maydoni xodim kartochkasidan tanlanadi.
- Kurs tekshiruvi — Uy 2G.4: umumiy `offer_check` dvigatelidagi `COURSE` turi.

## 9. DOMEN MODELI VA VEKTOR SUITE'LARI
### 9.1. Yangi tushunchalar (taxminiy; aniq sxema — K1+ sessiyalarida, `BARAKA_OILASI.md` 8)
| Tushuncha | Mazmun | Mavjud asos |
|---|---|---|
| `KkSettings` | egasi maoshi, o'z mehnati bahosi, soliq zaxirasi qoidasi, taqsimot qoidasi (bp), muzlash chegarasi | `allocation_rules` |
| `Sale` / `Expense` | tushum va chiqim, kanal, ixtiyoriy tovar qatorlari | `incomes`, `expenses` (`space_id = KASBKOR`) |
| `OwnerDraw`, `OwnerContribution`, `OwnerSalary` | egasi oldi, kiritdi, maosh o'tkazmasi | makonlararo o'tkazma (4.6) |
| `Item`, `StockMove` | tovar va harakatlar (xarid, sotuv, hisobdan chiqarish, tuzatish) | — (yangi) |
| `Equipment` | narx, muddat, qoldiq qiymati, eskirish | `assets` |
| `FamilyLabor` | a'zo, soat, soat bahosi, oy | `members` |
| `CashDay` | ochilish, sanalgan, kutilgan, farq, izoh; yopilgach o'zgarmas | jurnal triggerlari (U12) |
| `Customer`, `CreditSale` | mijoz (rozilik bilan), nasiya kelishuvi va jadvali | `agreements`, `receivables` |
| `Employee`, `Advance` | xodim va avans jadvali | `agreements` |
| `MonthClose` | «Hisob kuni» bayonnomasi: foyda, maosh, taqsimot, zanjir boshi | `venture_periods` naqshi |
| `StockCount`, `ZakatCalc` | inventarizatsiya va zakot snapshot | `asset_snapshots` |

### 9.2. Vektor suite'lari (avval oracle, keyin Rust)
| Suite | Case'lar (kamida) |
|---|---|
| `kk_true_profit` | 3.1 misoli; oilaviy mehnat to'langan (ikki marta hisoblanmaydi); manfiy haqiqiy foyda; tovar xaridi xarajat emas |
| `kk_depreciation` | 12 mln / 60; 7 mln / 36 (qoldiq tiyinlar); qoldiq qiymati bilan; muddatdan oldin sotish |
| `kk_order_quote` | 3.2 Jasur misoli; narx tannarxdan yuqori; soatsiz; zaxira yaxlitlash; avans materialga yetmaydi / yopadi |
| `kk_cogs` | o'rtacha (4.2 misoli), FIFO, oxirgi birlik (qiymat aniq 0), qoldiqdan ko'p sotish — xato, hisobdan chiqarish |
| `kk_replacement` | 4.3 misoli; narx tushgan holat; sotuv narxi < qayta tiklash — ogohlantirish |
| `kk_cash_close` | 5.1 misoli; «egasi oldi»siz farq; ortiqcha (+) farq; karta tushumi kassaga ta'sir qilmaydi |
| `kk_month_close` | 4.5 misoli; qolgan pul manfiy; soliq foydadan; largest remainder qoldiq tiyinlari |
| `kk_credit_sale` | jadval yig'indisi = nasiya narxi; kechikish (summa o'zgarmaydi); qisman kechirish; yosh guruhlari |
| `kk_expansion_gate` | 6.1 ning har bir sharti alohida va birga |
| `kk_payroll` | avans teng ulushlarda (qoldiq tiyinlar); haqsiz oy — ushlanmagani keyingi oyga, ustamasiz; ikki avans; qisman va ortiq to'lov |
| `kk_supplier_balance` | to'lov eng erta muddatdan; kechikish jarimasiz; qoldiqdan ko'p to'lov — xato; 7 kun ichida to'lanadigani |
| `kk_zakat` | 8.3 misoli; nisobdan past; umidsiz nasiya chiqarilgan; qarzlar bazadan katta (baza ≤ 0) |

## 10. UI/UX
- **Desktop — asosiy ish stoli** (`BARAKA_OILASI.md` 11.2): kunlik kassa jadvali, nasiya jadvali (filtr, yosh guruhlari), tovar qoldig'i, «Hisob kuni» ustasi, inventarizatsiya. Klaviatura bilan to'liq ishlash.
- **Android — tez kiritish:** tushum, «egasi oldi», kassa yopish, nasiya to'lovi; vidjet — «yoza oladi, o'qiy olmaydi» (`BARAKA_OILASI.md` 7.5).
- Makon tanlovchi navigatsiyada (Uy / Kasb-kor); har makonning o'z bosh ekrani.
- Ohang — moliyaviy maslahatchi: «Hisob qilgan — yutqazmaydi». Kamomad, kechikkan nasiya, muzlagan tovar — ayblovsiz, keyingi qadam bilan.

## 11. MAHSULOT CHEKLOVLARI (qat'iy)
- `docs/uy/SPEC.md` 3 va `BARAKA_OILASI.md` 2.3 dagi barcha cheklovlar.
- Nasiya va xodim avansida foiz, ustama, jarima maydoni **yo'q** (domen darajasida rad etiladi).
- «Ikkinchi daftar» yo'q: tushumni yashirish, ikki xil hisobot, «soliq uchun» alohida raqamlar funksiyasi qilinmaydi va taklif qilinmaydi.
- Soliq — halollik qismi; ilova soliqdan qochishga undaydigan matn ko'rsatmaydi (taqiqlangan iboralar linteriga qo'shiladi).
- Mijoz va xodim ma'lumotlari — minimal, rozilik bilan, faqat qurilmada (shifrlangan); eksportda ham shifrlangan `.baraka`.

## 12. KO'P QURILMA VA ROLLAR (K8 — avval ADR)
- Rollar: **EGASI** (hammasi), **SOTUVCHI** (tushum, kassa yopish, nasiya to'lovi; foyda, maosh, «egasi oldi», taqsimot va xodimlar haqini ko'rmaydi), ixtiyoriy **HISOBCHI** (o'qish).
- Sotuvchi qurilmasiga faqat kerakli ma'lumot ketadi (tovar katalogi, o'z yozuvlari) — `.baraka` eksportida rol bo'yicha filtr; qabul qilishda sotuvchi faqat ruxsat etilgan jadvallarga yozadi.
- Transport: avval U14 dagi fayl almashish (LAN/fayl); relay server — R1 (ADR tasdiqlangandan keyin). Hisob yurituvchi qurilma qoidasi (6.6) saqlanadi.

### 12.1. K8 da qanday qilindi (farqlar, ADR-0003)
- Rol **qurilmaga** beriladi (odamga emas): egasi ulash faylini rol va Kasb-kor makoni bilan yaratadi; yangi qurilma birinchi faylida uni tasdiqlaganda egasi qurilmani rolga bog'laydi. Rolsiz qurilma — egasi (oila qurilmalari U14 dagi kabi to'liq).
- **«Kassa yopish» o'rniga smena:** sotuvchi barcha naqd harakatlarni (chiqim, «egasi oldi») bilmaydi, shuning uchun egasining kunlik yopishini qila olmaydi. Smena: ochilish (oldingi smenada qolgani, birinchisida — kiritiladi) + o'z naqd savdosi + naqd nasiya to'lovlari = kutilgan; sanalgan → farq va sabab (kassa sabablari); egasiga topshirilgan → keyingi smenaga qolgani (`kk_shift_close`). Egasi smenalarni «Kassa» bo'limida ko'radi; o'z kunlik yopishini avvalgidek qiladi (sotuvchi faylini import qilgandan keyin).
- Sotuvchiga tovar xaridlari yuborilmaydi (tannarx), shuning uchun sotuv qoldiqqa sotuvchi qurilmasida emas, **egasining importida** tekshiriladi; qoldiqdan ko'p sotuv, yopilgan oy yoki kassa kuniga tushgan yozuv rad etiladi (tushumi bilan birga) va import ko'rinishida sababi bilan ko'rsatiladi.
- Sotuvchi nasiya bermaydi va mijoz qo'shmaydi (faqat to'lov qabul qiladi), sanasi — faqat bugun (OQ-K7).
- Hisobchi qurilmasi biznesning hamma yozuvini oladi (Uy makonisiz) va faqat o'qiydi — yozish baza darajasida to'xtatiladi.
- Bekor qilingan qurilma bilan fayl almashilmaydi; undagi mavjud ma'lumot masofadan o'chirilmaydi.

## 13. ISH REJASI (K1–K9)
| # | Mavzu | Bo'limlar | Qabul mezonlari (asosiylari) |
|---|---|---|---|
| K1 | Ikki cho'ntak, tushum/chiqim, egasi oldi, maosh, makonlararo o'tkazma | 2 | o'tkazma atomik (test); «egasi oldi» foydani kamaytirmaydi; bosh ekran 2-raqami |
| K2 | Haqiqiy foyda, buyurtma kalkulyatori, uskunalar | 3 | `kk_true_profit`, `kk_depreciation` yashil; bosh ekran 1-raqami |
| K3 | Taqsimot qoidasi va «Hisob kuni» | 4.5 | `kk_month_close`; bayonnoma o'zgarmas, PDF |
| K4 | Kunlik kassa yopish, nasiya daftari, haftalik ko'rik | 5 | `kk_cash_close`, `kk_credit_sale`; nasiyada ustama maydoni yo'q (test) |
| K5 | Tovar qoldig'i, tannarx, qayta tiklash narxi, muzlagan tovar | 4.1–4.4 | `kk_cogs`, `kk_replacement`; miqdorlar butun sonda |
| K6 | Xodimlar va avans, `EMPLOYMENT`, `SUPPLY` | 7 | shablonlar `reviewStatus` bilan; avansda jarima yo'q |
| K7 | Kengayish darvozasi, soliq zaxirasi, zakot, inventarizatsiya, tarozi | 6, 8 | `kk_expansion_gate`, `kk_zakat`; diniy matnlar `APPROVED` siz ko'rinmaydi |
| K8 | Ko'p qurilma va rollar | 12 | avval ADR; sotuvchi qurilmasida foyda ma'lumoti yo'q (test) |
| K9 | 8-tamoyil: egasining soat qiymati, «o'zim qilaymi yoki o'rgatib topshiraymi?», biznes o'qish xarajati | 8A | `hour_value`, `kk_delegate` yashil; Uy U16 bilan umumiy formula va `offer_check` (`COURSE`) |

Har bir K-vazifa uch qismda (a — yadro va vektorlar, b — saqlash va use-case'lar, c — desktop UI, FRB, E2E, hujjatlar), Uy vazifalari kabi.

## 14. OCHIQ SAVOLLAR
`docs/OPEN_QUESTIONS.md`: mahsulot egasi — OQ-K1…OQ-K7; ulamo — OQ-D5 (nasiya narxi, zakot baholash, xodim foyda ulushi, konsignatsiya), OQ-D7 (nisob, umidli nasiya, oilaviy mehnat, oldindan to'lov chegirmasi); yurist — OQ-Y3 (mijoz ma'lumotlari), OQ-Y6 (xodim va ta'minotchi kelishuvlari), OQ-Y7 (fiskal talablar va «boshqaruv hisobi» chegarasi).
