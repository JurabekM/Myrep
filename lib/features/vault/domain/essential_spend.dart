import 'package:baraka_daftari/core/domain/enums.dart';
import 'package:baraka_daftari/core/money/money.dart';
import 'package:baraka_daftari/core/time/calendar.dart';
import 'package:baraka_daftari/core/time/clock.dart';
import 'package:baraka_daftari/features/budget/domain/budget_math.dart';
import 'package:baraka_daftari/features/expenses/domain/expense.dart';
import 'package:baraka_daftari/features/household/domain/household.dart';
import 'package:baraka_daftari/features/vault/domain/reserve.dart';

/// Zaxira maqsadi uchun oylik zarur + kerak xarajatlar (SPEC 2C.3): oxirgi
/// 3 ta to'liq oy (oylik kuni bo'yicha) o'rtachasi; ma'lumot kam bo'lsa —
/// foydalanuvchi kiritgan taxminiy summa.
class EssentialSpendService {
  EssentialSpendService({
    required HouseholdRepository households,
    required ExpenseRepository expenses,
    required CategoryRepository categories,
    required Clock clock,
  }) : _households = households,
       _expenses = expenses,
       _categories = categories,
       _clock = clock;

  static const months = 3;

  final HouseholdRepository _households;
  final ExpenseRepository _expenses;
  final CategoryRepository _categories;
  final Clock _clock;

  /// Oxirgi [months] ta to'liq oyning (eng eskisi birinchi) zarur + kerak
  /// jami.
  Future<List<Money>> monthTotals() async {
    final h = await _households.current();
    final c = h.baseCurrency;
    final categories = {
      for (final cat in await _categories.listActive(h.meta.id))
        cat.meta.id: cat,
    };
    var month = h.calendar.monthOf(Tashkent.dateOf(_clock.nowUtc()));
    final ranges = <DateRange>[];
    for (var i = 0; i < months; i++) {
      month = h.calendar.monthOf(month.start.plusDays(-1));
      ranges.insert(0, month);
    }
    return [
      for (final r in ranges)
        Money.sum([
          for (final e in await _expenses.listInRange(h.meta.id, r))
            if (e.amount.currency == c &&
                switch (effectiveNecessity(e, categories[e.categoryId])) {
                  Necessity.zarur || Necessity.kerak => true,
                  _ => false,
                })
              e.amount,
        ], c),
    ];
  }

  /// Zaxira maqsadi asosi: 3+ oylik ma'lumot bo'lsa — haqiqiy jami, aks
  /// holda foydalanuvchi kiritgan oylik taxmin.
  Future<({EssentialBasis? basis, bool fromEstimate})> monthly() async {
    final h = await _households.current();
    final basis = essentialBasis(monthTotals: await monthTotals());
    if (basis != null) return (basis: basis, fromEstimate: false);
    final estimate = h.reserveMonthlyEstimate;
    return (
      basis: estimate == null
          ? null
          : EssentialBasis(total: estimate, months: 1),
      fromEstimate: true,
    );
  }

  /// Ma'lumot 3 oydan kam bo'lganda taxminiy summa.
  Future<void> setEstimate(Money? monthly) async {
    final h = await _households.current();
    await _households.update(h.copyWith(reserveMonthlyEstimate: monthly));
  }
}
