import 'dart:math' as math;

import 'package:baraka_daftari/core/time/calendar.dart';
import 'package:baraka_daftari/features/content/domain/content.dart';
import 'package:meta/meta.dart';

/// Bob ochilishi uchun kontekst.
@immutable
final class UnlockContext {
  const UnlockContext({
    required this.programStart,
    required this.today,
    required this.calendar,
    this.taskFirstCompleted = const {},
  });

  /// Dastur boshlangan sana (birinchi ishga tushirish).
  final LocalDate programStart;
  final LocalDate today;
  final BudgetCalendar calendar;

  /// Vazifa ID → u birinchi marta bajarilgan sana (Toshkent). Keyin
  /// belgisi olib tashlangan bo'lsa ham hisoblanadi — ochilgan bob qayta
  /// yopilmaydi.
  final Map<String, LocalDate> taskFirstCompleted;
}

/// Bitta bob uchun qoida natijasi.
@immutable
final class ChapterUnlock {
  const ChapterUnlock({this.date, this.tasksRemaining = 0, this.notBefore});

  /// Ochilish sanasi (kelajakda bo'lishi mumkin). `null` — hali aniq emas
  /// (oldingi bobning vazifalari yetarli bajarilmagan).
  final LocalDate? date;

  /// Oldingi bobdan yana nechta vazifa bajarilishi kerak.
  final int tasksRemaining;

  /// Kun sharti bo'yicha eng erta sana (odat qoidasida).
  final LocalDate? notBefore;

  bool isUnlockedOn(LocalDate today) {
    final d = date;
    return d != null && !today.isBefore(d);
  }
}

/// Bob qachon ochilishi qoidasi. Interfeys (funksiya emas) — qoidalar
/// sozlanadigan parametrlari bilan almashtiriladi.
// ignore: one_member_abstracts
abstract interface class ChapterUnlockPolicy {
  /// [chapters] — `order` bo'yicha tartiblangan; natija ham shu tartibda.
  List<ChapterUnlock> evaluate(List<Chapter> chapters, UnlockContext ctx);
}

/// Har juma yangi bob (SPEC 1.1): 1-bob darhol, k-bob dastur boshlangan
/// haftadan (k−1) hafta keyin, haftaning birinchi kuni (juma).
class TimeBasedUnlockPolicy implements ChapterUnlockPolicy {
  const TimeBasedUnlockPolicy();

  @override
  List<ChapterUnlock> evaluate(List<Chapter> chapters, UnlockContext ctx) {
    final firstWeek = ctx.calendar.weekOf(ctx.programStart).start;
    return [
      for (final c in chapters)
        ChapterUnlock(
          date: c.order <= 1
              ? ctx.programStart
              : firstWeek.plusDays(7 * (c.order - 1)),
        ),
    ];
  }
}

/// Odat asosidagi qoida (SPEC 2C.6, MVP_PLAN Vazifa 6): 1-bob darhol;
/// keyingisi oldingi bob ochilgandan kamida [minDays] kun o'tib, uning
/// vazifalaridan kamida [requiredTasks] tasi bajarilganda ochiladi.
/// Vaqtning o'zi bob ochmaydi — odat ochadi.
class HabitUnlockPolicy implements ChapterUnlockPolicy {
  const HabitUnlockPolicy({this.requiredTasks = 2, this.minDays = 7})
    : assert(requiredTasks >= 0 && minDays >= 0, 'manfiy shart');

  final int requiredTasks;
  final int minDays;

  @override
  List<ChapterUnlock> evaluate(List<Chapter> chapters, UnlockContext ctx) {
    final out = <ChapterUnlock>[];
    for (var i = 0; i < chapters.length; i++) {
      if (i == 0) {
        out.add(ChapterUnlock(date: ctx.programStart));
        continue;
      }
      final prev = chapters[i - 1];
      final prevDate = out[i - 1].date;
      final required = math.min(requiredTasks, prev.weeklyTasks.length);
      if (prevDate == null) {
        out.add(ChapterUnlock(tasksRemaining: required));
        continue;
      }
      final notBefore = prevDate.plusDays(minDays);
      final done = [
        for (final t in prev.weeklyTasks) ?ctx.taskFirstCompleted[t.id],
      ]..sort();
      if (done.length < required) {
        out.add(
          ChapterUnlock(
            tasksRemaining: required - done.length,
            notBefore: notBefore,
          ),
        );
        continue;
      }
      final tasksMet = required == 0 ? prevDate : done[required - 1];
      out.add(
        ChapterUnlock(
          date: tasksMet.isAfter(notBefore) ? tasksMet : notBefore,
          notBefore: notBefore,
        ),
      );
    }
    return out;
  }
}
