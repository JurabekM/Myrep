import 'package:baraka_daftari/core/domain/sync_meta.dart';
import 'package:baraka_daftari/core/errors/data_exceptions.dart';
import 'package:baraka_daftari/core/money/money.dart';
import 'package:baraka_daftari/core/time/calendar.dart';
import 'package:baraka_daftari/core/time/clock.dart';
import 'package:baraka_daftari/features/household/domain/household.dart';
import 'package:baraka_daftari/features/prices/domain/price_math.dart';
import 'package:baraka_daftari/features/prices/domain/prices.dart';
import 'package:meta/meta.dart';

/// Mahsulotning narx tarixi va «oldin → bugun» taqqoslash.
@immutable
final class ItemHistory {
  const ItemHistory({required this.item, required this.points});

  final PriceItem item;

  /// Sana bo'yicha (eskisi birinchi).
  final List<PricePoint> points;

  PricePoint? get first => points.isEmpty ? null : points.first;
  PricePoint? get last => points.isEmpty ? null : points.last;

  /// Birinchi va oxirgi narx orasidagi o'zgarish (bp); kamida 2 ta narx.
  int? get changeBp =>
      points.length < 2 ? null : changeBasisPoints(first!.price, last!.price);

  List<Observation> get observations => [
    for (final p in points) Observation(p.observedOn, p.price),
  ];
}

/// «Narx daftari» holati (SPEC 2C.1).
@immutable
final class PriceBookOverview {
  const PriceBookOverview({
    required this.items,
    required this.today,
    required this.streakWeeks,
    this.yearInflationBp,
    this.sinceStartBp,
    this.startDate,
  });

  final List<ItemHistory> items;
  final LocalDate today;

  /// Ketma-ket narx kiritilgan haftalar (joriy hafta hali bo'lmasa — o'tgan
  /// haftagacha).
  final int streakWeeks;

  /// Shaxsiy inflyatsiya: bir yil oldin → bugun (bp).
  final int? yearInflationBp;

  /// Birinchi kuzatuvdan bugungacha (bp).
  final int? sinceStartBp;
  final LocalDate? startDate;
}

/// «Narx daftari» va shaxsiy inflyatsiya indeksi.
class PriceBookService {
  PriceBookService({
    required HouseholdRepository households,
    required PriceItemRepository items,
    required PricePointRepository points,
    required SyncMetaFactory metaFactory,
    required Clock clock,
  }) : _households = households,
       _items = items,
       _points = points,
       _meta = metaFactory,
       _clock = clock;

  static const errNameRequired = 'price_item_name_required';
  static const errQuantity = 'price_item_quantity_positive';
  static const errNotPositive = 'price_must_be_positive';
  static const errFuture = 'price_date_in_future';

  final HouseholdRepository _households;
  final PriceItemRepository _items;
  final PricePointRepository _points;
  final SyncMetaFactory _meta;
  final Clock _clock;

  LocalDate get _today => Tashkent.dateOf(_clock.nowUtc());

  Future<PriceItem> addItem({
    required String name,
    required String unit,
    int monthlyQuantityMilli = 1000,
  }) async {
    if (name.trim().isEmpty) throw const DomainRuleException(errNameRequired);
    if (monthlyQuantityMilli <= 0) {
      throw const DomainRuleException(errQuantity);
    }
    final hh = (await _households.current()).meta.id;
    final count = (await _items.listActive(hh)).length;
    return _items.add(
      PriceItem(
        meta: _meta.create(hh),
        name: name.trim(),
        unit: unit.trim(),
        monthlyQuantityMilli: monthlyQuantityMilli,
        sortOrder: count,
      ),
    );
  }

  Future<void> archiveItem(PriceItem item) async {
    await _items.update(item.copyWith(isArchived: true));
  }

  /// Narx kiritish (o'tgan sana ham — eski daftardan ko'chirish uchun).
  Future<PricePoint> addPrice(
    PriceItem item,
    Money price, {
    LocalDate? on,
    String? place,
  }) async {
    if (!price.isPositive) throw const DomainRuleException(errNotPositive);
    final date = on ?? _today;
    if (date.isAfter(_today)) throw const DomainRuleException(errFuture);
    return _points.add(
      PricePoint(
        meta: _meta.create(item.meta.householdId),
        itemId: item.meta.id,
        price: price,
        observedOn: date,
        place: (place?.trim().isEmpty ?? true) ? null : place!.trim(),
      ),
    );
  }

  Future<PriceBookOverview> overview() async {
    final h = await _households.current();
    final today = _today;
    final items = [
      for (final i in await _items.listActive(h.meta.id))
        if (!i.isArchived)
          ItemHistory(item: i, points: await _points.forItem(i.meta.id)),
    ];
    final basket = [
      for (final i in items)
        BasketLine(
          quantityMilli: i.item.monthlyQuantityMilli,
          points: i.observations,
        ),
    ];
    LocalDate? start;
    for (final i in items) {
      final f = i.first?.observedOn;
      if (f != null && (start == null || f.isBefore(start))) start = f;
    }
    // 29-fevral → 28-fevral.
    final yearAgo = LocalDate(
      today.year - 1,
      today.month,
      today.day.clamp(1, LocalDate.daysInMonth(today.year - 1, today.month)),
    );
    return PriceBookOverview(
      items: items,
      today: today,
      streakWeeks: _streak(h.calendar, today, [
        for (final i in items)
          for (final p in i.points) p.meta.createdAt,
      ]),
      yearInflationBp: personalInflationBp(basket, yearAgo, today),
      sinceStartBp: start == null
          ? null
          : personalInflationBp(basket, start, today),
      startDate: start,
    );
  }

  /// Narx kiritish odati: ketma-ket haftalar (kiritilgan vaqt bo'yicha).
  static int _streak(
    BudgetCalendar calendar,
    LocalDate today,
    List<DateTime> entries,
  ) {
    final weeks = {
      for (final e in entries) calendar.weekOf(Tashkent.dateOf(e)).start,
    };
    var week = calendar.weekOf(today).start;
    if (!weeks.contains(week)) week = week.plusDays(-7);
    var n = 0;
    while (weeks.contains(week)) {
      n++;
      week = week.plusDays(-7);
    }
    return n;
  }
}
