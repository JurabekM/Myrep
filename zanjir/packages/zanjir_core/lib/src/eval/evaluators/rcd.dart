import '../../model/enums.dart';
import '../../norms/norm.dart';
import '../context.dart';
import '../rule_check.dart';

/// UZO: `multiplier` bo'yicha tanlangan normalar (selektiv — S-normalar).
/// `tripped = false` → FAIL. IΔn da o'chish vaqti va o'chish toki (RCD-RAMP) birga tekshiriladi.
List<Check> evaluateRcd(EvalContext ctx, List<Norm> norms) {
  final tripped = ctx.values['tripped'];
  if (tripped == null) {
    return [
      needsReview('value_missing', extra: {'field': 'tripped'}),
    ];
  }
  if (tripped is! bool) {
    return [
      needsReview('invalid_value', extra: {'field': 'tripped'}),
    ];
  }
  if (!tripped) {
    return [
      const Check(verdict: Verdict.fail, reason: 'rcd_not_tripped', extra: {'field': 'tripped'}),
    ];
  }
  return [for (final n in norms) _checkNorm(ctx, n)];
}

Check _checkNorm(EvalContext ctx, Norm norm) {
  final rule = norm.rule;
  final isCurrent = rule is RangeRule && rule.relativeTo == RangeBase.idnMa;
  final field = isCurrent ? 'trip_current_ma' : 'trip_time_ms';
  final r = readNumber(ctx.values, field, positive: true);
  final value = r.value;
  if (value == null) return needsReview(r.reason!, normId: norm.id, extra: {'field': field});
  return checkRule(
    normId: norm.id,
    rule: rule,
    value: value,
    marginPct: ctx.marginPct,
    base: isCurrent ? positiveAttr(ctx.node.attrs, 'idn_ma') : null,
  ).withExtra({'field': field});
}
