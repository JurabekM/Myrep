import 'dart:convert';

import 'package:drift/drift.dart';
import 'package:zanjir_core/zanjir_core.dart';

import '../db/database.dart';
import '../repo/context.dart';
import '../repo/staff_repository.dart';
import '../sync/wire.dart';
import 'exchange_file.dart';
import 'import_rules.dart';

/// Import natijasi: jadval → yangi / yangilangan qatorlar soni.
class ImportResult {
  const ImportResult(this.inserted, this.updated);
  final Map<String, int> inserted;
  final Map<String, int> updated;

  int get total => inserted.values.fold(0, (a, b) => a + b) + updated.values.fold(0, (a, b) => a + b);
}

/// Faylni bazaga birlashtiradi — **hammasi yoki hech narsa** (bitta tranzaksiya). Birlashtirilgan holat serverdagi push
/// tekshiruvlarining barchasidan o'tishi shart (ADR-0017 8-band), aks holda [DataRuleException] (`code` — sabab) va
/// baza o'zgarmaydi.
///
/// [approveDevices] — foydalanuvchi tasdiqlagan noma'lum qurilmalar (zaxiradan tiklangan telefon): [approver] import
/// tranzaksiyasi ichida `DEVICE_APPROVED` yozadi (faqat LEAD/ADMIN).
///
/// [trustAll] — taklif orqali qo'shilish (bo'sh baza): fayldagi qurilma va foydalanuvchilar ishonchli (taklif paroli
/// yuzma-yuz berilgan), qolgan barcha tekshiruvlar (zanjirlar, o'lchov/protokol/reja/normalar) bajariladi.
Future<ImportResult> importExchange(
  ZanjirDatabase db,
  ExchangeBody body, {
  required String orgId,
  required DateTime Function() clock,
  bool trustAll = false,
  Set<String> approveDevices = const {},
  Future<void> Function(String deviceId)? approver,
}) async {
  if (body.header.orgId != orgId) throw const DataRuleException('exchange_wrong_org');
  if (body.header.schemaVersion > db.schemaVersion) throw const DataRuleException('exchange_newer_version');
  final ctx = DataContext(db: db, orgId: orgId, clock: clock);
  return db.transaction(() async {
    await db.customStatement('PRAGMA defer_foreign_keys = ON');
    final merger = _Merger(ctx, trustAll: trustAll);
    await merger.merge(body.tables);
    await checkMerged(
      ctx,
      merger.changes,
      trustAll: trustAll,
      senderDeviceId: body.senderDeviceId,
      approveDevices: approveDevices,
      approver: approver,
    );
    await applyRevocations(ctx);
    final fk = await db.customSelect('PRAGMA foreign_key_check').get();
    if (fk.isNotEmpty) throw DataRuleException('constraint_violation', '${fk.first.data['table']}');
    return ImportResult(
      {for (final e in merger.changes.inserted.entries) e.key: e.value.length},
      {for (final e in merger.changes.updated.entries) e.key: e.value.length},
    );
  });
}

/// Import qilingan o'zgarishlar: jadval → ID lar; yangilanganlar uchun — eski qator (sim formati).
class MergeChanges {
  final inserted = <String, Set<String>>{};
  final updated = <String, Map<String, Map<String, Object?>>>{};

  /// Yangi audit hodisalari: qurilma → seq lar.
  final newEvents = <String, Set<int>>{};

  /// Importdan oldin bazada bo'lgan qurilmalar.
  final knownDevices = <String>{};

  bool isNew(String table, String id) => inserted[table]?.contains(id) ?? false;
  Iterable<String> touched(String table) => {...?inserted[table], ...?updated[table]?.keys};
}

/// Serverdagi push'dan farqi: fayl to'liq surat, takroriy qatorlar jim o'tkazib yuboriladi.
class _Merger {
  _Merger(this._ctx, {required this.trustAll});
  final DataContext _ctx;
  final bool trustAll;
  final changes = MergeChanges();
  ZanjirDatabase get _db => _ctx.db;

  static const _lww = {
    'organization',
    'app_user',
    'instrument',
    'site',
    'node',
    'edge',
    'measurement_session',
    'isolation_plan',
  };
  static const maxSkew = Duration(minutes: 10);

  Future<void> merge(Map<String, List<Map<String, Object?>>> tables) async {
    changes.knownDevices.addAll([
      for (final r
          in await _db.customSelect('SELECT id FROM device WHERE org_id = ?', variables: [Variable(_ctx.orgId)]).get())
        r.read<String>('id'),
    ]);
    for (final table in syncTables) {
      final rows = tables[table] ?? const [];
      final cols = wireColumns(_db, table);
      final seen = <String>{};
      for (final raw in rows) {
        final row = normalizeRow(_db, table, cols, raw);
        final id = row['id']! as String;
        if (!seen.add(id)) throw DataRuleException('exchange_invalid', 'duplicate:$table');
        final org = table == 'organization' ? id : row['org_id'];
        if (org != _ctx.orgId) throw DataRuleException('wrong_org', table);
        await switch (table) {
          'device' => _device(cols, row),
          'audit_event' => _event(cols, row),
          'measurement' || 'protocol' || 'protocol_document' => _append(table, cols, row),
          'norm_set' => _normSet(cols, row),
          'org_setting' => _orgSetting(cols, row),
          _ when _lww.contains(table) => _upsert(table, cols, row),
          _ => throw DataRuleException('table_not_importable', table),
        };
      }
    }
  }

  Future<Map<String, Object?>?> _local(
    String table,
    Map<String, WireType> cols,
    String where,
    List<Object> args,
  ) async {
    final r = await _db
        .customSelect('SELECT * FROM "$table" WHERE $where', variables: [for (final a in args) Variable(a)])
        .getSingleOrNull();
    return r == null ? null : rowToWire(cols, r.data);
  }

  Future<void> _insert(String table, Map<String, WireType> cols, Map<String, Object?> row) async {
    final names = cols.keys.toList();
    final extra = localOnlyDefaults[table] ?? const {};
    await _db.customInsert(
      'INSERT INTO "$table" (${[...names, ...extra.keys].map((c) => '"$c"').join(', ')}) '
      'VALUES (${List.filled(names.length + extra.length, '?').join(', ')})',
      variables: [for (final c in names) wireToVariable(cols[c]!, row[c]), for (final v in extra.values) Variable(v)],
    );
    (changes.inserted[table] ??= {}).add(row['id']! as String);
  }

  Future<void> _update(String table, Map<String, WireType> cols, Map<String, Object?> row, String localId) async {
    final names = cols.keys.where((c) => c != 'id').toList();
    await _db.customUpdate(
      'UPDATE "$table" SET ${names.map((c) => '"$c" = ?').join(', ')} WHERE id = ?',
      variables: [for (final c in names) wireToVariable(cols[c]!, row[c]), Variable(localId)],
    );
  }

  Future<void> _append(String table, Map<String, WireType> cols, Map<String, Object?> row) async {
    final old = await _local(table, cols, 'id = ?', [row['id']!]);
    if (old == null) return _insert(table, cols, row);
    if (canonicalJson(old) != canonicalJson(row))
      throw DataRuleException('append_only_conflict', '$table:${row['id']}');
  }

  Future<void> _event(Map<String, WireType> cols, Map<String, Object?> row) async {
    final device = row['device_id']! as String;
    final seq = row['seq']! as int;
    final old = await _local('audit_event', cols, 'org_id = ? AND device_id = ? AND seq = ?', [
      _ctx.orgId,
      device,
      seq,
    ]);
    if (old != null) {
      if (old['event_hash'] != row['event_hash']) throw DataRuleException('audit_conflict', '$device#$seq');
      return;
    }
    if (await _local('audit_event', cols, 'id = ?', [row['id']!]) != null) {
      throw DataRuleException('audit_conflict', '${row['id']}');
    }
    await _insert('audit_event', cols, row);
    (changes.newEvents[device] ??= {}).add(seq);
  }

  /// Qurilma qatori o'zgarmaydi (bekor qilish — faqat `DEVICE_REVOKED` hodisasidan, [applyRevocations]).
  Future<void> _device(Map<String, WireType> cols, Map<String, Object?> row) async {
    final old = await _local('device', cols, 'id = ?', [row['id']!]);
    if (old == null) return _insert('device', cols, {...row, 'revoked_at': null});
    for (final k in const ['user_id', 'public_key_ed25519', 'sig_alg']) {
      if (old[k] != row[k]) throw DataRuleException('device_conflict', '${row['id']}');
    }
  }

  /// Bir versiya — bir mazmun; turli telefonlarda ID farq qilishi mumkin.
  Future<void> _normSet(Map<String, WireType> cols, Map<String, Object?> row) async {
    final old = await _local('norm_set', cols, 'org_id = ? AND version = ?', [_ctx.orgId, row['version']!]);
    if (old == null) return _insert('norm_set', cols, row);
    if (old['sha256'] != row['sha256']) throw DataRuleException('norm_set_conflict', '${row['version']}');
  }

  /// Tashkilotda bitta qator (ID telefonlarda farq qilishi mumkin) — LWW, mahalliy ID saqlanadi.
  Future<void> _orgSetting(Map<String, WireType> cols, Map<String, Object?> row) async {
    final old = await _local('org_setting', cols, 'org_id = ?', [_ctx.orgId]);
    if (old == null) return _insert('org_setting', cols, row);
    if (!_wins(row, old)) return;
    _checkSkew('org_setting', row);
    final localId = old['id']! as String;
    await _update('org_setting', cols, {...row, 'id': localId}, localId);
    (changes.updated['org_setting'] ??= {})[localId] = old;
  }

  Future<void> _upsert(String table, Map<String, WireType> cols, Map<String, Object?> row) async {
    final id = row['id']! as String;
    final old = await _local(table, cols, 'id = ?', [id]);
    if (old == null) {
      if (table == 'organization' && !trustAll) throw const DataRuleException('wrong_org');
      _checkSkew(table, row);
      return _insert(table, cols, row);
    }
    if (canonicalJson(old) == canonicalJson(row)) return;
    // O'zgarmas maydonlar va holat o'tishlari LWW dan oldin (eskirgan qator ham rad etilishi mumkin).
    final decision = checkMutable(table, old, row);
    if (decision == MutableDecision.skip || (decision == MutableDecision.lww && !_wins(row, old))) return;
    _checkSkew(table, row);
    await _update(table, cols, row, id);
    (changes.updated[table] ??= {})[id] = old;
  }

  void _checkSkew(String table, Map<String, Object?> row) {
    final limit = _ctx.now().add(maxSkew);
    for (final k in const ['created_at', 'updated_at']) {
      final t = row[k];
      if (t is String && DateTime.parse(t).isAfter(limit)) throw DataRuleException('clock_skew', table);
    }
  }

  /// LWW: `(updated_at, rev)`, teng bo'lsa — mazmun (kanonik JSON) bo'yicha; barcha telefonlar bir xil natijaga keladi.
  static bool _wins(Map<String, Object?> a, Map<String, Object?> b) {
    final t = DateTime.parse(a['updated_at']! as String).compareTo(DateTime.parse(b['updated_at']! as String));
    if (t != 0) return t > 0;
    final r = (a['rev']! as int).compareTo(b['rev']! as int);
    if (r != 0) return r > 0;
    String content(Map<String, Object?> m) => canonicalJson({...m}..removeWhere((k, _) => k == 'id'));
    return content(a).compareTo(content(b)) > 0;
  }
}

/// Sim formatidagi qator: ustunlar to'plami aniq, turlar qat'iy (serverdagi `from_wire` kabi), qiymatlar `rowToWire`
/// bilan bir xil ko'rinishga keltiriladi (taqqoslash uchun).
Map<String, Object?> normalizeRow(
  ZanjirDatabase db,
  String table,
  Map<String, WireType> cols,
  Map<String, Object?> raw,
) {
  final t = db.allTables.firstWhere((t) => t.actualTableName == table);
  final nullable = {for (final c in t.$columns) c.name: c.$nullable};
  for (final k in raw.keys) {
    if (!cols.containsKey(k)) throw DataRuleException('exchange_invalid', 'unknown_column:$table.$k');
  }
  final out = <String, Object?>{};
  for (final MapEntry(key: c, value: type) in cols.entries) {
    if (!raw.containsKey(c)) throw DataRuleException('exchange_invalid', 'missing:$table.$c');
    final v = raw[c];
    if (v == null) {
      if (!(nullable[c] ?? false)) throw DataRuleException('exchange_invalid', 'null:$table.$c');
      out[c] = null;
      continue;
    }
    out[c] = _value(type, v) ?? (throw DataRuleException('exchange_invalid', 'type:$table.$c'));
  }
  return out;
}

final _isoDate = RegExp(r'^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(\.\d{1,6})?(Z|[+-]\d{2}:\d{2})$');

Object? _value(WireType type, Object v) {
  switch (type) {
    case WireType.text:
      return v is String ? v : null;
    case WireType.int:
      return v is int ? v : null;
    case WireType.real:
      return v is num && v.isFinite ? v.toDouble() : null;
    case WireType.bool:
      return v is bool ? v : null;
    case WireType.datetime:
      return v is String && _isoDate.hasMatch(v) ? isoUtcMillis(DateTime.parse(v)) : null;
    case WireType.jsonMap:
    case WireType.jsonList:
      if (type == WireType.jsonMap ? v is! Map : v is! List) return null;
      try {
        return jsonDecode(canonicalJson(v));
      } on Object {
        return null;
      }
    case WireType.base64:
      if (v is! String) return null;
      try {
        final s = base64Encode(base64Decode(v));
        return s == v ? s : null;
      } on FormatException {
        return null;
      }
  }
}
