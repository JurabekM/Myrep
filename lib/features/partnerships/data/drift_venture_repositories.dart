import 'package:baraka_daftari/core/db/app_database.dart';
import 'package:baraka_daftari/core/db/database_provider.dart';
import 'package:baraka_daftari/core/db/synced_repository.dart';
import 'package:baraka_daftari/core/domain/sync_meta.dart';
import 'package:baraka_daftari/core/money/money.dart';
import 'package:baraka_daftari/core/time/clock.dart';
import 'package:baraka_daftari/features/partnerships/domain/venture.dart';
import 'package:drift/drift.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:riverpod_annotation/riverpod_annotation.dart';

part 'drift_venture_repositories.g.dart';

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

class DriftVentureEntryRepository
    extends
        DriftSyncedRepository<
          $VentureEntriesTable,
          VentureEntryRow,
          VentureEntry
        >
    implements VentureEntryRepository {
  DriftVentureEntryRepository(super.db, super.clock);

  @override
  TableInfo<$VentureEntriesTable, VentureEntryRow> get table =>
      db.ventureEntries;

  @override
  String get entityName => 'venture_entry';

  @override
  VentureEntry fromRow(VentureEntryRow r) => VentureEntry(
    meta: _m(
      r.id,
      r.householdId,
      r.createdAt,
      r.updatedAt,
      r.deletedAt,
      r.version,
    ),
    partnershipId: r.partnershipId,
    kind: r.kind,
    title: r.title,
    amount: Money(r.amountMinor, r.currency),
    occurredOn: r.occurredOn,
    note: r.note,
    receiptImage: r.receiptImage,
  );

  @override
  Insertable<VentureEntryRow> toRow(VentureEntry e) =>
      VentureEntriesCompanion.insert(
        id: e.meta.id,
        householdId: e.meta.householdId,
        createdAt: e.meta.createdAt,
        updatedAt: e.meta.updatedAt,
        deletedAt: Value(e.meta.deletedAt),
        version: Value(e.meta.version),
        partnershipId: e.partnershipId,
        kind: e.kind,
        title: e.title,
        amountMinor: e.amount.minorUnits,
        currency: e.amount.currency,
        occurredOn: e.occurredOn,
        note: Value(e.note),
        receiptImage: Value(
          e.receiptImage == null ? null : Uint8List.fromList(e.receiptImage!),
        ),
      );

  @override
  VentureEntry withMeta(VentureEntry e, SyncMeta meta) =>
      e.copyWith(meta: meta);

  @override
  Future<List<VentureEntry>> forPartnership(String id) async {
    final rows =
        await (db.select(table)
              ..where((t) => t.partnershipId.equals(id) & t.deletedAt.isNull())
              ..orderBy([
                (t) => OrderingTerm.desc(t.occurredOn),
                (t) => OrderingTerm.desc(t.createdAt),
              ]))
            .get();
    return rows.map(fromRow).toList();
  }
}

class DriftVenturePeriodRepository
    extends
        DriftSyncedRepository<
          $VenturePeriodsTable,
          VenturePeriodRow,
          VenturePeriod
        >
    implements VenturePeriodRepository {
  DriftVenturePeriodRepository(super.db, super.clock);

  @override
  TableInfo<$VenturePeriodsTable, VenturePeriodRow> get table =>
      db.venturePeriods;

  @override
  String get entityName => 'venture_period';

  @override
  VenturePeriod fromRow(VenturePeriodRow r) => VenturePeriod(
    meta: _m(
      r.id,
      r.householdId,
      r.createdAt,
      r.updatedAt,
      r.deletedAt,
      r.version,
    ),
    partnershipId: r.partnershipId,
    startDate: r.startDate,
    endDate: r.endDate,
    income: Money(r.incomeMinor, r.currency),
    expense: Money(r.expenseMinor, r.currency),
    net: Money(r.netMinor, r.currency),
    buyout: Money(r.buyoutMinor, r.currency),
    negligence: r.negligence,
    negligenceNote: r.negligenceNote,
    incomeId: r.incomeId,
  );

  @override
  Insertable<VenturePeriodRow> toRow(VenturePeriod e) =>
      VenturePeriodsCompanion.insert(
        id: e.meta.id,
        householdId: e.meta.householdId,
        createdAt: e.meta.createdAt,
        updatedAt: e.meta.updatedAt,
        deletedAt: Value(e.meta.deletedAt),
        version: Value(e.meta.version),
        partnershipId: e.partnershipId,
        startDate: e.startDate,
        endDate: e.endDate,
        incomeMinor: e.income.minorUnits,
        expenseMinor: e.expense.minorUnits,
        netMinor: e.net.minorUnits,
        buyoutMinor: Value(e.buyout.minorUnits),
        currency: e.net.currency,
        negligence: Value(e.negligence),
        negligenceNote: Value(e.negligenceNote),
        incomeId: Value(e.incomeId),
      );

  @override
  VenturePeriod withMeta(VenturePeriod e, SyncMeta meta) =>
      e.copyWith(meta: meta);

  @override
  Future<List<VenturePeriod>> forPartnership(String id) async {
    final rows =
        await (db.select(table)
              ..where((t) => t.partnershipId.equals(id) & t.deletedAt.isNull())
              ..orderBy([(t) => OrderingTerm.asc(t.endDate)]))
            .get();
    return rows.map(fromRow).toList();
  }
}

class DriftDistributionShareRepository
    extends
        DriftSyncedRepository<
          $DistributionSharesTable,
          DistributionShareRow,
          DistributionShare
        >
    implements DistributionShareRepository {
  DriftDistributionShareRepository(super.db, super.clock);

  @override
  TableInfo<$DistributionSharesTable, DistributionShareRow> get table =>
      db.distributionShares;

  @override
  String get entityName => 'distribution_share';

  @override
  DistributionShare fromRow(DistributionShareRow r) => DistributionShare(
    meta: _m(
      r.id,
      r.householdId,
      r.createdAt,
      r.updatedAt,
      r.deletedAt,
      r.version,
    ),
    periodId: r.periodId,
    partnerId: r.partnerId,
    amount: Money(r.amountMinor, r.currency),
    buyout: Money(r.buyoutMinor, r.currency),
  );

  @override
  Insertable<DistributionShareRow> toRow(DistributionShare e) =>
      DistributionSharesCompanion.insert(
        id: e.meta.id,
        householdId: e.meta.householdId,
        createdAt: e.meta.createdAt,
        updatedAt: e.meta.updatedAt,
        deletedAt: Value(e.meta.deletedAt),
        version: Value(e.meta.version),
        periodId: e.periodId,
        partnerId: e.partnerId,
        amountMinor: e.amount.minorUnits,
        buyoutMinor: Value(e.buyout.minorUnits),
        currency: e.amount.currency,
      );

  @override
  DistributionShare withMeta(DistributionShare e, SyncMeta meta) =>
      e.copyWith(meta: meta);

  @override
  Future<List<DistributionShare>> forPeriod(String periodId) async {
    final rows =
        await (db.select(table)..where(
              (t) => t.periodId.equals(periodId) & t.deletedAt.isNull(),
            ))
            .get();
    return rows.map(fromRow).toList();
  }
}

class DriftSkillRepository
    extends DriftSyncedRepository<$SkillsTable, SkillRow, Skill>
    implements SkillRepository {
  DriftSkillRepository(super.db, super.clock);

  @override
  TableInfo<$SkillsTable, SkillRow> get table => db.skills;

  @override
  String get entityName => 'skill';

  @override
  Skill fromRow(SkillRow r) => Skill(
    meta: _m(
      r.id,
      r.householdId,
      r.createdAt,
      r.updatedAt,
      r.deletedAt,
      r.version,
    ),
    name: r.name,
    memberId: r.memberId,
  );

  @override
  Insertable<SkillRow> toRow(Skill e) => SkillsCompanion.insert(
    id: e.meta.id,
    householdId: e.meta.householdId,
    createdAt: e.meta.createdAt,
    updatedAt: e.meta.updatedAt,
    deletedAt: Value(e.meta.deletedAt),
    version: Value(e.meta.version),
    name: e.name,
    memberId: Value(e.memberId),
  );

  @override
  Skill withMeta(Skill e, SyncMeta meta) => e.copyWith(meta: meta);
}

class DriftVentureIdeaRepository
    extends
        DriftSyncedRepository<$VentureIdeasTable, VentureIdeaRow, VentureIdea>
    implements VentureIdeaRepository {
  DriftVentureIdeaRepository(super.db, super.clock);

  @override
  TableInfo<$VentureIdeasTable, VentureIdeaRow> get table => db.ventureIdeas;

  @override
  String get entityName => 'venture_idea';

  @override
  List<OrderingTerm Function($VentureIdeasTable)> get defaultOrder => [
    (t) => OrderingTerm.desc(t.createdAt),
  ];

  @override
  VentureIdea fromRow(VentureIdeaRow r) => VentureIdea(
    meta: _m(
      r.id,
      r.householdId,
      r.createdAt,
      r.updatedAt,
      r.deletedAt,
      r.version,
    ),
    title: r.title,
    pessimisticIncome: Money(r.pessimisticIncomeMinor, r.currency),
    baseIncome: Money(r.baseIncomeMinor, r.currency),
    optimisticIncome: Money(r.optimisticIncomeMinor, r.currency),
    monthlyExpense: Money(r.monthlyExpenseMinor, r.currency),
    myShareBp: r.myShareBp,
    skillId: r.skillId,
  );

  @override
  Insertable<VentureIdeaRow> toRow(VentureIdea e) =>
      VentureIdeasCompanion.insert(
        id: e.meta.id,
        householdId: e.meta.householdId,
        createdAt: e.meta.createdAt,
        updatedAt: e.meta.updatedAt,
        deletedAt: Value(e.meta.deletedAt),
        version: Value(e.meta.version),
        title: e.title,
        pessimisticIncomeMinor: e.pessimisticIncome.minorUnits,
        baseIncomeMinor: e.baseIncome.minorUnits,
        optimisticIncomeMinor: e.optimisticIncome.minorUnits,
        monthlyExpenseMinor: e.monthlyExpense.minorUnits,
        myShareBp: Value(e.myShareBp),
        currency: e.baseIncome.currency,
        skillId: Value(e.skillId),
      );

  @override
  VentureIdea withMeta(VentureIdea e, SyncMeta meta) => e.copyWith(meta: meta);
}

class DriftIdeaCapexItemRepository
    extends
        DriftSyncedRepository<
          $IdeaCapexItemsTable,
          IdeaCapexItemRow,
          IdeaCapexItem
        >
    implements IdeaCapexItemRepository {
  DriftIdeaCapexItemRepository(super.db, super.clock);

  @override
  TableInfo<$IdeaCapexItemsTable, IdeaCapexItemRow> get table =>
      db.ideaCapexItems;

  @override
  String get entityName => 'idea_capex_item';

  @override
  IdeaCapexItem fromRow(IdeaCapexItemRow r) => IdeaCapexItem(
    meta: _m(
      r.id,
      r.householdId,
      r.createdAt,
      r.updatedAt,
      r.deletedAt,
      r.version,
    ),
    ideaId: r.ideaId,
    title: r.title,
    amount: Money(r.amountMinor, r.currency),
  );

  @override
  Insertable<IdeaCapexItemRow> toRow(IdeaCapexItem e) =>
      IdeaCapexItemsCompanion.insert(
        id: e.meta.id,
        householdId: e.meta.householdId,
        createdAt: e.meta.createdAt,
        updatedAt: e.meta.updatedAt,
        deletedAt: Value(e.meta.deletedAt),
        version: Value(e.meta.version),
        ideaId: e.ideaId,
        title: e.title,
        amountMinor: e.amount.minorUnits,
        currency: e.amount.currency,
      );

  @override
  IdeaCapexItem withMeta(IdeaCapexItem e, SyncMeta meta) =>
      e.copyWith(meta: meta);

  @override
  Future<List<IdeaCapexItem>> forIdea(String ideaId) async {
    final rows =
        await (db.select(table)
              ..where((t) => t.ideaId.equals(ideaId) & t.deletedAt.isNull())
              ..orderBy([(t) => OrderingTerm.asc(t.createdAt)]))
            .get();
    return rows.map(fromRow).toList();
  }
}

class DriftOfferCheckRepository
    extends
        DriftSyncedRepository<
          $OfferChecksTable,
          OfferCheckRow,
          OfferCheckRecord
        >
    implements OfferCheckRepository {
  DriftOfferCheckRepository(super.db, super.clock);

  @override
  TableInfo<$OfferChecksTable, OfferCheckRow> get table => db.offerChecks;

  @override
  String get entityName => 'offer_check';

  @override
  List<OrderingTerm Function($OfferChecksTable)> get defaultOrder => [
    (t) => OrderingTerm.desc(t.createdAt),
  ];

  @override
  OfferCheckRecord fromRow(OfferCheckRow r) => OfferCheckRecord(
    meta: _m(
      r.id,
      r.householdId,
      r.createdAt,
      r.updatedAt,
      r.deletedAt,
      r.version,
    ),
    title: r.title,
    answersJson: r.answersJson,
    verdict: r.verdict,
    amount: r.amountMinor == null || r.currency == null
        ? null
        : Money(r.amountMinor!, r.currency!),
    promisedMonthlyBp: r.promisedMonthlyBp,
    advisor: r.advisor,
    decision: r.decision,
    decidedAt: r.decidedAt,
  );

  @override
  Insertable<OfferCheckRow> toRow(OfferCheckRecord e) =>
      OfferChecksCompanion.insert(
        id: e.meta.id,
        householdId: e.meta.householdId,
        createdAt: e.meta.createdAt,
        updatedAt: e.meta.updatedAt,
        deletedAt: Value(e.meta.deletedAt),
        version: Value(e.meta.version),
        title: e.title,
        answersJson: e.answersJson,
        verdict: e.verdict,
        amountMinor: Value(e.amount?.minorUnits),
        currency: Value(e.amount?.currency),
        promisedMonthlyBp: Value(e.promisedMonthlyBp),
        advisor: Value(e.advisor),
        decision: Value(e.decision),
        decidedAt: Value(e.decidedAt),
      );

  @override
  OfferCheckRecord withMeta(OfferCheckRecord e, SyncMeta meta) =>
      e.copyWith(meta: meta);
}

@Riverpod(keepAlive: true)
Future<VentureEntryRepository> ventureEntryRepository(Ref ref) async =>
    DriftVentureEntryRepository(
      await ref.watch(appDatabaseProvider.future),
      ref.watch(clockProvider),
    );

@Riverpod(keepAlive: true)
Future<VenturePeriodRepository> venturePeriodRepository(Ref ref) async =>
    DriftVenturePeriodRepository(
      await ref.watch(appDatabaseProvider.future),
      ref.watch(clockProvider),
    );

@Riverpod(keepAlive: true)
Future<DistributionShareRepository> distributionShareRepository(
  Ref ref,
) async => DriftDistributionShareRepository(
  await ref.watch(appDatabaseProvider.future),
  ref.watch(clockProvider),
);

@Riverpod(keepAlive: true)
Future<SkillRepository> skillRepository(Ref ref) async => DriftSkillRepository(
  await ref.watch(appDatabaseProvider.future),
  ref.watch(clockProvider),
);

@Riverpod(keepAlive: true)
Future<VentureIdeaRepository> ventureIdeaRepository(Ref ref) async =>
    DriftVentureIdeaRepository(
      await ref.watch(appDatabaseProvider.future),
      ref.watch(clockProvider),
    );

@Riverpod(keepAlive: true)
Future<IdeaCapexItemRepository> ideaCapexItemRepository(Ref ref) async =>
    DriftIdeaCapexItemRepository(
      await ref.watch(appDatabaseProvider.future),
      ref.watch(clockProvider),
    );

@Riverpod(keepAlive: true)
Future<OfferCheckRepository> offerCheckRepository(Ref ref) async =>
    DriftOfferCheckRepository(
      await ref.watch(appDatabaseProvider.future),
      ref.watch(clockProvider),
    );
