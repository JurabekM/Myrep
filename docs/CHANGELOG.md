# O'zgarishlar jurnali

## [1.0.0] Reliz nomzodi — 2026-10-23

- Versiya `1.0.0+2` (0.1.0 sinov o'rnatmasi ustidan yangilanadi).
- `tools/build_release.ps1` endi APK'lar bilan birga Play uchun **AAB** ni yig'adi va hammasini `build/release/<versiya>/` ga to'playdi: har build'ning o'z `mapping` va Dart belgilari (zip), `SHA256SUMS.txt`; `-NoBundle` — faqat APK.
- Imzo hali debug kaliti — Play'ga yuklash uchun upload kaliti kerak (RELEASE_CHECKLIST 2 va 12-bo'lim).
- Sinov: `flutter test` 764 o'tdi, 4 o'tkazib yuborildi; emulyatorda 0.1.0 → 1.0.0 yangilanish ma'lumotni saqladi.

## [Rebrend] «Baraka Dastur», mustaqil kontent, yangi logotip — 2026-10-23

- **Nom:** «Baraka daftari» → **«Baraka Dastur»** («Барака Дастур»): Android yorlig'i, `appTitle`, biometrik oyna, onboarding, PDF meta va pastki yozuv, zaxira xabari. Sabab: Google Play'da moliya toifasida «baraka» nomli boshqa ilova bor. Nomda «Baraka» qolgani uchun adashtirish xavfi to'liq yo'qolmagan (OPEN, pastda).
- **Play identifikatori:** `applicationId` `uz.barakadastur.app`. Kotlin `namespace` (`uz.barakadaftari.app`), Dart paketi `baraka_daftari`, Pigeon kanallari va zaxira formati (`baraka-daftari-backup`) ichki — o'zgarmadi (eski zaxira fayllari tiklanadi). `adb`: `uz.barakadastur.app/uz.barakadaftari.app.MainActivity`.
- **Mustaqil kontent (SPEC v1.0, mustaqillik qarori):** barcha bob matnlari, maslahatlar va UI matnlarini loyiha jamoasi yozadi. Murabbiy — nomsiz «Maslahatchi» (`contentAdvisor`; bob ichidagi maslahat bloki shu belgi bilan). 7 bobning sarlavhalari SPEC qonun nomlaridan, matn va maslahatlar o'z so'zlarimiz bilan; diniy bloklar `PENDING` (ulamo tekshiruvigacha). 1-bobdagi «5 %» va «o'ndan bir» ziddiyati tuzatildi (progressiv rejim).
- **Atamalar (SPEC v1.0):** «Favqulodda zaxira» (ichki `VaultType.qorovul` / `QOROVUL` o'zgarmadi), «Inflyatsiya ta'siri», «Avval yig'ilgan pul», katta summa ekranida «Oilaviy zaxira», «9 ta asosiy savol», tayyorgarlik darvozasi «Avval tayyorgarlik, keyin sarmoya», «payvandlash ustaxonasi» shabloni; kelishuv maslahati kaliti `agAdvisorTip`. Iqtibos ko'rinishidagi iboralar o'z so'zlarimiz bilan qayta yozildi.
- **Logotip:** yashil gradient fonda krem «B» va tilla bug'doy boshog'i (to'kinlik ramzi; jonzot, tanga-quti, foiz belgisi yo'q). `tools/make_icon.py`: launcher (legacy + adaptive + monochrome), `assets/branding/logo.png` (qulf ekrani va onboarding — `BrandLogo`), Play uchun `tools/store/play_icon_512.png` va `feature_graphic_1024x500.png`. Desktop ham shu belgiga o'tdi.
- **Testlar:** test ma'lumotlaridagi ismlar desktop va umumiy vektorlar bilan bir xil shartli ismlar; E2E `integration_test/full_e2e_test.dart`, `full_scenario.dart`, `test/e2e/full_e2e_host_test.dart`. `spec/test-vectors/` dan `agreement_completeness`, `amortization`, `journal_chain` desktop nusxasi bilan almashtirildi (xeshlar Dart'da aynan). Yangi: `test/design/source_policy_test.dart` (ARB va kontentda tashqi manba nomlari, eski nom yo'q; yorliq va `applicationId`), `test/app/branding_test.dart`. Golden `loan_receipt.pdf` yangilandi (pastki yozuv).
- **Sinov natijasi:** `flutter test` — 764 o'tdi, 4 o'tkazib yuborildi; vektorlar 117/117; Kotlin JUnit 46/46; `flutter analyze --fatal-infos`, format, `uz_orthography --check` — toza; E2E (x64 release, emulyator) — «All tests passed!». Qurilma natijalari — RELEASE_CHECKLIST, 11-bo'lim.

## [Vazifa 14B] 7-qonun: besh xavf belgisi, oilaviy zaxira, «to'xta, maslahatlash», hunar shablonlari — 2026-10-20

- **SPEC v0.9** (2G): 7-qonun — firibgarlikdan himoya va hunarga sarmoya. 3-bo'limga yangi band: ilova hech qanday investitsiya platformasini reklama qilmaydi. SPEC 4.3: 7-qonun zakot haqida emas (OPEN 139). `MVP_PLAN.md` — **14B** vazifasi (18 vazifa); `DESKTOP_PROMPT.md` v1.2 — 7-qonun qatori va 4 yangi suite.
- **Besh xavf belgisi** (2G.1, `ScamSign`): taklif tekshiruviga 3 savol qo'shildi — pulni istagan vaqtda qaytarish, davlat ruxsati, o'z ko'zi bilan tekshirish. Baho: 1 belgi — hushyor (kamida sariq), 2+ — qoch (qizil), 2E.5 bilan eng og'iri. Natijada `RIBO | GHARAR | QIMOR` toifalari (2G.7). Saqlangan javoblarni o'qish noma'lum savol kodiga chidamli.
- **«O'z ko'zim bilan ko'raman»** (2G.2): taklif ekranida tekshiruv ro'yxati (ombor va mol, shartnoma, ruxsat, to'lov manbai, qaytarish tartibi).
- **Va'da qilingan foyda** (2G.3): oylik % → yiliga oddiy va murakkab ko'paytma (oyiga 35 % — 5,2 / 36,6 barobar), faqat ogohlantirish.
- **Piramida** (2G.4): `k` va aholi bo'yicha qavatlar va eng pastki qavat ulushi (k = 5, 1 mln — 10-qavatda, 51 % pastda).
- **Oilaviy zaxira** (2G.5): «Kelajagim» → «Katta summa tushdimi?» — summa (dollar bo'lsa, kurs bilan so'mga), avval 6 oylik zaxira kamomadi, qolgani hunarga; «Oilaviy zaxiraga qo'yish» qorovulga qo'yadi, «Hunardan ishga o'tish».
- **«To'xta, maslahatlash»** (2G.6): taklifda summa va maslahatchi; «pul qo'yaman» maslahatchi ismi yozilgach va tekshiruvdan 24 soat o'tgach ochiladi; «rad etdim» / «keyinga qoldiraman» darhol; yakuniy qaror o'zgarmaydi; tarixda qaror ko'rinadi.
- **Hunar shabloni** (2G.8): «Hunardan ishga»da temirchilik / payvand ustaxonasi — CAPEX nomlari tavsiya, summani foydalanuvchi yozadi; «talab bormi?» savoli.
- **Sxema v16**: `offer_checks` ga `amount_minor`, `currency`, `promised_monthly_bp`, `advisor`, `decision`, `decided_at` (hammasi ixtiyoriy); migratsiya testi — eski tekshiruvlar yo'qolmaydi.
- **Kontent**: 7-bob («Qopqon va hunar», placeholder) va haftalik vazifalar (`OFFER_CHECKED`, `EMERGENCY_TARGET_SET`, `VENTURE_IDEA_CREATED`).
- **Umumiy vektorlar** (DESKTOP_PROMPT 5.4 — avval vektor): `scam_signals` (8), `promised_return` (5), `pyramid_levels` (4), `lump_sum_split` (4) — mustaqil Python hisobi bilan bitma-bit.
- **E2E ssenariy**: Bekzod qadami — «Tez Foyda» taklifi qizil (4 belgi), maslahatsiz «pul qo'yaman» rad etiladi, rad etish yoziladi, oilaviy zaxira taqsimoti.
- **14A tuzatishi (qurilmada topilgan)**: yillik yangilash eslatmasi rejalashtirilmasdi. Sabablar: autoDispose `agreementsProvider.future` tinglovchisiz o'qilib, xato jim yutilardi; `AgreementService.create()` kelishuvning `reviewDate` ini o'rnatmasdi. Regressiya testi `renewal_reminders_test.dart` (tuzatishdan oldin ikkala sabab bilan yiqilgani tekshirilgan).
- **Siyosat testlari ushlagan**: `handyman` ikonkasida odam tasviri — `build` ga almashtirildi; ruscha matndagi «гарантированная прибыль» ribo filtriga tushdi — qayta yozildi.
- **Emulyatorda (release APK) topilib tuzatilgan**: (1) har «bilmayman» bayrog'i bir xil matn bilan takrorlanardi — endi qaysi savol ekanini aytadi (`offerFlagUnknown(question)`, widget testi); (2) oilaviy zaxirada zaxira maqsadi yo'q bo'lsa «avval belgilang» deyilardi-yu, joyi ko'rsatilmasdi — shu ekranda «Taxminiy summani kiritish» (`lump-estimate`, widget testi); (3) temirchilik shabloni nomi chip ichida kesilardi — qatorga o'raladigan tugma.
- **Qurilmada tasdiqlandi**: E2E (x64 release) «All tests passed!» — Bekzod qadami bilan; yillik yangilash ishi WorkManager'da (+334 kun, 2027-09-20 09:00) va `adb reboot`, qayta o'rnatish, `force-stop` dan keyin saqlanadi (RELEASE_CHECKLIST 10-bo'lim).
- **Sinov natijasi**: `flutter test` — 756 o'tdi, 4 o'tkazib yuborildi; `flutter analyze --fatal-infos` — toza; `uz_orthography --check` — toza.

## [Vazifa 14A] Vazifalar, oylik ko'rik, «katta foyda», nizo va hakam, oilaviy kelishuvlar — 2026-10-15

- **«Katta foyda» qoidasi** (`ProfitSpike`, SPEC 2F.7): `alert = actual > 0 && (A || B)`; vektor `spec/test-vectors/profit_spike.json` (ps-001…005) yashil. Sheriklikda reja maydoni yo'q, shuning uchun A sharti hozircha qo'llanmaydi, faqat oxirgi 3 yopilgan davr (B) — OPEN 129.
- **Jurnal turlari** (SPEC 2F.1 entitylari): `DUTY_INCIDENT`, `REVIEW_OPENED`, `REVIEW_ACK`, `ACCOUNT_REVIEW`, `PROFIT_SPIKE_ACK`, `DISPUTE_OPENED`, `ARBITER_DECISION`. Alohida jadval yo'q, sxema v15 o'zgarmadi; xesh-zanjir va append-only saqlanadi (OPEN 128).
- **«Bajarilmadi» oqimi** (2F.4): tomon sabab, sana va yechim bilan xabar beradi; shartnomaning tegishli bandi darhol ko'rsatiladi; hodisa jurnalga yoziladi va keyingi ko'rikda chiqadi.
- **Oylik ochiq ko'rik** (2F.5): ochish (kesim — bugun), har tomon «roziman» yoki «e'tiroz + izoh», bayonnoma `chainHead` bilan (`ReviewMinutesNote`). Bayonnomadan keyin o'sha davrga faqat tuzatuvchi yozuv (`assertWritable`, `ensureWritable`). `minutesIntact` o'zgartirilgan yozuvni aniqlaydi. Ekran: `review_screen.dart`.
- **Davrni yopish gate'lari** (`VentureLedgerService.closePeriod`): nizo ochiq bo'lsa — `IN_DISPUTE`, taqsimot to'xtaydi; ochiq ko'rik bo'lsa davr yopilmaydi; «katta foyda»da ikkala tomon tasdiqlamaguncha taqsimot o'tmaydi (`ProfitSpikeDialog`, uz/ru matnlari ARB'da).
- **Nizo va hakam** (2F.8): nizo ochish, boshqa tomon talabi, hakam qarori (kelishuv `ACTIVE` ga qaytadi; matn o'zgarsa — «Yangi versiya» orqali qayta imzo, OPEN 135). Hakam papkasi PDF (`buildArbiterFolderPdf`): kelishuv va versiyalar, tomonlar, hisob yozuvlari va zanjir tekshiruvi, bayonnomalar, hodisalar, ikki tomon talabi, hakam qarorlari, zanjir boshi.
- **Yillik yangilash**: «o'zgarishsiz tasdiqlash» — yangi versiya, qayta imzo, `reviewDate` bir yilga suriladi. Eslatma `reviewDate` dan 30 kun oldin, 09:00 (Asia/Tashkent): Kotlin `AgreementRenewalWorker` (WorkManager, bir martalik, `REPLACE`), Pigeon `scheduleAgreementRenewal` / `cancelAgreementRenewal`; `syncAgreementRenewals` bosh ekran ochilganda chaqiriladi.
- **Oilaviy kelishuv** (2F.10): `FAMILY` turi uchun 4 shablon (sarlavha va izoh), hakam ixtiyoriy. Shablonlar javoblarni oldindan to'ldirmaydi (OPEN 131); oila a'zolari imzosi keyingi bosqich (OPEN 132). Yaratishda `FAMILY_AGREEMENT_CREATED`.
- **Kelishuvlar markazi**: ro'yxatda keyingi ko'rik sanasi, ochiq hodisalar va nizolar soni (`agreementCenterProvider`). Bosh ekranda «Yaqinlashayotgan ko'rik / yangilash» kartasi (`AccountabilityHomeCard`, slot 155).
- **Kelishuv ekrani**: «Bajara olmayapman» tugmalari, ko'rik kartasi, nizolar kartasi, yillik yangilash (`accountability_section.dart`); eski `ag-renew-unchanged` shu bo'limga ko'chdi.
- **Kontent**: 6-bob («Sheriklik odobi»), placeholder tana matni bilan; 6-qonun jumlasi qoralama (OPEN 130). `ACCOUNT_REVIEW_COMPLETED` va `FAMILY_AGREEMENT_CREATED` triggerlari (`TaskTrigger`, `docs/content_schema.json`).
- **Tozalash**: `LoanReceiptService.addWitness`/`remove` olib tashlandi (ishlatilmagan); `percentLabel`/`parsePercentBp` `app/widgets/labels.dart` ga ko'chirildi (OPEN 111); bo'sh `lib/features/offers/` va `lib/features/ventures/` papkalari o'chirildi (OPEN 112). Tilxatdagi `loanReceiptService.signers()` qoldi: lender/borrower rollarini yaratadi (OPEN 136).
- **Testlar**: yangi — `accountability_test` (8), `venture_gates_test` (4), `accountability_pdf_test` (3), `review_flow_test` (1, widget), `profit_spike` vektor (5). Yangilangan — `agreement_flows_test` (ekran uzaygani uchun `reveal` boshidan qidiradi), `content_test` (6 bob), `home_slots_test` (yangi karta).
- **Sinov natijasi**: `flutter test` — 710 o'tdi, 4 o'tkazib yuborildi, 0 yiqildi; `flutter analyze` — toza; `uz_orthography --check` — toza; `dart format` — o'zgargan fayllar toza.
- **Hali bajarilmagan**: release APK qurilmada to'liq sinovi (foydalanuvchi, `docs/RELEASE_CHECKLIST.md` 10-bo'lim); emulyatorda yillik eslatmaning qayta yoqilgandan keyin saqlanishi — natija 10-bo'limda.

## [Release sinovi, 2-bosqich] Qarorlar, zaxira tuzatishi, toʻliq sinov — 2026-10-14

- **Zaxira (kritik tuzatish)**: uy xoʻjaligi yoʻq (boʻsh) yuk endi oʻchirishdan oldin rad etiladi (`BackupService.import`). Avval toʻgʻri parol bilan boʻsh faylni tiklash butun bazani oʻchirardi. Regressiya testi: `backup_test.dart`.
- **Tilxat va kelishuv — bitta imzo manbai** (OPEN 116): tilxat ekrani kelishuv oʻzgarishini kuzatadi (`ref.listen`), imzo va guvoh qoʻshilgach kelishuv ekrani yangilanadi; guvoh kelishuv javoblariga yoziladi (`saveAnswers`); imzolangan tomon qayta imzolamaydi (`AgreementService.errAlreadySigned`, uz/ru).
- **Bob sarlavhalari** (OPEN 119): `chapters.json` dan «(placeholder)» belgisi olib tashlandi; tana matnidagi «[Placeholder]» belgilari qoldi.
- **Xarajat suring bilan oʻchirish** (OPEN 120): «Xarajat oʻchirildi.» SnackBar'i va «Bekor qilish» (`ExpenseRepository.restore`, `SyncedRepository.restoreDeleted`). «Oxirgisini takrorlash» tasdiqsiz qoldi (SnackBar'idagi «Bekor qilish» bilan).
- **Yaxlitlash** (OPEN 121, qaror: yuqoriga): qorovul qayta toʻldirish rejasi butun soʻmgacha yuqoriga yaxlitlanadi (kasrli soʻm chiqmaydi); SPEC 2.2 ga qoida yozildi. Testlar: `reserve_test.dart` (5 000 / 6 → 834).
- **Buyout toʻlovlari** (OPEN 123, qaror: alohida joy): sherikchilik ekranida «Buyout toʻlovlari» kartasi (`_BuyoutHistoryCard`).
- **Sinov natijasi**: `flutter test` — 689 oʻtdi, 5 oʻtkazib yuborildi; `flutter analyze --fatal-infos` toza; E2E `full_e2e_test.dart` (shifrlangan zaxira → 1:1 tiklash) va `encrypted_db_test.dart` — release x64, «All tests passed!». Qurilmadagi natijalar: `docs/RELEASE_CHECKLIST.md`, 9-bo'lim.

## [Release sinovi] Qurilma sinovidan keyingi tuzatishlar — 2026-10-14

- **Kelishuv muharriri** (`question_editor.dart`): ulush (4-savol), hisob (6-savol), chiqish (7-savol) va muddat maydonlari build vaqtidagi nusxadan emas, joriy holatdan o'qiydi — bitta sessiyada yozilgan matnlar bir-birini o'chirmaydi. Chiqishdagi raqam maydoni bo'shatilsa, «yo'q» deb saqlanadi.
- **Sherikchilik imzosi**: imzolangan tomon qayta imzolay olmaydi. «Imzolash» tugmasi imzolangan qatorda yashirildi; servis imzoni bazadan tekshiradi va `partnership_already_signed` bilan rad etadi (uz/ru matnlari ARB'da).
- **Integratsiya testi** (`integration_test/encrypted_db_test.dart`): kategoriya kutilmasi `CategoryKey.values.length` ga o'tkazildi (13 ta; 11 ta kutilma v6 dan oldingi holat edi). Qurilmada «All tests passed!» (+8).
- Testlar: `flutter test` — 686 o'tdi, 5 o'tkazib yuborildi (9A dan beri +4). Yangi: `question_fields_test.dart` (3 test; tuzatishsiz muharrirda uchalasi yiqilishi tekshirildi), `partnership_test.dart` (qayta imzo rad etilishi), `partnership_flows_test.dart` (imzolangan qatorda tugma yo'q). `flutter analyze --fatal-infos`: toza.
- Qurilmada qayta tekshirildi (release arm64, emulyator): 4-, 6-, 7-savol — PASS; sherikchilik imzolangan tomonlarida tugma yo'q — PASS.
- Ochiq qarorlar (kodga kirmadi): OPEN_QUESTIONS 116, 119, 120, 121, 123; reliz kaliti (122).

## [Vazifa 9A] Kelishuv dvigateli (9 savol) va append-only jurnal — 2026-10-13

- **`Agreement`** (SPEC 2F.1): turlar `PARTNERSHIP | LOAN | RENT | SERVICE | FAMILY | OTHER`, holatlar `DRAFT → SIGNED → ACTIVE → (IN_DISPUTE) → CLOSED`, `effectiveFrom` (og'zakida — o'tmishda), `reviewDate`; **versiyalar** (`agreement_versions`) — imzolangan versiya o'zgarmaydi, har o'zgarish yangi versiya va qayta imzo; yillik yangilash «o'zgarishsiz tasdiqlandi» ham yangi versiya.
- **9 savol** (SPEC 2F.2): tomonlar, hissalar, vazifalar (**yagona mas'ul** + «bajarilmasa» bandi), foyda (faqat bp), zarar, hisob (qayerda, kim yuritadi, ko'rik davriyligi — oyiga 1 martadan siyrak bo'lsa ogohlantirish), chiqish, hakam (tomonlardan biri bo'la olmaydi), muddat. «Tegishli emas» — izoh majburiy. **To'liqlik «N / 9»**, 9/9 bo'lmaguncha imzolash yopiq. Tur bo'yicha strategiya: `LOAN` — 3-savol = qaytarish jadvali, 4–5 = «foiz yo'q»; `PARTNERSHIP` — 2E.1 (qat'iy summa taqiq, 100 %); `FAMILY` — hakam ixtiyoriy.
- **Imzolar** `PARTY | WITNESS | ARBITER` (yangi `SignerRole.arbiter`) shu qurilmada; hakam ham imzolaydi. Imzolashdan oldin javob o'zgarsa imzolovchilar ro'yxati moslanadi.
- **Append-only jurnal** (SPEC 2F.6): `journal_entries`, `UPDATE`/`DELETE` — **DB triggeri** (`RAISE(ABORT)`), repozitoriyda faqat `append`; tuzatish — `CORRECTION` yozuvi. **Xesh-zanjir**: RFC 8785 JCS + SHA-256, `hash = SHA256(prevHash + "\n" + JCS(entry))`, genesis 64 ta `0`, har kelishuvning o'z zanjiri; `verifyChain` birinchi buzilgan yozuvni qaytaradi. `journal_chain.json` vektorining 3 xeshi va salbiy holati yashil (desktop bilan bitma-bit).
- **Refaktor (MVP_PLAN 1-bo'lim 6-band)**: qarz tilxati = `Agreement(LOAN)`, sheriklik shartnomasi = `Agreement(PARTNERSHIP)`; qarz va bergan qarz to'lovlari, kapital, kassa daftari yozuvlari (o'chirish — teskari tuzatish), davr taqsimoti va buyout jurnalga yoziladi. Sheriklik va tilxat 9/9 siz imzolanmaydi; ekranlarida «Kelishuv: N / 9» kartasi.
- **Migratsiya v14 → v15**: 9A dan oldingi tilxatlar (`loan_signers` dagi hujjatlar) va sheriklik shartnomalari `Agreement` ga ko'chiriladi — **versiya ID si = eski hujjat ID si**, imzolar ko'chirilmasdan joyida; mavjud to'lovlar, kapital, kassa yozuvlari va taqsimot sana tartibida jurnalga (xesh-zanjir bilan); `legacy` — oldin imzolangan hujjat o'z kuchida. Faqat xom SQL.
- **Og'zaki kelishuvni yozib olish** (SPEC 2F.9): o'tgan sanadan, «shu kungacha holat» — `OPENING_BALANCE` jurnal yozuvlari, so'ng 9 savol va imzo.
- **UI**: «Kelishuvlar» bo'limi (bosh sahifa), kelishuv ekrani (N/9, savol muharrirlari, Maslahatchi maslahati, imzolar, faollashtirish, yangilash, jurnal va zanjir holati, **kelishuv PDF'i** — 9 bo'lim oddiy tilda, zanjir boshi, imzolar), og'zaki kelishuv ustasi. Hodisalar: `AGREEMENT_SIGNED`, `ORAL_AGREEMENT_RECORDED`.
- **Umumiy vektorlar**: `agreement_completeness.json` (15 holat — egasiz vazifa, «bajarilmasa»siz, hakam-tomon, izohsiz «tegishli emas», qat'iy summa, 90 % ulush, bitta tomon, hissasiz tomon, qarz va oila soddalashtirishlari, siyrak ko'rik — ogohlantirish).
- **Zaxira**: import jurnalni faqat bitta tranzaksiya ichida ochadi (`withJournalUnlocked`), keyin trigger yana faol.
- **Sxema v15**: `agreements`, `agreement_versions`, `journal_entries` (+ trigger va `journal_guard`). Bog'liqlik: `crypto` (dev → asosiy).
- Testlar: 682 Dart (+ vektor: jurnal 2, to'liqlik 15; servis 6 — ijara hayot sikli, imzolovchilar moslashi, og'zaki, tuzatish va buzilishni aniqlash, tilxat jurnali, sheriklik 9/9 va versiya; UI 3; migratsiya v14→v15 ma'lumot bilan; zaxira jurnal bilan; E2E: shartnoma 9/9 va jurnal), 46 Kotlin.

## [v0.8 tayyorgarlik] Umumiy oltin test vektorlari, half-up yaxlitlash — 2026-10-13

- **`spec/test-vectors/`** (DESKTOP_PROMPT.md 5): 13 suite — `allocate`, `percent_of`, `amortization` (amort-001…003, to'liq oyma-oy jadval), `profit_distribution` (dist-001…004), `emergency_target`, `personal_inflation`, `unexplained_gap`, `readiness_gate` (16 holatli to'liq matritsa), `debt_recovery_split`, `fx_convert`, `money_format`, `journal_chain` (spec xeshlari, Python bilan tasdiqlangan) va `profit_spike`. Runner `test/vectors/vectors_test.dart` har case'ni to'liq solishtiradi, noma'lum suite'da yiqiladi; jurnal va «katta foyda» — 9A / 14A gacha «kutilmoqda». CI'da alohida qadam.
- **Yaxlitlash half-up** (`MoneyRounding.defaultMode`, avval `halfEven`); **`percentOf = allocate([bp, 10000 − bp])[0]`** — 12 345 ning 10 % i endi 1235 (avval 1234). Bu barcha ulush va kurs hisoblariga taalluqli (yarim tiyinli holatlarda 1 tiyin farq).
- **Zaxira maqsadi** spec bo'yicha `round_half_up(Σ × 6 / k)`: avval o'rtacha so'mgacha yaxlitlanib, keyin 6 ga ko'paytirilardi (vektorda 31 000 000 o'rniga 31 000 002 so'm chiqardi). `ReserveStatus` endi yig'indi va oylar sonini saqlaydi; «to'ldi» — balans ≥ maqsad.
- **Shaxsiy inflyatsiya** — og'irlikli o'rtacha: `round_half_up(Σ(w_i × bp_i) / Σw_i)`, og'irlik — bazaviy xarajat ulushi (desktop bilan bitta formula).
- Sof funksiyalar: `emergencyTarget`, `weightedInflationBp`, `gateLockReasons` (+ `GateState.reasons`), `unexplainedGap`.
- Amortizatsiya simulyatori o'zgarishsiz vektorlardan o'tdi; jadval spec algoritmining mustaqil Python hisobi bilan har oyda bir xil.
- Testlar: 648 Dart (+ 69 vektor case), 46 Kotlin. Mutatsiya tekshiruvi: `halfEven` ga qaytarilsa runner qizil.

## [Vazifa 15] Onboarding, shifrlangan eksport, accessibility, reliz — 2026-10-11

- **Onboarding** (PIN bilan 5 ekran, `/onboarding`): til (uz / ru), oila a'zolari (egasi ismi, katta / bola), **daromad turi** — kunlik naqd, buyurtma bo'yicha yoki oylik maosh (maosh kuni = oylik davr boshi), **faol qarz bormi** → «Qarzdan chiqish» (70/20/10) tushuntirishi va to'g'ridan-to'g'ri «Qarzlar» bo'limi. Router onboarding tugamaguncha boshqa bo'limlarni yopadi (`appRedirect`), «Zaxiradan tiklash» birinchi ekrandan ochiq. Mavjud foydalanuvchilar migratsiyada «onboarding tugagan» deb belgilanadi.
- **Daromad turiga moslashish**: bosh ekran tugmasi («Bugungi tushum» / «Buyurtma puli» / «Maosh»), tez daromad oynasining standart manbasi va kanali, **eslatma** (Kotlin WorkManager): kunlik — har kuni 20:00, buyurtma — shanba 20:00, maosh — maosh kuni 10:00; bildirishnomada summa yo'q. Sozlamalarda o'zgartiriladi.
- **Shifrlangan zaxira nusxa** (`/backup`, Sozlamalar va onboarding'dan): butun baza (52 jadval, qatorlar o'zgarishsiz, BLOB'lar bilan) JSON → gzip → Kotlin `BackupCipher`: **PBKDF2-HMAC-SHA256 (310 000) + AES-256-GCM**, sarlavha (`BRKD`, versiya, iteratsiya, tuz, IV) AAD. Parol ≥ 8 belgi, takror bilan; fayl `.bkd` ulashish oynasi orqali saqlanadi. Import: tizim fayl tanlagichi (o'zimizning `ACTION_OPEN_DOCUMENT`, Pigeon `pickBackupFile`), parol, almashtirishni tasdiqlash, so'ng **to'liq 1:1 almashtirish** (tashqi kalitlar oxirida `foreign_key_check`). Xatolar: noto'g'ri parol, boshqa fayl, boshqa sxema versiyasi — ma'lumot o'zgarmaydi.
- **Accessibility**: asosiy 9 ekran va onboarding uchun `androidTapTargetGuideline` (48dp), `labeledTapTargetGuideline`, `textContrastGuideline` testlari; 200 % shriftda toshib ketish yo'q; qulf ekrani katta shriftda aylantirib yetiladi.
- **Ishlash**: o'sib boradigan ro'yxatlar paginatsiyasi (`PagedList`, 30 tadan, «Yana ko'rsatish»): oy xarajatlari, qarz to'lovlari, kassa daftari, narx daftari. Sovuq start emulyatorda 2,0–2,4 s (o'rnatishdan keyingi birinchisi 4,2 s) — telefonda o'lchanadi.
- **Release hardening**: R8 (`isMinifyEnabled`, `isShrinkResources`), Dart `--obfuscate --split-debug-info` (`tools/build_release.ps1`), imzo konfiguratsiyasi **repodan tashqarida** (`BARAKA_SIGNING_PROPERTIES` / `-PsigningProperties`, yo'q bo'lsa debug kaliti). `docs/RELEASE_CHECKLIST.md`.
- **Yakuniy E2E** (`integration_test/full_e2e_test.dart`, host varianti `test/e2e/`): Akmal ssenariysi ilova provayderlari orqali — daromad → ulush → audit → havas chegarasi (ikki katta rozi) → obuna bekor → qutqarilgan pul «Kelajagim»ga → avtokredit 39 mln → 70/20/10 → payoff (+2 mln/oy: 9 oy, 2 432 340,42 so'm tejash) → qarz yopilishi → qorovul to'lib darvoza ochilishi → musharaka shartnomasi (imzo, chetlab o'tmasdan faollashuv) → davr taqsimoti (3 mln uy daromadiga) → shifrlangan zaxira va boshqa bazaga 1:1 tiklash.
- **Sxema v14**: `households.onboarded_at`, `households.income_kind`; migratsiya testlari v13→v14 va v1→v14. Pigeon: `SecurityApi` v4 (`encryptBackup`, `decryptBackup`, `pickBackupFile`), `ReminderApi.scheduleIncomeReminder`.
- Testlar: 579 Dart (+ onboarding / zaxira oqimlari 7, accessibility 15, paginatsiya 1, E2E host 1, zaxira servisi 3, router), 46 Kotlin (+ `BackupCipherTest` 6, daromad eslatmasi jadvali 3, fayl tanlagich 1).
- **Qurilmada (release x64, obfuskatsiyalangan)**: E2E «All tests passed!» (haqiqiy SQLCipher va AES-GCM, zaxira 4,7 KB, shifrlash 1,1 s, 63 qator 1:1); v13→v14 yangilash — onboarding chiqmaydi, ma'lumotlar joyida; `FLAG_SECURE` — skrinshot 100 % qora; eksport → ulashish oynasida `.bkd`; import — noto'g'ri parol, boshqa fayl va boshqa sxema xatolari (Python'da yasalgan fayl Kotlin'da ochildi — format mos); `pm clear` → PIN → 5 ekranli onboarding → «Qarzlar»; bosh ekranda «Bugungi tushum».
- **Topilib tuzatilgan**: (1) `file_selector` plagini qo'shilganda **release ishga tushishda yiqilardi** (R8 bilan `DartExecutor` NPE, `retrace` bilan topildi) — plagin olib tashlandi, o'rniga Pigeon orqali o'zimizning hujjat tanlagich; (2) migratsiya qilingan foydalanuvchida daromad turi `null` bo'lgani uchun Sozlamalarda tanlash ro'yxati chiqmasdi; (3) zaxira paroli dialogidagi controller yopilish animatsiyasidan oldin dispose qilinardi.

## [Vazifa 14] Venture ledger, taqsimot, «Hunardan ishga», taklif detektori — 2026-10-11

- **Kassa daftari** (`/partnerships/item/:id/ledger`, SPEC 2E.3): faol sheriklik uchun kirim (buyurtmalar), xarajat (mato, ish haqi), fors-major (izoh va dalil bilan) va tuzatish yozuvlari; **chek yoki dalil rasmi** (kamera / galereya, `image_picker`) SQLCipher bilan shifrlangan bazada. **Biznes puli uy pulidan alohida** — uy byudjetiga faqat taqsimlangan ulushim `Income` (`TAVAKKAL`) sifatida tushadi. Mudarabada sof kapital egasi daftarni faqat ko'radi.
- **Davr taqsimoti** (`distribute`): foyda — ulushlar bo'yicha (largest remainder); zarar — Vazifa 13 qoidalari (musharaka kapitalga mutanosib, mudaraba kapital egasida, beparvolik izoh bilan ishchiga); **buyout to'lovi mehnat egasi ulushidan avtomatik ayirilib** kapital egasiga qo'shiladi va qolgan ulushni kamaytiradi. **Yopilgan davr o'zgarmaydi** — yozuvlar qulflanadi, tuzatish faqat ochiq davrda yangi yozuv bilan.
- **Sherikka shaffoflik**: davr hisoboti PDF (kirim, xarajat, sof foyda, taqsimot, buyout va qolgan ulush, yozuvlar).
- **«Hunardan ishga»** (`/ideas`, SPEC 2E.4): hunarlar ro'yxati, g'oya: CAPEX bandlari, oylik kirim / xarajat, **uch stsenariy** (pessimistik −30 %, o'rtacha, optimistik +30 %), sheriklikdagi ulushdan keyingi foyda va **payback** — jonli ko'rinadi; bir bosishda **shartnoma qoralamasi** (usta: men — mehnat egasi, CAPEX — sherik uskunasi).
- **Taklif detektori** (`/offer-check`, SPEC 2E.5): 6 savol (ha / yo'q / bilmayman), qaror jadvali — **yashil / sariq / qizil**, har bayroq izohlanadi; bosh ekrandagi karta va sheriklik ekranidan ochiladi; tekshiruvlar tarixi. Hodisalar: `OFFER_CHECKED`, `VENTURE_IDEA_CREATED`.
- Ohang: «tavakkalsiz foyda va'dasi» — ribo filtri bilan mos iboralar.
- **Sxema v13**: `venture_entries` (chek blob), `venture_periods`, `distribution_shares`, `skills`, `venture_ideas`, `idea_capex_items`, `offer_checks`. Migratsiya testlari v12→v13 va v1→v13.
- Testlar: 548 Dart (+ 19 sof: mudaraba foyda / zarar / beparvolik, musharaka zarar, buyout bilan foyda va chegaralari, payback CAPEX 8 mln — 40 / 4 / 3 oy va ulush 60 % — 7 oy, OfferCheck qaror jadvali har savol bo'yicha; 8 servis: davr yopish va uy daromadi, qulflangan davr va tuzatish, buyout, zarar, faqat ko'rish, g'oya, tekshiruv; 4 UI oqimi), 36 Kotlin.
- **Qurilmada (release x64)**: v12→v13 migratsiya, bosh ekrandan taklif tekshiruvi → qizil va 6 bayroq izohi; daftarga yozuv emulyator kamerasidan chek rasmi bilan, davrni yopish — men 2 mln (3 mln − 1 mln buyout), Gayrat 3 mln, uy daromadiga 2 mln, yozuv qulflandi, hisobot PDF ulashildi; g'oya hisobi: CAPEX 8 mln, pessimistik 40 oy.
- **Topilib tuzatilgan**: (1) yangi bosh ekran kartasi tufayli «Qutqarilgan pul» testi tugmani panel ostida bosardi; (2) «sariq» bayroqlar ko'k-yashil chiqardi; (3) davr bugun yopilganda «Ochiq davr: ertaga — bugun» yozuvi — endi «Keyingi davr: … dan».

## [Vazifa 13] 5-qonun: sheriklik domeni, shartnoma ustasi, buyout — 2026-10-10

- **«Sheriklik»** (`/partnerships`, SPEC 2E.1): `MUDARABA | MUSHARAKA`, holat `DRAFT → SIGNED → ACTIVE → CLOSED`, muddat; rollar `CAPITAL_PROVIDER | WORKER | BOTH`; kapital — pul yoki narxlangan uskuna.
- **Domen qoidalari** (`PartnershipRules`, kod darajasida): foyda faqat **sof foydaning foizi**, ulushlar yig'indisi 100 %; **qat'iy summa yoki zarar bo'lsa ham va'da qilingan foyda kiritib bo'lmaydi** — «Bu sheriklik emas — ribo yoki qarz» (UI'da ham variant tanlansa qizil tushuntirish va «Keyingi» o'chiq); mudarabada kapital bir tomondan, mehnat ikkinchidan, ishchida kapital yo'q; musharakada har sherik kapital kiritadi; zarar: musharaka — `capital_i / Σcapital`, mudaraba — kapital egasida, ishchiga faqat `negligence` va izoh bilan.
- **Shartnoma ustasi** (6 qadam): tur va rol, tomonlar, kapital, foyda va zarar qoidasi, muddat / hisobot davriyligi / muddat tugashi / nizolar (standart matnlar bilan), guvohlar, ko'rib chiqish. **Shartnomasiz sheriklik yaratilmaydi** — 1-versiya va imzolovchilar birga yoziladi.
- **Imzo va PDF**: tomonlar va guvohlar shu qurilmada imzo chizadi; PDF (`core/pdf`, tomonlar jadvali, kapital, shartlar, izoh, imzolar) ulashiladi. **Har o'zgarish — yangi versiya** (shartlar surati JSON, eski versiyalar saqlanadi) va hamma qayta imzolaydi; imzolangan reja qoralamaga qaytadi, faol sheriklik faol qoladi, lekin «qayta imzo kerak».
- **Darvoza (SPEC 2E.6)**: **kapital kirituvchi** boshlashda tayyorgarlik darvozasi tekshiriladi (yopiq bo'lsa faqat ongli tasdiq bilan, qayd etiladi); **kapital qabul qiluvchi** uchun darvoza yo'q, lekin «Bu qarz emas» tushuntirishi va barcha kattalarning roziligi (shaxsiy PIN bilan) majburiy.
- **Buyout (kamayib boruvchi musharaka)**: oylik to'lov, jadval (oxirgi to'lov qoldiqni aynan yopadi), kapital egasining qolgan ulushi progress bilan, to'lov yozish.
- **«Zarar bo'lsa kim ko'taradi?»** kalkulyatori (beparvolik va izoh bilan).
- **Shablonlar** `reviewStatus` bilan: ikkala shablon `PENDING` — ekranda, ustada va PDF'da «yurist va ulamo tomonidan hali tekshirilmagan» ogohlantirishi.
- **Sxema v12**: `partnerships`, `partners`, `capital_contributions`, `partnership_contracts` (`contract_version`), `buyout_payments`, `partnership_consents`; imzolar `loan_signers` da (`SignerRole.party`). Migratsiya testlari v11→v12 va v1→v12.
- Testlar: 512 Dart (+ 15 domen: har qoida uchun ijobiy va salbiy, versiya va qayta imzo, darvoza faqat kapital kirituvchiga, rozilik va PIN, buyout; PDF va glif qamrovi; 4 UI oqimi), 36 Kotlin.
- **Qurilmada (release x64)**: v11→v12 migratsiya, usta orqali mudaraba (men — mehnat egasi, Gayrat — 40 mln uskuna), «Qat'iy summa» bloklandi, ikki tomon ekranda imzoladi → «Imzolangan», «Bu qarz emas» + rozilik → faol, `sheriklik_shartnomasi.pdf` ulashish, buyout 1 mln/oy → 40 oy.
- **Topilib tuzatilgan**: (1) shartnoma jadvalidagi `version` ustuni sinxronizatsiya versiyasi bilan to'qnashardi — `contract_version`; (2) tor ekranda shartnoma qatori va usta tugmalari sig'masdi (`Wrap` / `OverflowBar`); (3) kapital egasi kartasida «kapital kiritmaydi» va mudarabada «musharakada …» degan noto'g'ri matnlar; (4) qo'l tasviri ikonkasi (ikonka siyosati testi ushladi) — abstrakt belgi.

## [Vazifa 12] Marosim rejalovchisi va maqsadlar — 2026-10-09

- **«Marosimlar»** (`/ceremonies`, SPEC 2D.8): to'y, beshik to'y, sunnat to'y, ma'raka va boshqa; holat `DRAFT → DISCUSSED → CONFIRMED`; bosh ekran bo'limlarida.
- **Byudjet qatorlari**: bir martalik yoki «kishi boshiga × mehmonlar», har qatorga moliyalash manbasi — jamg'arma / oila hissasi / kutilayotgan to'yona / **qarz** (qizil bayroq).
- **Asosiy qoida**: tanlangan stsenariyda qarz manbali qator bo'lsa, «Buni qarzsiz qanday o'tkazamiz?» muhokamasi majburiy — 5 savol va **har bir katta a'zo** belgi qo'yadi (shaxsiy PIN bo'lsa — PIN bilan; bola belgi qo'ya olmaydi). Hamma belgilagach reja `DISCUSSED`, shundan keyingina tasdiqlanadi (UI va domen darajasida `ceremony_discussion_required`). Muhokamadan keyin reja o'zgarsa — muhokama qaytadan; tasdiqlangan reja o'zgarmaydi («Qayta ochish» bilan qoralamaga).
- **Stsenariylar taqqoslashi** (2–3 ta, nusxalab yaratiladi): jami narx, manbalar, qarz va **to'lash muddati — Vazifa 11 simulyatori bilan** (oyiga to'lov kiritiladi; kiritilmasa daromadning 20 % ulushi; stavka bo'lsa ortiqcha to'lov ham), oylik to'lov foizni qoplamasa — «qarz hech qachon tugamaydi». Shu pulga erishiladigan muqobil maqsadlar (`Goal`) — «bu pulga: «Kontrakt» — 300 %».
- **To'yona o'rniga jamg'arma**: yosh oila uchun maqsad, mehmonlar hissasi qo'lda yoziladi, progress va ulashiladigan matn (`share_plus`). Real o'tkazma keyinroq.
- **Ijtimoiy bosimga qarshi kartochkalar** («El uch kun gapiradi…» va boshqalar).
- **Sxema v11**: `ceremony_plans`, `ceremony_scenarios`, `ceremony_budget_lines`, `ceremony_discussion_marks`, `goal_contributions`. Migratsiya testlari v10→v11 va v1→v11; qurilmadagi haqiqiy v10 bazasi yo'qotishsiz yangilandi.
- Kattaning PIN oynasi umumiy vidjetga ko'chirildi (`showMemberPinPrompt`) — havas roziligi va marosim muhokamasi bir xil.
- Testlar: 487 Dart (+ 11 domen: muhokamasiz tasdiqlash taqiqi, PIN, bola, o'zgarishdan keyin qayta muhokama, simulyator bilan bir xil muddat — foizsiz va 24 %, cheksiz qarz, muqobil maqsadlar, stsenariy chegarasi, to'yona; 4 UI oqimi), 36 Kotlin.
- **Qurilmada (release x64)**: v10→v11 migratsiya, reja tuzish, 200 kishi, «Sarpo» 10 mln qarz → muhokama kartasi va o'chiq «Tasdiqlash», oyiga 1,5 mln → «Qarz 7 oyda uziladi (09.05.2027 gacha)», «Muhokama qildim» → tasdiqlash → «Tasdiqlandi», reja qulflandi.

## [Vazifa 11] 4-qonun: «Qarzdan chiqish» 70/20/10, payoff planner, sotiladigan buyumlar, «Qarzsiz kun» — 2026-10-09

- **`DEBT_RECOVERY` rejimi** (`/debts/recovery`, SPEC 2D.1): faol qarz bo'lsa Qarzlar ekrani va bosh ekran rejimni taklif qiladi. Standart **70 / 20 / 10** (ro'zg'or / qo'shimcha qarz to'lovi / «Kelajagim»), oila o'zgartira oladi. **Jamg'arma ulushi 0 ga tushirilmaydi** — 1 % dan kam bo'lsa qizil xato va saqlash o'chiq (domen darajasida ham `recovery_savings_required`). Majburiy oylik to'lovlar 70 % ichida ko'rsatiladi («ro'zg'orga qoladi»), sig'masa ogohlantirish. Yoqilganda «Kelajagim» foiz ulushi 10 % dan kam bo'lsa ko'tariladi.
- **Avtomatik qaytish**: oxirgi qarz yopilganda rejim o'zi `STANDARD` ga qaytadi va bo'shagan 20 % ni «Kelajagim»ga yo'naltirish taklif qilinadi (foiz ulushiga qo'shiladi).
- **Payoff planner** (`/debts/plan`, SPEC 2D.2): har qarz uchun oyma-oy, **tiyin aniqligidagi** amortizatsiya simulyatori (`payoff.dart`): annuitet va differensialda qo'shimcha to'lov asosiy qarzni kamaytiradi va foiz qayta hisoblanadi (muddat qisqaradi, oylik to'lov o'zgarmaydi); ustama / qo'lda / foizsiz qarzda oxirgi to'lovlar qisqaradi. Odatiy va qo'shimchali grafik yonma-yon, «N oy erta» va «X so'm tejaldi», umumiy «Qarzsiz kun». Qo'shimcha manbalar: 20 % ulush, qutqarilgan pul (bir bosishda qarzga), sotilgan buyumlar; bir martalik summa. «Taxminiy hisob» izohi doim ko'rinadi.
- **Yopish tartibi**: standart — avval foizlilar (stavka yoki ortiqcha to'lov ulushi bo'yicha eng qimmati), keyin foizsizlar (muddati yaqini); yuqoriga/pastga bilan qo'lda o'zgartiriladi (`debts.payoff_order`), «Standart tartib» bilan qaytariladi.
- **Muddatidan oldin to'lash jarimasi** (bp, qarz sahifasida): qo'shimcha to'lovdan ushlanadi (`debt_payments.fee_minor`), simulyatsiyada ham hisobga olinadi.
- **To'lov mantig'i qayta yozildi**: to'lov avval navbatdagi reja qatorini yopadi, ortgani — qo'shimcha to'lov; reja qayta quriladi, qarz qoldig'i va haqiqiy narx shunga ko'ra kamayadi (qurilmada: 100 000 so'm → 21 899,46 so'm foiz tejaldi). To'lash summasi «hozir to'liq yopish» summasidan oshmaydi.
- **Sotiladigan buyumlar** (`/debts/sell`, SPEC 2D.7): nomi, taxminiy narxi, `LISTED → SOLD`; sotilgan puli bir bosishda tanlangan qarzga qo'shimcha to'lov.
- **Yelkadoshlar** (`DebtContributor`, SPEC 2D.4): qarzga oila a'zosi / farzand yoziladi (oylik ulushi ixtiyoriy), to'lovda «Kim to'ladi?» so'raladi, har birining to'lagani ko'rinadi. Ilovaga taklif — keyinroq.
- **«Qarzsiz kun»** (SPEC 2D.9): har qarz va umumiy sana (har to'lovdan keyin yangilanadi), bosh ekranda karta (rejimda — reja bo'yicha sana ham). Qarz yopilganda **nishonlash ekrani** va bo'shagan oylik to'lovni «Kelajagim»ga yo'naltirish taklifi.
- **Darvoza**: qarz sharti «foizli qarz yo'q **yoki** qarzdan chiqish rejasi bor (rejim yoqilgan)».
- **Sxema v10**: `households.budget_mode`, `recovery_*_bp`, `freed_share_offer_pending`; `debts.payoff_order`, `prepay_fee_bp`; `debt_payments.fee_minor`, `contributor_id`; yangi `debt_contributors`, `sellable_items`. Migratsiya testlari v9→v10 va v1→v10; **qurilmadagi haqiqiy v9 bazasi** (Vazifa 10 dagi kredit, to'lovlar, bergan qarz) yo'qotishsiz yangilandi.
- Testlar: 469 Dart (+ etalonlar: **Akmal** 39 mln / 14 oy / 24 %, oyiga +2 mln → 9 oy, 2 432 340,42 so'm tejaladi; **Hamid aka** 9 mln, oyiga 1,5 mln — 600 000 i foiz, 8 oy; 96 kombinatsiyada qoldiq aynan 0; jarima; ko'p qarz tartibi; rejim qaytishi; jamg'arma 0 taqiqi; 5 UI oqimi), 36 Kotlin.
- **Topilib tuzatilgan**: (1) v5→v6 migratsiya yordamchisi `households` ni joriy klass bilan o'qirdi — v10 dagi NOT NULL ustunlar tufayli eski bazadan yangilash yiqilardi; endi faqat kerakli ustunlar o'qiladi (v9 backfill ham). (2) Qarz sahifasida birinchi to'lanmagan qatordan keyingi kichik oxirgi qator ham «to'langan» deb belgilanardi (qurilmada topildi). (3) Dialoglardagi `TextEditingController` yopilish animatsiyasi tugamasdan `dispose` qilinardi (havas, maqsad, guvoh oynalari) — umumiy `showTextPrompt` ga o'tkazildi.

## [Vazifa 10] 4-qonun: qarzlar, to'lov jadvali, haqiqiy narx, tilxat — 2026-10-08

- **«Qarzlar»** (`/debts`, SPEC 2D): olgan qarzlar (bank, do'kon, qarindosh, do'st, boshqa) va bergan qarzlar alohida; umumiy ko'rsatkichlar — jami qarz, oylik qarz yuki (o'rtacha oylik daromadga nisbatan; daromad bo'lmasa — «daromad hali yozilmagan»), «menga qaytishi kerak».
- **To'lov jadvali majburiy** (4 tur): teng to'lov (annuitet), kamayib boruvchi (differensial), qat'iy ustama va «o'zim yozaman». Rejasiz yoki rejasi summani qoplamaydigan qarzni saqlab bo'lmaydi (UI va domen darajasida). Muddatidan oldin to'lash shartlari matn sifatida.
- **Qarzning haqiqiy narxi**: asosiy summa → jami to'lanadi → ortiqcha to'lov; imkoniyat narxi `goals` (maqsadlar) bilan taqqoslanadi. Foiz yoki ustama bo'lsa — qizil «bu ribo» ogohlantirishi (stavka faqat hisob uchun).
- **«To'xta va o'yla»** (`BorrowCheck`): yangi qarzdan oldin zarurat/hashamat va foizsiz muqobil savollari; javob qarz yozuvida JSON bo'lib saqlanadi. Taqiq emas — ongli qaror.
- **To'lovlar**: «To'lov qildim» — rejadagidan ko'p bo'lsa muddatidan oldin to'lov deb belgilanadi; rejada to'langan qatorlar belgilanadi. Nasiya daftari ham endi to'lov sanasi va jadval qatori bilan yoziladi.
- **Bergan qarz** (qarzi hasana): **foiz maydoni umuman yo'q** (jadvalda ham, modelda ham); muddatga 3 kun qolganda bosh ekranda xushmuomala eslatma kartasi; «Qaytardi» tugmasi.
- **Qarz tilxati** (SPEC 2D.5): qarz beruvchi va oluvchi avtomatik, guvohlar qo'shiladi; har biri **shu qurilmada** ismini yozib, barmoq bilan imzo chizadi (PNG bazada). PDF `core/pdf` orqali (Noto Sans, o'zbekcha belgilar), «shaxsiy hisob uchun yozuv, yuridik kafolat emas» izohi bilan; tizimning ulashish oynasi (`share_plus`). Qarz va tilxat sahifalari FLAG_SECURE (parametrli marshrutlar ham).
- **Darvoza** (Vazifa 9): qarz sharti endi haqiqiy ma'lumotda — ochiq foizli qarz bo'lmasa bajarilgan (`DebtDataReadiness`).
- **Sxema v9**: `debts` ga `schedule_type`, `term_months`, `annual_rate_bp`, `start_date`, `borrow_check`; yangi `debt_installments`, `debt_payments`, `receivables` (foiz ustunisiz), `goals`, `loan_signers`. Migratsiyada har ochiq qarzga bitta jadval qatori yaratiladi (muddat yoki yaratilgan sana + 30 kun). Migratsiya testlari v8→v9 va v1→v9.
- Testlar: 434 Dart (+ 4 jadval turi haqiqiy narxi, annuitet aniq tiyingacha, qarz yuki, rejasiz saqlash taqiqi, `Receivable` da foiz yo'qligi, tilxat PDF golden va glif qamrovi, 7 ta UI oqimi), 36 Kotlin.
- **Qurilmada (release x64)**: bank krediti 10 mln / 12 oy / 24 % → qizil ogohlantirish, jami 11 347 151,59 soʻm, ortiqcha 1 347 151,59 soʻm, birinchi oy foizi 200 000; to'lov va reja belgisi; tilxatni imzolash va `qarz_tilxati.pdf` ulashish oynasi; bergan qarz (foiz maydonisiz).
- **Topilib tuzatilgan**: summa oynasi faqat butun so'm oladi, bank jadvalida esa tiyin bor — 945 595,97 lik to'lov 945 595 bo'lib yozilib, reja qatori to'lanmagan qolardi. Endi butun so'mli kiritish navbatdagi to'lov yoki qoldiqqa (1 so'mdan kam farq bo'lsa) aynan moslanadi (`snapPayment`).

## [Vazifa 9] 3-qonun: qorovul / o'sadigan pul, narx daftari, darvoza, ribo filtri — 2026-10-08

- **Jamg'arma ikkiga bo'lindi** (SPEC 2C.3): migratsiyada mavjud «Kelajagim» to'liq **qorovul pul**ga o'tadi (tranzaksiyalar o'z aktivida — balans o'zgarmaydi); **o'sadigan pul** aktivi alohida. «Kelajagim» jami = ikkalasi (bosh ekran KPI, audit ham). Avto-ulush va boshqa kiritishlar avval qorovulni maqsadgacha to'ldiradi, ortgani — qarz sharti bajarilganda — o'sadiganga.
- **Zaxira maqsadi**: oxirgi 3 to'liq oyning (ZARUR + KERAK, amaldagi toifa bo'yicha; havas va sadaqa kirmaydi) o'rtachasi × 6; bosqichlar 3 va 6 oy; progress «1,4 / 6 oy». Ma'lumot 3 oydan kam bo'lsa — taxminiy summa so'raladi.
- **Qorovul puldan olish**: «Bu haqiqatan favqulodda holat» tasdig'i majburiy (domen darajasida ham); olingandan keyin qayta to'ldirish rejasi (6 oyga, 1 000 soʻmgacha yuqoriga). O'sadigandan olishda bu tasdiq so'ralmaydi.
- **Tayyorgarlik darvozasi** (SPEC 2C.4): qorovul ≥ 6 oy **va** qarz sharti (Vazifa 10–11 gacha `NoDebtDataReadiness` stub — «qarz yo'q»). Yopiq holatda shartlar va progress ko'rsatiladi; ongli chetlab o'tish — ogohlantirish, tasdiq, `households.gate_bypassed_at` va lokal log hodisasi.
- **«Narx daftari»** (`/prices`, SPEC 2C.1): savat (nomi, birlik, oylik miqdor — og'irlik), narx tarixi va joy, «oldin → bugun» taqqoslash, **shaxsiy inflyatsiya indeksi** (1 yil va boshidan; bazis punkt, faqat ikkala sanada narxi ma'lum mahsulotlar), narx kiritish streak'i, haftalik (shanba) eslatma. Hodisa: `PRICE_COMPARISON_DONE`.
- **«Inflyatsiya ta'siri»** (`/vault/mouse`, SPEC 2C.2): qorovul pulga bugungi va bir yil oldingi narxda necha kg/dona, shaxsiy indeks bilan 3 yildan keyin; har doim keyingi qadam bilan tugaydi.
- **Ribo filtri** (SPEC 2C.5): daromadda ixtiyoriy «ter / mol / tavakkal / foiz (ribo)» belgisi; foizli daromad auditda alohida. ARB (uz, ru) va kontent JSON'da foizni daromad sifatida tavsiya qiluvchi iboralar yo'qligi test bilan tekshiriladi.
- **Sxema v8**: `price_items`, `price_points`, `households.reserve_monthly_estimate_minor`, `households.gate_bypassed_at`; `assets.vault_type` → `qorovul`. Migratsiya testlari v7→v8 (balans saqlanadi) va v1→v8; qurilmadagi haqiqiy v7 bazasi yangilandi.
- Daromad kiritish ekranida ham summa, klaviatura va «Saqlash» pastga mahkamlandi (ribo belgilari qo'shilgach klaviatura ko'rinmay qolardi).
- Testlar: 400 Dart (+ zaxira maqsadi, taqsimot, darvoza matritsasi, qayta to'ldirish, inflyatsiya indeksi, narx daftari, migratsiya, ribo filtri, 5 ta UI oqimi), 36 Kotlin.
- **Qurilmada (release x64)**: v7→v8 migratsiya (1 959 633 soʻm qorovulga), taxminiy summa → «4,8 / 6 oy» va 3 oylik bosqich, darvoza shartlari, narx daftari, «Inflyatsiya ta'siri» 15,07 kg.
- **Topilib tuzatilgan**: ulush taqsimotida ortiqcha qism o'sadiganga hech qachon o'tmasdi (`gate.ready` qorovul allaqachon to'la bo'lishini talab qiladi — endi faqat qarz sharti).

## [Vazifa 8] Obunalar, konvertlar, «Qutqarilgan pul» — 2026-10-08

- **Obunalar** (`/subscriptions`, SPEC 2B.5): oylik yoki yillik narx, har birining **yillik narxi** va faol obunalarning yillik jami. «Ishlatdim» belgisi; 30 kun belgilanmasa — «unutilgan obuna» ogohlantirishi (neytral rangda). Bekor qilinganda oylik ekvivalenti `savings_rescues` ga yoziladi va «yiliga X tejaladi» ko'rsatiladi. Hodisa: `SUBSCRIPTIONS_REVIEWED`.
- **Konvertlar** (`/envelopes`, SPEC 2B.6): haftalik limit, kategoriyalarga bog'lanadi (bitta kategoriya — bitta konvert); shu kategoriyadagi har xarajat — **naqd ham, karta ham** — konvertdan ayiriladi. Naqd rejimda «Bu hafta konvertga X soʻm soling» va hafta tugagach qoldiqni kiritish; karta konverti hafta chegarasida (juma 00:00, Toshkent) avtomatik yopiladi. Har hafta limit surati `envelope_periods` da. Hodisa: `ENVELOPE_CREATED`.
- **«Qutqarilgan pul»** (`/rescue`, SPEC 2B.7): havas kamayishi (bazaviy oy havasi × o'tgan kunlar / bazaviy oy kunlari − joriy havas) + bekor qilingan obunalar (bekor qilingan kundan, oylik ekvivalent × kun / 30) + shu davrda yopilgan konvert qoldiqlari. Ko'proq sarflangan bo'lsa havas qismi **0** va ayblamaydigan matn; manfiy qism boshqa qutqarishlarni yemaydi. Bazaviy oy — birinchi audit oyi yoki tanlangan oy (`households.rescue_baseline_start`). Hafta va oy bo'yicha.
- **Bir bosishda «Kelajagim»ga o'tkazish** (1- va 2-qonun ulanishi): yangi sabab `VaultTransactionReason.rescue`; o'tkazilgani hisobdan ayiriladi — bir pul ikki marta o'tkazilmaydi.
- **Bosh ekran**: «Bu hafta qutqarildi: X» kartasi («Bu hafta qancha qutqardingiz?») va o'tkazish tugmasi; bo'limlarga obunalar, konvertlar, qutqarilgan pul.
- **Sxema v7**: `subscriptions`, `envelopes`, `envelope_periods`, `savings_rescues` + `households.rescue_baseline_start`. Migratsiya testlari v6→v7 va v1→v7; qurilmadagi haqiqiy v6 bazasi ma'lumot yo'qotmasdan yangilandi.
- Testlar: 356 Dart (+ formula, manfiy holat, yillik tejam, obuna prorata, konvert hafta chegarasi payshanba 23:59 / juma 00:00, naqd konvert qoldig'i, ikki marta o'tkazib bo'lmasligi, migratsiya, 4 ta UI oqimi), 36 Kotlin.
- **Qurilmada (release x64)**: v6→v7 migratsiya, obuna qo'shish → bekor qilish (yillik 588 000 soʻm), «Qutqarilgan pul» 1 633 soʻm (49 000 / 30), bazaviy oy tanlanganda ko'proq sarflangan holat — 0 va ayblamaydigan matn, «Kelajagim»ga o'tkazish va tugmaning yo'qolishi, naqd konvert ochish (kategoriyalar bilan, joriy hafta xarajati hisoblandi).
- **Topilib tuzatilgan**: (1) konvert oynasida kategoriyalar chiqmasdi (kuzatilmagan provider `read(...).valueOrNull` — doim `null`); (2) xuddi shu xato Vazifa 7 dagi kategoriyalar ekranida — oilada bir nechta a'zo bo'lsa ham «Kim o'zgartiryapti?» so'ralmasdi (regressiya testi qo'shildi); (3) obunani bekor qilish oynasida «Bekor qilish» va «Bekor qildim» tugmalari adashtirardi — «Hali yoʻq»; (4) imlo vositasi Windows'da ARB'ni CRLF bilan yozardi.

## [Vazifa 7] Uch toifa, shablonlar, vidjet, havas chegarasi — 2026-10-08

- **Zarur / Kerak / Havas** (SPEC 2B.2): har kategoriyaning standart toifasi (bola = `KERAK`, ijara/oziq-ovqat/yo'lkira = `ZARUR`, ichimlik/kafe = `HAVAS`, sadaqa — toifadan tashqari). Oila toifani o'zgartiradi; kim va qachon o'zgartirgani `necessity_changes` tarixida (`/expenses/categories`). Xarajat kiritishda toifa kategoriyadan avtomatik olinadi, o'zgartirish mumkin. Ranglar neytral (havas qizil emas).
- **Tez kiritish** (SPEC 2B.1): xarajat shablonlari (`expense_templates`), «Shablon sifatida ham saqlash», «Oxirgisini takrorlash»; bosh ekranda «Tez yozish» kartasi — bir bosishda yozish va «Bekor qilish». Xarajat ekranida summa, klaviatura va «Saqlash» pastga mahkamlandi (kiritish 1 ekranda).
- **Bosh ekran vidjeti** (Kotlin, Jetpack Glance 1.1.1): 4 tagacha shablon tugmasi. Bosilgan yozuv Keystore bilan shifrlangan navbatga tushadi va ilova qulfdan ochilgach bazaga yoziladi (bosilgan vaqt bilan). **Ilova qulfli bo'lsa summalar ko'rsatilmaydi**: Flutter ko'rinish muddatini (`hozir + qulf vaqti`) uzatadi, qulflanganda va jarayon qayta ishga tushganda — 0; «cheksiz» holat atayin yo'q. Muddat tugaganda WorkManager vidjetni qayta chizadi. Pigeon `WidgetApi`.
- **Jamlash effekti**: mayda kategoriyalar uchun oxirgi 30 kun bo'yicha haftasiga / oyiga / yiliga prognoz (butun so'mgacha) va «oyiga — «Ijara»ning X%i» taqqoslash (ijara bo'lmasa — eng katta majburiyat). Majburiyat kategoriyalari, oziq-ovqat va sadaqa «mayda» hisoblanmaydi.
- **Havas chegarasi** (`havas_limits` + `limit_consents`): taklif barcha kattalar (shaxsiy PIN bo'lsa — PIN bilan) rozi bo'lmaguncha **faol emas**; bola rozilik bermaydi. Yangi taklif kelishilguncha eski chegara amalda. 80 % va 100 % da yumshoq ogohlantirish, bloklash yo'q. Kelishilganda `HAVAS_LIMIT_AGREED` vazifa hodisasi.
- **Isrof va saxovat** (SPEC 2B.8): `isGift` (havas hisobiga kirmaydi), `isOstentation` (alohida ko'rsatiladi), `fundedByDebt` + havas = qizil bayroq (ro'yxatda va tahlilda). Sadaqa havas va «oqib ketish» hisobiga kirmaydi — qo'lda «havas» deb belgilansa ham.
- **«Juma shirinligi»** (`scheduled_treats`): nomi, hafta kuni, summa; tanlangan kuni 09:00 (Toshkent) quvonchli eslatma (Kotlin `TreatReminderWorker`, matnda summa yo'q).
- **Odatlar** (`habits`, `expenses.habitId`): faqat statistika — oyiga / yiliga, ayblovchi matn yo'q.
- **Sxema v6**: 6 ta yangi jadval + `expenses.habit_id`; mavjud standart kategoriyalarga toifa to'ldiriladi (foydalanuvchi o'zgartirgani saqlanadi), yangi «Ichimlik va gazak», «Choyxona va kafe» kategoriyalari qo'shiladi. Migratsiya testlari v5→v6 va v1→v6; qurilmadagi haqiqiy v5 bazasi ma'lumot yo'qotmasdan yangilandi.
- `core/money`: `Money.scaled` (bir marta yaxlitlanadigan nisbat), `ratioBasisPoints`.
- Imlo vositasi so'z oxiridagi `oʻ` ni ham tuzatadi («Obroʻ»); himoya testi kuchaytirildi. Ikonka siyosati: qo'l tasvirlari (`volunteer_activism`, `back_hand` …) taqiqlandi.
- Testlar: 335 Dart (+ toifa, rozilik, sadaqa, yillik jamlash, shablon, odat, shirinlik, migratsiya, 6 ta UI oqimi: vidjet ko'rinishi va navbati, tez yozish + bekor qilish, sadaqa/qizil bayroq, havas roziligi PIN bilan, toifa tarixi), 36 Kotlin (+ hafta kuni hisobi, vidjet ko'rinish qoidasi).
- **Qurilmada (release x64)**: v5→v6 migratsiya, toifa avtomatik, shablon saqlash, bosh ekran «Tez yozish», havas taklifi → rozilik → 80 % va oshish ogohlantirishi, vidjetni bosh ekranga qo'yish, qulfli holatda summasiz ko'rinish, qulfli paytda bosilgan 2 ta yozuv qulf ochilgach yozildi, shirinlik saqlandi va eslatma rejalashtirildi, kategoriyalar ekrani.
- **Qurilmada topilib tuzatilgan**: (1) Glance `update()` ishlayotgan sessiyada ma'lumotni qayta o'qimasdi — holat versiyasi bilan tuzatildi; (2) ilova ochiq paytda jarayon o'ldirilsa vidjet summani cheksiz ko'rsatardi — «cheksiz» holat olib tashlandi; (3) prognozlarda tiyin chiqardi; (4) oziq-ovqat «mayda xarajat» sifatida ko'rinardi; (5) «Obro'» imlosi; (6) sadaqa yonida qo'l ikonkasi; (7) ketma-ket roziliklarda snackbar navbatga tushardi.

## [0-vazifa] Yangi MVP rejasi bo'yicha 1–6-vazifalarga qo'shimchalar — 2026-10-07

- **Shrift**: ilovaga o'rnatilgan Noto Sans (Regular/Medium/Bold/Italic, OFL) — `ʻ` (U+02BB), `ʼ` (U+02BC) va kirill to'g'ri chiqadi; Roboto'da U+02BB yo'q edi. Ilova va PDF bitta shriftdan foydalanadi.
- **O'zbek imlosi**: uz ARB'dagi 79 ta matn `oʻ/gʻ` (U+02BB) va tutuq `ʼ` (U+02BC) ga o'tkazildi, valyuta belgisi `soʻm`. `tools/uz_orthography.py` (`--check`) va himoya testi: uz ARB'da ham, kontent JSON'da ham ASCII apostrof qolmasin. `MoneyParser` klaviaturadan keladigan barcha apostrof turlarini qabul qiladi (`so'm`, `so‘m`, `so’m`, `soʻm`, `soʼm`).
- **`core/pdf`**: umumiy PDF quruvchi (`BarakaPdf`) — sarlavha, matn, «belgi: qiymat» qatorlari, jadval (summalar o'ngga), izoh, imzo bloki (chizilgan imzo rasmi bilan), sahifa raqami va pastki yozuv. Shrift PDF ichiga joylanadi. Namuna PDF ko'z bilan tekshirildi.
- **Yangi modullar** (bo'sh): `budget, subscriptions, envelopes, prices, debts, ceremonies, partnerships, ventures, offers`.
- **Bosh ekran slotlari**: `homeCardSlotsProvider` (karta, `order` bo'yicha) va `homeSectionsProvider` («Bo'limlar»). Keyingi vazifalar bosh ekran kodiga tegmasdan o'z kartasini qo'shadi.
- **Sxema v5**: `members.pin_record` — oila a'zosining ixtiyoriy shaxsiy PIN hosilasi (oilaviy rozilik). `MemberPinService`: o'rnatish, almashtirish, o'chirish, tekshirish; hosila va lockout asosiy PIN bilan bir xil (`PinService.createRecord/verifyRecord`), lekin har a'zoning xatolar hisobi alohida. Migratsiya v4→v5 va v1→v5 testlari; qurilmadagi haqiqiy v4 bazasi ma'lumot yo'qotmasdan yangilandi.
- **`TaskTrigger` reyestri**: satr kodli, kengaytiriladigan (15 ta: hozir yuboriladiganlari `VAULT_OPENED`, `VAULT_FIRST_DEPOSIT`, `INCOME_SHARED`, `AUDIT_COMPLETED`, `DAFTAR_PAGE_WRITTEN`, `EXPENSE_RECORDED`; qolganlari 7–14-vazifalar uchun). Noma'lum kod bobni yaroqsiz qiladi; `docs/content_schema.json` dagi ro'yxat test bilan reyestrga bog'langan.
- **5 ta bob** (placeholder matn, qonun matnlari SPEC'dan, har bobda 3 vazifa triggerlar bilan).
- **Bob ochilishi odat asosida** (`HabitUnlockPolicy`, sozlanadi: 2 vazifa, 7 kun): k-bob (k−1)-bob ochilgandan ≥7 kun o'tib **va** uning vazifalaridan ≥2 tasi bajarilganda ochiladi. Vaqtning o'zi bob ochmaydi; bir marta bajarilgan vazifa belgisi olib tashlansa ham ochilgan bob qayta yopilmaydi. Yopiq bobda «Oldingi bobdan yana N ta vazifa bajarilsa ochiladi». `TimeBasedUnlockPolicy` saqlanib qoldi.
- Testlar: 303 Dart (+ PDF/glif, slotlar, a'zo PIN va lockout, migratsiya, odat qoidasi, trigger reyestri, yangi triggerlarning UI integratsiyasi, imlo), 32 Kotlin. Qurilmada (release x64): shrift va `ʻ`, slotli bosh ekran, 5 bob ro'yxati, v4→v5 migratsiya.

## [Vazifa 6] Kontent dvigateli: boblar, «Daftar sahifasi», haftalik vazifalar — 2026-10-07

- **Kontent** koddan ajratilgan: `assets/content/chapters.json` (bob: id, tartib, sarlavha, matn bloklari, ixtiyoriy audio URL, qonun, aniq 3 ta haftalik vazifa). Sxema: `docs/content_schema.json`; ilovada `ContentParser` uni tekshiradi — buzuq bob o'tkazib yuboriladi, buzuq fayl «yuklab bo'lmadi» holatini ko'rsatadi, ilova yiqilmaydi (500 ta tasodifiy buzilish testi).
- **Diniy bloklar**: `religiousReviewStatus` (`PENDING | APPROVED`) va manba majburiy. `PENDING` release build'da ko'rsatilmaydi; debug'da «ulamo tekshiruvida» belgisi bilan (kontent tekshiruvi uchun).
- **1-bob** — faqat placeholder matn (litsenziya hal bo'lguncha); qonun matni va vazifalar ishlaydi.
- **Bob ochilishi** — `ChapterUnlockPolicy` interfeysi; MVP-1 da `TimeBasedUnlockPolicy` (1-bob darhol, k-bob dastur boshlangan haftadan k−1 juma keyin). Odat asosidagi qoida uchun kontekst tayyor.
- **«Daftar sahifasi»** — qog'oz uslubidagi chiziqli sahifa, qonunni o'z so'zlari bilan yozish; `daftar_pages` (sxema v4).
- **Haftalik vazifalar** — checklist (bosh ekran va bob ekranida), `task_completions` (sxema v4). Avtomatik: «Kelajagim» ochildi → 1-vazifa, daromaddan ulush → 2-vazifa, oylik audit yakunlandi → 3-vazifa; qo'lda belgilash/bekor qilish.
- **Juma bildirishnomasi** — har juma 09:00 (Toshkent), «Yangi bob / haftalik yakun»; Kotlin WorkManager, keyingi jumani o'zi rejalashtiradi.
- Har ta'limiy ekranda disklеymer: «Ta'limiy material. Fatvo yoki moliyaviy maslahat emas».
- Testlar: 282 Dart (parser, filtr, ochilish, servis, avtomatik belgilash integratsiyasi, «Daftar sahifasi», buzuq kontent), 32 Kotlin (+ juma hisobi). Qurilmada: release'da PENDING diniy blok yo'q, «Kelajagim» ochilganda 1-vazifa avtomatik belgilandi va qayta ishga tushirish/qayta o'rnatishdan keyin saqlandi, «Daftar sahifasi» saqlandi; WorkManager ishlari (juma +2 kun, majburiyat +30 kun) **emulyator qayta yoqilgandan keyin ilova ochilmasdan tiklandi**; juma ishi majburan ishga tushirilganda bildirishnoma keldi va keyingi juma rejalashtirildi.
- Qurilmada topilib tuzatilgan: «Daftar sahifasi» chiziqlari matn qatorlariga to'g'ri kelmasdi.
- Test infratuzilmasi: `rootBundle` keshi o'chirildi (keshlangan Future eski test zonasiga bog'lanib, keyingi testlarni osiltirardi); `tapVisible` yordamchisi.

## [Vazifa 5] Xarajatlar, majburiyatlar, «Kimning puli?», oylik audit — 2026-10-06

- **Xarajat kiritish** (`/expenses/new`): summa (o'z klaviaturasi), kategoriya, kanal, kim; `necessity` so'ralmaydi. Shu oy xarajatlari ro'yxati (`/expenses`).
- **Majburiyatlar** (`/obligations`): ijara, kredit, kommunal, telefon, benzin; turi o'z kategoriyasiga bog'lanadi. **Eslatma** to'lov kunidan 1 kun oldin 09:00 (Toshkent) — Kotlin WorkManager + bildirishnoma (Pigeon `ReminderApi`); worker keyingi oyni o'zi rejalashtiradi, ilova ochilganda hammasi qayta sinxronlanadi; bir to'lov uchun ikki marta kelmaydi; matnda summa yo'q, qulf ekranida yashirin. Android 13+ ruxsati so'raladi, o'chiq bo'lsa ogohlantirish.
- **Nasiya daftari** (`/nasiya`): `Debt(SHOP)` — qo'shish, qisman to'lash, jami qoldiq.
- **Oylik audit ustasi** (`/audit`): o'tgan oy (oylik kuni bo'yicha) — daromad → majburiyatlar → kategoriyalar → natija. **Izohsiz summa** = daromad − (majburiyatlar + kiritilgan xarajatlar + sof jamg'arma). Ikki marta hisoblamaslik: majburiyat o'z kategoriyasidagi yozilgan xarajat bilan qoplanadi, faqat yozilmagan qoldig'i qo'shiladi. Izohsizni «mayda kundalik xarajat» deb belgilash yoki kategoriyalarga taqsimlash; yakun `monthly_reports` ga yoziladi (sxema v3).
- **«Kimning puli?»** (`/whose-money`): uy egasi, bank, do'kondor, kommunal, yoqilg'i, **o'zingiz**, sadaqa (alohida, isrof emas), boshqalar, izohsiz — gorizontal bo'lak-diagramma, iliq «daftar» ranglari, oylar bo'yicha o'tish.
- **Bosh ekran**: 1-raqam «O'zingizga to'langan (shu oy)», «Kelajagim» + streak, oy yakuni (+/−), oylik audit holati, haftalik vazifalar kartasi (Vazifa 6), «Daromad» va «Xarajat» tugmalari.
- **Oilaviy rejim (lokal)**: a'zolar (`/members`), egasi avtomatik; ikki va undan ko'p a'zo bo'lsa daromad/xarajatda «Kim?» tanlovi. A'zolar rasm emas, bosh harf bilan.
- **Sozlamalar** (`/settings`): oylik kuni (oy chegarasi), a'zolar, native ko'prik holati.
- **Qurilmada topilib tuzatilgan**: (1) ruxsat berilgach ham «bildirishnoma o'chiq» ogohlantirishi qolardi; (2) ruxsat yo'q paytda worker eslatmani «yuborildi» deb belgilab yo'qotardi — endi to'lov kunigacha soatiga qayta urinadi; (3) «Kimning puli?» diagrammasi ko'rinmasdi (bolasiz bo'laklar balandligi 0); (4) audit tugmalari tor ekranda toshardi / noto'g'ri joylashardi. Har biriga regressiya testi.
- Ikonka siyosati kengaytirildi (`diversity`, `family`, `groups` … — odam siluetlari).
- Testlar: 256 Dart (+ hisob mantig'i, servislar, UI oqimlari), 31 Kotlin (+ eslatma vaqti). Qurilmada: xarajat, majburiyat → ruxsat → bildirishnoma keldi, qayta ishga tushirishdan keyin keyingi oy rejalashtirilgan (+30 kun), «Kimning puli?», audit.

## [Vazifa 4] Daromad kiritish va «Kelajagim» — 2026-10-06

- **Tez daromad kiritish** (`/income/new`): raqamli klaviatura (tizim klaviaturasisiz), oxirgi 3 ta summa chip'i, oxirgi manba va kanal oldindan tanlangan. Bosh sahifadagi «Daromad» tugmasi → chip → «Saqlash» = **3 bosish**.
- **Ulush taklifi**: «Shundan X so'm — kelajagingiz uchun» — [Ajratish] [Boshqa summa] [Bu safar emas]. X `percentOf` orqali (double yo'q), 1 000 so'mgacha yuqoriga yaxlitlanadi (kichik summada — butun so'mgacha), daromaddan oshmaydi. Qat'iy oylik summa rejimida — oy maqsadidan qolgan qism. Ajratilganda `vault_transactions` ga DEPOSIT (`incomeShare`, `incomeId` bilan).
- **Ulush sozlamalari** (`/vault/rule`): 5 % / 10 % / qat'iy summa (oyiga) + progressiv rejim: 4 hafta ketma-ket ajratilsa +1 % taklif, 10 % gacha (1-qonun: 1/10). Javobdan (qabul/rad) keyin keyingi taklif yana 4 haftadan so'ng.
- **«Kelajagim» ekrani**: odat (ketma-ket haftalar, jami haftalar, bu hafta holati) balansdan oldin; balans, qoida, tarix. Streak jumadan boshlanadigan haftalar bo'yicha, Toshkent vaqtida; joriy hafta tugamaguncha streak uzilmaydi.
- **Pul olish** (`/vault/withdraw`): eslatma («bu pul kelajakdagi o'zingizniki»), sabab majburiy, 5 soniyalik o'ylash pauzasi, PIN qayta so'raladi. `PinApproval` — faqat to'g'ri PIN'dan keyin, bir martalik, 1 daqiqa amal qiladi; servis usiz pul olishni rad etadi. Baza CHECK cheklovi ham sababsiz chiqimni to'xtatadi.
- **«Avval yig'ilgan pul»**: ilovadan oldingi jamg'arma — bir martalik DEPOSIT (`initial`), odatga kirmaydi.
- **Sxema v2**: `allocation_rules.progression_offered_at` — birinchi haqiqiy migratsiya (v1 → v2 ma'lumot saqlanishi testi bilan).
- **Qurilmada topilib tuzatilgan**: platforma kanalidan kelgan DB kaliti o'zgarmas ro'yxat — uni tozalash (`fillRange`) yiqilib, baza umuman ochilmasdi; daromad ekrani cheksiz yuklanishda qolardi. Kalit nusxasi bilan ishlash + xato holati + regressiya testi.
- Dialog va pastki panel foni «daftar» qog'oz rangida.
- Testlar: 219+ Dart (domen: streak juma chegaralari bilan, ulush, pul olish, progressiv; UI: 3 bosish, taklif tugmalari, avval yig'ilgan pul, qoida, pul olish pauza/PIN); CI testlariga 60 s vaqt chegarasi.
- Qurilmada (emulyator, release x64): PIN → daromad 150 000 → taklif 8 000 → ajratish → «Kelajagim» (1 hafta, 8 000) → avval yig'ilgan pul 2 000 000 → pul olish (pauza, noto'g'ri PIN rad, to'g'ri PIN bilan 50 000) → qayta ishga tushirish: ma'lumot saqlangan; ruscha ko'plik shakllari; qoida 10 % progressiv.

## [Vazifa 3] Domen yadrosi va shifrlangan baza — 2026-10-06

- `core/money`: `Money` (int minor birlik, toshishdan himoya), `CurrencyCode` (UZS/USD/EUR/RUB), `CurrencyMismatchException`, `MoneyRounding` (6 rejim, BigInt orqali, standart — halfEven), `allocate` (largest remainder), `percentOf` (basis point), `FxRate` (kurs kasr ko'rinishida, `double`siz) va `convert`, uz/ru formatlash (`8 000 000 so'm`, bo'linmas bo'sh joy) va kiritilgan summani o'qish.
- `core/ids`: UUIDv7 (RFC 9562), bir ms ichida va soat orqaga ketganda ham monoton.
- `core/time`: Toshkent (UTC+5, doimiy), `LocalDate`, `BudgetCalendar` — hafta jumadan, oylik kuni sozlanadi (31 → qisqa oyda oxirgi kun).
- Drift + SQLCipher: kalit Keystore'dan (Vazifa 2), xom 256-bit `PRAGMA key`; SQLCipher yuklanmasa baza ochilmaydi (shifrsizga jim tushish yo'q). Baza fayli `<app support>/db/baraka.sqlite`.
- Sxema v1: households, members, categories, incomes, expenses, obligations, debts, assets, asset_snapshots, vault_transactions, allocation_rules, fx_rates — har birida id (UUIDv7), householdId, createdAt/updatedAt (UTC, ISO matn, ms aniqlik), deletedAt, version. CHECK cheklovlari: musbat summa, pul olishda sabab majburiy, ulush 0–10 000 bp, oy kuni 1–31; FK yoqilgan.
- Repository'lar: umumiy `SyncedRepository` (add / optimistik update / soft delete / findById / listActive / watchActive) + har aggregate uchun domen interfeysi va Drift implementatsiyasi (`features/*/domain|data`).
- Seed: uy xo'jaligi va 11 ta standart kategoriya (kalit bilan; nomlari keyin ARB'dan).
- Migratsiya infratuzilmasi: `drift_schemas/default/drift_schema_v1.json`, `test/drift/default/` (SchemaVerifier). CI snapshot dolzarbligini tekshiradi.
- Yangi paketlar: `drift`, `drift_dev` (dev), `sqlcipher_flutter_libs`, `sqlite3`, `path`, `meta`, `integration_test` (dev). APK hajmi ~17 → ~36 MB (SQLCipher + OpenSSL).
- Testlar: 175 Dart (property-based `allocate` — 22 000 tasodifiy holat, yaxlitlash, valyuta, formatlash, UUIDv7, kalendar, repository CRUD/soft delete/versiya, migratsiya); `core/money` qamrovi **98,1 %** (hisob-kitob fayllari 100 %, CI chegarasi 95 %). Qurilmada `integration_test/encrypted_db_test.dart` 6/6 (Keystore kaliti barqaror, SQLCipher yuklangan, fayl sarlavhasi SQLite emas, kalitsiz va noto'g'ri kalit bilan ochilmaydi).

## [Vazifa 2] Xavfsizlik qatlami — 2026-10-06

**Kotlin (`native/`, Pigeon `SecurityApi` v2):**
- Keystore AES-256-GCM wrap kaliti (StrongBox bo'lsa unda; bo'lmasa TEE). Blob formati `ver|iv|ct+tag`, AAD = blob nomi (blob'larni almashtirib bo'lmaydi).
- `getOrCreateDatabaseKey()`: 256-bit tasodifiy kalit `noBackupFilesDir/secure/` ga wrap qilinib, atomik yoziladi. Begona kalit bilan ochilmasa, jimgina yangisini yaratmaydi — xato beradi.
- PIN hosilasi: PBKDF2-HMAC-SHA256, ≥310 000 iteratsiya, fon oqimida (RFC 7914 KAT bilan tekshirilgan).
- `BiometricPrompt`: BIOMETRIC_STRONG yoki qurilma krediensiali (API 30+). `MainActivity` → `FlutterFragmentActivity`.
- `setSecureFlag`, `getIntegritySignals` (root, emulyator, debugger, debuggable, imzo SHA-256; kutilgan xesh `-PexpectedSignatureSha256` bilan).
- Manifest: `allowBackup=false`, `dataExtractionRules`/`fullBackupContent` hammasini chiqaradi; `USE_BIOMETRIC`. Release'da `Log.d/v/i` R8 bilan olib tashlanadi.

**Flutter:**
- PIN o'rnatish (6 raqam, 111111/123456 kabi oddiy kodlar rad etiladi), tasdiqlash, biometriyani ixtiyoriy yoqish.
- `PinService`: PIN saqlanmaydi; yozuv (tuz + hosila) va lockout holati Keystore bilan shifrlangan blob'larda. Konstant vaqtli solishtirish. 5-xatodan boshlab kutish 30 s → 1 → 2 → 4 daq … ≤ 1 soat; qayta ishga tushirish va soatni orqaga surish uni bekor qilmaydi.
- Qulf ekrani: o'z raqamli klaviaturasi (tizim klaviaturasi PIN'ni ko'rmaydi), kutish hisoblagichi, biometriya avtomatik so'raladi.
- `AppLockController`: fonga o'tgandan 2 daqiqa (sozlanadi) keyin qayta qulflanadi; router redirect, qulf ochilgach o'sha ekranga qaytiladi.
- FLAG_SECURE marshrut darajasida: qulf, PIN o'rnatish, bosh sahifa, daromad, «Kelajagim», audit — yoqilgan; boblar — o'chiq.
- Integrity ogohlantirishi (bloklamaydi) va lokal log (`security/integrity.log`, faqat vaqt + xavf kodlari, 200 qator).
- Log siyosati: release'da `debugPrint` va `FlutterError` konsoli o'chiriladi; `AppLog.event` faqat kod qabul qiladi.
- Yangi paketlar: `androidx.biometric` (ADR), `path_provider` (integrity logi; Drift ham ishlatadi), `crypto` (faqat dev — PBKDF2 etaloni).

**Testlar:** 60 Dart (PIN/lockout/KAT, oqimlar, timeout, FLAG_SECURE, integrity), 25 Kotlin JUnit.
**Qurilmada (emulyator, release x64):** PIN o'rnatish → qayta ishga tushirish → PIN bilan kirish (Keystore unwrap saqlangan); 5 xato → kutish, qayta ishga tushganda ham saqlandi; FLAG_SECURE: moliyaviy ekran skrinshoti qora, boblar ko'rinadi; fon 30 s → ochiq, 125 s → qulf; backup bayrog'i yo'q.
Qurilmada topilib tuzatilgan: push qilingan ekranlarda FLAG_SECURE noto'g'ri marshrutga qarab yoqilardi (regressiya testi qo'shildi).

## [Vazifa 1] Loyiha skeleti va infratuzilma — 2026-10-06

- Flutter loyihasi: `applicationId uz.barakadaftari.app` (vaqtinchalik), minSdk 26, Flutter 3.32.5 `.fvmrc` da qotirilgan.
- Feature-first tuzilma (`app/`, `core/`, `features/*/{presentation,domain,data}`).
- Riverpod 2 (generator), go_router (`/lock`, `/home`, `/income/new`, `/vault`, `/audit`, `/content`), freezed + json_serializable (`AppSettings`).
- `flutter gen-l10n`: `uz` (shablon) va `ru`; AppBar'da til va mavzu almashtirgichi.
- Lint: `very_good_analysis` 9 + `strict-casts`, `strict-raw-types`, `strict-inference`.
- Pigeon `SecurityApi` kontrakti; Kotlin `SecurityApiImpl`: `ping()` ishlaydi, qolgan metodlar `UNIMPLEMENTED` qaytaradi (Vazifa 2).
- «Daftar» placeholder mavzusi: qog'oz foni, light/dark.
- Grafika qoidasi (`docs/DESIGN_GUIDELINES.md`) va ikonka denylist testi; «Kelajagim» ikonkasi hamyonga almashtirildi.
- Loyihaga xos launcher ikonkasi (`tools/make_icon.py`), adaptive icon bilan.
- GitHub Actions: generatsiya dolzarbligi → format → analyze → test → build apk --debug → Kotlin JUnit.
- Testlar: 20 Dart (marshrutlar, til, mavzu, ARB kalitlari tengligi, ikonka siyosati, Pigeon kanali, native karta), 3 Kotlin JUnit.
