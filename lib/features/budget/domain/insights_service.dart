import 'package:baraka_daftari/core/domain/enums.dart';
import 'package:baraka_daftari/core/domain/sync_meta.dart';
import 'package:baraka_daftari/core/errors/data_exceptions.dart';
import 'package:baraka_daftari/core/money/allocation.dart';
import 'package:baraka_daftari/core/money/money.dart';
import 'package:baraka_daftari/core/time/calendar.dart';
import 'package:baraka_daftari/core/time/clock.dart';
import 'package:baraka_daftari/features/budget/domain/budget.dart';
import 'package:baraka_daftari/features/budget/domain/budget_math.dart';
import 'package:baraka_daftari/features/expenses/domain/expense.dart';
import 'package:baraka_daftari/features/household/domain/household.dart';
import 'package:baraka_daftari/features/obligations/domain/obligation.dart';
import 'package:meta/meta.dart';

/// Bitta kategoriya (yoki odat) uchun jamlash.
@immutable
final class RollupLine<T> {
  const RollupLine({required this.subject, required this.rollup});

  final T subject;
  final Rollup rollup;
}

/// Jamlash effekti va taqqoslash (SPEC 2B.1).
@immutable
final class SpendingInsights {
  const SpendingInsights({
    required this.window,
    required this.lines,
    this.reference,
  });

  /// Oxirgi [Rollup.windowDays] kun (bugun ham).
  final DateRange window;

  /// Mayda kategoriyalar, yillik jami bo'yicha kamayish tartibida.
  final List<RollupLine<Category>> lines;

  /// Taqqoslash uchun majburiyat (ijara, bo'lmasa eng kattasi).
  final Obligation? reference;

  /// «Bu summa ijarangizning X%i» — bazis punktda.
  int? shareOfReference(Money perMonth) {
    final r = reference;
    if (r == null || r.amount.currency != perMonth.currency) return null;
    return ratioBasisPoints(perMonth, r.amount);
  }
}

/// Mayda xarajatlar jamlanishi, odatlar va «Juma shirinligi».
class InsightsService {
  InsightsService({
    required HouseholdRepository households,
    required ExpenseRepository expenses,
    required CategoryRepository categories,
    required ObligationRepository obligations,
    required HabitRepository habits,
    required ScheduledTreatRepository treats,
    required SyncMetaFactory metaFactory,
    required Clock clock,
  }) : _households = households,
       _expenses = expenses,
       _categories = categories,
       _obligations = obligations,
       _habits = habits,
       _treats = treats,
       _meta = metaFactory,
       _clock = clock;

  static const windowDays = 30;
  static const errTitleRequired = 'title_required';
  static const errNotPositive = 'amount_must_be_positive';
  static const errBadWeekday = 'treat_bad_weekday';

  /// Majburiyat bilan qoplanadigan, asosiy oziq-ovqat va sadaqa — «mayda»
  /// (teshik) emas.
  static const _notSmall = <CategoryKey?>{
    CategoryKey.groceries,
    CategoryKey.rent,
    CategoryKey.credit,
    CategoryKey.utilities,
    CategoryKey.sadaqa,
  };

  final HouseholdRepository _households;
  final ExpenseRepository _expenses;
  final CategoryRepository _categories;
  final ObligationRepository _obligations;
  final HabitRepository _habits;
  final ScheduledTreatRepository _treats;
  final SyncMetaFactory _meta;
  final Clock _clock;

  DateRange _window() {
    final today = Tashkent.dateOf(_clock.nowUtc());
    return DateRange(today.plusDays(1 - windowDays), today.plusDays(1));
  }

  Future<SpendingInsights> spending() async {
    final h = await _households.current();
    final hh = h.meta.id;
    final window = _window();
    final categories = await _categories.listActive(hh);
    final totals = <String, Money>{};
    for (final e in await _expenses.listInRange(hh, window)) {
      if (e.amount.currency != h.baseCurrency) continue;
      totals[e.categoryId] =
          (totals[e.categoryId] ?? Money.zero(h.baseCurrency)) + e.amount;
    }
    final lines = [
      for (final c in categories)
        if (!_notSmall.contains(c.systemKey) && totals[c.meta.id] != null)
          RollupLine(
            subject: c,
            rollup: Rollup(totals[c.meta.id]!, windowDays),
          ),
    ]..sort((a, b) => b.rollup.total.compareTo(a.rollup.total));

    final active = [
      for (final o in await _obligations.listActive(hh))
        if (o.isActive && o.amount.currency == h.baseCurrency) o,
    ];
    Obligation? biggest(Iterable<Obligation> list) => list.isEmpty
        ? null
        : list.reduce((a, b) => b.amount > a.amount ? b : a);
    final reference =
        biggest(active.where((o) => o.kind == ObligationKind.rent)) ??
        biggest(active);
    return SpendingInsights(window: window, lines: lines, reference: reference);
  }

  // --- Odatlar (SPEC 2B.9): faqat statistika ---

  Future<List<RollupLine<Habit>>> habits() async {
    final h = await _households.current();
    final hh = h.meta.id;
    final totals = <String, Money>{};
    for (final e in await _expenses.listInRange(hh, _window())) {
      final id = e.habitId;
      if (id == null || e.amount.currency != h.baseCurrency) continue;
      totals[id] = (totals[id] ?? Money.zero(h.baseCurrency)) + e.amount;
    }
    return [
      for (final habit in await _habits.listActive(hh))
        if (!habit.isArchived)
          RollupLine(
            subject: habit,
            rollup: Rollup(
              totals[habit.meta.id] ?? Money.zero(h.baseCurrency),
              windowDays,
            ),
          ),
    ];
  }

  Future<Habit> addHabit(String title) async {
    if (title.trim().isEmpty) throw const DomainRuleException(errTitleRequired);
    final hh = (await _households.current()).meta.id;
    return _habits.add(Habit(meta: _meta.create(hh), title: title.trim()));
  }

  Future<void> archiveHabit(Habit h) async {
    await _habits.update(h.copyWith(isArchived: true));
  }

  // --- «Juma shirinligi» (SPEC 2B.4) ---

  Future<List<ScheduledTreat>> treats() async =>
      _treats.listActive((await _households.current()).meta.id);

  Future<ScheduledTreat> addTreat({
    required String title,
    required Money amount,
    int weekday = DateTime.friday,
  }) async {
    if (title.trim().isEmpty) throw const DomainRuleException(errTitleRequired);
    if (!amount.isPositive) throw const DomainRuleException(errNotPositive);
    if (weekday < DateTime.monday || weekday > DateTime.sunday) {
      throw const DomainRuleException(errBadWeekday);
    }
    final hh = (await _households.current()).meta.id;
    return _treats.add(
      ScheduledTreat(
        meta: _meta.create(hh),
        title: title.trim(),
        amount: amount,
        weekday: weekday,
      ),
    );
  }

  Future<ScheduledTreat> setTreatActive(ScheduledTreat t, {required bool on}) =>
      _treats.update(t.copyWith(isActive: on));

  Future<void> deleteTreat(String id) => _treats.softDelete(id);
}
