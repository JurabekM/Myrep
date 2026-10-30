import 'package:yaml/yaml.dart';

import '../model/enums.dart';
import 'norm.dart';
import 'norm_set.dart';

/// Normalar fayli `norms/schema.json` ga mos emas.
class NormFormatException extends FormatException {
  NormFormatException(super.message);
}

const _schemaVersion = 1;
final _semver = RegExp(r'^[0-9]+\.[0-9]+\.[0-9]+$');
final _date = RegExp(r'^[0-9]{4}-[0-9]{2}-[0-9]{2}$');
final _normId = RegExp(r'^[A-Z0-9]+(-[A-Z0-9]+)*$');

NormSet parseNormSet(String yaml) {
  final Object? doc;
  try {
    doc = loadYaml(yaml);
  } on YamlException catch (e) {
    throw NormFormatException('YAML xatosi: ${e.message}');
  }
  final r = _Reader(_map(doc, '<root>'), '<root>');
  final schemaVersion = r.integer('schema_version');
  if (schemaVersion != _schemaVersion) r.fail('schema_version', 'kutilgan $_schemaVersion');
  final version = r.string('version');
  if (!_semver.hasMatch(version)) r.fail('version', 'semver emas');
  final reviewedBy = r.string('reviewed_by', allowEmpty: true);
  final reviewedAt = r.string('reviewed_at', allowEmpty: true);
  if (reviewedAt.isNotEmpty && !_date.hasMatch(reviewedAt)) r.fail('reviewed_at', 'YYYY-MM-DD emas');
  final margin = r.number('margin_pct');
  if (margin < 0 || margin > 50) r.fail('margin_pct', '0…50 oralig\'ida emas');

  final tm = r.child('trip_multipliers');
  final byCurve = <String, double>{};
  for (final curve in const ['B', 'C', 'D']) {
    final k = tm.number(curve);
    if (k <= 0) tm.fail(curve, 'musbat emas');
    byCurve[curve] = k;
  }
  final tripMultipliers = TripMultipliers(
    byCurve: Map.unmodifiable(byCurve),
    source: _source(tm.child('source')),
    status: _enum(tm, 'status', NormStatus.values, (v) => v.code),
  );
  tm.done();

  final normsRaw = r.list('norms');
  if (normsRaw.isEmpty) r.fail('norms', 'bo\'sh');
  final ids = <String>{};
  final norms = <Norm>[];
  for (var i = 0; i < normsRaw.length; i++) {
    final n = _norm(_Reader(_map(normsRaw[i], 'norms[$i]'), 'norms[$i]'));
    if (!ids.add(n.id)) throw NormFormatException('Takrorlangan norma ID: ${n.id}');
    norms.add(n);
  }
  r.done();
  return NormSet(
    schemaVersion: schemaVersion,
    version: version,
    reviewedBy: reviewedBy,
    reviewedAt: reviewedAt,
    marginPct: margin,
    tripMultipliers: tripMultipliers,
    norms: List.unmodifiable(norms),
  );
}

Norm _norm(_Reader r) {
  final id = r.string('id');
  if (!_normId.hasMatch(id)) r.fail('id', 'format noto\'g\'ri');
  final type = _enum(r, 'measurement_type', MeasurementType.values, (v) => v.code);
  final testVoltage = r.optNumber('test_voltage_v');
  if (testVoltage != null && testVoltage <= 0) r.fail('test_voltage_v', 'musbat emas');
  if (type == MeasurementType.insulation && testVoltage == null) {
    r.fail('test_voltage_v', 'izolyatsiya normasida majburiy');
  }
  final norm = Norm(
    id: id,
    title: r.string('title'),
    measurementType: type,
    appliesTo: _appliesTo(r.child('applies_to')),
    testVoltageV: testVoltage,
    rule: _rule(r.child('rule')),
    unit: _enum(r, 'unit', NormUnit.values, (v) => v.code),
    source: _source(r.child('source')),
    status: _enum(r, 'status', NormStatus.values, (v) => v.code),
  );
  r.done();
  return norm;
}

AppliesTo _appliesTo(_Reader r) {
  final kinds = _enumSet(r, 'node_kinds', NodeKind.values, (v) => v.code)!;
  final systems = _enumSet(r, 'earthing_systems', EarthingSystem.values, (v) => v.code);
  double? u0Min;
  double? u0Max;
  if (r.has('u0_volts')) {
    final u = r.child('u0_volts');
    u0Min = u.number('min');
    u0Max = u.number('max');
    if (u0Min > u0Max) u.fail('min', 'max dan katta');
    u.done();
  }
  final applies = AppliesTo(
    nodeKinds: kinds,
    earthingSystems: systems,
    u0Min: u0Min,
    u0Max: u0Max,
    attrs: _conditions(r, 'attrs'),
    values: _conditions(r, 'values'),
  );
  r.done();
  return applies;
}

Map<String, List<Object>> _conditions(_Reader r, String key) {
  if (!r.has(key)) return const {};
  final c = r.child(key);
  final out = <String, List<Object>>{};
  for (final k in c.keys) {
    final items = c.list(k);
    if (items.isEmpty) c.fail(k, 'bo\'sh');
    out[k] = List.unmodifiable([
      for (final v in items)
        if (v is String || v is num || v is bool) v! else c.fail(k, 'skalyar emas'),
    ]);
  }
  c.done();
  return Map.unmodifiable(out);
}

NormRule _rule(_Reader r) {
  final type = r.string('type');
  final NormRule rule;
  switch (type) {
    case 'min' || 'max' || 'max_time_ms':
      final v = r.number('value');
      if (v < 0) r.fail('value', 'manfiy');
      rule = switch (type) {
        'min' => MinRule(v),
        'max' => MaxRule(v),
        _ => MaxTimeRule(v),
      };
    case 'range':
      final min = r.number('min');
      final max = r.number('max');
      if (min < 0 || max < 0) r.fail('min', 'manfiy');
      if (min > max) r.fail('min', 'max dan katta');
      rule = RangeRule(
        min: min,
        max: max,
        minInclusive: r.optBool('min_inclusive') ?? true,
        maxInclusive: r.optBool('max_inclusive') ?? true,
        relativeTo: r.has('relative_to') ? _enum<RangeBase>(r, 'relative_to', RangeBase.values, (v) => v.code) : null,
      );
    case 'max_product':
      final v = r.number('value');
      if (v <= 0) r.fail('value', 'musbat emas');
      rule = MaxProductRule(v, _enum(r, 'factor', ProductFactor.values, (v) => v.code));
    default:
      r.fail('type', 'noma\'lum qoida turi: $type');
  }
  r.done();
  return rule;
}

NormSource _source(_Reader r) {
  final s = NormSource(doc: r.string('doc'), clause: r.string('clause'), note: r.optString('note'));
  r.done();
  return s;
}

T _enum<T>(_Reader r, String key, List<T> values, String Function(T) codeOf) {
  final code = r.string(key);
  for (final v in values) {
    if (codeOf(v) == code) return v;
  }
  r.fail(key, 'noma\'lum qiymat: $code');
}

Set<T>? _enumSet<T>(_Reader r, String key, List<T> values, String Function(T) codeOf) {
  if (!r.has(key)) {
    if (key == 'node_kinds') r.fail(key, 'majburiy');
    return null;
  }
  final items = r.list(key);
  if (items.isEmpty) r.fail(key, 'bo\'sh');
  final out = <T>{};
  for (final item in items) {
    final v = values.where((v) => codeOf(v) == item);
    if (v.isEmpty) r.fail(key, 'noma\'lum qiymat: $item');
    if (!out.add(v.first)) r.fail(key, 'takrorlangan: $item');
  }
  return Set.unmodifiable(out);
}

YamlMap _map(Object? v, String path) => v is YamlMap ? v : throw NormFormatException('$path: xarita (map) kutilgan');

/// Qat'iy o'quvchi: noma'lum kalitlar `done()` da rad etiladi.
class _Reader {
  _Reader(this._m, this._path);
  final YamlMap _m;
  final String _path;
  final _used = <String>{};

  Iterable<String> get keys => _m.keys.map((k) => '$k');

  bool has(String key) => _m.containsKey(key);

  Never fail(String key, String why) => throw NormFormatException('$_path.$key: $why');

  Object? _get(String key) {
    _used.add(key);
    if (!_m.containsKey(key)) fail(key, 'majburiy');
    return _m[key];
  }

  String string(String key, {bool allowEmpty = false}) {
    final v = _get(key);
    if (v is! String) fail(key, 'satr kutilgan');
    if (!allowEmpty && v.trim().isEmpty) fail(key, 'bo\'sh');
    return v;
  }

  String? optString(String key) => has(key) ? string(key) : null;

  double number(String key) {
    final v = _get(key);
    if (v is! num || !v.isFinite) fail(key, 'son kutilgan');
    return v.toDouble();
  }

  double? optNumber(String key) => has(key) ? number(key) : null;

  int integer(String key) {
    final v = _get(key);
    if (v is! int) fail(key, 'butun son kutilgan');
    return v;
  }

  bool? optBool(String key) {
    if (!has(key)) return null;
    final v = _get(key);
    if (v is! bool) fail(key, 'mantiqiy qiymat kutilgan');
    return v;
  }

  List<Object?> list(String key) {
    final v = _get(key);
    if (v is! YamlList) fail(key, 'ro\'yxat kutilgan');
    return v;
  }

  _Reader child(String key) => _Reader(_map(_get(key), '$_path.$key'), '$_path.$key');

  void done() {
    final unknown = keys.where((k) => !_used.contains(k)).toList();
    if (unknown.isNotEmpty) throw NormFormatException('$_path: noma\'lum maydon(lar): ${unknown.join(', ')}');
  }
}
