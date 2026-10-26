import '../graph/graph.dart';
import '../model/enums.dart';
import '../model/frozen.dart';
import '../model/measurement.dart';
import '../model/node.dart';
import '../model/session.dart';
import '../model/site.dart';
import '../norms/applicability.dart';
import '../norms/norm.dart';
import '../norms/norm_set.dart';
import 'context.dart';
import 'evaluators/bonding.dart';
import 'evaluators/earth.dart';
import 'evaluators/insulation.dart';
import 'evaluators/loop.dart';
import 'evaluators/rcd.dart';
import 'rule_check.dart';

/// Laboratoriya sozlamalari (LEAD o'zgartiradi).
class EvalSettings {
  const EvalSettings({this.kCorr = 1.0});

  /// Sirtmoq chegarasi koeffitsienti: Zs_max = k_corr · U0 / Ia. Oraliq (0; 1] —
  /// 1 dan katta qiymat chegarani yumshatadi, shuning uchun rad etiladi.
  final double kCorr;
}

class EvalResult {
  const EvalResult({required this.verdict, required this.normId, required this.normSetVersion, required this.detail});
  final Verdict verdict;

  /// Hal qiluvchi (eng qat'iy) norma; ma'lumot yetishmasa — null bo'lishi mumkin.
  final String? normId;
  final String normSetVersion;

  /// `measurement.eval_detail` (JSON'ga o'giriladigan qiymatlar).
  final Map<String, Object?> detail;
}

/// O'lchovni normaga solishtiradi. Sof, deterministik funksiya.
/// Ma'lumot yetishmasa natija NEEDS_REVIEW, hech qachon PASS emas.
EvalResult evaluate({
  required Measurement measurement,
  required Node node,
  required Site site,
  required MeasurementSession session,
  required NormSet normSet,
  required Graph graph,
  EvalSettings settings = const EvalSettings(),
}) {
  if (measurement.nodeId != node.id) throw ArgumentError('O\'lchov boshqa tugunga tegishli');
  if (node.siteId != site.id) throw ArgumentError('Tugun boshqa obyektda');
  if (session.siteId != site.id || measurement.sessionId != session.id) {
    throw ArgumentError('Sessiya o\'lchov yoki obyektga mos emas');
  }
  if (graph.node(node.id) == null) throw ArgumentError('Tugun grafda yo\'q');
  final k = settings.kCorr;
  if (!(k > 0 && k <= 1)) throw ArgumentError.value(k, 'kCorr', '(0; 1] oralig\'ida bo\'lishi kerak');

  final values = measurement.values;
  final detail = <String, Object?>{
    'norm_set_version': normSet.version,
    'margin_pct': normSet.marginPct,
    'k_corr': k,
    'measurement_type': measurement.type.code,
    'node_kind': node.kind.code,
    'site': {'earthing_system': site.earthingSystem?.code, 'u0_volts': site.u0Volts},
    'ambient_temp_c': session.ambientTempC,
    'inputs': values,
  };
  EvalResult done(Verdict verdict, String? reason, {String? normId}) => EvalResult(
    verdict: verdict,
    normId: normId,
    normSetVersion: normSet.version,
    detail: freezeMap({...detail, 'strictest_norm_id': normId, 'reason': reason}),
  );

  if (values.containsKey('not_applicable_reason')) {
    final why = values['not_applicable_reason'];
    return why is String && why.trim().isNotEmpty
        ? done(Verdict.notApplicable, 'marked_not_applicable')
        : done(Verdict.needsReview, 'invalid_value');
  }
  // ADR-0002 S4: 0,5·IΔn sinovida o'chmaslik to'g'ri natija — normasi yo'q.
  final multiplier = values['multiplier'];
  if (measurement.type == MeasurementType.rcdTrip && multiplier is num && multiplier < 1) {
    return done(Verdict.needsReview, 'rcd_multiplier_below_1');
  }

  final matched = <Norm>[];
  final unknown = <String, Object?>{};
  for (final n in normSet.norms.where((n) => n.measurementType == measurement.type)) {
    final a = checkApplicability(n, node, site, values);
    switch (a.status) {
      case Applicability.match:
        matched.add(n);
      case Applicability.unknown:
        unknown[n.id] = a.missing;
      case Applicability.noMatch:
        break;
    }
  }
  detail['matched_norms'] = [for (final n in matched) n.id];
  if (unknown.isNotEmpty) {
    detail['unknown_norms'] = unknown;
    return done(Verdict.needsReview, 'norm_applicability_unknown');
  }
  if (matched.isEmpty) return done(Verdict.needsReview, 'no_matching_norm');

  final ctx = EvalContext(
    node: node,
    site: site,
    session: session,
    normSet: normSet,
    graph: graph,
    settings: settings,
    values: values,
  );
  final checks = switch (measurement.type) {
    MeasurementType.insulation => evaluateInsulation(ctx, matched),
    MeasurementType.loopImpedance => evaluateLoop(ctx, matched),
    MeasurementType.rcdTrip => evaluateRcd(ctx, matched),
    MeasurementType.earthResistance => evaluateEarth(ctx, matched),
    MeasurementType.continuityBonding => evaluateBonding(ctx, matched),
  };
  detail['checks'] = [for (final c in checks) c.toDetail()];
  final d = decisive(checks);
  return done(d.verdict, d.reason, normId: d.normId);
}
