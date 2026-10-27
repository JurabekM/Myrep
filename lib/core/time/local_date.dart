import 'package:meta/meta.dart';

/// Vaqt zonasisiz kalendar sanasi (byudjet davrlari uchun, SPEC 4.4).
@immutable
final class LocalDate implements Comparable<LocalDate> {
  LocalDate(this.year, this.month, this.day) {
    final normalized = DateTime.utc(year, month, day);
    if (normalized.year != year ||
        normalized.month != month ||
        normalized.day != day) {
      throw ArgumentError("Mavjud bo'lmagan sana: $year-$month-$day");
    }
  }

  factory LocalDate.fromDateTime(DateTime d) =>
      LocalDate(d.year, d.month, d.day);

  /// `2026-10-09`.
  factory LocalDate.parse(String iso) {
    final m = RegExp(r'^(\d{4})-(\d{2})-(\d{2})$').firstMatch(iso);
    if (m == null) throw FormatException("Sana noto'g'ri", iso);
    return LocalDate(
      int.parse(m.group(1)!),
      int.parse(m.group(2)!),
      int.parse(m.group(3)!),
    );
  }

  final int year;
  final int month;
  final int day;

  DateTime get _utcMidnight => DateTime.utc(year, month, day);

  /// ISO hafta kuni: dushanba = 1 … yakshanba = 7 (`DateTime.monday`…).
  int get weekday => _utcMidnight.weekday;

  LocalDate plusDays(int days) =>
      LocalDate.fromDateTime(_utcMidnight.add(Duration(days: days)));

  /// Oy qo'shish; kun oy uzunligiga qisqartiriladi (31-yanvar + 1 → 28/29-fevral).
  LocalDate plusMonths(int months) {
    final total = year * 12 + (month - 1) + months;
    final y = total ~/ 12;
    final m = total % 12 + 1;
    return LocalDate(y, m, day.clamp(1, daysInMonth(y, m)));
  }

  int daysUntil(LocalDate other) =>
      other._utcMidnight.difference(_utcMidnight).inDays;

  static int daysInMonth(int year, int month) =>
      DateTime.utc(year, month + 1, 0).day;

  bool isBefore(LocalDate other) => compareTo(other) < 0;
  bool isAfter(LocalDate other) => compareTo(other) > 0;

  @override
  int compareTo(LocalDate other) => year != other.year
      ? year.compareTo(other.year)
      : month != other.month
      ? month.compareTo(other.month)
      : day.compareTo(other.day);

  @override
  bool operator ==(Object other) =>
      other is LocalDate &&
      other.year == year &&
      other.month == month &&
      other.day == day;

  @override
  int get hashCode => Object.hash(year, month, day);

  @override
  String toString() =>
      '${year.toString().padLeft(4, '0')}-'
      '${month.toString().padLeft(2, '0')}-'
      '${day.toString().padLeft(2, '0')}';
}
