import '../graph/graph.dart';
import '../model/node.dart';
import '../model/session.dart';
import '../model/site.dart';
import '../norms/norm_set.dart';
import 'evaluate.dart';

/// Baholovchilar uchun umumiy kirish.
class EvalContext {
  const EvalContext({
    required this.node,
    required this.site,
    required this.session,
    required this.normSet,
    required this.graph,
    required this.settings,
    required this.values,
  });
  final Node node;
  final Site site;
  final MeasurementSession session;
  final NormSet normSet;
  final Graph graph;
  final EvalSettings settings;
  final Map<String, Object?> values;

  double get marginPct => normSet.marginPct;
}

/// Son o'qish natijasi: `value` yoki `reason` (`value_missing` / `invalid_value`).
typedef NumberRead = ({double? value, String? reason});

/// Manfiy bo'lmagan chekli son. `positive` — nol ham rad etiladi (fizik jihatdan
/// mumkin bo'lmagan qiymat: Zs = 0 Ω, t = 0 ms — asbob xatosi, PASS bo'lmasligi kerak).
NumberRead readNumber(Map<String, Object?> m, String key, {bool positive = false}) {
  final v = m[key];
  if (v == null) return (value: null, reason: 'value_missing');
  if (v is! num || !v.isFinite || v < 0 || (positive && v == 0)) return (value: null, reason: 'invalid_value');
  return (value: v.toDouble(), reason: null);
}

/// Musbat son yoki null (apparat atributlari uchun).
double? positiveAttr(Map<String, Object?> attrs, String key) {
  final v = attrs[key];
  return v is num && v.isFinite && v > 0 ? v.toDouble() : null;
}
