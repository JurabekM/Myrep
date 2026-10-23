# O'zgarishlar tarixi

Format: [Keep a Changelog](https://keepachangelog.com/uz/1.1.0/) ruhida. Versiya: [SemVer](https://semver.org/lang/uz/).

## [Unreleased]

### «Baraka Dastur»: yangi nom, logotip va mustaqil kontent (2026-10-23)

**Sabab.** Google Play'da «Baraka» nomli boshqa ilova bor; kontent mualliflari bilan aloqa o'rnatilmadi. Ilovalar halol
moliyaning yetti tamoyili ma'no-mazmunidan ilhomlangan mustaqil asar sifatida davom etadi (SPEC boshidagi
«Mustaqillik qarori»).

**Nom.** Ko'rinadigan hamma joyda «Baraka Dastur»: oyna sarlavhasi, yon panel, tray, mini oyna, o'rnatuvchi
(`Baraka Dastur_0.1.0_x64-setup.exe`, 17 908 642 bayt, SHA-256 `AB49CBF9…952A`), o'rnatish papkasi
`%LOCALAPPDATA%\Baraka Dastur`, exe `baraka-dastur.exe` (`mainBinaryName`), Start menyusi, reestr, ilova ma'lumoti.
Ichki identifikatorlar o'zgarmadi (`uz.barakadaftari.desktop`, keyring `BarakaDaftari`, crate nomlari, `.baraka`) —
mavjud ma'lumotlar papkasi va kalit saqlanadi (OPEN_QUESTIONS).

**Logotip.** Yangi belgi: yashil fonda krem geometrik «B» va oltin sakkiz burchakli yulduz. Shriftsiz chiziladi
(`scripts/baraka_logo.py` — desktop va Android uchun bitta manba), < 48 px da yulduz tushiriladi. Ikonkalar
(`src-tauri/icons`, ICO 16–256) va ilova ichidagi `BrandMark` SVG yangilandi; ranglar `globals.css` tokenlarida
(`--color-brand*`).

**Personajlar va matnlar.**
- «Sobir hoji maslahati» → «Maslahatchi fikri»; kod izohlari va test ma'lumotlaridagi qissa personajlari shartli
  ismlarga almashtirildi (Akmal, Jasur, Zarina, Gulnora, Bekzod, Sardor, Shavkat aka; «Plyus» → «Tez Foyda»).
- Boblar (`spec/content/chapters.json`, mobil bilan bitta fayl): o'z nomlari («Avval o'zingizga», «Xarajatni
  ko'ring», «Zaxira va o'sish», «Qarzsiz yashash», «Halol sarmoya», «Yozma kelishuv», «Tekshirib, keyin
  ishoning»), o'z matni (uz/ru) va «Maslahatchi savoli»; qonun jumlalari qayta yozildi. Diniy bloklar PENDING.
- Qissadan olingan iboralar o'z so'zimiz bilan almashtirildi: «jangga yarador askar…», «El uch kun gapiradi…»,
  «Ot bilan omoch…», «Sichqon kemirgani» → «Inflyatsiya ta'siri», «Qorovul pul» → «Favqulodda zaxira», «Qal'a
  devori» → «Himoya zaxirasi», «baliqchining yemi», piramida matnlari, besh xavf belgisi izohlari («Ekran mol
  emas», «Siz xaridor emas, molsiz» va boshq.), «Dunyodagi eng katta savdo…», «hisob-kitobni uch marta qildim»,
  hunar shablonidagi personaj hikoyasi.
- Umumiy vektorlardagi ismlar almashtirildi (`agreement_completeness`, `amortization`, `journal_chain`);
  `journal_chain` xeshlari Rust bilan qayta hisoblandi, `SHA256SUMS` yangilandi (mobil bilan bir xil fayllar).
- Hujjatlar: SPEC v1.0 (mustaqillik qarori, personajlar jadvali shartli ismlar bilan, «Manba: N-qism» va homiy
  satrlari olib tashlandi, qonun nomlari o'z so'zimiz bilan), DESKTOP_PROMPT, MVP_PLAN, README, CLAUDE.md;
  litsenziya kutilayotgan bandlar «hal qilindi». Tarixiy CHANGELOG yozuvlari o'zgartirilmadi.

Tekshiruv: `cargo test` 368, clippy, vitest 93, typecheck/lint/format yashil; PDF snapshot'lari test ismlari
almashgani uchun qayta yaratildi. GUI (dev build): nom, logotip, 7 bob, bob matni, «Maslahatchi fikri», taklif
tekshiruvi, Kelajagim, Narx daftari, Marosimlar. O'rnatilgan build: eski o'rnatma olib tashlandi, yangisi `/S`
bilan o'rnatildi, sovuq start 64 ms, yopilish to'g'ri.

### Reliz tekshiruvi 0.1.0 — ichki sinov, imzolanmagan (2026-10-20)

**O'rnatuvchi:** `Baraka Daftari_0.1.0_x64-setup.exe`, 17 898 989 bayt (17,07 MiB),
SHA-256 `98851128BDDFC7A8C3A3741786A7A44EFDA18813AB307376386BACE8CB2608E1`. `/S` o'rnatish, `uninstall.exe /S`
(fayllar va reestr yozuvi o'chadi) va qayta o'rnatish — exit 0. Sovuq start (jarayon → sarlavhali oyna) 50–69 ms.
Kod imzosi yo'q — SmartScreen ogohlantiradi; reliz «ichki sinov» darajasida.

**Qanday sinaldi.** Avtomatik: lint, typecheck, vitest 93, `cargo test` 368, clippy, format, vektor manifesti.
O'rnatilgan build — buyruqlar bilan (ishga tushish, yopish, jarayon qoldig'i), chunki release oynasi
`set_content_protected` sababli skrinshotga tushmaydi. Tugmalarni bosish — dev buildda toza profilda:
PIN sozlash va kutish qoidasi, 11 menyu bandi, daromad + ulush, xarajat, oila kengashi (toifa, havas chegarasi,
rozilik, bayonnoma PDF), byudjet (obuna, konvert, o'tkazma), qayta ishga tushirishda saqlanish, `Tab`/skip-link,
RU tili, E2E ssenariysi qo'lda (6 qadam). DPI 200 % — 760 px oyna bilan taqlid.

**Topilgan va tuzatilgan**

- **Fon jarayon qolishi.** `Ctrl+Alt+B` mini oynasi bir marta ochilgan bo'lsa, asosiy oyna yopilgach jarayon
  yashirin qolardi (mini oyna yopilganda faqat yashiriladi). Endi asosiy oyna yo'q qilinganda `app.exit(0)`.
  Tuzatishsiz va tuzatish bilan qurilgan release exe'lar bir xil stsenariyda solishtirildi.
- **Vektor qoplanish testi** D16 dan beri yiqilgan edi (4 yangi suite ro'yxatda yo'q edi) — D16 hisobotidagi
  «`cargo test` yashil» noto'g'ri bo'lgan; tuzatildi.
- **Tor oyna / yuqori DPI'da ustma-ust tushish:** «Hunardan ishga» formasi (5 ustun), sheriklik formalari (4),
  narx daftari ko'rsatkichlari, eksport sana maydoni, payoff ko'rsatkichlari (kasrli summa qo'shni ustunga chiqardi).
  Asosiy kontent `max-w-3xl` ichida bo'lgani uchun 4–5 ustun hech qachon sig'masdi: 3 ustunli to'rlar endi `lg` dan,
  payoff va sheriklik formalari 2 ustun; `Stat` qiymati sig'masa qatorga o'tadi.
- **Payoff grafigi:** o'q yorliqlari «4,000,000» → «4 000 000», legenda chiziqlar ustidan tepaga ko'chdi; jadvalda
  sana bo'linmaydi.
- **Hisobot fayl nomlari** UTC vaqtida edi (20:03 da yaratilgan fayl `…-150315`) — endi Toshkent vaqtida
  (`commands::file_stamp`, test bilan).
- `spec/content/content_schema.json` (mobildan) CRLF bilan kelgan — formatlandi.
- E2E skeletida 2 eskirgan selektor («PIN ni o'rnatish», daromad oynasi/ulush taklifi) tuzatildi.

**Ma'lum cheklovlar (foydalanuvchiga)**

- Kod imzosi yo'q (SmartScreen); avtomatik yangilash yo'q.
- Boblar matni va diniy matnlar — placeholder (litsenziya va ulamo tekshiruvi).
- PIN unutilsa yoki `keys.bin` yo'qolsa — ma'lumotni tiklab bo'lmaydi.
- Avto-qulflash Win+L va uyquni sezmaydi (faqat oyna fokusi va vaqt).
- `.baraka` fayl yo'li qo'lda kiritiladi (fayl tanlash dialogi yo'q).
- Qal'a devori taqsimotni hisoblaydi, zaxiraga o'tkazma tugmasi yo'q.
- Toifa o'zgarishi oldin yozilgan xarajatlarga ta'sir qilmaydi.
- Haqiqiy 150/200 % DPI va High Contrast rejimi qo'lda sinalmagan (tizim sozlamasi).
- `%LOCALAPPDATA%/Baraka Daftari/export-bindings.exe` — 2026-10-12 dagi eski o'rnatishdan qolgan fayl;
  uninstaller uni o'chirmaydi, qo'lda o'chirish mumkin.

### D16 — 7-qonun: «Ko'rmagan ishingga pul tikma — pulingni hunaringga ishlat» (2026-10-20)

Manba: 7-qism (Rustam — chet eldan qaytgan vatandosh, «Plyus» piramidasi, Sobir hojining besh xavf belgisi va qal'a
devori). Spetsifikatsiya mobil jamoadan ko'chirildi: `docs/SPEC.md` v0.9 (2G), `docs/DESKTOP_PROMPT.md` v1.3
(1.1 jadval 7-qator, 5-bo'lim 4 vektor, 9-bo'lim D16), `docs/MVP_PLAN.md` (14B). Sxema **v18**.

**Umumiy vektorlar (avval vektor, keyin kod):** `scam_signals` (8), `promised_return` (5), `pyramid_levels` (4),
`lump_sum_split` (4) — mobil fayllari bitma-bit, `SHA256SUMS` ga qo'shildi, runner `crates/vectors/tests/scam_vectors.rs`.

**Domen**

- `domain::offer_check` qayta yozildi: 9 savol `HA | YO'Q | BILMAYMAN` (`Answer`, `Question`), 2E.5 bayroqlari
  (har «bilmayman» — qaysi savol ekani bilan sariq), **besh xavf belgisi** (`ScamSign`, tartib qat'iy), daraja
  (`NONE | CAUTION | FLEE` — «bittasini ko'rsang hushyor tort, ikkitasini ko'rsang qoch»), umumiy baho = eng og'iri,
  toifalar `RIBO | GHARAR | QIMOR`. Avvalgi «uch sariq — qizil» qoidasi umumiy vektorga (sc-007) zid edi — olib tashlandi.
- `domain::scam_math`: `promised_return` (oylik bp → oddiy va murakkab yillik ko'paytma, `checked` arifmetika, 24 oygacha),
  `pyramid_levels` (k, aholi → qavatlar, oxirgi qavat ulushi), `lump_sum_split` (avval zaxira kamomadi).
- `DomainError`: `ADVISOR_REQUIRED`, `COOLING_PERIOD`, `OFFER_ALREADY_DECIDED`, `RESERVE_ESTIMATE_REQUIRED`.

**Saqlash va xizmat**

- `offer_checks` (javoblar JSON, baho, daraja, belgilar, toifalar, summa, va'da bp, maslahatchi, qaror, vaqtlar);
  `OfferCheckRepo`. Tekshiruv endi **saqlanadi** va `OFFER_CHECKED` hodisasini beradi (7-bob vazifasi).
- `scam` xizmati: `check_offer`, `list_offers`, **«to'xta, maslahatlash»** `decide_offer` (`ACCEPTED` faqat maslahatchi
  ismi bor va tekshiruvdan 24 soat o'tgan bo'lsa; `DECLINED`/`POSTPONED` darhol; qaror bir marta), `promised`,
  `pyramid`, **«qal'a devori»** `plan_lump_sum` (valyuta + qo'lda kurs → so'm; 6 oylik maqsad xarajat tarixidan,
  tarix bo'lmasa taxminiy oylik zarur xarajat × 6; `EMERGENCY_TARGET_SET`), hunar shablonlari (temirchilik/payvand,
  tikuvchilik, ta'mir — CAPEX nomlari, summasiz).
- Buyruqlar: `check_offer` (yangi imzo), `list_offer_checks`, `decide_offer`, `promised_return`, `pyramid_model`,
  `plan_lump_sum`, `list_hustle_templates`.
- Kontent: `spec/content/chapters.json` mobil bilan bitta fayl — 6-bob («Sheriklik odobi») va 7-bob («Qopqon va hunar»)
  qo'shildi; `ACCOUNT_REVIEW_COMPLETED` (ko'rikda hamma tomon belgilagach) va `FAMILY_AGREEMENT_CREATED` triggerlari
  endi desktopda ham ishlaydi.

**UI**

- Taklif tekshiruvi kartasi (Sheriklik sahifasi): nom, summa, «va'da: oyiga %», maslahatchi; 9 savol radio
  (ha/yo'q/bilmayman); natija — baho, «besh belgidan n tasi», toifalar, belgilar izohi, bayroqlar, **«oyiga 35 % —
  yiliga 5,2 / 36,6 barobar»** (faqat ogohlantirish), «o'z ko'zim bilan ko'raman» ro'yxati, «To'xta, maslahatlash»
  bloki (rad / keyinga / pul qo'yaman — maslahatchisiz va 24 soatgacha o'chiq, sabab matni bilan), tekshiruvlar tarixi.
- «Piramida — qaysi qavatda bo'lasiz?» kartasi (k, aholi → qavatlar, pastki qavat ulushi, «baliqchining yemi»).
- «Qal'a devori» kartasi («Kelajagim» sahifasi): summa, valyuta, kurs, kerak bo'lsa taxminiy oylik xarajat;
  taqsimot va holat matni. Qorovulga o'tkazma — keyingi qadam (OPEN_QUESTIONS).
- «Hunardan ishga»: hunar shabloni tanlovi — CAPEX qatorlari nomlari, «talab bormi?» savoli, nom avto-to'ldiriladi.

Testlar: Rust (domen 6 + `scam` xizmati 4 + 4 vektor suite + sxema v18 ×3 + kontent 7 bob), vitest 93
(yangi `offer.test.tsx`: «Plyus» oqimi, 24 soatdan keyin qabul, piramida + shablon).

**GUI sinovi (toza dev profil `baraka-dev-profile2`, haqiqiy oyna, 2026-10-20):** «Plyus» — Baxtiyor, 10 000 000,
oyiga 35 %, javoblar kafolat ha / zarar yo'q / mol bilmayman / yangi odam ha / shoshirish ha / shartnoma ha /
chiqish bilmayman / ruxsat bilmayman / ko'rmadim → **Qizil, 4 belgi, ribo · g'arar · qimor, 5,2 / 36,6 barobar**;
«pul qo'yaman» maslahatchisiz o'chiq, ism yozilgach «yana 24 soat»; «Rad etdim» → qaror satri va tarix. Piramida
5 × 1 000 000 → 10 qavat, pastda 511 719 (51,2 %). «Hunardan ishga» shablon → nom, 6 qator, «talab bormi?».
Qal'a devori: 18 000 $ × 12 500 → 225 000 000; tarix yo'q → taxmin 3 000 000 so'raldi → 18 000 000 zaxiraga,
207 000 000 hunarga, «devor to'ldi».

**Sinovda topilgan va tuzatilgan**

- Har «bilmayman» bayrog'i bir xil matn bilan chiqardi — endi savol nomi bilan (mobildagi kabi).
- Qal'a devori ko'rsatkichlari 4 ustunda bir-biriga kirib ketardi — 2 ustun.
- **Eski dev profil ochilmay qoldi** («Qurilma kaliti topilmadi yoki bu daftarga mos emas»): qurilma kaliti
  Credential Manager'da bitta nom bilan saqlanar, boshqa (bo'sh) profilni sozlash uni ustiga yozgan. Tuzatish:
  `BARAKA_DATA_DIR` profillari uchun papka yo'lidan hosil qilingan alohida keyring nomi (`device_key_store`);
  standart profil nomi o'zgarmadi. Sinov yangi profilda qaytadan o'tkazildi (OPEN_QUESTIONS).

### D11+ — Oila kengashi rejimi: «Buni qarzsiz qanday o'tkazamiz?» (2026-10-17)

2-toifa birinchi bandi. Avvalgi «muhokama o'tkazildi» tugmasi (bitta belgi) o'rniga to'liq ekranli kengash sessiyasi
(DESKTOP_PROMPT 7-bo'lim «Oila kengashi rejimi» uslubi, D6 havas chegarasidagi rozilik qoidasi bilan). Sxema **v17**.

**Qo'shildi**

- `ceremony_discussions` (marosim, tanlangan stsenariy, qaror matni ≥ 20 belgi, boshlangan/yakunlangan vaqt) va
  `ceremony_discussion_consents` (a'zo, vaqt; `UNIQUE`). Repo `DiscussionRepo`. Oxirgi muhokama amal qiladi;
  yangi qaror — roziliklar qaytadan (havas chegarasidagi kabi).
- Xizmat: `start_discussion` (qisqa matn → `DISCUSSION_NOTE_REQUIRED`), `consent_discussion` (faqat `ADULT`,
  o'z PIN'i, noto'g'ri urinish kutish qoidasiga kiradi; **hamma katta rozi bo'lgach** `completed_at` va
  `ceremonies.family_discussed = 1` — shundan keyingina qarzli stsenariy tasdiqlanadi), `minutes_pdf`.
- Bayonnoma PDF (`crates/pdf/src/discussion.rs`, `DiscussionMinutes`, snapshot `discussion-minutes.pdf`):
  stsenariylar taqqoslash jadvali, qaror, kattalar roziligi.
- Buyruqlar: `start_ceremony_discussion`, `consent_ceremony_discussion`, `create_ceremony_minutes_pdf`
  (`discuss_ceremony` olib tashlandi). DTO: `CeremonyDto.discussion` (`DiscussionDto`: stsenariy, qaror, sanalar,
  `adults: AdultConsentDto[]`, `complete`).
- UI: `CeremonyCouncilPage` — 3 qadam: 1) taqqoslash jadvali + stsenariy + qaror matni (hisoblagich «n / kamida
  20»); 2) har katta uchun PIN maydoni, «Rozi: n / m», noto'g'ri PIN xabari, maydon har urinishdan keyin
  tozalanadi; 3) yakun + «Bayonnoma PDF». Kartada «Kengash qarori (stsenariy, rozi n / m) — matn» satri va
  «Oila kengashi: qarzsiz muhokama» / «…davom ettirish» tugmasi. `Esc` yopadi.

**Qarorlar**

- Muhokama = qaror matni + barcha katta a'zolarning PIN roziligi (bitta kattali xonadonda — o'zi). Rozilik
  bermagan katta bo'lsa marosim tasdiqlanmaydi; PIN'siz katta avval Xarajatlar → Oila kengashida PIN o'rnatadi.
- Bayonnoma D4 kengash bayonnomasidan alohida hujjat (`kengash-marosim-*.pdf`), chunki mavzu va tuzilma boshqa.

Testlar: Rust (xizmat: qisqa qaror rad, muhokamasiz rozilik yo'q, noto'g'ri PIN, 1/2 → 2/2 yakun, PDF, tasdiq,
tasdiqlangan marosimda yangi muhokama yo'q; sxema v17 ×3; PDF 2), vitest 91 (kengash oqimi to'liq).

**GUI sinovi (toza dev profil, haqiqiy oyna, 2026-10-17):** «Qizimizning to'yi» → stsenariy «Katta» (3 kun, 200
kishi: osh 200 × 45 000 jamg'arma, sarpo 8 000 000 qarz) → «Sanani tasdiqlash» rad («Qarzli reja uchun avval oilaviy
muhokama o'tkaziladi») → «Oila kengashi: qarzsiz muhokama»: taqqoslash jadvali, qaror 59 belgi (tugma 20 dan keyin
faollashdi), 2-qadam: noto'g'ri PIN rad, to'g'ri a'zo PIN'i → «Rozi: 1 / 1», «Hamma katta rozi»; 3-qadam:
bayonnoma PDF (`reports/kengash-marosim-*.pdf`, mazmuni tekshirildi) → «Yakunlash» → kartada «Kengash qarori
(Katta, rozi 1 / 1) — …», «Muhokama o'tkazilgan ✓» → «Sanani tasdiqlash» → «Marosim tasdiqlangan». Eslatma:
WebView2 mutatsiyadan keyin 1–2 s qora kadr beradi (skrinshot vaqtidagi repaint, funksional xato emas).

### D10+ qoldiqlari — DebtContributor, yopish strategiyasi, sotiladigan buyumlar, ongli chetlab o'tish, chek rasmlari (2026-10-16)

Bitta sessiyada D10–D13 dan qolgan 1-toifa (koddan hal bo'ladigan) bandlar yopildi. Sxema **v16**.

**Qarzlar (D10)**

- **`DebtContributor`** (SPEC 2D.6): to'lovda «Kim to'ladi (oila a'zosi)» tanlanadi (`loan_payments.contributor_member_id`), qarz kartasida «Hissalar: a'zo — summa» yig'indisi ko'rinadi. A'zo xonadoni tekshiriladi; bo'sh — umumiy.
- **Yopish tartibi** (`PayoffStrategy`: `SNOWBALL` — eng kichik qoldiq avval, `AVALANCHE` — ustamali qarz avval). Hisob Rustda: `domain::loans::payoff_order` — oylik simulyatsiya, qo'shimcha summa fokus qarzga, yopilgan qarzning to'lovi keyingisiga qo'shiladi (rollover). Qo'shimcha summa = 70/20/10 «qarz» ulushi − joriy oylik yuk (≥ 0). Karta: strategiya tanlovi (saqlanadi, `settings.payoff_strategy`), har qarz uchun yopilish oyi va sanasi, prognoz qarzsiz kun, boshqa strategiyadagi muddat. **Taklif vektori** `spec/test-vectors/proposed/payoff_strategy.json` (3 holat, `PROPOSED`).
- **Tiklash rejimining avtomatik qaytishi:** oxirgi olingan qarz to'liq yopilganda `DEBT_RECOVERY` → `STANDARD` (Rustda, `pay` ichida), sahifada tabrik xabari («bo'shagan to'lovni Kelajagimga yo'naltiring»).
- **Sotiladigan buyumlar** (SPEC 2D.7): ro'yxat, taxminiy qiymat, izoh, «Sotildi» belgisi, o'chirish; taxminiy jami qarz qoldig'i yonida.
- Payoff rejalashtiruvchisi **mavjud qarzdan to'ldiriladi** (qoldiq va to'lovlar soni).

**Sheriklik (D12/D8)**

- **«Ongli chetlab o'tish»** (OPEN_QUESTIONS 8-bo'lim qarori): darvoza yopiq bo'lsa kapital egasi sifatida sheriklik yaratish uchun sabab (kamida 20 belgi) + katta a'zo PIN'i talab qilinadi; yozuv `gate_overrides` da, kartada «Darvoza ongli chetlab o'tilgan: sabab» ko'rinadi. Noto'g'ri PIN — kutish qoidasi bilan. Darvozaning o'zi ochilmaydi. Xato kodlari: `OVERRIDE_REASON_REQUIRED`.

**Kassa daftari (D13)**

- **Chek rasmlari:** har jurnal yozuviga rasm biriktiriladi (`venture_attachments`, data-URL, ≤ ~2 MB), yozuv qatorida miniatyura. Faqat `data:image/` qabul qilinadi (`ATTACHMENT_INVALID`).

**Yangi buyruqlar:** `set_payoff_strategy`, `add_sellable_item`, `mark_sellable_sold`, `remove_sellable_item`, `attach_receipt` (build.rs + capabilities). DTO: `LoanDto.contributions`, `LoansDto.payoff/sellable/recoveryModeReset`, `LoanPaymentInputDto.contributorId`, `PartnershipInputDto.gateOverride`, `PartnershipDto.gateOverrideReason`, `VentureDto.attachments`.

**GUI sinovi (toza dev profil, haqiqiy oyna, 2026-10-16):** ikki qarz (1 200 000 / 5 000 000 ustamali) → qor to'pi: Dilshod fokus, 11 oy; ko'chki: Bank fokus; sotiladigan buyum qo'shildi → «Sotildi»; a'zo «O'zim» bilan to'lov → «Hissalar: O'zim 100 000»; hamma qarz yopildi → tabrik xabari, rejim STANDARD; rejalashtiruvchi Bank qarzidan to'ldirildi; darvoza yopiq — kapital egasi: noto'g'ri PIN rad, to'g'ri PIN bilan yaratildi, kartada sabab; «Non sexi» 9/9 + 3 imzo → SIGNED; kassa daftarida kirim/xarajat, ikkala yozuvga chek PNG biriktirildi (fayl dialogi), miniatyura.

**Sinovda topilgan va tuzatilgan**

- Faol strategiya tugmasi ajralib ko'rinmasdi (`border-border` va `border-accent` sinflari to'qnashuvi) — `aria-checked:` variantlari bilan.
- Oxirgi qarz yopilganda «Qarz tiklash rejimi» kartasi eski holatni (yoqilgan) ko'rsatardi — `recovery` keshi bekor qilinadi.
- `sr-only` fayl maydoni fokusda butun oynani surib yuborardi (WebView2) — maydon yorliq ustida ko'rinmas qatlam qilindi.

**Qoldi (2-toifa, keyingi sessiyalar):** D11 kengash muhokamasi rejimi (mahsulot qarori kerak), E2E muhit, fayl dialogi (9-band), sertifikat, mobil bilan vektor kelishuvi (`proposed/`).

Testlar: Rust 351 (shundan `payoff_strategy_taklif_vektorlari`), vitest 90 (yangi: strategiya almashtirish, sotiladigan buyum, hissador + tiklash xabari, chetlab o'tish formasi va karta satri, chek biriktirish).

### GUI sinovi D10–D15 va tuzatishlar (2026-10-16)

**Sinov tartibi.** `BARAKA_DATA_DIR` (yangi, faqat dev/sinov) bilan toza profil: `C:/Temp/claude/baraka-dev-profile`; test PIN `src-tauri/dev-test-pin.example` da. Haqiqiy Tauri oynasida (computer-use) quyidagilar bosib tekshirildi:

- Onboarding 5 qadam → «Boshlash»; daromad 3 000 000 + «Kelajagim» ulushi.
- **D10** Qarzlar: 70/20/10 (2,1 / 0,6 / 0,3 mln), jamg'arma 0 → «kamida 1 %» rad, rejim saqlandi; payoff 3 900 000 / 24 % / 14 oy / +160 000 → qarzsiz kun 2027-07-16, 6 oy erta, tejalgan 213 048,92, **ECharts grafigi chizildi** (patch ishlaydi), jadval.
- **D11** Marosimlar: marosim, 2 stsenariy, qatorlar (jamg'arma/qarz), taqqoslash («qarzni to'lash muddati 14 oy»), muhokamasiz tasdiq o'tmadi → muhokama → tasdiqlandi, smeta PDF, maqsad.
- **D12** Sheriklik: darvoza yopiq — kapital egasi rad; mehnat egasi → usta 9/9 (hamma savol), 3 imzo (canvas); «Imzolashni yakunlash» → «Oilaviy rozilik kerak» rad; rozilik «Nodira» → SIGNED; buyout jadvali 3 × 1 000 000.
- **D13** Kassa daftari: kirim 6 000 000, xarajat 2 500 000, davr yopildi → Anvar 2 100 000 (buyout ayirmasi 1 000 000), Dilshod 1 400 000; jurnal 5 yozuv zanjir to'g'ri; buyout 1-bo'lak ✓ (66,6 %); davr hisoboti PDF; «Hunardan ishga» hisob; detektor → qizil.
- **D13A** Hodisa (band bilan) → yopildi; ko'rik sessiyasi (to'liq ekran): rozi / e'tiroz izoh bilan, bayonnoma PDF; nizo → «taqsimot bloklangan», hakam papkasi PDF (30 KB), qaror + yangi versiya (11); markaz jadvali; oilaviy shablon → a'zo PIN (Oila kengashi) → tasdiq → SIGNED; «o'zgarishsiz tasdiqlash» → 3-versiya.
- **D14** Sozlamalar: eksport (43 jadval, 46 qator), import — noto'g'ri parol aniq xabar, ko'rik 0/0/0, qo'llandi.

**Topilgan va tuzatilgan**

- Sheriklik kartasi kelishuv ustasidagi o'zgarishdan keyin yangilanmasdi («Tomonlar hali kiritilmagan», 1-versiya) — `useApplyAgreement` endi `partnerships` keshini ham bekor qiladi.
- Yangi ko'rik ochilganda sessiya avtomatik ochilmasdi («latest» identifikatori) — tuzatildi.
- Kosmetika: payoff ko'rsatkichlari va hodisa/ledger formalari tor oynada 4–5 ustun o'rniga 2 ustun (`xl` da avvalgidek).
- NSIS: `displayLanguageSelector: true` bo'lsa `/S` (silent) o'rnatish ham «Installer Language» dialogini ko'rsatadi va to'xtab qoladi — selektor o'chirildi (NSIS tizim tilini o'zi tanlaydi: uz/ru/en).
- Xonadon qoidasi (D14) ilova ichida: bo'sh «urug'» daftar kiruvchi xonadonga bo'shatiladi, yozuvli daftar — `household_mismatch` bilan to'xtaydi (OPEN_QUESTIONS 15 hal qilindi).

**O'rnatuvchi sinovi:** 2026-10-16 — `/S` jim o'rnatish exit 0 → `%LOCALAPPDATA%/Baraka Daftari` (reestr Uninstall 0.1.0), `uninstall.exe /S` exit 0, qayta o'rnatish exit 0. O'rnatilgan exe toza profil (`BARAKA_DATA_DIR`) bilan ishga tushdi: **sovuq start 216 ms** (jarayon → asosiy oyna dastagi). O'rnatilgan ilova oynasiga computer-use ruxsati foydalanuvchi tomonidan rad etilgani uchun release oynasida tugmalar bosilmadi (dev build'da bosilgan); bu qadam foydalanuvchi uchun RELEASE_CHECKLIST 3-bo'limda qoldi. Eslatma: `%LOCALAPPDATA%/Baraka Daftari/export-bindings.exe` — 2026-10-12 dagi eski o'rnatishdan qolgan fayl (yangi o'rnatuvchida yo'q; uninstaller faqat o'zi o'rnatgan fayllarni o'chiradi) — qo'lda o'chirish mumkin.

### D15 — Reliz tayyorgarligi (2026-10-15)

**Qo'shildi**

- **Onboarding** (≤ 5 qadam): «Xush kelibsiz» (disklеymer), «Avval daromad», «Kelajagim ulushi», «Xarajat va havas», «Xavfsizlik va telefon» — har qadamda bo'limga o'tish, «O'tkazib yuborish», Esc; holat `localStorage` (`baraka.onboarding`, UI afzalligi). Testlarda standart holda o'tilgan deb olinadi.
- **Accessibility**: «Asosiy mazmunga o'tish» skip-link (`#main`), `forced-colors` (Windows High Contrast — tizim ranglari, ko'rinadigan chegara va fokus), `prefers-reduced-motion`, `prefers-contrast: more` (kuchliroq chegara/matn tokenlari); o'lchamlar rem'da (DPI 125–200 %).
- **E2E skeleti**: `e2e/anvar.e2e.ts` (WebdriverIO + `tauri-driver`, accessible-name selektorlari) va `e2e/README.md` (tayyorgarlik, ssenariy 10 bosqich, sovuq startni o'lchash). Ishga tushirilmagan — muhit yo'q (`OPEN_QUESTIONS` 18).
- `docs/RELEASE_CHECKLIST.md` — 7-bo'lim: D11–D15 qo'lda sinov bandlari, sovuq start, E2E, kod imzolash (to'xtab turibdi).
- Testlar: UI 2 (5 qadam + saqlash; bo'limga o'tish, Esc, skip-link).

**Build**

- `pnpm build` (NSIS, x64): muvaffaqiyatli, 2026-10-15 23:53 — `C:/Users/comp_2.1/.cargo-targets/baraka-daftari/release/bundle/nsis/Baraka Daftari_0.1.0_x64-setup.exe` (16,93 MiB), D15 kodidan; imzolanmagan. Foydalanuvchi uni haqiqiy Windows'da o'rnatib, RELEASE_CHECKLIST 3 va 7-bo'limlarni o'tishi kerak.

**To'xtab turgan (tashqi shart)**

- Kod imzolash sertifikati yo'q → o'rnatuvchi imzolanmagan (SmartScreen ogohlantirishi), imzolangan updater manifesti yo'q (`OPEN_QUESTIONS` 17).
- Sovuq start o'lchovi va E2E — faqat haqiqiy mashinada; ro'yxatda bo'sh joy qoldirildi.
- GUI sinovi (D10–D15) — dev bazaning test PIN'i sessiyada tiklanmagani uchun o'tkazilmadi; foydalanuvchi PIN'ni bergach yoki bazani zaxiralab qayta boshlagach har bo'lim bosib tekshiriladi.

### D14 — `.baraka` eksport/import (telefon ↔ desktop) (2026-10-15)

**Qo'shildi**

- `spec/interchange/export-format.schema.json` (JSON Schema 2020-12) va `README.md` — konteyner tartibi, birlashtirish qoidalari; mobil bilan umumiy.
- `security::container` — `seal_container` / `open_container`: Argon2id(parol, tuz) → XChaCha20-Poly1305, sarlavha AAD; `WRONG_PASSWORD`, `CORRUPT_CONTAINER`, `WEAK_PASSWORD` (≥ 8 belgi) xatolari.
- `storage::interchange` — umumiy (jadvalga bog'lanmagan) JSON eksport (to'liq yoki `since` bo'yicha inkremental) va import: `id` bo'yicha moslash, `version` kattasi / `updated_at` kechrog'i yutadi, tombstone oddiy maydon; **jurnal**: kiruvchi zanjir qayta hisoblanadi (`verify_chain`) va mahalliy bilan solishtiriladi (`check_import`) — fork bo'lsa import butunlay to'xtaydi, faqat davomi qo'shiladi; yopilgan davrlar va imzolar faqat qo'shiladi; imzolangan kelishuvning shu versiyasi o'zgarmaydi. Dry-run (tranzaksiya + rollback) → ko'rik.
- Xizmat `src-tauri/src/sync.rs` va 3 command: `export_baraka` (ilova papkasi `exports/` yoki berilgan yo'l), `preview_baraka_import`, `apply_baraka_import`. `ApiError` ga parol/konteyner kodlari.
- UI: Sozlamalar → **Telefon bilan almashish** kartasi — eksport (yo'l, parol, «shu sanadan keyin»), import ko'rigi (qo'shiladi/yangilanadi, jurnal, ziddiyatlar, forklar) → tasdiqlab qo'llash; fork bo'lsa qo'llash tugmasi yo'q.
- Testlar: security 2, storage 3 (round-trip 1:1 barcha jadvallar + xeshlar qayta hisoblanadi + idempotent; fork va buzilgan zanjir; versiya/ziddiyat/inkremental), Tauri 1 (fayl → yangi baza, noto'g'ri parol), UI 3.

**Qarorlar**

- Fayl tanlash dialogi yo'q (ADR: dialog plugin yoqilmagan) — yo'l matn maydonida; standart — ilova papkasi.
- `schemars` qo'shilmadi: sxema qo'lda yozildi, kod formatni (`format`, `schemaVersion`) tekshiradi.
- Xonadon identifikatori ikkala qurilmada bir xil deb olinadi (birinchi qurilma eksportidan ikkinchisi boshlanadi) — `OPEN_QUESTIONS` ga yozildi.
- GUI sinovi — D10 dagi sabab (PIN) tufayli kutilmoqda.

### D13A — Kelishuvlar markazi: vazifalar, ko'rik, «katta foyda», nizo va hakam, oilaviy kelishuvlar (2026-10-15)

**Qo'shildi**

- Sxema v15: `duty_incidents`, `reviews` + `review_marks`, `disputes`, `family_consents`, `version_notes`. Repo `crates/storage/src/center.rs`.
- Xizmat (`src-tauri/src/center.rs`) va 14 command: `get_agreements_center`, `get_agreement_ops`, `report_duty_incident`, `resolve_duty_incident`, `open_review`, `mark_review`, `create_review_pdf`, `open_dispute`, `decide_dispute`, `create_arbiter_pdf`, `confirm_unchanged`, `list_family_templates`, `create_family_agreement`, `confirm_family`.
- **Markaz jadvali** (TanStack Table): turi, holati, keyingi ko'rik (30 kun eslatma — `review_reminder_due`), ochiq hodisalar, nizolar, zanjir / oilaviy tasdiq; qidiruv va tur/holat filtri. Eski oddiy ro'yxat o'rniga.
- **`DutyIncident`**: «bajara olmayapman» — vazifa, sabab, taklif; tegishli «bajarilmasa» bandi darhol ko'rsatiladi; yopish («qoidaga qaytildi»).
- **Oylik ochiq hisob ko'rigi**: to'liq ekran sessiya (`role="dialog"`) — davr yozuvlari, yakun (turlar bo'yicha), ochiq hodisalar, `verify_chain` natijasi va zanjir boshi; har tomon `AGREE` / `OBJECT + izoh` (e'tirozda izoh majburiy); **bayonnoma PDF** (`ReviewMinutes`, `chain_head` bilan) + snapshot.
- **Nizo**: `IN_DISPUTE` (taqsimot bloklanadi — `ensure_distribution_allowed`, D13 `close_period`), **hakam uchun ish papkasi PDF** (`ArbiterFolder`: mundarija `#outline`, sahifa raqamlari, bo'limlar — versiya, versiyalar tarixi, yozuvlar + zanjir, bayonnomalar, hodisalar, talablar) + snapshot; hakam qarori → `SIGNED`, ixtiyoriy yangi versiya (qayta imzolash).
- **Yillik yangilash**: «o'zgarishsiz tasdiqlash» — yangi versiya + `version_notes` yozuvi; markazda va ustada eslatma.
- **Oilaviy kelishuvlar**: 4 shablon (uy ishlari, pul va hisob, havas chegarasi, oila kengashi) → `FAMILY` kelishuvi (tomonlar — ADULT a'zolar, vazifalar shablondan, 4/5/7 «tegishli emas»); imzo o'rniga **ADULT PIN tasdig'i** (lockout bilan, `family.rs` mantig'i); hamma kattalar tasdiqlagach — `SIGNED`.
- `ProfitSpikeAlert` — D13 da (`venture.spike`, `profit_spike.json` yashil).
- Testlar: Tauri 3 (hodisa+ko'rik+bayonnoma; nizo+blok+papka+qaror+yangilash; oilaviy shablon+PIN), PDF 2 (snapshot), UI 3; mavjud testlar markaz jadvaliga moslandi.

**Qarorlar**

- Ko'rik sessiyasi — ustaning ichida (to'liq ekran dialog), alohida sahifa emas.
- «O'zgartirilgan yozuv `chain_head` bilan aniqlanadi» — bayonnomada `chain_head` saqlanadi; DB triggerlari yozuvni o'zgartirishga yo'l qo'ymaydi, import (D14) da `verify_chain` solishtiradi.
- GUI sinovi — D10 dagi sabab (PIN) tufayli kutilmoqda.

### D13 — Venture ledger, taqsimot, «Hunardan ishga», taklif detektori (2026-10-15)

**Qo'shildi**

- Domen: `JournalKind` kengaytirildi — `VENTURE_INCOME`, `VENTURE_EXPENSE`, `FORCE_MAJEURE`, `LOSS_DISTRIBUTION`, `BUYOUT_PAYMENT` (zanjir algoritmi o'zgarmadi; `journal_chain.json` yashil). `venture.rs`: `net_of`, `payback_months`, `hustle_scenarios` (pessimistik 70/120 %, o'rtacha, optimistik 130/90 % — bp'da). Xato `PERIOD_CLOSED`.
- Sxema v14: `journal_entries` qayta qurildi (CHECK kengaytirish uchun; triggerlar qayta yaratildi), `venture_periods` (yopilgan davr: yakun, zanjir boshi, taqsimot JSON, fors-major izohi) — UPDATE/DELETE triggerlar bilan o'zgarmas.
- Xizmat (`src-tauri/src/ventures.rs`) va 6 command: `get_venture`, `add_venture_entry`, `close_venture_period`, `create_period_report_pdf`, `check_offer`, `hustle_plan`. Ledger yozuvlari D8A jurnali orqali (imzolangan kelishuv, hisob yurituvchi qurilma); yopilgan davrga yozib bo'lmaydi; davr yopilganda `partnership::distribute` (foyda ulush bo'yicha, zarar — mudarabada kapital egasida, musharakada kapitalga mutanosib), **buyout ayirmasi** (mehnat egasining ulushidan navbatdagi bo'lak, qoldiq bilan cheklangan) to'lov sifatida yoziladi, `IN_DISPUTE` da bloklanadi (`ensure_distribution_allowed`). «Katta foyda» belgisi ochiq davr uchun (`profit_spike_alert`, oxirgi 3 davr).
- Sherik uchun davr hisoboti PDF: `crates/pdf/src/period.rs` (`PeriodReport`, `render_period_report`, zanjir boshi bilan) + snapshot `period-report.pdf`.
- UI: Sheriklik kartasida **Kassa daftari** (imzolangan sheriklikda): yakun, yozuv formasi, davr yopish, yopilgan davrlar + taqsimot + PDF, «katta foyda» ogohlantirishi; **«Hunardan ishga»** kartasi (3 stsenariy jadvali, bir bosishda sheriklik qoralamasi); **«Kafolatlangan foyda» detektori** kartasi (6 savol → yashil/sariq/qizil, bayroq izohlari).
- Testlar: domen 2, Tauri 3 (yopish/taqsimot/o'zgarmaslik/PDF; zarar+fors-major+buyout ayirmasi; detektor+hunar), PDF 2, UI 3.

**Qarorlar**

- Chek rasmlari biriktirish — qo'shilmadi (baza SQLCipher bilan shifrlangan; fayl biriktirish D14 dan keyin). Fors-major — izoh majburiy.
- `LOSS_DISTRIBUTION` alohida tur (jurnal summasi doim musbat; yo'nalish turdan).
- GUI sinovi — D10 dagi sabab (PIN) tufayli kutilmoqda.

### D12 — Sheriklik domeni, shartnoma, buyout (2026-10-15)

**Qo'shildi**

- Domen (`partnership.rs`): `validate_structure` — `MUDARABA`da kapital faqat bir tomondan (+ kamida bitta mehnat tomoni), `MUSHARAKA`da kamida ikki tomon kapital; kafolatli summa har turda taqiq. `buyout_schedule` — kamayib boruvchi sheriklik jadvali (`allocate` bilan teng bo'laklar, qolgan ulush bp). Yangi xato kodlari: `FAMILY_CONSENT_REQUIRED`, `READINESS_GATE_LOCKED`, `PARTNERSHIP_STRUCTURE_INVALID`.
- Sxema v13: `partnerships` (kelishuvga 1:1 — tur, mening rolim, buyout shartlari, oilaviy rozilik), `partnership_buyout_payments`. Repo `crates/storage/src/partnerships.rs`.
- Xizmat (`src-tauri/src/partnerships.rs`) va 5 command: `get_partnerships`, `create_partnership`, `set_buyout`, `pay_buyout`, `consent_partnership`. Sheriklik = `Agreement(PARTNERSHIP)` (D8A ustasi) + sheriklik yozuvi; kapital = 2-savoldagi pul hissalari, ulush = 4-savol.
- **Darvoza (SPEC 2E.6):** kapital kirituvchi (`CAPITAL_PROVIDER`) faqat tayyorgarlik darvozasi `OPEN` bo'lsa yaratadi; mehnat egasi (`WORKER`) darvozaga bo'ysunmaydi, lekin imzolashdan oldin **oilaviy rozilik** (a'zo nomi) yoziladi. `agreements::sign` endi `partnerships::check_before_sign` ni chaqiradi: rozilik + tuzilma + kafolatli summa.
- Versiyalash D8A'da: javob o'zgarsa versiya oshadi, holat `DRAFT`, imzolar qayta so'raladi (mavjud test).
- UI: «Kelishuvlar» sahifasida **Sheriklik** kartasi — darvoza holati, sherikliklar (tomonlar, kapital, ulush), muammolar ro'yxati (kodlar matnga), rozilik formasi, buyout jadvali (progress + jadval + to'lov), «Shartnomani ochish» (D8A ustasi), yangi sheriklik formasi (rol izohi bilan).
- Testlar: domen 2, Tauri 3 (darvoza, rozilik/tuzilma/kafolat, buyout), UI 3; storage sxema 13.

**Qarorlar**

- Uskuna ro'yxati alohida jadval emas — 2-savoldagi `goods` hissalari (narxi bilan); buyout qiymati foydalanuvchi tomonidan kiritiladi.
- `dist-001…004` vektorlari D5 dan beri yashil (`crates/vectors`), D12 ularni qayta ishlatmaydi.
- GUI sinovi — D10 dagi sabab (PIN) tufayli kutilmoqda.

### D11 — Marosim rejalovchisi (2026-10-15)

**Qo'shildi**

- Sxema v12: `ceremonies` (tur, nom, sana, holat, oilaviy muhokama, tanlangan stsenariy, jamg'arma maqsadi), `ceremony_scenarios`, `ceremony_lines` (miqdor × birlik narxi, manba `SAVINGS | FAMILY | EXPECTED_GIFTS | DEBT`). Repo: `crates/storage/src/ceremonies.rs`.
- Xizmat (`src-tauri/src/ceremonies.rs`) va 9 command: `get_ceremonies`, `create_ceremony`, `add_ceremony_scenario`, `add_ceremony_line`, `remove_ceremony_line`, `discuss_ceremony`, `confirm_ceremony`, `set_ceremony_goal`, `create_ceremony_pdf`. Tasdiqlash domen `ceremony::confirm` orqali — qarz qatori bo'lsa muhokamasiz `CONFIRMED` bo'lmaydi (`FAMILY_DISCUSSION_REQUIRED`). Tasdiqlangan reja o'zgarmaydi (`AGREEMENT_LOCKED` kodi qayta ishlatildi).
- Stsenariylarni taqqoslash: umumiy narx, qarz qismi, **qarzni to'lash muddati** (qarz qismi ÷ 70/20/10 «qarz» ulushi — D10 `split_parts`), **muqobil** (shu pulga necha oylik zarur xarajat — D8 `monthly_essentials`).
- Smeta PDF: `crates/pdf/src/estimate.rs` (`CeremonyEstimate`, `render_estimate`) + snapshot `tests/snapshots/estimate.pdf`; fayl `reports/smeta-*.pdf`.
- UI: «Marosimlar» sahifasi (yon panelda yoqildi — endi barcha bo'limlar faol): taqqoslash jadvali, stsenariy bloklari (qatorlar, qo'shish/o'chirish, PDF), «Buni qarzsiz qanday o'tkazamiz?» bloki, tasdiqlash, to'yona o'rniga jamg'arma maqsadi, yangi marosim formasi; «El uch kun gapiradi…» matni.
- Testlar: Tauri 4 (taqqoslash, muhokamasiz tasdiq rad, qarzsiz darhol tasdiq + PDF, maqsad/o'chirish), storage sxema v12, PDF 2, UI 2.

**Qarorlar**

- «Oila kengashi rejimi» — alohida ekran emas: muhokama tugmasi + izoh (D4 kengash bayonnomasi bilan bog'lash keyingi bosqichga). **2026-10-17: to'liq ekranli sessiya va bayonnoma bilan almashtirildi (D11+).**
- «Qolgan ulushlar bo'yicha payoff D10 simulyatori bilan» — qarz qismi uchun oddiy bo'linma (foizsiz), chunki oilaviy qarz ustamasiz; ustamali qarz uchun foydalanuvchi D10 rejalashtiruvchisini qo'lda ishlatadi.
- `Goal` MVP'da virtual: nom + summa; ulashiladigan havola yo'q (SPEC shunday deydi).

**Ma'lum cheklovlar**

- GUI sinovi — D10 dagi sabab (PIN) tufayli kutilmoqda.

### D10 — Payoff rejalashtiruvchisi, 70/20/10, «Qarzsiz kun» (2026-10-15)

**Qo'shildi**

- Xizmat (`src-tauri/src/payoff.rs`): `simulate_payoff` — annuitet / differensial / qat'iy ustama, odatiy va tezlashtirilgan (qo'shimcha oylik to'lov) grafik, tejalgan ustama, qisqargan oylar, har ikkisi uchun «qarzsiz kun» (sanalar `add_months` bilan); `get_recovery` / `set_recovery` — `STANDARD | DEBT_RECOVERY` rejimi va ulushlar (`household_settings`), shu oy daromadi bo'yicha qismlar (`domain::recovery::recovery_split`).
- UI (Qarzlar sahifasi): **Payoff rejalashtiruvchisi** — forma, 4 ko'rsatkich, **ECharts** qoldiq grafigi (odatiy va tezlashtirilgan), **TanStack Table** jadvali; **Qarz tiklash rejimi** kartasi — qismlar, rejim tugmasi, ulushlar (%), saqlash.
- Testlar: Tauri 2 (amort-002 bilan bir xil raqamlar; jamg'arma 0 rad etiladi), UI 2.

**Qarorlar va sabablar**

- `echarts` 6 va `@tanstack/react-table` **8.x** qo'shildi (ADR 2-bo'limda nomlangan). TanStack Table 9 (hozirgi `latest`) boshqa API (`createCoreRowModel`); barqaror 8.21 tanlandi — CHANGELOG'da sabab, keyin ko'chirish mumkin.
- **ECharts 6 + `freezePrototype`**: `Scheduler.mockMethods` muzlatilgan `Object.prototype` tufayli `constructor`ga yoza olmay modul yuklanishda yiqildi (ilova bo'sh qora oyna). Xavfsizlik sozlamasi o'zgartirilmadi; `pnpm patch` bilan bir qatorli tuzatish (`patches/echarts@6.1.0.patch`, `pnpm-workspace.yaml` → `patchedDependencies`) — `constructor` o'tkazib yuboriladi. Faqat `lib/` va `dist/echarts.esm.js` patchlangan (biz `echarts/core` ishlatamiz).
- Qat'iy ustamada qo'shimcha to'lov muddatni qisqartirmaydi (ustama kelishilgan summa) — faqat odatiy jadval ko'rsatiladi.
- Jamg'arma ulushini 0 qilib bo'lmaydi — qoida Rustda (`SAVINGS_BELOW_MINIMUM`), UI faqat xabar ko'rsatadi.
- Stavka maydoni — foydalanuvchining mavjud qarzi tavsifi (chiqish uchun); «muqobil daromad» matni yo'q (ribo filtri testi o'tadi).

**Ma'lum cheklovlar**

- `DebtContributor` (oila a'zolarining qarzga hissasi), «sotiladigan buyumlar» ro'yxati, yopish tartibi strategiyasi (qor to'pi / ko'chki) va rejimning avtomatik qaytishi — qo'shilmadi.
- Simulyatsiya mavjud qarz yozuviga bog'lanmagan (qo'lda kiritiladi).
- **GUI sinovi o'tkazilmadi**: dev bazaning test PIN'i sessiyada tiklanmadi (baza papkasini zaxiralab qayta boshlashga ham ruxsat berilmadi). Avtomatik testlar (Rust + UI) yashil; haqiqiy oynada Qarzlar sahifasi (rejalashtiruvchi, grafik, 70/20/10) foydalanuvchi PIN'ni bergach yoki bazani zaxiralagach tekshiriladi.

### D9 — Qarzlar: reja, «to'xta va o'yla», qarzsiz kun, tilxat (2026-10-15)

**Qo'shildi**

- Sxema v11: `loans` (olingan/bergan, `counterparty_type`, `has_markup`, friction javoblari, `borrow_verdict`, `agreement_id`), `loan_installments`, `loan_payments`. Foiz maydoni yo'q — bergan qarzda tuzilmaning o'zi foizni ifodalay olmaydi (SPEC 2D.5). «Nasiya daftari» (D4, SHOP) o'z joyida qoldi.
- `domain::loans`: `add_months` (kun qisqaradi), `equal_plan` (teng bo'laklar, `allocate` — yig'indisi aynan asosiy summa), `debt_free_day`, `next_installment`; `borrow_check` chegaralari testlandi.
- Xizmat (`src-tauri/src/loans.rs`): ko'rinish (qoldiq, to'langan, keyingi/oxirgi to'lov, oylik yuk, daromad, qarzsiz kun), `check_borrow` (mavjud yuk + yangi qarz / shu oy daromadi → `OK | CAUTION | STOP`, saqlanmaydi), `add_loan` (reja majburiy; olingan qarzda natija yozuvda qoladi), `pay` (qoldiqdan oshmaydi), **`create_iou`** — D8A `LOAN` kelishuvi qoralamasi: tomonlar, hissa, jadval, hisob yurituvchi, chiqish, muddat oldindan to'ldirilgan; faqat hakam (8-savol) qoladi — usta 8/9 bilan ochiladi; qarzga bog'lanadi.
- UI «Qarzlar» (`DebtsPage.tsx`, nav ochildi): umumiy ko'rinish, olingan/bergan ro'yxatlar (to'lov formasi, «Tilxat yaratish / ochish» → D8A ustasi), yangi qarz formasi: friction bloki (zarurat, foizsiz muqobil, mavjud ustamali qarz belgisi), «Oylik yukni hisoblash» → natija va foiz; bergan qarzda «foiz maydoni yo'q» izohi.
- Amortizatsiyaning qolgan turlari: `differentiated_schedule`, `fixed_markup_schedule` (`domain::amortization`), **taklif vektori** `spec/test-vectors/proposed/amortization_extended.json` (`status: PROPOSED`, runner `proposed_vectors.rs`, `load_proposed_suite`). Asosiy qoplanish testi `proposed/` ni ko'rmaydi (qaror: «Vektorsiz formulalar uchun tartib»). `MANUAL` — foydalanuvchi rejasining o'zi (`RepaymentPlan::new`).
- Testlar: domen 7 (loans 5, amortizatsiya 2), Tauri xizmati 4, taklif vektorlari 1, UI 3 (`debts.test.tsx`).

**Qarorlar va sabablar**

- Oylik yuk = barcha ochiq olingan qarzlarning keyingi to'lovlari + yangi qarzning teng bo'lagi; daromad = shu oy daromadi. Daromad 0 bo'lsa — `STOP` (100 %).
- `STOP` taqiq emas (SPEC 2D.6): tugma o'chmaydi, natija qarz yozuvida ko'rinadi.
- Reja faqat teng bo'laklar (oylik): D10 payoff planner boshqa jadvallarni (annuitet, differensial, qat'iy ustama) simulyatsiya uchun ishlatadi; qarz yozuvining o'zi foizsiz.
- Tilxat = `Agreement(LOAN)` (DESKTOP_PROMPT D9); alohida PDF shabloni yo'q — D8A kelishuv PDF'i (snapshot bor).

**Ma'lum cheklovlar**

- Tilxat PDF'ida «guvohlar» bo'limi yo'q (D8A: guvoh imzosi UI'da yo'q).
- «Sotiladigan buyumlar» ro'yxati va `Goal` (maqsadli jamg'arma) — D10/D11.
- Haqiqiy narx va imkoniyat narxi (opportunity cost) hisobi — D10 bilan.

### D8A ustasi — 9 savol, imzolar, og'zaki kelishuv, kelishuv PDF, jurnal UI (2026-10-15)

**Qo'shildi**

- **Tauri qatlami** (`agreements.rs`, `agreement_commands.rs`): `list_agreements`, `create_agreement`, `get_agreement`, `save_agreement_answers` (versiya oshadi; `SIGNED` bo'lsa yana `DRAFT` — imzolar qayta so'raladi), `add_signature` (faqat 9/9 to'ldirilganda), `sign_agreement` (hamma tomon va hakam joriy versiyani imzolagan bo'lishi shart; `effective_from` o'tmishda bo'lishi mumkin; boshlang'ich balans — `OPENING_BALANCE` jurnal yozuvi), `append_journal_entry` (faqat `SIGNED`, faqat hisob yurituvchi qurilma), `get_journal` (zanjir tekshiruvi bilan), `create_agreement_pdf`.
- Javoblar `AgreementAnswersDto` (serde + specta) sifatida bazada JSON; domen `AgreementAnswers` ga aylantirilib `completeness` hisoblanadi — qoidalar bitta joyda (Rust).
- Sxema v10: `agreements.effective_from`, `signatures` (tomon/guvoh/hakam, versiya, PNG data URL; `UNIQUE(agreement, party, role, version)`).
- **PDF**: `crates/pdf/src/agreement.rs` — 9 bo'lim, imzolar jadvali, disklеymer; snapshot test `tests/snapshots/agreement.pdf`.
- **UI** (`ui/src/app/agreements/`): «Sheriklik» bo'limi ochildi — ro'yxat va qoralama yaratish; **9 qadamli usta** (`AgreementWizard.tsx`): chapda «N / 9» progress (✓ belgilar), o'rtada forma (`react-hook-form` + `zod`, `useFieldArray` — tomonlar, hissalar, vazifalar, ulushlar), o'ngda Sobir hoji maslahati va **jonli hujjat ko'rinishi**; «Imzolash» 9/9 bo'lmaguncha o'chiq; to'liqlik xatolari Rust kodlaridan tarjima qilinadi. **Imzo chizish** (`SignaturePad.tsx`, canvas, pointer events → PNG). Og'zaki kelishuv: amal qilish sanasi + boshlang'ich balans. **Jurnal kartasi**: yozuvlar, xesh, zanjir holati, yangi yozuv (faqat hisob yurituvchi qurilmada).
- Testlar: Tauri xizmati 2 (to'liq oqim + qayta imzolash), PDF snapshot 1, UI 3 (`agreements.test.tsx`: ro'yxat/yaratish, saqlash va 9/9 qulfi, imzo chizish).

**Qarorlar va sabablar**

- `react-hook-form`, `zod`, `@hookform/resolvers` qo'shildi (ADR 2-bo'limda nomlangan). zod faqat maydon shaklini tekshiradi; biznes qoidalari (ulushlar 100 %, hakam tomon emas, ...) Rustda — frontend qoida hisoblamaydi.
- `serde_json` `src-tauri` da endi oddiy bog'liqlik (ilgari faqat test): javoblar JSON sifatida saqlanadi.
- ESLint: `restrict-template-expressions` uchun `allowNumber: true` — RHF yo'llari (`parties.${index}.name`) raqamli indeks talab qiladi, `String()` tipni buzadi.
- Jonli ko'rinish — hujjat matnining HTML oynasi (PDF bilan bir xil ma'lumot), PDF'ning o'zi tugma bilan faylga yoziladi. WebView2 ichida PDF iframe'i CSP (`default-src 'self'`) ga zid; CSP bo'shashtirilmadi.
- Hisob yurituvchi qurilma = kelishuvni yaratgan qurilma (`origin_device_id`). SPEC'dagi `custody.keeper_device_id` D14 almashishda ulanadi.
- Vitest `testTimeout` 20 s: usta testlari parallel yuklanishda 5 s dan oshdi (yolg'iz o'tadi).

**GUI sinovi (haqiqiy oyna)**

- Qoralama → 9 savol to'ldirildi (tomonlar, hissalar, vazifa, ulushlar 5000+5000, zarar, hisob yuritish, chiqish, hakam, muddat) → «9 / 9» → uch imzo canvas'da chizildi → og'zaki kelishuv sanasi 2026-09-01 va boshlang'ich balans → `SIGNED`, jurnalda 1-yozuv va xesh, zanjir to'g'ri.
- Sana maydoni: kun segmentiga aniq bosish kerak (WebView2 `<input type=date>`); birinchi urinishda qiymat tushmadi — testda emas, UI'da cheklov yo'q.

**Ma'lum cheklovlar**

- «Chop etib qo'lda imzolash → skan biriktirish» rejimi yo'q (faqat canvas). Guvoh imzosi UI'da yo'q (backend `WITNESS` rolini qabul qiladi).
- Tray/mini oyna kabi, PDF faylga yoziladi; tizim chop etish dialogi (`Ctrl+P`) keyingi bosqich.
- `DutyIncident`, nizo, oylik ko'rik — D13A.

### D8 UI — Qorovul zaxirasi kartasi va «Narx daftari» (2026-10-15)

**Qo'shildi**

- **Kelajagim → «Qorovul pul»** kartasi (`ReserveCard.tsx`, `src-tauri/src/reserve.rs`): oylik `ZARUR + KERAK` o'rtachasi (so'nggi 12 oydan 3 ta ma'lumotli oy, joriy oy kirmaydi), 3 va 6 oylik maqsad (`domain::emergency`), «necha oylik zaxira bor» progressi (o'ndan bir oy, `1,4 / 6 oy`), tayyorgarlik darvozasi (`domain::readiness`) va sabablari. Ma'lumotli oy 3 tadan kam bo'lsa — tushuntirish, raqam emas.
- **«Narx daftari»** sahifasi (`PricesPage.tsx`, nav ochildi): mahsulot (bazaviy narx → joriy narx, xarajatdagi ulushi), har biri uchun o'zgarish (bp), shaxsiy indeks (`domain::inflation::personal_index`), **«Sichqon kemirgani»** — balansning bugungi narxlardagi real qiymati (`real_value`) va misol («avval N dona, hozir M dona»), keyingi qadam matni. Narxni yangilash (inline), o'chirish (mantiqiy).
- Sxema v9 `price_items`; `PriceRepo`; commandlar `get_reserve`, `get_prices`, `add_price_item`, `update_price`, `remove_price_item`.
- Testlar: domen (`real_value`, `units_affordable`), Tauri xizmati (2), UI (`prices.test.tsx`, 3).

**Qarorlar va sabablar**

- Darvozaning qarz sharti (foizli qarz / chiqish rejasi) D9 gacha «yo'q» deb olinadi (MVP_PLAN: stub). D9 da `borrow_check` va qarz ro'yxati ulanadi.
- Oylik o'rtacha = 3 oylik maqsad / 3: ikkala raqam bir xil uchta oydan, yaxlitlash mos.
- `PricesDto.example_units_*` — `u32`: specta `i64` ni TS'ga chiqarmaydi (BigInt taqiqi); birliklar soni manfiy bo'lmaydi.
- `PriceItem::create` 8 argumentdan `PriceDraft` tuzilmasiga o'tdi (clippy `too_many_arguments`, `#[allow]` yo'q).

**GUI sinovi (haqiqiy oyna)**

- Kelajagim: karta ko'rindi («hozir: 0» ma'lumotli oy, darvoza yopiq, sabab). Narx daftari: yozuv qo'shish → +62,5 %, real qiymat 2 461,54; narx yangilash → +100,0 %, 2 000; o'chirish.
- Topilgan va tuzatilgan nuqson: inline narx maydoni fokuslanmasdi — yozilgan matn yo'qolardi (`autoFocus`).

**Ma'lum cheklovlar**

- «Ongli chetlab o'tish» (qaror: bitta amal, sabab, ADULT PIN) hali UI'da yo'q — D9 qarz oqimi bilan birga.
- Misoldagi birliklar balans narxdan kichik bo'lsa «0 dona» chiqadi — to'g'ri, lekin matn boyitilishi mumkin.

### D7 qoldig'i — Tray, Ctrl+Alt+B mini oyna, CSV import ustasi (2026-10-15)

**Qo'shildi**

- **Tray ikonkasi** (`src-tauri/src/desktop.rs`): menyu — «Ochish», «Tez xarajat (Ctrl+Alt+B)», «Qulflash», «Chiqish»; ikki marta bosish asosiy oynani ochadi. Matnlar o'zbekcha (ilovaning asosiy tili); tray tilini almashtirish keyingi bosqichda.
- **`Ctrl+Alt+B`** (`tauri-plugin-global-shortcut`): «Tez xarajat» mini oynasi (`quick` yorlig'i, 440×420, doim ustida, taskbar'da yo'q). Yopish — yashirish; keyingi ochilish darhol. Qulf holatida oyna **summa va ro'yxat ko'rsatmaydi** — faqat «Daftar qulflangan» va «Asosiy oynani ochish» (`QuickWindow.tsx`, test bilan). Ochiq holatda: summa, kategoriya, izoh → `add_expense`; Escape — yashirish.
- Mini oynaning o'z capability fayli (`capabilities/quick-window.json`): faqat holat, kategoriyalar, xarajat qo'shish va ikki oyna buyrug'i (`show_main_window`, `hide_quick_window`).
- **CSV import ustasi** (`CsvImportWizard.tsx`, `src-tauri/src/csv_import.rs`): matn joylash → ustunlarni moslash (sana, summa, izoh; kategoriya; kirimlarni tashlash) → ko'rib chiqish (satr, sana, summa, holat) → import. Tahlil Rustda: ajratuvchi avtomatik (`;`, `,`, tab), qo'shtirnoqli maydonlar, sana `YYYY-MM-DD` / `DD.MM.YYYY` / `DD/MM/YYYY`, summa `money::parse_amount` (manfiy — chiqim), bugundan kech yoki 24 oydan eski sana — xato, 500 satrgacha. Xatoli satr bo'lsa **hech narsa yozilmaydi** (`CSV_HAS_ERRORS`); import bitta tranzaksiyada. Testlar: Rust 5 ta, UI 2 ta.
- Oyna yorlig'i (`window-label.ts`): `@tauri-apps/api/webviewWindow` orqali; Tauri tashqarisida «main».

**Qarorlar va sabablar**

- `tauri` `tray-icon` feature'i yoqildi; `tauri-plugin-global-shortcut = "2"` qo'shildi (ADR 7-bo'limda nomlangan). `cargo search` 3.0 alpha'ni ko'rsatadi — Tauri 2 uchun 2.x qatori.
- CSV import «Hafta varag'i»dan farqli: istalgan o'tgan sana (24 oygacha) — bank ko'chirmasi uchun. Shuning uchun alohida xizmat (`csv_import`), `add_expenses` qoidasi o'zgarmadi.
- Mini oyna alohida webview, o'sha frontend: yorliq bo'yicha `App` boshqa ekran ko'rsatadi. Qulf holati `get_security_status` bilan 5 soniyada tekshiriladi.
- Asosiy oynani yopish ilovani tugatadi (tray'ga yig'ilmaydi) — reliz checklist'idagi «fon jarayon qolmaydi» talabi.

**Ma'lum cheklovlar**

- **Tray menyusi qo'lda sinalmagan:** ikonka ko'rindi, lekin menyu bandlari (Ochish / Tez xarajat / Qulflash / Chiqish) avtomatlashtirilgan sinovda bosilmadi (taskbar ruxsati yo'q). Foydalanuvchi tekshirishi kerak.
- Tray menyusi faqat o'zbekcha. Global tugma band bo'lsa (boshqa dastur egallagan) faqat log ogohlantirishi, foydalanuvchiga xabar yo'q.
- CSV: kategoriya barcha satrlar uchun bitta; satrma-satr kategoriya tanlash yo'q.

### Barqarorlashtirish — GUI sinovi, ribo filtri, error boundary, qarorlar (2026-10-15)

Yangi funksiya yo'q. Byudjet sahifasi (D7) haqiqiy Tauri oynasida boshidan oxirigacha bosib sinaldi: PIN o'rnatish, obuna qo'shish/«ishlatdim»/bekor qilish, konvert qo'shish va hafta yakuni, «Kelajagim»ga o'tkazish (to'g'ri va ortiqcha summa), bazaviy davr (o'tgan va joriy davr), Kelajagim balansi va tarixi. Hisoblar domen bilan mos (1 000 + 500 000 = 501 000; o'tkazishdan keyin 497 000).

**GUI sinovi topgan va tuzatilgan nuqsonlar**

- «Kelajagim» tarixida qutqarilgan puldan kirim «Pul olish» deb ko'rsatilardi (`kindLabel` ning `default` tarmog'i). Endi `RESCUE_DEPOSIT` → «Qutqarilgan puldan».
- O'tkazish va bazaviy davr xatolari karta oxirida, tugmadan uzoqda chiqardi (ekrandan tashqarida qolardi). Endi har forma o'z xatosini tugmasi ostida ko'rsatadi.
- Joriy davrni bazaviy qilishga urinishda «Kun 1 dan 31 gacha bo'lishi kerak» chiqardi (`INVALID_DAY` qayta ishlatilgan). Yangi `BASELINE_NOT_PAST` kodi va matni.
- WebView2 avtoto'ldirish popup'i («Сохраненные сведения») summa maydonida tugmani yopib qo'yardi. `Field` da `autoComplete="off"` standart.
- Bitta sahifaning render xatosi butun ilovani bo'sh qoldirardi (error boundary yo'q; HMR oraliq holatida kuzatildi). `PageErrorBoundary` — sahifa darajasida umumiy xabar va «Qayta urinish», boshqa bo'limga o'tganda tiklanadi. Xato matni foydalanuvchiga ko'rsatilmaydi va loglanmaydi (ma'lumot bo'lishi mumkin).

**Qo'shildi**

- Ribo filtri testi `ui/src/i18n/ribo-terms.test.ts`: uz/ru tarjimalari va `spec/content/chapters.json` da foizni daromad yoki yechim sifatida targ'ib qiluvchi iboralar yo'qligi (DESKTOP_PROMPT 8-bo'lim). Qarz kategoriyasi «Kredit» va ta'limiy taqiq matnlari ruxsat etilgan.
- `offer_check`: uch va undan ko'p sariq bayroq — qizil (qaror, OPEN_QUESTIONS «Hal qilingan»).
- Qarorlar yozildi (OPEN_QUESTIONS «Hal qilingan»): `IncomeSourceType` ma'nolari, «ongli chetlab o'tish» (bitta amal, 20+ belgi sabab, ADULT PIN), qarz yuk chegaralari 30%/50% (friction, taqiq emas), OfferCheck qoidasi, vektorsiz formulalar uchun `spec/test-vectors/proposed/` tartibi.

**Tekshirildi, o'zgartirilmadi**

- `set_content_protected(true)` relizda allaqachon bor (`lib.rs`); debug'da skrinshot uchun o'chiq.
- `Ctrl+L` (qulflash) va `Ctrl+N` (tez kiritish) bor; `Ctrl+K`, `Ctrl+P` yo'q (keyingi bosqich).

**Qolgan kichik kamchilik**

- Bazaviy davr saqlangach, o'sha davrda xarajat bo'lmasa, ekranda «Bazaviy davr yo'q» qolaveradi — tanlov saqlangani ko'rinmaydi. DTO'ga tanlangan sanani alohida chiqarish kerak (D8 UI bilan).

### D9, D11, D13, D13A, D14 (domen qismi) — Qarzlar, marosim, taklif tekshiruvi, nizo, almashish (2026-10-15)

**Qo'shildi**

- `domain::loans`: `RepaymentPlan` (bo'sh reja — `REPAYMENT_PLAN_REQUIRED`), `Loan` va `Receivable` (reja summasi = asosiy qarz; `Receivable` da foiz maydoni yo'q), `borrow_check` (`OK / CAUTION / STOP`).
- `domain::ceremony`: `BudgetLine` (miqdor × narx), `FundingSource` (`SAVINGS | FAMILY_CONTRIBUTION | EXPECTED_GIFT | DEBT`), `confirm` — qarzli qator bo'lsa oilaviy muhokamasiz tasdiqlanmaydi (`FAMILY_DISCUSSION_REQUIRED`).
- `domain::offer_check`: 6 savol, `GREEN / YELLOW / RED` va har bir bayroqning izohi.
- `domain::review`: yillik yangilash eslatmasi (`review_date` dan 30 kun oldin), nizoda taqsimot bloklanishi (`IN_DISPUTE`).
- `domain::interchange`: kalit qurilma (`NOT_KEEPER_DEVICE`) va import oldidan fork aniqlash (birinchi farq, 1 dan).
- Yangi `DomainError` kodlari: `REPAYMENT_PLAN_REQUIRED`, `PLAN_MISMATCH`, `FAMILY_DISCUSSION_REQUIRED`, `IN_DISPUTE`, `NOT_KEEPER_DEVICE`.

**Qarorlar (mahsulot qarori — tasdiqlash kerak, OPEN_QUESTIONS «Hal qilingan»)**

- Qarz oldidan yuk chegaralari: daromadning 30% — ogohlantirish, 50% — to'xtash. SPEC aniq raqam bermaydi.
- OfferCheck qoidasi: QIZIL — kafolatlangan foyda yoki yangi a'zo talab qilinishi; SARIQ — shoshiltirish, yozma shartnoma yo'qligi, real mol/ish yo'qligi yoki «zarar yo'q» deyilishi; YASHIL — qolgani.

**Ma'lum cheklovlar (keyingi ishga qoldirildi)**

- D9: `Debt` jadval turlari (`DIFFERENTIATED`, `FIXED_MARKUP`, `MANUAL`), storage, IOU (tilxat) PDF, «qarzsiz kun» prognozi, friction ekrani — qo'shilmadi. Qarz va bergan qarz tuzilmalari va reja qoidalari bor.
- D11: stsenariylarni taqqoslash, «Goal» (maqsadli jamg'arma) va chop etiladigan smeta — qo'shilmadi. Tasdiqlash qoidasi bor.
- D13: venture ledger saqlash, davrni yopish va o'zgarmaslik (storage), avtomatik taqsimot bilan bog'lash, «Hunardan ishga» stsenariylari, sherik uchun davr PDF — qo'shilmadi. OfferCheck va taqsimot bloklash tayyor.
- D14: `.baraka` konteyner (shifrlash, JSON Schema `spec/interchange/`), eksport/import oqimi — qo'shilmadi. Kalit qurilma va fork qoidalari tayyor.
- D15: kod imzolash uchun sertifikat talab qilinadi (tashqi); onboarding va E2E — qo'shilmadi. `docs/RELEASE_CHECKLIST.md` yozildi.

### D10–D13A (domen qismi) — Amortizatsiya, 70/20/10, sheriklik taqsimoti, katta foyda (2026-10-15)

**Qo'shildi**

- `domain::amortization`: annuitet to'lovi (i128 qo'zg'aladigan-nuqta, `f64` yo'q), oylik jadval, qo'shimcha to'lov bilan muddatni qisqartirish. Vektor `amortization.json` (3 case, to'liq jadval bilan).
- `domain::recovery`: 70/20/10 taqsimoti (`allocate`), jamg'arma ≥ 100 bp, yig'indisi 10 000. Vektor `debt_recovery_split.json` (6 case).
- `domain::partnership`: `MUDARABA` (foyda ulush bo'yicha, zarar kapital egasiga) va `MUSHARAKA` (zarar kapitalga mutanosib); kafolatli summa taqiqlangan. Vektor `profit_distribution.json` (4 case).
- `domain::profit_spike`: «katta foyda» — reja ≥ 150% yoki uch davr o'rtachasi ≥ 200%. Vektor `profit_spike.json` (5 case).
- Vektor runnerlari: `crates/vectors/tests/debt_vectors.rs`, `profit_vectors.rs`. Fayllar mobil bilan baytma-bayt, `SHA256SUMS` da.

**Qarorlar va sabablar**

- Annuitet: `P·r·g/(g−1)`, `g = (1+r)^N` — i128 qo'zg'aladigan-nuqta (10^18), ko'paytmalar bo'linadi (`mul_fixed`), shuning uchun realistik muddatlarda ham i128 chegarasidan oshmaydi. Oxirgi to'lov qoldiqdan oshmaydi.
- Taqsimot qismlari `allocate` bilan: yig'indisi har doim daromadga teng (tiyin yo'qolmaydi). Zarar — manfiy qismlar, `allocate` mutlaq qiymatda hisoblanadi.
- `DomainError` ga yangi kodlar: `SPLIT_NOT_100_PERCENT`, `SAVINGS_BELOW_MINIMUM`, `PROFIT_SHARES_NOT_100`, `GUARANTEED_RETURN_FORBIDDEN`.

**Ma'lum cheklovlar (keyingi ishga qoldirildi)**

- D10: amortizatsiyaning qolgan uch turi (`DIFFERENTIATED`, `FIXED_MARKUP`, `MANUAL`), payoff rejalashtiruvchisi, UI (jadval va grafik) — qo'shilmadi. Faqat annuitet (vektor bilan qoplangan).
- D10: `DebtContributor`, «Qarzsiz kun», rejimning avtomatik qaytishi — qo'shilmadi.
- D12: sheriklik shartnomasi ustasi, versiyalash, PDF, buyout jadvali, kapital qabul qilishda oilaviy rozilik — qo'shilmadi (domen hisoblash bor).
- D13A: `ProfitSpikeAlert` taqsimotga ulanmagan (UI va Tauri qatlami keyin).

### D8A — Kelishuv dvigateli va append-only jurnal (2026-10-15)

**Qo'shildi**

- `domain::journal`: `JournalEntry`, JCS (RFC 8785) kanonizatsiya — qo'lda, kalitlar tartibi qat'iy, pul — satr; `hash_n = SHA256(hash_{n-1} + "\n" + JCS)`, genesis — 64 nol; `verify_chain` birinchi buzilgan yozuvni 1 dan boshlab qaytaradi (`journal_chain.json`: 3 xesh + buzilish).
- `domain::agreement`: `AgreementType`, `AgreementStatus`, 9 savol bo'yicha `completeness` (`agreement_completeness.json`, 15 vektor). Tur farqi: LOAN — 3-savol jadval (`hasSchedule`), 4–5 avtomatik; FAMILY — hakam ixtiyoriy, 4–5 izohli «tegishli emas».
- Sxema v8: `agreements` (versiyali), `journal_entries` (`seq`, `prev_hash`, `hash`), `BEFORE UPDATE` va `BEFORE DELETE` triggerlari — `RAISE(ABORT, 'journal is append-only')`. Tuzatish — `CORRECTION` yozuvi.
- Storage: `AgreementRepo` (versiya bo'yicha optimistik yangilash, `VersionConflict`), `JournalRepo` (`append` — bitta tranzaksiyada, `list`, `verify`).
- Vektor fayllari mobil bilan baytma-bayt (`SHA256SUMS` ga qo'shildi).

**Qarorlar va sabablar**

- JCS domen darajasida qo'lda: `serde_json` ni domenga tortmaslik uchun. Qochlar RFC 8785 bo'yicha (`"`, `\`, boshqaruv belgilari; qolgani UTF-8). Izoh yo'q bo'lsa `note` kaliti yozilmaydi.
- `verify` ikki darajali natija: ichki — zanjir buzilishi, tashqi — baza xatosi. Baza xatosi «zanjir to'g'ri» deb o'qilmaydi.
- `prev_hash` jadvalda ham saqlanadi: tekshiruv qayta hisoblash bilan birga, DB'dagi zanjirni ko'rish uchun.

**Ma'lum cheklovlar (keyingi ishga qoldirildi)**

- 9 savol ustasi (UI), jonli PDF preview, imzolar (sichqoncha/pero/skan), oral kelishuv yozuvi, kelishuv PDF snapshot testi — qo'shilmadi. Domen va saqlash tayyor.
- Tauri command va DTO qatlami kelishuvlar uchun hali yo'q (OPEN_QUESTIONS, 36).
- `DutyIncident` (bajara olmayman xabari) — D13A bilan birga.

### D8 — Qorovul, zaxira maqsadi, shaxsiy inflyatsiya, tayyorgarlik darvozasi (2026-10-15)

**Qo'shildi**

- `domain::emergency` — zaxira maqsadi: so'nggi 3 ma'lumotli oy o'rtachasi × N, yarim tiyin yuqoriga (`emergency_target.json`, 3 vektor).
- `domain::inflation` — shaxsiy indeks: bazis punktlarda mahsulot o'zgarishi, og'irlikli o'rtacha (`personal_inflation.json`, 1 vektor).
- `domain::readiness` — tayyorgarlik darvozasi: zaxira ≥ 6,0 oy VA (foizli qarz yo'q YOKI chiqish rejasi bor); sabablar tartibi doim bir xil (`readiness_gate.json`, 16 vektor).
- `domain::income_source` — `IncomeSourceType` (`TER | MOL | TAVAKKAL | RIBO`), faqat kodlar (ma'nolari OPEN_QUESTIONS «Hal qilingan»).
- Sxema v7: eski «Kelajagim» yozuvlarida `vault_type` bo'lmasa, `QOROVUL` deb to'ldiriladi. Balans o'zgarmaydi (`reserve_flows.rs`).
- `spec/test-vectors/`: uchta vektor fayli mobil ilova bilan umumiy — baytma-bayt nusxa; `SHA256SUMS` manifesti bilan tekshiriladi (`mobil_bilan_umumiy_vektorlar_manifestga_mos`).

**Qarorlar va sabablar**

- **`sha2` 0.10** (`crates/vectors`, faqat dev-dependency): vektor fayllarining xeshini tekshirish uchun. D8A jurnal zanjiri (SHA-256) ham shu crate'dan foydalanadi. Boshqa yangi crate yo'q.
- Zaxira o'rtachasi: xarajati nolga teng oylar hisobga olinmaydi; uchtadan kam ma'lumotli oy bo'lsa maqsad `None` (hisoblanmaydi).
- Shaxsiy indeks: noldan katta bazaviy narx va bir valyuta talab qilinadi (`INVALID_PRICE`). Og'irliklar 100% bo'lishi shart emas, faqat yig'indisi nolga teng bo'lmasligi.
- Aktiv turi `assets.type = 'VAULT'` saqlanadi: uni `QOROVUL` ga o'zgartirish jadval qayta yaratishni talab qiladi, pul esa bunga muhtoj emas.

**Tuzatildi**

- **SQLCipher poygasi.** Parallel testlarda birinchi ochish kalitni bo'sh deb o'qirdi (`sqlcipher not initialized`) — `storage_flows` 3 yugurishdan 1 tasida yiqilardi. `Database::open*` endi ochishni jarayon bo'yicha qulf bilan ketma-ket bajaradi; 6 yugurishda 6/6 yashil.

**Ma'lum cheklovlar (keyingi ishga qoldirildi)**

- «Narx daftari» (narx nuqtalari, savat) va «Sichqon kemirgani» UI'si qo'shilmadi: domen darajasidagi indeks tayyor, saqlash va ekran keyingi bosqichda.
- «Ongli chetlab o'tish» (darvozani qasddan ochish) qo'shilmadi: vektorlarda semantika yo'q; OPEN_QUESTIONS «Hal qilingan».
- `ReadinessGate` zaxira oylarini hisoblamaydi (kirish — o'ndan bir oy birligida); qorovul balansidan hisoblash keyingi bosqichda.

### D7 — Byudjet: obunalar, konvertlar, «Qutqarilgan pul», «Kelajagim»ga o'tkazish (2026-10-15)

**Qo'shildi**

- Sxema v6: `subscriptions`, `envelopes`, `savings_rescues`, `household_settings` (xonadon sozlamalari, kalit–qiymat).
- Domen: `rescue.rs` (havas kamayishi, jami, qoldiq; yaxlitlash yarmidan yuqoriga), `subscription.rs` (bekor qilish, «ishlatdim», 30 kunlik «unutilgan» chegarasi), `envelope.rs` (haftalik limit, qoldiq manfiy emas).
- `VaultMovement::RescueDeposit`: «Kelajagim»ga o'tkazish `vault_transactions` da `DEPOSIT` bo'lib yoziladi, `reason` ustunida qutqarish yozuvi identifikatori.
- Vektorlar: `spec/test-vectors/savings_rescue.json` (hisob 7 ta, obuna tejami 6 ta) — `crates/vectors` runner'i bilan.
- Tauri: `budget.rs` (xizmat), `budget_commands.rs` (8 ta command: `get_budget`, `add_subscription`, `mark_subscription_used`, `cancel_subscription`, `add_envelope`, `close_envelope_week`, `transfer_to_vault_from_rescue`, `set_baseline_period`). `build.rs` va `capabilities/default.json` da ruxsat.
- UI: «Byudjet» sahifasi (`ui/src/app/budget/`): qutqarilgan pul kartasi, «Kelajagim»ga o'tkazish, bazaviy davr, obunalar, haftalik konvertlar.
- Testlar: domen (rescue, subscription, envelope), storage (`budget_flows.rs`, 6 ta; sxema v6), Tauri xizmati (3 ta), frontend (`budget.test.tsx`, 5 ta).

**Qarorlar va sabablar**

- Formula mobil `rescue.dart` bilan bir xil (`spec/test-vectors/savings_rescue.json`). Obuna tejami: oylik × kunlar / 30, bekor qilingan kunning o'zi ham kiradi; davr boshidan oldin bekor qilingan bo'lsa — davr boshidan. Yakunda butun so'mgacha yaxlitlanadi.
- Havas — shu davrdagi `HAVAS` toifali xarajatlar. Bazaviy davr: sozlamada tanlangan, bo'lmasa o'tgan davr; uning xarajatlari bo'lmasa, bazaviy taqqoslash o'tkazilmaydi (`has_baseline = false`). Ko'proq sarflash — ayblov emas, faqat holat (`spent_more`).
- «Kelajagim»ga o'tkazish bitta tranzaksiyada yoziladi: `TRANSFER` qutqarish yozuvi + `DEPOSIT` kirimi. Summa hali o'tkazilmagan qismidan oshsa — `RESCUE_EXCEEDS_AVAILABLE`.
- Konvert qoldig'i hafta uchun bir marta yoziladi (`ENVELOPE_WEEK_CLOSED`). Qoldiq = limit − bog'langan kategoriyaning shu haftadagi sarfi (manfiy emas).
- Obuna tejami jonli hisoblanadi, saqlanmaydi: `SUBSCRIPTION` turi sxemada bor, lekin hozircha yozuv yaratilmaydi.

**Ma'lum cheklovlar (keyingi ishga qoldirildi)**

- Tray ikonkasi va Ctrl+Alt+B mini oynasi (global shortcut, qulflanganda summalar yashiriladi) — qo'shilmadi.
- CSV import ustasi (matn joylash, ustunlarni moslash) — qo'shilmadi.
- Haqiqiy oynada (Tauri) qo'lda sinov qilinmagan: testlar jsdom va xizmat darajasida.

### D6 — davomi: bayonnoma PDF, hafta varag'i, odatlar, Juma bildirishnomasi, PIN xavfsizligi (2026-10-15)

**Qo'shildi**

- **`crates/pdf` (`baraka-pdf`):** oila kengashi bayonnomasi typst bilan PDF qilinadi (DESKTOP_PROMPT 2: PDF = typst). Yangi tashqi bog'liqliklar: `typst`, `typst-pdf`, `typst-assets` (`fonts` xususiyati) — hammasi 0.13.1. Sabab: 0.13 API'si shu loyiha uchun tekshirilgan; 0.15 keyingi yangilash alohida vazifa. Shriftlar (Libertinus Serif) ilova ichida: tizim shriftiga bog'liq emas. Matnlar typst'ga faqat satr qiymati sifatida beriladi (markup inyeksiya yo'q). Testlar: PDF yaratiladi; `ʻ`/`ʼ` shriftda bor; snapshot mos (`UPDATE_SNAPSHOTS=1` bilan yangilanadi).
- **`create_council_report`:** PDF ilova ma'lumot papkasining `reports` bo'limiga yoziladi; yo'li UI'da ko'rsatiladi. Fayl tanlash dialogi keyingi bosqichda (OPEN_QUESTIONS, 9-band).
- **Hafta varag'i:** `add_expenses` — bir martada ko'p xarajat. Sana shu hafta ichida va bugungacha bo'lishi shart. Hammasi avval tekshiriladi, keyin yoziladi. Ma'lumotlar bazasi tranzaksiyasi ishlatilmagan: yozish xatosi tekshiruvdan keyin kutilmaydi (OPEN_QUESTIONS, 36-band).
- **Odatlar (SPEC 2B.9):** kategoriyaga `is_habit` belgisi (sxema v5). `domain::odat` — oy va yil bo'yicha jami, yozuvlar soni. Ayblov matni yo'q. Yangi odat — `add_habit` (toifasi `HAVAS`).
- **Juma shirinligi bildirishnomasi:** `tauri-plugin-notification` 2.7.0 (DESKTOP_PROMPT 7 da nomlangan). Sabab: ilova ochiq bo'lganda ritual kunini eslatish. Ilova qulflangan bo'lsa tekshiruv jim o'tkaziladi; bir kunda bir marta.
- **Xarajat sanasi:** `add_expense` endi `occurredOn` qabul qiladi (yo'q bo'lsa — bugun).
- **Oy xulosasi:** `weekStart` va `today` maydonlari (hafta varag'i uchun).
- **Havas chegarasi uchun PIN:** a'zo PIN'ini almashtirish joriy PIN'ni talab qiladi; faqat PIN egasi almashtira oladi (OPEN_QUESTIONS, 39-band).

**Qarorlar va sabablar**

- **PIN almashtirish:** joriy PIN noto'g'ri bo'lsa — urinish hisobga olinadi va kutish qoidasi qo'llanadi (ilova PIN'idek).
- **Chegarani o'zgartirish rozilikni bekor qiladi** — shunday qoldi (OPEN_QUESTIONS, 40-band).
- **Bayonnoma:** hisob-kitob backend'da; PDF tarkibi tayyor matn sifatida beriladi. Snapshot o'zgarsa, testdan xabar chiqadi.

**Tekshiruv**

- `cargo test --workspace`: yashil. Yangi: `baraka-pdf` 3 test; `family` 12 test (hafta varag'i, odat, PIN almashtirish, bildirishnoma); `report` 2 test; domen `odat` 2 test.
- `cargo clippy --workspace --all-targets -- -D warnings`: toza. `cargo fmt --all -- --check`: toza.
- Frontend: `pnpm test` (yashil, oila testlari 44 ta), `pnpm lint`, `pnpm typecheck`, `pnpm format:check`: yashil.
- GUI: React UI in-app brauzerda IPC soxtasi bilan tekshirildi: odat qo'shish (ro'yxatda «Oyiga: 0 soʻm»), hafta varag'i (saqlash holati, ro'yxatda yangi xarajat), kengash — PIN almashtirish tugmasi, PDF tugmasi va yo'l ko'rsatilishi. Native oyna va Windows toast bildirishnomasi bu muhitda tekshirilmagan.

**Hali bajarilmagan**

- Fayl tanlash dialogi (bayonnomani istalgan joyga saqlash) va chop etish dialogi — OPEN_QUESTIONS, 9-band.
- Oila a'zolarini tahrirlash va o'chirish — OPEN_QUESTIONS, 39-band.

### D6 — Uch toifa, havas chegarasi, oila kengashi (2026-10-15)

**Qo'shildi**

- **`crates/security`:** a'zo PIN verifier (`member_pin`): tuz va Argon2id, solishtirish doimiy vaqtda. PIN saqlanmaydi.
- **`crates/domain`:**
  - `necessity` — `ZARUR | KERAK | HAVAS` va `NecessityChange` (kim, qachon, qaysidan qaysiga). Standart toifalar `CategoryKey::default_necessity` da: ZARUR — ijara, kredit, oziq-ovqat, kommunal, yoqilg'i, yo'lkira; HAVAS — gazak, kafe; KERAK — qolganlari, shu jumladan bola ta'limi va sadaqa.
  - `Category::change_necessity` — o'zgartirish tarix yozuvi bilan birga qaytadi.
  - `Expense` — `necessity`, `is_gift`, `is_ostentation`, `funded_by_debt`.
  - `limit` — `HavasLimit`, `LimitConsent`; `is_active` (barcha kattalar rozi); `counts_as_havas` (`HAVAS`, sovg'a emas, sadaqa emas); `level` (80% va 100% — yumshoq darajalar).
  - `treat` — `ScheduledTreat` (haftalik, hafta kuni bo'yicha).
  - `DomainError`: `NECESSITY_UNCHANGED`, `PIN_NOT_SET`.
- **`crates/storage`:** sxema v4. Toifa standart qiymatlari v1 dagi mavjud ustunlarni (`categories.default_necessity`, `expenses.necessity`) to'ldiradi; migratsiya testi bor. Yangi jadvallar: `necessity_changes`, `havas_limits`, `limit_consents` (`UNIQUE`), `scheduled_treats`; `members` ga `pin_failed_attempts`, `pin_failed_at`. Repo'lar: `PinRepo`, `LimitRepo`, `TreatRepo`; `CategoryRepo` — tarix; `ExpenseRepo` — yangi maydonlar.
- **`src-tauri`:** `family` servisi va 12 command: `get_month_summary`, `list_month_expenses`, `add_expense`, `set_category_necessity`, `get_havas_limit`, `set_havas_limit`, `consent_havas_limit`, `list_members`, `add_member`, `set_member_pin`, `list_treats`, `add_treat`. Xarajat qo'shilganda `EXPENSE_RECORDED` hodisasi yoziladi.
- **UI:** «Xarajatlar» sahifasi (oy xulosasi, xarajat qo'shish: sovg'a, obro' va qarz bayroqlari, ro'yxat), «Juma shirinligi» kartasi, «Oila kengashi» (to'liq ekran, 4 qadam: oyni ko'rib chiqish, toifalarni kelishish, havas chegarasi va kattalar roziligi — har biri o'z PIN'i bilan, yakun). i18n: uz va ru.

**Qarorlar va sabablar**

- **Toifa xarajat yozilganda kategoriyadan olinadi va xarajatda saqlanadi.** Keyingi o'zgarish eski yozuvlarni o'zgartirmaydi.
- **Sovg'a va sadaqa havas hisobiga kirmaydi** (testlar bilan). Obro' xarajati havas ichida qoladi, lekin alohida ko'rsatiladi.
- **Chegara faol emas**, agar bitta katta ham rozi bo'lmasa (test). Yumshoq ogohlantirish faqat faol chegarada ko'rsatiladi; bloklash yo'q.
- **Chegara o'zgarsa, rozilik qayta olinadi** — yangi chegara, yangi rozilik.
- **A'zo PIN'i** ilova PIN'i bilan bir xil himoyada: uchta noto'g'ri urinishdan keyin kutish (`retry_after_secs`).
- **Juma shirinligi** faqat haftalik. Bildirishnoma yo'q (OPEN_QUESTIONS, 38-band).

**Tekshiruv**

- `cargo test --workspace`: yashil (domen 81, storage oila oqimlari 5 va v4 migratsiyasi, security PIN 5, src-tauri oila 6).
- `cargo clippy --workspace --all-targets -- -D warnings`: toza. `cargo fmt --all -- --check`: toza.
- Frontend: `pnpm test` (41, shu jumladan 7 ta yangi oila testi), `pnpm lint`, `pnpm typecheck`, `pnpm format:check`: yashil.
- GUI: dev build ochilmadi (native oyna avtomatizatsiyaga ulanmadi). React UI in-app brauzerda IPC soxtasi bilan tekshirildi: xarajat qo'shish (sovg'a bayrog'i), toifani o'zgartirish, PIN o'rnatish, noto'g'ri PIN xatosi, ikki katta roziligi («Chegara faol»), Escape bilan yopish.

**Hali bajarilmagan (keyingi bosqich)**

- Bayonnoma PDF — bajarildi (yuqoridagi «davomi» bo'limiga qarang).
- «Hafta varag'i» ommaviy kiritish (36-band).
- Odat statistikasi, SPEC 2B.9 (37-band).
- Juma shirinligi bildirishnomalari va a'zo tahriri/o'chirish (38–39-bandlar).

### D5 — Kontent dvigateli: boblar, odat asosidagi ochilish, haftalik vazifalar, «Daftar sahifasi» (2026-10-14)

**Qo'shildi**

- **Kontent (`spec/content/`):** `chapters.json` va `content_schema.json` mobil repo bilan bayt-bayt bir xil (sha256 tekshirilgan). 5 bob, har bobda aniq 3 ta haftalik vazifa, qonun va diniy bloklar. Qissa matnlari hozircha placeholder.
- **`crates/domain`:**
  - `content` — `LocalizedText` (`uz` majburiy, `ru` ixtiyoriy), `ContentBlock` (paragraph, quote, religious + `ReligiousReviewStatus`), `Chapter`, `Law`, `WeeklyTask`, `TaskTrigger` (17 hodisa kodi; noma'lum kod bobni yaroqsiz qiladi).
  - `content_parser` — mobil `ContentParser` qoidalari va xato xabarlari; buzuq bob o'tkazib yuboriladi, butun fayl buzuq bo'lsa — bo'sh natija.
  - `unlock` — `ChapterUnlockPolicy`; `HabitUnlockPolicy` (standart: 2 vazifa, 7 kun — SPEC 2C.6) va `TimeBasedUnlockPolicy` (mobil bilan paritet).
  - `progress` — `TaskCompletion` (hafta boshi bo'yicha), `DaftarPage` (bob uchun bitta, 5000 belgigacha).
  - `DomainError`: `CHAPTER_LOCKED`, `TASK_NOT_CURRENT`, `BODY_REQUIRED`, `BODY_TOO_LONG`.
- **`crates/storage`:** sxema v3 (faqat yangi jadvallar: `task_completions`, `daftar_pages`; v1 va v2 o'zgarmagan). Repo'lar: `TaskCompletionRepo` (hafta bo'yicha; birinchi bajarilish tarixi mantiqiy o'chirilganlarni ham hisobga oladi), `DaftarPageRepo`.
- **`src-tauri`:**
  - `content` servisi: kontent bir marta yuklanadi (kompilyatsiyada `include_str!`); ochilish, joriy bob va bajarilishlar har chaqiriqda hisoblanadi.
  - Command'lar: `list_chapters`, `get_chapter`, `get_weekly_tasks`, `set_task_done`, `save_daftar_page`.
  - Avtomatik hodisalar: `VAULT_OPENED` («Kelajagim» ochilganda), `INCOME_SHARED` va `VAULT_FIRST_DEPOSIT` (ulush qabul qilinganda), `EXPENSE_RECORDED` (audit xarajati), `AUDIT_COMPLETED` (audit yakunida), `DAFTAR_PAGE_WRITTEN` (sahifa saqlanganda).
  - Tasdiqlanmagan diniy blok DTO'ga release'da kirmaydi (`SHOW_PENDING_RELIGIOUS = cfg!(debug_assertions)`).
  - `ApiError`'ga yangi variant qo'shilmadi: yangi xatolar mavjud `Rule { rule }` orqali yuboriladi.
- **UI:** «Boblar» (ro'yxat: ochiq/yopiq holat, ochilish sharti), bob sahifasi (qissa bloklari, qonun, haftalik vazifalar, «Daftar sahifasi»), bosh sahifada «Shu haftaning vazifalari» kartasi. Har kontent ekranida disklеymer. i18n: uz va ru (kalitlar parite).
- **Bog'liqlik:** `crates/domain` ga `serde_json` qo'shildi (kontent JSON'ini domen qatlamida tekshirish uchun). `serde_json` workspace'da allaqachon bor (`vectors`, `src-tauri`); yangi crate emas, ADR o'zgarmadi.

**Qarorlar va sabablar**

- **Ochilish mobil bilan bir xil.** Keyingi bob: oldingi bobning 2 ta vazifasi bajarilgan va kamida 7 kun o'tgan bo'lsa ochiladi. Ochilgan bob qayta yopilmaydi: birinchi bajarilish sanasi mantiqiy o'chirilganda ham saqlanadi.
- **Joriy bob — eng so'nggi ochilgan bob.** Haftalik vazifalar faqat shu bob uchun shu hafta belgilanadi. Oldingi boblarda vazifalar faqat ko'rsatiladi (bir marta bajarilgan bo'lsa belgisi bilan).
- **Hafta juma kunidan boshlanadi** (`week_of`, mobil bilan bir xil).
- **Tasdiqlanmagan diniy blok.** Release'da yashirin: `cargo test --release` da `release_buildda_get_chapter_pending_blokni_chiqarmaydi` shuni tekshiradi. Debug buildda ulamo tekshiruvi uchun ko'rinadi va «ulamo tekshiruvida» belgisi bilan chiqadi.
- **Avtomatik belgilash idempotent.** Bir hafta ichida bir vazifa ikki marta yozilmaydi; hodisa faqat joriy bobning vazifalariga tegishli.
- **`VAULT_OPENED`** — «Kelajagim» ma'lumoti yuklanganda yoziladi. Ma'lumot qayta yuklanganda ham chaqiriladi, lekin haftada bir marta yoziladi.
- **«Daftar sahifasi» — 5000 belgi chegarasi** (standart qaror; mobilda chegara yo'q edi). OPEN_QUESTIONS, 34-band.

**Tekshiruv**

- `cargo test --workspace`: domen (unlock, parser, progress, content), storage (progress oqimlari, migratsiya v3), src-tauri (content servisi: ochilish, hodisa, DTO, Daftar sahifasi), vektorlar — yashil.
- `cargo test --release -p baraka-daftari release_buildda`: release buildda tasdiqlanmagan diniy blok `get_chapter` javobida yo'q — yashil.
- `cargo clippy --workspace --all-targets -- -D warnings`: toza. `cargo fmt --all -- --check`: toza.
- Frontend: `pnpm test` (7 fayl, 34 test), `pnpm lint`, `pnpm typecheck`, `pnpm format:check` — yashil.
- GUI: dev build (`pnpm dev`) ochilmadi — native oyna avtomatizatsiyaga ulanmadi. Shu sababli React UI in-app brauzerda, IPC soxtasi bilan tekshirildi: ro'yxat, ochiq/yopiq bob, bob sahifasi, vazifa belgilash va olib tashlash, «Daftar sahifasi» saqlash, RU/UZ almashinuvi, «Barcha boblar» va «Boblar roʻyxatiga qaytish» tugmalari, bosh sahifa kartasi. Haqiqiy Tauri IPC bilan E2E hali o'tkazilmagan (OPEN_QUESTIONS, 14-band).

### D4 — Daromad, «Kelajagim», audit, «Kimning puli?», majburiyat va nasiya, bosh sahifa (2026-10-14)

**Qo'shildi**

- **Vektorlar (`spec/test-vectors/`):**
  - `unexplained_gap.json` — mobil ilovadagi fayl bilan bayt-bayt bir xil (sha256 tekshirilgan).
  - `streak.json`, `income_share.json`, `money_parse.json` — yangi. Qoidalar mobil `habit.dart`, `vault_service.dart`, `money_format.dart` va ularning testlaridan olingan. Mobil ilova bu fayllarni hali ishlatmaydi (OPEN_QUESTIONS, 21-band).
  - `vectors` runner'lari: 8 ta suite, har bir fayl uchun runner bor (qamrov testi buni tekshiradi).
- `crates/money`: `parse_amount` (MoneyParser qoidalari: bo'sh joy, `_`, apostrof, `so'm`/`soʻm`/`сум`/`$`/`€`/`₽`, kasr aniqligi), `ceil_to_step` (yuqoriga yaxlitlash — yaxlitlashning ikkinchi yagona joyi), `MoneyError::ParseError` (`PARSE_ERROR`).
- `crates/domain`:
  - `calendar` — Toshkent sanasi (UTC+5), haftalar jumadan, oylar oylik kunidan (31 → oyning oxirgi kuni).
  - `habit` — streak (joriy hafta tugamaguncha uzilmaydi), `streak_since` (progressiv taklif uchun).
  - `share` — `ShareRule` (foiz yoki oylik summa, progressiv), `suggest_share`, `progression_offer` (4 hafta → +1 %, maks 10 %).
  - `income`, `expense`, `obligation` (tur → standart kategoriya), `category` (13 tizim kalitli kategoriya), `debt` (nasiya qoldig'i), `vault` (balans, ulush, pul olish va boshlang'ich balans qoidalari).
  - `ledger` — oy hisobi: majburiyat kategoriyadagi yozilgan xarajat bilan qoplanadi (ikki marta hisoblamaslik), izohsiz summa, «Kimning puli?» egalari.
  - `report` — oylik audit surati (o'zgarmas).
  - `DomainError` kengaytirildi: har xato barqaror kodga ega (`INSUFFICIENT_BALANCE`, `REASON_REQUIRED`, `INCOME_ALREADY_SHARED` va boshqalar).
- `crates/storage`:
  - Sxema v2 (faqat `ALTER TABLE ... ADD COLUMN` va yangi jadvallar; v1 ma'lumotlari saqlanadi — migratsiya testi bor): `households.month_start_day`, `categories.system_key` (xonadonda bir marta), `obligations.kind` va `category_id`, `vault_transactions.income_id`, `allocation_rules.progression_offered_on`. Yangi: `debts`, `debt_payments`, `monthly_reports` (davr uchun bir marta, `UNIQUE`).
  - Repo'lar: `CategoryRepo`, `IncomeRepo`, `ExpenseRepo`, `ObligationRepo`, `VaultRepo` (aktiv va yozuvlar), `RuleRepo`, `DebtRepo`, `ReportRepo`.
- `src-tauri`:
  - `session`: `verify_pin` (pul olish tasdig'i), `with_database` (faqat ochiq bazada ishlaydi), `SessionError::Locked`, `DatabaseWithoutKey` (kalit fayli yo'q, baza bor bo'lsa sozlash rad etiladi — ma'lumot jim ustiga yozilmaydi).
  - `finance` servisi va 22 ta command (`get_home`, `create_income`, `accept_share`, `withdraw`, `get_audit`, `finish_audit`, `get_whose_money`, `add_obligation`, `pay_debt` va boshqalar). Har command yupqa; biznes mantiq `finance` da.
  - DTO: pul — `minor` (satr) va tayyor `formatted`; «Kimning puli?» bo'laklari `shareBp` bilan (kenglikni backend hisoblaydi).
  - `ApiError`: `Locked`, `DatabaseWithoutKey`, `Rule { rule }` (domen kodi).
- UI:
  - Tez daromad (`Ctrl+N`): summa → Enter → «Shundan X so'm — kelajagingiz uchun» → Enter bilan ajratish. Taklif matni (`formatted`) qayta kiritiladi.
  - «Daromad» sahifasi (shu oy), bosh sahifa KPI kartalari («O'zingizga to'langan», «Kelajagim» balansi, «Oy yakuni», odat, audit holati).
  - «Kelajagim»: balans, odat, progressiv taklif, ulush qoidasi (5 % / 10 % / oylik summa), boshlang'ich balans (bir marta), pul olish (sabab majburiy, 5 soniya o'ylash pauzasi, PIN har safar), tarix.
  - Oylik audit ustasi (4 qadam): daromad va majburiyatlar, xarajat yozish, izohsiz summani «mayda kundalik» deb belgilash, yakunlash (hisobot o'zgarmas saqlanadi). Klaviatura bilan bajariladi: birinchi boshqaruv fokusda, Enter tasdiqlaydi, Esc orqaga.
  - «Kimning puli?»: oy bo'yicha o'tish, egalar bo'yicha bo'laklar.
  - «Majburiyatlar va nasiya»: doimiy to'lovlar (qo'shish, o'chirish), nasiya (qo'shish, qisman to'lash, qoldiq).
  - i18n: uz va ru; xato kodlari `errors.*` orqali matnga aylanadi.

**Qarorlar va sabablar**

- **Yozuvlarda kalendar sanasi, vaqt emas.** Odat va audit kun darajasida hisoblanadi; Toshkent vaqti (UTC+5) konvertatsiyasi unit testda. Mobil ilova instant saqlaydi — natija bir xil, chunki hafta chegarasi kun darajasida.
- **Ulush taklifi:** foiz bo'yicha `percent_of`, so'ng 1 000 so'mgacha (kichik summada — butun so'mgacha) yuqoriga, daromaddan oshmaydi. Mobil `suggestShare` bilan bir xil; `income_share.json` bilan tasdiqlangan.
- **Pul olish: har safar PIN.** Mobildagi 1 daqiqalik PIN ruxsat tokeni o'rniga, PIN buyruqning o'zida qayta tekshiriladi (noto'g'ri urinish `security` da hisoblanadi). Soddaroq va xavfsizroq; tasdiq kerak (OPEN_QUESTIONS, 25-band).
- **Oy yakuni** = `daromad − (yozilmagan majburiyat + xarajat + sof jamg'arma)`. Mobil ta'rifi bilan bir xil, izohsiz summa bilan bir xil formula (OPEN_QUESTIONS, 28-band).
- **Xarajat kanali:** `expenses.channel` ustuni majburiy, domen modelida kanal yo'q — hozircha `CASH`. D6 da qo'shiladi (OPEN_QUESTIONS, 23-band).
- **Bitta xonadon, bitta egasi a'zo («O'zim»).** Oilaviy rejim (2+ a'zo) D6 da (OPEN_QUESTIONS, 24-band).
- **ID — UUIDv7** (`uuid` crate, ADR: `uuid` v7; `fast-rng` tasodifiy qism uchun). `time` (formatting, parsing, macros) va `thiserror` src-tauri'ga qo'shildi — ikkalasi ham ish joyida allaqachon bor.
- **`zeroize`** storage crate'ga to'g'ridan-to'g'ri bog'landi (`PRAGMA key` satrini tozalash); versiya `security` bilan bir xil.
- **Sxema v2 — faqat qo'shish.** Eski v1 migratsiyasi o'zgartirilmadi; yangi ustunlar `DEFAULT` yoki `NULL` bilan.
- Testlar uchun `security` temp papkalari endi tugagach o'chiriladi (D3 da qolib ketgan).

**Natijalar**

- `cargo test --workspace`: 148 ta test — yashil. D4 ga oid: `baraka-money` (parse, ceil), `baraka-domain` (calendar, habit, share, vault, ledger, debt va boshqalar), `baraka-vectors` (8 suite), `baraka-storage` (v1→v2 migratsiya, daromad → ulush bog'liqligi, cheklovlar, hisobot bir marta), `baraka-daftari` (oqimlar: daromad → ulush → balans, pul olish, ro'molcha, audit).
- `cargo clippy --workspace --all-targets -D warnings`, `cargo fmt --check` — toza.
- Frontend: `pnpm test` 22 ta — yashil (ilova qobig'i, xavfsizlik, tez daromad, pul olish pauzasi va PIN, audit klaviatura oqimi, «Kimning puli?» bo'laklari, bosh sahifa). `lint`, `typecheck`, `format:check` — toza.
- Haqiqiy ilovada qo'lda sinov (ishlab chiqish rejimi, ekran suratlari bilan):
  - sozlash → bosh sahifa;
  - `Ctrl+N`: 150 000 → taklif 8 000 → Enter bilan ajratish → bosh sahifada «O'zingizga to'langan» 8 000, «Kelajagim» 8 000, «Oy yakuni» 142 000, odat 1 hafta;
  - «Kelajagim»: ro'molcha 100 000 (kartochka yo'qoladi, bir marta); pul olish — noto'g'ri PIN xabari va maydon tozalanishi, so'ng to'g'ri PIN bilan 30 000 «Dori» tarixda;
  - audit: klaviatura bilan 4 qadam (Enter, Enter, Tab-Enter, Enter), «Ijara» 5 000 yozildi, yakunlandi — «Audit yakunlangan» holati;
  - «Kimning puli?» — izohsiz bo'lak; «Majburiyatlar va nasiya»: nasiya 200 000 qo'shildi, 50 000 to'landi — qoldiq 150 000;
  - ruscha til: bosh sahifa va yon panel to'g'ri ko'rinadi.

**Ma'lum cheklovlar**

- Audit izohsiz summa bilan yakunlanishi mumkin (majburiy tanlov yo'q) — OPEN_QUESTIONS, 22-band.
- Pul olish va boshqa yozuvlarning qayta ishga tushirishdan keyingi saqlanishi D4 da alohida tekshirilmadi (baza D3 da sinalgan).
- Oylik kun (`month_start_day`) sozlamasi UI'da yo'q; standart — 1.
- Nasiya minimal: foiz, tilxat va friction D9 da.
- Daromad `source_type` (TER/MOL/TAVAKKAL/RIBO) ustuni ishlatilmaydi — ribo filtri D8 da.

### D3 — Xavfsizlik va shifrlangan baza (2026-10-14)

**Qo'shildi**

- `crates/domain` (paket `baraka-domain`): `Household`, `Member`, `MemberRole` (ADULT/CHILD), `Meta` (yaratilgan/yangilangan/o'chirilgan vaqt, `version`, `origin_device_id`), `validate_name`, `validate_uuid_v7`, `Clock` va `IdGen` traitlari.
- `crates/security` (paket `baraka-security`):
  - 6 raqamli PIN. Baza kaliti tasodifiy 256 bit; u ikki qatlamda o'raladi: ichki qatlam PIN'dan Argon2id bilan (19 MiB, t=2, p=1), tashqi qatlam OS keyring'idagi qurilma kaliti bilan. Ikkala qatlam XChaCha20-Poly1305.
  - Kalit fayli `keys.bin` (208 bayt, `BDKEY001`), atomik yoziladi.
  - Lockout: 3-urinishdan keyin 30 s, 4 — 60 s, 5 — 5 daqiqa, 6 — 15 daqiqa, 7 va undan keyin 1 soat. Keyring kaliti yo'q bo'lsa, urinish hisoblanmaydi.
  - `AutoLockPolicy`: oyna fokusdan tushib 5 daqiqa o'tsa, qulflash.
- `crates/storage` (paket `baraka-storage`): SQLCipher bilan shifrlangan baza (`PRAGMA key` 256 bit hex). Sxema v1 — `rusqlite_migration` bilan (`user_version`), 11 ta `STRICT` jadval, CHECK cheklovlari (masalan, `WITHDRAWAL` uchun sabab majburiy). `HouseholdRepo`, `MemberRepo` — mantiqiy o'chirish va optimistik versiya nazorati. Vaqt — RFC 3339, UTC.
- `src-tauri`:
  - `session` moduli: qulflangan/ochiq holat, PIN bilan ochish, qulflash, avto-qulflash. Tauri'dan mustaqil.
  - Commandlar: `get_security_status`, `setup_pin`, `unlock`, `lock`. Xato — `ApiError` (`code`, `retryAfterSeconds`); PIN yoki kalit qiymati hech qachon xatoda yoki logda bo'lmaydi.
  - Relizda oyna ekran suratidan chiqariladi (`set_content_protected`). Ishlab chiqish rejimida o'chiq.
  - Ma'lumotlar papkasi: `%APPDATA%\uz.barakadaftari.desktop` (`keys.bin`, `daftar.db`).
- UI: `SecurityGate` (avval PIN sozlash, keyin qulflash, keyin ilova), `SetupScreen` (PIN ikki marta kiritiladi), `LockScreen` (Enter bilan yuboriladi, noto'g'ri PIN xabari, lockout sanog'i), yon paneldagi «Qulflash» tugmasi va `Ctrl+L`. Tarjimalar uz va ru'da. Yangi rang tokeni `--color-danger`.

**Qarorlar va sabablar**

- **Ikki qatlamli o'rash** (DESKTOP_PROMPT.md 6.2): faqat PIN ham, faqat keyring ham yetarli emas. Keyring yozuvi o'chirilsa, PIN to'g'ri bo'lsa ham baza ochilmaydi.
- **Tartib:** format → lockout → keyring → PIN. Keyring kaliti yo'q bo'lsa, bu tizim xatosi: PIN tekshirilmaydi va urinish hisoblanmaydi.
- **Keyring nomi:** xizmat `BarakaDaftari`, hisob `db-device-key-v1` (Windows'da `db-device-key-v1.BarakaDaftari`).
- **`retryAfterSeconds` — `u32`:** specta TypeScript'da 64-bitli butun sonlarni (`bigint`) taqiqlaydi. Kutish bir soatgacha bo'lgani uchun u sig'adi.
- **Commandlar `async`:** Argon2id (bir necha yuz millisekund) UI oqimini bloklamasligi uchun `spawn_blocking` ichida bajariladi.
- **Sozlash bazani ochadi:** PIN kiritilgach yangi o'rnatishda ilova darhol ochiladi.
- **Ekran surati:** Windows bu oynani ekran suratidan chiqarib tashlaydi (`WDA_EXCLUDEFROMCAPTURE`, affinity `0x11`). Qora to'rtburchak chiqmaydi — oyna ortidagi oyna ko'rinadi. Eski Windows'da xulq boshqacha bo'lishi mumkin (tekshirilmagan).
- **Windows'da SQLCipher'ni yig'ish** to'liq Perl'ni talab qiladi (OpenSSL Configure). Git bilan kelgan perl yetmaydi; `OPENSSL_SRC_PERL` bilan ko'rsatiladi (README).

**Bog'liqliklar va sabablari** (ADR bo'yicha, DESKTOP_PROMPT.md 2-bo'lim)

- `argon2` 0.6 — PIN'dan kalit (Argon2id).
- `chacha20poly1305` 0.11 — AEAD (XChaCha20-Poly1305), `zeroize` xususiyati bilan.
- `keyring` 4.2 — OS xavfsiz saqlash (Windows Credential Manager).
- `rand` 0.10 — tasodifiy sonlar (OS manbai).
- `zeroize` 1.9 — kalit xotirasini tozalash (`security` va `storage`).
- `rusqlite` 0.40, `bundled-sqlcipher-vendored-openssl` — SQLCipher; `rusqlite_migration` 2.6 — migratsiyalar.
- `time` 0.3, `thiserror` 2 — vaqt va xatolar (`src-tauri` ham `thiserror` ishlatadi).
- Ichki bog'liqliklar: `src-tauri` → `baraka-security`, `baraka-storage`.

**Natijalar**

- `cargo test --workspace`: yashil. D3 testlari: `baraka-domain` 5; `baraka-security` 15 (unit) + 9 (integratsiya: PIN+keyring ikki qatlam, keyring yo'qolganda PIN yetmasligi, lockout, avto-qulflash); `baraka-storage` 8 (shifrlangan fayl kalitsiz o'qilmaydi, noto'g'ri kalit rad etiladi, migratsiya v1, versiya nomuvofiqligi, tashqi kalit, CHECK); `baraka-daftari` 12 (seans 7, commandlar 4, bindinglar 1).
- `cargo clippy --workspace --all-targets -D warnings`, `cargo fmt --check` — toza.
- Frontend: `pnpm test` 17 ta — yashil (App 5, xavfsizlik oqimlari 6, ikonka siyosati, tarjima kalitlari); `lint`, `typecheck`, `format:check` — toza.
- Haqiqiy ilovada qo'lda sinov (ishlab chiqish rejimi, sichqoncha va klaviatura, har bir ekran suratga olingan):
  - sozlash: PIN ikki marta, «Saqlash va boshlash» — bosh sahifa ochildi;
  - «Qulflash» tugmasi va `Ctrl+L` — qulflash ekrani;
  - noto'g'ri PIN — xabar, maydon tozalanadi, ilova qulflangan qoladi;
  - uchinchi noto'g'ri urinish — 30 soniyalik kutish, sanoq, maydon va tugma o'chiq; sanoq tugagach maydon qayta yoqildi;
  - to'g'ri PIN — ilova ochildi;
  - oyna 5 daqiqa fokusdan tashqarida (minimallashtirilgan) — qayta ochilganda qulflash ekrani;
  - ilova qayta ishga tushirildi — qulflash ekrani (kalit fayli va keyring saqlangan), to'g'ri PIN bilan ochildi;
  - keyring yozuvi Windows Credential Manager'dan o'chirildi — to'g'ri PIN ham ochmadi: «Qurilma kaliti topilmadi» xabari.
- Reliz exe (`target\release`, o'rnatilmagan): ekran surati oyna mazmunini chiqarmadi (yuqoridagi qaror).

**Ma'lum cheklovlar**

- PIN unutilsa, ma'lumotlarni tiklash yo'q (docs/OPEN_QUESTIONS.md, 15-band).
- Windows Hello yo'q (kechiktirildi, 16-band). OS qulflash hodisasi (Win+L, uyqu) aniqlanmaydi, faqat oyna fokusi va vaqt (17-band).
- PIN JS tomonida qisqa vaqt matn sifatida turadi; Rust tomonda `zeroize` qilinmaydi (Tauri deserializatsiyasi `String` beradi).
- Kalit fayli o'chirilib, `daftar.db` qolsa, sozlash eski bazani ochishga urinadi va `INTERNAL` xato beradi (18-band).
- O'rnatuvchi (NSIS) bu vazifada qayta qurilmadi va o'rnatilmadi; silent o'rnatish va o'chirish sinalmagan (19-band).

### D2 — `money` crate va test vektorlari runner'i (2026-10-14)

**Qo'shildi**

- `crates/money` (paket `baraka-money`, kodda `money`):
  - `Money` — butun minor birliklar (tiyin, sent) va valyuta; `checked_add`/`checked_sub` valyuta aralashuvini va chegaradan oshishni xato bilan qaytaradi.
  - `Currency` — UZS, USD, EUR, RUB; minor birlik ikki xonali.
  - `round_half_up_div` — loyihadagi yagona yaxlitlash joyi (yarmi noldan uzoqqa).
  - `allocate` — largest remainder usuli: qismlar yig'indisi aniq teng, teng kasrda kichik indeks ustun, manfiy summa simmetrik.
  - `percent_of` — basis points (1 % = 100 bp) bo'yicha foiz.
  - `FxRate` + `convert` — kurs kasr sifatida (`rate_num / rate_den`), yarmi noldan uzoqqa yaxlitlanadi.
  - `format_money` — `uz` va `ru` lokallari: guruhlash bo'linmas bo'sh joy bilan, kasr faqat tiyin nolga teng bo'lmasa, `soʻm` (U+02BB) / `сум`, `$`, `€`, `₽`.
  - `MoneyError::code()` — barqaror kodlar (`CURRENCY_MISMATCH`, `OVERFLOW` va hokazo).
- `crates/vectors` (paket `baraka-vectors`, kodda `vectors`):
  - suite yuklovchi: `spec/test-vectors/*.json` ni o'qiydi;
  - pul runner'lari: `allocate` (5 ta), `percent_of` (2 ta), `fx_convert` (5 ta), `money_format` (8 ta) — jami 20 ta vektor. Har bir natija `expected` bilan TO'LIQ solishtiriladi;
  - qoplanmagan vektor fayli bo'lsa, `har_bir_vektor_fayli_runner_bilan_qoplangan` testi qizil bo'ladi.
- `spec/test-vectors/` — to'rtta D2 suite (`allocate`, `percent_of`, `fx_convert`, `money_format`) mobil repo'dagi fayllarning bayt-bayt nusxasi (sha256 mos).
- Xususiyat testlari (proptest, har biri 256 ta tasodifiy holat): taqsimot yig'indisi aniq teng; ishora saqlanadi; har bir qism aniq ulushdan bir minor birlikdan ko'p og'maydi; nisbati nol bo'lgan qism nolga teng; `percent_of` = `allocate([bp, 10000 − bp])[0]`; yaxlitlash simmetrik.
- CI: alohida «Pul vektorlari» qadami va `coverage` job (`baraka-money` qamrovi ≥ 95 %).
- README: tekshiruv buyruqlari va qamrov o'lchash.

**Natijalar**

- Testlar: 32 ta unit, 6 ta xususiyat, 5 ta runner — hammasi o'tdi.
- Qamrov: `baraka-money` satrlari 99,80 % (talab ≥ 95 %).
- Mutatsiya sinovi: tie-break qoidasi ataylab buzildi — `alloc-001`, `alloc-003`, `alloc-004` qizil bo'ldi. Qoida qaytarilgach, hammasi yana yashil.
- `cargo fmt --check`, `clippy -D warnings`, Prettier — toza.

**Qarorlar va sabablar**

- **Yaxlitlash — yarmi noldan uzoqqa, manfiy uchun ham.** Vektor `fx-004` talab qiladi: −12 650,5 → −12 651. Mobil `MoneyRounding.defaultMode` bilan bir xil.
- **Manfiy summa.** `allocate` modulni taqsimlaydi va ishorani qo'yadi (`dist-003`: −300 000 000 kapital bo'yicha → −225 000 000 / −75 000 000).
- **`percent_of` oraliqdan tashqarida** (masalan, 120 % ustama): `round_half_up(amount × bp / 10 000)`. Desktop spec'da bu holat yo'q; mobil ilova xuddi shunday qiladi. 0..=10 000 oralig'ida ikkala ta'rif teng — xususiyat testi buni tasdiqlaydi.
- **Vektorlar nusxasi.** Ikki repo bitta vektor to'plamini ishlatadi (DESKTOP_PROMPT.md 5.1). Hozircha nusxa; sinxronlash usuli ochiq (docs/OPEN_QUESTIONS.md, 2-band).
- **Bog'liqlik yo'nalishi.** `money` vektorlarga bog'lanmaydi; runner `vectors` da. Shu sababli tsikl va ikki nusxadagi tiplar yo'q.
- **Yangi crate'lar** (ADR bo'yicha sabablari): `thiserror` — xatolar (ADR: xatolar); `time` — `FxRate.date` kurs sanasi (ADR: sana); `proptest` — xususiyat testlari (ADR: testlar); `serde`, `serde_json` — vektor JSON'ini o'qish (faqat `vectors`).
- **Vositalar.** `cargo-llvm-cov` — qamrov o'lchash (bog'liqlik emas, CI'da o'rnatiladi).

**Hali yo'q (keyingi bosqichlar)**

- Kiritilgan matnni summaga aylantirish (`MoneyParser`) — D4 (forma kiritish) da.
- `Money` DTO (`{ minor: string, currency, formatted }`) — `src-tauri` commandlarida, D4 da.
- Qolgan 10 ta vektor suite'i (`amortization`, `personal_inflation`, `emergency_target`, `readiness_gate`, `journal_chain`, `profit_spike`, `profit_distribution`, `agreement_completeness`, `debt_recovery_split`, `unexplained_gap`) — mos vazifalarda runner bilan birga qo'shiladi.
- CODEOWNERS — vektor o'zgarishi ikki platforma egasining ma'qulligini talab qiladi (DESKTOP_PROMPT.md 5.4); egalar aniqlangach.

### D1 — Workspace, Tauri skeleti, CI (2026-10-14)

**Qo'shildi**

- Cargo workspace (Rust 1.97.1, `rust-toolchain.toml`) va pnpm workspace (pnpm 12.11.2, Node 24).
- Tauri 2.12 ilova skeleti (`src-tauri/`): asosiy oyna, `get_app_info` command, NSIS o'rnatuvchisi (`currentUser` — administrator huquqi shart emas).
- TypeScript bindinglari tauri-specta orqali (`ui/src/bindings/bindings.ts`). `cargo test` va debug ishga tushirish ularni yangilaydi; CI farqni tekshiradi.
- React 19 + TypeScript (strict) + Vite 8 + Tailwind CSS 4 + Radix UI (ToggleGroup, Tooltip) + i18next (`uz` asosiy, `ru`).
- Qorong'i tema (Claude Code desktop uslubi). Noto Sans shrifti ilova ichida — `ʻ` (U+02BB) va `ʼ` (U+02BC) belgilari to'g'ri chiqadi.
- Navigatsiya: 11 ta bo'lim. Tayyori ikkita — «Bosh sahifa» va «Sozlamalar». Qolganlari o'chirilgan, sababi (keyingi bosqichda qo'shiladi) tooltip'da ko'rsatiladi.
- Ilova ikonkasi: `scripts/make_icon.py` (Pillow) — krem «daftar» va geometrik sakkiz burchakli yulduz. 16–256 px uchun alohida chiziladi.
- Xavfsizlik: qat'iy CSP (`script-src 'self'`, tashqi manba yo'q), minimal capabilities (`core:default` va faqat `allow-get-app-info`), release'da DevTools yo'q.
- Testlar: Rust — 3 ta (JSON kontrakt, yig'ish profili, bindinglar). Frontend — 11 ta (ilova qobig'i, tooltip, til almashinuvi, xato holati, tarjima kalitlari bir xilligi, ikonka siyosati).
- CI (`.github/workflows/ci.yml`): frontend (format, lint, typecheck, test); Rust — Windows, macOS, Ubuntu (fmt, clippy `-D warnings`, test, bindinglar farqi); Windows NSIS build (artifact).
- Hujjatlar: `docs/SPEC.md`, `docs/DESKTOP_PROMPT.md`, `docs/MVP_PLAN.md`, `CLAUDE.md`, `README.md`, `docs/CHANGELOG.md`, `docs/OPEN_QUESTIONS.md`.

**Qarorlar va sabablar**

- **Tauri 2.12** (ADR). Tauri 3 alpha ishlatilmaydi.
- **TypeScript 6.0.3**, 7.0 emas: TypeScript 7 `typescript-eslint` bilan mos emas.
- **ESLint 10**, `eslint-plugin-jsx-a11y`siz: a11y plagini ESLint 10 bilan mos emas. A11y tekshiruvi Testing Library'ning rol bo'yicha so'rovlari orqali.
- **`common-controls-v6` o'chirildi** (`default-features = false`): test binary'lari `STATUS_ENTRYPOINT_NOT_FOUND` bilan yiqilardi. Ilova binary'si manifestni baribir oladi.
- **`style-src 'unsafe-inline'`**: Radix va popper komponentlari inline uslub qo'yadi. `script-src` qat'iy.
- **NSIS tillari**: `Uzbek`, `Russian`, `English`. NSIS 3.11 da `Uzbek.nlf` bor.
- **pnpm 12 minimal chiqarilish yoshi**: yangi chiqqan ikki paket (`lucide-react@1.56.0`, `@testing-library/user-event@14.6.8`) istisnoga qo'shildi (`pnpm-workspace.yaml`). Keyinroq tekshiriladi (docs/OPEN_QUESTIONS.md, 8-band).
- **Ikonkalarda** odam, hayvon, cho'chqa, qimor, alkogol, bank binosi va foiz belgisi ishlatilmaydi. Taqiq `icon-policy.test.ts` da tekshiriladi.

**Bog'liqliklar va sabablari**

- Rust: `tauri` 2.12, `tauri-build` (ilova build skripti), `tauri-specta` + `specta` (`=2.0.0-rc.25`, TS bindinglari — ADR), `specta-typescript` 0.0.12 (bindinglarni yozish), `serde` (DTO), `tracing` + `tracing-subscriber` (log — ADR), `serde_json` (faqat testlar).
- npm: `react`, `react-dom` 19 (ADR: React 18+); `vite` 8, `@vitejs/plugin-react`; `typescript` 6.0 (strict); `tailwindcss` 4 + `@tailwindcss/vite`; `@radix-ui/react-toggle-group`, `@radix-ui/react-tooltip` (ADR: Radix primitivlari); `i18next`, `react-i18next` (ADR); `@tanstack/react-query` (ADR); `zustand` (ADR: faqat UI holati); `@tauri-apps/api` (bindinglar uchun) va `@tauri-apps/cli` (ADR: Tauri); `lucide-react` (ikonkalar — ADR'da yo'q, qo'shildi, ikonka siyosati bilan); `@fontsource-variable/noto-sans` (shrift ilova ichida); `vitest`, `jsdom`, `@testing-library/*`; `eslint`, `typescript-eslint`, `eslint-plugin-react-hooks`, `globals`, `@eslint/js`; `prettier` (ADR).
- Python (faqat ikonka uchun): `Pillow`.

**Ma'lum cheklovlar**

- GitHub Actions CI hali GitHub'da ishga tushirilmagan: repo'da push qilinmagan. Uning qadamlari mahalliy Windows muhitida qo'lda takrorlangan.
- O'rnatuvchi kod imzolanmagan — SmartScreen ogohlantirishi chiqishi mumkin.
- Silent o'rnatish sinalgan (`/S`). Interaktiv o'rnatish va til tanlovi oynasi qo'lda sinalmagan.
- Haqiqiy oynada til almashinuvi tugmasi sichqoncha avtomatizatsiyasi bilan to'liq tasdiqlanmadi. Bu jsdom testlari bilan qoplangan; E2E (WebDriver) keyingi bosqichda.
- Mobil (Flutter) loyiha bu repo'da yo'q; `spec/test-vectors/` faqat to'rtta D2 suite'iga ega (docs/OPEN_QUESTIONS.md, 1–2-bandlar).
