/// O'zbekcha sana va son formatlash (intl paketisiz).
const _months = [
  'yanvar', 'fevral', 'mart', 'aprel', 'may', 'iyun', //
  'iyul', 'avgust', 'sentabr', 'oktabr', 'noyabr', 'dekabr',
];

String formatDate(DateTime d) {
  final l = d.toLocal();
  return '${l.day}-${_months[l.month - 1]}, ${l.year}';
}

String formatShortDate(DateTime d) {
  final l = d.toLocal();
  return '${l.day}-${_months[l.month - 1]}';
}

String formatDateTime(DateTime d) {
  final l = d.toLocal();
  String two(int v) => v.toString().padLeft(2, '0');
  return '${formatShortDate(l)}, ${two(l.hour)}:${two(l.minute)}';
}

String timeAgo(DateTime d, {DateTime? now}) {
  final diff = (now ?? DateTime.now()).difference(d);
  if (diff.inMinutes < 1) return 'hozirgina';
  if (diff.inMinutes < 60) return '${diff.inMinutes} daqiqa oldin';
  if (diff.inHours < 24) return '${diff.inHours} soat oldin';
  if (diff.inDays < 2) return 'kecha';
  if (diff.inDays < 31) return '${diff.inDays} kun oldin';
  if (diff.inDays < 365) return '${diff.inDays ~/ 30} oy oldin';
  return formatDate(d);
}

/// 6234 → "6 234"
String formatInt(int v) {
  final s = v.abs().toString();
  final b = StringBuffer();
  for (var i = 0; i < s.length; i++) {
    if (i > 0 && (s.length - i) % 3 == 0) b.write(' ');
    b.write(s[i]);
  }
  return v < 0 ? '-$b' : b.toString();
}

String formatPercent(double v) => '${v.toStringAsFixed(1)}%';
