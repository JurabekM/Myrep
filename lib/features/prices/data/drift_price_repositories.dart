import 'package:baraka_daftari/core/db/app_database.dart';
import 'package:baraka_daftari/core/db/database_provider.dart';
import 'package:baraka_daftari/core/db/synced_repository.dart';
import 'package:baraka_daftari/core/domain/sync_meta.dart';
import 'package:baraka_daftari/core/money/money.dart';
import 'package:baraka_daftari/core/time/clock.dart';
import 'package:baraka_daftari/features/prices/domain/prices.dart';
import 'package:drift/drift.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:riverpod_annotation/riverpod_annotation.dart';

part 'drift_price_repositories.g.dart';

SyncMeta _meta(
  String id,
  String householdId,
  DateTime createdAt,
  DateTime updatedAt,
  DateTime? deletedAt,
  int version,
) => DriftSyncedRepository.metaOf(
  id: id,
  householdId: householdId,
  createdAt: createdAt,
  updatedAt: updatedAt,
  deletedAt: deletedAt,
  version: version,
);

class DriftPriceItemRepository
    extends DriftSyncedRepository<$PriceItemsTable, PriceItemRow, PriceItem>
    implements PriceItemRepository {
  DriftPriceItemRepository(super.db, super.clock);

  @override
  TableInfo<$PriceItemsTable, PriceItemRow> get table => db.priceItems;

  @override
  String get entityName => 'price_item';

  @override
  List<OrderingTerm Function($PriceItemsTable)> get defaultOrder => [
    (t) => OrderingTerm.asc(t.sortOrder),
    (t) => OrderingTerm.asc(t.createdAt),
  ];

  @override
  PriceItem fromRow(PriceItemRow r) => PriceItem(
    meta: _meta(
      r.id,
      r.householdId,
      r.createdAt,
      r.updatedAt,
      r.deletedAt,
      r.version,
    ),
    name: r.name,
    unit: r.unit,
    monthlyQuantityMilli: r.monthlyQuantityMilli,
    sortOrder: r.sortOrder,
    isArchived: r.isArchived,
  );

  @override
  Insertable<PriceItemRow> toRow(PriceItem e) => PriceItemsCompanion.insert(
    id: e.meta.id,
    householdId: e.meta.householdId,
    createdAt: e.meta.createdAt,
    updatedAt: e.meta.updatedAt,
    deletedAt: Value(e.meta.deletedAt),
    version: Value(e.meta.version),
    name: e.name,
    unit: e.unit,
    monthlyQuantityMilli: Value(e.monthlyQuantityMilli),
    sortOrder: Value(e.sortOrder),
    isArchived: Value(e.isArchived),
  );

  @override
  PriceItem withMeta(PriceItem e, SyncMeta meta) => e.copyWith(meta: meta);
}

class DriftPricePointRepository
    extends DriftSyncedRepository<$PricePointsTable, PricePointRow, PricePoint>
    implements PricePointRepository {
  DriftPricePointRepository(super.db, super.clock);

  @override
  TableInfo<$PricePointsTable, PricePointRow> get table => db.pricePoints;

  @override
  String get entityName => 'price_point';

  @override
  PricePoint fromRow(PricePointRow r) => PricePoint(
    meta: _meta(
      r.id,
      r.householdId,
      r.createdAt,
      r.updatedAt,
      r.deletedAt,
      r.version,
    ),
    itemId: r.itemId,
    price: Money(r.priceMinor, r.currency),
    observedOn: r.observedOn,
    place: r.place,
  );

  @override
  Insertable<PricePointRow> toRow(PricePoint e) => PricePointsCompanion.insert(
    id: e.meta.id,
    householdId: e.meta.householdId,
    createdAt: e.meta.createdAt,
    updatedAt: e.meta.updatedAt,
    deletedAt: Value(e.meta.deletedAt),
    version: Value(e.meta.version),
    itemId: e.itemId,
    priceMinor: e.price.minorUnits,
    currency: e.price.currency,
    observedOn: e.observedOn,
    place: Value(e.place),
  );

  @override
  PricePoint withMeta(PricePoint e, SyncMeta meta) => e.copyWith(meta: meta);

  @override
  Future<List<PricePoint>> forItem(String itemId) async {
    final rows =
        await (db.select(table)
              ..where((t) => t.itemId.equals(itemId) & t.deletedAt.isNull())
              ..orderBy([(t) => OrderingTerm.asc(t.observedOn)]))
            .get();
    return rows.map(fromRow).toList();
  }
}

@Riverpod(keepAlive: true)
Future<PriceItemRepository> priceItemRepository(Ref ref) async =>
    DriftPriceItemRepository(
      await ref.watch(appDatabaseProvider.future),
      ref.watch(clockProvider),
    );

@Riverpod(keepAlive: true)
Future<PricePointRepository> pricePointRepository(Ref ref) async =>
    DriftPricePointRepository(
      await ref.watch(appDatabaseProvider.future),
      ref.watch(clockProvider),
    );
