/// Yadrodagi `YYYY-MM-DD` ni `15.11.2026` ko'rinishida ko'rsatadi (faqat matn, hisob yo'q).
String showDate(String iso) {
  final p = iso.split('-');
  return p.length >= 3 ? '${p[2].substring(0, 2)}.${p[1]}.${p[0]}' : iso;
}

/// `YYYY-MM-01` → `06.2027`.
String showMonth(String iso) {
  final p = iso.split('-');
  return p.length >= 2 ? '${p[1]}.${p[0]}' : iso;
}

String _pad(int n) => n.toString().padLeft(2, '0');

/// Bugungi sana `YYYY-MM-DD` (sana maydonlari uchun boshlang'ich qiymat; hisob emas).
String todayIso() {
  final d = DateTime.now();
  return '${d.year}-${_pad(d.month)}-${_pad(d.day)}';
}

/// `DateTime` → `YYYY-MM-DD`.
String isoDate(DateTime d) => '${d.year}-${_pad(d.month)}-${_pad(d.day)}';
