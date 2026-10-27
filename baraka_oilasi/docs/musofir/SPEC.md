# «MUSOFIR» MAKONI — SPETSIFIKATSIYA
### Chet elda ishlaydigan migrant va uning uydagi oilasi uchun ribosiz hisob va odatlar daftari

> Versiya: **v1.0 — mahsulot egasi tasdiqladi (2026-10-19)**; M1 (2–4-bo'limlar), M2 (5, 8-bo'limlar, ADR-0004), M3 va M4 (6-bo'lim), M5 (6.8) va M6 (6A) amalga oshirildi — farqlari 4.4, 5.1, 6.5, 6.7 va 6A.1 da. Mahsulot savollari OQ-MF1…OQ-MF8 yopildi (OQ-MF5 — relay keyinga qoldirildi); ulamo savoli — OQ-D3 (`docs/OPEN_QUESTIONS.md`). Android UI — A4 da qilindi (1.0.0).
> Manba: `docs/BARAKA_OILASI.md` 2.2 («Musofir — qisqa karta») va `docs/uy/SPEC.md` 10-bo'limidagi 7-tamoyil ishorasi. Format — `docs/uy/SPEC.md` va `docs/kasbkor/SPEC.md` kabi.
> Bu hujjat **mahsulot va qoidalarni** belgilaydi. Texnik qarorlar (stek, saqlash, shifrlash, sinxronlash, PDF, i18n) — `docs/BARAKA_OILASI.md` (3–13-bo'limlar).

---

## 0. HUJJAT HAQIDA
- Musofir — bitta «Baraka» ilovasidagi uchinchi makon (`SpaceKind::MUSOFIR`). Uy va Kasb-kor bilan bir xonadon, bir baza, bir PIN, bir jurnal dvigateli.
- Musofir makonining **o'z ish valyutasi** bor (KRW, RUB, KZT, TRY, USD, EUR, GBP). Xonadon valyutasi (odatda UZS) — **uy valyutasi**. Makon ichidagi har bir summa ish valyutasida yoziladi; uy valyutasidagi ko'rinish — faqat foydalanuvchi kiritgan kurs bilan (`BARAKA_OILASI.md` 5.6) va **qaysi kurs bilan hisoblangani ko'rsatiladi**.
- Hamma pul hisoblari faqat yadroda, `Money`, `round_half_up`, `convert` bilan. Har bir yangi pul funksiyasi uchun avval `spec/test-vectors/` ga oracle bilan hisoblangan vektor (9.2).
- Qayta ishlatiladigan mexanizmlar: `incomes` / `expenses` (makon bo'yicha), kelishuv dvigateli va 9 savol (M2 — `REMITTANCE`), qarz inventari va payoff (M3 — yo'l qarzi), «Hunardan ishga» (M3 — qaytgandan keyingi ish), «Taklifni tekshirish» (M3 — kengaytirilgan detektor), `.baraka` almashish (M2).

## 1. MAHSULOT MOHIYATI
**Asosiy tashxis:** «Yillar ishlaydi, qaytganda qo'lida hech narsa yo'q». Sabablari:
- **hammasi uyga ketadi** — o'zi uchun ulush ajratilmaydi; uydagi pul kundalik xarajat, marosim va qarindoshlar orasida tarqaladi;
- **chet eldagi xarajat ko'rinmaydi** — ijara, ovqat, yo'l, telefon, jo'natish komissiyasi «o'z-o'zidan» ketadi;
- **kurs va valyuta tushunilmaydi** — qancha yuborilgani so'mda, qancha ishlangani vonda; qaysi kurs bilan — yozilmaydi;
- **kelishuv og'zaki** — «uy uchun yubordim» deyiladi, uyda boshqa narsaga sarflanadi; keyin gina;
- **qaytishda «kalxatlar»** — katta pul bilan qaytgan odamni «ajoyib loyiha», qarz so'raydiganlar va firibgarlar kutadi.

**Falsafa:** ribo yo'q; omonat — o'z ulushi, ochiq hisob va oila bilan yozma kelishuv. Ilova pulni saqlamaydi, o'tkazmaydi va ayirboshlamaydi.

**Odat ritmi:** har maoshda — o'z ulushini ajratish (2 daqiqa) → har yuborishda — maqsad va kurs (M2) → har oy — oy hisobi va kurs yangilash → qaytishdan 6 oy oldin — qaytish rejasi (M3) → qaytgandan keyin 90 kun — sovutish davri (M3).

**Bosh ekran:** 1-raqam — **«Qaytish jamg'armasi»** (ish valyutasida va uy valyutasida, kursi bilan); 2-raqam — **«Shu oy o'z ulushi»** (ajratildi / maqsad). Keyin: shu oy pul oqimi (maosh → xarajat → uyga → jamg'arma → qo'lda), qaytish sanasigacha prognoz, kurs kartasi.

**Bu makon nima EMAS:** pul o'tkazish xizmati, valyuta ayirboshlash yoki kurs prognozi, ish topib beruvchi agentlik, o'tkazma kompaniyalari reklamasi yoki solishtiruvchisi, viza/huquqiy maslahatchi.

### 1.1. Kontent
- Musofir darslari 8 tamoyilni ochadi (Uy makonidagi bob tuzilmasi, U3 dvigateli). Matnlar — faqat o'zimiz yozganlari; boshqa mualliflarning qissalari, personajlari va brendi ishlatilmaydi (`BARAKA_OILASI.md` 2.1).
- Har bir ta'limiy ekranda: «Ta'limiy material. Fatvo, moliyaviy, soliq yoki yuridik maslahat emas».

### 1.2. Personajlar
| Personaj | Segment | Moliyaviy xulq | Ilova nimani yechishi kerak |
|---|---|---|---|
| **Bobur aka** — Koreya, zavod (E-9), 4-yil | Barqaror maosh vonda, oila Samarqandda | Maoshning deyarli hammasini xotiniga yuboradi; 4 yilda o'zida jamg'arma yo'q | O'z ulushi, qaytish jamg'armasi va qaytish sanasigacha prognoz (M1); yuborishning maqsadi (M2); qaytishdagi «kalxatlar» (M3) |
| **Dilnoza** — Rossiya, oshxona | Maosh rublda, naqd; ijara qimmat | Xarajatini yozmaydi, oy oxirida qarz oladi | Chet eldagi xarajatlar, qo'ldagi pul manfiy bo'lsa — ogohlantirish (M1) |
| **Jahongir** — Turkiya, to'qimachilik, 1-yil | Yo'l uchun 15 mln qarz olgan | Avval qarzni yopishni bilmaydi, lira tushadi | Yo'l qarzidan chiqish rejasi (M3), valyutada saqlash (M1 — jamg'arma ish valyutasida) |
| **Farrux** — Qozog'iston, mavsumiy qurilish | 6 oy ishlaydi, 6 oy uyda | Kuzda katta pul bilan qaytadi, qishda tugaydi | Qaytish sanasi va jamg'arma maqsadi «uyda necha oy» bilan (M1), sovutish davri (M3) |
| **Mohira** — Bobur akaning xotini (uyda) | Uy makonini yuritadi | «Qancha kelishini» bilmaydi, rejalashtira olmaydi | «Ikki qirg'oq»: kelgan pulning maqsadi va uydagi xarajat (M2) |

Maslahat ovozi — moliyaviy maslahatchi (Uy va Kasb-kor bilan bir xil, ismsiz): «Musofirning puli ikki marta ishlanadi — biri ishda, biri hisobda».

## 2. 1-TAMOYIL: «O'Z ULUSHI» — QAYTISH JAMG'ARMASI (M1)
### 2.1. Talablar
- Makon sozlamasida **o'z ulushi** — maoshning foizi (`share_bp`, standart 20 %, 0–100 %). Har bir maosh yozilganda yadro ulushni taklif qiladi: «Shu maoshdan 600 000 KRW — qaytish jamg'armangizga».
- **Qaytish jamg'armasi** — uyga yuborilmaydigan pul (alohida hisob yoki konvert). Ilova unga faqat yozuv bilan qaraydi: «jamg'armaga qo'ydim» (`FUND_IN`), «jamg'armadan oldim» (`FUND_OUT`, **sabab majburiy**), boshlang'ich qoldiq (`FUND_OPENING`).
- Jamg'arma **ish valyutasida** yuritiladi (2.3 — valyutada saqlash). Uy valyutasidagi qiymati — oxirgi kurs bilan.
- Maqsad: **uy valyutasida** summa (masalan, «qaytgach 12 oy yashash + ish boshlash uchun 120 mln so'm») va ixtiyoriy **qaytish sanasi**.
- Oy hisobida: o'z ulushi maqsadi (`percent_of(maosh, share_bp)`), haqiqatda jamg'armaga qo'yilgan (sof: qo'yilgan − olingan) va **yetmagan qism**. Ayblovsiz: «Bu oy 200 000 KRW kam ajratildi. Keyingi maoshdan qo'shamizmi?».

### 2.2. Qaytish prognozi
- Oxirgi 3 to'liq oyning sof jamg'armaga qo'yilgani o'rtachasi (yozuvi bor oylar; 0 ta bo'lsa — prognoz yo'q).
- Maqsadgacha qolgan summa, shu sur'atda **necha oy** (yuqoriga yaxlitlangan butun son).
- Qaytish sanasi bo'lsa: shu sanagacha to'liq oylar soni × o'rtacha + hozirgi qoldiq = **qaytishdagi jamg'arma (prognoz)**; maqsaddan kam bo'lsa — yetmaydigan summa va holat `BEHIND`.
- Holatlar: `REACHED` (maqsadga yetdi), `ON_TRACK`, `BEHIND`, `NO_SAVING` (o'rtacha ≤ 0), `NO_TARGET`.

### 2.3. Valyutada saqlash
- Jamg'arma ish valyutasida turadi; ilova «hammasini so'mga aylantiring» yoki aksincha maslahat bermaydi va kurs prognozi qilmaydi.
- Kurs — foydalanuvchi kiritadi (sana, «1 KRW = 9,1 so'm», ixtiyoriy manba: bank, o'tkazma ilovasi). Oxirgi kurs 30 kundan eski bo'lsa — «kursni yangilang» eslatmasi (M1 da — ko'rsatkich).
- **Zaxira pul** (chet eldagi kutilmagan xarajat uchun, masalan, 1 oylik xarajat) — M3 (OQ-MF3).

## 3. 2-TAMOYIL: «CHET ELDAGI XARAJATNI BIL» (M1)
- Maosh va boshqa daromad — `incomes` (makon = Musofir, valyuta = ish valyutasi, kanal naqd/karta).
- Xarajatlar — `expenses` (`category.mf.*`: ijara, ovqat, yo'l, telefon, komissiya, boshqa).
- **Uyga yuborilgan** (`SENT_HOME`) — summa ish valyutasida, ixtiyoriy komissiya va ixtiyoriy «uyda olingan» summa uy valyutasida (haqiqiy kurs ko'rinadi). Maqsad va kelishuv — M2.
- Oy hisobi (`mf_month`): daromad = maosh + boshqa; xarajat; uyga yuborilgan va komissiya; jamg'armaga sof; **qo'ldagi pul** = boshlang'ich + daromad − xarajat − yuborilgan − komissiya − jamg'armaga sof. Ulushlar (daromaddan bp): xarajat, uyga (komissiya bilan), jamg'arma.
- Ogohlantirishlar: `POCKET_NEGATIVE` (qo'ldagi pul manfiy — «qayerdandir qarz olindimi?»), `NO_SHARE` (daromad bor, jamg'arma yo'q), `SHARE_BELOW_TARGET`, `FUND_WITHDRAWN`.

## 4. KO'P VALYUTA VA KURS (M1)
### 4.1. Qoidalar
- Ish valyutasi makon sozlamasida bir marta tanlanadi; yozuvlar paydo bo'lgach o'zgartirilmaydi (`WORK_CURRENCY_LOCKED`). Ish valyutasi uy valyutasi bilan bir xil bo'lishi mumkin (ichki migratsiya) — unda kurs 1.
- Kurs: `MfRate { on, from = ish valyutasi, to = uy valyutasi, rate_num, rate_den, source }`; kiritish `"9,1"` → `91/10` (ko'pi bilan 6 kasr xonasi, > 0).
- Uy valyutasidagi har bir ko'rsatkich yonida «kurs: 1 KRW = 9,1 soʻm, 18.10.2026». Kurs yo'q bo'lsa — uy valyutasidagi ko'rsatkich ko'rsatilmaydi (taxmin qilinmaydi).

### 4.2. Ekran
- Musofir makoni bosh sahifasi: 1-raqam, 2-raqam, oy oqimi, qaytish prognozi, kurs kartasi, sozlamalar kartasi (birinchi kirishda — sozlash ustasi: mamlakat, ish valyutasi, o'z ulushi, maqsad, qaytish sanasi), yozuv tugmalari (maosh `Ctrl+N`, xarajat, uyga yuborish, jamg'armaga, jamg'armadan, boshlang'ich qoldiq), shu oy yozuvlari.

### 4.3. Domen (M1)
| Tushuncha | Mazmun | Asos |
|---|---|---|
| `MfSettings` | mamlakat, ish valyutasi, `share_bp`, maqsad (uy valyutasida), qaytish sanasi | yangi (`mf_settings`) |
| `MfRate` | sana, kurs (`num/den`), manba | yangi (`mf_rates`) |
| `Salary`, `Expense` | daromad va xarajat | `incomes`, `expenses` (`space_id = MUSOFIR`) |
| `MfMove` | `OPENING`, `SENT_HOME` (komissiya, uyda olingan), `FUND_IN`, `FUND_OUT` (sabab), `FUND_OPENING` | yangi (`mf_moves`) |

### 4.4. M1 da qanday qilindi (farqlar)
- **Maosh va boshqa daromad** — bitta `incomes` jadvali: maosh `source_type = TER` (mehnat daromadi), boshqa daromad — `NULL`. O'z ulushi **butun daromaddan** hisoblanadi (maosh + boshqa); taklif har bir daromad yozilganda chiqadi.
- **Komissiya** uyga yuborish yozuvining ichida (alohida xarajat emas); oy hisobida alohida qator, «uyga» ulushiga qo'shiladi. «Uyda olingan» summa faqat ko'rsatiladi (haqiqiy kurs) — hisobga kirmaydi.
- **Prognoz** — joriy oydan oldingi 3 ta to'liq oydan yozuvi borlari; bitta ham bo'lmasa, prognoz yo'q («bir oy to'lgach»). Jamg'arma qoldig'i — ko'rilayotgan oy oxiridagi.
- **Kurs** — `mf_rates` (o'zgarmas, sinxronlanadi); amaldagisi — bugungacha eng so'nggi sanali; 30 kundan eski bo'lsa belgisi. Ish valyutasi uy valyutasi bilan bir xil bo'lsa — kurs 1, kiritish kerak emas (`RATE_NOT_NEEDED`). Kurs yo'q — uy valyutasidagi ko'rsatkichlar umuman ko'rsatilmaydi, holat `NO_RATE`.
- **Ish valyutasi** — makonda yozuv paydo bo'lgach o'zgarmaydi (`WORK_CURRENCY_LOCKED`); ulush, maqsad, sana va mamlakat o'zgaradi.
- **Jamg'armadan olish** — sabab majburiy (DB CHECK ham), butun qoldiqdan oshmaydi.
- Qilinmagan: yozuvni tuzatish va o'chirish, zaxira pul (OQ-MF3), uydagi oila bilan bog'lanish (M2), Android UI.

## 5. 6-TAMOYIL: «IKKI QIRG'OQ» — OILA BILAN PUL KELISHUVI (M2)
- Har bir yuborishning **maqsadlari** — ulushlar bilan (bp, yig'indisi 100 %): uy xarajati, qarz to'lovi, qurilish va ta'mir, o'qish, marosim, uydagi jamg'arma, boshqa. Standart bo'linish — kelishuv shartlaridan, har yuborishda o'zgartirish mumkin.
- Oila bilan **«Ikki qirg'oq» kelishuvi** (`REMITTANCE`): shartlar (maqsadlar va ulushlar, kim qabul qiladi) va ulardan yasalgan matn — Uy makonidagi **oilaviy kelishuv** (U13): har bir katta a'zo PIN bilan tasdiqlaydi, matn o'zgarsa hamma qayta tasdiqlaydi.
- **Uy tomoni:** kelgan pulni qabul qilish — haqiqatda olingan summa uy valyutasida va kim oldi; qabul **Uy makonida daromad** bo'lib tushadi (bitta tranzaksiyada). Xarajatni maqsadga bog'lab yozish — Uy makonidagi oddiy xarajat + maqsad belgisi.
- **Maqsadlar qoldig'i** (`mf_remittance`): har qabul qilingan summa ulushlar bo'yicha bo'linadi (largest remainder); maqsad bo'yicha olingan − sarflangan = qoldiq. Qabul qilinmagan yuborishlar — «yo'lda». Ikkala tomon ham ko'radi.
- Ayblovsiz: maqsaddan ortiq sarflansa (`OVERSPENT`) — «kelishuvni yangilaymizmi?» savoli, gina emas; xarajat taqiqlanmaydi.
- Transport — `.baraka` fayl (U14); relay — R1 (alohida ADR).

### 5.1. M2 da qanday qilindi (farqlar)
- **Kelishuv** — 9 savolli dvigatel emas, U13 dagi **oilaviy kelishuv** (`REMITTANCE` shabloni): musofir shartlarni (ulushlar, qabul qiluvchi) va matnni Musofir makonida belgilaydi, kelishuv Uy makonida yaratiladi; kattalar «Kelishuvlar» bo'limida PIN bilan tasdiqlaydi (oila qurilmasida ham). Kelishuvlar markazida bu kelishuv tahrirlanmaydi (OQ-MF7).
- **Ulushlar** har yuborishda yoziladi (`mf_remittance_parts`, o'zgarmas); shartlar keyin o'zgarsa, eski yuborishlar o'z ulushlari bilan qoladi. Maqsadsiz eski (M1) yuborish — uy xarajati 100 %.
- **Qabul** — uydagi qurilmada yoki musofirning o'zida (oila ilovasiz bo'lsa); bir yuborish bir marta qabul qilinadi (`ALREADY_RECEIVED`). Musofir yozgan «uyda olingan» summa — faqat taklif; maqsadlarga **haqiqatda olingan** summa bo'linadi.
- **Maqsad bo'yicha xarajat** — Uy makonidagi oddiy xarajat (Uy kategoriyalari bilan) + maqsad belgisi (`mf_spends`); oylik audit va Uy hisobotlarida odatdagidek ko'rinadi.
- **Maxfiylik** (ADR-0004): `HOME` roli; filtr xonadondagi **barcha** Musofir makonlariga qo'llanadi; oila qurilmasida Musofir makoni tugmasi ko'rsatilmaydi, `mf_*` shaxsiy use-case'lari `ROLE_FORBIDDEN`. Oila qurilmasi Uy makonida hamma narsani yozadi va jurnal yozuvlari ham qabul qilinadi.
- Qilinmagan: qabulni yoki maqsad belgisini tuzatish, maqsadlar orasida ko'chirish, qabul bo'yicha eslatma (masalan, 3 kun qabul qilinmasa), relay (R1), Android UI.

## 6. 4, 5, 7-TAMOYILLAR (M3)
### 6.1. Yo'l qarzidan chiqish (4-tamoyil)
- Yo'l qarzi — U8 qarz inventaridagi oddiy **Uy qarzi** (kreditor, summa, reja; odatda qarindoshdan, foizsiz). Musofir uni Musofir makonida «yo'l qarzi» deb belgilaydi.
- Qarz uyda to'lanadi: «Ikki qirg'oq»dagi **«Qarz to'lovi»** maqsadidan oila (yoki musofir) U8 to'lovini yozadi — to'lov maqsad belgisi bilan (`DEBT`), maqsad qoldig'i kamayadi, qarz qoldig'i kamayadi.
- **Reja** (`mf_travel_debt`): qarz qoldig'i − «Qarz to'lovi» maqsadida turgan pul = qolgan; oxirgi to'liq oylarda shu maqsadga kelgan o'rtacha → necha oyda yopiladi; «birinchi maoshlardan» maqsadli muddat (standart 6 oy, OQ-MF8) uchun oyiga qancha kerak. Holatlar: `CLEARED`, `ON_TRACK`, `BEHIND`, `NO_PAYMENTS`.
- Ayblovsiz: «Qarz ulushini oshirsak, N oyda yopiladi» — kelishuv shartlarini o'zgartirishga havola.

### 6.2. Qaytgandan keyingi ish rejasi (5-tamoyil)
- «Hunardan ishga» (U12) — Uy makonida; Musofir bosh sahifasidan havola. Ish boshlash summasi qaytish jamg'armasi maqsadining bir qismi sifatida rejalashtiriladi.

### 6.3. Sovutish davri va «kalxatlar» (7-tamoyil)
- Musofir **«Qaytdim»** deb belgilaydi: sana va olib kelingan summa (uy valyutasida). Keyingi **90 kun** — sovutish davri; bosh sahifada qolgan kunlar.
- Har bir **katta qaror** (qarz berish, sheriklik, sarmoya, katta xarid, boshqa) oldidan tekshiruv (`mf_cooling`):
  - U12 dagi «Taklifni tekshirish» 6 savoli — sheriklik va sarmoyada;
  - musofirga xos savollar: taklif qaytganingizdan keyin tanish yoki qarindosh orqali keldimi; avval pul, keyin hujjat yoki mol so'ralyaptimi; chet elga qayta ish yoki viza uchun pul so'ralyaptimi; qarz berishda qaytarish muddati bormi; oila bilan maslahatlashdingizmi;
  - sovutish qoidasi: davr ichida summa olib kelinganining 10 %idan ko'p bo'lsa — «kuting» (sariq), 30 %idan ko'p bo'lsa — qizil (OQ-MF8).
- Natija: yashil / sariq / qizil, har bir bayroq izohi bilan va «kutish sanasi». Qaror **taqiqlanmaydi** — musofir tanlaydi: «kutaman», «baribir qilaman», «rad etaman»; tanlov o'zgarmas qarorlar jurnaliga yoziladi (musofirning shaxsiy hisobi — oilaga yuborilmaydi, ADR-0004).

### 6.4. Zaxira pul (M4, OQ-MF3 — mahsulot egasi qarori)
- **Zaxira pul** — chet eldagi kutilmagan xarajat (kasallik, ishsiz qolish) uchun **qaytish jamg'armasidan alohida** pul, ish valyutasida. Harakatlar: «Zaxira pulga», «Zaxira puldan» (sabab majburiy, qoldiqdan oshmaydi), «Zaxira pul (boshlang'ich)».
- **Maqsad** = oxirgi to'liq oylardagi (yozuvi borlari, ko'pi bilan 3 ta) **chet eldagi o'rtacha oylik xarajat × N oy**; N — sozlamada, 1–3, standart **1**. Tarix bo'lmasa — maqsad yo'q (`NO_HISTORY`), qo'lda kiritilmaydi.
- **Navbat:** o'z ulushi avval zaxira pulga, to'lgach — qaytish jamg'armasiga. Maoshdan keyingi taklif ikkiga bo'linadi: `zaxiraga = min(ulush, yetmagani)`, `jamg'armaga = ulush − zaxiraga`.
- **Oy hisobi:** qo'ldagi pul zaxira pulga sof qo'yilgancha kamayadi; **o'z ulushi** = jamg'armaga sof + zaxira pulga qo'yilgan (zaxira puldan olish ulushni kamaytirmaydi; ogohlantirishlar shunga qarab). Zaxira puldan olish — ayblovsiz, ogohlantirish yo'q (u shuning uchun bor).
- Holatlar: `FULL`, `PARTIAL`, `EMPTY`, `NO_HISTORY`. Zaxira pul — musofirning shaxsiy hisobi (oilaga yuborilmaydi).

### 6.5. M3 da qanday qilindi (farqlar)
- **Yo'l qarzi** faqat uy valyutasidagi faol Uy qarzi bo'la oladi (`CURRENCY_MISMATCH`); belgi, maqsadli muddat (1–60 oy), qaytish sanasi va olib kelingan summa — `mf_settings` da (musofirning shaxsiy hisobi, oilaga yuborilmaydi). Reja — faqat musofirda.
- **«Qarz to'lovi» maqsadidan to'lov** istalgan faol Uy qarziga qilinadi (yo'l qarzi bilan cheklanmaydi; oila qurilmasi yo'l qarzi belgisini ko'rmaydi). U8 to'lovi va `mf_debt_payments` belgisi bitta tranzaksiyada; belgi o'zgarmas va oila qurilmasidan qabul qilinadi. «Ikki qirg'oq»da xarajatlar ro'yxatida `DEBT_PAYMENT` bo'lib, kreditor bilan ko'rinadi; maqsaddan ortiq to'lov taqiqlanmaydi.
- **Oylik o'rtacha** — oxirgi 3 to'liq oyda (qabuli borlari) uyda qabul qilingan yuborishlarning «Qarz to'lovi» bo'lagi; qabul sanasi bo'yicha. Joriy oy hisobga olinmaydi (`NO_PAYMENTS` matni shunga mos).
- **«Qaytdim»** — kelajakdagi sana bo'lmaydi (`FUTURE_DATE`); belgini olib tashlash mumkin. Sovutish davri bosh sahifada (qolgan kunlar).
- **Katta qaror tekshiruvi** sovutish davridan tashqarida ham ishlaydi (taklif detektori). Savollar yadrodan (`mf_decision_questions`); javoblar to'liq bo'lmasa `MISSING_ANSWER`, ortiqcha yoki noma'lum kalit — `INVALID_ANSWER`. Yozishda tanlov majburiy (`WAIT`, `PROCEED`, `DECLINE`); `mf_decisions` — o'zgarmas, oilaga yuborilmaydi.
- Qilinmagan: zaxira pul (OQ-MF3), «Hunardan ishga» havolasi (6.2), qarorni keyin «bajarildi/bekor» deb belgilash, Android UI.

### 6.6. Ish boshlash summasi va qaror natijasi (M4)
- **Ish boshlash summasi** (5-tamoyil, 6.2) — qaytish jamg'armasi maqsadining bir qismi, uy valyutasida; ixtiyoriy ravishda Uy makonidagi «Hunardan ishga» g'oyasiga bog'lanadi (summani g'oyaning boshlang'ich sarmoyasidan taklif qilish mumkin). Maqsad ikkiga bo'linib ko'rsatiladi: `yashash uchun = maqsad − ish boshlash` (ish boshlash summasi maqsaddan oshmaydi — `STARTUP_EXCEEDS_TARGET`). Bosh sahifadan «Hunardan ishga»ga havola.
- **Qaror natijasi:** jurnaldagi qaror keyin bir marta belgilanadi — «qildim» (`DONE`) yoki «qilmadim» (`DROPPED`), sana va izoh bilan; o'zgarmas, shaxsiy.

### 6.7. M4 da qanday qilindi (farqlar)
- **Zaxira pul harakatlari** alohida jadvalda (`mf_reserve_moves`, ish valyutasida, tuzatiladigan); oy hisobida jamg'arma harakatlari bilan birga (qoldiqlar alohida). Zaxira puldan olish — sabab bilan va qoldiqdan oshmaydi (`RESERVE_INSUFFICIENT`).
- **Maqsad tarixi** — qaytish jamg'armasi prognozi bilan bir xil oylar (oxirgi 3 to'liq oy, yozuvi borlari); o'sha oylarda xarajat bo'lmasa maqsad 0 (`FULL`).
- **Maoshdan keyingi taklif** ikki qadam: avval «Zaxira pulga qo'yish», keyin qolgani «Jamg'armaga qo'yish» (summalar yadrodan).
- **Ish boshlash summasi** — `mf_settings` da (uy valyutasida) va ixtiyoriy U12 g'oyasi; g'oya tanlansa, uning boshlang'ich sarmoyasi (uy valyutasida bo'lsa) taklif qilinadi. Maqsad keyin kamaytirilsa — summa saqlanadi, belgi bilan ko'rsatiladi (`exceeds_target`). «Hunardan ishga» — Uy makonida; Musofir bosh sahifasidagi tugma o'sha ekranni ochadi.
- **Qaror natijasi** — `mf_decision_outcomes` (bir qarorga bir marta; sana qaror sanasidan oldin va kelajakda bo'lmaydi); shaxsiy.
- Hammasi oilaga yuborilmaydi (ADR-0004; ikki qurilmali test).
- Qilinmagan: zaxira pul uy valyutasida ko'rinishi (kurs bilan), Android UI.

### 6.8. Firibgarlik belgilari va qaytish xavfsizligi (M5; OQ-MF10…OQ-MF12 — mahsulot egasi qarori, 2026-10-20)
- **«Besh xavf belgisi»** (firibgarlikning keng ma'lum belgilari): 1 — katta foydani kafolatlash, 2 — shoshirish («faqat bugun, joy kam»), 3 — daromad yangi odam olib kelishdan, 4 — ishning o'zi yo'q (ombor, mol, hujjat, **ruxsat** yo'q; **o'z ko'zi bilan tekshirtirmaydi**), 5 — **kirish oson, chiqish qiyin**. Taklif detektoriga uch savol qo'shildi — `licensed` (yo'q — sariq), `inspection` (yo'q — qizil), `exitEasy` (yo'q — qizil); «bilmayman» — sariq. **Ikki va undan ortiq belgi — `TWO_SIGNS` (qizil)**: bitta belgi — ehtiyot bo'lishga, ikkitasi — taklifdan voz kechishga sabab. Jadval Uy U12 «Taklifni tekshirish» bilan umumiy (vektorlar `offer_check`, `mf_cooling`; paritet testi).
- **Va'da qilingan foyda:** katta qaror tekshiruvida ixtiyoriy «oyiga va'da qilingan foyda, %» — oddiy hisob: yiliga = oyiga × 12, pul (1 + yiliga) barobar («oyiga 35 % — yiliga 420 %, pul 5,2 barobar»). Bu taxmin emas — va'daning o'zi qanchalik g'ayrioddiyligini ko'rsatadi.
- **«Qal'a devori»:** qaytgandan keyin olib kelingandan oilaning **6 oylik ro'zg'ori** ajratiladi = Uy makonining oxirgi to'liq oylardagi (yozuvi borlari, ko'pi bilan 3 ta) o'rtacha xarajati × 6 (`mf_wall`). Katta qaror «erkin pul»dan (olib kelingan − devor) oshsa — `FORTRESS_WALL` (qizil), **sovutish davridan tashqarida ham**. Uy xarajati tarixi bo'lmasa — devor yo'q.
- **Olib kelingan summa valyutada:** «Qaytdim»da summa istalgan valyutada (masalan, 18 000 USD) va kurs bilan; foiz va devor — uy valyutasida (`convert`). Uy valyutasida bo'lsa kurs kerak emas.

## 6A. 8-TAMOYIL: «O'ZINGIZGA SARMOYA QILING» (M6; mahsulot egasi qarori, 2026-10-27)
Umumiy mazmun — `docs/uy/SPEC.md` 2G.
- **Soat qiymati ish valyutasida:** oylik daromad — `mf_month` ta'rifidagidek (maosh + boshqa daromad), oxirgi 3 **to'liq** oy o'rtachasi taklif qilinadi va tahrirlanadi (Uy 2G.1 bilan bir xil qoida va `hour_value` vektori) ÷ oylik ish soatlari. Uy valyutasida ham ko'rsatiladi — faqat kiritilgan kurs bilan (4.1; kurssiz — taxmin yo'q, 30 kunlik eskirish ogohlantirishi).
- **Bilim rejasining ikki maqsadi:** (a) chet eldagi soatni qimmatlashtirish (masalan, ish joyidagi til, malaka toifasi, guvohnoma); (b) qaytgandan keyin uyda daromad beradigan hunar — 6.2 «Qaytgandan keyingi ish rejasi», 6.6 ish boshlash summasi va Uy 2E.4 «Hunardan ishga» rejalovchisi (U12) bilan bog'lanadi.
- **O'qish xarajati** chet eldagi xarajatlarda «Sarmoya» belgisi bilan (Uy 2G.3 kabi); «o'z ulushi» va qaytish jamg'armasiga tegilmaydi.
- **Kurs tekshiruvi:** umumiy `offer_check` dvigatelidagi `COURSE` turi (Uy 2G.4) va «besh xavf belgisi» (6.8) bitta jadvalda; qo'shimcha belgi `JOB_ABROAD_PROMISE` — «kursdan keyin chet elda ish kafolati» (o'zi qizil). Uning `TWO_SIGNS` bilan birikishi `offer_check` vektoridagi `COURSE` case'lari bilan qotiriladi.
- **«Ilm zakoti»:** yangi kelgan hamyurtlarga ish, til yoki hujjat bo'yicha yordam ham o'rgatish yozuvi sifatida qayd etiladi.

### 6A.1. M6 da qanday qilindi (farqlar)
- **Soat qiymati ish valyutasida** — umumiy `hour_value` (Uy 2G.1 bilan bitta funksiya, yaxlitlash va soat chegarasi). Oylik daromad — `mf_month` ta'rifidagidek **maosh + boshqa daromad** (ish valyutasidagi barcha `incomes` yozuvlari), taklif — joriy oydan oldingi oxirgi ko'pi bilan 3 ta to'liq oydan **daromad yozuvi borlari** o'rtachasi (Uy 2G.1 kabi; faqat xarajati bor oy o'rtachani 0 bilan tushirmaydi); bo'sh bo'lsa — qo'lda (`NO_INCOME`). Hisoblar `mf_hour_values` da o'zgarmas tarix (`AUTO` da nechta oy).
- **Uy valyutasida — faqat kurs bilan** (vektor `mf_hour_value`, `domain-musofir::invest`): `convert(ish valyutasidagi 1 soat)` — daromad emas, soat qiymatining o'zi aylantiriladi; «ikki barobar maqsad» = 2 × shu (yaxlitlangan qiymatning ikki hissasi, `convert(2 × soat)` emas — vektorda qotirilgan). Holatlar: `FRESH`, `STALE` (kurs 30 kundan eski — qiymat ko'rsatiladi, «yangilang»; 30 kun — hali yangi; kurs sanasi kelajakda yoki noma'lum — `FUTURE_DATE`), `NO_RATE` (uy valyutasidagi qiymat umuman yo'q, taxmin qilinmaydi), `SAME_CURRENCY` (ichki migratsiya, kurs kerak emas). Uy valyutasidagi ko'rinish saqlanmaydi — har safar amaldagi kurs (bosh sahifadagi kurs kartasi bilan bir xil) va qaysi kurs bilan hisoblangani ko'rsatiladi. Yangi pul funksiyasi aslida yo'q (`hour_value` + `convert`), lekin hisob tartibi va holatlar alohida suite bilan qotirildi.
- **Bilim rejasi** — Uy 2G.2 qoidalari (`validate_plan`, `transition`, faol rejalar chegarasi 2 — yangi ochishda va `PAUSED → ACTIVE` da) + **maqsad** `ABROAD` / `HOME`. Chegara musofir uchun **ikkala maqsad birga** (bitta odam). Ko'rik sanasi bo'sh satr bo'lsa — standart +3 oy, boshlanish sanasi bo'sh — bugun (Uy bilan bitta qoida). Chegara sanog'i va yozuv bitta tranzaksiyada (bir vaqtdagi so'rovlar ham 2 tadan oshirmaydi). Soat qiymatini saqlash va natijani o'lchashda javob yozuvdan oldin tayyorlanadi — xato bo'lsa hech narsa saqlanmaydi. Byudjet — ish valyutasida. `HOME` reja ixtiyoriy ravishda Uy makonidagi «Hunardan ishga» g'oyasiga bog'lanadi (faqat `HOME` — `IDEA_HOME_ONLY`); yangi reja oynasida standart tanlov — ish boshlash summasiga (6.6) bog'langan g'oya. Natijani o'lchash (2G.5) — boshlang'ich va oxirgi soat qiymati ish valyutasida. Jadval `mf_learning_plans`: Uy'dagi `learning_plans` a'zoga bog'langan (`member_id NOT NULL`), Musofir makonida esa daromad yozuvlarida a'zo yo'q — musofirning o'zi makon (Kasb-kor K9 kabi alohida jadvallar).
- **«Sarmoya (o'qish)»** — mavjud `expenses.self_investment` belgisi chet eldagi xarajatda (`MfExpenseInput.selfInvestment`). Xarajat o'z toifasida qoladi va oy hisobida odatdagidek xarajat (qo'ldagi pulni kamaytiradi); «o'z ulushi» maqsadi, qaytish jamg'armasi va zaxira pulga tegilmaydi. Oy hisobida «shundan «Sarmoya (o'qish)»» qatori — jami va oy daromadidagi ulushi (`self_invest_share`), «O'zimga sarmoya» ekranida ham shu qiymat. Belgi faqat Musofir yozuv oynasi orqali (`mf_record_expense`, ish valyutasida); umumiy (Uy) xarajat yo'lida Musofir makonida belgi rad (`NOT_UY_SPACE`). Musofir xarajati rejaga bog'lanmaydi. Qator bosh sahifa va «O'zimga sarmoya» ekranida bitta yordamchidan (belgili xarajatlar — bitta so'rov, oy daromadi).
- **«Ilm zakoti»** — `mf_teaching_logs`: soha (`WORK` ish, `LANGUAGE` til, `DOCUMENTS` hujjatlar, `OTHER`), nimani, kimga (ixtiyoriy, masalan «yangi kelgan hamyurt»), qancha vaqt (≤ 1 kun); sana bo'sh — bugun, kelajakdagi sana yo'q (`FUTURE_DATE`; tekshiruv uchala makonda bitta). Pul hisobi yo'q.
- **Kurs tekshiruvi** — umumiy `check_course`; Musofir makonida (bo'lim tugmasi, reja kartasi va yon menyudagi «Taklifni tekshirish») `COURSE` turi 9-savolni — «Kursdan keyin chet elda ish kafolatlanyaptimi?» (`jobAbroad`) — so'raydi va yuboradi; Uy va Kasb-kor — so'ramaydi (`null`).
- **Maxfiylik (ADR-0004):** soat qiymati chet eldagi maoshdan hisoblanadi, rejalar va «Ilm zakoti» ham musofirning shaxsiy hisobi — uchala jadval `space_id = Musofir`, shuning uchun mavjud `HOME` filtri ularni oila qurilmasiga **umuman yubormaydi**; use-case'lar u yerda `ROLE_FORBIDDEN`, menyuda bo'lim yo'q (ikki qurilmali test). Uy makonidagi g'oya — oilaga umumiy.
- **Qilinmagan:** o'qish vaqti yozuvi (juma ritmi) va reja kartasida byudjetdan sarflangani (xarajatni Musofir rejasiga bog'lash), juma eslatmalari, bob matni va diniy matnlar (2G.8).

## 7. MAHSULOT CHEKLOVLARI (qat'iy)
- `docs/uy/SPEC.md` 3 va `BARAKA_OILASI.md` 2.3 dagi barcha cheklovlar.
- Kurs prognozi, «qachon ayirboshlash foydali», o'tkazma xizmatlarini reklama qilish yoki reytingi yo'q.
- Jamg'arma foizli depozit sifatida taklif qilinmaydi; «foiz bilan o'stiring» iboralari linterda.
- Uydagi oila haqida ayblovchi matn yo'q («hammasini sarflab yuborishdi» emas — «kelishuv bo'yicha qancha qoldi»).

## 8. MAXFIYLIK
- **Mahsulot egasi qarori (OQ-MF2): oila ko'rmaydi.** Uydagi oila qurilmasi — `HOME` roli (ADR-0004): unga musofirning maoshi, chet eldagi xarajatlari, qaytish jamg'armasi, sozlamalari va kurslari **umuman yuborilmaydi**; faqat uyga yuborilganlar (komissiyasiz), maqsadlar, qabul va maqsad bo'yicha xarajatlar. Uy makoni ikkala tomonda to'liq.
- Shart: musofirning qurilmasi xonadon egasi (rolsiz) bo'lishi kerak (ADR-0004, 5). Xonadon uydagi oila qurilmasida yaratilgan bo'lsa — egalik o'tkazilmaydi; **o'sha qurilma maxfiy joyda, oila bilan kelishilgan seyfda saqlanadi** (OQ-MF6, mahsulot egasi qarori). Ilova buni ulash ekranida aytadi.
- Sinxronlash — faqat `.baraka` fayl almashish (U14); relay (R1) keyinga qoldirildi (OQ-MF5).

## 9. VEKTOR SUITE'LARI
### 9.1. M1
| Suite | Case'lar (kamida) |
|---|---|
| `mf_month` | Bobur aka (KRW, 0 kasr): maosh, xarajat, uyga + komissiya, jamg'arma — ulush bajarildi; ulush yetmadi; jamg'arma yo'q; jamg'armadan olindi; qo'ldagi pul manfiy; daromadsiz oy (ulushlar `null`); USD (2 kasr) bp yaxlitlash; xatolar — summa ≤ 0, manfiy komissiya, noma'lum tur, bp > 10000 |
| `mf_return_fund` | maqsadga yetgan; shu sur'atda N oy (yuqoriga yaxlitlash); qaytish sanasigacha yetmaydi (`BEHIND`); jamg'arish yo'q (`NO_SAVING`); maqsadsiz; o'rtacha qoldiq yaxlitlash; qaytish sanasi o'tib ketgan (0 oy); xatolar — noto'g'ri kurs |

### 9.2. M2, M3
- `mf_remittance` (M2): bitta va bir nechta yuborish, largest remainder qoldiq birliklari, qabul qilinmagan («yo'lda»), maqsaddan ortiq sarflangan, ulushsiz maqsadga xarajat; xatolar — ulushlar yig'indisi ≠ 100 %, takroriy maqsad, nol ulush, noma'lum maqsad, summa ≤ 0.
- `mf_travel_debt`, `mf_cooling` — M3.
- `mf_reserve`, `mf_startup` (M4); `mf_month` zaxira pul harakatlari bilan kengayadi.
- `mf_wall` (M5); `offer_check` va `mf_cooling` — «besh xavf belgisi», `TWO_SIGNS`, `FORTRESS_WALL`, va'da hisobi.
- `mf_hour_value` (M6): KRW kurs bilan, kurssiz (`NO_RATE`), eski kurs (31 kun — `STALE`, 30 kun — yangi), bir xil valyuta (kurs e'tiborsiz), RUB qo'lda, uy valyutasidagi yaxlitlash va «ikki barobar» = 2 × yaxlitlangan, KZT soat chegarasi, TRY bitta oy; xatolar — daromad yo'q (kurs bo'lsa ham), noto'g'ri kurs, kelajakdagi kurs, sanasi noma'lum kurs, avval soat qiymati tekshiriladi, 4 oy. `offer_check` `COURSE` + `JOB_ABROAD_PROMISE` — U16a da.

## 10. ISH REJASI
| # | Mavzu | Bo'limlar | Qabul mezonlari (asosiylari) |
|---|---|---|---|
| M1 | Ko'p valyuta, chet eldagi maosh va xarajat, o'z ulushi, qaytish jamg'armasi | 2–4 | `mf_month`, `mf_return_fund` yashil; uy valyutasidagi har ko'rsatkich kursi bilan; kurssiz — taxmin yo'q; bosh ekran 1 va 2-raqami |
| M2 | «Ikki qirg'oq»: maqsadlar, `REMITTANCE`, uyda maqsad bo'yicha xarajat | 5, 8 | maqsad bo'yicha qoldiq; kelishuv 9 savol; `.baraka` round-trip |
| M3 | Yo'l qarzi, sovutish davri, kengaytirilgan taklif detektori | 6 | 90 kunlik sovutish; detektor vektorlari |
| M4 | Zaxira pul (OQ-MF3), ish boshlash summasi va «Hunardan ishga» havolasi, qaror natijasi | 6.4, 6.6 | `mf_month` (zaxira harakatlari), `mf_reserve`, `mf_startup` yashil; ulush avval zaxiraga |
| M5 | Firibgarlik belgilari va qaytish xavfsizligi: «besh xavf belgisi», qal'a devori, valyutada olib kelingan summa | 6.8 | `offer_check`, `mf_cooling`, `mf_wall` yashil; namunaviy «kafolatli foyda» taklifi — qizil |
| M6 | 8-tamoyil: soat qiymati ish valyutasida, ikki maqsadli bilim rejasi, «Sarmoya» belgisi, kurs tekshiruvi | 6A | `hour_value` (valyuta va kurs bilan), `offer_check` (`COURSE` + `JOB_ABROAD_PROMISE` case'lari) yashil; kurssiz uy valyutasidagi qiymat yo'q — ✅ (`mf_hour_value`, 6A.1) |

Har bir M-vazifa uch qismda (a — yadro va vektorlar, b — saqlash va use-case'lar, c — desktop UI, FRB, E2E, hujjatlar).

## 11. OCHIQ SAVOLLAR
`docs/OPEN_QUESTIONS.md`: mahsulot egasi — OQ-MF1…OQ-MF4; ulamo — OQ-D3 (valyuta va qarz); relay — R1 ADR.
