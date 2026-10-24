import 'package:baraka_daftari/core/db/app_database.dart';
import 'package:baraka_daftari/core/db/database_provider.dart';
import 'package:baraka_daftari/core/db/synced_repository.dart';
import 'package:baraka_daftari/core/domain/sync_meta.dart';
import 'package:baraka_daftari/core/money/money.dart';
import 'package:baraka_daftari/core/time/calendar.dart';
import 'package:baraka_daftari/core/time/clock.dart';
import 'package:baraka_daftari/features/income/domain/income.dart';
import 'package:drift/drift.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:riverpod_annotation/riverpod_annotation.dart';

part 'drift_income_repository.g.dart';

class DriftIncomeRepository
    extends DriftSyncedRepository<$IncomesTable, IncomeRow, Income>
    implements IncomeRepository {
  DriftIncomeRepository(super.db, super.clock);

  @override
  TableInfo<$IncomesTable, IncomeRow> get table => db.incomes;

  @override
  String get entityName => 'income';

  @override
  List<OrderingTerm Function($IncomesTable)> get defaultOrder => [
    (t) => OrderingTerm.desc(t.receivedAt),
    (t) => OrderingTerm.desc(t.id),
  ];

  @override
  Income fromRow(IncomeRow r) => Income(
    meta: DriftSyncedRepository.metaOf(
      id: r.id,
      householdId: r.householdId,
      createdAt: r.createdAt,
      updatedAt: r.updatedAt,
      deletedAt: r.deletedAt,
      version: r.version,
    ),
    amount: Money(r.amountMinor, r.currency),
    source: r.source,
    channel: r.channel,
    receivedAt: r.receivedAt.toUtc(),
    memberId: r.memberId,
    sourceType: r.sourceType,
    note: r.note,
  );

  @override
  Insertable<IncomeRow> toRow(Income e) => IncomesCompanion.insert(
    id: e.meta.id,
    householdId: e.meta.householdId,
    createdAt: e.meta.createdAt,
    updatedAt: e.meta.updatedAt,
    deletedAt: Value(e.meta.deletedAt),
    version: Value(e.meta.version),
    amountMinor: e.amount.minorUnits,
    currency: e.amount.currency,
    source: e.source,
    channel: e.channel,
    receivedAt: e.receivedAt,
    memberId: Value(e.memberId),
    sourceType: Value(e.sourceType),
    note: Value(e.note),
  );

  @override
  Income withMeta(Income e, SyncMeta meta) => e.copyWith(meta: meta);

  @override
  Future<List<Income>> listInRange(String householdId, DateRange range) async {
    final rows =
        await (activeQuery(householdId)..where(
              (t) =>
                  t.receivedAt.isBiggerOrEqualValue(range.startInstant) &
                  t.receivedAt.isSmallerThanValue(range.endInstantExclusive),
            ))
            .get();
    return rows.map(fromRow).toList();
  }

  @override
  Future<List<Money>> recentAmounts(
    String householdId, {
    int limit = 3,
  }) async {
    final rows = await db
        .customSelect(
          'SELECT amount_minor, currency, MAX(received_at) AS last_at '
          'FROM incomes WHERE household_id = ? AND deleted_at IS NULL '
          'GROUP BY amount_minor, currency ORDER BY last_at DESC LIMIT ?',
          variables: [Variable<String>(householdId), Variable<int>(limit)],
          readsFrom: {db.incomes},
        )
        .get();
    return [
      for (final r in rows)
        Money(
          r.read<int>('amount_minor'),
          CurrencyCode.values.byName(r.read<String>('currency')),
        ),
    ];
  }

  @override
  Future<Income?> latest(String householdId) async {
    final row = await (activeQuery(householdId)..limit(1)).getSingleOrNull();
    return row == null ? null : fromRow(row);
  }
}

@Riverpod(keepAlive: true)
Future<IncomeRepository> incomeRepository(Ref ref) async =>
    DriftIncomeRepository(
      await ref.watch(appDatabaseProvider.future),
      ref.watch(clockProvider),
    );
