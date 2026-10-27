import 'dart:math';

import 'package:baraka_daftari/core/ids/uuid_v7.dart';
import 'package:baraka_daftari/core/time/calendar.dart';
import 'package:flutter_test/flutter_test.dart';

import '../helpers/fakes.dart';

LocalDate d(int y, int m, int day) => LocalDate(y, m, day);

void main() {
  group('LocalDate', () {
    test('yaratish, parse, toString', () {
      expect(LocalDate.parse('2026-10-09'), d(2026, 10, 9));
      expect(d(2026, 1, 5).toString(), '2026-01-05');
      expect(() => d(2026, 2, 30), throwsArgumentError);
      expect(() => LocalDate.parse('9.10.2026'), throwsFormatException);
    });

    test('kun/oy qoʻshish va farq', () {
      expect(d(2026, 12, 31).plusDays(1), d(2027, 1, 1));
      expect(d(2026, 1, 31).plusMonths(1), d(2026, 2, 28));
      expect(d(2028, 1, 31).plusMonths(1), d(2028, 2, 29));
      expect(d(2026, 3, 15).plusMonths(-3), d(2025, 12, 15));
      expect(d(2026, 1, 1).daysUntil(d(2026, 3, 1)), 59);
      expect(d(2026, 10, 9).weekday, DateTime.friday);
    });

    test('taqqoslash va tenglik', () {
      expect(d(2026, 1, 1).isBefore(d(2026, 1, 2)), isTrue);
      expect(d(2026, 2, 1).isAfter(d(2026, 1, 31)), isTrue);
      expect(d(2025, 12, 31).compareTo(d(2026, 1, 1)), isNegative);
      expect(d(2026, 1, 1).hashCode, d(2026, 1, 1).hashCode);
    });
  });

  group('Toshkent vaqti (UTC+5)', () {
    test('UTC 19:00 — Toshkentda ertasi kun', () {
      expect(
        Tashkent.dateOf(DateTime.utc(2026, 10, 8, 18, 59)),
        d(2026, 10, 8),
      );
      expect(Tashkent.dateOf(DateTime.utc(2026, 10, 8, 19)), d(2026, 10, 9));
    });

    test('kun boshi UTC instant sifatida', () {
      expect(
        Tashkent.startOfDay(d(2026, 10, 9)),
        DateTime.utc(2026, 10, 8, 19),
      );
    });
  });

  group('BudgetCalendar — hafta jumadan', () {
    const cal = BudgetCalendar();

    test('juma — haftaning birinchi kuni', () {
      final friday = d(2026, 10, 9);
      expect(cal.weekOf(friday), DateRange(friday, d(2026, 10, 16)));
    });

    test('payshanba — oʻtgan jumaning haftasi', () {
      expect(cal.weekOf(d(2026, 10, 15)).start, d(2026, 10, 9));
      expect(cal.weekOf(d(2026, 10, 8)).start, d(2026, 10, 2));
    });

    test('har kun uchun: 7 kunlik, ichida, boshi juma', () {
      var day = d(2026, 1, 1);
      for (var i = 0; i < 400; i++) {
        final week = cal.weekOf(day);
        expect(week.lengthInDays, 7);
        expect(week.contains(day), isTrue);
        expect(week.start.weekday, DateTime.friday);
        day = day.plusDays(1);
      }
    });

    test('hafta boshi sozlanadi', () {
      const monday = BudgetCalendar(weekAnchor: DateTime.monday);
      expect(monday.weekOf(d(2026, 10, 9)).start, d(2026, 10, 5));
    });
  });

  group('BudgetCalendar — oylik kuni', () {
    test('standart: kalendar oyi', () {
      const cal = BudgetCalendar();
      expect(
        cal.monthOf(d(2026, 10, 9)),
        DateRange(d(2026, 10, 1), d(2026, 11, 1)),
      );
      expect(
        cal.monthOf(d(2026, 12, 31)),
        DateRange(d(2026, 12, 1), d(2027, 1, 1)),
      );
    });

    test('oylik 10-sanada: 9-oktabr sentabr davriga kiradi', () {
      const cal = BudgetCalendar(monthStartDay: 10);
      expect(
        cal.monthOf(d(2026, 10, 9)),
        DateRange(d(2026, 9, 10), d(2026, 10, 10)),
      );
      expect(cal.monthOf(d(2026, 10, 10)).start, d(2026, 10, 10));
      expect(
        cal.monthOf(d(2026, 1, 5)),
        DateRange(d(2025, 12, 10), d(2026, 1, 10)),
      );
    });

    test('31-sana qisqa oyda oyning oxirgi kuniga tushadi', () {
      const cal = BudgetCalendar(monthStartDay: 31);
      expect(
        cal.monthOf(d(2026, 2, 28)),
        DateRange(d(2026, 2, 28), d(2026, 3, 31)),
      );
      expect(
        cal.monthOf(d(2026, 2, 27)),
        DateRange(d(2026, 1, 31), d(2026, 2, 28)),
      );
    });

    test('oldingi oy (audit uchun)', () {
      const cal = BudgetCalendar(monthStartDay: 10);
      expect(
        cal.previousMonthOf(d(2026, 10, 15)),
        DateRange(d(2026, 9, 10), d(2026, 10, 10)),
      );
    });

    test('davrlar boʻshliqsiz va ustma-ust tushmasdan ketma-ket', () {
      for (final startDay in [1, 10, 15, 28, 29, 30, 31]) {
        final cal = BudgetCalendar(monthStartDay: startDay);
        var period = cal.monthOf(d(2025, 1, 1));
        for (var i = 0; i < 30; i++) {
          final next = cal.monthOf(period.endExclusive);
          expect(next.start, period.endExclusive, reason: 'start=$startDay');
          expect(period.lengthInDays, inInclusiveRange(28, 31));
          period = next;
        }
      }
    });

    test('boʻsh oraliq yaratilmaydi', () {
      expect(
        () => DateRange(d(2026, 1, 2), d(2026, 1, 2)),
        throwsArgumentError,
      );
    });
  });

  group('UUIDv7', () {
    test('format: versiya 7, variant 10', () {
      final gen = UuidV7Generator(clock: FakeClock());
      for (var i = 0; i < 1000; i++) {
        expect(gen.next(), matches(UuidV7Generator.pattern));
      }
    });

    test('ichidagi vaqt soatdan olinadi', () {
      final clock = FakeClock();
      final id = UuidV7Generator(clock: clock).next();
      expect(UuidV7Generator.timestampOf(id), clock.nowUtc());
    });

    test('bir ms ichida ham, soat orqaga ketsa ham tartib oʻsadi', () {
      final clock = FakeClock();
      final gen = UuidV7Generator(clock: clock, random: Random(1));
      final ids = <String>[];
      for (var i = 0; i < 10000; i++) {
        if (i % 3000 == 0) clock.advance(const Duration(milliseconds: 1));
        if (i == 5000) clock.advance(const Duration(seconds: -10));
        ids.add(gen.next());
      }
      final sorted = [...ids]..sort();
      expect(ids, sorted);
      expect(ids.toSet(), hasLength(ids.length));
    });

    test('hisoblagich toʻlsa vaqt 1 ms oldinga suriladi', () {
      final clock = FakeClock();
      final gen = UuidV7Generator(clock: clock, random: Random(3));
      final first = UuidV7Generator.timestampOf(gen.next());
      var last = '';
      for (var i = 0; i < 5000; i++) {
        last = gen.next();
      }
      expect(UuidV7Generator.timestampOf(last).isAfter(first), isTrue);
    });
  });
}
