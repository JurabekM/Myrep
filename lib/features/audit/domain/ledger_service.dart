import 'package:baraka_daftari/core/domain/enums.dart';
import 'package:baraka_daftari/core/domain/sync_meta.dart';
import 'package:baraka_daftari/core/errors/data_exceptions.dart';
import 'package:baraka_daftari/core/money/money.dart';
import 'package:baraka_daftari/core/time/calendar.dart';
import 'package:baraka_daftari/core/time/clock.dart';
import 'package:baraka_daftari/features/audit/domain/month_ledger.dart';
import 'package:baraka_daftari/features/audit/domain/monthly_report.dart';
import 'package:baraka_daftari/features/expenses/domain/expense.dart';
import 'package:baraka_daftari/features/household/domain/household.dart';
import 'package:baraka_daftari/features/income/domain/income.dart';
import 'package:baraka_daftari/features/obligations/domain/obligation.dart';
import 'package:baraka_daftari/features/vault/domain/habit.dart';
import 'package:baraka_daftari/features/vault/domain/vault.dart';
import 'package:meta/meta.dart';

/// Bosh ekran ko'rsatkichlari (SPEC 9).
@immutable
final class HomeKpis {
  const HomeKpis({
    required this.period,
    required this.auditPeriod,
    required this.paidToSelf,
    required this.vaultBalance,
    required this.habit,
    required this.monthResult,
    required this.income,
    required this.lastAudit,
  });

  final DateRange period;

  /// Oylik audit davri (o'tgan oy).
  final DateRange auditPeriod;

  /// 1-raqam: «O'zingizga to'langan (shu oy)» — «Kelajagim»ga ajratilgan
  /// (avval yigʻilgan pulsiz).
  final Money paidToSelf;
  final Money vaultBalance;
  final HabitStats habit;

  /// Oy yakuni (+/−): daromad − (yozilgan xarajat + majburiyat qoldig'i +
  /// sof jamg'arma).
  final Money monthResult;
  final Money income;
  final MonthlyReport? lastAudit;

  /// O'tgan oy uchun audit o'tkazilganmi.
  bool get auditDone =>
      lastAudit != null && !lastAudit!.periodStart.isBefore(auditPeriod.start);
}

/// Oy hisobi, oylik audit va bosh ekran KPI'lari.
class LedgerService {
  LedgerService({
    required HouseholdRepository households,
    required IncomeRepository incomes,
    required ExpenseRepository expenses,
    required CategoryRepository categories,
    required ObligationRepository obligations,
    required AssetRepository assets,
    required VaultTransactionRepository vaultTransactions,
    required MonthlyReportRepository reports,
    required SyncMetaFactory metaFactory,
    required Clock clock,
  }) : _households = households,
       _incomes = incomes,
       _expenses = expenses,
       _categories = categories,
       _obligations = obligations,
       _assets = assets,
       _vaultTxs = vaultTransactions,
       _reports = reports,
       _meta = metaFactory,
       _clock = clock;

  static const errNothingToMark = 'audit_nothing_to_mark';

  final HouseholdRepository _households;
  final IncomeRepository _incomes;
  final ExpenseRepository _expenses;
  final CategoryRepository _categories;
  final ObligationRepository _obligations;
  final AssetRepository _assets;
  final VaultTransactionRepository _vaultTxs;
  final MonthlyReportRepository _reports;
  final SyncMetaFactory _meta;
  final Clock _clock;

  LocalDate get _today => Tashkent.dateOf(_clock.nowUtc());

  Future<DateRange> currentPeriod() async =>
      (await _households.current()).calendar.monthOf(_today);

  /// Oylik audit davri — o'tgan oy (oylik kuni sozlamasi bilan).
  Future<DateRange> previousPeriod() async =>
      (await _households.current()).calendar.previousMonthOf(_today);

  /// [period] dan oldingi davr.
  Future<DateRange> previousPeriodOf(DateRange period) async =>
      (await _households.current()).calendar.monthOf(
        period.start.plusDays(-1),
      );

  Future<MonthLedger> ledgerFor(DateRange period) async {
    final household = await _households.current();
    final hh = household.meta.id;
    return buildMonthLedger(
      period: period,
      currency: household.baseCurrency,
      incomes: await _incomes.listInRange(hh, period),
      expenses: await _expenses.listInRange(hh, period),
      obligations: await _obligations.listActive(hh),
      vaultTransactions: await _allVaultTransactions(hh),
    );
  }

  /// Ikkala jamg'arma (qorovul + o'sadigan, SPEC 2C.3) tranzaksiyalari.
  Future<List<VaultTransaction>> _allVaultTransactions(String hh) async => [
    for (final v in await _assets.listVaults(hh))
      ...await _vaultTxs.listForVault(v.meta.id),
  ];

  /// Kategoriya ID → standart kalit (foydalanuvchi kategoriyasida `null`).
  Future<Map<String, CategoryKey?>> categoryKeys() async {
    final hh = (await _households.current()).meta.id;
    return {
      for (final c in await _categories.listActive(hh)) c.meta.id: c.systemKey,
    };
  }

  Future<Map<MoneyOwner, Money>> whoseMoneyFor(DateRange period) async =>
      whoseMoney(await ledgerFor(period), await categoryKeys());

  Future<HomeKpis> homeKpis() async {
    final household = await _households.current();
    final hh = household.meta.id;
    final period = household.calendar.monthOf(_today);
    final ledger = await ledgerFor(period);
    final txs = await _allVaultTransactions(hh);
    return HomeKpis(
      period: period,
      auditPeriod: household.calendar.previousMonthOf(_today),
      paidToSelf: ledger.savingsDeposited,
      vaultBalance: Money.sum([
        for (final v in await _assets.listVaults(hh))
          await _vaultTxs.balance(v.meta.id, household.baseCurrency),
      ], household.baseCurrency),
      habit: computeHabit(
        savingInstants: [
          for (final t in txs)
            if (t.type == VaultTransactionType.deposit &&
                t.reason != VaultTransactionReason.initial)
              t.occurredAt,
        ],
        calendar: household.calendar,
        today: _today,
      ),
      monthResult: ledger.unexplained,
      income: ledger.income,
      lastAudit: await _reports.latest(hh),
    );
  }

  /// Audit davri uchun kiritiladigan yozuv vaqti: davrning oxirgi kuni,
  /// Toshkent 12:00 (davr ichida bo'lishi kafolatlanadi).
  DateTime instantInside(DateRange period) => Tashkent.startOfDay(
    period.endExclusive.plusDays(-1),
  ).add(const Duration(hours: 12));

  /// Izohsiz summani «mayda kundalik xarajatlar» deb belgilash.
  Future<Expense> markUnexplainedAsDailySmall(DateRange period) async {
    final ledger = await ledgerFor(period);
    final amount = ledger.unexplained;
    if (!amount.isPositive) throw const DomainRuleException(errNothingToMark);
    final hh = (await _households.current()).meta.id;
    final category = await _categories.findBySystemKey(
      hh,
      CategoryKey.dailySmall,
    );
    return _expenses.add(
      Expense(
        meta: _meta.create(hh),
        amount: amount,
        categoryId: category!.meta.id,
        channel: PaymentChannel.cash,
        spentAt: instantInside(period),
      ),
    );
  }

  /// Auditni yakunlash: natija `MonthlyReport` ga yoziladi (qayta o'tkazilsa
  /// yangilanadi).
  Future<MonthlyReport> completeAudit(DateRange period) async {
    final ledger = await ledgerFor(period);
    final hh = (await _households.current()).meta.id;
    final existing = await _reports.findByPeriodStart(hh, period.start);
    final report = MonthlyReport(
      meta: existing?.meta ?? _meta.create(hh),
      periodStart: period.start,
      periodEnd: period.endExclusive,
      income: ledger.income,
      obligations: ledger.obligationsUnrecorded,
      expenses: ledger.expenses,
      savings: ledger.netSavings,
      unexplained: ledger.unexplained,
      completedAt: _clock.nowUtc(),
    );
    return existing == null ? _reports.add(report) : _reports.update(report);
  }

  Future<MonthlyReport?> reportFor(DateRange period) async =>
      _reports.findByPeriodStart(
        (await _households.current()).meta.id,
        period.start,
      );
}
