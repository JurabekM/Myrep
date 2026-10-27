import 'package:baraka_daftari/core/db/app_database.dart';
import 'package:baraka_daftari/core/db/database_provider.dart';
import 'package:baraka_daftari/core/db/synced_repository.dart';
import 'package:baraka_daftari/core/domain/sync_meta.dart';
import 'package:baraka_daftari/core/money/fx_rate.dart';
import 'package:baraka_daftari/core/money/fx_rate_repository.dart';
import 'package:baraka_daftari/core/money/money.dart';
import 'package:baraka_daftari/core/time/clock.dart';
import 'package:baraka_daftari/core/time/local_date.dart';
import 'package:drift/drift.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:riverpod_annotation/riverpod_annotation.dart';

part 'drift_fx_rate_repository.g.dart';

class DriftFxRateRepository
    extends DriftSyncedRepository<$FxRatesTable, FxRateRow, StoredFxRate>
    implements FxRateRepository {
  DriftFxRateRepository(super.db, super.clock);

  @override
  TableInfo<$FxRatesTable, FxRateRow> get table => db.fxRates;

  @override
  String get entityName => 'fx_rate';

  @override
  List<OrderingTerm Function($FxRatesTable)> get defaultOrder => [
    (t) => OrderingTerm.desc(t.rateDate),
    (t) => OrderingTerm.desc(t.createdAt),
  ];

  @override
  StoredFxRate fromRow(FxRateRow r) {
    final date = r.rateDate;
    return StoredFxRate(
      meta: DriftSyncedRepository.metaOf(
        id: r.id,
        householdId: r.householdId,
        createdAt: r.createdAt,
        updatedAt: r.updatedAt,
        deletedAt: r.deletedAt,
        version: r.version,
      ),
      rate: FxRate(
        from: r.fromCurrency,
        to: r.toCurrency,
        numerator: r.rateNumerator,
        denominator: r.rateDenominator,
        date: DateTime.utc(date.year, date.month, date.day),
        source: r.source,
      ),
    );
  }

  @override
  Insertable<FxRateRow> toRow(StoredFxRate e) => FxRatesCompanion.insert(
    id: e.meta.id,
    householdId: e.meta.householdId,
    createdAt: e.meta.createdAt,
    updatedAt: e.meta.updatedAt,
    deletedAt: Value(e.meta.deletedAt),
    version: Value(e.meta.version),
    fromCurrency: e.rate.from,
    toCurrency: e.rate.to,
    rateNumerator: e.rate.numerator,
    rateDenominator: e.rate.denominator,
    rateDate: LocalDate.fromDateTime(e.rate.date),
    source: Value(e.rate.source),
  );

  @override
  StoredFxRate withMeta(StoredFxRate e, SyncMeta meta) =>
      e.copyWith(meta: meta);

  @override
  Future<StoredFxRate?> latest(
    String householdId,
    CurrencyCode from,
    CurrencyCode to,
  ) async {
    final row =
        await (activeQuery(householdId)
              ..where(
                (t) =>
                    t.fromCurrency.equalsValue(from) &
                    t.toCurrency.equalsValue(to),
              )
              ..limit(1))
            .getSingleOrNull();
    return row == null ? null : fromRow(row);
  }
}

@Riverpod(keepAlive: true)
Future<FxRateRepository> fxRateRepository(Ref ref) async =>
    DriftFxRateRepository(
      await ref.watch(appDatabaseProvider.future),
      ref.watch(clockProvider),
    );
