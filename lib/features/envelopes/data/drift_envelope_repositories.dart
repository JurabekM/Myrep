import 'package:baraka_daftari/core/db/app_database.dart';
import 'package:baraka_daftari/core/db/database_provider.dart';
import 'package:baraka_daftari/core/db/synced_repository.dart';
import 'package:baraka_daftari/core/domain/sync_meta.dart';
import 'package:baraka_daftari/core/money/money.dart';
import 'package:baraka_daftari/core/time/clock.dart';
import 'package:baraka_daftari/features/envelopes/domain/envelope.dart';
import 'package:drift/drift.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:riverpod_annotation/riverpod_annotation.dart';

part 'drift_envelope_repositories.g.dart';

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

class DriftEnvelopeRepository
    extends DriftSyncedRepository<$EnvelopesTable, EnvelopeRow, Envelope>
    implements EnvelopeRepository {
  DriftEnvelopeRepository(super.db, super.clock);

  @override
  TableInfo<$EnvelopesTable, EnvelopeRow> get table => db.envelopes;

  @override
  String get entityName => 'envelope';

  @override
  List<OrderingTerm Function($EnvelopesTable)> get defaultOrder => [
    (t) => OrderingTerm.asc(t.createdAt),
  ];

  @override
  Envelope fromRow(EnvelopeRow r) => Envelope(
    meta: _meta(
      r.id,
      r.householdId,
      r.createdAt,
      r.updatedAt,
      r.deletedAt,
      r.version,
    ),
    title: r.title,
    weeklyLimit: Money(r.weeklyLimitMinor, r.currency),
    isCash: r.isCash,
    categoryIds: [
      for (final id in r.categoryIds.split(','))
        if (id.isNotEmpty) id,
    ],
    isArchived: r.isArchived,
  );

  @override
  Insertable<EnvelopeRow> toRow(Envelope e) => EnvelopesCompanion.insert(
    id: e.meta.id,
    householdId: e.meta.householdId,
    createdAt: e.meta.createdAt,
    updatedAt: e.meta.updatedAt,
    deletedAt: Value(e.meta.deletedAt),
    version: Value(e.meta.version),
    title: e.title,
    weeklyLimitMinor: e.weeklyLimit.minorUnits,
    currency: e.weeklyLimit.currency,
    isCash: Value(e.isCash),
    categoryIds: Value(e.categoryIds.join(',')),
    isArchived: Value(e.isArchived),
  );

  @override
  Envelope withMeta(Envelope e, SyncMeta meta) => e.copyWith(meta: meta);
}

class DriftEnvelopePeriodRepository
    extends
        DriftSyncedRepository<
          $EnvelopePeriodsTable,
          EnvelopePeriodRow,
          EnvelopePeriod
        >
    implements EnvelopePeriodRepository {
  DriftEnvelopePeriodRepository(super.db, super.clock);

  @override
  TableInfo<$EnvelopePeriodsTable, EnvelopePeriodRow> get table =>
      db.envelopePeriods;

  @override
  String get entityName => 'envelope_period';

  @override
  EnvelopePeriod fromRow(EnvelopePeriodRow r) => EnvelopePeriod(
    meta: _meta(
      r.id,
      r.householdId,
      r.createdAt,
      r.updatedAt,
      r.deletedAt,
      r.version,
    ),
    envelopeId: r.envelopeId,
    weekStart: r.weekStart,
    limit: Money(r.limitMinor, r.currency),
    leftover: r.leftoverMinor == null
        ? null
        : Money(r.leftoverMinor!, r.currency),
    closedAt: r.closedAt?.toUtc(),
  );

  @override
  Insertable<EnvelopePeriodRow> toRow(EnvelopePeriod e) =>
      EnvelopePeriodsCompanion.insert(
        id: e.meta.id,
        householdId: e.meta.householdId,
        createdAt: e.meta.createdAt,
        updatedAt: e.meta.updatedAt,
        deletedAt: Value(e.meta.deletedAt),
        version: Value(e.meta.version),
        envelopeId: e.envelopeId,
        weekStart: e.weekStart,
        limitMinor: e.limit.minorUnits,
        currency: e.limit.currency,
        leftoverMinor: Value(e.leftover?.minorUnits),
        closedAt: Value(e.closedAt),
      );

  @override
  EnvelopePeriod withMeta(EnvelopePeriod e, SyncMeta meta) =>
      e.copyWith(meta: meta);

  @override
  Future<List<EnvelopePeriod>> forEnvelope(String envelopeId) async {
    final rows =
        await (db.select(table)
              ..where(
                (t) => t.envelopeId.equals(envelopeId) & t.deletedAt.isNull(),
              )
              ..orderBy([(t) => OrderingTerm.asc(t.weekStart)]))
            .get();
    return rows.map(fromRow).toList();
  }
}

@Riverpod(keepAlive: true)
Future<EnvelopeRepository> envelopeRepository(Ref ref) async =>
    DriftEnvelopeRepository(
      await ref.watch(appDatabaseProvider.future),
      ref.watch(clockProvider),
    );

@Riverpod(keepAlive: true)
Future<EnvelopePeriodRepository> envelopePeriodRepository(Ref ref) async =>
    DriftEnvelopePeriodRepository(
      await ref.watch(appDatabaseProvider.future),
      ref.watch(clockProvider),
    );
