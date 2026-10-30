import '../../norms/norm.dart';
import '../context.dart';
import '../rule_check.dart';

/// Izolyatsiya: har bir juftlik ≥ min. Asbob kuchlanishi normadagidan past
/// yoki sessiya harorati kiritilmagan bo'lsa — NEEDS_REVIEW.
List<Check> evaluateInsulation(EvalContext ctx, List<Norm> norms) {
  if (ctx.session.ambientTempC == null) {
    return [
      needsReview('missing_ambient_temp', extra: {'field': 'session.ambient_temp_c'}),
    ];
  }
  final tv = readNumber(ctx.values, 'test_voltage_v', positive: true);
  final testVoltage = tv.value;
  if (testVoltage == null) {
    return [
      needsReview(tv.reason!, extra: {'field': 'test_voltage_v'}),
    ];
  }
  final pairs = ctx.values['pairs'];
  if (pairs is! List || pairs.isEmpty) {
    return [
      needsReview('no_pairs', extra: {'field': 'pairs'}),
    ];
  }

  return [for (final norm in norms) _checkNorm(ctx, norm, testVoltage, pairs)];
}

Check _checkNorm(EvalContext ctx, Norm norm, double testVoltage, List<Object?> pairs) {
  final required = norm.testVoltageV;
  final voltage = {'test_voltage_v': testVoltage, 'required_test_voltage_v': required};
  if (required != null && testVoltage < required) {
    return needsReview('test_voltage_below_norm', normId: norm.id, extra: voltage);
  }
  final pairChecks = <Check>[];
  for (var i = 0; i < pairs.length; i++) {
    final p = pairs[i];
    if (p is! Map<String, Object?>) {
      pairChecks.add(needsReview('value_missing', normId: norm.id, extra: {'field': 'pairs[$i]'}));
      continue;
    }
    final label = p['pair'];
    if (label is! String || label.trim().isEmpty) {
      pairChecks.add(needsReview('value_missing', normId: norm.id, extra: {'field': 'pairs[$i].pair'}));
      continue;
    }
    final r = readNumber(p, 'mohm');
    final mohm = r.value;
    pairChecks.add(
      mohm == null
          ? needsReview(r.reason!, normId: norm.id, extra: {'field': 'pairs[$i].mohm', 'pair': label})
          : checkRule(
              normId: norm.id,
              rule: norm.rule,
              value: mohm,
              marginPct: ctx.marginPct,
            ).withExtra({'pair': label}),
    );
  }
  return decisive(pairChecks).withExtra({
    ...voltage,
    'pairs': [for (final c in pairChecks) c.toDetail()],
  });
}
