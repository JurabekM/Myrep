import 'package:baraka_daftari/core/db/converters.dart';
import 'package:baraka_daftari/core/domain/enums.dart';
import 'package:baraka_daftari/core/money/currency.dart';
import 'package:drift/drift.dart';

// Sxema v1 (MVP-1). Qoidalar (SPEC 4.4):
// * ID — UUIDv7 matn, autoincrement yo'q;
// * har jadvalda householdId, createdAt, updatedAt (UTC), deletedAt?, version;
// * pul — `…Minor` (butun son) + `currency` ustunlari, double yo'q;
// * keyingi bosqich maydonlari hozirdan nullable yoki standart qiymat bilan.

/// Umumiy sinx ustunlari.
mixin SyncColumns on Table {
  TextColumn get id => text()();
  TextColumn get householdId => text()();
  DateTimeColumn get createdAt => dateTime()();
  DateTimeColumn get updatedAt => dateTime()();
  DateTimeColumn get deletedAt => dateTime().nullable()();
  IntColumn get version => integer().withDefault(const Constant(1))();

  @override
  Set<Column<Object>> get primaryKey => {id};
}

@DataClassName('HouseholdRow')
class Households extends Table with SyncColumns {
  TextColumn get name => text().nullable()();
  TextColumn get baseCurrency =>
      textEnum<CurrencyCode>().withDefault(Constant(CurrencyCode.uzs.name))();

  /// `DateTime.friday` = 5 (SPEC 4.4: weekAnchor = FRIDAY).
  IntColumn get weekAnchor => integer().withDefault(const Constant(5))();

  /// Oylik davr boshlanadigan kun (oylik kuni).
  IntColumn get monthStartDay => integer().withDefault(const Constant(1))();

  /// «Qutqarilgan pul» bazaviy oyi boshi (v7); `null` — birinchi audit oyi.
  TextColumn get rescueBaselineStart =>
      text().map(const LocalDateConverter()).nullable()();

  /// Oylik zarur + kerak xarajatlarning taxminiy summasi (v8) — ma'lumot
  /// 3 oydan kam bo'lsa zaxira maqsadi shundan hisoblanadi.
  IntColumn get reserveMonthlyEstimateMinor => integer().nullable()();

  /// Tayyorgarlik darvozasi ongli chetlab o'tilgan vaqt (v8, UTC).
  DateTimeColumn get gateBypassedAt => dateTime().nullable()();

  // --- v10 (MVP_PLAN Vazifa 11): «Qarzdan chiqish» rejimi ---
  TextColumn get budgetMode =>
      textEnum<BudgetMode>().withDefault(Constant(BudgetMode.standard.name))();

  /// 70 / 20 / 10 ulushlari (bp): ro'zg'or, qo'shimcha qarz to'lovi,
  /// «Kelajagim» (0 bo'lmaydi).
  IntColumn get recoveryNeedsBp =>
      integer().withDefault(const Constant(7000))();
  IntColumn get recoveryDebtBp => integer().withDefault(const Constant(2000))();
  IntColumn get recoverySavingsBp =>
      integer().withDefault(const Constant(1000))();

  /// Hamma qarz yopilib rejim odatiyga qaytgach — bo'shagan 20 % taklifi.
  BoolColumn get freedShareOfferPending =>
      boolean().withDefault(const Constant(false))();

  // --- v14 (MVP_PLAN Vazifa 15): onboarding ---
  /// Onboarding yakunlangan vaqt (UTC); `null` — hali o'tilmagan.
  DateTimeColumn get onboardedAt => dateTime().nullable()();
  TextColumn get incomeKind => textEnum<IncomeKind>().nullable()();
}

@DataClassName('MemberRow')
class Members extends Table with SyncColumns {
  TextColumn get displayName => text()();
  TextColumn get role => textEnum<MemberRole>()();
  BoolColumn get isOwner => boolean().withDefault(const Constant(false))();

  /// Ixtiyoriy shaxsiy PIN hosilasi (`PinRecord` JSON, v5). Oilaviy rozilikda
  /// a'zo o'z profilini shu PIN bilan tasdiqlaydi. PIN o'zi saqlanmaydi.
  TextColumn get pinRecord => text().nullable()();
}

@DataClassName('CategoryRow')
class Categories extends Table with SyncColumns {
  /// Standart kategoriya kaliti; foydalanuvchi yaratganida `null`.
  TextColumn get systemKey => textEnum<CategoryKey>().nullable()();

  /// Foydalanuvchi bergan nom; standart kategoriyada `null` (ARB'dan).
  TextColumn get name => text().nullable()();
  TextColumn get defaultNecessity => textEnum<Necessity>().nullable()();
  IntColumn get sortOrder => integer().withDefault(const Constant(0))();
  BoolColumn get isArchived => boolean().withDefault(const Constant(false))();

  @override
  List<String> get customConstraints => [
    'CHECK (system_key IS NOT NULL OR name IS NOT NULL)',
  ];
}

@DataClassName('IncomeRow')
class Incomes extends Table with SyncColumns {
  IntColumn get amountMinor => integer()();
  TextColumn get currency => textEnum<CurrencyCode>()();
  TextColumn get source => textEnum<IncomeSource>()();
  TextColumn get channel => textEnum<PaymentChannel>()();
  TextColumn get memberId => text().nullable().references(Members, #id)();
  TextColumn get sourceType => textEnum<IncomeSourceType>().nullable()();
  DateTimeColumn get receivedAt => dateTime()();
  TextColumn get note => text().nullable()();

  @override
  List<String> get customConstraints => ['CHECK (amount_minor > 0)'];
}

@DataClassName('ExpenseRow')
class Expenses extends Table with SyncColumns {
  IntColumn get amountMinor => integer()();
  TextColumn get currency => textEnum<CurrencyCode>()();
  TextColumn get categoryId => text().references(Categories, #id)();
  TextColumn get channel => textEnum<PaymentChannel>()();
  TextColumn get memberId => text().nullable().references(Members, #id)();
  TextColumn get necessity => textEnum<Necessity>().nullable()();

  /// MVP-2 (konvertlar) — jadval hali yo'q, shuning uchun FK ham yo'q.
  TextColumn get envelopeId => text().nullable()();
  BoolColumn get isGift => boolean().withDefault(const Constant(false))();
  BoolColumn get isOstentation =>
      boolean().withDefault(const Constant(false))();
  BoolColumn get fundedByDebt => boolean().withDefault(const Constant(false))();
  DateTimeColumn get spentAt => dateTime()();
  TextColumn get note => text().nullable()();

  /// Kuzatiladigan odat (v6, SPEC 2B.9).
  TextColumn get habitId => text().nullable().references(Habits, #id)();

  @override
  List<String> get customConstraints => ['CHECK (amount_minor > 0)'];
}

@DataClassName('ObligationRow')
class Obligations extends Table with SyncColumns {
  TextColumn get title => text()();
  TextColumn get kind => textEnum<ObligationKind>()();
  IntColumn get amountMinor => integer()();
  TextColumn get currency => textEnum<CurrencyCode>()();

  /// Oyning qaysi kuni to'lanadi (1–31; qisqa oyda oxirgi kun).
  IntColumn get dayOfMonth => integer()();
  TextColumn get categoryId => text().nullable().references(Categories, #id)();
  TextColumn get debtId => text().nullable().references(Debts, #id)();
  BoolColumn get isActive => boolean().withDefault(const Constant(true))();

  @override
  List<String> get customConstraints => [
    'CHECK (day_of_month BETWEEN 1 AND 31)',
    'CHECK (amount_minor > 0)',
  ];
}

@DataClassName('DebtRow')
class Debts extends Table with SyncColumns {
  TextColumn get creditorType => textEnum<CreditorType>()();
  TextColumn get creditorName => text()();
  TextColumn get currency => textEnum<CurrencyCode>()();
  IntColumn get principalMinor => integer()();
  IntColumn get remainingMinor => integer()();
  IntColumn get monthlyPaymentMinor => integer().nullable()();
  TextColumn get dueDate => text().map(const LocalDateConverter()).nullable()();

  /// Sabab: «to'y», «mashina», «ro'zg'or» (erkin matn).
  TextColumn get reason => text().nullable()();
  BoolColumn get hasMarkup => boolean().withDefault(const Constant(false))();

  // MVP-4 maydonlari (SPEC 5) — hozircha bo'sh.
  IntColumn get totalPaidMinor => integer().nullable()();
  IntColumn get markupAmountMinor => integer().nullable()();
  TextColumn get earlyRepaymentTerms => text().nullable()();
  IntColumn get priority => integer().nullable()();
  TextColumn get note => text().nullable()();

  // --- v9 (MVP_PLAN Vazifa 10) ---
  TextColumn get scheduleType => textEnum<DebtScheduleType>().nullable()();

  /// Muddat (oy) — annuitet / differensial / ustama uchun.
  IntColumn get termMonths => integer().nullable()();

  /// Yillik foiz stavkasi, bazis punktda (bank krediti; faqat hisob uchun).
  IntColumn get annualRateBp => integer().nullable()();
  TextColumn get startDate =>
      text().map(const LocalDateConverter()).nullable()();

  /// Qarz oldidan «to'xta va o'yla» javoblari (JSON, SPEC 2D.6).
  TextColumn get borrowCheck => text().nullable()();

  // --- v10 (MVP_PLAN Vazifa 11) ---
  /// Yopish tartibi (payoff planner); `null` — standart tartib.
  IntColumn get payoffOrder => integer().nullable()();

  /// Muddatidan oldin to'lash jarimasi / komissiyasi (qo'shimcha to'lovdan,
  /// bp).
  IntColumn get prepayFeeBp => integer().nullable()();

  @override
  List<String> get customConstraints => [
    'CHECK (principal_minor >= 0 AND remaining_minor >= 0)',
  ];
}

@DataClassName('AssetRow')
class Assets extends Table with SyncColumns {
  TextColumn get type => textEnum<AssetType>()();
  TextColumn get name => text().nullable()();

  /// Butun son: pul — minor birlik, oltin — milligramm.
  IntColumn get quantity => integer().withDefault(const Constant(0))();
  TextColumn get unit => textEnum<QuantityUnit>()();
  TextColumn get currency => textEnum<CurrencyCode>().nullable()();
  DateTimeColumn get acquiredAt => dateTime()();

  /// MVP-3: qorovul / o'sadigan.
  TextColumn get vaultType => textEnum<VaultType>().nullable()();
}

/// Balans tarixi — zakotdagi hawl (1 yil) hisobi uchun (SPEC 4.3).
@DataClassName('AssetSnapshotRow')
class AssetSnapshots extends Table with SyncColumns {
  TextColumn get assetId => text().references(Assets, #id)();
  IntColumn get quantity => integer()();
  DateTimeColumn get takenAt => dateTime()();
}

@DataClassName('VaultTransactionRow')
class VaultTransactions extends Table with SyncColumns {
  TextColumn get vaultAssetId => text().references(Assets, #id)();
  TextColumn get type => textEnum<VaultTransactionType>()();
  IntColumn get amountMinor => integer()();
  TextColumn get currency => textEnum<CurrencyCode>()();
  TextColumn get reason => textEnum<VaultTransactionReason>()();

  /// Erkin izoh; pul olishda majburiy (repository tekshiradi).
  TextColumn get reasonNote => text().nullable()();
  TextColumn get incomeId => text().nullable().references(Incomes, #id)();
  TextColumn get memberId => text().nullable().references(Members, #id)();
  DateTimeColumn get occurredAt => dateTime()();

  @override
  List<String> get customConstraints => [
    'CHECK (amount_minor > 0)',
    // Pul olish sababsiz yozilmaydi — baza darajasida ham. drift faqat
    // literalni o'qiydi, shuning uchun satr bo'linmagan.
    // ignore: lines_longer_than_80_chars
    "CHECK (type <> 'withdraw' OR (reason_note IS NOT NULL AND length(trim(reason_note)) > 0))",
  ];
}

@DataClassName('AllocationRuleRow')
class AllocationRules extends Table with SyncColumns {
  TextColumn get vaultAssetId => text().references(Assets, #id)();
  TextColumn get mode => textEnum<AllocationMode>()();

  /// Ulush: 500 = 5 %, 1000 = 10 %. Qat'iy summa rejimida `null`.
  IntColumn get basisPoints => integer().nullable()();

  /// Qat'iy summa (masalan, oyiga 300 000 so'm).
  IntColumn get fixedAmountMinor => integer().nullable()();
  TextColumn get currency => textEnum<CurrencyCode>()();
  BoolColumn get isActive => boolean().withDefault(const Constant(true))();

  /// v2: progressiv rejimda oxirgi «+1 %» taklifi berilgan payt (UTC).
  /// Keyingi taklif shundan keyingi 4 ketma-ket haftadan so'ng.
  DateTimeColumn get progressionOfferedAt => dateTime().nullable()();

  @override
  List<String> get customConstraints => [
    'CHECK (basis_points IS NOT NULL OR fixed_amount_minor IS NOT NULL)',
    'CHECK (basis_points IS NULL OR basis_points BETWEEN 0 AND 10000)',
  ];
}

@DataClassName('FxRateRow')
class FxRates extends Table with SyncColumns {
  TextColumn get fromCurrency => textEnum<CurrencyCode>()();
  TextColumn get toCurrency => textEnum<CurrencyCode>()();
  IntColumn get rateNumerator => integer()();
  IntColumn get rateDenominator => integer()();
  TextColumn get rateDate => text().map(const LocalDateConverter())();
  TextColumn get source => text().withDefault(const Constant('manual'))();

  @override
  List<String> get customConstraints => [
    'CHECK (rate_numerator > 0 AND rate_denominator > 0)',
  ];
}

/// v3: oylik audit yakuni (SPEC 5: `MonthlyReport`). Bir davr uchun bitta
/// faol yozuv; audit qayta o'tkazilsa yangilanadi.
@DataClassName('MonthlyReportRow')
class MonthlyReports extends Table with SyncColumns {
  /// Davr boshi (shu kun kiradi).
  TextColumn get periodStart => text().map(const LocalDateConverter())();

  /// Davr oxiri (shu kun kirmaydi).
  TextColumn get periodEnd => text().map(const LocalDateConverter())();
  TextColumn get currency => textEnum<CurrencyCode>()();
  IntColumn get incomeMinor => integer()();
  IntColumn get obligationsMinor => integer()();
  IntColumn get expensesMinor => integer()();

  /// Sof jamg'arma (ajratilgan − olingan); manfiy bo'lishi mumkin.
  IntColumn get savingsMinor => integer()();

  /// Izohsiz qolgan summa; manfiy bo'lishi mumkin.
  IntColumn get unexplainedMinor => integer()();
  DateTimeColumn get completedAt => dateTime()();
}

/// v4: «Daftar sahifasi» — foydalanuvchi qonunni o'z qo'li bilan yozadi
/// (SPEC 1.1). Har bob uchun bitta faol sahifa.
@DataClassName('DaftarPageRow')
class DaftarPages extends Table with SyncColumns {
  /// Kontentdagi bob ID (masalan, `ch01`).
  TextColumn get chapterId => text()();
  IntColumn get lawNumber => integer()();
  TextColumn get body => text()();
}

/// v4: haftalik vazifa bajarilishi (SPEC 5: `TaskCompletion`).
@DataClassName('TaskCompletionRow')
class TaskCompletions extends Table with SyncColumns {
  /// Kontentdagi vazifa ID (masalan, `ch01.t1`).
  TextColumn get taskId => text()();

  /// Hafta boshi (juma) — vazifa shu hafta uchun bajarilgan.
  TextColumn get weekStart => text().map(const LocalDateConverter())();

  /// Ilova o'zi belgilaganmi (masalan, «Kelajagim» ochilganda).
  BoolColumn get isAuto => boolean().withDefault(const Constant(false))();
}

// --- Sxema v6 (MVP_PLAN Vazifa 7: 2-qonun) ---

/// Kategoriya standart toifasining o'zgarish tarixi (SPEC 2B.2): kim va
/// qachon (`createdAt`).
@DataClassName('NecessityChangeRow')
class NecessityChanges extends Table with SyncColumns {
  TextColumn get categoryId => text().references(Categories, #id)();
  TextColumn get fromNecessity => textEnum<Necessity>().nullable()();
  TextColumn get toNecessity => textEnum<Necessity>().nullable()();
  TextColumn get memberId => text().nullable().references(Members, #id)();
}

/// Kuzatiladigan odat (masalan, chekish) — faqat statistika (SPEC 2B.9).
@DataClassName('HabitRow')
class Habits extends Table with SyncColumns {
  TextColumn get title => text()();
  BoolColumn get isArchived => boolean().withDefault(const Constant(false))();
}

/// Xarajat shabloni (somsa, ichimlik, benzin …) — bir bosishda yozish.
@DataClassName('ExpenseTemplateRow')
class ExpenseTemplates extends Table with SyncColumns {
  TextColumn get title => text()();
  IntColumn get amountMinor => integer()();
  TextColumn get currency => textEnum<CurrencyCode>()();
  TextColumn get categoryId => text().references(Categories, #id)();
  TextColumn get channel => textEnum<PaymentChannel>()();

  /// `null` — kategoriya toifasi olinadi.
  TextColumn get necessity => textEnum<Necessity>().nullable()();
  TextColumn get habitId => text().nullable().references(Habits, #id)();
  IntColumn get sortOrder => integer().withDefault(const Constant(0))();

  @override
  List<String> get customConstraints => ['CHECK (amount_minor > 0)'];
}

/// Havas uchun oylik chegara taklifi (SPEC 2B.3). Barcha kattalar rozilik
/// bermaguncha faol emas.
@DataClassName('HavasLimitRow')
class HavasLimits extends Table with SyncColumns {
  IntColumn get amountMinor => integer()();
  TextColumn get currency => textEnum<CurrencyCode>()();
  TextColumn get proposedBy => text().nullable().references(Members, #id)();

  @override
  List<String> get customConstraints => ['CHECK (amount_minor > 0)'];
}

/// A'zoning chegaraga rozilik tasdig'i.
@DataClassName('LimitConsentRow')
class LimitConsents extends Table with SyncColumns {
  TextColumn get limitId => text().references(HavasLimits, #id)();
  TextColumn get memberId => text().references(Members, #id)();
}

/// «Juma shirinligi» — davriy havas rituali (SPEC 2B.4).
@DataClassName('ScheduledTreatRow')
class ScheduledTreats extends Table with SyncColumns {
  TextColumn get title => text()();
  IntColumn get amountMinor => integer()();
  TextColumn get currency => textEnum<CurrencyCode>()();

  /// `DateTime.monday` (1) … `DateTime.sunday` (7).
  IntColumn get weekday => integer()();
  BoolColumn get isActive => boolean().withDefault(const Constant(true))();

  @override
  List<String> get customConstraints => [
    'CHECK (amount_minor > 0)',
    'CHECK (weekday BETWEEN 1 AND 7)',
  ];
}

// --- Sxema v7 (MVP_PLAN Vazifa 8: obunalar, konvertlar, qutqarilgan pul) ---

/// Takroriy to'lov / obuna (SPEC 2B.5). MVP'da qo'lda kiritiladi.
@DataClassName('SubscriptionRow')
class Subscriptions extends Table with SyncColumns {
  TextColumn get title => text()();
  IntColumn get amountMinor => integer()();
  TextColumn get currency => textEnum<CurrencyCode>()();
  TextColumn get cycle => textEnum<SubscriptionCycle>()();
  TextColumn get startedOn => text().map(const LocalDateConverter())();

  /// Oxirgi marta «ishlatdim» deb belgilangan sana.
  TextColumn get lastUsedOn =>
      text().map(const LocalDateConverter()).nullable()();

  /// Bekor qilingan sana; `null` — faol.
  TextColumn get cancelledOn =>
      text().map(const LocalDateConverter()).nullable()();

  @override
  List<String> get customConstraints => ['CHECK (amount_minor > 0)'];
}

/// Haftalik konvert (SPEC 2B.6). Kategoriyalarga bog'lanadi: shu
/// kategoriyadagi xarajat (naqd ham, karta ham) konvertdan ayiriladi.
@DataClassName('EnvelopeRow')
class Envelopes extends Table with SyncColumns {
  TextColumn get title => text()();
  IntColumn get weeklyLimitMinor => integer()();
  TextColumn get currency => textEnum<CurrencyCode>()();

  /// Naqd rejim: «konvertga X so'm soling», hafta oxirida qoldiq kiritiladi.
  BoolColumn get isCash => boolean().withDefault(const Constant(true))();

  /// Bog'langan kategoriya ID'lari (vergul bilan).
  TextColumn get categoryIds => text().withDefault(const Constant(''))();
  BoolColumn get isArchived => boolean().withDefault(const Constant(false))();

  @override
  List<String> get customConstraints => ['CHECK (weekly_limit_minor > 0)'];
}

/// Konvertning bir haftasi: limit surati va yopilgandagi qoldiq.
@DataClassName('EnvelopePeriodRow')
class EnvelopePeriods extends Table with SyncColumns {
  TextColumn get envelopeId => text().references(Envelopes, #id)();
  TextColumn get weekStart => text().map(const LocalDateConverter())();
  IntColumn get limitMinor => integer()();
  TextColumn get currency => textEnum<CurrencyCode>()();

  /// Yopilganda qolgan pul (naqdda — foydalanuvchi kiritgan).
  IntColumn get leftoverMinor => integer().nullable()();
  DateTimeColumn get closedAt => dateTime().nullable()();
}

/// «Qutqarilgan pul» yozuvlari (SPEC 2B.7).
@DataClassName('SavingsRescueRow')
class SavingsRescues extends Table with SyncColumns {
  TextColumn get kind => textEnum<RescueKind>()();
  IntColumn get amountMinor => integer()();
  TextColumn get currency => textEnum<CurrencyCode>()();

  /// Obuna, konvert davri yoki «Kelajagim» tranzaksiyasi ID.
  TextColumn get sourceId => text().nullable()();

  /// Qaysi sanaga tegishli (Toshkent).
  TextColumn get occurredOn => text().map(const LocalDateConverter())();

  @override
  List<String> get customConstraints => ['CHECK (amount_minor > 0)'];
}

// --- Sxema v8 (MVP_PLAN Vazifa 9: 3-qonun) ---

/// «Narx daftari» savatidagi mahsulot (SPEC 2C.1).
@DataClassName('PriceItemRow')
class PriceItems extends Table with SyncColumns {
  TextColumn get name => text()();

  /// O'lchov birligi (kg, dona, litr …) — foydalanuvchi matni.
  TextColumn get unit => text()();

  /// Oylik iste'mol miqdori, mingdan birlarda (1,5 kg = 1500) — shaxsiy
  /// inflyatsiya indeksidagi og'irlik.
  IntColumn get monthlyQuantityMilli =>
      integer().withDefault(const Constant(1000))();
  IntColumn get sortOrder => integer().withDefault(const Constant(0))();
  BoolColumn get isArchived => boolean().withDefault(const Constant(false))();

  @override
  List<String> get customConstraints => [
    'CHECK (monthly_quantity_milli > 0)',
  ];
}

/// Mahsulot narxi bir sanada (`PricePoint`, SPEC 2C.1).
@DataClassName('PricePointRow')
class PricePoints extends Table with SyncColumns {
  TextColumn get itemId => text().references(PriceItems, #id)();
  IntColumn get priceMinor => integer()();
  TextColumn get currency => textEnum<CurrencyCode>()();
  TextColumn get observedOn => text().map(const LocalDateConverter())();
  TextColumn get place => text().nullable()();

  @override
  List<String> get customConstraints => ['CHECK (price_minor > 0)'];
}

// --- Sxema v9 (MVP_PLAN Vazifa 10: 4-qonun) ---

/// Qarz to'lov rejasining bir qatori (`RepaymentSchedule`, SPEC 2D.5).
@DataClassName('DebtInstallmentRow')
class DebtInstallments extends Table with SyncColumns {
  TextColumn get debtId => text().references(Debts, #id)();
  TextColumn get dueOn => text().map(const LocalDateConverter())();
  IntColumn get amountMinor => integer()();

  /// Shundan foiz / ustama qismi (hisob uchun).
  IntColumn get interestMinor => integer().withDefault(const Constant(0))();
  TextColumn get currency => textEnum<CurrencyCode>()();

  @override
  List<String> get customConstraints => [
    'CHECK (amount_minor > 0 AND interest_minor >= 0)',
  ];
}

/// Qarzga qilingan to'lov (`DebtPayment`).
@DataClassName('DebtPaymentRow')
class DebtPayments extends Table with SyncColumns {
  TextColumn get debtId => text().references(Debts, #id)();
  IntColumn get amountMinor => integer()();
  TextColumn get currency => textEnum<CurrencyCode>()();
  TextColumn get paidOn => text().map(const LocalDateConverter())();

  /// Rejadan tashqari, muddatidan oldin qo'shimcha to'lov.
  BoolColumn get isPrepayment => boolean().withDefault(const Constant(false))();
  TextColumn get note => text().nullable()();

  /// Qo'shimcha to'lovdan ushlangan jarima / komissiya (v10, `amount` ichida).
  IntColumn get feeMinor => integer().withDefault(const Constant(0))();

  /// Kim to'ladi (oilaviy yelkadoshlik, v10); `null` — oilaning o'zi.
  TextColumn get contributorId =>
      text().nullable().references(DebtContributors, #id)();

  @override
  List<String> get customConstraints => ['CHECK (amount_minor > 0)'];
}

/// Foydalanuvchi bergan qarz (`Receivable`, SPEC 2C.7, 2D.5). Foiz maydoni
/// atayin YO'Q — ilova foizli qarz berishga yo'l qo'ymaydi.
@DataClassName('ReceivableRow')
class Receivables extends Table with SyncColumns {
  TextColumn get debtorName => text()();
  IntColumn get principalMinor => integer()();
  IntColumn get remainingMinor => integer()();
  TextColumn get currency => textEnum<CurrencyCode>()();
  TextColumn get dueDate => text().map(const LocalDateConverter())();
  TextColumn get reason => text().nullable()();
  TextColumn get note => text().nullable()();

  @override
  List<String> get customConstraints => [
    'CHECK (principal_minor > 0 AND remaining_minor >= 0)',
  ];
}

/// Oila maqsadi (`Goal`) — imkoniyat narxi taqqoslash uchun (SPEC 2D.3).
@DataClassName('GoalRow')
class Goals extends Table with SyncColumns {
  TextColumn get title => text()();
  IntColumn get targetMinor => integer()();
  TextColumn get currency => textEnum<CurrencyCode>()();
  TextColumn get targetDate =>
      text().map(const LocalDateConverter()).nullable()();

  @override
  List<String> get customConstraints => ['CHECK (target_minor > 0)'];
}

/// Qarz tilxati imzolovchisi (`LoanReceipt`, SPEC 2D.5): tomonlar va
/// guvohlar shu qurilmada ismini yozib, ekranda imzo chizadi.
@DataClassName('LoanSignerRow')
class LoanSigners extends Table with SyncColumns {
  /// Qarz yoki bergan qarz ID.
  TextColumn get documentId => text()();
  TextColumn get role => textEnum<SignerRole>()();
  TextColumn get name => text()();

  /// Imzo rasmi (PNG); `null` — hali imzolanmagan.
  BlobColumn get signaturePng => blob().nullable()();
  DateTimeColumn get signedAt => dateTime().nullable()();
}

/// Qarzni to'lashda yelkadosh (`DebtContributor`, SPEC 2D.4): oila a'zosi
/// yoki alohida yashovchi farzand. MVP'da oddiy yozuv.
@DataClassName('DebtContributorRow')
class DebtContributors extends Table with SyncColumns {
  TextColumn get debtId => text().references(Debts, #id)();
  TextColumn get name => text()();
  TextColumn get memberId => text().nullable().references(Members, #id)();

  /// Va'da qilingan oylik ulush.
  IntColumn get monthlyShareMinor => integer().nullable()();
  TextColumn get currency => textEnum<CurrencyCode>()();
}

/// Sotiladigan buyum (`SellableItem`, SPEC 2D.7).
@DataClassName('SellableItemRow')
class SellableItems extends Table with SyncColumns {
  TextColumn get name => text()();
  IntColumn get estimatedMinor => integer()();
  TextColumn get currency => textEnum<CurrencyCode>()();
  TextColumn get status => textEnum<SellableStatus>()();
  IntColumn get soldMinor => integer().nullable()();
  TextColumn get soldOn => text().map(const LocalDateConverter()).nullable()();

  /// Puli yo'naltirilgan qarz va to'lov.
  TextColumn get debtId => text().nullable().references(Debts, #id)();
  TextColumn get paymentId => text().nullable()();

  @override
  List<String> get customConstraints => [
    'CHECK (estimated_minor >= 0 AND (sold_minor IS NULL OR sold_minor > 0))',
  ];
}

/// Marosim rejasi (`CeremonyPlan`, SPEC 2D.8, v11).
@DataClassName('CeremonyPlanRow')
class CeremonyPlans extends Table with SyncColumns {
  TextColumn get title => text()();
  TextColumn get type => textEnum<CeremonyType>()();
  TextColumn get status => textEnum<CeremonyStatus>()();
  TextColumn get eventDate =>
      text().map(const LocalDateConverter()).nullable()();

  /// Tanlangan stsenariy (tasdiqlanadigani).
  TextColumn get selectedScenarioId => text().nullable()();

  /// «To'yona o'rniga jamg'arma» maqsadi.
  TextColumn get giftGoalId => text().nullable().references(Goals, #id)();

  /// Qarz bo'lsa — oyiga qancha to'lay olamiz va stavka (simulyatsiya uchun).
  IntColumn get debtMonthlyMinor => integer().nullable()();
  IntColumn get debtAnnualRateBp => integer().nullable()();
  TextColumn get currency => textEnum<CurrencyCode>()();
}

/// Marosim stsenariysi (`CeremonyScenario`): «3 kunlik, 200 kishi» va h.k.
@DataClassName('CeremonyScenarioRow')
class CeremonyScenarios extends Table with SyncColumns {
  TextColumn get planId => text().references(CeremonyPlans, #id)();
  TextColumn get name => text()();
  IntColumn get guests => integer().withDefault(const Constant(0))();
  IntColumn get sortOrder => integer().withDefault(const Constant(0))();

  @override
  List<String> get customConstraints => ['CHECK (guests >= 0)'];
}

/// Byudjet qatori (`CeremonyBudgetLine`).
@DataClassName('CeremonyBudgetLineRow')
class CeremonyBudgetLines extends Table with SyncColumns {
  TextColumn get scenarioId => text().references(CeremonyScenarios, #id)();
  TextColumn get title => text()();
  TextColumn get kind => textEnum<CeremonyLineKind>()();

  /// Bir martalik summa yoki kishi boshiga narx.
  IntColumn get amountMinor => integer()();
  TextColumn get currency => textEnum<CurrencyCode>()();
  TextColumn get source => textEnum<FundingSource>()();
  IntColumn get sortOrder => integer().withDefault(const Constant(0))();

  @override
  List<String> get customConstraints => ['CHECK (amount_minor > 0)'];
}

/// «Buni qarzsiz qanday o'tkazamiz?» muhokamasida katta a'zoning belgisi.
@DataClassName('CeremonyDiscussionMarkRow')
class CeremonyDiscussionMarks extends Table with SyncColumns {
  TextColumn get planId => text().references(CeremonyPlans, #id)();
  TextColumn get memberId => text().references(Members, #id)();
}

/// Maqsadga hissa (to'yona o'rniga jamg'arma — mehmonlar hissasi qo'lda).
@DataClassName('GoalContributionRow')
class GoalContributions extends Table with SyncColumns {
  TextColumn get goalId => text().references(Goals, #id)();
  TextColumn get contributorName => text()();
  IntColumn get amountMinor => integer()();
  TextColumn get currency => textEnum<CurrencyCode>()();
  TextColumn get receivedOn => text().map(const LocalDateConverter())();

  @override
  List<String> get customConstraints => ['CHECK (amount_minor > 0)'];
}

/// Sheriklik (`Partnership`, SPEC 2E.1, v12).
@DataClassName('PartnershipRow')
class Partnerships extends Table with SyncColumns {
  TextColumn get title => text()();
  TextColumn get type => textEnum<PartnershipType>()();
  TextColumn get status => textEnum<PartnershipStatus>()();
  TextColumn get currency => textEnum<CurrencyCode>()();
  TextColumn get startDate =>
      text().map(const LocalDateConverter()).nullable()();
  IntColumn get termMonths => integer()();
  TextColumn get reportPeriod => textEnum<ReportPeriod>()();

  /// Muddat tugaganda nima bo'ladi, nizolar qanday hal qilinadi (matn).
  TextColumn get endTerms => text()();
  TextColumn get disputeTerms => text()();

  /// Joriy shartnoma versiyasi (`partnership_contracts.version`).
  IntColumn get contractVersion => integer().withDefault(const Constant(1))();

  /// Kapital qabul qiluvchi: «bu qarz emas» tushuntirishi o'qildi.
  BoolColumn get notDebtAcknowledged =>
      boolean().withDefault(const Constant(false))();

  /// Kamayib boruvchi musharaka: oyiga to'lov (buyout).
  IntColumn get buyoutMonthlyMinor => integer().nullable()();
}

/// Sherik (`PartnerRole`); `is_me` — ilova egasining oilasi.
@DataClassName('PartnerRow')
class Partners extends Table with SyncColumns {
  TextColumn get partnershipId => text().references(Partnerships, #id)();
  TextColumn get name => text()();
  TextColumn get role => textEnum<PartnerRole>()();
  BoolColumn get isMe => boolean().withDefault(const Constant(false))();

  /// Sof foydadagi ulush (bp); yig'indi 10 000.
  IntColumn get profitShareBp => integer()();
  IntColumn get sortOrder => integer().withDefault(const Constant(0))();

  @override
  List<String> get customConstraints => [
    'CHECK (profit_share_bp >= 0 AND profit_share_bp <= 10000)',
  ];
}

/// Kiritilgan kapital (`CapitalContribution`): pul yoki uskuna.
@DataClassName('CapitalContributionRow')
class CapitalContributions extends Table with SyncColumns {
  TextColumn get partnershipId => text().references(Partnerships, #id)();
  TextColumn get partnerId => text().references(Partners, #id)();
  TextColumn get kind => textEnum<CapitalKind>()();
  TextColumn get title => text()();
  IntColumn get amountMinor => integer()();
  TextColumn get currency => textEnum<CurrencyCode>()();

  @override
  List<String> get customConstraints => ['CHECK (amount_minor > 0)'];
}

/// Shartnoma versiyasi (`PartnershipContract`): shartlar surati (JSON) —
/// har o'zgarish yangi versiya va qayta imzo (imzolar `loan_signers` da,
/// `document_id` = shu qator ID si).
@DataClassName('PartnershipContractRow')
class PartnershipContracts extends Table with SyncColumns {
  TextColumn get partnershipId => text().references(Partnerships, #id)();
  IntColumn get contractVersion => integer()();
  TextColumn get templateId => text()();
  TextColumn get termsJson => text()();
}

/// Kamayib boruvchi musharaka: ulush sotib olish to'lovi.
@DataClassName('BuyoutPaymentRow')
class BuyoutPayments extends Table with SyncColumns {
  TextColumn get partnershipId => text().references(Partnerships, #id)();
  IntColumn get amountMinor => integer()();
  TextColumn get currency => textEnum<CurrencyCode>()();
  TextColumn get paidOn => text().map(const LocalDateConverter())();

  @override
  List<String> get customConstraints => ['CHECK (amount_minor > 0)'];
}

/// Kapital qabul qilishga oilaviy rozilik (katta a'zolar).
@DataClassName('PartnershipConsentRow')
class PartnershipConsents extends Table with SyncColumns {
  TextColumn get partnershipId => text().references(Partnerships, #id)();
  TextColumn get memberId => text().references(Members, #id)();
}

/// Sheriklik kassa daftari yozuvi (`VentureEntry`, SPEC 2E.3, v13). Biznes
/// puli uy pulidan alohida — xonadon byudjetiga faqat taqsimlangan ulush.
@DataClassName('VentureEntryRow')
class VentureEntries extends Table with SyncColumns {
  TextColumn get partnershipId => text().references(Partnerships, #id)();
  TextColumn get kind => textEnum<VentureEntryKind>()();
  TextColumn get title => text()();

  /// Har doim musbat; tuzatish (`correction`) — ishorali.
  IntColumn get amountMinor => integer()();
  TextColumn get currency => textEnum<CurrencyCode>()();
  TextColumn get occurredOn => text().map(const LocalDateConverter())();
  TextColumn get note => text().nullable()();

  /// Chek yoki dalil rasmi (baza SQLCipher bilan shifrlangan).
  BlobColumn get receiptImage => blob().nullable()();
}

/// Yopilgan davr va taqsimot (`ProfitDistribution`). Yopilgan davr
/// o'zgarmaydi — tuzatish faqat keyingi davrda yangi yozuv bilan.
@DataClassName('VenturePeriodRow')
class VenturePeriods extends Table with SyncColumns {
  TextColumn get partnershipId => text().references(Partnerships, #id)();
  TextColumn get startDate => text().map(const LocalDateConverter())();
  TextColumn get endDate => text().map(const LocalDateConverter())();
  IntColumn get incomeMinor => integer()();
  IntColumn get expenseMinor => integer()();

  /// Sof foyda (manfiy — zarar).
  IntColumn get netMinor => integer()();
  IntColumn get buyoutMinor => integer().withDefault(const Constant(0))();
  TextColumn get currency => textEnum<CurrencyCode>()();
  BoolColumn get negligence => boolean().withDefault(const Constant(false))();
  TextColumn get negligenceNote => text().nullable()();

  /// Mening ulushim uy byudjetiga tushgan daromad yozuvi.
  TextColumn get incomeId => text().nullable()();
}

/// Davr taqsimotidagi sherik ulushi (manfiy — zarar ulushi).
@DataClassName('DistributionShareRow')
class DistributionShares extends Table with SyncColumns {
  TextColumn get periodId => text().references(VenturePeriods, #id)();
  TextColumn get partnerId => text().references(Partners, #id)();
  IntColumn get amountMinor => integer()();

  /// Buyout: ulushdan ayirilgan (+ kapital egasiga qo'shilgan) summa.
  IntColumn get buyoutMinor => integer().withDefault(const Constant(0))();
  TextColumn get currency => textEnum<CurrencyCode>()();
}

/// Oiladagi hunar (`Skill`, SPEC 2E.4).
@DataClassName('SkillRow')
class Skills extends Table with SyncColumns {
  TextColumn get name => text()();
  TextColumn get memberId => text().nullable().references(Members, #id)();
}

/// Hunardan ish g'oyasi (`VentureIdea`): CAPEX, oylik kirim / xarajat,
/// uch stsenariy.
@DataClassName('VentureIdeaRow')
class VentureIdeas extends Table with SyncColumns {
  TextColumn get title => text()();
  TextColumn get skillId => text().nullable().references(Skills, #id)();
  IntColumn get pessimisticIncomeMinor => integer()();
  IntColumn get baseIncomeMinor => integer()();
  IntColumn get optimisticIncomeMinor => integer()();
  IntColumn get monthlyExpenseMinor => integer()();

  /// Sheriklik bo'lsa — mening foyda ulushim (bp); yolg'iz — 10 000.
  IntColumn get myShareBp => integer().withDefault(const Constant(10000))();
  TextColumn get currency => textEnum<CurrencyCode>()();
}

/// G'oyaning boshlang'ich xarajati (CAPEX) bandi.
@DataClassName('IdeaCapexItemRow')
class IdeaCapexItems extends Table with SyncColumns {
  TextColumn get ideaId => text().references(VentureIdeas, #id)();
  TextColumn get title => text()();
  IntColumn get amountMinor => integer()();
  TextColumn get currency => textEnum<CurrencyCode>()();

  @override
  List<String> get customConstraints => ['CHECK (amount_minor > 0)'];
}

/// «Kafolatlangan foyda» detektori natijasi (`OfferCheck`, SPEC 2E.5).
@DataClassName('OfferCheckRow')
class OfferChecks extends Table with SyncColumns {
  TextColumn get title => text()();

  /// Savol kodi → javob (`yes` / `no` / `unknown`), JSON.
  TextColumn get answersJson => text()();
  TextColumn get verdict => textEnum<OfferVerdict>()();

  // --- v16 (7-qonun, SPEC 2G.3, 2G.6) ---

  /// Taxminiy qo'yiladigan summa (minor) va valyuta.
  IntColumn get amountMinor => integer().nullable()();
  TextColumn get currency => textEnum<CurrencyCode>().nullable()();

  /// Va'da qilingan oylik foyda (bp) — yillikka aylantirib ko'rsatiladi.
  IntColumn get promisedMonthlyBp => integer().nullable()();

  /// Kim bilan maslahatlashildi («to'xta, maslahatlash»).
  TextColumn get advisor => text().nullable()();
  TextColumn get decision => textEnum<OfferDecision>().nullable()();
  DateTimeColumn get decidedAt => dateTime().nullable()();
}

// --- Sxema v15 (MVP_PLAN Vazifa 9A: 6-qonun) ---

/// Kelishuv (`Agreement`, SPEC 2F.1). Tilxat (`LOAN`) va sheriklik
/// shartnomasi (`PARTNERSHIP`) ham shu dvigatelning turlari.
@DataClassName('AgreementRow')
class Agreements extends Table with SyncColumns {
  TextColumn get type => textEnum<AgreementType>()();
  TextColumn get status => textEnum<AgreementStatus>()();
  TextColumn get title => text()();
  TextColumn get effectiveFrom => text().map(const LocalDateConverter())();
  IntColumn get currentVersion => integer().withDefault(const Constant(1))();

  /// Bog'langan yozuv (qarz, bergan qarz, sheriklik).
  TextColumn get source => textEnum<AgreementSource>().nullable()();
  TextColumn get sourceId => text().nullable()();

  /// Og'zaki kelishuvdan yozib olingan (SPEC 2F.9).
  BoolColumn get oral => boolean().withDefault(const Constant(false))();

  /// 9A dan oldin imzolangan hujjatdan ko'chirilgan.
  BoolColumn get legacy => boolean().withDefault(const Constant(false))();
  TextColumn get reviewDate =>
      text().map(const LocalDateConverter()).nullable()();
}

/// Kelishuv versiyasi: 9 savol javoblari (JSON). Imzolar `loan_signers` da
/// (`document_id` = shu qator ID si). Imzolangan versiya o'zgarmaydi.
@DataClassName('AgreementVersionRow')
class AgreementVersions extends Table with SyncColumns {
  TextColumn get agreementId => text().references(Agreements, #id)();
  IntColumn get versionNo => integer()();
  TextColumn get answersJson => text()();
  TextColumn get note => text().nullable()();

  @override
  List<String> get customConstraints => ['UNIQUE (agreement_id, version_no)'];
}

/// Append-only hisob jurnali (SPEC 2F.6): `UPDATE` / `DELETE` trigger bilan
/// taqiqlangan; tuzatish — `CORRECTION` yozuvi. Xesh-zanjir har kelishuvda.
@DataClassName('JournalEntryRow')
class JournalEntries extends Table with SyncColumns {
  TextColumn get agreementId => text().references(Agreements, #id)();
  IntColumn get seq => integer()();

  /// `JournalKind.code` (masalan, `LOAN_PAYMENT`).
  TextColumn get kind => text()();
  TextColumn get partyId => text().nullable()();
  IntColumn get amountMinor => integer().nullable()();
  TextColumn get currency => textEnum<CurrencyCode>().nullable()();
  TextColumn get entryDate => text().map(const LocalDateConverter())();
  TextColumn get note => text().nullable()();
  TextColumn get refId => text().nullable()();
  TextColumn get prevHash => text()();
  TextColumn get hash => text()();

  @override
  List<String> get customConstraints => ['UNIQUE (agreement_id, seq)'];
}

// --- Sxema v17 (MVP_PLAN Vazifa 14C: 8-qonun) ---

/// «Bir soatim qancha turadi?» hisobi (`HourlySnapshot`, SPEC 2H.1).
@DataClassName('HourlySnapshotRow')
class HourlySnapshots extends Table with SyncColumns {
  TextColumn get memberId => text().nullable().references(Members, #id)();
  IntColumn get incomeMinor => integer()();
  TextColumn get currency => textEnum<CurrencyCode>()();
  IntColumn get minutesPerDay => integer()();
  IntColumn get daysPerMonth => integer()();
  IntColumn get maxMinutesPerDay => integer()();

  /// Hisoblangan soat qiymati (minor) — tarixda solishtirish uchun.
  IntColumn get hourlyMinor => integer()();

  @override
  List<String> get customConstraints => [
    'CHECK (income_minor >= 0)',
    'CHECK (minutes_per_day BETWEEN 1 AND 1440)',
    'CHECK (max_minutes_per_day BETWEEN 1 AND 1440)',
    'CHECK (days_per_month BETWEEN 1 AND 31)',
  ];
}

/// O'qish maqsadi (`LearningGoal`, SPEC 2H.2): soatni qimmatlashtiradigan
/// bilim yoki mahorat.
@DataClassName('LearningGoalRow')
class LearningGoals extends Table with SyncColumns {
  TextColumn get memberId => text().nullable().references(Members, #id)();
  TextColumn get title => text()();

  /// Nega aynan shu bilim (qaysi ishni yaxshiroq qilish imkonini beradi).
  TextColumn get why => text().nullable()();
  IntColumn get baseHourlyMinor => integer()();
  IntColumn get targetHourlyMinor => integer()();
  TextColumn get currency => textEnum<CurrencyCode>()();
  TextColumn get status => textEnum<LearningGoalStatus>()();
  DateTimeColumn get closedAt => dateTime().nullable()();

  @override
  List<String> get customConstraints => [
    'CHECK (base_hourly_minor >= 0)',
    'CHECK (target_hourly_minor >= 0)',
  ];
}

/// O'qish yo'li (`LearningItem`, SPEC 2H.3); kurs tekshiruvi (2H.5) natijasi
/// ham shu yerda.
@DataClassName('LearningItemRow')
class LearningItems extends Table with SyncColumns {
  TextColumn get goalId => text().references(LearningGoals, #id)();
  TextColumn get kind => textEnum<LearningItemKind>()();
  TextColumn get title => text()();

  /// «Buni o'rgangach nimani qila olaman?» — majburiy.
  TextColumn get purpose => text()();
  IntColumn get costMinor => integer().nullable()();
  TextColumn get costCurrency => textEnum<CurrencyCode>().nullable()();
  IntColumn get studyMinutes => integer().nullable()();
  TextColumn get status => textEnum<LearningItemStatus>()();

  /// Erishilgan natija (`DONE` da).
  TextColumn get outcome => text().nullable()();

  /// Kurs tekshiruvi: savol → javob (JSON) va baho.
  TextColumn get courseAnswersJson => text().nullable()();
  TextColumn get courseVerdict => textEnum<OfferVerdict>().nullable()();
  DateTimeColumn get completedAt => dateTime().nullable()();

  @override
  List<String> get customConstraints => [
    'CHECK (cost_minor IS NULL OR cost_minor >= 0)',
    'CHECK (study_minutes IS NULL OR study_minutes >= 0)',
  ];
}

/// «O'rgatganlarim» yozuvi (`TeachingEntry`, SPEC 2H.6).
@DataClassName('TeachingEntryRow')
class TeachingEntries extends Table with SyncColumns {
  TextColumn get memberId => text().nullable().references(Members, #id)();

  /// Kimga: ism yoki «hamkasb», «farzandim».
  TextColumn get learner => text()();
  TextColumn get topic => text()();
  TextColumn get taughtOn => text().map(const LocalDateConverter())();
  IntColumn get minutes => integer().nullable()();
  TextColumn get note => text().nullable()();
}
