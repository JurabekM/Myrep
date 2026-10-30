import 'package:zanjir_core/zanjir_core.dart';

/// Sonni o'nlik vergul bilan ko'rsatadi, ortiqcha nollarsiz: 0.84 → "0,84", 16.0 → "16".
String formatDecimal(num value, {int maxFraction = 4}) {
  var s = value.toStringAsFixed(maxFraction);
  if (s.contains('.')) s = s.replaceFirst(RegExp(r'\.?0+$'), '');
  return s.replaceAll('.', ',');
}

/// O'lchov qiymatlarining qisqa ko'rinishi (ilova ro'yxatlari va PDF jadvali uchun).
String summarizeValues(MeasurementType type, Map<String, Object?> v) {
  String n(String key, String unit) => v[key] is num ? '${formatDecimal(v[key]! as num)} $unit' : '—';
  if (v['not_applicable_reason'] is String) return '${v['not_applicable_reason']}';
  return switch (type) {
    MeasurementType.insulation => [
      for (final p in (v['pairs'] as List?) ?? const [])
        if (p is Map) '${p['pair']}: ${p['mohm'] is num ? formatDecimal(p['mohm']! as num) : '—'} MΩ',
    ].join(', '),
    MeasurementType.loopImpedance => '${v['pair'] ?? ''} Zs ${n('zs_ohm', 'Ω')}',
    MeasurementType.rcdTrip =>
      '${v['multiplier'] is num ? formatDecimal(v['multiplier']! as num) : '?'}·IΔn: '
          '${n('trip_time_ms', 'ms')}${v['trip_current_ma'] is num ? ' / ${n('trip_current_ma', 'mA')}' : ''}',
    MeasurementType.earthResistance =>
      'R ${n('r_ohm', 'Ω')} · ψ ${v['season_coeff'] is num ? formatDecimal(v['season_coeff']! as num) : '—'}',
    MeasurementType.continuityBonding => 'R ${n('r_ohm', 'Ω')}',
  };
}
