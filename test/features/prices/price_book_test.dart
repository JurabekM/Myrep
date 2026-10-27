import 'package:baraka_daftari/core/errors/data_exceptions.dart';
import 'package:baraka_daftari/core/money/money.dart';
import 'package:baraka_daftari/core/time/calendar.dart';
import 'package:baraka_daftari/features/household/data/drift_household_repository.dart';
import 'package:baraka_daftari/features/prices/data/drift_price_repositories.dart';
import 'package:baraka_daftari/features/prices/domain/price_book_service.dart';
import 'package:flutter_test/flutter_test.dart';

import '../../helpers/db.dart';

Money som(int major) => Money.major(major, CurrencyCode.uzs);

void main() {
  late TestDb t;
  late PriceBookService book;

  setUp(() {
    t = TestDb.open();
    book = PriceBookService(
      households: DriftHouseholdRepository(t.db, t.clock),
      items: DriftPriceItemRepository(t.db, t.clock),
      points: DriftPricePointRepository(t.db, t.clock),
      metaFactory: t.meta,
      clock: t.clock,
    );
  });

  test('narx tarixi, oldin → bugun va shaxsiy indeks', () async {
    // Bugun 2026-10-09.
    final meat = await book.addItem(
      name: 'Goʻsht',
      unit: 'kg',
      monthlyQuantityMilli: 4000,
    );
    final bread = await book.addItem(
      name: 'Non',
      unit: 'dona',
      monthlyQuantityMilli: 30000,
    );
    await book.addPrice(meat, som(80000), on: LocalDate(2023, 10, 1));
    await book.addPrice(meat, som(100000), on: LocalDate(2025, 10, 1));
    await book.addPrice(meat, som(130000));
    await book.addPrice(bread, som(2000), on: LocalDate(2025, 10, 1));
    await book.addPrice(bread, som(3000), place: '  Chorsu ');

    final o = await book.overview();
    final m = o.items.firstWhere((i) => i.item.name == 'Goʻsht');
    expect(m.points.map((p) => p.price), [
      som(80000),
      som(100000),
      som(130000),
    ]);
    expect(m.changeBp, 6250, reason: '80 000 → 130 000');
    expect(o.items.last.last!.place, 'Chorsu');
    // 2025-10-09 → bugun: 460 000 → 610 000.
    expect(o.yearInflationBp, 3261);
    // Boshidan: 2023-10-01 da faqat goʻsht maʼlum → +62,5 %.
    expect(o.startDate, LocalDate(2023, 10, 1));
    expect(o.sinceStartBp, 6250);
  });

  test('notoʻgʻri kiritish rad etiladi', () async {
    await expectLater(
      book.addItem(name: ' ', unit: 'kg'),
      throwsA(isA<DomainRuleException>()),
    );
    final item = await book.addItem(name: 'Un', unit: 'kg');
    await expectLater(
      book.addPrice(item, const Money.zero(CurrencyCode.uzs)),
      throwsA(isA<DomainRuleException>()),
    );
    await expectLater(
      book.addPrice(item, som(9000), on: LocalDate(2026, 10, 10)),
      throwsA(isA<DomainRuleException>()),
      reason: 'kelajak sanasi',
    );
  });

  test('narx kiritish odati: ketma-ket haftalar', () async {
    final item = await book.addItem(name: 'Benzin', unit: 'litr');
    expect((await book.overview()).streakWeeks, 0);
    for (var w = 0; w < 3; w++) {
      await book.addPrice(item, som(12000 + w * 100));
      t.clock.advance(const Duration(days: 7));
    }
    // Joriy haftada hali yoʻq — oʻtgan 3 hafta hisoblanadi.
    expect((await book.overview()).streakWeeks, 3);
    t.clock.advance(const Duration(days: 7));
    expect(
      (await book.overview()).streakWeeks,
      0,
      reason: 'bir hafta oʻtkazildi',
    );
  });

  test('arxivlangan mahsulot indeksga kirmaydi', () async {
    final a = await book.addItem(name: 'A', unit: 'kg');
    await book.addPrice(a, som(1000), on: LocalDate(2025, 10, 1));
    await book.addPrice(a, som(5000));
    await book.archiveItem(a);
    final o = await book.overview();
    expect(o.items, isEmpty);
    expect(o.yearInflationBp, isNull);
  });
}
