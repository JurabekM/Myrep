import 'package:baraka_daftari/core/money/money.dart';

/// «Katta foyda» ogohlantirishi (SPEC 2F.7, MVP_PLAN 14A).
///
/// Davr foydasi rejadagidan 150 % yoki oxirgi 3 davr o'rtachasidan 200 %
/// (standart; `planBp`, `averageBp` bilan sozlanadi) oshsa, taqsimotdan oldin
/// ikkala tomon shartnomani qayta o'qishi kerak. Chegaralar bp'da — sozlanadi.
///
/// Qoida umumiy vektor bilan bir xil (`spec/test-vectors/profit_spike.json`):
/// `alert = actual > 0 && (A || B)`, bu yerda
/// - A: `plan > 0` va `actual * 10000 >= plan * planBp`;
/// - B: oxirgi 3 davr ma'lum, `S = sum(last3) > 0` va
///   `actual * 3 * 10000 >= S * averageBp`.
abstract final class ProfitSpike {
  static const defaultPlanBp = 15000;
  static const defaultAverageBp = 20000;

  /// Oxirgi davrlar soni («o'rtacha»).
  static const window = 3;

  /// `plan` — rejadagi foyda, yo'q bo'lsa `null` (sheriklikda reja hozircha
  /// yo'q, shuning uchun B sharti asosiy). `last3` — eng yangi 3 ta yopilgan
  /// davr foydasi, kamida 3 ta bo'lmasa `null`.
  static bool evaluate({
    required Money actual,
    Money? plan,
    List<Money>? last3,
    int planBp = defaultPlanBp,
    int averageBp = defaultAverageBp,
  }) {
    if (!actual.isPositive) return false;
    final byPlan =
        plan != null &&
        plan.isPositive &&
        actual.times(10000) >= plan.times(planBp);
    final history = last3;
    final byAverage = () {
      if (history == null || history.length != window) return false;
      final sum = Money.sum(history, actual.currency);
      return sum.isPositive &&
          actual.times(window * 10000) >= sum.times(averageBp);
    }();
    return byPlan || byAverage;
  }
}
