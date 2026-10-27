import 'package:baraka_daftari/core/money/allocation.dart';
import 'package:baraka_daftari/core/money/money.dart';
import 'package:meta/meta.dart';

/// Uch stsenariy (SPEC 2E.4: «hisob-kitobni uch marta qildim»).
enum IdeaScenario { pessimistic, base, optimistic }

/// Stsenariy bo'yicha mini biznes-hisob.
@immutable
final class IdeaScenarioResult {
  const IdeaScenarioResult({
    required this.scenario,
    required this.income,
    required this.expense,
    required this.net,
    required this.myNet,
    this.paybackMonths,
  });

  final IdeaScenario scenario;
  final Money income;
  final Money expense;

  /// Oylik sof foyda (manfiy — zarar).
  final Money net;

  /// Sheriklikda ulushdan keyingi (mening) oylik foydam.
  final Money myNet;

  /// CAPEX necha oyda qoplanadi; foyda bo'lmasa — `null`.
  final int? paybackMonths;
}

/// Stsenariylar uchun standart kirim: pessimistik −30 %, optimistik +30 %.
(Money, Money) defaultScenarioIncomes(Money base) => (
  percentOf(base, 7000),
  percentOf(base, 13000),
);

/// Bitta stsenariy hisobi: sof foyda, ulushdan keyingi foyda va
/// payback = ⌈CAPEX / mening oylik foydam⌉.
IdeaScenarioResult evaluateScenario({
  required IdeaScenario scenario,
  required Money capex,
  required Money income,
  required Money expense,
  int myShareBp = basisPointsWhole,
}) {
  final net = income - expense;
  final myNet = net.isPositive ? percentOf(net, myShareBp) : net;
  int? payback;
  if (myNet.isPositive) {
    payback = capex.isPositive
        ? (capex.minorUnits + myNet.minorUnits - 1) ~/ myNet.minorUnits
        : 0;
  }
  return IdeaScenarioResult(
    scenario: scenario,
    income: income,
    expense: expense,
    net: net,
    myNet: myNet,
    paybackMonths: payback,
  );
}
