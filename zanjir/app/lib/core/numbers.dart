export 'package:zanjir_protocol/zanjir_protocol.dart' show formatDecimal;

/// Dala klaviaturasi uchun: vergul ham, nuqta ham qabul qilinadi ("0,84" = "0.84").
double? parseDecimal(String? text) {
  final t = text?.trim().replaceAll(',', '.') ?? '';
  if (t.isEmpty || !RegExp(r'^-?\d+(\.\d+)?$').hasMatch(t)) return null;
  return double.tryParse(t);
}

/// `YYYY-MM-DD` → UTC sana.
DateTime? parseIsoDate(String? text) {
  final t = text?.trim() ?? '';
  final m = RegExp(r'^(\d{4})-(\d{2})-(\d{2})$').firstMatch(t);
  if (m == null) return null;
  final d = DateTime.utc(int.parse(m[1]!), int.parse(m[2]!), int.parse(m[3]!));
  return d.month == int.parse(m[2]!) && d.day == int.parse(m[3]!) ? d : null;
}

String formatIsoDate(DateTime d) {
  final u = d.toUtc();
  return '${u.year.toString().padLeft(4, '0')}-${u.month.toString().padLeft(2, '0')}-${u.day.toString().padLeft(2, '0')}';
}

/// Mahalliy vaqt: `2026-10-30 08:15` (qurilma soat mintaqasida).
String formatLocalDateTime(DateTime d) {
  final t = d.toLocal();
  String two(int v) => v.toString().padLeft(2, '0');
  return '${t.year.toString().padLeft(4, '0')}-${two(t.month)}-${two(t.day)} ${two(t.hour)}:${two(t.minute)}';
}
