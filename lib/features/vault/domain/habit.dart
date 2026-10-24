import 'package:baraka_daftari/core/time/calendar.dart';
import 'package:meta/meta.dart';

/// «Kelajagim» odati ko'rsatkichlari (SPEC 2.2: miqdordan ko'ra odat).
@immutable
final class HabitStats {
  const HabitStats({
    required this.currentStreakWeeks,
    required this.totalWeeks,
    required this.thisWeekDone,
    required this.currentWeek,
  });

  /// Ketma-ket ajratilgan haftalar (joriy hafta hali tugamagan bo'lsa va
  /// unda ajratish yo'q bo'lsa, streak uzilmaydi — o'tgan haftadan sanaladi).
  final int currentStreakWeeks;

  /// Jami ajratilgan haftalar soni.
  final int totalWeeks;

  /// Joriy haftada ajratish bo'lganmi.
  final bool thisWeekDone;
  final DateRange currentWeek;

  @override
  bool operator ==(Object other) =>
      other is HabitStats &&
      other.currentStreakWeeks == currentStreakWeeks &&
      other.totalWeeks == totalWeeks &&
      other.thisWeekDone == thisWeekDone &&
      other.currentWeek == currentWeek;

  @override
  int get hashCode =>
      Object.hash(currentStreakWeeks, totalWeeks, thisWeekDone, currentWeek);

  @override
  String toString() =>
      'HabitStats(streak: $currentStreakWeeks, total: $totalWeeks, '
      'thisWeek: $thisWeekDone)';
}

/// Ajratish paytlaridan (UTC) odat statistikasi. Haftalar [calendar] bo'yicha
/// (standart — jumadan), sanalar Toshkent vaqtida.
HabitStats computeHabit({
  required Iterable<DateTime> savingInstants,
  required BudgetCalendar calendar,
  required LocalDate today,
}) {
  final weeks = _weekStarts(savingInstants, calendar, today);
  final current = calendar.weekOf(today);
  final thisWeekDone = weeks.contains(current.start);
  return HabitStats(
    currentStreakWeeks: _streakEndingAt(
      weeks,
      thisWeekDone ? current.start : current.start.plusDays(-7),
    ),
    totalWeeks: weeks.length,
    thisWeekDone: thisWeekDone,
    currentWeek: current,
  );
}

/// [since] dan keyingi haftalardagi ketma-ketlik (progressiv taklif uchun).
/// [since] tushgan hafta hisobga olinmaydi.
int streakWeeksSince({
  required Iterable<DateTime> savingInstants,
  required BudgetCalendar calendar,
  required LocalDate today,
  required DateTime? since,
}) {
  final weeks = _weekStarts(savingInstants, calendar, today);
  final current = calendar.weekOf(today);
  final end = weeks.contains(current.start)
      ? current.start
      : current.start.plusDays(-7);
  final floor = since == null
      ? null
      : calendar.weekOf(Tashkent.dateOf(since)).start;
  return _streakEndingAt(weeks, end, after: floor);
}

Set<LocalDate> _weekStarts(
  Iterable<DateTime> instants,
  BudgetCalendar calendar,
  LocalDate today,
) => {
  for (final t in instants)
    if (!Tashkent.dateOf(t).isAfter(today))
      calendar.weekOf(Tashkent.dateOf(t)).start,
};

int _streakEndingAt(Set<LocalDate> weeks, LocalDate end, {LocalDate? after}) {
  var count = 0;
  var w = end;
  while (weeks.contains(w) && (after == null || w.isAfter(after))) {
    count++;
    w = w.plusDays(-7);
  }
  return count;
}
