import 'dart:math' as math;

import '../model/enums.dart';
import '../norms/norm.dart';

/// Suzuvchi nuqta xatosi uchun nisbiy tolerantlik (norma qiymati emas):
/// `2.5 * 1.6 = 4.000000000000001` chegaradagi qiymat sifatida PASS bo'ladi.
const double _relTolerance = 1e-9;

bool _close(double a, double b) => (a - b).abs() <= _relTolerance * math.max(1, math.max(a.abs(), b.abs()));
bool _le(double a, double b) => a < b || _close(a, b);
bool _ge(double a, double b) => a > b || _close(a, b);
bool _lt(double a, double b) => a < b && !_close(a, b);
bool _gt(double a, double b) => a > b && !_close(a, b);

/// Nisbiy zaxira: musbat — normada, manfiy — chegaradan tashqarida.
double _rel(double diff, double base) => base > 0 ? diff / base : diff;

/// Bitta tekshiruv natijasi (`eval_detail.checks[]`).
class Check {
  const Check({
    this.normId,
    required this.verdict,
    this.reason,
    this.formula,
    this.limit,
    this.value,
    this.slack,
    this.extra = const {},
  });

  final String? normId;
  final Verdict verdict;

  /// PASS bo'lmasa — sabab kodi (masalan, `out_of_limit`, `value_missing`).
  final String? reason;
  final String? formula;

  /// Hisoblangan chegara: son yoki `{min, max}`.
  final Object? limit;
  final double? value;
  final double? slack;
  final Map<String, Object?> extra;

  Check withExtra(Map<String, Object?> more) => Check(
    normId: normId,
    verdict: verdict,
    reason: reason,
    formula: formula,
    limit: limit,
    value: value,
    slack: slack,
    extra: {...extra, ...more},
  );

  Map<String, Object?> toDetail() => {
    'norm_id': normId,
    'verdict': verdict.code,
    'reason': ?reason,
    'formula': ?formula,
    'limit': ?limit,
    'value': ?value,
    'slack': ?slack,
    ...extra,
  };
}

Check needsReview(String reason, {String? normId, Map<String, Object?> extra = const {}}) =>
    Check(normId: normId, verdict: Verdict.needsReview, reason: reason, extra: extra);

/// Norma qoidasini qiymatga qo'llaydi. `margin_pct` chegarani qat'iylashtiradi.
/// `base` — nisbiy `range` uchun (IΔn, mA); `factor` — `max_product` uchun (Ia, A).
Check checkRule({
  required String normId,
  required NormRule rule,
  required double value,
  required double marginPct,
  double? base,
  double? factor,
  String? factorMissingReason,
}) {
  final tighten = 1 - marginPct / 100;
  final loosen = 1 + marginPct / 100;
  Check result(bool ok, String formula, Object limit, double measured, double slack) => Check(
    normId: normId,
    verdict: ok ? Verdict.pass : Verdict.fail,
    reason: ok ? null : 'out_of_limit',
    formula: formula,
    limit: limit,
    value: measured,
    slack: slack,
  );

  switch (rule) {
    case MinRule(value: final min):
      final limit = min * loosen;
      return result(_ge(value, limit), 'value ≥ min · (1 + margin)', limit, value, _rel(value - limit, limit));
    case MaxRule(value: final max):
      final limit = max * tighten;
      return result(_le(value, limit), 'value ≤ max · (1 − margin)', limit, value, _rel(limit - value, limit));
    case MaxTimeRule(valueMs: final max):
      final limit = max * tighten;
      return result(_le(value, limit), 't ≤ max_time · (1 − margin)', limit, value, _rel(limit - value, limit));
    case RangeRule():
      var scale = 1.0;
      var formula = 'min · (1 + margin) ≤ value ≤ max · (1 − margin)';
      if (rule.relativeTo != null) {
        if (base == null) {
          return needsReview('device_attrs_missing', normId: normId, extra: {'field': 'node.attrs.idn_ma'});
        }
        scale = base;
        formula = 'min · IΔn · (1 + margin) ≤ value ≤ max · IΔn · (1 − margin)';
      }
      final lo = rule.min * scale * loosen;
      final hi = rule.max * scale * tighten;
      final okLo = rule.minInclusive ? _ge(value, lo) : _gt(value, lo);
      final okHi = rule.maxInclusive ? _le(value, hi) : _lt(value, hi);
      if (!rule.minInclusive) formula = formula.replaceFirst('≤ value', '< value');
      if (!rule.maxInclusive) formula = formula.replaceFirst('value ≤', 'value <');
      final slack = math.min(_rel(value - lo, lo), _rel(hi - value, hi));
      return result(okLo && okHi, formula, {'min': lo, 'max': hi}, value, slack);
    case MaxProductRule(value: final max):
      if (factor == null) return needsReview(factorMissingReason ?? 'factor_unavailable', normId: normId);
      final limit = max * tighten;
      final product = value * factor;
      return result(
        _le(product, limit),
        'value · Ia ≤ max · (1 − margin)',
        limit,
        product,
        _rel(limit - product, limit),
      ).withExtra({'factor': factor, 'measured': value});
  }
}

int _severity(Verdict v) => switch (v) {
  Verdict.fail => 3,
  Verdict.needsReview => 2,
  Verdict.pass || Verdict.notApplicable => 0,
};

/// Hal qiluvchi tekshiruv: eng og'ir natija (FAIL > NEEDS_REVIEW > PASS),
/// teng bo'lsa — eng kichik zaxira (eng qat'iy norma); zaxirasiz tekshiruv birinchi.
Check decisive(List<Check> checks) {
  if (checks.isEmpty) throw StateError('Tekshiruvlar yo\'q');
  var best = checks.first;
  for (final c in checks.skip(1)) {
    final bySeverity = _severity(c.verdict) - _severity(best.verdict);
    if (bySeverity > 0 || (bySeverity == 0 && _tighter(c.slack, best.slack))) best = c;
  }
  return best;
}

bool _tighter(double? a, double? b) => b != null && (a == null || a < b);
