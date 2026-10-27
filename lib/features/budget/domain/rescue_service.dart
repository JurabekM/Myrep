import 'package:baraka_daftari/core/domain/enums.dart';
import 'package:baraka_daftari/core/domain/sync_meta.dart';
import 'package:baraka_daftari/core/errors/data_exceptions.dart';
import 'package:baraka_daftari/core/money/money.dart';
import 'package:baraka_daftari/core/time/calendar.dart';
import 'package:baraka_daftari/core/time/clock.dart';
import 'package:baraka_daftari/features/audit/domain/monthly_report.dart';
import 'package:baraka_daftari/features/budget/domain/budget_math.dart';
import 'package:baraka_daftari/features/budget/domain/rescue.dart';
import 'package:baraka_daftari/features/expenses/domain/expense.dart';
import 'package:baraka_daftari/features/household/domain/household.dart';
import 'package:baraka_daftari/features/vault/domain/vault_service.dart';
import 'package:meta/meta.dart';

/// Hafta va oy bo'yicha «Qutqarilgan pul».
@immutable
final class RescueOverview {
  const RescueOverview({
    required this.week,
    required this.weekRange,
    required this.month,
    required this.monthRange,
    this.baseline,
  });

  final RescueBreakdown week;
  final DateRange weekRange;
  final RescueBreakdown month;
  final DateRange monthRange;

  /// Havas taqqoslanadigan bazaviy oy; `null` — hali yo'q.
  final DateRange? baseline;
}

/// «Qutqarilgan pul» (SPEC 2B.7) — 2-qonunning asosiy KPI'si va uni bir
/// bosishda «Kelajagim»ga o'tkazish.
class RescueService {
  RescueService({
    required HouseholdRepository households,
    required ExpenseRepository expenses,
    required CategoryRepository categories,
    required MonthlyReportRepository reports,
    required SavingsRescueRepository rescues,
    required VaultService vault,
    required SyncMetaFactory metaFactory,
    required Clock clock,
  }) : _households = households,
       _expenses = expenses,
       _categories = categories,
       _reports = reports,
       _rescues = rescues,
       _vault = vault,
       _meta = metaFactory,
       _clock = clock;

  static const errNothingToTransfer = 'rescue_nothing_to_transfer';

  final HouseholdRepository _households;
  final ExpenseRepository _expenses;
  final CategoryRepository _categories;
  final MonthlyReportRepository _reports;
  final SavingsRescueRepository _rescues;
  final VaultService _vault;
  final SyncMetaFactory _meta;
  final Clock _clock;

  LocalDate get _today => Tashkent.dateOf(_clock.nowUtc());

  /// Bazaviy oy: tanlangani, bo'lmasa birinchi audit oyi.
  Future<DateRange?> baseline() async {
    final h = await _households.current();
    final start =
        h.rescueBaselineStart ??
        (await _reports.earliest(h.meta.id))?.periodStart;
    return start == null ? null : h.calendar.monthOf(start);
  }

  /// Bazaviy oyni tanlash ([date] — shu oy ichidagi istalgan kun).
  Future<void> setBaseline(LocalDate date) async {
    final h = await _households.current();
    await _households.update(
      h.copyWith(rescueBaselineStart: h.calendar.monthOf(date).start),
    );
  }

  Future<Money> _havasIn(Household h, DateRange range) async {
    final categories = {
      for (final c in await _categories.listActive(h.meta.id)) c.meta.id: c,
    };
    var total = Money.zero(h.baseCurrency);
    for (final e in await _expenses.listInRange(h.meta.id, range)) {
      if (e.amount.currency == total.currency &&
          countsAsHavas(e, categories[e.categoryId])) {
        total += e.amount;
      }
    }
    return total;
  }

  Future<RescueBreakdown> _breakdown(
    Household h,
    DateRange period,
    DateRange? base,
    List<SavingsRescue> rows,
  ) async {
    final today = _today;
    final elapsed = DateRange(period.start, today.plusDays(1));
    final c = h.baseCurrency;
    Money sumOf(RescueKind kind) => Money.sum([
      for (final r in rows)
        if (r.kind == kind &&
            r.amount.currency == c &&
            elapsed.contains(r.occurredOn))
          r.amount,
    ], c);
    return computeRescue(
      currency: c,
      elapsedDays: elapsed.lengthInDays,
      currentHavas: await _havasIn(h, elapsed),
      baselineHavas: base == null ? null : await _havasIn(h, base),
      baselineDays: base?.lengthInDays ?? 30,
      subscriptions: subscriptionSavings(
        currency: c,
        cancelled: [
          for (final r in rows)
            if (r.kind == RescueKind.subscription) (r.amount, r.occurredOn),
        ],
        period: period,
        today: today,
      ),
      envelopeLeftovers: sumOf(RescueKind.envelopeLeftover),
      transferred: sumOf(RescueKind.transfer),
    );
  }

  Future<RescueOverview> overview() async {
    final h = await _households.current();
    final today = _today;
    final rows = await _rescues.listActive(h.meta.id);
    final base = await baseline();
    final week = h.calendar.weekOf(today);
    final month = h.calendar.monthOf(today);
    return RescueOverview(
      week: await _breakdown(h, week, base, rows),
      weekRange: week,
      month: await _breakdown(h, month, base, rows),
      monthRange: month,
      baseline: base,
    );
  }

  /// Qutqarilganni «Kelajagim»ga o'tkazish (haftalik mavjud qismdan ko'p
  /// emas — bir pul ikki marta o'tkazilmasin).
  Future<Money> transferWeek() async {
    final o = await overview();
    final amount = o.week.available;
    if (!amount.isPositive) {
      throw const DomainRuleException(errNothingToTransfer);
    }
    final tx = await _vault.depositRescue(amount);
    await _rescues.add(
      SavingsRescue(
        meta: _meta.create(tx.meta.householdId),
        kind: RescueKind.transfer,
        amount: amount,
        occurredOn: _today,
        sourceId: tx.meta.id,
      ),
    );
    return amount;
  }

  /// Qutqarilganni qarzga qo'shimcha to'lov qilish (SPEC 2D.2: qo'shimcha
  /// to'lov manbalaridan biri). [pay] to'lovni amalga oshirib, uning ID sini
  /// qaytaradi; [max] — qarz qolganidan oshmasin.
  Future<Money> transferWeekTo(
    Future<String> Function(Money amount) pay, {
    Money? max,
  }) async {
    final o = await overview();
    var amount = o.week.available;
    if (max != null && amount > max) amount = max;
    if (!amount.isPositive) {
      throw const DomainRuleException(errNothingToTransfer);
    }
    final paymentId = await pay(amount);
    await _rescues.add(
      SavingsRescue(
        meta: _meta.create((await _households.current()).meta.id),
        kind: RescueKind.transfer,
        amount: amount,
        occurredOn: _today,
        sourceId: paymentId,
      ),
    );
    return amount;
  }
}
