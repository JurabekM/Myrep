import '../../graph/traversal.dart';
import '../../model/enums.dart';
import '../../norms/norm.dart';
import '../context.dart';
import '../rule_check.dart';

const _protective = {NodeKind.breaker, NodeKind.rcbo, NodeKind.fuse};
const _residual = {NodeKind.rcd, NodeKind.rcbo};
final _pePair = RegExp(r'^L[123]-PEN?$');

/// "Faza-nol" sirtmog'i: Zs ≤ k_corr · U0 / Ia, Ia = k(egri chiziq) · In (ADR-0002 S2, S3).
/// Bir nechta kirish bo'lsa, eng qat'iy chegara olinadi.
List<Check> evaluateLoop(EvalContext ctx, List<Norm> norms) {
  final pair = ctx.values['pair'];
  if (pair == null) {
    return [
      needsReview('value_missing', extra: {'field': 'pair'}),
    ];
  }
  if (pair is! String) {
    return [
      needsReview('invalid_value', extra: {'field': 'pair'}),
    ];
  }
  if (!_pePair.hasMatch(pair)) {
    return [
      needsReview('loop_pair_not_pe', extra: {'pair': pair}),
    ];
  }
  final zsRead = readNumber(ctx.values, 'zs_ohm', positive: true);
  final zs = zsRead.value;
  if (zs == null) {
    return [
      needsReview(zsRead.reason!, extra: {'field': 'zs_ohm'}),
    ];
  }
  final u0 = ctx.site.u0Volts;
  if (u0 == null) {
    return [
      needsReview('value_missing', extra: {'field': 'site.u0_volts'}),
    ];
  }

  // Eng qisqa o'chish vaqti talab qilingan norma — hal qiluvchi.
  final strictest = norms.reduce((a, b) => _timeMs(b) < _timeMs(a) ? b : a).id;
  Check review(String reason, [Map<String, Object?> extra = const {}]) =>
      needsReview(reason, normId: strictest, extra: extra);

  final protection = findUpstreamProtection(ctx.graph, ctx.node.id, _protective);
  final ids = [for (final d in protection.devices) d.id];
  if (protection.unprotectedPathToSource) return [review('unprotected_path')];
  if (ids.isEmpty) return [review('no_protective_device')];
  if (protection.devices.any((d) => d.kind == NodeKind.fuse)) {
    return [
      review('fuse_protection', {'devices': ids}),
    ];
  }

  final factor = ctx.settings.kCorr * (1 - ctx.marginPct / 100);
  final devices = <Map<String, Object?>>[];
  for (final d in protection.devices) {
    final inA = positiveAttr(d.attrs, 'in_a');
    final curve = d.attrs['curve'];
    if (inA == null || curve is! String) {
      return [
        review('device_attrs_missing', {'device': d.id}),
      ];
    }
    final k = ctx.normSet.tripMultipliers.forCurve(curve);
    if (k == null) {
      return [
        review('curve_unknown', {'device': d.id, 'curve': curve}),
      ];
    }
    final ia = k * inA;
    devices.add({
      'id': d.id,
      'kind': d.kind.code,
      'in_a': d.attrs['in_a'],
      'curve': curve,
      'trip_multiplier': k,
      'ia_a': ia,
      'zs_max_ohm': factor * u0 / ia,
    });
  }
  final limits = [for (final d in devices) d['zs_max_ohm']! as double];
  final zsMax = limits.reduce((a, b) => a < b ? a : b);
  final zsMaxLoosest = limits.reduce((a, b) => a > b ? a : b);
  final base = checkRule(normId: strictest, rule: MaxRule(zsMax), value: zs, marginPct: 0);
  final check = Check(
    normId: strictest,
    verdict: base.verdict,
    reason: base.reason,
    formula: 'Zs ≤ k_corr · U0 / (k · In) · (1 − margin)',
    limit: zsMax,
    value: zs,
    slack: base.slack,
    extra: {'pair': pair, 'u0_volts': u0, 'devices': devices},
  );
  if (check.verdict == Verdict.pass) return [check];

  // Bir nechta kirish: biror chegaraga sig'adi, eng qat'iysiga emas — qaysi apparat himoya qilishi noma'lum.
  if (checkRule(normId: strictest, rule: MaxRule(zsMaxLoosest), value: zs, marginPct: 0).verdict == Verdict.pass) {
    return [_with(check, Verdict.needsReview, 'zs_ambiguous_multiple_feeds')];
  }
  final rcdOnAllPaths = !sourceReachableAvoiding(ctx.graph, ctx.node.id, _residual);
  return [
    rcdOnAllPaths
        ? _with(check, Verdict.needsReview, 'zs_exceeded_rcd_present')
        : _with(check, Verdict.fail, 'zs_exceeded'),
  ];
}

double _timeMs(Norm n) => switch (n.rule) {
  MaxTimeRule(valueMs: final ms) => ms,
  _ => double.infinity,
};

Check _with(Check c, Verdict verdict, String reason) => Check(
  normId: c.normId,
  verdict: verdict,
  reason: reason,
  formula: c.formula,
  limit: c.limit,
  value: c.value,
  slack: c.slack,
  extra: c.extra,
);
