# «MUSOFIR» MAKONI — SPETSIFIKATSIYA
### Chet elda ishlaydigan migrant va uning uydagi oilasi uchun ribosiz hisob va odatlar daftari

> Versiya: **v0.1 — QORALAMA (M0)**; M1 (2–4-bo'limlar) amalga oshirildi — farqlari 4.4 da. Holat: mahsulot egasi tasdig'i kutilmoqda; ulamo va yurist savollari `docs/OPEN_QUESTIONS.md` da (OQ-MF*).
> Manba: `docs/BARAKA_OILASI.md` 2.2 («Musofir — qisqa karta») va `docs/uy/SPEC.md` 10-bo'limidagi 7-qonun ishorasi. Format — `docs/uy/SPEC.md` va `docs/kasbkor/SPEC.md` kabi.
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
- Musofir qissalari 7 qonunni ochadi (Uy makonidagi bob tuzilmasi, U3 dvigateli). Matnlar litsenziya hal bo'lguncha — placeholder (`BARAKA_OILASI.md` 18).
- Har bir ta'limiy ekranda: «Ta'limiy material. Fatvo, moliyaviy, soliq yoki yuridik maslahat emas».

### 1.2. Personajlar
| Personaj | Segment | Moliyaviy xulq | Ilova nimani yechishi kerak |
|---|---|---|---|
| **Rustam aka** — Koreya, zavod (E-9), 4-yil | Barqaror maosh vonda, oila Samarqandda | Maoshning deyarli hammasini xotiniga yuboradi; 4 yilda o'zida jamg'arma yo'q | O'z ulushi, qaytish jamg'armasi va qaytish sanasigacha prognoz (M1); yuborishning maqsadi (M2); qaytishdagi «kalxatlar» (M3) |
| **Dilnoza** — Rossiya, oshxona | Maosh rublda, naqd; ijara qimmat | Xarajatini yozmaydi, oy oxirida qarz oladi | Chet eldagi xarajatlar, qo'ldagi pul manfiy bo'lsa — ogohlantirish (M1) |
| **Jahongir** — Turkiya, to'qimachilik, 1-yil | Yo'l uchun 15 mln qarz olgan | Avval qarzni yopishni bilmaydi, lira tushadi | Yo'l qarzidan chiqish rejasi (M3), valyutada saqlash (M1 — jamg'arma ish valyutasida) |
| **Farrux** — Qozog'iston, mavsumiy qurilish | 6 oy ishlaydi, 6 oy uyda | Kuzda katta pul bilan qaytadi, qishda tugaydi | Qaytish sanasi va jamg'arma maqsadi «uyda necha oy» bilan (M1), sovutish davri (M3) |
| **Gulnora** — Rustam akaning xotini (uyda) | Uy makonini yuritadi | «Qancha kelishini» bilmaydi, rejalashtira olmaydi | «Ikki qirg'oq»: kelgan pulning maqsadi va uydagi xarajat (M2) |

Mentor — Sobir hoji (Uy va Kasb-kor bilan bir xil ovoz): «Musofirning puli ikki marta ishlanadi — biri ishda, biri hisobda».

## 2. 1-QONUN: «O'Z ULUSHI» — QAYTISH JAMG'ARMASI (M1)
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
- **Qorovul pul** (chet eldagi kutilmagan xarajat uchun, masalan, 1 oylik xarajat) — M3 (OQ-MF3).

## 3. 2-QONUN: «CHET ELDAGI XARAJATNI BIL» (M1)
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
- Qilinmagan: yozuvni tuzatish va o'chirish, qorovul pul (OQ-MF3), uydagi oila bilan bog'lanish (M2), Android UI.

## 5. 6-QONUN: «IKKI QIRG'OQ» — OILA BILAN PUL KELISHUVI (M2)
- Har bir yuborishning **maqsadi** (uy xarajati, qarz to'lovi, qurilish, jamg'arma, marosim, boshqa) va oila bilan **`REMITTANCE` kelishuvi** (9 savol: kim oladi, qaysi maqsadga qancha, hisobot qanday, o'zgartirish tartibi).
- Uydagi a'zo (Uy makoni) kelgan pulni maqsad bo'yicha qabul qiladi va xarajatni shu maqsadga bog'lab yozadi; musofir maqsad bo'yicha qoldiqni ko'radi. Transport — `.baraka` fayl (U14); relay — R1 (alohida ADR).
- Ayblovsiz: maqsaddan chetga chiqish — «kelishuvni yangilaymizmi?» savoli, gina emas.

## 6. 4, 5, 7-QONUNLAR (M3)
- **Yo'l qarzidan chiqish:** U8/U9 qarz inventari va payoff ish valyutasida; birinchi maoshlardan qarz rejasi.
- **Qaytgandan keyingi ish rejasi:** «Hunardan ishga» (U12) qaytish jamg'armasi bilan; ish boshlash summasi maqsadning bir qismi.
- **Sovutish davri:** qaytgandan keyin 90 kun — katta qarorlar (qarz berish, sheriklik, katta xarid) uchun «to'xta va o'yla» va kengaytirilgan «Taklifni tekshirish» (`docs/uy/SPEC.md` 2E.5).
- **Qorovul pul** chet elda (OQ-MF3).

## 7. MAHSULOT CHEKLOVLARI (qat'iy)
- `docs/uy/SPEC.md` 3 va `BARAKA_OILASI.md` 2.3 dagi barcha cheklovlar.
- Kurs prognozi, «qachon ayirboshlash foydali», o'tkazma xizmatlarini reklama qilish yoki reytingi yo'q.
- Jamg'arma foizli depozit sifatida taklif qilinmaydi; «foiz bilan o'stiring» iboralari linterda.
- Uydagi oila haqida ayblovchi matn yo'q («hammasini sarflab yuborishdi» emas — «kelishuv bo'yicha qancha qoldi»).

## 8. MAXFIYLIK
- Musofir makoni shu xonadon bazasida; uydagi qurilmaga (M2) faqat kelishilgan ma'lumot ketadi — musofirning chet eldagi xarajatlari va jamg'armasi oilaga avtomatik ko'rsatilmaydi (OQ-MF2). Texnik vosita — K8 dagi rol filtri naqshi (ADR-0003).

## 9. VEKTOR SUITE'LARI
### 9.1. M1
| Suite | Case'lar (kamida) |
|---|---|
| `mf_month` | Rustam aka (KRW, 0 kasr): maosh, xarajat, uyga + komissiya, jamg'arma — ulush bajarildi; ulush yetmadi; jamg'arma yo'q; jamg'armadan olindi; qo'ldagi pul manfiy; daromadsiz oy (ulushlar `null`); USD (2 kasr) bp yaxlitlash; xatolar — summa ≤ 0, manfiy komissiya, noma'lum tur, bp > 10000 |
| `mf_return_fund` | maqsadga yetgan; shu sur'atda N oy (yuqoriga yaxlitlash); qaytish sanasigacha yetmaydi (`BEHIND`); jamg'arish yo'q (`NO_SAVING`); maqsadsiz; o'rtacha qoldiq yaxlitlash; qaytish sanasi o'tib ketgan (0 oy); xatolar — noto'g'ri kurs |

### 9.2. M2, M3
- `mf_remittance` (maqsadlar bo'yicha qoldiq), `mf_travel_debt`, `mf_cooling` — tegishli sessiyalarda.

## 10. ISH REJASI
| # | Mavzu | Bo'limlar | Qabul mezonlari (asosiylari) |
|---|---|---|---|
| M1 | Ko'p valyuta, chet eldagi maosh va xarajat, o'z ulushi, qaytish jamg'armasi | 2–4 | `mf_month`, `mf_return_fund` yashil; uy valyutasidagi har ko'rsatkich kursi bilan; kurssiz — taxmin yo'q; bosh ekran 1 va 2-raqami |
| M2 | «Ikki qirg'oq»: maqsadlar, `REMITTANCE`, uyda maqsad bo'yicha xarajat | 5, 8 | maqsad bo'yicha qoldiq; kelishuv 9 savol; `.baraka` round-trip |
| M3 | Yo'l qarzi, sovutish davri, kengaytirilgan taklif detektori | 6 | 90 kunlik sovutish; detektor vektorlari |

Har bir M-vazifa uch qismda (a — yadro va vektorlar, b — saqlash va use-case'lar, c — desktop UI, FRB, E2E, hujjatlar).

## 11. OCHIQ SAVOLLAR
`docs/OPEN_QUESTIONS.md`: mahsulot egasi — OQ-MF1…OQ-MF4; ulamo — OQ-D3 (valyuta va qarz); relay — R1 ADR.
