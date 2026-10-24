import 'package:baraka_daftari/core/money/money.dart';
import 'package:baraka_daftari/core/time/calendar.dart';
import 'package:baraka_daftari/features/prices/domain/price_math.dart';
import 'package:flutter_test/flutter_test.dart';

Money som(int major) => Money.major(major, CurrencyCode.uzs);
LocalDate d(int y, int m, int day) => LocalDate(y, m, day);

void main() {
  test('narx sanada: shu kungacha eng soʻnggi kuzatuv', () {
    final points = [
      Observation(d(2023, 10, 1), som(80000)),
      Observation(d(2025, 3, 1), som(110000)),
      Observation(d(2026, 10, 1), som(130000)),
    ];
    expect(priceAt(points, d(2023, 9, 30)), isNull);
    expect(priceAt(points, d(2024, 1, 1)), som(80000));
    expect(priceAt(points, d(2026, 10, 1)), som(130000));
  });

  test('SPEC misollari: goʻsht +62,5 %, non +50 %', () {
    expect(changeBasisPoints(som(80000), som(130000)), 6250);
    expect(changeBasisPoints(som(2000), som(3000)), 5000);
    expect(changeBasisPoints(som(3000), som(2400)), -2000);
  });

  group('shaxsiy inflyatsiya indeksi', () {
    final meat = BasketLine(
      quantityMilli: 4000, // oyiga 4 kg
      points: [
        Observation(d(2025, 10, 1), som(100000)),
        Observation(d(2026, 10, 1), som(130000)),
      ],
    );
    final bread = BasketLine(
      quantityMilli: 30000, // oyiga 30 dona
      points: [
        Observation(d(2025, 10, 1), som(2000)),
        Observation(d(2026, 10, 1), som(3000)),
      ],
    );

    test('ogʻirliklar boʻyicha: savat 460 000 → 610 000 = +32,61 %', () {
      // Oldin: 4 × 100 000 + 30 × 2 000 = 460 000.
      // Keyin: 4 × 130 000 + 30 × 3 000 = 610 000.
      expect(
        personalInflationBp([meat, bread], d(2025, 10, 1), d(2026, 10, 1)),
        3261,
      );
    });

    test('ogʻirlik muhim: koʻproq non — indeks nonga yaqin', () {
      final lotsOfBread = BasketLine(
        quantityMilli: 300000,
        points: bread.points,
      );
      final bp = personalInflationBp(
        [meat, lotsOfBread],
        d(2025, 10, 1),
        d(2026, 10, 1),
      )!;
      // 4 × 100 000 + 300 × 2 000 = 1 000 000 → 1 420 000: +42 % —
      // goʻsht (+30 %) emas, nonga (+50 %) yaqin.
      expect(bp, 4200);
    });

    test('ikkala sanada narxi yoʻq mahsulot qatnashmaydi', () {
      final newItem = BasketLine(
        quantityMilli: 1000,
        points: [Observation(d(2026, 9, 1), som(999999))],
      );
      expect(
        personalInflationBp([meat, newItem], d(2025, 10, 1), d(2026, 10, 1)),
        3000,
      );
      expect(
        personalInflationBp([newItem], d(2025, 10, 1), d(2026, 10, 1)),
        isNull,
      );
      expect(
        personalInflationBp(const [], d(2025, 1, 1), d(2026, 1, 1)),
        isNull,
      );
    });
  });

  group('«Inflyatsiya taʼsiri»', () {
    test('1 950 000 soʻmga 130 000 lik goʻshtdan 15 kg', () {
      expect(purchasableMilli(som(1950000), som(130000)), 15000);
      expect(purchasableMilli(som(100000), som(130000)), 769);
      expect(purchasableMilli(som(1), const Money.zero(CurrencyCode.uzs)), 0);
    });

    test('yillik 30 % bilan 2 yildan keyin narx va kg', () {
      final later = projectPrice(som(130000), 3000, 2);
      expect(later, som(219700));
      expect(purchasableMilli(som(1950000), later), 8875);
      expect(projectPrice(som(130000), 3000, 0), som(130000));
    });
  });
}
