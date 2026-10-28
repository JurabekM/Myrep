# MVP rejasining holati (`docs/MVP_PLAN.md`)

> 2026-10-07. MVP-1 (`docs/MVP1_KICKOFF.md`) bo'yicha 1–6-vazifalar bajarilgan. Yangi reja 1–3-vazifalarni o'zgarishsiz qoldiradi deydi, lekin 1, 3, 5 va 6-vazifalarga **qo'shimcha talablar** kiritgan. Ular quyida «0-vazifa» sifatida jamlangan va 7-vazifadan oldin bajariladi.

| # | Vazifa | Holat |
|---|---|---|
| 1 | Loyiha skeleti | ✅ (qo'shimchalar — 0-vazifada) |
| 2 | Xavfsizlik qatlami | ✅ |
| 3 | Domen yadrosi va shifrlangan baza | ✅ (qo'shimchalar — 0-vazifada) |
| 4 | Daromad va «Kelajagim» | ✅ |
| 5 | Xarajatlar, majburiyatlar, audit, bosh ekran | ✅ (qo'shimcha — 0-vazifada) |
| 6 | Kontent dvigateli | ✅ (qo'shimchalar — 0-vazifada) |
| 0 | **Yangi reja bo'yicha yetishmayotganlar** (quyida) | ✅ |
| 7 | Uch toifa, shablonlar, vidjet, havas chegarasi | ✅ |
| 8 | Obunalar, konvertlar, «Qutqarilgan pul» | ✅ |
| 9 | Qorovul / o'sadigan, narx daftari, inflyatsiya, darvoza, ribo filtri | ✅ |
| 9A | **Kelishuv dvigateli (9 savol) va append-only jurnal (xesh-zanjir)** — 6-qonun, v0.8 da qo'shildi; tilxat va sheriklik shartnomasini `Agreement` ga ko'chirish migratsiyasi bilan | ✅ |
| 10 | Qarzlar, to'lov jadvali, haqiqiy narx, friction, tilxat | ✅ |
| 11 | `DEBT_RECOVERY` 70/20/10, payoff planner, sotiladigan buyumlar, «Qarzsiz kun» | ✅ |
| 12 | Marosim rejalovchisi va maqsadlar | ✅ |
| 13 | Sheriklik domeni, shartnoma ustasi, buyout | ✅ |
| 14 | Venture ledger, taqsimot, «Hunardan ishga», taklif detektori | ✅ (ledger yozuvlari 9A jurnaliga ko'chiriladi) |
| 14A | **Vazifalar va «bajarilmadi», oylik ko'rik va bayonnoma, «katta foyda», nizo va hakam papkasi, oilaviy kelishuvlar** — 6-qonun | ✅ (2026-10-15; yillik eslatma defekti 2026-10-20 da tuzatilib, qurilmada tasdiqlandi — RELEASE_CHECKLIST 10-bo'lim) |
| 14B | **Besh xavf belgisi, «o'z ko'zim bilan ko'raman», piramida, oilaviy zaxira, «to'xta, maslahatlash», hunar shablonlari** — 7-qonun | ✅ (2026-10-20; qabul mezonlari pastda) |
| 14C | **Soat qiymati va jismoniy chegara, o'qish maqsadi va yo'llari, qoplanish, kurs tekshiruvi, «o'rgatganlarim»** — 8-qonun | ✅ (2026-10-27; qabul mezonlari pastda) |
| 15 | Onboarding, eksport, sifat va reliz | ✅ v0.7 bo'yicha; E2E ssenariysi 14A (vazifa hodisasi, oylik ko'rik) va 14B (Bekzod) qadamlari bilan qurilmada o'tdi (2026-10-20). Imzo kaliti bor (2026-10-28); `1.0.0+6` — `targetSdk 36`, ilova ichida maxfiylik siyosati, Play materiallari (`docs/PLAY_CONSOLE.md`, RELEASE_CHECKLIST 18). Qoldi: haqiqiy telefonda sinov, aloqa emaili va siyosat URL'i (OPEN 163–164), Play akkaunti |

## v0.8 (6-qonun) ta'siri — 2026-10-13

Reja 17 vazifaga kengaydi: tartib `… 9 → 9A → 10 … 14 → 14A → 15`. 10, 13, 14 va 15 allaqachon bajarilgan, shuning uchun (MVP_PLAN 1-bo'lim, 6-band):

- **9A** da `LoanReceipt` (qarz tilxati: `loan_signers`) va `PartnershipContract` (`partnership_contracts`) `Agreement(type = LOAN / PARTNERSHIP)` ga ko'chiriladi, ma'lumot yo'qolmasligi migratsiya testi bilan; `DebtPayment` va `VentureEntry` jurnal (`JournalEntry`) orqali yoziladi.
- **Umumiy test vektorlari** (`spec/test-vectors/`, `DESKTOP_PROMPT.md` 5) mobil CI uchun majburiy. Joriy kod bilan dastlabki tekshiruv (2026-10-13):
  - `allocate` alloc-001/003/004 — mos;
  - `amortization` amort-001…003 — **mos** (14 oy / 610 067 573; +1,6 mln → 9 oy / 397 018 667; +2,4 mln → 8 oy / 341 756 885 tiyin);
  - `percent_of` pct-002 — mos emas edi (halfEven); **2026-10-13 tuzatildi**: half-up + `allocate` orqali. Zaxira maqsadi ham spec formulasiga o'tkazildi.
- **Vektor runner** (`test/vectors/`, CI qadami): 11 suite yashil, `journal_chain` va `profit_spike` — 9A / 14A da.
- **15** ning E2E ssenariysi v0.8 da kengaygan (9/9 savol, «bot ishdan chiqdi» hodisasi, oylik ko'rik, 1,4 mln taqsimot) — 14A dan keyin yangilanadi.

## 0-vazifa: 1–6-vazifalarga yangi rejadagi qo'shimchalar

| Manba | Talab | Holat |
|---|---|---|
| V1 | `features/` ostida yangi modullar: `budget, subscriptions, envelopes, prices, debts, ceremonies, partnerships, ventures, offers`; `core/pdf` | ✅ bo'sh modullar + `core/pdf` |
| V1 | O'zbek yozuvi: `ʻ` (U+02BB) va `ʼ` (U+02BC) to'g'ri ko'rinadigan **ilovaga o'rnatilgan font** (PDF uchun ham) | ✅ Noto Sans; ARB va kontent `ʻ`/`ʼ` da, himoya testi bilan |
| V3 | `core/pdf`: `pdf` paketi asosida umumiy PDF quruvchi (sarlavha, jadval, imzo bloki, o'zbekcha font) | ✅ `BarakaPdf` |
| V3 | `members`: ixtiyoriy shaxsiy PIN hosilasi (oilaviy rozilik uchun) | ✅ sxema v5, `MemberPinService` |
| V5 | Bosh ekran **slot-arxitektura**: keyingi vazifalar o'z kartalarini qo'shadi | ✅ `homeCardSlotsProvider`, `homeSectionsProvider` |
| V6 | **5 ta bob** strukturasi (placeholder matn) | ✅ 5 bob |
| V6 | Kengaytiriladigan `TaskTrigger`: `VAULT_FIRST_DEPOSIT`, `AUDIT_COMPLETED`, `SUBSCRIPTIONS_REVIEWED`, `DEBT_INVENTORY_COMPLETED`, `PRICE_COMPARISON_DONE` … | ✅ 15 kodli reyestr, 6 tasi hozir yuboriladi |
| V6 | `ChapterUnlockPolicy` — **odat asosida**: oldingi bobdan ≥2 vazifa bajarilgan **va** ≥7 kun o'tgan (sozlanadi) + unit testlar | ✅ `HabitUnlockPolicy` (standart) |

Allaqachon bor va keyingi vazifalarga tayyor poydevor: `debts` jadvali (MVP-4 maydonlari bilan), `assets.vaultType` (Vazifa 9 dagi qorovul/o'sadigan bo'linishi), `expenses.necessity/isGift/isOstentation/fundedByDebt` (Vazifa 7), `incomes.sourceType` (ribo filtri), `allocate` (70/20/10 va foyda taqsimoti), WorkManager eslatmalari, `DaftarPage`/`TaskCompletion`.

## Vazifa 7: qabul mezonlari

| Mezon | Holat | Dalil |
|---|---|---|
| 2 kattadan 1 tasi tasdiqlasa, chegara faol emas | ✅ | `test/features/budget/budget_test.dart` (rozilik guruhi), UI: `budget_flows_test.dart` |
| Sadaqa havas hisobiga kirmasligi test bilan tekshirilgan | ✅ | `budget_test.dart`: «sadaqa havas hisobiga kirmaydi — «havas» deb belgilansa ham» |
| Ilova qulfli bo'lganda vidjet summa ko'rsatmaydi | ✅ | Dart: `budget_flows_test.dart` (qulf → `setVisibleUntil(0)`), Kotlin: `WidgetVisibilityTest`; qurilmada ko'rildi. Cheklov: fondagi qulf vaqti tugagach yashirish WorkManager orqali — emulyatorda ~1,5 daqiqa kechikdi (OPEN_QUESTIONS 41) |
| Yillik jamlash hisobi testlangan | ✅ | `budget_test.dart`: «kuniga 2 ta ichimlik — yiliga 4 380 000», `money_test.dart` (`scaled`) |

## Vazifa 8: qabul mezonlari

| Mezon | Holat | Dalil |
|---|---|---|
| Qutqarilgan pul formulasi unit testlangan, manfiy holat ham; manfiyda ayblamaydi va «0» | ✅ | `test/features/budget/rescue_test.dart` (formula guruhi, «koʻproq sarflangan hafta»); qurilmada ko'rildi |
| Konvert davri hafta chegarasida to'g'ri yopiladi | ✅ | `rescue_test.dart`: «payshanba 23:59 / juma 00:00»; naqd konvert — `rescue_flows_test.dart` |
| Bekor qilingan obunaning yillik tejami to'g'ri | ✅ | `rescue_test.dart`: 49 000 × 12 = 588 000, yillik 400 000 = 400 000; UI: `rescue_flows_test.dart` |

## Vazifa 9: qabul mezonlari

| Mezon | Holat | Dalil |
|---|---|---|
| VAULT → QOROVUL migratsiya testi, balans yo'qolmaydi | ✅ | `test/drift/default/migration_test.dart` (v7 → v8); qurilmada haqiqiy baza |
| Zaxira maqsadi va inflyatsiya indeksi hisoblari unit testlangan | ✅ | `test/features/vault/reserve_test.dart`, `vault_split_test.dart`, `test/features/prices/price_math_test.dart`, `price_book_test.dart` |
| Darvoza holatlari test matritsasi bilan tekshirilgan | ✅ | `reserve_test.dart`: 7 holat (zaxira × qarz × chetlab o'tish) |
| ARB'da taqiqlangan iboralar yo'qligi test bilan tasdiqlangan | ✅ | `test/design/riba_filter_test.dart` (uz, ru, kontent JSON + filtr haqiqatan ushlashi) |

Eslatma: qarz sharti Vazifa 10–11 gacha stub (`NoDebtDataReadiness`, MVP_PLAN talabiga ko'ra).

## Vazifa 10: qabul mezonlari

| Mezon | Holat | Dalil |
|---|---|---|
| `Receivable` modelida foiz maydoni yo'qligi test bilan tasdiqlangan | ✅ | `test/features/debts/debt_service_test.dart` (jadval ustunlari va model maydonlari); UI — `debt_flows_test.dart` |
| To'lov rejasisiz qarzni saqlab bo'lmaydi | ✅ | `debt_service_test.dart` (`errScheduleRequired`, `errPlanMismatch`), `debt_flows_test.dart` (tugma o'chiq) |
| PDF'da o'zbekcha belgilar (`oʻ`, `gʻ`) to'g'ri chiqadi (golden test) | ✅ | `test/features/debts/loan_receipt_pdf_test.dart` + `goldens/loan_receipt.pdf` (glif qamrovi, ToUnicode) |
| Haqiqiy narx hisobi 4 xil jadval turi uchun testlangan | ✅ | `test/features/debts/debt_math_test.dart` (annuitet, differensial, qat'iy ustama, qo'lda) |

Darvozaning qarz sharti endi `DebtDataReadiness` (ochiq foizli qarz yo'q). Qarzdan chiqish rejasi (payoff planner) — Vazifa 11.

## Vazifa 11: qabul mezonlari

| Mezon | Holat | Dalil |
|---|---|---|
| Amortizatsiya simulyatori etalon misollar bilan: Akmal 39 mln, 14 oy → ~8–9 oy; Hamid aka 9 mln, oyiga 1,5 mln, 600 mingi foiz | ✅ | `test/features/debts/payoff_test.dart` (Akmal: 24 %, +2 mln/oy → 9 oy, 2 432 340,42 soʻm; Karim: 80 % yillik → birinchi oy foizi 600 000, 8 oy), mustaqil Python hisobi bilan bir xil |
| Simulyatsiya oxirida qoldiq aynan 0 (tiyin farqisiz) | ✅ | `payoff_test.dart`: 96 kombinatsiya (2 tur × 4 stavka × 3 muddat × 4 qo'shimcha, jarima bilan) — qoldiq 0, to'langan asosiy qarz = asosiy summa |
| Rejimning avtomatik `STANDARD` ga qaytishi testlangan | ✅ | `test/features/debts/recovery_test.dart`, UI: `payoff_flows_test.dart` (nishonlash → bo'shagan 20 % → «Kelajagim» 30 %) |
| Jamg'arma ulushini 0 qilishga urinish to'xtatiladi | ✅ | `recovery_test.dart` (0 va 0,5 % — `recovery_savings_required`, sozlama saqlanmaydi), UI: qizil xato va o'chiq tugma |

## Vazifa 12: qabul mezonlari

| Mezon | Holat | Dalil |
|---|---|---|
| `DEBT` manbasi bilan muhokamasiz `CONFIRMED` holatiga o'tib bo'lmaydi (test bilan) | ✅ | `test/features/ceremonies/ceremony_test.dart` (`ceremony_discussion_required`, bitta katta belgilagani yetmaydi, o'zgarishdan keyin qaytadan), UI: `ceremony_flows_test.dart` (o'chiq tugma), qurilmada |
| Stsenariy taqqoslashidagi to'lash muddati Vazifa 11 simulyatori natijasiga mos keladi | ✅ | `ceremony_test.dart`: `rowsFromBalance` + `planPayoff` bilan muddat, sana va jami bir xil (foizsiz 7 oy va 24 % stavka) |

## Vazifa 13: qabul mezonlari

| Mezon | Holat | Dalil |
|---|---|---|
| Validatsiya qoidalarining har biri uchun ijobiy va salbiy testlar bor | ✅ | `test/features/partnerships/partnership_test.dart` (ulushlar 100 %, manfiy ulush, qat'iy / va'da qilingan foyda, mudaraba rollari, ishchida kapital, kapitalsiz, musharaka kapitali, zarar taqsimoti, beparvolik izohi) |
| Kafolatli daromadni kiritish UI va domen darajasida bloklanadi | ✅ | domen: `errNotPartnership`, servis yaratmaydi; UI: `partnership_flows_test.dart` (qizil tushuntirish, «Keyingi» o'chiq); qurilmada |
| Shartnoma versiyasi o'zgarganda imzolar qayta so'raladi | ✅ | `partnership_test.dart` (2-versiya — barcha imzolar bo'sh, guvoh ham; faol sheriklikda `needsResign`), UI: «Shartnoma, 2-versiya» va ogohlantirish |
| Darvoza faqat kapital kirituvchiga qo'llanishi test bilan tekshirilgan | ✅ | `partnership_test.dart`: kapital kirituvchi — yopiq darvoza `errGateClosed`; qabul qiluvchi — darvoza yopiq bo'lsa ham faqat «qarz emas» + rozilik |

## Vazifa 14: qabul mezonlari

| Mezon | Holat | Dalil |
|---|---|---|
| Taqsimot testlari: mudaraba foyda, mudaraba zarar, musharaka zarar va buyout bilan foyda | ✅ | `test/features/partnerships/venture_math_test.dart` (+ beparvolik, buyout chegaralari), servisda: `ledger_test.dart` |
| Yopilgan davrni o'zgartirib bo'lmaydi | ✅ | `ledger_test.dart` (o'chirish va eski sana bilan qo'shish — `ledger_period_closed`, tuzatish faqat ochiq davrda), UI: yopish tugmasi yo'qoladi, yozuv qulflangan; qurilmada |
| Payback hisobi testlangan (CAPEX 8 mln) | ✅ | `venture_math_test.dart`: 6 mln kirim / 4 mln xarajat → 4 oy, pessimistik 40, optimistik 3, ulush 60 % → 7; UI: `venture_flows_test.dart` |
| OfferCheck qaror jadvali unit testlangan | ✅ | `venture_math_test.dart`: har savolning xavfli javobi, «bilmayman», qizilning ustunligi, JSON |

## Vazifa 15: qabul mezonlari

| Mezon | Holat | Dalil |
|---|---|---|
| E2E ssenariy yashil | ✅ | `integration_test/full_e2e_test.dart` (avval `full_e2e_test.dart`) qurilmada (release x64, SQLCipher + Kotlin AES-GCM): 12 qadam, logcat «All tests passed!»; host varianti `test/e2e/full_e2e_host_test.dart` CI'da |
| Eksport → o'chirish → import natijasida ma'lumotlar 1:1 tiklanadi | ✅ | `test/features/backup/backup_test.dart` (yangi bazaga, har jadval qatorma-qator, BLOB bilan), E2E qurilmada (52 jadval, 63 qator, haqiqiy shifr), UI: `onboarding_flow_test.dart` (sozlamalardan va yangi telefonda onboarding'dan); xato yo'llari qurilmada |
| Release APK obfuskatsiya qilingan, `FLAG_SECURE` va lock ishlaydi | ✅ | `tools/build_release.ps1` (`--obfuscate --split-debug-info`, R8): `libapp.so` da Dart sinf nomlari yo'q, Kotlin klasslari qisqargan; qurilmada skrinshot qora, qulf → PIN; `docs/RELEASE_CHECKLIST.md` |

Qo'shimcha: onboarding 5 ekran (PIN bilan), daromad turiga moslashish, accessibility guideline testlari, ro'yxatlar paginatsiyasi, imzo konfiguratsiyasi repodan tashqarida. Sovuq start < 2 s **telefonda** hali o'lchanmagan (emulyatorda 2,0–2,4 s) — `OPEN_QUESTIONS` 98.

## Vazifa 9A: qabul mezonlari

| Mezon | Holat | Dalil |
|---|---|---|
| `journal_chain.json` yashil (xeshlar desktop bilan bitma-bit) | ✅ | `test/vectors/vectors_test.dart` (3 xesh + 2-yozuv buzilishi), Python bilan ham tasdiqlangan |
| Jurnalni o'zgartirish yoki o'chirish xato beradi (repozitoriy va DB trigger) | ✅ | `JournalRepository` da faqat `append`; trigger: `migration_test.dart` (v14→v15 dan keyin UPDATE/DELETE rad), `backup_test.dart` (tiklashdan keyin ham faol) |
| 9/9 bo'lmasa imzolash bloklanadi; «tegishli emas» izohsiz qabul qilinmaydi | ✅ | `agreement_service_test.dart` (`prepareSigning`, sheriklik `sign` → `partnership_agreement_incomplete`), `agreement_completeness.json` (ac-005), UI: izohsiz saqlash tugmasi o'chiq |
| Egasiz yoki «hamma»ga yozilgan vazifa validatsiyadan o'tmaydi | ✅ | `agreement_completeness.json` ac-002 (+ «bajarilmasa»siz — ac-003), muharrirda «hamma» varianti yo'q |
| O'zgartirilgan bazada `verifyChain` buzilgan joyni aniq topadi | ✅ | `agreement_service_test.dart` (trigger olib tashlanib yozuv o'zgartirilganda — 1-yozuv), vektor chain-002 (2-yozuv) |
| (1-bo'lim 6-band) Tilxat va shartnoma `Agreement` ga ko'chirildi, ma'lumot yo'qolmadi | ✅ | `migration_test.dart` v14→v15: versiya ID = hujjat ID (imzolar joyida), to'lov / kapital / kassa / taqsimot jurnalda, o'chirilgan yozuv kirmaydi |

## Vazifa 14A: qabul mezonlari

| Mezon | Holat | Dalil |
|---|---|---|
| `profit_spike.json` vektori yashil | ✅ | `test/vectors/vectors_test.dart` (ps-001…005, runner `ProfitSpike.evaluate`) |
| `IN_DISPUTE` holatida taqsimot bloklanadi | ✅ | `test/features/partnerships/venture_gates_test.dart` — «nizo ochiq boʻlsa taqsimot bloklanadi, hakam qarori ochadi» |
| Bayonnomadagi `chainHead` keyingi `verifyChain` bilan mos; o'zgartirilgan yozuv aniqlanadi | ✅ | `accountability_test.dart` — «ko'rik: ochish → javoblar → bayonnoma chainHead bilan mos», «o'zgartirilgan yozuv aniqlanadi (ikki usulda)» (oddiy o'zgartirish → `verifyChain` 1-yozuv; qayta hisoblangan zanjir → `minutesIntact` false) |
| Hakam papkasi PDF'ida barcha bo'limlar bor (snapshot) | ✅ | `test/features/agreements/accountability_pdf_test.dart` — 9 bo'lim sarlavhasi aniq ro'yxat bilan; PDF baytlari (`%PDF-`) |
| Yillik yangilash eslatmasi rejalashtiriladi va qurilma qayta yoqilgandan keyin ham ishlaydi | ✅ (2026-10-20) | Avval rejalashtirilmasdi (ikki sabab, CHANGELOG 14B); regressiya — `renewal_reminders_test.dart`. Emulyatorda (release): ish +334 kun (2027-09-20 09:00), `adb reboot` dan keyin o'sha muddat bilan joyida — RELEASE_CHECKLIST, 10-bo'lim |

Qo'shimcha mezonlar (MVP_PLAN 14A matnidan):

| Mezon | Holat | Dalil |
|---|---|---|
| «Bajara olmayapman»: sabab, sana, yechim; band darhol ko'rinadi; jurnalda; keyingi ko'rikda | ✅ | `accountability_test.dart` — «vazifa bajarilmadi…»; `accountability_section.dart` (band dialogi) |
| Oylik ko'rik: ochish, AGREE/OBJECT (izohsiz e'tiroz rad etiladi), yakunlashda hamma javob shart; bayonnomadan keyin faqat tuzatish | ✅ | `accountability_test.dart`; `review_flow_test.dart` (widget: roziman → e'tiroz → yakunlash → PDF ulashish tugmasi) |
| «Katta foyda» taqsimotdan oldin; ikkala tomon tasdiqlashi; ko'rik taklifi | ✅ | `venture_gates_test.dart` — «katta foyda: ikkala tomon tasdiqlamaguncha…», «foyda oʻzgarsa tasdiq eskirgan…»; `profit_spike_dialog.dart` |
| Nizo: talablar, hakam qarori, `ACTIVE` ga qaytish | ✅ | `accountability_test.dart` — «nizo: IN_DISPUTE, hakam qarori ACTIVE ga qaytaradi»; `dispute_screen.dart` |
| Yillik yangilash «o'zgarishsiz» — yangi versiya va qayta imzo | ✅ | `accountability_test.dart` — «yillik yangilash: eslatma 30 kun oldin, tasdiq yangi versiya» |
| Oilaviy kelishuv: 4 shablon, hakam ixtiyoriy | ✅ (sarlavha + izoh; javoblar oldindan to'ldirilmaydi — OPEN 131) | `agreement_screen.dart` (`_FamilyTemplate`), `completeness.dart` (hakam ixtiyoriy) |
| Kelishuvlar markazi: holat, keyingi ko'rik, ochiq hodisa, nizo | ✅ | `agreement_screen.dart` (`AgreementsScreen` ro'yxati), `agreementCenterProvider` |
| Bosh ekran «Yaqinlashayotgan ko'rik / yangilash» kartasi | ✅ | `home_cards.dart` (`AccountabilityHomeCard`), `home_slots.dart` (slot 155), `home_slots_test.dart` |
| 6-bob va triggerlar `ACCOUNT_REVIEW_COMPLETED`, `FAMILY_AGREEMENT_CREATED` | ✅ | `assets/content/chapters.json` (ch06), `content_test.dart` (6 bob), `docs/content_schema.json` |

## Vazifa 14B: qabul mezonlari

| Mezon | Holat | Dalil |
|---|---|---|
| `scam_signals.json`, `promised_return.json`, `pyramid_levels.json`, `lump_sum_split.json` yashil | ✅ | `test/vectors/vectors_test.dart` (21 holat); qiymatlar mustaqil Python hisobi bilan bitma-bit |
| Ikki belgi (shoshirish + qiyin chiqish) bahoni qizilga ko'taradi | ✅ | `scam_check_test.dart` — «ikki sariq belgi bahoni qizilga ko'taradi»; vektor sc-003 |
| «Pul qo'yaman» maslahatchisiz va 24 soatdan oldin bloklanadi | ✅ | `scam_check_test.dart` — «pul qo'yish maslahatchisiz va 24 soatdan oldin bloklanadi» (23:59 — rad, 24:00 — ochiq); widget: `offer-accept` o'chiq |
| Katta summa taqsimotida zaxira to'lmaguncha sarmoyaga faqat ortgan qism | ✅ | `lump_sum_test.dart` (dollar 18 000 × 12 650 → 18 mln devorga, 209,7 mln hunarga; qorovul balansi 18 mln); vektor ls-002 |
| Migratsiya v15 → v16: eski tekshiruvlar yo'qolmaydi | ✅ | `migration_test.dart` — «v15 → v16: eski taklif tekshiruvlari yo'qolmaydi», sxema v15→v16 va v1→v16 |

Qo'shimcha: hunar shabloni — `idea_template_test.dart`; 7-bob — `content_test.dart` (7 bob); E2E — Bekzod qadami, 14 qadam (host va emulyatorda x64 release). Qurilmada ko'rib tuzatilgan uchta UI kamchiligi — CHANGELOG 14B.

## Vazifa 14C (8-qonun): qabul mezonlari — 2026-10-27

| Mezon | Holat | Dalil |
|---|---|---|
| `hourly_value.json`, `skill_payback.json`, `course_check.json` yashil | ✅ | `test/vectors/vectors_test.dart` (majburiy ro'yxatda) |
| Ikki belgi kurs bahosini qizilga ko'taradi | ✅ | `test/features/learning/learning_test.dart` («ikki belgi…»), UI: `learning_flows_test.dart` |
| Natija maqsadisiz yo'l saqlanmaydi; soat qiymatisiz maqsad ochilmaydi | ✅ | `learning_test.dart`; UI: «Yangi maqsad» tugmasi soat qiymatisiz o'chiq, yo'l oynasida xato |
| Qo'shimcha daromad 0 — «qoplanmaydi», va'da matni yo'q | ✅ | `learning_test.dart` («qoʻshimcha daromad yoʻq»), ARB `lnPaybackNote` |
| Migratsiya v16 → v17 | ✅ | `test/drift/default/migration_test.dart` (v16 → v17, v1 → v17) |
| Kontent siyosati: 8-bobda tashqi manba personajlari va o'xshatishlari yo'q | ✅ | `test/design/source_policy_test.dart` (8-qonun manbasi iboralari qo'shildi) |

