import 'dart:convert';
import 'dart:typed_data';

/// Kanonik JSON (RFC 8785 / JCS): kalitlar UTF-16 kod birliklari bo'yicha saralangan, bo'sh joy yo'q,
/// sonlar ECMAScript formatida, vaqt — UTC ISO-8601 (millisekund), natija UTF-8.
/// Dart va Python bir xil `tools/vectors/*.json` vektorlaridan o'tadi (3-faza).
String canonicalJson(Object? value) {
  final out = StringBuffer();
  _write(out, value);
  return out.toString();
}

Uint8List canonicalJsonBytes(Object? value) => utf8.encode(canonicalJson(value));

/// JavaScript'da aniq ifodalanadigan eng katta butun son (2^53 − 1).
const _maxSafeInt = 9007199254740991;

void _write(StringBuffer out, Object? v) {
  switch (v) {
    case null:
      out.write('null');
    case final bool b:
      out.write(b ? 'true' : 'false');
    case final String s:
      _string(out, s);
    case final int i:
      if (i.abs() > _maxSafeInt) throw ArgumentError.value(i, 'value', 'butun son 2^53 dan katta');
      out.write(i);
    case final double d:
      out.write(_number(d));
    case final DateTime t:
      if (!t.isUtc) throw ArgumentError.value(t, 'value', 'vaqt UTC bo\'lishi kerak');
      _string(out, _iso(t));
    case final Map<Object?, Object?> m:
      final keys = [
        for (final k in m.keys)
          if (k is String) k else throw ArgumentError.value(k, 'key', 'kalit satr bo\'lishi kerak'),
      ]..sort();
      out.write('{');
      for (var i = 0; i < keys.length; i++) {
        if (i > 0) out.write(',');
        _string(out, keys[i]);
        out.write(':');
        _write(out, m[keys[i]]);
      }
      out.write('}');
    case final List<Object?> l:
      out.write('[');
      for (var i = 0; i < l.length; i++) {
        if (i > 0) out.write(',');
        _write(out, l[i]);
      }
      out.write(']');
    default:
      throw ArgumentError.value(v, 'value', 'JSON\'ga o\'girib bo\'lmaydi: ${v.runtimeType}');
  }
}

void _string(StringBuffer out, String s) {
  out.write('"');
  if (_plain(s)) {
    out.write(s);
    out.write('"');
    return;
  }
  for (var i = 0; i < s.length; i++) {
    final c = s.codeUnitAt(i);
    if (c >= 0xD800 && c <= 0xDBFF) {
      final next = i + 1 < s.length ? s.codeUnitAt(i + 1) : 0;
      if (next < 0xDC00 || next > 0xDFFF) throw ArgumentError.value(s, 'value', 'yolg\'iz surrogat');
      out.writeCharCode(c);
      out.writeCharCode(next);
      i++;
      continue;
    }
    if (c >= 0xDC00 && c <= 0xDFFF) throw ArgumentError.value(s, 'value', 'yolg\'iz surrogat');
    switch (c) {
      case 0x22:
        out.write(r'\"');
      case 0x5C:
        out.write(r'\\');
      case 0x08:
        out.write(r'\b');
      case 0x0C:
        out.write(r'\f');
      case 0x0A:
        out.write(r'\n');
      case 0x0D:
        out.write(r'\r');
      case 0x09:
        out.write(r'\t');
      default:
        if (c < 0x20) {
          out.write(r'\u');
          out.write(c.toRadixString(16).padLeft(4, '0'));
        } else {
          out.writeCharCode(c);
        }
    }
  }
  out.write('"');
}

/// Ekranlash ham, surrogat ham yo'q — satr o'zgarishsiz yoziladi (tez yo'l).
bool _plain(String s) {
  for (var i = 0; i < s.length; i++) {
    final c = s.codeUnitAt(i);
    if (c < 0x20 || c == 0x22 || c == 0x5C || (c >= 0xD800 && c <= 0xDFFF)) return false;
  }
  return true;
}

/// ECMAScript `Number.prototype.toString()` (RFC 8785, 3.2.2.3).
String _number(double x) {
  if (!x.isFinite) throw ArgumentError.value(x, 'value', 'NaN yoki cheksiz son');
  if (x == 0) return '0';
  final sign = x < 0 ? '-' : '';
  final a = x.abs();
  // Dart eng qisqa aniq raqamlar ketma-ketligini beradi: "d.ddde±N".
  final parts = a.toStringAsExponential().split('e');
  final digits = parts[0].replaceAll('.', '');
  final k = digits.length;
  final n = int.parse(parts[1]) + 1;
  final String body;
  if (k <= n && n <= 21) {
    body = digits + '0' * (n - k);
  } else if (0 < n && n <= 21) {
    body = '${digits.substring(0, n)}.${digits.substring(n)}';
  } else if (-6 < n && n <= 0) {
    body = '0.${'0' * -n}$digits';
  } else {
    final e = n - 1;
    final mantissa = k == 1 ? digits : '${digits[0]}.${digits.substring(1)}';
    body = '${mantissa}e${e < 0 ? '-' : '+'}${e.abs()}';
  }
  return sign + body;
}

String _iso(DateTime t) {
  String two(int v) => v.toString().padLeft(2, '0');
  final y = t.year;
  final year = y >= 0 && y <= 9999
      ? y.toString().padLeft(4, '0')
      : '${y < 0 ? '-' : '+'}${y.abs().toString().padLeft(6, '0')}';
  return '$year-${two(t.month)}-${two(t.day)}T${two(t.hour)}:${two(t.minute)}:${two(t.second)}.'
      '${t.millisecond.toString().padLeft(3, '0')}Z';
}
