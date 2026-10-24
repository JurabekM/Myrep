import 'package:baraka_daftari/core/domain/enums.dart';
import 'package:baraka_daftari/core/money/allocation.dart';
import 'package:baraka_daftari/core/money/money.dart';
import 'package:baraka_daftari/core/time/calendar.dart';
import 'package:baraka_daftari/features/ceremonies/domain/ceremony.dart';
import 'package:baraka_daftari/features/debts/domain/debt_math.dart';
import 'package:baraka_daftari/features/debts/domain/debts.dart';
import 'package:baraka_daftari/features/debts/domain/payoff.dart';
import 'package:meta/meta.dart';

/// Marosim qarzining to'lanishi — Vazifa 11 simulyatori bilan: [debt]
/// [start] dan keyin har oy [monthly] dan (stavka bo'lsa — qoldiqqa foiz),
/// oxirgi to'lov qoldiqni aynan yopadi. To'lov foizni ham qoplamasa —
/// `null` (qarz hech qachon tugamaydi).
PayoffSchedule? ceremonyDebtPayoff({
  required Money debt,
  required Money monthly,
  required LocalDate start,
  int annualRateBp = 0,
}) {
  if (!debt.isPositive || !monthly.isPositive) return null;
  final terms = PayoffTerms.annuity(
    annualRateBp: annualRateBp,
    annuityPayment: monthly,
  );
  // Qoldiq kamayib boradi — birinchi oy foizi eng katta. To'lov uni
  // qoplamasa, reja hech qachon tugamaydi.
  final firstInterest = MoneyRounding.mulDiv(
    debt.minorUnits,
    annualRateBp,
    12 * basisPointsWhole,
  );
  if (monthly.minorUnits <= firstInterest) return null;
  final rows = rowsFromBalance(
    balance: debt,
    firstDue: start.plusMonths(1),
    terms: terms,
  );
  return planPayoff(
    [PayoffDebt(id: 'ceremony', rows: rows, terms: terms)],
    monthlyExtra: Money.zero(debt.currency),
  ).debts.single.baseline;
}

/// Stsenariy xulosasi (SPEC 2D.8: taqqoslash umumiy narx, qarz, to'lash
/// muddati va muqobil maqsadlar bo'yicha).
@immutable
final class ScenarioSummary {
  const ScenarioSummary({
    required this.scenario,
    required this.lines,
    required this.total,
    required this.bySource,
    required this.goalShares,
    this.debtPayoff,
    this.debtMonthly,
  });

  final CeremonyScenario scenario;
  final List<CeremonyBudgetLine> lines;
  final Money total;
  final Map<FundingSource, Money> bySource;

  /// Shu stsenariy narxi har bir maqsadning necha bp i.
  final List<(Goal, int)> goalShares;

  /// Qarzning to'lanish grafigi; qarz yo'q yoki oylik to'lov kiritilmagan —
  /// `null`.
  final PayoffSchedule? debtPayoff;
  final Money? debtMonthly;

  Money get debt => bySource[FundingSource.debt] ?? Money.zero(total.currency);

  bool get hasDebt => debt.isPositive;

  /// Oylik to'lov foizni ham qoplamaydi — qarz tugamaydi.
  bool get debtNeverEnds =>
      hasDebt &&
      debtMonthly != null &&
      debtMonthly!.isPositive &&
      debtPayoff == null;

  /// Qarz bo'yicha ortiqcha to'lov (foiz).
  Money get debtOverpayment => debtPayoff == null
      ? Money.zero(total.currency)
      : debtPayoff!.totalPaid - debt;
}

ScenarioSummary summarizeScenario(
  CeremonyScenario scenario,
  List<CeremonyBudgetLine> lines, {
  required CurrencyCode currency,
  required LocalDate debtStart,
  Money? debtMonthly,
  int debtAnnualRateBp = 0,
  List<Goal> goals = const [],
}) {
  final bySource = <FundingSource, Money>{};
  for (final l in lines) {
    final t = l.totalFor(scenario.guests);
    bySource[l.source] = (bySource[l.source] ?? Money.zero(currency)) + t;
  }
  final total = Money.sum(bySource.values, currency);
  final debt = bySource[FundingSource.debt] ?? Money.zero(currency);
  return ScenarioSummary(
    scenario: scenario,
    lines: lines,
    total: total,
    bySource: bySource,
    goalShares: [
      for (final g in goals)
        if (g.target.currency == currency)
          (g, opportunityBp(total, g.target) ?? 0),
    ],
    debtMonthly: debtMonthly,
    debtPayoff: debtMonthly == null
        ? null
        : ceremonyDebtPayoff(
            debt: debt,
            monthly: debtMonthly,
            start: debtStart,
            annualRateBp: debtAnnualRateBp,
          ),
  );
}
