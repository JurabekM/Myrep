import 'package:baraka_daftari/core/domain/repository.dart';
import 'package:baraka_daftari/core/domain/sync_meta.dart';
import 'package:baraka_daftari/core/money/money.dart';
import 'package:baraka_daftari/core/time/calendar.dart';
import 'package:freezed_annotation/freezed_annotation.dart';

part 'prices.freezed.dart';

/// «Narx daftari» savatidagi mahsulot (`BasketItem`, SPEC 2C.1).
@freezed
abstract class PriceItem with _$PriceItem implements Synced {
  const factory PriceItem({
    required SyncMeta meta,
    required String name,

    /// kg, dona, litr … (foydalanuvchi matni).
    required String unit,

    /// Oylik iste'mol, mingdan birlarda — indeksdagi og'irlik.
    @Default(1000) int monthlyQuantityMilli,
    @Default(0) int sortOrder,
    @Default(false) bool isArchived,
  }) = _PriceItem;
}

/// Narx kuzatuvi (`PricePoint`).
@freezed
abstract class PricePoint with _$PricePoint implements Synced {
  const factory PricePoint({
    required SyncMeta meta,
    required String itemId,
    required Money price,
    required LocalDate observedOn,
    String? place,
  }) = _PricePoint;
}

abstract interface class PriceItemRepository
    implements SyncedRepository<PriceItem> {}

abstract interface class PricePointRepository
    implements SyncedRepository<PricePoint> {
  Future<List<PricePoint>> forItem(String itemId);
}
