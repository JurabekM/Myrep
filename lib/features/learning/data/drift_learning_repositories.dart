import 'package:baraka_daftari/core/db/app_database.dart';
import 'package:baraka_daftari/core/db/database_provider.dart';
import 'package:baraka_daftari/core/db/synced_repository.dart';
import 'package:baraka_daftari/core/domain/sync_meta.dart';
import 'package:baraka_daftari/core/money/money.dart';
import 'package:baraka_daftari/core/time/clock.dart';
import 'package:baraka_daftari/features/learning/domain/learning.dart';
import 'package:drift/drift.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:riverpod_annotation/riverpod_annotation.dart';

part 'drift_learning_repositories.g.dart';

SyncMeta _m(
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

class DriftHourlySnapshotRepository
    extends
        DriftSyncedRepository<
          $HourlySnapshotsTable,
          HourlySnapshotRow,
          HourlySnapshot
        >
    implements HourlySnapshotRepository {
  DriftHourlySnapshotRepository(super.db, super.clock);

  @override
  TableInfo<$HourlySnapshotsTable, HourlySnapshotRow> get table =>
      db.hourlySnapshots;

  @override
  String get entityName => 'hourly_snapshot';

  /// Eng yangisi birinchi.
  @override
  List<OrderingTerm Function($HourlySnapshotsTable)> get defaultOrder => [
    (t) => OrderingTerm.desc(t.createdAt),
    (t) => OrderingTerm.desc(t.id),
  ];

  @override
  HourlySnapshot fromRow(HourlySnapshotRow r) => HourlySnapshot(
    meta: _m(
      r.id,
      r.householdId,
      r.createdAt,
      r.updatedAt,
      r.deletedAt,
      r.version,
    ),
    income: Money(r.incomeMinor, r.currency),
    minutesPerDay: r.minutesPerDay,
    daysPerMonth: r.daysPerMonth,
    maxMinutesPerDay: r.maxMinutesPerDay,
    hourly: Money(r.hourlyMinor, r.currency),
    memberId: r.memberId,
  );

  @override
  Insertable<HourlySnapshotRow> toRow(HourlySnapshot e) =>
      HourlySnapshotsCompanion.insert(
        id: e.meta.id,
        householdId: e.meta.householdId,
        createdAt: e.meta.createdAt,
        updatedAt: e.meta.updatedAt,
        deletedAt: Value(e.meta.deletedAt),
        version: Value(e.meta.version),
        memberId: Value(e.memberId),
        incomeMinor: e.income.minorUnits,
        currency: e.income.currency,
        minutesPerDay: e.minutesPerDay,
        daysPerMonth: e.daysPerMonth,
        maxMinutesPerDay: e.maxMinutesPerDay,
        hourlyMinor: e.hourly.minorUnits,
      );

  @override
  HourlySnapshot withMeta(HourlySnapshot e, SyncMeta meta) =>
      e.copyWith(meta: meta);
}

class DriftLearningGoalRepository
    extends
        DriftSyncedRepository<
          $LearningGoalsTable,
          LearningGoalRow,
          LearningGoal
        >
    implements LearningGoalRepository {
  DriftLearningGoalRepository(super.db, super.clock);

  @override
  TableInfo<$LearningGoalsTable, LearningGoalRow> get table => db.learningGoals;

  @override
  String get entityName => 'learning_goal';

  @override
  List<OrderingTerm Function($LearningGoalsTable)> get defaultOrder => [
    (t) => OrderingTerm.desc(t.createdAt),
    (t) => OrderingTerm.desc(t.id),
  ];

  @override
  LearningGoal fromRow(LearningGoalRow r) => LearningGoal(
    meta: _m(
      r.id,
      r.householdId,
      r.createdAt,
      r.updatedAt,
      r.deletedAt,
      r.version,
    ),
    title: r.title,
    why: r.why,
    baseHourly: Money(r.baseHourlyMinor, r.currency),
    targetHourly: Money(r.targetHourlyMinor, r.currency),
    status: r.status,
    memberId: r.memberId,
    closedAt: r.closedAt,
  );

  @override
  Insertable<LearningGoalRow> toRow(LearningGoal e) =>
      LearningGoalsCompanion.insert(
        id: e.meta.id,
        householdId: e.meta.householdId,
        createdAt: e.meta.createdAt,
        updatedAt: e.meta.updatedAt,
        deletedAt: Value(e.meta.deletedAt),
        version: Value(e.meta.version),
        memberId: Value(e.memberId),
        title: e.title,
        why: Value(e.why),
        baseHourlyMinor: e.baseHourly.minorUnits,
        targetHourlyMinor: e.targetHourly.minorUnits,
        currency: e.baseHourly.currency,
        status: e.status,
        closedAt: Value(e.closedAt),
      );

  @override
  LearningGoal withMeta(LearningGoal e, SyncMeta meta) =>
      e.copyWith(meta: meta);
}

class DriftLearningItemRepository
    extends
        DriftSyncedRepository<
          $LearningItemsTable,
          LearningItemRow,
          LearningItem
        >
    implements LearningItemRepository {
  DriftLearningItemRepository(super.db, super.clock);

  @override
  TableInfo<$LearningItemsTable, LearningItemRow> get table => db.learningItems;

  @override
  String get entityName => 'learning_item';

  @override
  List<OrderingTerm Function($LearningItemsTable)> get defaultOrder => [
    (t) => OrderingTerm.asc(t.createdAt),
    (t) => OrderingTerm.asc(t.id),
  ];

  @override
  LearningItem fromRow(LearningItemRow r) => LearningItem(
    meta: _m(
      r.id,
      r.householdId,
      r.createdAt,
      r.updatedAt,
      r.deletedAt,
      r.version,
    ),
    goalId: r.goalId,
    kind: r.kind,
    title: r.title,
    purpose: r.purpose,
    status: r.status,
    cost: r.costMinor == null || r.costCurrency == null
        ? null
        : Money(r.costMinor!, r.costCurrency!),
    studyMinutes: r.studyMinutes,
    outcome: r.outcome,
    courseAnswersJson: r.courseAnswersJson,
    courseVerdict: r.courseVerdict,
    completedAt: r.completedAt,
  );

  @override
  Insertable<LearningItemRow> toRow(LearningItem e) =>
      LearningItemsCompanion.insert(
        id: e.meta.id,
        householdId: e.meta.householdId,
        createdAt: e.meta.createdAt,
        updatedAt: e.meta.updatedAt,
        deletedAt: Value(e.meta.deletedAt),
        version: Value(e.meta.version),
        goalId: e.goalId,
        kind: e.kind,
        title: e.title,
        purpose: e.purpose,
        costMinor: Value(e.cost?.minorUnits),
        costCurrency: Value(e.cost?.currency),
        studyMinutes: Value(e.studyMinutes),
        status: e.status,
        outcome: Value(e.outcome),
        courseAnswersJson: Value(e.courseAnswersJson),
        courseVerdict: Value(e.courseVerdict),
        completedAt: Value(e.completedAt),
      );

  @override
  LearningItem withMeta(LearningItem e, SyncMeta meta) =>
      e.copyWith(meta: meta);

  @override
  Future<List<LearningItem>> forGoal(String goalId) async {
    final rows =
        await (db.select(table)
              ..where((t) => t.goalId.equals(goalId) & t.deletedAt.isNull())
              ..orderBy([
                (t) => OrderingTerm.asc(t.createdAt),
                (t) => OrderingTerm.asc(t.id),
              ]))
            .get();
    return rows.map(fromRow).toList();
  }
}

class DriftTeachingEntryRepository
    extends
        DriftSyncedRepository<
          $TeachingEntriesTable,
          TeachingEntryRow,
          TeachingEntry
        >
    implements TeachingEntryRepository {
  DriftTeachingEntryRepository(super.db, super.clock);

  @override
  TableInfo<$TeachingEntriesTable, TeachingEntryRow> get table =>
      db.teachingEntries;

  @override
  String get entityName => 'teaching_entry';

  /// Eng yangi sana birinchi.
  @override
  List<OrderingTerm Function($TeachingEntriesTable)> get defaultOrder => [
    (t) => OrderingTerm.desc(t.taughtOn),
    (t) => OrderingTerm.desc(t.createdAt),
  ];

  @override
  TeachingEntry fromRow(TeachingEntryRow r) => TeachingEntry(
    meta: _m(
      r.id,
      r.householdId,
      r.createdAt,
      r.updatedAt,
      r.deletedAt,
      r.version,
    ),
    learner: r.learner,
    topic: r.topic,
    taughtOn: r.taughtOn,
    minutes: r.minutes,
    note: r.note,
    memberId: r.memberId,
  );

  @override
  Insertable<TeachingEntryRow> toRow(TeachingEntry e) =>
      TeachingEntriesCompanion.insert(
        id: e.meta.id,
        householdId: e.meta.householdId,
        createdAt: e.meta.createdAt,
        updatedAt: e.meta.updatedAt,
        deletedAt: Value(e.meta.deletedAt),
        version: Value(e.meta.version),
        memberId: Value(e.memberId),
        learner: e.learner,
        topic: e.topic,
        taughtOn: e.taughtOn,
        minutes: Value(e.minutes),
        note: Value(e.note),
      );

  @override
  TeachingEntry withMeta(TeachingEntry e, SyncMeta meta) =>
      e.copyWith(meta: meta);
}

@Riverpod(keepAlive: true)
Future<HourlySnapshotRepository> hourlySnapshotRepository(Ref ref) async =>
    DriftHourlySnapshotRepository(
      await ref.watch(appDatabaseProvider.future),
      ref.watch(clockProvider),
    );

@Riverpod(keepAlive: true)
Future<LearningGoalRepository> learningGoalRepository(Ref ref) async =>
    DriftLearningGoalRepository(
      await ref.watch(appDatabaseProvider.future),
      ref.watch(clockProvider),
    );

@Riverpod(keepAlive: true)
Future<LearningItemRepository> learningItemRepository(Ref ref) async =>
    DriftLearningItemRepository(
      await ref.watch(appDatabaseProvider.future),
      ref.watch(clockProvider),
    );

@Riverpod(keepAlive: true)
Future<TeachingEntryRepository> teachingEntryRepository(Ref ref) async =>
    DriftTeachingEntryRepository(
      await ref.watch(appDatabaseProvider.future),
      ref.watch(clockProvider),
    );
