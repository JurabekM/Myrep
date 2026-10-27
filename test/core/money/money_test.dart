import 'package:baraka_daftari/core/money/allocation.dart';
import 'package:baraka_daftari/core/money/fx_rate.dart';
import 'package:baraka_daftari/core/money/money.dart';
import 'package:baraka_daftari/core/money/money_format.dart';
import 'package:flutter_test/flutter_test.dart';

const CurrencyCode uzs = CurrencyCode.uzs;
const CurrencyCode usd = CurrencyCode.usd;

Money som(int major) => Money.major(major, uzs);

void main() {
  group('Money', () {
    test('major va minor', () {
      expect(som(8000000).minorUnits, 800000000);
      expect(const Money.zero(uzs).isZero, isTrue);
      expect(uzs.minorPerMajor, 100);
      expect(CurrencyCode.fromIso('usd'), usd);
      expect(() => CurrencyCode.fromIso('XYZ'), throwsArgumentError);
    });

    test('arifmetika', () {
      expect(som(100) + som(50), som(150));
      expect(som(100) - som(150), som(-50));
      expect(-som(5), som(-5));
      expect(som(3).times(4), som(12));
      expect(som(-7).abs(), som(7));
      expect(som(7).abs(), som(7));
      expect(som(1).isPositive, isTrue);
      expect(som(-1).isNegative, isTrue);
      expect(Money.sum([som(1), som(2), som(3)], uzs), som(6));
      expect(Money.sum(const [], uzs), const Money.zero(uzs));
    });

    test('taqqoslash', () {
      expect(som(1) < som(2), isTrue);
      expect(som(2) <= som(2), isTrue);
      expect(som(3) > som(2), isTrue);
      expect(som(2) >= som(3), isFalse);
      expect([som(3), som(1), som(2)]..sort(), [som(1), som(2), som(3)]);
    });

    test('har xil valyutani aralashtirish exception beradi', () {
      final dollars = Money.major(10, usd);
      expect(() => som(1) + dollars, throwsA(isA<CurrencyMismatchException>()));
      expect(() => som(1) - dollars, throwsA(isA<CurrencyMismatchException>()));
      expect(() => som(1) < dollars, throwsA(isA<CurrencyMismatchException>()));
      expect(
        () => Money.sum([som(1), dollars], uzs),
        throwsA(isA<CurrencyMismatchException>()),
      );
      expect(
        const CurrencyMismatchException(uzs, usd).toString(),
        contains('UZS != USD'),
      );
    });

    test('tenglik va hashCode valyutani hisobga oladi', () {
      expect(som(1), som(1));
      expect(som(1).hashCode, som(1).hashCode);
      expect(const Money(100, uzs) == const Money(100, usd), isFalse);
      expect(som(1).toString(), 'Money(100 UZS)');
    });

    test('toshib ketish jim oʻtmaydi', () {
      const max = Money(9223372036854775807, uzs);
      const min = Money(-9223372036854775807 - 1, uzs);
      expect(
        () => max + const Money(1, uzs),
        throwsA(isA<MoneyOverflowException>()),
      );
      expect(
        () => min - const Money(1, uzs),
        throwsA(isA<MoneyOverflowException>()),
      );
      expect(() => -min, throwsA(isA<MoneyOverflowException>()));
      expect(() => max.times(2), throwsA(isA<MoneyOverflowException>()));
      expect(
        () => Money.major(9223372036854775807, uzs),
        throwsA(isA<MoneyOverflowException>()),
      );
      expect(
        const MoneyOverflowException().toString(),
        'MoneyOverflowException',
      );
      expect(som(0).times(5), som(0));
    });

    test('roundTo — 1 000 soʻmgacha', () {
      // 1 234 500 soʻm: aynan yarmi — standart half-up yuqoriga (1 235 000),
      // halfEven juftga (1 234 000).
      expect(const Money(123450000, uzs).roundTo(100000), som(1235000));
      expect(
        const Money(123450000, uzs).roundTo(100000, RoundingMode.halfEven),
        som(1234000),
      );
      expect(
        const Money(123450000, uzs).roundTo(100000),
        som(1235000),
      );
      expect(
        const Money(123449999, uzs).roundTo(100000),
        som(1234000),
      );
      expect(() => som(1).roundTo(0), throwsArgumentError);
    });
  });

  group('MoneyRounding', () {
    // (son, maxraj) → har rejim natijasi.
    final cases = <(int, int), Map<RoundingMode, int>>{
      (25, 10): {
        RoundingMode.halfEven: 2,
        RoundingMode.halfUp: 3,
        RoundingMode.down: 2,
        RoundingMode.up: 3,
        RoundingMode.floor: 2,
        RoundingMode.ceiling: 3,
      },
      (35, 10): {RoundingMode.halfEven: 4, RoundingMode.halfUp: 4},
      (-25, 10): {
        RoundingMode.halfEven: -2,
        RoundingMode.halfUp: -3,
        RoundingMode.down: -2,
        RoundingMode.up: -3,
        RoundingMode.floor: -3,
        RoundingMode.ceiling: -2,
      },
      (21, 10): {
        RoundingMode.halfEven: 2,
        RoundingMode.halfUp: 2,
        RoundingMode.up: 3,
        RoundingMode.ceiling: 3,
        RoundingMode.floor: 2,
      },
      (29, 10): {RoundingMode.halfEven: 3, RoundingMode.down: 2},
      (-29, 10): {RoundingMode.halfEven: -3, RoundingMode.ceiling: -2},
      (20, 10): {RoundingMode.up: 2, RoundingMode.floor: 2},
      (25, -10): {RoundingMode.halfEven: -2, RoundingMode.floor: -3},
    };
    for (final MapEntry(key: (n, d), value: modes) in cases.entries) {
      for (final MapEntry(key: mode, value: expected) in modes.entries) {
        test('$n / $d, ${mode.name} = $expected', () {
          expect(MoneyRounding.divide(n, d, mode), expected);
        });
      }
    }

    test('nolga boʻlish', () {
      expect(() => MoneyRounding.divide(1, 0), throwsArgumentError);
    });

    test('mulDiv oraliq toshishsiz', () {
      // 9e18 * 10000 int64 dan katta, lekin natija sigʻadi.
      expect(
        MoneyRounding.mulDiv(9000000000000000000, 1000, 10000),
        900000000000000000,
      );
      expect(
        () => MoneyRounding.mulDiv(9000000000000000000, 10, 1),
        throwsA(isA<MoneyOverflowException>()),
      );
    });
  });

  group('scaled va ratioBasisPoints (jamlash, SPEC 2B.1)', () {
    test('scaled: bir marta yaxlitlanadi', () {
      // 30 kunda 100 000 → yiliga 1 216 666,67 (tiyingacha).
      expect(som(100000).scaled(365, 30), const Money(121666667, uzs));
      expect(som(300000).scaled(7, 30), som(70000));
      expect(som(-90).scaled(1, 1), som(-90));
      expect(() => som(1).scaled(1, 0), throwsArgumentError);
    });

    test('ratioBasisPoints: ulush bazis punktda', () {
      expect(ratioBasisPoints(som(1200000), som(3000000)), 4000);
      expect(ratioBasisPoints(som(1), som(3)), 3333);
      expect(
        ratioBasisPoints(som(79999), som(100000), RoundingMode.down),
        7999,
      );
      expect(ratioBasisPoints(som(5), const Money.zero(uzs)), isNull);
      expect(
        () => ratioBasisPoints(som(5), Money.major(5, CurrencyCode.usd)),
        throwsA(isA<CurrencyMismatchException>()),
      );
    });
  });

  group('percentOf', () {
    test('10 % va 5 %', () {
      expect(percentOf(som(8000000), 1000), som(800000));
      expect(percentOf(som(150000), 500), som(7500));
    });

    test('tiyinlarda yaxlitlash: allocate([bp, 10000 − bp])[0] (half-up)', () {
      // 0,05 % × 1 soʻm = 0,05 tiyin → 0
      expect(percentOf(const Money(100, uzs), 5), const Money(0, uzs));
      // 12,5 tiyin → 13 (teng kasrda birinchi qism); halfEven bilan 12
      expect(percentOf(const Money(125, uzs), 1000), const Money(13, uzs));
      expect(
        percentOf(const Money(125, uzs), 1000, RoundingMode.halfEven),
        const Money(12, uzs),
      );
      // Manfiy summa simmetrik: −12,5 → −13.
      expect(percentOf(const Money(-125, uzs), 1000), const Money(-13, uzs));
      // 100 % dan katta bp — markazlashgan half-up.
      expect(percentOf(const Money(125, uzs), 15000), const Money(188, uzs));
    });
  });

  group('allocate (largest remainder)', () {
    test('70 / 20 / 10', () {
      expect(allocate(som(1000000), [7000, 2000, 1000]), [
        som(700000),
        som(200000),
        som(100000),
      ]);
    });

    test('qoldiq tiyinlar katta kasrga, teng boʻlsa oldingisiga', () {
      expect(allocate(const Money(100, uzs), [1, 1, 1]), const [
        Money(34, uzs),
        Money(33, uzs),
        Money(33, uzs),
      ]);
      // 1,5 va 3,5 — kasrlar teng, qoldiq tiyin oldingi qismga.
      expect(allocate(const Money(5, uzs), [3, 7]), const [
        Money(2, uzs),
        Money(3, uzs),
      ]);
      // 3,3 / 3,3 / 3,4: qoldiq eng katta kasrli (oxirgi) qismga.
      expect(allocate(const Money(10, uzs), [33, 33, 34]), const [
        Money(3, uzs),
        Money(3, uzs),
        Money(4, uzs),
      ]);
    });

    test('nol nisbatli qism doim nol', () {
      expect(allocate(const Money(10, uzs), [0, 1, 0, 2]), const [
        Money(0, uzs),
        Money(3, uzs),
        Money(0, uzs),
        Money(7, uzs),
      ]);
    });

    test('manfiy summa simmetrik', () {
      expect(allocate(const Money(-100, uzs), [1, 1, 1]), const [
        Money(-34, uzs),
        Money(-33, uzs),
        Money(-33, uzs),
      ]);
    });

    test('notoʻgʻri nisbatlar', () {
      expect(() => allocate(som(1), []), throwsArgumentError);
      expect(() => allocate(som(1), [0, 0]), throwsArgumentError);
      expect(() => allocate(som(1), [1, -1]), throwsArgumentError);
    });
  });

  group('FxRate va convert', () {
    final date = DateTime.utc(2026, 10, 6);

    test('1 USD = 12 650,50 soʻm', () {
      final rate = FxRate.parse(usd, uzs, '12650.50', date);
      expect(rate.numerator, 1265050);
      expect(rate.denominator, 100);
      expect(convert(Money.major(10, usd), rate), som(126505));
      // 0,01 USD = 126,505 soʻm → 12650,5 tiyin → half-up 12651
      expect(convert(const Money(1, usd), rate), const Money(12651, uzs));
    });

    test('teskari kurs va vergulli yozuv', () {
      final rate = FxRate.parse(usd, uzs, '12 650,50', date);
      final back = convert(som(126505), rate.inverse());
      expect(back, Money.major(10, usd));
      expect(rate.inverse().from, uzs);
    });

    test('valyuta mos kelmasa exception', () {
      final rate = FxRate.parse(usd, uzs, '12650', date);
      expect(
        () => convert(som(1), rate),
        throwsA(isA<CurrencyMismatchException>()),
      );
    });

    test('notoʻgʻri kurslar', () {
      expect(() => FxRate.parse(usd, uzs, 'abc', date), throwsFormatException);
      expect(() => FxRate.parse(usd, uzs, '-1', date), throwsFormatException);
      expect(
        () => FxRate(
          from: usd,
          to: usd,
          numerator: 1,
          denominator: 1,
          date: date,
        ),
        throwsArgumentError,
      );
      expect(
        () => FxRate(
          from: usd,
          to: uzs,
          numerator: 0,
          denominator: 1,
          date: date,
        ),
        throwsArgumentError,
      );
    });

    test('tenglik kasr qiymati boʻyicha', () {
      final a = FxRate(
        from: usd,
        to: uzs,
        numerator: 25,
        denominator: 2,
        date: date,
      );
      final b = FxRate(
        from: usd,
        to: uzs,
        numerator: 125,
        denominator: 10,
        date: date,
      );
      expect(a, b);
      expect(a.hashCode, b.hashCode);
    });
  });

  group('MoneyFormatter (UZS)', () {
    String n(String s) => s.replaceAll(' ', nbsp);

    test('8 000 000 soʻm', () {
      expect(MoneyFormatter.format(som(8000000)), n('8 000 000 soʻm'));
      expect(
        MoneyFormatter.format(som(8000000), languageCode: 'ru'),
        n('8 000 000 сум'),
      );
    });

    test('kichik va katta summalar, guruhlash', () {
      expect(MoneyFormatter.format(som(0)), n('0 soʻm'));
      expect(MoneyFormatter.format(som(999)), n('999 soʻm'));
      expect(MoneyFormatter.format(som(1000)), n('1 000 soʻm'));
      expect(MoneyFormatter.format(som(1234567890)), n('1 234 567 890 soʻm'));
    });

    test('tiyin faqat kerak boʻlsa', () {
      expect(
        MoneyFormatter.format(const Money(800000050, uzs)),
        n('8 000 000,50 soʻm'),
      );
      expect(
        MoneyFormatter.format(som(5), alwaysShowMinor: true),
        n('5,00 soʻm'),
      );
    });

    test('manfiy, belgisiz va boshqa valyutalar', () {
      expect(MoneyFormatter.format(som(-15000)), n('-15 000 soʻm'));
      expect(MoneyFormatter.format(som(15000), withSymbol: false), n('15 000'));
      expect(MoneyFormatter.format(const Money(1250, usd)), n(r'12,50 $'));
      expect(MoneyFormatter.format(Money.major(3, CurrencyCode.eur)), n('3 €'));
      expect(MoneyFormatter.format(Money.major(3, CurrencyCode.rub)), n('3 ₽'));
    });
  });

  group('MoneyParser', () {
    test('foydalanuvchi yozuvlari', () {
      expect(MoneyParser.tryParse('8 000 000', uzs), som(8000000));
      expect(MoneyParser.tryParse('8 000 000 soʻm', uzs), som(8000000));
      // Klaviaturalar turli apostrof beradi: ', ‘, ’, ʻ, ʼ, `.
      for (final v in ["so'm", 'so‘m', 'so’m', 'soʻm', 'soʼm', 'so`m', 'som']) {
        expect(MoneyParser.tryParse('1 500 $v', uzs), som(1500), reason: v);
      }
      expect(
        MoneyParser.tryParse('8000000,5', uzs),
        const Money(800000050, uzs),
      );
      expect(MoneyParser.tryParse('12.50', usd), const Money(1250, usd));
      expect(MoneyParser.tryParse('-300', uzs), som(-300));
      expect(MoneyParser.tryParse('150 000 сум', uzs), som(150000));
    });

    test('notoʻgʻri yozuvlar null', () {
      expect(MoneyParser.tryParse('', uzs), isNull);
      expect(MoneyParser.tryParse('abc', uzs), isNull);
      expect(MoneyParser.tryParse('1,234', uzs), isNull); // 3 kasr raqami
      expect(MoneyParser.tryParse('1' * 16, uzs), isNull);
    });

    test('format → parse aylanib qaytadi', () {
      for (final m in [som(0), som(7), som(8000000), const Money(12345, uzs)]) {
        expect(MoneyParser.tryParse(MoneyFormatter.format(m), uzs), m);
      }
    });
  });
}
