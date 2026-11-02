/// Telefon raqamini kanonik ko'rinishga keltirish. Kotlin'dagi `call/PhoneRules.kt`
/// (PhoneNumbers) bilan aynan bir xil — ikkalasi `test/fixtures/phone_kat.json` bilan tekshiriladi.
library;

/// "+998712310880", "+79123456789" yoki qisqa/ichki raqam ("1102", "08001200200"). Raqam bo'lmasa null.
String? normalizePhone(String? raw) {
  if (raw == null) return null;
  var s = raw.trim();
  if (s.toLowerCase().startsWith('tel:')) s = s.substring(4);
  if (s.contains('%')) {
    try {
      s = Uri.decodeComponent(s);
    } catch (_) {}
  }
  final plus = s.trimLeft().startsWith('+');
  final d = s.replaceAll(RegExp(r'[^0-9]'), '');
  if (d.isEmpty) return null;
  if (plus) return '+$d';
  if (d.startsWith('00') && d.length >= 9) return '+${d.substring(2)}';
  if (d.length == 12 && d.startsWith('998')) return '+$d';
  if (d.length == 9 && d[0] != '0') return '+998$d';
  return d;
}

bool isShortPhone(String n) => !n.startsWith('+');
bool isUzPhone(String n) => n.startsWith('+998');

String displayPhone(String n) {
  if (isUzPhone(n) && n.length == 13) {
    final x = n.substring(4);
    return '+998 ${x.substring(0, 2)} ${x.substring(2, 5)} ${x.substring(5, 7)} ${x.substring(7)}';
  }
  return n;
}

/// Matndagi telefon raqamlari: kamida 9 raqam (qisqa raqamlar summa va kodlar bilan adashadi).
List<String> extractPhones(String text) {
  final out = <String>[];
  for (final m in RegExp(r'(?<![\w.,/])\+?\d[\d \-()]{7,17}\d(?![\w.,/])').allMatches(text)) {
    final raw = m.group(0)!;
    // "500 000 000 so'm" — summa, raqam emas.
    final after = text.substring(m.end, (m.end + 8).clamp(0, text.length)).toLowerCase();
    if (RegExp(r"^\s*(so'?m|sum|сум|сўм|uzs|rubl|руб)").hasMatch(after)) continue;
    final digits = raw.replaceAll(RegExp(r'[^0-9]'), '');
    if (digits.length < 9 || digits.length > 15) continue;
    final n = normalizePhone(raw);
    if (n != null && !out.contains(n)) out.add(n);
  }
  return out;
}
