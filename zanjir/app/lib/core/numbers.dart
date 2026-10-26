/// Dala klaviaturasi uchun: vergul ham, nuqta ham qabul qilinadi ("0,84" = "0.84").
double? parseDecimal(String? text) {
  final t = text?.trim().replaceAll(',', '.') ?? '';
  if (t.isEmpty || !RegExp(r'^-?\d+(\.\d+)?$').hasMatch(t)) return null;
  return double.tryParse(t);
}

/// Sonni o'nlik vergul bilan ko'rsatadi, ortiqcha nollarsiz: 0.84 → "0,84", 16.0 → "16".
String formatDecimal(num value, {int maxFraction = 4}) {
  var s = value.toStringAsFixed(maxFraction);
  if (s.contains('.')) s = s.replaceFirst(RegExp(r'\.?0+$'), '');
  return s.replaceAll('.', ',');
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
