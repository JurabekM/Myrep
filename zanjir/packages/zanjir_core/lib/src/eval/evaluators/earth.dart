import '../../graph/traversal.dart';
import '../../model/enums.dart';
import '../../norms/norm.dart';
import '../context.dart';
import '../rule_check.dart';

const _maPerA = 1000;

/// Yerga ulash: `r_ohm × season_coeff` normadagi maksimum bilan solishtiriladi.
/// TT (`max_product`): Ia — yerga ulagich komponentidagi UZO'larning eng katta IΔn (konservativ).
List<Check> evaluateEarth(EvalContext ctx, List<Norm> norms) {
  final s = readNumber(ctx.values, 'season_coeff');
  final season = s.value;
  if (season == null) {
    final reason = s.reason == 'value_missing' ? 'season_coeff_missing' : s.reason!;
    return [
      needsReview(reason, extra: {'field': 'season_coeff'}),
    ];
  }
  if (season < 1) {
    return [
      needsReview('season_coeff_below_1', extra: {'season_coeff': season}),
    ];
  }

  final ia = norms.any((n) => n.rule is MaxProductRule) ? _rcdIa(ctx) : null;
  return [for (final n in norms) _checkNorm(ctx, n, season, ia)];
}

Check _checkNorm(EvalContext ctx, Norm norm, double season, ({double? amps, String? reason})? ia) {
  final r = readNumber(ctx.values, 'r_ohm', positive: true);
  final ohm = r.value;
  if (ohm == null) return needsReview(r.reason!, normId: norm.id, extra: {'field': 'r_ohm'});
  return checkRule(
    normId: norm.id,
    rule: norm.rule,
    value: ohm * season,
    marginPct: ctx.marginPct,
    factor: ia?.amps,
    factorMissingReason: ia?.reason,
  ).withExtra({'r_ohm': ohm, 'season_coeff': season});
}

({double? amps, String? reason}) _rcdIa(EvalContext ctx) {
  final rcds = [
    for (final id in component(ctx.graph, ctx.node.id))
      if (ctx.graph.node(id)!.kind case NodeKind.rcd || NodeKind.rcbo) ctx.graph.node(id)!,
  ];
  if (rcds.isEmpty) return (amps: null, reason: 'no_upstream_rcd');
  var maxMa = 0.0;
  for (final d in rcds) {
    final idn = positiveAttr(d.attrs, 'idn_ma');
    if (idn == null) return (amps: null, reason: 'rcd_idn_missing');
    if (idn > maxMa) maxMa = idn;
  }
  return (amps: maxMa / _maPerA, reason: null);
}
