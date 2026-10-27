import 'package:baraka_daftari/core/db/app_database.dart';
import 'package:baraka_daftari/core/db/database_provider.dart';
import 'package:baraka_daftari/core/db/synced_repository.dart';
import 'package:baraka_daftari/core/domain/sync_meta.dart';
import 'package:baraka_daftari/core/money/money.dart';
import 'package:baraka_daftari/core/time/clock.dart';
import 'package:baraka_daftari/features/ceremonies/domain/ceremony.dart';
import 'package:drift/drift.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:riverpod_annotation/riverpod_annotation.dart';

part 'drift_ceremony_repositories.g.dart';

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

class DriftCeremonyPlanRepository
    extends
        DriftSyncedRepository<
          $CeremonyPlansTable,
          CeremonyPlanRow,
          CeremonyPlan
        >
    implements CeremonyPlanRepository {
  DriftCeremonyPlanRepository(super.db, super.clock);

  @override
  TableInfo<$CeremonyPlansTable, CeremonyPlanRow> get table => db.ceremonyPlans;

  @override
  String get entityName => 'ceremony_plan';

  @override
  List<OrderingTerm Function($CeremonyPlansTable)> get defaultOrder => [
    (t) => OrderingTerm.desc(t.createdAt),
  ];

  @override
  CeremonyPlan fromRow(CeremonyPlanRow r) => CeremonyPlan(
    meta: _meta(
      r.id,
      r.householdId,
      r.createdAt,
      r.updatedAt,
      r.deletedAt,
      r.version,
    ),
    title: r.title,
    type: r.type,
    currency: r.currency,
    status: r.status,
    eventDate: r.eventDate,
    selectedScenarioId: r.selectedScenarioId,
    giftGoalId: r.giftGoalId,
    debtMonthly: r.debtMonthlyMinor == null
        ? null
        : Money(r.debtMonthlyMinor!, r.currency),
    debtAnnualRateBp: r.debtAnnualRateBp,
  );

  @override
  Insertable<CeremonyPlanRow> toRow(CeremonyPlan e) =>
      CeremonyPlansCompanion.insert(
        id: e.meta.id,
        householdId: e.meta.householdId,
        createdAt: e.meta.createdAt,
        updatedAt: e.meta.updatedAt,
        deletedAt: Value(e.meta.deletedAt),
        version: Value(e.meta.version),
        title: e.title,
        type: e.type,
        status: e.status,
        currency: e.currency,
        eventDate: Value(e.eventDate),
        selectedScenarioId: Value(e.selectedScenarioId),
        giftGoalId: Value(e.giftGoalId),
        debtMonthlyMinor: Value(e.debtMonthly?.minorUnits),
        debtAnnualRateBp: Value(e.debtAnnualRateBp),
      );

  @override
  CeremonyPlan withMeta(CeremonyPlan e, SyncMeta meta) =>
      e.copyWith(meta: meta);
}

class DriftCeremonyScenarioRepository
    extends
        DriftSyncedRepository<
          $CeremonyScenariosTable,
          CeremonyScenarioRow,
          CeremonyScenario
        >
    implements CeremonyScenarioRepository {
  DriftCeremonyScenarioRepository(super.db, super.clock);

  @override
  TableInfo<$CeremonyScenariosTable, CeremonyScenarioRow> get table =>
      db.ceremonyScenarios;

  @override
  String get entityName => 'ceremony_scenario';

  @override
  CeremonyScenario fromRow(CeremonyScenarioRow r) => CeremonyScenario(
    meta: _meta(
      r.id,
      r.householdId,
      r.createdAt,
      r.updatedAt,
      r.deletedAt,
      r.version,
    ),
    planId: r.planId,
    name: r.name,
    guests: r.guests,
    sortOrder: r.sortOrder,
  );

  @override
  Insertable<CeremonyScenarioRow> toRow(CeremonyScenario e) =>
      CeremonyScenariosCompanion.insert(
        id: e.meta.id,
        householdId: e.meta.householdId,
        createdAt: e.meta.createdAt,
        updatedAt: e.meta.updatedAt,
        deletedAt: Value(e.meta.deletedAt),
        version: Value(e.meta.version),
        planId: e.planId,
        name: e.name,
        guests: Value(e.guests),
        sortOrder: Value(e.sortOrder),
      );

  @override
  CeremonyScenario withMeta(CeremonyScenario e, SyncMeta meta) =>
      e.copyWith(meta: meta);

  @override
  Future<List<CeremonyScenario>> forPlan(String planId) async {
    final rows =
        await (db.select(table)
              ..where((t) => t.planId.equals(planId) & t.deletedAt.isNull())
              ..orderBy([
                (t) => OrderingTerm.asc(t.sortOrder),
                (t) => OrderingTerm.asc(t.createdAt),
              ]))
            .get();
    return rows.map(fromRow).toList();
  }
}

class DriftCeremonyBudgetLineRepository
    extends
        DriftSyncedRepository<
          $CeremonyBudgetLinesTable,
          CeremonyBudgetLineRow,
          CeremonyBudgetLine
        >
    implements CeremonyBudgetLineRepository {
  DriftCeremonyBudgetLineRepository(super.db, super.clock);

  @override
  TableInfo<$CeremonyBudgetLinesTable, CeremonyBudgetLineRow> get table =>
      db.ceremonyBudgetLines;

  @override
  String get entityName => 'ceremony_budget_line';

  @override
  CeremonyBudgetLine fromRow(CeremonyBudgetLineRow r) => CeremonyBudgetLine(
    meta: _meta(
      r.id,
      r.householdId,
      r.createdAt,
      r.updatedAt,
      r.deletedAt,
      r.version,
    ),
    scenarioId: r.scenarioId,
    title: r.title,
    kind: r.kind,
    amount: Money(r.amountMinor, r.currency),
    source: r.source,
    sortOrder: r.sortOrder,
  );

  @override
  Insertable<CeremonyBudgetLineRow> toRow(CeremonyBudgetLine e) =>
      CeremonyBudgetLinesCompanion.insert(
        id: e.meta.id,
        householdId: e.meta.householdId,
        createdAt: e.meta.createdAt,
        updatedAt: e.meta.updatedAt,
        deletedAt: Value(e.meta.deletedAt),
        version: Value(e.meta.version),
        scenarioId: e.scenarioId,
        title: e.title,
        kind: e.kind,
        amountMinor: e.amount.minorUnits,
        currency: e.amount.currency,
        source: e.source,
        sortOrder: Value(e.sortOrder),
      );

  @override
  CeremonyBudgetLine withMeta(CeremonyBudgetLine e, SyncMeta meta) =>
      e.copyWith(meta: meta);

  @override
  Future<List<CeremonyBudgetLine>> forScenario(String scenarioId) async {
    final rows =
        await (db.select(table)
              ..where(
                (t) => t.scenarioId.equals(scenarioId) & t.deletedAt.isNull(),
              )
              ..orderBy([
                (t) => OrderingTerm.asc(t.sortOrder),
                (t) => OrderingTerm.asc(t.createdAt),
              ]))
            .get();
    return rows.map(fromRow).toList();
  }
}

class DriftCeremonyDiscussionMarkRepository
    extends
        DriftSyncedRepository<
          $CeremonyDiscussionMarksTable,
          CeremonyDiscussionMarkRow,
          CeremonyDiscussionMark
        >
    implements CeremonyDiscussionMarkRepository {
  DriftCeremonyDiscussionMarkRepository(super.db, super.clock);

  @override
  TableInfo<$CeremonyDiscussionMarksTable, CeremonyDiscussionMarkRow>
  get table => db.ceremonyDiscussionMarks;

  @override
  String get entityName => 'ceremony_discussion_mark';

  @override
  CeremonyDiscussionMark fromRow(CeremonyDiscussionMarkRow r) =>
      CeremonyDiscussionMark(
        meta: _meta(
          r.id,
          r.householdId,
          r.createdAt,
          r.updatedAt,
          r.deletedAt,
          r.version,
        ),
        planId: r.planId,
        memberId: r.memberId,
      );

  @override
  Insertable<CeremonyDiscussionMarkRow> toRow(CeremonyDiscussionMark e) =>
      CeremonyDiscussionMarksCompanion.insert(
        id: e.meta.id,
        householdId: e.meta.householdId,
        createdAt: e.meta.createdAt,
        updatedAt: e.meta.updatedAt,
        deletedAt: Value(e.meta.deletedAt),
        version: Value(e.meta.version),
        planId: e.planId,
        memberId: e.memberId,
      );

  @override
  CeremonyDiscussionMark withMeta(CeremonyDiscussionMark e, SyncMeta meta) =>
      e.copyWith(meta: meta);

  @override
  Future<List<CeremonyDiscussionMark>> forPlan(String planId) async {
    final rows = await (db.select(
      table,
    )..where((t) => t.planId.equals(planId) & t.deletedAt.isNull())).get();
    return rows.map(fromRow).toList();
  }
}

class DriftGoalContributionRepository
    extends
        DriftSyncedRepository<
          $GoalContributionsTable,
          GoalContributionRow,
          GoalContribution
        >
    implements GoalContributionRepository {
  DriftGoalContributionRepository(super.db, super.clock);

  @override
  TableInfo<$GoalContributionsTable, GoalContributionRow> get table =>
      db.goalContributions;

  @override
  String get entityName => 'goal_contribution';

  @override
  GoalContribution fromRow(GoalContributionRow r) => GoalContribution(
    meta: _meta(
      r.id,
      r.householdId,
      r.createdAt,
      r.updatedAt,
      r.deletedAt,
      r.version,
    ),
    goalId: r.goalId,
    contributorName: r.contributorName,
    amount: Money(r.amountMinor, r.currency),
    receivedOn: r.receivedOn,
  );

  @override
  Insertable<GoalContributionRow> toRow(GoalContribution e) =>
      GoalContributionsCompanion.insert(
        id: e.meta.id,
        householdId: e.meta.householdId,
        createdAt: e.meta.createdAt,
        updatedAt: e.meta.updatedAt,
        deletedAt: Value(e.meta.deletedAt),
        version: Value(e.meta.version),
        goalId: e.goalId,
        contributorName: e.contributorName,
        amountMinor: e.amount.minorUnits,
        currency: e.amount.currency,
        receivedOn: e.receivedOn,
      );

  @override
  GoalContribution withMeta(GoalContribution e, SyncMeta meta) =>
      e.copyWith(meta: meta);

  @override
  Future<List<GoalContribution>> forGoal(String goalId) async {
    final rows =
        await (db.select(table)
              ..where((t) => t.goalId.equals(goalId) & t.deletedAt.isNull())
              ..orderBy([(t) => OrderingTerm.asc(t.receivedOn)]))
            .get();
    return rows.map(fromRow).toList();
  }
}

@Riverpod(keepAlive: true)
Future<CeremonyPlanRepository> ceremonyPlanRepository(Ref ref) async =>
    DriftCeremonyPlanRepository(
      await ref.watch(appDatabaseProvider.future),
      ref.watch(clockProvider),
    );

@Riverpod(keepAlive: true)
Future<CeremonyScenarioRepository> ceremonyScenarioRepository(Ref ref) async =>
    DriftCeremonyScenarioRepository(
      await ref.watch(appDatabaseProvider.future),
      ref.watch(clockProvider),
    );

@Riverpod(keepAlive: true)
Future<CeremonyBudgetLineRepository> ceremonyBudgetLineRepository(
  Ref ref,
) async => DriftCeremonyBudgetLineRepository(
  await ref.watch(appDatabaseProvider.future),
  ref.watch(clockProvider),
);

@Riverpod(keepAlive: true)
Future<CeremonyDiscussionMarkRepository> ceremonyDiscussionMarkRepository(
  Ref ref,
) async => DriftCeremonyDiscussionMarkRepository(
  await ref.watch(appDatabaseProvider.future),
  ref.watch(clockProvider),
);

@Riverpod(keepAlive: true)
Future<GoalContributionRepository> goalContributionRepository(Ref ref) async =>
    DriftGoalContributionRepository(
      await ref.watch(appDatabaseProvider.future),
      ref.watch(clockProvider),
    );
