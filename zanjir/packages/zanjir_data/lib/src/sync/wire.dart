import 'dart:convert';

import 'package:drift/drift.dart';
import 'package:zanjir_core/zanjir_core.dart';

import '../db/converters.dart';
import '../db/database.dart';

/// Sinxronlash jadvallari server tartibida (ota jadvallar birinchi) — `tools/vectors/sync_schema.json` bilan bir xil.
const syncTables = [
  'organization',
  'app_user',
  'device',
  'instrument',
  'site',
  'node',
  'edge',
  'measurement_session',
  'measurement',
  'protocol',
  'protocol_document',
  'audit_event',
  'isolation_plan',
  'norm_set',
  'org_setting',
];

/// Faqat API orqali boshqariladi — navbatga tushmaydi va push qilinmaydi.
const apiOnlyTables = {'app_user', 'device'};
const appendOnlyTables = {'measurement', 'protocol', 'protocol_document', 'audit_event'};

/// Serverda yo'q (faqat qurilmada) ustunlar va yangi qator uchun standart qiymatlari.
const localOnlyDefaults = {
  'app_user': {'phone': ''},
};

enum WireType { text, int, real, bool, datetime, jsonMap, jsonList, base64 }

/// Drift ustuni → sim formati turi.
WireType wireType(GeneratedColumn<Object> c) {
  if (c is GeneratedColumnWithTypeConverter) {
    final conv = (c as GeneratedColumnWithTypeConverter<Object?, Object>).converter;
    if (conv is JsonMapConverter) return WireType.jsonMap;
    if (conv is JsonListConverter) return WireType.jsonList;
  }
  return switch (c.type) {
    DriftSqlType.bool => WireType.bool,
    DriftSqlType.int || DriftSqlType.bigInt => WireType.int,
    DriftSqlType.double => WireType.real,
    DriftSqlType.dateTime => WireType.datetime,
    DriftSqlType.blob => WireType.base64,
    _ => WireType.text,
  };
}

/// Jadval ustunlari (nom → tur), lokal-faqat ustunlarsiz.
Map<String, WireType> wireColumns(ZanjirDatabase db, String table) {
  final t = db.allTables.firstWhere((t) => t.actualTableName == table);
  final local = localOnlyDefaults[table] ?? const {};
  return {
    for (final c in t.$columns)
      if (!local.containsKey(c.name)) c.name: wireType(c),
  };
}

/// SQLite qatori (xom) → sim formati.
Map<String, Object?> rowToWire(Map<String, WireType> columns, Map<String, Object?> raw) => {
  for (final MapEntry(key: name, value: type) in columns.entries) name: _toWire(type, raw[name]),
};

Object? _toWire(WireType type, Object? v) {
  if (v == null) return null;
  return switch (type) {
    WireType.bool => v == 1 || v == true,
    WireType.datetime => isoUtcMillis(_parseDate(v)),
    WireType.jsonMap || WireType.jsonList => jsonDecode(v as String),
    WireType.base64 => base64Encode(v as List<int>),
    WireType.real => (v as num).toDouble(),
    _ => v,
  };
}

DateTime _parseDate(Object v) => switch (v) {
  final String s => DateTime.parse(s).toUtc(),
  final int secs => DateTime.fromMillisecondsSinceEpoch(secs * 1000, isUtc: true),
  _ => throw FormatException('Sana formati', '$v'),
};

/// Sim formati → SQLite qiymati (Drift saqlash formati: sana — ISO matn, bool — 0/1, JSON — kanonik matn).
Variable<Object> wireToVariable(WireType type, Object? v) {
  if (v == null) return const Variable(null);
  return switch (type) {
    WireType.bool => Variable<int>(v == true ? 1 : 0),
    WireType.datetime => Variable<String>(DateTime.parse(v as String).toUtc().toIso8601String()),
    WireType.jsonMap || WireType.jsonList => Variable<String>(canonicalJson(v)),
    WireType.base64 => Variable<Uint8List>(base64Decode(v as String)),
    WireType.int => Variable<int>((v as num).toInt()),
    WireType.real => Variable<double>((v as num).toDouble()),
    WireType.text => Variable<String>(v as String),
  };
}

DateTime? wireDate(Object? v) => v is String ? DateTime.parse(v).toUtc() : null;
DateTime? localDate(Object? v) => v == null ? null : _parseDate(v);
