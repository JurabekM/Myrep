import '../model/enums.dart';

enum NormStatus {
  sourceSeen('source_seen'),
  needsVerification('needs_verification');

  const NormStatus(this.code);
  final String code;
}

enum NormUnit {
  mohm('MOhm'),
  ohm('Ohm'),
  ms('ms'),
  ma('mA'),
  v('V');

  const NormUnit(this.code);
  final String code;
}

/// `range` chegaralari qaysi kattalikka ko'paytiriladi.
enum RangeBase {
  /// UZO nominal differensial toki, mA (`node.attrs.idn_ma`).
  idnMa('idn_ma');

  const RangeBase(this.code);
  final String code;
}

/// `max_product` dagi ko'paytuvchi (ADR-0002, S7).
enum ProductFactor {
  /// Yerga ulagich komponentidagi UZO'larning eng katta IΔn qiymati, A.
  upstreamRcdIdnA('upstream_rcd_idn_a');

  const ProductFactor(this.code);
  final String code;
}

sealed class NormRule {
  const NormRule();
  String get type;
}

final class MinRule extends NormRule {
  const MinRule(this.value);
  final double value;
  @override
  String get type => 'min';
}

final class MaxRule extends NormRule {
  const MaxRule(this.value);
  final double value;
  @override
  String get type => 'max';
}

final class MaxTimeRule extends NormRule {
  const MaxTimeRule(this.valueMs);
  final double valueMs;
  @override
  String get type => 'max_time_ms';
}

final class RangeRule extends NormRule {
  const RangeRule({
    required this.min,
    required this.max,
    this.minInclusive = true,
    this.maxInclusive = true,
    this.relativeTo,
  });
  final double min;
  final double max;
  final bool minInclusive;
  final bool maxInclusive;
  final RangeBase? relativeTo;
  @override
  String get type => 'range';
}

final class MaxProductRule extends NormRule {
  const MaxProductRule(this.value, this.factor);
  final double value;
  final ProductFactor factor;
  @override
  String get type => 'max_product';
}

class NormSource {
  const NormSource({required this.doc, required this.clause, this.note});
  final String doc;
  final String clause;
  final String? note;
}

/// Qo'llanish sharti. `null` / bo'sh — cheklov yo'q.
class AppliesTo {
  const AppliesTo({
    required this.nodeKinds,
    this.earthingSystems,
    this.u0Min,
    this.u0Max,
    this.attrs = const {},
    this.values = const {},
  });
  final Set<NodeKind> nodeKinds;
  final Set<EarthingSystem>? earthingSystems;
  final double? u0Min;
  final double? u0Max;

  /// Tugun atributi → ruxsat etilgan qiymatlar.
  final Map<String, List<Object>> attrs;

  /// O'lchov qiymati → ruxsat etilgan qiymatlar.
  final Map<String, List<Object>> values;
}

class Norm {
  const Norm({
    required this.id,
    required this.title,
    required this.measurementType,
    required this.appliesTo,
    required this.rule,
    required this.unit,
    required this.source,
    required this.status,
    this.testVoltageV,
  });
  final String id;
  final String title;
  final MeasurementType measurementType;
  final AppliesTo appliesTo;
  final double? testVoltageV;
  final NormRule rule;
  final NormUnit unit;
  final NormSource source;
  final NormStatus status;
}
