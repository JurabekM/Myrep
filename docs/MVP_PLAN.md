# «BARAKA DASTUR» — TO'LIQ MVP (1–7-QONUNLAR) ISHGA TUSHIRISH PROMPTI
> AI-dasturchi (Claude Code va h.k.) uchun. Spetsifikatsiya: `docs/SPEC.md` (v0.9; v0.8 = `FINTECH_PROMPT.md`).
> Bu fayl `MVP1_KICKOFF.md` ni **o'rnini bosadi**: 1–3-vazifalar o'sha fayldagi bilan bir xil, qolganlari 2–6-qonunlarni qo'shadi.
> **v0.8 o'zgarishi:** 6-qonun uchun ikkita vazifa qo'shildi. **9A** (kelishuv dvigateli va jurnal) qarz va sheriklik vazifalaridan **oldin** bajariladi. **14A** (ko'rik, nizo, oilaviy kelishuvlar) 14-vazifadan keyin bajariladi. 10- va 13-vazifalar endi 9A dvigatelidan foydalanadi.
> **v0.9 o'zgarishi:** 7-qonun uchun **14B** vazifasi qo'shildi (besh xavf belgisi, «o'z ko'zim bilan ko'raman», piramida hisobi, oilaviy zaxira, «to'xta, maslahatlash», hunar shablonlari). 14A dan keyin, 15 dan oldin.
> **Umumiy test vektorlari:** `spec/test-vectors/` (`DESKTOP_PROMPT.md` 5-bo'lim). Mobil CI ham ulardan o'tishi **majburiy**.

---

## 0. MVP DOIRASI — NIMA KIRADI, NIMA KEYINGA QOLADI

**Asosiy cheklov: MVP to'liq offline ishlaydi, backend yo'q.** Shu sababli SPEC'dagi ikkinchi qurilma yoki ikkinchi odamning internet orqali ishtirok etishini talab qiladigan funksiyalar **qurilma ichidagi muqobil** bilan almashtiriladi.

| Qonun | MVP'ga kiradi | Keyinga qoladi (backend yoki hamkor kerak) |
|---|---|---|
| **1. Avval o'zingga to'la** | Tez daromad kiritish, avto-ulush, «Kelajagim», progressiv ulush, streak, oylik audit, «Kimning puli?», majburiyatlar, eslatmalar | Real alohida karta (hamkor bank) |
| **2. Xarajatni ko'r va boshqar** | Zarur/Kerak/Havas, shablonlar, **bosh ekran vidjeti**, havas chegarasi (oila a'zolari rozilik beradi), konvertlar, obunalar (qo'lda kiritiladi), «Qutqarilgan pul», «Juma shirinligi», sadaqa va obro' xarajatlari | Bankdan obunalarni avtomatik aniqlash |
| **3. Avval zaxira, keyin o'sish** | Qorovul / O'sadigan jamg'arma, 6 oylik zaxira maqsadi, «Narx daftari», shaxsiy inflyatsiya indeksi, «Inflyatsiya ta'siri», tayyorgarlik darvozasi, ribo filtri | Rasmiy CPI bilan taqqoslash |
| **4. Ribodan qoch, reja bilan chiq** | Qarz inventari, bergan qarzlar, qarzning haqiqiy narxi, `DEBT_RECOVERY` 70/20/10, payoff planner, yangi qarz oldidan friction so'rovi, **qarz tilxati PDF** (shu qurilmada imzolanadi), sotiladigan buyumlar, marosim rejalovchisi, «Qarzsiz kun» | Tilxatni ikkinchi tomon o'z telefonida tasdiqlashi; to'lovchini (Sardor) ilovaga taklif qilish |
| **5. Pulni halol ishga sol** | Mudoraba/Musharaka domeni va validatsiyasi, shartnoma ustasi + PDF (shu qurilmada imzolanadi), buyout jadvali, venture ledger, foyda/zarar taqsimoti, fors-major, «Hunardan ishga», «Kafolatlangan foyda» detektori | Kapital egasi uchun real vaqtdagi read-only ko'rinish (MVP'da uning o'rniga **PDF hisobot** ulashiladi) |
| **7. Ko'rmagan ishingga pul tikma** | Besh xavf belgisi va baho qoidasi, «o'z ko'zim bilan ko'raman» tekshiruv ro'yxati, va'da qilingan foydani yillikka aylantirish, piramida ta'limiy hisobi, katta summa uchun «Oilaviy zaxira» taqsimoti, «to'xta, maslahatlash» (24 soat + maslahatchi), g'arar/qimor izohi, hunar shablonlari | Litsenziyalar reyestri bilan avtomatik tekshirish (davlat API) |
| **6. Kelishuvni yozinglar** | Umumiy kelishuv dvigateli (9 savol, to'liqlik indikatori; turlar: sheriklik, qarz, ijara, xizmat, oilaviy), vazifalar va «bajarilmadi» oqimi, oylik ochiq hisob ko'rigi va bayonnoma, append-only jurnal va xesh-zanjir, «katta foyda» ogohlantirishi, nizo va hakam papkasi, og'zaki kelishuvni yozib olish | Ikkinchi tomon va hakamning o'z qurilmasida masofadan tasdiqlashi va ko'rib chiqishi |

**Qurilma ichidagi muqobillar:**
- *Ikkinchi tomonning tasdig'i* → ikkinchi tomon shu telefonda ismini yozadi va ekranda imzo chizadi. Imzo PDF'ga qo'shiladi.
- *Oilaviy rozilik* → har bir oila a'zosi o'z profilini tanlab tasdiqlaydi (ixtiyoriy shaxsiy PIN bilan).
- *Sherikka shaffoflik* → davriy ledger hisobotini PDF qilib ulashish.

---

## 1. QANDAY ISHLATILADI (dasturchi uchun yo'riqnoma)
1. Bo'sh repo yarating va `FINTECH_PROMPT.md` ni `docs/SPEC.md` nomi bilan joylang. Bu faylni esa `docs/MVP_PLAN.md` qilib qo'ying.
2. Repo ildiziga `CLAUDE.md` faylini qo'shing va unga quyidagini yozing:
   «Har sessiya boshida `docs/SPEC.md` ning 3, 4, 5, 6, 12-bo'limlarini va `docs/MVP_PLAN.md` ning 0-bo'limini o'qi. SPEC 4-bo'lim (ADR) qat'iy.»
3. **18 ta vazifani tartib bilan, har birini alohida sessiyada bering.** Har bir sessiyaga «Umumiy kirish» va bitta vazifa matnini nusxalang.
4. Har bir vazifadan keyin qabul mezonlarini tekshiring, commit qiling, keyin keyingisiga o'ting.
5. **Bosqichlar** (har bosqich oxirida ishlaydigan ilova chiqadi, uni test qurilmalariga berish mumkin):
   - **A. Poydevor:** 1–3
   - **B. 1-qonun:** 4–6
   - **C. 2-qonun:** 7–8
   - **D. 3-qonun:** 9
   - **D2. 6-qonun poydevori:** 9A (kelishuv dvigateli — 4- va 5-qonunlar undan foydalanadi)
   - **E. 4-qonun:** 10–12
   - **F. 5-qonun:** 13–14
   - **F2. 6-qonun:** 14A
   - **F3. 7-qonun:** 14B
   - **G. Reliz tayyorgarligi:** 15
   Tartib: 1 → 2 → … → 9 → **9A** → 10 → 11 → 12 → 13 → 14 → **14A** → **14B** → 15.
6. **Agar 10- yoki 13-vazifa allaqachon bajarilgan bo'lsa:** 9A sessiyasida `LoanReceipt` va `PartnershipContract` ni `Agreement` ga ko'chiradigan **migratsiya** yoziladi (ma'lumotlar yo'qolmasligi test bilan tekshiriladi).

---

## 2. UMUMIY KIRISH (har bir sessiya boshiga qo'yiladi)
```
Sen «Baraka Dastur» loyihasining senior Flutter + Kotlin dasturchisisan.
Avval docs/SPEC.md va docs/MVP_PLAN.md (0-bo'lim) ni o'qi. SPEC 4-bo'lim (texnik qarorlar) qat'iy.
Bu sessiyada FAQAT quyidagi vazifani bajar. Boshqa vazifalarning funksiyalarini qo'shma.
Yangi jadval kerak bo'lsa — Drift sxema versiyasini oshir va migratsiya testini yoz.
Pul bilan bog'liq har qanday hisob faqat core/money orqali (double taqiqlanadi).
Ishni boshlashdan oldin qisqa reja yoz (fayllar + qadamlar), keyin bajar.
Oxirida: bajarilgan ishlar, qabul mezonlari holati va ochiq savollarni yoz.
Kod, identifikatorlar va commit xabarlari inglizcha. Izohlar, hujjatlar va UI matnlari o'zbekcha.
```

---

# A. POYDEVOR

## VAZIFA 1 — Loyiha skeleti va infratuzilma
- Flutter loyihasi: `applicationId` = `uz.barakadaftari.app` (vaqtinchalik), minSdk 26, Flutter versiyasi `.fvmrc` orqali qotiriladi.
- **Feature-first** tuzilma:
  ```
  lib/
    app/      (router, theme, l10n, bootstrap)
    core/     (money, time, ids, errors, result, pdf, security bridge)
    features/
      lock/ home/ income/ vault/ expenses/ obligations/ audit/ content/
      budget/ subscriptions/ envelopes/ prices/ debts/ ceremonies/
      partnerships/ ventures/ offers/
        presentation/ domain/ data/
  android/app/src/main/kotlin/.../native/
  pigeons/   test/   integration_test/
  ```
- Kutubxonalar: Riverpod (generator bilan), go_router, `freezed`/`json_serializable`.
- Lokalizatsiya: `gen-l10n`, `uz` va `ru`. UI matnlari faqat ARB'da, hardcode taqiqlanadi.
- Lint: `very_good_analysis`, `strict-casts`, `strict-raw-types`.
- Pigeon `SecurityApi` stub sifatida.
- CI (GitHub Actions): `format → analyze → test → build apk --debug`.
- «Daftar» mavzusi: qog'oz rangidagi fon, light va dark rejim.
- **O'zbek yozuvi:** shrift `ʻ` (U+02BB) va `ʼ` (U+02BC) belgilarini to'g'ri ko'rsatadi. Bu PDF'lar uchun ham kerak. Font fayli ilovaga o'rnatiladi.

**Qabul mezonlari:**
- [ ] CI yashil, `analyze` 0 ta ogohlantirish.
- [ ] Barcha marshrutlar placeholder ekranlarni ochadi.
- [ ] `uz` ↔ `ru` almashadi.
- [ ] Pigeon stub Flutter'dan chaqiriladi va javob qaytaradi.

## VAZIFA 2 — Xavfsizlik qatlami (Kotlin + Flutter)
- **Kotlin** (`SecurityApi`):
  - Keystore AES-GCM kalit (StrongBox mavjud bo'lsa, StrongBox'da);
  - `getOrCreateDatabaseKey()` — 256-bit kalitni wrap/unwrap qiladi;
  - `BiometricPrompt` (`BIOMETRIC_STRONG` yoki qurilma krediensiali);
  - `setSecureFlag()`;
  - `getIntegritySignals()` — root, emulyator, debugger, imzo xeshi. MVP'da faqat ogohlantirish, bloklash yo'q.
- **Flutter:**
  - 6 xonali PIN, Argon2id (yoki PBKDF2-SHA256 ≥310k) hosilasi;
  - biometriya ixtiyoriy;
  - fondan qaytganda 2 daqiqadan keyin qayta qulflash;
  - 5 marta xato kiritilsa, o'sib boruvchi kutish;
  - moliyaviy marshrutlarda `FLAG_SECURE` avtomatik yoqiladi.
- `allowBackup="false"` va `dataExtractionRules`. Release'da `debugPrint` o'chiq, maxfiy maydonlar loglanmaydi.

**Qabul mezonlari:**
- [ ] Kalit wrap/unwrap uchun Kotlin testi bor.
- [ ] PIN (to'g'ri, noto'g'ri, lockout) uchun Dart testlari bor.
- [ ] Skrinshot bloklangan (qo'lda tekshiruv).
- [ ] Timeout'dan keyin lock ekrani ochiladi.

## VAZIFA 3 — Domen yadrosi va shifrlangan baza
- **`core/money`:**
  - `Money(int minorUnits, CurrencyCode)` (`UZS`, `USD`, `EUR`, `RUB`);
  - valyuta aralashganda `CurrencyMismatchException`;
  - `MoneyRounding`, `allocate(total, ratios)` (largest remainder), `percentOf(Money, basisPoints)`;
  - `FxRate` va `convert`;
  - UZS formatlash: `8 000 000 so'm`.
- **`core/ids`:** UUIDv7. **`core/time`:** `Clock` abstraksiyasi, `Asia/Tashkent`, `weekAnchor = FRIDAY`, sozlanadigan oylik kuni.
- **`core/pdf`:** `pdf` paketi asosidagi umumiy PDF quruvchi (sarlavha, jadval, imzo bloki, o'zbekcha font). Keyingi vazifalardagi barcha hujjatlar shundan foydalanadi.
- Drift + SQLCipher (kalit Vazifa 2 dan olinadi).
- **Sxema v1** (har bir jadvalda SPEC 4.4 dagi umumiy maydonlar bo'ladi):
  - `households`, `members` (rol: `ADULT | CHILD`, ixtiyoriy shaxsiy PIN hosilasi);
  - `categories` (`defaultNecessity` nullable);
  - `incomes` (`source`, `channel CASH|CARD`, `memberId`, `sourceType` nullable);
  - `expenses` (`categoryId`, `channel`, `memberId`; keyingi bosqich maydonlari nullable yoki default: `necessity`, `envelopeId`, `isGift`, `isOstentation`, `fundedByDebt`);
  - `assets` (SPEC 4.3) va `asset_snapshots`;
  - `vault_transactions`;
  - `allocation_rules`;
  - `obligations`;
  - `fx_rates`.
- Repository interfeyslari (domain) va Drift implementatsiyalari (data).
- Standart kategoriyalar seed qilinadi.

**Qabul mezonlari:**
- [ ] `allocate` uchun property-based test: yig'indi har doim aniq teng, manfiy qism yo'q.
- [ ] Valyuta aralashuvi exception beradi, UZS formatlash testlari bor.
- [ ] Repository'lar uchun in-memory testlar bor (CRUD va soft delete).
- [ ] Shifrlangan DB faylini kalitsiz ochib bo'lmaydi.
- [ ] Migratsiya test infratuzilmasi tayyor.
- [ ] `core/money` qamrovi ≥ 95%.

---

# B. 1-QONUN: «AVVAL O'ZINGGA TO'LA»

## VAZIFA 4 — Daromad va «Kelajagim» (SPEC 2.1, 2.2)
- **Tez daromad kiritish:** saqlash ≤ 3 bosishda. Oxirgi manba va kanal eslab qolinadi.
- **Ulush taklifi:** [Ajratish] [Boshqa summa] [Bu safar emas]. Ajratilganda `vault_transactions` ga DEPOSIT yoziladi.
- **AllocationRule:** 5% / 10% / qat'iy summa.
  - **Progressiv rejim:** 4 hafta ketma-ket ajratilsa, +1% taklif qilinadi.
- **«Kelajagim» ekrani:** balans, tarix va **streak** (ajratilgan haftalar). Odat ko'rsatkichi summadan oldinda turadi.
- **Pul olish uchun friction:** tasdiqlash, sabab (majburiy) va PIN.
- **Boshlang'ich balans («avval yig'ilgan pul»):** `reason = INITIAL`.
- Bu bosqichda bitta umumiy `VAULT` asset bo'ladi. Uni 2 turga bo'lish Vazifa 9 da qilinadi.

**Qabul mezonlari:**
- [ ] Daromad 3 bosishda saqlanishi widget test bilan tekshirilgan.
- [ ] Ulush faqat `core/money` orqali hisoblanadi.
- [ ] Streak Clock mock bilan testlangan (hafta jumadan boshlanadi).
- [ ] PIN va sababsiz pul olib bo'lmaydi.

## VAZIFA 5 — Xarajatlar, majburiyatlar, audit va bosh ekran (SPEC 2.3–2.5)
- **Tez xarajat kiritish.** Xarajat shablonlari Vazifa 7 da qo'shiladi.
- **Majburiyatlar:** to'lov kunidan 1 kun oldin eslatma (Kotlin WorkManager + bildirishnoma, Pigeon orqali). Eslatmalar qurilma qayta yoqilgandan keyin ham saqlanadi.
- **Oylik audit ustasi:** daromad → majburiyatlar → xarajatlar → **izohsiz qolgan summa**.
- **«Kimning puli?»:** daromadning egalar bo'yicha taqsimoti va «O'zingiz» ulushi.
- **Bosh ekran:**
  - 1-raqam — «O'zingizga to'langan (shu oy)»;
  - «Kelajagim» balansi va streak;
  - oy yakuni (+ yoki −);
  - «Shu haftaning vazifalari» kartasi (Vazifa 6 bilan ulanadi).
  Bosh ekran **slot-arxitektura** bilan quriladi: keyingi vazifalar unga o'z kartalarini (havas chegarasi, qarzsiz kun, sheriklik va h.k.) qo'shadi.
- Oilaviy rejim (lokal): bir qurilmada bir nechta a'zo, har bir yozuvda «kim» belgisi.

**Qabul mezonlari:**
- [ ] Izohsiz summa uchun unit test bor, manfiy holat ham qamrab olingan.
- [ ] Oylik kuni sozlamasi to'g'ri ishlaydi.
- [ ] Eslatma qurilmada keladi.
- [ ] Bosh ekran KPI'lari repository ma'lumotlariga mos (integration test).

## VAZIFA 6 — Kontent dvigateli (5 bob uchun)
- Kontent ilovaga o'rnatilgan JSON (`assets/content/`) sifatida keladi:
  - `Chapter`, `Law`, `WeeklyTask[3]`;
  - `religiousReviewStatus` (`PENDING | APPROVED`);
  - `PENDING` diniy bloklar **release build'da ko'rsatilmaydi**.
- **5 ta bob** uchun to'liq struktura bo'ladi, matnlar esa **faqat placeholder** (litsenziya hal bo'lguncha asl matnlar ko'chirilmaydi).
- «Daftar sahifasi»: foydalanuvchi qonunni o'zi yozadi (`daftar_pages`).
- **Haftalik vazifalarni avtomatik belgilash.** Har bir vazifa ilovadagi biror hodisa bilan bog'lanadi (`TaskTrigger`):
  - masalan, `VAULT_FIRST_DEPOSIT`, `AUDIT_COMPLETED`, `SUBSCRIPTIONS_REVIEWED`, `DEBT_INVENTORY_COMPLETED`, `PRICE_COMPARISON_DONE` va hokazo;
  - triggerlar ro'yxati kengaytiriladigan qilib quriladi, keyingi vazifalar unga o'z hodisalarini qo'shadi.
- `ChapterUnlockPolicy` — **odat asosida** (SPEC 2C.6): oldingi bobning vazifalaridan kamida 2 tasi bajarilgan va kamida 7 kun o'tgan bo'lishi kerak. Shart sozlanadi.
- Juma ertalab bildirishnoma.
- Har bir ta'limiy ekranda disklеymer.

**Qabul mezonlari:**
- [ ] JSON validatsiyasi bor, buzuq kontent ilovani yiqitmaydi.
- [ ] `PENDING` blok release'da ko'rinmasligi test bilan tekshirilgan.
- [ ] Unlock policy uchun unit testlar bor.
- [ ] Trigger → vazifa belgilanishi integration test bilan tekshirilgan.

---

# C. 2-QONUN: «XARAJATNI KO'R VA BOSHQAR»

## VAZIFA 7 — Uch toifa, shablonlar, vidjet, havas chegarasi (SPEC 2B.1–2B.4, 2B.8)
- `Necessity` (`ZARUR | KERAK | HAVAS`):
  - har bir kategoriyaning standart toifasi bor va oila uni o'zgartira oladi;
  - o'zgarishlar tarixi saqlanadi;
  - bola ta'limi = `KERAK`.
- Endi xarajat kiritishda toifa kategoriyadan avtomatik olinadi va o'zgartirish mumkin.
- **Xarajat shablonlari** (somsa, ichimlik, benzin...) va «oxirgisini takrorlash».
- **Bosh ekran vidjeti** (Kotlin, Jetpack Glance): shablon tugmalari va bir bosishda yozish. Ma'lumot ilovaga xavfsiz uzatiladi; ilova qulfli bo'lsa, vidjet summalarni **ko'rsatmaydi**.
- **Jamlash effekti:** mayda kategoriyalar uchun hafta, oy va yil bo'yicha jami; «ijarangizning X%i» kabi taqqoslash.
- **Havas chegarasi** (`HavasLimit` + `LimitConsent`):
  - barcha `ADULT` a'zolar tasdiqlamaguncha chegara **faol bo'lmaydi**;
  - 80% va 100% da yumshoq ogohlantirish, bloklash yo'q.
- `isGift` («siz olib kelsangiz hisobga kirmaydi»), `isOstentation` va `fundedByDebt` (qizil bayroq).
- `SADAQA` kategoriyasi havas va «oqib ketish» hisobiga **kirmaydi**.
- **«Juma shirinligi»** (`ScheduledTreat`): davriy ritual va eslatma.
- **Odatlar** (`Habit`, masalan chekish): faqat statistika ko'rsatiladi, ayblovchi matn yo'q.
- Ranglar: havas neytral rangda, qizil emas.

**Qabul mezonlari:**
- [ ] Rozilik testlari: 2 kattadan 1 tasi tasdiqlasa, chegara faol emas.
- [ ] Sadaqa havas hisobiga kirmasligi test bilan tekshirilgan.
- [ ] Ilova qulfli bo'lganda vidjet summa ko'rsatmaydi.
- [ ] Yillik jamlash hisobi testlangan.

## VAZIFA 8 — Obunalar, konvertlar, «Qutqarilgan pul» (SPEC 2B.5–2B.7)
- **Obunalar** (`Subscription`):
  - oylik va **yillik** narx, oxirgi ishlatilgan sana;
  - «Kerakmi?» savoli va **unutilgan obuna** ogohlantirishi (N kun davomida «ishlatdim» belgilanmasa);
  - bekor qilingan obuna `SavingsRescue` ga yoziladi.
- **Konvertlar** (`Envelope` + `EnvelopePeriod`):
  - haftalik limit;
  - naqd rejim: «konvertga X so'm soling» va hafta oxirida qoldiqni kiritish;
  - karta xarajati ham konvertdan ayiriladi.
- **«Qutqarilgan pul»:** joriy davrdagi havas va oqib ketgan summa bazaviy davr bilan taqqoslanadi. Bazaviy davr — birinchi audit oyi yoki tanlangan oy. Bunga qo'shiladi: bekor qilingan obunalar + konvertlarda qolgan qoldiqlar.
- **Bir bosishda «Kelajagim»ga o'tkazish** (1- va 2-qonunlar shu yerda ulanadi).
- Bosh ekranga «Bu hafta qutqarildi» kartasi qo'shiladi.

**Qabul mezonlari:**
- [ ] Qutqarilgan pul formulasi unit testlangan, jumladan manfiy holat (ko'proq sarflangan) ham. Manfiy holatda ilova ayblamaydi va «0» deb ko'rsatadi.
- [ ] Konvert davri hafta chegarasida to'g'ri yopiladi.
- [ ] Bekor qilingan obunaning yillik tejami to'g'ri hisoblanadi.

---

# D. 3-QONUN: «AVVAL ZAXIRA, KEYIN O'SISH»

## VAZIFA 9 — Qorovul / O'sadigan, narx daftari, inflyatsiya, darvoza, ribo filtri (SPEC 2C)
- **Jamg'armani ikkiga bo'lish:**
  - mavjud `VAULT` `QOROVUL` va `OSADIGAN` turiga ajratiladi; migratsiyada eski balans to'liq `QOROVUL` ga o'tadi;
  - avto-ulush avval favqulodda zaxirani to'ldiradi.
- **Zaxira maqsadi:** oxirgi 3 oydagi (`ZARUR` + `KERAK`) o'rtachasi × 6 oy. Milestone'lar: 3 oy va 6 oy. Progress «1,4 / 6 oy» ko'rinishida ko'rsatiladi. Ma'lumot 3 oydan kam bo'lsa, foydalanuvchidan taxminiy summa so'raladi.
- **Favqulodda zaxiradan pul olish:** «favqulodda holatmi?» tasdig'i va qayta to'ldirish rejasi taklifi.
- **«Narx daftari»** (`PriceBasket`, `BasketItem`, `PricePoint`):
  - foydalanuvchi o'z savatini tuzadi;
  - narx tarixi va «N yil oldin → bugun» taqqoslash;
  - **shaxsiy inflyatsiya indeksi** savatdagi og'irliklar bo'yicha hisoblanadi;
  - haftalik eslatma.
  - Hisoblash qoidasi: foizlar `basisPoints` (int) bilan hisoblanadi, ko'rsatish uchungina formatlanadi.
- **«Inflyatsiya ta'siri»:** yotgan jamg'armaning real qiymati shaxsiy indeks asosida, «necha kg go'sht» ko'rinishida. Ekran har doim keyingi qadam bilan tugaydi.
- **Tayyorgarlik darvozasi** (`ReadinessGate`):
  - shartlar: favqulodda zaxira ≥ 6 oy **va** (faol foizli qarz yo'q **yoki** faol qarzdan chiqish rejasi bor);
  - darvoza qo'riydigan funksiyalar: `OSADIGAN` ga kapital kiritish va sheriklikka kapital berish (Vazifa 13);
  - qulflangan ekranda shartlar va progress ko'rsatiladi;
  - ongli chetlab o'tish: ogohlantirish va tasdiq, hodisa lokal logga yoziladi.
  - Qarz bilan bog'liq shart Vazifa 10–11 tayyor bo'lgunicha interfeys orqali «qarz yo'q» deb qaytariladi (stub).
- **Ribo filtri:**
  - `IncomeSourceType` (`TER | MOL | TAVAKKAL | RIBO`) ixtiyoriy belgi sifatida;
  - ilovaning **hech bir joyida** foiz stavkasi «muqobil daromad» sifatida ko'rsatilmaydi. Bu matn darajasida tekshiriladi (ARB lint testi taqiqlangan iboralarni qidiradi).

**Qabul mezonlari:**
- [ ] VAULT → QOROVUL migratsiya testi bor, balans yo'qolmaydi.
- [ ] Zaxira maqsadi va inflyatsiya indeksi hisoblari unit testlangan.
- [ ] Darvoza holatlari test matritsasi bilan tekshirilgan.
- [ ] ARB'da taqiqlangan iboralar yo'qligi test bilan tasdiqlangan.

---

# D2. 6-QONUN POYDEVORI: «KELISHUVNI YOZINGLAR»

## VAZIFA 9A — Umumiy kelishuv dvigateli va append-only jurnal (SPEC 2F.1–2F.3, 2F.6, 2F.9)
- **`Agreement`:**
  - `type`: `PARTNERSHIP | LOAN | RENT | SERVICE | FAMILY | OTHER`;
  - `status`: `DRAFT → SIGNED → ACTIVE → (IN_DISPUTE) → CLOSED`;
  - `effectiveFrom` (o'tmishdagi sana ham bo'lishi mumkin), `term`, `reviewDate`;
  - **versiyalar** (`AgreementVersion`) — har bir o'zgarish yangi versiya bo'ladi va eski versiyalar o'zgarmaydi.
- **9 savol strukturasi** (SPEC 2F.2): `parties`, `contributions`, `duties`, `profitRule`, `lossRule`, `custody`, `exitClause`, `arbiter`, `term`.
  - Har bir savol uchun `QuestionStatus`: `ANSWERED` yoki `NOT_APPLICABLE + reason` (izoh majburiy).
  - **To'liqlik indikatori** «N / 9». 9/9 bo'lmaguncha imzolash bosqichi **ochilmaydi**.
  - Validatsiyalar:
    - vazifada **yagona mas'ul** bo'lishi shart («hamma» qabul qilinmaydi);
    - har bir vazifada «bajarilmasa» bandi bo'ladi;
    - foyda faqat bp ko'rinishida;
    - hakam tomonlardan biri bo'lishi mumkin emas;
    - ko'rik davriyligi oyiga 1 martadan siyrak bo'lsa, ogohlantirish chiqadi.
  - **Tur bo'yicha moslashuv** (strategy pattern): `LOAN` → 3-savol = qaytarish jadvali, 4–5-savollar = «foiz yo'q» (avtomatik); `PARTNERSHIP` → 2E.1 validatorlari; `FAMILY` → guvoh va hakam ixtiyoriy.
- **Imzolar** (`Signature`: `PARTY | WITNESS | ARBITER`): shu qurilmada imzo chiziladi; hakam roziligi ham imzo bilan olinadi. Versiya o'zgarsa, imzolar qayta so'raladi.
- **Kelishuv PDF'i:** 9 savol bo'limlari oddiy tilda, imzo bloklari bilan, `core/pdf` orqali. Shablonlarda `reviewStatus` bor.
- **Append-only jurnal** (`JournalEntry`):
  - kelishuvga bog'langan barcha moliyaviy yozuvlar shu jurnal orqali yoziladi;
  - `UPDATE` va `DELETE` taqiqlanadi (repository darajasida + Drift trigger);
  - tuzatish faqat `CORRECTION` turidagi yangi yozuv bilan qilinadi;
  - **xesh-zanjir:** SHA-256, RFC 8785 (JCS) kanonik JSON, `hash_n = SHA256(prevHash + "\n" + canonical(entry))`, genesis = 64 ta `0`, har bir kelishuvning o'z zanjiri bor;
  - `verifyChain(agreementId)` — zanjirni tekshiradi va birinchi buzilgan yozuvni qaytaradi.
- **Og'zaki kelishuvni yozib olish ustasi** (SPEC 2F.9): `effectiveFrom` o'tmishda; shu kungacha bo'lgan holat bitta `OpeningBalance` jurnal yozuvi sifatida kiritiladi va tomonlar imzo bilan tasdiqlaydi.
- Haftalik vazifalar uchun triggerlar: `AGREEMENT_SIGNED`, `ORAL_AGREEMENT_RECORDED`.

**Qabul mezonlari:**
- [ ] `journal_chain.json` test vektori yashil (xeshlar desktop bilan bitma-bit mos).
- [ ] Jurnalni o'zgartirish yoki o'chirishga urinish xato beradi (repository va DB trigger testlari).
- [ ] 9/9 bo'lmasa, imzolash bloklanadi; «tegishli emas» izohsiz qabul qilinmaydi.
- [ ] Egasiz yoki «hamma»ga yozilgan vazifa validatsiyadan o'tmaydi.
- [ ] Yozuv o'zgartirilgan bazada `verifyChain` buzilgan joyni aniq topadi.

---

# E. 4-QONUN: «RIBODAN QOCH! QARZGA TUSHSANG — REJA BILAN CHIQ!»

## VAZIFA 10 — Qarz inventari, haqiqiy narx, friction, qarz tilxati (SPEC 2C.7, 2D.3, 2D.5, 2D.6)
- **`Debt`:**
  - `creditorType` (`BANK | SHOP | RELATIVE | FRIEND | OTHER`);
  - `principal`, `remaining`, `monthlyPayment`, `dueDate`, `reason`, `hasMarkup`, `markupAmount`, `priority`, `earlyRepaymentTerms`;
  - **jadval turi:** `ANNUITY | DIFFERENTIATED | FIXED_MARKUP | MANUAL` (bank kreditlari uchun);
  - to'lovlar tarixi (`DebtPayment`), shu jumladan `isPrepayment`.
- **Nasiya daftari** = `Debt` ning `SHOP` turi.
- **`Receivable`** (foydalanuvchi bergan qarzlar): **foiz maydoni umuman yo'q**. Muddat kelganda xushmuomala eslatma chiqadi.
- **Umumiy ko'rsatkichlar:** jami qarz, oylik qarz yuki (daromadga nisbatan %).
- **Qarzning haqiqiy narxi:** asosiy summa → jami to'langan → ortiqcha to'lov. Imkoniyat narxi `Goal` lar bilan taqqoslanadi (`Goal` jadvali shu vazifada yaratiladi).
- **Yangi qarz oldidan friction so'rovi** (`BorrowCheck`): zaruratmi, foizsiz muqobil bormi, oylik yuk necha %. Natija qarz yozuvida saqlanadi. Foizli qarz kiritilganda qizil ogohlantirish chiqadi.
- **Qarz tilxati** = `Agreement(type = LOAN)` (Vazifa 9A dvigateli):
  - to'lov rejasini (`RepaymentSchedule`) kiritish **majburiy** (bu 3-savolning javobi);
  - guvohlar ro'yxati;
  - ikkinchi tomon va guvohlar **shu qurilmada** ismini yozib, ekranda imzo chizadi;
  - `core/pdf` orqali PDF yaratiladi va ulashiladi;
  - matnda «shaxsiy hisob uchun yozuv, yuridik kafolat emas» degan izoh bo'ladi.
- `DebtPayment` lar tilxatga bog'langan qarzlarda **jurnal** (`JournalEntry`) orqali yoziladi.
- Darvozadagi (Vazifa 9) qarz sharti endi haqiqiy ma'lumotga ulanadi.

**Qabul mezonlari:**
- [ ] `Receivable` modelida foiz maydoni yo'qligi test bilan tasdiqlangan.
- [ ] To'lov rejasisiz qarzni saqlab bo'lmaydi.
- [ ] PDF'da o'zbekcha belgilar (`oʻ`, `gʻ`) to'g'ri chiqadi (golden test).
- [ ] Haqiqiy narx hisobi 4 xil jadval turi uchun ham testlangan.

## VAZIFA 11 — `DEBT_RECOVERY` 70/20/10, payoff planner, sotiladigan buyumlar, «Qarzsiz kun» (SPEC 2D.1, 2D.2, 2D.7, 2D.9)
- **`BudgetMode`** (`STANDARD | DEBT_RECOVERY`):
  - faol qarz bo'lsa, ilova rejimni taklif qiladi;
  - `AllocationSplit` standarti 70/20/10, sozlanadi;
  - **jamg'arma ulushi 0 ga tushirilmaydi** (minimal 1%, 0 tanlansa ogohlantirish);
  - majburiy to'lovlar 70% ichida hisoblanadi;
  - barcha qarzlar yopilganda rejim avtomatik `STANDARD` ga qaytadi va bo'shagan 20% ni yo'naltirish taklif qilinadi.
- **Payoff planner:**
  - har bir jadval turi uchun **amortizatsiya simulyatori** (oyma-oy, tiyin aniqligida);
  - odatiy va tezlashtirilgan grafik yonma-yon;
  - natija: «N oy erta» va «X so'm tejaldi»;
  - qo'shimcha to'lov manbalari: 20% ulush, qutqarilgan pul (Vazifa 8) va sotilgan buyumlar.
- **Qarzlarni yopish tartibi:** standart — avval foizli qarzlar (eng yuqori ustamalisidan), keyin foizsizlar (muddati yaqinidan). Foydalanuvchi tartibni qo'lda o'zgartira oladi.
- **Muddatidan oldin to'lash shartlari** (jarima, komissiya) hisobga olinadi. Ekranda «taxminiy hisob» izohi turadi.
- **`DebtContributor`:** qarzni bir necha kishi to'lashi mumkin (masalan, o'g'il). MVP'da bu oddiy yozuv bo'ladi, ilovaga taklif qilish keyinroq.
- **Sotiladigan buyumlar** (`SellableItem`: `LISTED | SOLD`): sotilgan buyum puli bir bosishda tanlangan qarzga qo'shimcha to'lov sifatida yo'naltiriladi.
- **«Qarzsiz kun»:** har bir qarz va umumiy prognoz sanasi, har to'lovdan keyin yangilanadi. Qarz yopilganda nishonlash ekrani chiqadi va bo'shagan summani jamg'armaga yo'naltirish taklif qilinadi.
- Bosh ekranga «Qarzsiz kun» kartasi qo'shiladi.

**Qabul mezonlari:**
- [ ] Amortizatsiya simulyatori `amortization.json` vektorlaridan (amort-001…003, to'liq jadvallar bilan) o'tadi: Akmal — 39 mln, 14 oy → 1,6 mln qo'shimcha to'lov bilan 9 oy, 2,4 mln bilan 8 oy.
- [ ] Simulyatsiya oxirida qoldiq aniq 0 bo'ladi (tiyin farqisiz).
- [ ] Rejimning avtomatik `STANDARD` ga qaytishi testlangan.
- [ ] Jamg'arma ulushini 0 qilishga urinish to'xtatiladi.

## VAZIFA 12 — Marosim rejalovchisi va maqsadlar (SPEC 2D.8)
- **`CeremonyPlan`:**
  - turlari: `TOY`, `BESHIK_TOY`, `SUNNAT_TOY`, `MARAKA`, `OTHER`;
  - holatlar: `DRAFT → DISCUSSED → CONFIRMED`.
- **`CeremonyBudgetLine`:**
  - bir martalik yoki «kishi boshiga × mehmonlar soni» ko'rinishidagi qatorlar;
  - har bir qator uchun `FundingSource`: `SAVINGS | FAMILY | EXPECTED_GIFTS | DEBT`.
- **Asosiy qoida:** `DEBT` manbali qator bo'lsa, rejani `CONFIRMED` ga o'tkazishdan oldin **oilaviy muhokama bosqichi** majburiy. Unda «Buni qarzsiz qanday o'tkazamiz?» degan savollar ro'yxati bo'ladi va barcha `ADULT` a'zolar belgi qo'yadi.
- **`CeremonyScenario`:** 2–3 stsenariy yonma-yon taqqoslanadi: jami narx, qarz, to'lash muddati (Vazifa 11 simulyatori bilan) va shu pulga erishiladigan muqobil `Goal` lar.
- **To'yona o'rniga jamg'arma:** yosh oila uchun `Goal`. Mehmonlar hissasi qo'lda kiritiladi, ulashiladigan matn yoki QR beriladi. Real pul o'tkazmasi keyinroq bo'ladi.
- Ijtimoiy bosimga qarshi kontent kartochkalari («El uch kun gapiradi»).

**Qabul mezonlari:**
- [ ] `DEBT` manbasi bilan muhokamasiz `CONFIRMED` holatiga o'tib bo'lmaydi (test bilan tekshirilgan).
- [ ] Stsenariy taqqoslashidagi to'lash muddati Vazifa 11 simulyatori natijasiga mos keladi.

---

# F. 5-QONUN: «PULNI HALOL ISHGA SOL»

## VAZIFA 13 — Sheriklik domeni, shartnoma ustasi, buyout (SPEC 2E.1, 2E.2, 2E.6)
- **`Partnership`:**
  - turi: `MUDARABA | MUSHARAKA`;
  - holat: `DRAFT → SIGNED → ACTIVE → CLOSED`;
  - muddat.
- **`PartnerRole`** (`CAPITAL_PROVIDER | WORKER | BOTH`) va **`CapitalContribution`** (pul yoki narxlangan uskuna ro'yxati).
- **Validatsiya (domen qatlamida, testlar bilan):**
  - foyda faqat sof foydaning foizi (`basisPoints`) sifatida, ulushlar yig'indisi 100%;
  - **qat'iy summa yoki kafolatli daromad belgilashni kiritib bo'lmaydi.** Urinilsa, «Bu sheriklik emas — ribo yoki qarz» degan tushuntirish chiqadi;
  - `MUDARABA`: kapital zarari `WORKER` ga faqat `negligence = true` va izoh bilan yuklanadi;
  - `MUSHARAKA`: zarar `capital_i / Σcapital` nisbatda taqsimlanadi.
- **Shartnoma ustasi (wizard)** = `Agreement(type = PARTNERSHIP)` (Vazifa 9A dvigateli). U 9 savol bo'yicha yuradi va unga sheriklikka xos qadamlar qo'shiladi: tur, kapital, ulushlar, zarar qoidalari, buyout. Natijada PDF chiqadi.
  - **Tomonlar va guvohlar shu qurilmada imzo chizadi.**
  - Shartnomaga keyingi o'zgarishlar **yangi versiya** sifatida saqlanadi va qayta imzolanadi.
  - Shartnomasiz sheriklik ochib bo'lmaydi.
- **Buyout (kamayib boruvchi musharaka):** foyda ulushidan oz-ozdan to'lash jadvali, qolgan ulush vizual ko'rsatiladi.
- **Darvoza bilan bog'liqlik** (SPEC 2E.6):
  - **kapital kiritish** → `ReadinessGate` (Vazifa 9) tekshiriladi;
  - **kapital qabul qilish** → darvoza yo'q, lekin oilaviy rozilik (`ADULT` a'zolar) va «bu qarz emas» tushuntirishi majburiy.
- Shartnoma shablonlari `reviewStatus` bilan belgilanadi (yurist va ulamo tekshiruvi). `PENDING` shablon release'da ogohlantirish bilan ko'rsatiladi.

**Qabul mezonlari:**
- [ ] Validatsiya qoidalarining har biri uchun ijobiy va salbiy testlar bor.
- [ ] Kafolatli daromadni kiritish UI va domen darajasida bloklanadi.
- [ ] Shartnoma versiyasi o'zgarganda imzolar qayta so'raladi.
- [ ] Darvoza faqat kapital kirituvchiga qo'llanishi test bilan tekshirilgan.

## VAZIFA 14 — Venture ledger, taqsimot, «Hunardan ishga», taklif detektori (SPEC 2E.3–2E.5, 2E.8)
- **`VentureLedger` / `VentureEntry`:**
  - kirim (buyurtmalar) va xarajatlar (material, ish haqi), chek rasmi biriktirilishi mumkin (shifrlangan lokal saqlash);
  - barcha yozuvlar Vazifa 9A **jurnali** orqali yoziladi (append-only, xesh-zanjir);
  - **biznes puli uy pulidan ajratilgan** bo'ladi. Xonadon byudjetiga faqat taqsimlangan foyda ulushi `Income` sifatida tushadi (`sourceType = MOL / TAVAKKAL`).
- **`ProfitDistribution`:**
  - davr yopilganda foyda yoki zarar Vazifa 13 qoidalari bo'yicha `allocate` orqali taqsimlanadi;
  - buyout to'lovi taqsimotdan avtomatik ayriladi;
  - yopilgan davr o'zgartirilmaydi, tuzatish faqat yangi yozuv bilan kiritiladi.
- **`ForceMajeureEvent`:** izoh va dalillar bilan; zarar qoidaga ko'ra taqsimlanadi.
- **Sherikka shaffoflik:** davr hisobotini PDF qilib ulashish (kirim, xarajat, foyda, taqsimot, buyout holati).
- **«Hunardan ishga» rejalovchisi:**
  - `Skill` ro'yxati;
  - `VentureIdea`: CAPEX ro'yxati, oylik kirim va xarajat;
  - **3 stsenariy** (pessimistik, o'rtacha, optimistik);
  - payback va ulushdan keyingi foyda;
  - bir bosishda shartnoma qoralamasiga o'tish (Vazifa 13).
- **«Kafolatlangan foyda» detektori** (`OfferCheck`):
  - tekshiruv savollari: kafolatlanganmi, zarar bo'lishiladimi, real mol yoki ish bormi, yangi a'zo jalb qilish talab qilinadimi, shoshiltirish bormi, yozma shartnoma bormi;
  - natija yashil, sariq yoki qizil bo'ladi va har bir bayroq izohlanadi;
  - ilovaning istalgan joyidan ochiladi (bosh ekranda «Taklifni tekshirish» tugmasi).
- UX ohangi: «Ot bilan omoch». Sadaqa yoki minnat ohangi bo'lmaydi.

**Qabul mezonlari:**
- [ ] Taqsimot testlari: mudoraba foyda, mudoraba zarar, musharaka zarar va buyout bilan foyda holatlari tekshirilgan.
- [ ] Yopilgan davrni o'zgartirib bo'lmaydi.
- [ ] Payback hisobi testlangan (masalan, CAPEX 8 mln).
- [ ] OfferCheck qaror jadvali unit testlangan.

---

# F2. 6-QONUN: «KELISHUVNI YOZMA TUZ»

## VAZIFA 14A — Vazifalar, oylik ko'rik, «katta foyda», nizo va hakam, oilaviy kelishuvlar (SPEC 2F.4, 2F.5, 2F.7, 2F.8, 2F.10)
- **Vazifalar va «bajarilmadi» oqimi** (`DutyIncident`):
  - har bir tomon «vazifamni bajara olmayapman» deb xabar beradi (sabab, sana, o'rniga yechim);
  - ilova shartnomaning tegishli bandini darhol ko'rsatadi;
  - hodisa jurnalga yoziladi va keyingi ko'rikda ko'rinadi;
  - ohang ayblovsiz: «kelishilgan qoidaga qaytamiz».
- **Oylik ochiq hisob ko'rigi** (`AccountReview` + `ReviewAck`):
  - ko'rik shartnomadagi `custody.reviewEvery` bo'yicha avtomatik rejalashtiriladi, eslatma yuboriladi;
  - sessiya ekranida: davr yozuvlari, yakun, ochiq hodisalar, zanjir tekshiruvi natijasi (`verifyChain`);
  - har bir tomon `AGREE` yoki `OBJECT + izoh` belgilaydi;
  - **ko'rik bayonnomasi PDF** yaratiladi, unda `chainHead` qayd etiladi;
  - bayonnomadan keyin o'sha davrning yozuvlariga faqat `CORRECTION` qo'shish mumkin, u keyingi ko'rikda ko'rinadi.
- **«Katta foyda» ogohlantirishi** (`ProfitSpikeAlert`):
  - shart: davr foydasi ≥ rejadagining 150% **yoki** oxirgi 3 davr o'rtachasining ≥ 200% (bp'da, sozlanadi);
  - taqsimotdan **oldin** chiqadi: 4–5-bandlarni ikkala tomon qayta o'qiganini belgilash + navbatdan tashqari ko'rik taklifi;
  - ohang: «Barakali foyda — tabriklaymiz! Endi kelishuvni birga qayta o'qib chiqaylik».
- **Nizo va hakam** (`Dispute`, `ArbiterDecision`):
  - nizo ochilganda kelishuv holati `IN_DISPUTE` bo'ladi va taqsimot to'xtatib turiladi;
  - **«hakam uchun ish papkasi» PDF**: amaldagi va oldingi versiyalar, tegishli davr yozuvlari va zanjir tekshiruvi, ko'rik bayonnomalari, vazifa hodisalari, ikki tomonning talablari;
  - hakam qarori yozib qo'yiladi; kerak bo'lsa, yangi versiya yaratiladi va kelishuv `ACTIVE` ga qaytadi.
- **Yillik yangilash:** `reviewDate` dan 30 kun oldin eslatma. «O'zgarishsiz tasdiqlash» ham yangi versiya va qayta imzo hisoblanadi.
- **Oilaviy kelishuvlar** (`FAMILY`): yengil format, `ADULT` a'zolar tasdig'i. 4 ta shablon: «Uyda kim nima qiladi», «Pul qayerda turadi», «Havas chegarasi» (2B.3 bilan bog'langan), «Oila kengashi qachon».
- **Kelishuvlar markazi ekrani:** barcha kelishuvlar, ularning holati, keyingi ko'rik sanasi, ochiq hodisalar va nizolar.
- Bosh ekranga «Yaqinlashayotgan ko'rik / yangilash» kartasi qo'shiladi.
- 6-bob kontenti (placeholder) va triggerlar: `ACCOUNT_REVIEW_COMPLETED`, `FAMILY_AGREEMENT_CREATED`.

**Qabul mezonlari:**
- [ ] `profit_spike.json` test vektori yashil.
- [ ] `IN_DISPUTE` holatida taqsimot bloklanadi (test).
- [ ] Bayonnomadagi `chainHead` keyingi `verifyChain` bilan mos keladi; o'zgartirilgan yozuv aniqlanadi.
- [ ] Hakam papkasi PDF'ida barcha bo'limlar bor (snapshot test).
- [ ] Yillik yangilash eslatmasi rejalashtiriladi va qurilma qayta yoqilgandan keyin ham ishlaydi.

---

# F3. 7-QONUN: «TEKSHIRMAGAN ISHGA PUL TIKMA»

## VAZIFA 14B — Besh xavf belgisi, tekshiruv, piramida, oilaviy zaxira, «to'xta, maslahatlash», hunar shablonlari (SPEC 2G)
- **Besh xavf belgisi** (`ScamSign`, 2G.1): taklif tekshiruviga 3 ta savol qo'shiladi (`exitEasy`, `license`, `verifiedInPerson`); belgilar javoblardan aniqlanadi; baho: 1 belgi — kamida sariq, 2+ — qizil; umumiy baho 2E.5 bilan birlashtiriladi (eng og'iri). Har belgi izohlanadi.
- **«O'z ko'zim bilan ko'raman»** (2G.2): tekshiruv ro'yxati ekrani (ombor, mol, hujjat, ruxsat, to'lov manbai, qaytarish tartibi); natija «ko'rsatishdi / rad etishdi / so'ramadim»; rad etish — `NO_REAL_BUSINESS`.
- **Va'da qilingan foyda** (2G.3): oylik bp → yillik oddiy va murakkab ko'paytma; faqat ogohlantirish.
- **Piramida** (2G.4): `k` va `N` bo'yicha qavatlar, jami, oxirgi qavat ulushi; ta'limiy ekran.
- **Oilaviy zaxira** (2G.5): katta summa (valyuta bilan) → avval 6 oylik zaxira kamomadi, qolgani sarmoyaga; qorovulga qo'yish va «Hunardan ishga»ga o'tish.
- **«To'xta, maslahatlash»** (2G.6): taklifda summa va maslahatchi; «pul qo'yaman» faqat maslahatchi yozilgach va 24 soatdan keyin; qaror tarixda (`DECLINED | POSTPONED | ACCEPTED`). Sxema v16: `offer_checks` ga yangi ustunlar + migratsiya testi.
- **G'arar / qimor** (2G.7): natijada `RIBO | GHARAR | QIMOR` toifalari.
- **Hunar shablonlari** (2G.8): payvandlash ustaxonasi — CAPEX nomlari oldindan, summasiz.
- 7-bob kontenti (placeholder) va haftalik vazifalar (mavjud triggerlar: `OFFER_CHECKED`, `EMERGENCY_TARGET_SET`, `VENTURE_IDEA_CREATED`).

**Qabul mezonlari:**
- [ ] `scam_signals.json`, `promised_return.json`, `pyramid_levels.json`, `lump_sum_split.json` vektorlari yashil.
- [ ] Ikki belgi (masalan, shoshirish + qiyin chiqish) bahoni qizilga ko'taradi (test).
- [ ] «Pul qo'yaman» maslahatchisiz va 24 soatdan oldin bloklanadi (test).
- [ ] Katta summa taqsimotida zaxira to'lmaguncha sarmoya ulushi faqat ortgan qism (test).
- [ ] Migratsiya v15 → v16: eski tekshiruvlar yo'qolmaydi (test).

---

# G. RELIZ TAYYORGARLIGI

## VAZIFA 15 — Onboarding, eksport, sifat va reliz
- **Onboarding** (≤ 5 ekran):
  - til, PIN, oila a'zolari;
  - oylik daromad turi (kunlik naqd, buyurtma bo'yicha yoki oylik maosh) — shu tanlovga qarab bosh ekran va eslatmalar moslashadi;
  - faol qarz bormi → `DEBT_RECOVERY` taklifi.
- **Shifrlangan eksport va import:** butun baza foydalanuvchi parolidan hosil qilingan kalit bilan shifrlangan fayl sifatida saqlanadi. Qayta tiklash ham shu fayl orqali bo'ladi.
- **Accessibility:** katta shrift, TalkBack yorliqlari, kontrast. Kam tajribali foydalanuvchi uchun 48dp+ tugmalar.
- **Ishlash ko'rsatkichlari:** sovuq start < 2 s (o'rta segment telefon), ro'yxatlar paginatsiyasi.
- **Release hardening:** R8/ProGuard, Dart `--obfuscate --split-debug-info`, imzolash konfiguratsiyasi repodan tashqarida saqlanadi.
- **Yakuniy E2E test** (`integration_test`): Akmal ssenariysi boshidan oxirigacha:
  - daromad → ulush → audit → havas chegarasi → obuna bekor qilish → qutqarilgan pulni ko'chirish → qarz → 70/20/10 → payoff → qarz yopilishi → darvoza ochilishi → Jasur bilan musharaka (9/9 savol, imzolar) → vazifa hodisasi («bot ishdan chiqdi») → oylik ko'rik → davr taqsimoti (1,4 mln ulush).
- `docs/RELEASE_CHECKLIST.md`.

**Qabul mezonlari:**
- [ ] E2E ssenariy yashil.
- [ ] Eksport → o'chirish → import natijasida ma'lumotlar 1:1 tiklanadi.
- [ ] Release APK obfuskatsiya qilingan, `FLAG_SECURE` va lock ishlaydi.

---

## UMUMIY «TAYYOR» TA'RIFI (har bir vazifa uchun)
- CI yashil, `analyze` toza.
- Yangi domen mantiqi testlar bilan qoplangan.
- Pul hisoblari faqat `core/money` orqali bajarilgan.
- UI matnlari ARB'da (`uz` va `ru`). Taqiqlangan iboralar testi (Vazifa 9 dan keyin) yashil.
- Maxfiy ma'lumot loglarda yo'q.
- `docs/CHANGELOG.md` va `docs/OPEN_QUESTIONS.md` yangilangan.

## RELIZDAN OLDIN KODDAN TASHQARIDA HAL QILINADIGAN MASALALAR
- Diniy matnlarning ulamo tekshiruvi (kontent va brend — loyihaniki, mustaqillik qarori).
- Diniy matnlar va sheriklik shablonlarining ulamo tomonidan tekshiruvi (`religiousReviewStatus` / `reviewStatus` → `APPROVED`).
- Tilxat va shartnoma shablonlarining yuristga ko'rsatilishi.
- Maxfiylik siyosati (shaxsiy ma'lumotlar to'g'risidagi qonun) va Play Market moliyaviy ilovalar talablari.
