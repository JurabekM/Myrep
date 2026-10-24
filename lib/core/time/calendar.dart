import 'package:baraka_daftari/core/time/local_date.dart';
import 'package:meta/meta.dart';

export 'package:baraka_daftari/core/time/local_date.dart';

/// `Asia/Tashkent` — UTC+5, 1992 yildan beri yozgi vaqt yo'q.
///
/// Shu sabab tzdata paketi qo'shilmadi: doimiy siljish yetarli va
/// deterministik. Qoida o'zgarsa — shu yerning o'zida o'zgartiriladi.
abstract final class Tashkent {
  static const utcOffset = Duration(hours: 5);

  /// UTC instant → Toshkentdagi kalendar sanasi.
  static LocalDate dateOf(DateTime instant) =>
      LocalDate.fromDateTime(instant.toUtc().add(utcOffset));

  /// Toshkentdagi sana boshlanishi (00:00) UTC instant sifatida.
  static DateTime startOfDay(LocalDate date) =>
      DateTime.utc(date.year, date.month, date.day).subtract(utcOffset);
}

/// Yarim ochiq sana oralig'i: `[start, endExclusive)`.
@immutable
final class DateRange {
  DateRange(this.start, this.endExclusive) {
    if (!start.isBefore(endExclusive)) {
      throw ArgumentError("Oraliq bo'sh: $start … $endExclusive");
    }
  }

  final LocalDate start;
  final LocalDate endExclusive;

  bool contains(LocalDate d) => !d.isBefore(start) && d.isBefore(endExclusive);

  int get lengthInDays => start.daysUntil(endExclusive);

  /// UTC instantlar oralig'i (bazadan so'rov uchun).
  DateTime get startInstant => Tashkent.startOfDay(start);
  DateTime get endInstantExclusive => Tashkent.startOfDay(endExclusive);

  @override
  bool operator ==(Object other) =>
      other is DateRange &&
      other.start == start &&
      other.endExclusive == endExclusive;

  @override
  int get hashCode => Object.hash(start, endExclusive);

  @override
  String toString() => '[$start, $endExclusive)';
}

/// Hafta va oy chegaralari (SPEC 4.4): hafta jumadan, oy — oylik kunidan.
@immutable
final class BudgetCalendar {
  const BudgetCalendar({
    this.weekAnchor = DateTime.friday,
    this.monthStartDay = 1,
  }) : assert(weekAnchor >= 1 && weekAnchor <= 7, 'weekAnchor 1..7'),
       assert(monthStartDay >= 1 && monthStartDay <= 31, 'monthStartDay 1..31');

  /// Hafta boshlanadigan kun (`DateTime.friday` = 5).
  final int weekAnchor;

  /// Oylik davr boshlanadigan kun (masalan, oylik 10-sanada kelsa — 10).
  /// Oyda bunday kun bo'lmasa (31 → fevral), oyning oxirgi kuni olinadi.
  final int monthStartDay;

  DateRange weekOf(LocalDate date) {
    final back = (date.weekday - weekAnchor + 7) % 7;
    final start = date.plusDays(-back);
    return DateRange(start, start.plusDays(7));
  }

  DateRange monthOf(LocalDate date) {
    final thisMonthStart = _startIn(date.year, date.month);
    final start = date.isBefore(thisMonthStart)
        ? _startIn(_prevYear(date), _prevMonth(date))
        : thisMonthStart;
    final next = LocalDate(start.year, start.month, 1).plusMonths(1);
    return DateRange(start, _startIn(next.year, next.month));
  }

  /// [date] dan oldingi to'liq oy (oylik audit uchun).
  DateRange previousMonthOf(LocalDate date) =>
      monthOf(monthOf(date).start.plusDays(-1));

  LocalDate _startIn(int year, int month) => LocalDate(
    year,
    month,
    monthStartDay.clamp(1, LocalDate.daysInMonth(year, month)),
  );

  static int _prevYear(LocalDate d) => d.month == 1 ? d.year - 1 : d.year;
  static int _prevMonth(LocalDate d) => d.month == 1 ? 12 : d.month - 1;
}
