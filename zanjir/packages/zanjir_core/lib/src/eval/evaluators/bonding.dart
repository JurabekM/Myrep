import '../../norms/norm.dart';
import '../context.dart';
import '../rule_check.dart';

/// Metallik bog'lanish: `r_ohm ≤ max`.
List<Check> evaluateBonding(EvalContext ctx, List<Norm> norms) => [for (final n in norms) _checkNorm(ctx, n)];

Check _checkNorm(EvalContext ctx, Norm norm) {
  final r = readNumber(ctx.values, 'r_ohm');
  final ohm = r.value;
  if (ohm == null) return needsReview(r.reason!, normId: norm.id, extra: {'field': 'r_ohm'});
  return checkRule(normId: norm.id, rule: norm.rule, value: ohm, marginPct: ctx.marginPct);
}
