import 'dart:convert';

import 'package:drift/drift.dart';
import 'package:zanjir_core/zanjir_core.dart';

/// Enum ↔ baza kodi (`code`). Noma'lum kod — FormatException (jim yo'qotish yo'q).
class CodeConverter<T extends Enum> extends TypeConverter<T, String> {
  const CodeConverter(this._values, this._codeOf);
  final List<T> _values;
  final String Function(T) _codeOf;

  @override
  T fromSql(String fromDb) =>
      _values.firstWhere((v) => _codeOf(v) == fromDb, orElse: () => throw FormatException('Noma\'lum kod', fromDb));

  @override
  String toSql(T value) => _codeOf(value);
}

String _nodeKindCode(NodeKind v) => v.code;
String _earthingCode(EarthingSystem v) => v.code;
String _measurementTypeCode(MeasurementType v) => v.code;
String _verdictCode(Verdict v) => v.code;
String _sessionKindCode(SessionKind v) => v.code;
String _enteredViaCode(EnteredVia v) => v.code;
String _switchStateCode(SwitchState v) => v.code;

const nodeKindConverter = CodeConverter(NodeKind.values, _nodeKindCode);
const earthingConverter = CodeConverter(EarthingSystem.values, _earthingCode);
const measurementTypeConverter = CodeConverter(MeasurementType.values, _measurementTypeCode);
const verdictConverter = CodeConverter(Verdict.values, _verdictCode);
const sessionKindConverter = CodeConverter(SessionKind.values, _sessionKindCode);
const enteredViaConverter = CodeConverter(EnteredVia.values, _enteredViaCode);
const switchStateConverter = CodeConverter(SwitchState.values, _switchStateCode);

/// JSON ustunlari kanonik JSON (RFC 8785) bilan yoziladi — bir xil qiymat har doim bir xil matn.
class JsonMapConverter extends TypeConverter<Map<String, Object?>, String> {
  const JsonMapConverter();

  @override
  Map<String, Object?> fromSql(String fromDb) => jsonDecode(fromDb) as Map<String, Object?>;

  @override
  String toSql(Map<String, Object?> value) => canonicalJson(value);
}

class JsonListConverter extends TypeConverter<List<Object?>, String> {
  const JsonListConverter();

  @override
  List<Object?> fromSql(String fromDb) => jsonDecode(fromDb) as List<Object?>;

  @override
  String toSql(List<Object?> value) => canonicalJson(value);
}
