/// Domen tahlili uchun yordamchilar: Punycode (RFC 3492), gomoglif skeleti,
/// ro'yxatdan o'tadigan domen va tahrir masofasi. Hammasi offlayn.
library;

/// RFC 3492 Punycode dekoderi ("xn--" prefiksisiz qism uchun). Xato bo'lsa null.
String? punycodeDecode(String input) {
  const base = 36, tMin = 1, tMax = 26, skew = 38, damp = 700;
  var n = 128, i = 0, bias = 72;
  final output = <int>[];
  final b = input.lastIndexOf('-');
  if (b > 0) {
    for (final c in input.substring(0, b).codeUnits) {
      if (c >= 0x80) return null;
      output.add(c);
    }
  }
  int adapt(int delta, int numPoints, bool first) {
    delta = first ? delta ~/ damp : delta ~/ 2;
    delta += delta ~/ numPoints;
    var k = 0;
    while (delta > ((base - tMin) * tMax) ~/ 2) {
      delta ~/= base - tMin;
      k += base;
    }
    return k + ((base - tMin + 1) * delta) ~/ (delta + skew);
  }

  int digitOf(int c) {
    if (c >= 48 && c <= 57) return c - 22; // 0-9 -> 26..35
    if (c >= 65 && c <= 90) return c - 65; // A-Z
    if (c >= 97 && c <= 122) return c - 97; // a-z
    return base;
  }

  var idx = b > 0 ? b + 1 : 0;
  while (idx < input.length) {
    final oldi = i;
    var w = 1;
    for (var k = base;; k += base) {
      if (idx >= input.length) return null;
      final digit = digitOf(input.codeUnitAt(idx++));
      if (digit >= base) return null;
      i += digit * w;
      final t = k <= bias ? tMin : (k >= bias + tMax ? tMax : k - bias);
      if (digit < t) break;
      w *= base - t;
      if (w > 0x7fffffff) return null;
    }
    bias = adapt(i - oldi, output.length + 1, oldi == 0);
    n += i ~/ (output.length + 1);
    i %= output.length + 1;
    if (n > 0x10ffff) return null;
    output.insert(i, n);
    i++;
  }
  return String.fromCharCodes(output);
}

/// Har bir "xn--" yorlig'ini Unicode'ga aylantiradi.
String decodeIdnHost(String host) => host
    .split('.')
    .map((l) => l.startsWith('xn--') ? (punycodeDecode(l.substring(4)) ?? l) : l)
    .join('.');

const Map<String, String> _confusable = {
  // Kirill
  'а': 'a', 'е': 'e', 'о': 'o', 'р': 'p', 'с': 'c', 'у': 'y', 'х': 'x', 'і': 'l', 'ј': 'j',
  'ԁ': 'd', 'ѕ': 's', 'ӏ': 'l', 'һ': 'h', 'ԛ': 'q', 'ԝ': 'w', 'к': 'k', 'м': 'm', 'т': 't',
  'в': 'b', 'н': 'h', 'п': 'n', 'г': 'r', 'ү': 'y', 'ӧ': 'o',
  // Yunon
  'ο': 'o', 'α': 'a', 'ε': 'e', 'ρ': 'p', 'ν': 'v', 'τ': 't', 'κ': 'k', 'ι': 'l', 'υ': 'u',
  // Lotin ichidagi o'xshashlar
  '0': 'o', '1': 'l', 'i': 'l', '|': 'l', '!': 'l', 'ı': 'l', 'ɡ': 'g',
};

/// UTS #39 uslubidagi soddalashtirilgan skelet: ko'zga bir xil ko'rinadigan satrlar
/// bir xil skeletga ega bo'ladi ("c1ick", "сlick" -> "cllck").
String skeleton(String s) {
  final sb = StringBuffer();
  for (final r in s.toLowerCase().runes) {
    final ch = String.fromCharCode(r);
    sb.write(_confusable[ch] ?? ch);
  }
  return sb.toString().replaceAll('rn', 'm').replaceAll('vv', 'w');
}

bool hasNonAscii(String s) => s.codeUnits.any((c) => c > 0x7f);

/// Lotin va kirill/yunon harflari bitta yorliqda aralashganmi.
bool mixedScripts(String label) {
  var latin = false, other = false;
  for (final r in label.runes) {
    if ((r >= 0x61 && r <= 0x7a) || (r >= 0x41 && r <= 0x5a)) {
      latin = true;
    } else if ((r >= 0x0400 && r <= 0x04ff) || (r >= 0x0370 && r <= 0x03ff)) {
      other = true;
    }
  }
  return latin && other;
}

const Set<String> _twoLevelSuffixes = {
  'co.uz', 'com.uz', 'org.uz', 'net.uz', 'gov.uz', 'edu.uz',
  'com.ru', 'org.ru', 'co.uk', 'com.tr', 'com.kz', 'org.kz',
};

/// Taxminiy eTLD+1: "pay.click.uz" -> "click.uz", "my.gov.uz" -> "my.gov.uz".
String registrableDomain(String host) {
  final parts = host.split('.');
  if (parts.length <= 2) return host;
  final last2 = parts.sublist(parts.length - 2).join('.');
  if (_twoLevelSuffixes.contains(last2)) return parts.sublist(parts.length - 3).join('.');
  return last2;
}

String firstLabel(String domain) => domain.split('.').first;

int levenshtein(String a, String b) {
  if (a == b) return 0;
  if (a.isEmpty) return b.length;
  if (b.isEmpty) return a.length;
  var prev = List<int>.generate(b.length + 1, (i) => i);
  for (var i = 1; i <= a.length; i++) {
    final cur = List<int>.filled(b.length + 1, 0);
    cur[0] = i;
    for (var j = 1; j <= b.length; j++) {
      final cost = a.codeUnitAt(i - 1) == b.codeUnitAt(j - 1) ? 0 : 1;
      cur[j] = [prev[j] + 1, cur[j - 1] + 1, prev[j - 1] + cost].reduce((x, y) => x < y ? x : y);
    }
    prev = cur;
  }
  return prev[b.length];
}

bool isIpv4(String host) => RegExp(r'^\d{1,3}(\.\d{1,3}){3}$').hasMatch(host);
