/// Xavf darajalari va topilmalar (Q2: har hukm dalil va izoh bilan).
library;

enum Severity {
  ok('Xavfsiz'),
  info("Ma'lumot"),
  low('Past'),
  medium("O'rta"),
  high('Yuqori'),
  critical('Kritik');

  const Severity(this.label);
  final String label;

  bool operator >=(Severity other) => index >= other.index;
  bool operator >(Severity other) => index > other.index;
  bool operator <=(Severity other) => index <= other.index;
  bool operator <(Severity other) => index < other.index;
}

/// Topilma bilan bog'liq foydalanuvchi harakati (masalan sozlamani ochish).
class FindingAction {
  const FindingAction(this.label, this.kind, [this.arg]);
  final String label;
  final String kind; // openAppDetails | openUnknownSources | openAccessibility | ...
  final String? arg;
}

class Finding {
  const Finding({
    required this.code,
    required this.severity,
    required this.title,
    required this.explain,
    this.evidence,
    this.action,
  });

  /// Barqaror identifikator — testlar va "bu xato" belgisi shunga tayanadi.
  final String code;
  final Severity severity;
  final String title;

  /// Oddiy tilda: nima uchun bu xavfli va nima qilish kerak.
  final String explain;

  /// Texnik dalil (sertifikat izi, ruxsat nomi, mos kelgan so'z).
  final String? evidence;
  final FindingAction? action;
}

Severity worstOf(Iterable<Finding> findings) {
  var worst = Severity.ok;
  for (final f in findings) {
    if (f.severity > worst) worst = f.severity;
  }
  return worst;
}

/// Topilmalarni xavf darajasi bo'yicha kamayish tartibida (barqaror) saralaydi.
List<Finding> sortFindings(Iterable<Finding> findings) {
  final list = findings.toList();
  final indexed = [for (var i = 0; i < list.length; i++) (i, list[i])];
  indexed.sort((a, b) {
    final c = b.$2.severity.index.compareTo(a.$2.severity.index);
    return c != 0 ? c : a.$1.compareTo(b.$1);
  });
  return [for (final e in indexed) e.$2];
}
