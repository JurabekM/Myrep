import 'package:baraka_daftari/core/db/app_database.dart';
import 'package:baraka_daftari/core/db/database_provider.dart';
import 'package:baraka_daftari/core/db/synced_repository.dart';
import 'package:baraka_daftari/core/domain/sync_meta.dart';
import 'package:baraka_daftari/core/money/money.dart';
import 'package:baraka_daftari/core/time/clock.dart';
import 'package:baraka_daftari/features/budget/domain/budget.dart';
import 'package:baraka_daftari/features/budget/domain/rescue.dart';
import 'package:drift/drift.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:riverpod_annotation/riverpod_annotation.dart';

part 'drift_budget_repositories.g.dart';

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

class DriftHavasLimitRepository
    extends DriftSyncedRepository<$HavasLimitsTable, HavasLimitRow, HavasLimit>
    implements HavasLimitRepository {
  DriftHavasLimitRepository(super.db, super.clock);

  @override
  TableInfo<$HavasLimitsTable, HavasLimitRow> get table => db.havasLimits;

  @override
  String get entityName => 'havas_limit';

  @override
  HavasLimit fromRow(HavasLimitRow r) => HavasLimit(
    meta: _meta(
      r.id,
      r.householdId,
      r.createdAt,
      r.updatedAt,
      r.deletedAt,
      r.version,
    ),
    amount: Money(r.amountMinor, r.currency),
    proposedBy: r.proposedBy,
  );

  @override
  Insertable<HavasLimitRow> toRow(HavasLimit e) => HavasLimitsCompanion.insert(
    id: e.meta.id,
    householdId: e.meta.householdId,
    createdAt: e.meta.createdAt,
    updatedAt: e.meta.updatedAt,
    deletedAt: Value(e.meta.deletedAt),
    version: Value(e.meta.version),
    amountMinor: e.amount.minorUnits,
    currency: e.amount.currency,
    proposedBy: Value(e.proposedBy),
  );

  @override
  HavasLimit withMeta(HavasLimit e, SyncMeta meta) => e.copyWith(meta: meta);
}

class DriftLimitConsentRepository
    extends
        DriftSyncedRepository<
          $LimitConsentsTable,
          LimitConsentRow,
          LimitConsent
        >
    implements LimitConsentRepository {
  DriftLimitConsentRepository(super.db, super.clock);

  @override
  TableInfo<$LimitConsentsTable, LimitConsentRow> get table => db.limitConsents;

  @override
  String get entityName => 'limit_consent';

  @override
  LimitConsent fromRow(LimitConsentRow r) => LimitConsent(
    meta: _meta(
      r.id,
      r.householdId,
      r.createdAt,
      r.updatedAt,
      r.deletedAt,
      r.version,
    ),
    limitId: r.limitId,
    memberId: r.memberId,
  );

  @override
  Insertable<LimitConsentRow> toRow(LimitConsent e) =>
      LimitConsentsCompanion.insert(
        id: e.meta.id,
        householdId: e.meta.householdId,
        createdAt: e.meta.createdAt,
        updatedAt: e.meta.updatedAt,
        deletedAt: Value(e.meta.deletedAt),
        version: Value(e.meta.version),
        limitId: e.limitId,
        memberId: e.memberId,
      );

  @override
  LimitConsent withMeta(LimitConsent e, SyncMeta meta) =>
      e.copyWith(meta: meta);

  @override
  Future<List<LimitConsent>> forLimit(String limitId) async {
    final rows =
        await (db.select(table)..where(
              (t) => t.limitId.equals(limitId) & t.deletedAt.isNull(),
            ))
            .get();
    return rows.map(fromRow).toList();
  }
}

class DriftScheduledTreatRepository
    extends
        DriftSyncedRepository<
          $ScheduledTreatsTable,
          ScheduledTreatRow,
          ScheduledTreat
        >
    implements ScheduledTreatRepository {
  DriftScheduledTreatRepository(super.db, super.clock);

  @override
  TableInfo<$ScheduledTreatsTable, ScheduledTreatRow> get table =>
      db.scheduledTreats;

  @override
  String get entityName => 'scheduled_treat';

  @override
  List<OrderingTerm Function($ScheduledTreatsTable)> get defaultOrder => [
    (t) => OrderingTerm.asc(t.createdAt),
  ];

  @override
  ScheduledTreat fromRow(ScheduledTreatRow r) => ScheduledTreat(
    meta: _meta(
      r.id,
      r.householdId,
      r.createdAt,
      r.updatedAt,
      r.deletedAt,
      r.version,
    ),
    title: r.title,
    amount: Money(r.amountMinor, r.currency),
    weekday: r.weekday,
    isActive: r.isActive,
  );

  @override
  Insertable<ScheduledTreatRow> toRow(ScheduledTreat e) =>
      ScheduledTreatsCompanion.insert(
        id: e.meta.id,
        householdId: e.meta.householdId,
        createdAt: e.meta.createdAt,
        updatedAt: e.meta.updatedAt,
        deletedAt: Value(e.meta.deletedAt),
        version: Value(e.meta.version),
        title: e.title,
        amountMinor: e.amount.minorUnits,
        currency: e.amount.currency,
        weekday: e.weekday,
        isActive: Value(e.isActive),
      );

  @override
  ScheduledTreat withMeta(ScheduledTreat e, SyncMeta meta) =>
      e.copyWith(meta: meta);
}

class DriftHabitRepository
    extends DriftSyncedRepository<$HabitsTable, HabitRow, Habit>
    implements HabitRepository {
  DriftHabitRepository(super.db, super.clock);

  @override
  TableInfo<$HabitsTable, HabitRow> get table => db.habits;

  @override
  String get entityName => 'habit';

  @override
  List<OrderingTerm Function($HabitsTable)> get defaultOrder => [
    (t) => OrderingTerm.asc(t.createdAt),
  ];

  @override
  Habit fromRow(HabitRow r) => Habit(
    meta: _meta(
      r.id,
      r.householdId,
      r.createdAt,
      r.updatedAt,
      r.deletedAt,
      r.version,
    ),
    title: r.title,
    isArchived: r.isArchived,
  );

  @override
  Insertable<HabitRow> toRow(Habit e) => HabitsCompanion.insert(
    id: e.meta.id,
    householdId: e.meta.householdId,
    createdAt: e.meta.createdAt,
    updatedAt: e.meta.updatedAt,
    deletedAt: Value(e.meta.deletedAt),
    version: Value(e.meta.version),
    title: e.title,
    isArchived: Value(e.isArchived),
  );

  @override
  Habit withMeta(Habit e, SyncMeta meta) => e.copyWith(meta: meta);
}

@Riverpod(keepAlive: true)
Future<HavasLimitRepository> havasLimitRepository(Ref ref) async =>
    DriftHavasLimitRepository(
      await ref.watch(appDatabaseProvider.future),
      ref.watch(clockProvider),
    );

@Riverpod(keepAlive: true)
Future<LimitConsentRepository> limitConsentRepository(Ref ref) async =>
    DriftLimitConsentRepository(
      await ref.watch(appDatabaseProvider.future),
      ref.watch(clockProvider),
    );

@Riverpod(keepAlive: true)
Future<ScheduledTreatRepository> scheduledTreatRepository(Ref ref) async =>
    DriftScheduledTreatRepository(
      await ref.watch(appDatabaseProvider.future),
      ref.watch(clockProvider),
    );

@Riverpod(keepAlive: true)
Future<HabitRepository> habitRepository(Ref ref) async => DriftHabitRepository(
  await ref.watch(appDatabaseProvider.future),
  ref.watch(clockProvider),
);

class DriftSavingsRescueRepository
    extends
        DriftSyncedRepository<
          $SavingsRescuesTable,
          SavingsRescueRow,
          SavingsRescue
        >
    implements SavingsRescueRepository {
  DriftSavingsRescueRepository(super.db, super.clock);

  @override
  TableInfo<$SavingsRescuesTable, SavingsRescueRow> get table =>
      db.savingsRescues;

  @override
  String get entityName => 'savings_rescue';

  @override
  SavingsRescue fromRow(SavingsRescueRow r) => SavingsRescue(
    meta: _meta(
      r.id,
      r.householdId,
      r.createdAt,
      r.updatedAt,
      r.deletedAt,
      r.version,
    ),
    kind: r.kind,
    amount: Money(r.amountMinor, r.currency),
    occurredOn: r.occurredOn,
    sourceId: r.sourceId,
  );

  @override
  Insertable<SavingsRescueRow> toRow(SavingsRescue e) =>
      SavingsRescuesCompanion.insert(
        id: e.meta.id,
        householdId: e.meta.householdId,
        createdAt: e.meta.createdAt,
        updatedAt: e.meta.updatedAt,
        deletedAt: Value(e.meta.deletedAt),
        version: Value(e.meta.version),
        kind: e.kind,
        amountMinor: e.amount.minorUnits,
        currency: e.amount.currency,
        occurredOn: e.occurredOn,
        sourceId: Value(e.sourceId),
      );

  @override
  SavingsRescue withMeta(SavingsRescue e, SyncMeta meta) =>
      e.copyWith(meta: meta);
}

@Riverpod(keepAlive: true)
Future<SavingsRescueRepository> savingsRescueRepository(Ref ref) async =>
    DriftSavingsRescueRepository(
      await ref.watch(appDatabaseProvider.future),
      ref.watch(clockProvider),
    );
