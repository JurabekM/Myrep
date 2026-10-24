# «BARAKA DASTUR» — MVP-1 ISHGA TUSHIRISH
> AI-dasturchi uchun. Spetsifikatsiya: `docs/SPEC.md` (bu `FINTECH_PROMPT.md` v0.7 ning nusxasi).

---

## QANDAY ISHLATILADI (dasturchi uchun yo'riqnoma)
1. Bo'sh repo yarating va `FINTECH_PROMPT.md` ni `docs/SPEC.md` nomi bilan joylang.
2. Repo ildiziga `CLAUDE.md` faylini qo'shing va unga quyidagini yozing:
   «Har sessiya boshida `docs/SPEC.md` ning 3, 4, 5, 6 va 12-bo'limlarini o'qi. 4-bo'lim (ADR) qat'iy.»
3. Quyidagi vazifalarni **har birini alohida sessiyada va ketma-ket** bering. Har bir sessiyaga «Umumiy kirish» va bitta vazifa matnini nusxalang.
4. Har bir vazifadan keyin «Qabul mezonlari»ni o'zingiz tekshiring, keyin commit qiling, shundan so'nggina keyingi vazifaga o'ting.

---

## UMUMIY KIRISH (har bir sessiya boshiga qo'yiladi)
```
Sen «Baraka Dastur» loyihasining senior Flutter + Kotlin dasturchisisan.
Avval docs/SPEC.md ni to'liq o'qi. 4-bo'lim (texnik qarorlar) qat'iy — undan chetga chiqma.
Bu sessiyada FAQAT quyidagi vazifani bajar. Keyingi bosqich funksiyalarini qo'shma.
Ishni boshlashdan oldin qisqa reja yoz (fayllar ro'yxati + qadamlar), keyin bajar.
Oxirida: nima qilinganini, qabul mezonlarining har biri bo'yicha holatni va ochiq savollarni yoz.
Kod, identifikatorlar va commit xabarlari inglizcha. Izohlar, hujjatlar va UI matnlari o'zbekcha.
```

---

## VAZIFA 1 — Loyiha skeleti va infratuzilma
**Maqsad:** keyingi barcha ishlar quriladigan toza poydevorni tayyorlash.

**Bajariladi:**
- Flutter loyihasi yaratiladi: `applicationId` = `uz.barakadaftari.app` (vaqtinchalik), minSdk 26, Flutter versiyasi `.fvmrc` orqali qotiriladi.
- Feature-first papka tuzilmasi:
  ```
  lib/
    app/            (router, theme, l10n, bootstrap)
    core/           (money, time, ids, errors, result, security bridge)
    features/
      income/  vault/  expenses/  obligations/  audit/  content/  home/  lock/
        presentation/  domain/  data/
  android/app/src/main/kotlin/.../native/   (Pigeon host implementatsiyalari)
  pigeons/          (Pigeon kontrakt fayllari)
  test/  integration_test/
  ```
- Riverpod (generator bilan), go_router (bo'sh ekranlar uchun marshrutlar: `/lock`, `/home`, `/income/new`, `/vault`, `/audit`, `/content`), `freezed` va `json_serializable`.
- `flutter gen-l10n`: `uz` va `ru` ARB fayllari. Barcha UI matnlari faqat ARB orqali beriladi, hardcode taqiqlanadi.
- Lint: `very_good_analysis`, `strict-casts`, `strict-raw-types`.
- Pigeon sozlanadi. Namunaviy kontrakt: `SecurityApi` (metodlar hozircha stub).
- GitHub Actions workflow: `dart format --set-exit-if-changed`, `flutter analyze`, `flutter test`, `flutter build apk --debug`.
- «Daftar» mavzusi uchun placeholder `ThemeData`: qog'oz rangidagi fon va o'qilishi oson shrift. Light va dark rejimlar bo'ladi.

**Qabul mezonlari:**
- [ ] `flutter analyze` 0 ta ogohlantirish beradi va CI yashil.
- [ ] Ilova ishga tushadi, barcha marshrutlar placeholder ekranlarni ochadi.
- [ ] Til `uz` ↔ `ru` almashadi.
- [ ] Pigeon kodi generatsiya qilinadi va Kotlin stub chaqiruvi Flutter'dan javob qaytaradi.

---

## VAZIFA 2 — Xavfsizlik qatlami (Kotlin + Flutter)
**Maqsad:** moliyaviy ma'lumot birinchi kundanoq himoyalangan bo'lishi.

**Bajariladi (Kotlin, Pigeon `SecurityApi` orqali):**
- Keystore'da AES-GCM kalit yaratiladi (StrongBox mavjud bo'lsa, StrongBox'da).
- `getOrCreateDatabaseKey()`: 256-bit tasodifiy kalit yaratadi, uni wrap qilib private storage'ga yozadi va unwrap qilib qaytaradi.
- `BiometricPrompt` (`BIOMETRIC_STRONG` yoki qurilma krediensiali).
- `setSecureFlag(enabled)` — `FLAG_SECURE`.
- `getIntegritySignals()`: root belgilari, emulyator, debugger ulanganligi, imzo xeshi mos kelishi. MVP'da ilova **bloklanmaydi**, foydalanuvchiga ogohlantirish ko'rsatiladi va signal lokal logga yoziladi.

**Bajariladi (Flutter):**
- Birinchi ishga tushirishda PIN (6 raqam) o'rnatiladi va biometriya ixtiyoriy yoqiladi. PIN Argon2id (yoki PBKDF2-SHA256 ≥310k) orqali hosilaga aylantiriladi, PIN o'zi saqlanmaydi.
- Lock ekrani. Ilova fonga o'tganidan N daqiqa (standart 2) keyin qayta qulflanadi.
- PIN 5 marta noto'g'ri kiritilsa, o'sib boruvchi kutish vaqti qo'yiladi.
- Moliyaviy ekranlarda `FLAG_SECURE` avtomatik yoqiladi (marshrut darajasida).
- `AndroidManifest`: `allowBackup="false"`, `dataExtractionRules` bilan backup cheklanadi.
- Release log siyosati: `debugPrint` o'chiriladi, maxfiy maydonlar loglanmaydi.

**Qabul mezonlari:**
- [ ] Kalit wrap/unwrap uchun Kotlin unit test bor. Kalit ilovani qayta ishga tushirgandan keyin ham bir xil chiqadi.
- [ ] PIN hosilasi va tekshiruvi uchun Dart testlari bor (to'g'ri, noto'g'ri va lockout holatlari).
- [ ] Moliyaviy ekranda skrinshot olib bo'lmaydi (qo'lda tekshiruv).
- [ ] Fon → qaytish tsikli timeout'dan keyin lock ekranini ochadi.

---

## VAZIFA 3 — Domen yadrosi va shifrlangan baza
**Maqsad:** butun ilovaning pul matematikasi va ma'lumotlar modeli. Eng ko'p test shu vazifada yoziladi.

**Bajariladi:**
- `core/money`:
  - `Money(int minorUnits, CurrencyCode currency)` (immutable) va `CurrencyCode` (`UZS, USD, EUR, RUB`);
  - arifmetika; har xil valyutalarni qo'shishga urinishda `CurrencyMismatchException`;
  - `MoneyRounding`;
  - `allocate(Money total, List<int> ratios)` — largest remainder usuli;
  - `percentOf(Money, basisPoints)`;
  - `FxRate` va `convert(Money, FxRate)`;
  - UZS formatlash: `8 000 000 so'm`, bo'sh joy bilan guruhlash, lokalga mos.
- `core/ids`: UUIDv7 generatori. `core/time`: `Clock` abstraksiyasi (testlar uchun), `Asia/Tashkent` lokal sana va `weekAnchor = FRIDAY`.
- Drift + SQLCipher. Kalit Vazifa 2 dagi `getOrCreateDatabaseKey()` dan olinadi.
- **Sxema v1** jadvallari (har birida SPEC 4.4 dagi umumiy maydonlar bo'ladi):
  - `households`, `members`;
  - `incomes` (`source`, `channel CASH|CARD`, `memberId`, `sourceType` nullable);
  - `expenses` (`categoryId`, `channel`, `memberId`, `necessity` nullable, `envelopeId` nullable, `isGift`, `isOstentation`, `fundedByDebt` — keyingi bosqich maydonlari nullable yoki default qiymat bilan);
  - `categories`;
  - `obligations` (doimiy to'lovlar: summa, kun, turi);
  - `debts` (`creditorType`, `principal`, `remaining`, `monthlyPayment`, `dueDate`, `reason`, `hasMarkup`);
  - `assets` (SPEC 4.3) va `asset_snapshots`;
  - `vault_transactions` (`vaultAssetId`, `type DEPOSIT|WITHDRAW`, `reason`);
  - `allocation_rules` (`basisPoints`, `mode FIXED|PROGRESSIVE`, `fixedAmount` nullable);
  - `fx_rates`.
- Har bir aggregate uchun repository interfeysi (domain) va Drift implementatsiyasi (data).
- Standart kategoriyalar seed qilinadi: ijara, kredit, oziq-ovqat, kommunal, telefon, benzin, yo'lkira, mayda kundalik xarajatlar, bola, sadaqa, boshqa.

**Qabul mezonlari:**
- [ ] `allocate` uchun property-based test: tasodifiy summa va ulushlarda qismlar yig'indisi = butun summa, hech bir qism manfiy emas.
- [ ] Valyuta aralashuvi exception beradi. UZS formatlash testlari bor.
- [ ] Repository'lar uchun in-memory Drift testlari bor (CRUD va soft delete).
- [ ] Shifrlangan DB faylini kalitsiz ochib bo'lmasligi tekshirilgan.
- [ ] Sxema versiyasi 1, migratsiya test infratuzilmasi tayyor.
- [ ] `core/money` qamrovi ≥ 95%.

---

## VAZIFA 4 — Daromad kiritish va «Kelajagim» jamg'armasi (1-qonun yadrosi)
**Maqsad:** «Avval o'zingga to'la» odati — SPEC 2.1, 2.2.

**Bajariladi:**
- **Tez daromad kiritish:** raqamli klaviaturali bitta ekran, oxirgi manba va kanal oldindan tanlangan. Saqlash ≤ 3 ta bosishda bajariladi.
- Saqlangandan so'ng **ulush taklifi** chiqadi: «Shundan X so'm — kelajagingiz uchun». Tugmalar: [Ajratish] [Boshqa summa] [Bu safar emas]. Ajratilganda `vault_transactions` ga DEPOSIT yoziladi.
- **AllocationRule sozlamalari:** 5% / 10% / qat'iy summa.
  - **Progressiv rejim:** 4 hafta ketma-ket ajratilsa, ulushni +1% ga oshirish taklif qilinadi.
- **«Kelajagim» ekrani:** balans, tarix va streak (ajratilgan haftalar soni). Miqdordan ko'ra odat ko'rsatkichi oldinda turadi.
- **Pul olish uchun friction:** tasdiqlash, sababni kiritish (majburiy) va PIN qayta so'raladi. Ilova «bu pul kelajakdagi o'zingizniki» degan eslatma ko'rsatadi.
- **Boshlang'ich balans («avval yig'ilgan pul»):** ilovadan oldin yig'ilgan naqd pul bir martalik DEPOSIT sifatida kiritiladi (`reason = INITIAL`).
- Matnlarda Maslahatchi ohangi saqlanadi: iliq, ayblamaydigan (SPEC 3).

**Qabul mezonlari:**
- [ ] Widget test: daromad 3 bosishda saqlanadi.
- [ ] Ulush hisobi `allocate` / `percentOf` orqali bajariladi, `double` ishlatilmaydi.
- [ ] Streak hisobi Clock mock bilan testlangan (hafta chegaralari jumadan boshlanadi).
- [ ] Pul olish PIN va sababsiz amalga oshmaydi.

---

## VAZIFA 5 — Xarajatlar, majburiyatlar, «Kimning puli?» va oylik audit
**Maqsad:** SPEC 2.3, 2.4, 2.5 — «Pul qayerga ketdi?».

**Bajariladi:**
- Xarajat kiritish (tez forma: summa, kategoriya, kanal). MVP-1 da `necessity` so'ralmaydi.
- **Majburiyatlar:** ijara, kredit, kommunal xizmatlar. To'lov kunidan 1 kun oldin eslatma yuboriladi (Kotlin WorkManager + bildirishnoma, Pigeon orqali).
- **Nasiya daftari:** `debts` jadvalida `creditorType = SHOP` bo'lgan yozuvlar, alohida ro'yxat ko'rinishida.
- **Oylik audit ustasi:** o'tgan oy uchun bosqichma-bosqich jarayon: daromad → majburiyatlar → kategoriyalar bo'yicha xarajat. Oxirida **«izohsiz qolgan summa»** chiqadi: `daromad − (majburiyatlar + kiritilgan xarajatlar + jamg'arma)`. Uni «mayda kundalik xarajatlar» deb belgilash yoki taqsimlash taklif qilinadi.
- **«Kimning puli?» ekrani:** oylik daromadning egalarga bo'linishi: uy egasi, bank, do'kon, kommunal, yoqilg'i, **o'zingiz**. Oddiy gorizontal bo'lak-diagramma, ranglari SPEC 9 ga mos.
- **Bosh ekran:** 1-raqam «O'zingizga to'langan (shu oy)», keyin «Kelajagim» balansi, streak, oy yakuni (+ yoki −) va «Shu haftaning vazifalari» kartasi (Vazifa 6 bilan ulanadi).
- **Oilaviy rejim (lokal):** bitta qurilmada bir nechta `member` bo'lishi va har bir yozuvda «kim» belgisi. Sinxronlash MVP-1 ga kirmaydi.

**Qabul mezonlari:**
- [ ] Izohsiz summa hisobi unit-testlangan, jumladan manfiy natija holati ham.
- [ ] Oy chegarasi sozlanadigan oylik kuni bilan to'g'ri ishlaydi (test bilan tekshirilgan).
- [ ] Eslatma qurilmada keladi (qo'lda tekshiruv) va ilova qayta ishga tushirilgandan keyin ham saqlanadi.
- [ ] Bosh ekrandagi KPI'lar repository ma'lumotlari bilan mos keladi (integration test).

---

## VAZIFA 6 — Kontent dvigateli: boblar, «Daftar sahifasi», haftalik vazifalar
**Maqsad:** ta'lim + amaliyot sikli. Kontent koddan ajratilgan holda saqlanadi.

**Bajariladi:**
- Kontent ilovaga o'rnatilgan JSON (`assets/content/`) sifatida keladi:
  - `Chapter` — id, tartib, sarlavha, matn bloklari, ixtiyoriy audio URL;
  - `Law` — raqam, matn;
  - `WeeklyTask[3]`;
  - **`religiousReviewStatus`** — `PENDING | APPROVED`.
- `PENDING` holatidagi diniy bloklar release build'da **ko'rsatilmaydi**.
- 1-bob uchun **faqat placeholder matn** bo'ladi (litsenziya hal bo'lguncha). Struktura va UI esa to'liq ishlaydi.
- **«Daftar sahifasi»:** foydalanuvchi qonunni o'z qo'li bilan yozadi (matn maydoni, qog'oz uslubida). `daftar_pages` jadvaliga saqlanadi.
- **Haftalik vazifalar:** checklist. Ba'zi vazifalar avtomatik belgilanadi, masalan: «Kelajagim» kartasi ochildi → 1-vazifa bajarildi; oylik audit yakunlandi → 3-vazifa bajarildi.
- Juma kuni ertalab «Yangi bob / haftalik yakun» bildirishnomasi yuboriladi.
- Bob ochilish mantiqi hozircha **vaqt bo'yicha** ishlaydi. Interfeys esa keyingi bosqichdagi odat asosidagi qoida uchun tayyor bo'ladi (`ChapterUnlockPolicy`).
- Har bir ta'limiy ekranda disklеymer bo'ladi: «Ta'limiy material. Fatvo yoki moliyaviy maslahat emas».

**Qabul mezonlari:**
- [ ] JSON sxemasi validatsiya qilinadi, buzuq kontent ilovani yiqitmaydi.
- [ ] `PENDING` diniy blok release'da ko'rinmasligi test bilan tekshirilgan.
- [ ] Avtomatik vazifa belgilanishi integration test bilan tekshirilgan.
- [ ] Juma bildirishnomasi rejalashtiriladi va qurilma qayta yoqilgandan keyin ham ishlaydi.

---

## MVP-1 DOIRASIDAN TASHQARIDA (qilinmaydi)
Quyidagilar MVP-1 ga kirmaydi:
- Zarur / Kerak / Havas tasnifi, konvertlar, obunalar;
- favqulodda zaxira va o'sadigan pul bo'linishi;
- qarzdan chiqish rejalovchisi va qarz tilxati;
- sheriklik moduli;
- backend va sinxronlash;
- bank integratsiyalari;
- tashqi muallif matnlari (ishlatilmaydi — mustaqillik qarori).
Bularning hammasi SPEC'dagi MVP-2…5 bosqichlarida qilinadi.

## UMUMIY «TAYYOR» TA'RIFI (Definition of Done)
- CI yashil, `flutter analyze` toza.
- Yangi domen mantiqi testlar bilan qoplangan.
- Barcha UI matnlari ARB'da, `uz` va `ru` tarjimalari bilan.
- Maxfiy ma'lumot loglarda yo'q.
- `docs/CHANGELOG.md` ga qisqa yozuv qo'shilgan.
- Ochiq savollar `docs/OPEN_QUESTIONS.md` ga yozilgan.
