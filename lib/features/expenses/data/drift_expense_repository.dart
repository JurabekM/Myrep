import 'package:baraka_daftari/core/db/app_database.dart';
import 'package:baraka_daftari/core/db/database_provider.dart';
import 'package:baraka_daftari/core/db/synced_repository.dart';
import 'package:baraka_daftari/core/domain/enums.dart';
import 'package:baraka_daftari/core/domain/sync_meta.dart';
import 'package:baraka_daftari/core/money/money.dart';
import 'package:baraka_daftari/core/time/calendar.dart';
import 'package:baraka_daftari/core/time/clock.dart';
import 'package:baraka_daftari/features/expenses/domain/expense.dart';
import 'package:drift/drift.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:riverpod_annotation/riverpod_annotation.dart';

part 'drift_expense_repository.g.dart';

class DriftCategoryRepository
    extends DriftSyncedRepository<$CategoriesTable, CategoryRow, Category>
    implements CategoryRepository {
  DriftCategoryRepository(super.db, super.clock);

  @override
  TableInfo<$CategoriesTable, CategoryRow> get table => db.categories;

  @override
  String get entityName => 'category';

  @override
  List<OrderingTerm Function($CategoriesTable)> get defaultOrder => [
    (t) => OrderingTerm.asc(t.sortOrder),
    (t) => OrderingTerm.asc(t.createdAt),
  ];

  @override
  Category fromRow(CategoryRow r) => Category(
    meta: DriftSyncedRepository.metaOf(
      id: r.id,
      householdId: r.householdId,
      createdAt: r.createdAt,
      updatedAt: r.updatedAt,
      deletedAt: r.deletedAt,
      version: r.version,
    ),
    systemKey: r.systemKey,
    name: r.name,
    defaultNecessity: r.defaultNecessity,
    sortOrder: r.sortOrder,
    isArchived: r.isArchived,
  );

  @override
  Insertable<CategoryRow> toRow(Category e) => CategoriesCompanion.insert(
    id: e.meta.id,
    householdId: e.meta.householdId,
    createdAt: e.meta.createdAt,
    updatedAt: e.meta.updatedAt,
    deletedAt: Value(e.meta.deletedAt),
    version: Value(e.meta.version),
    systemKey: Value(e.systemKey),
    name: Value(e.name),
    defaultNecessity: Value(e.defaultNecessity),
    sortOrder: Value(e.sortOrder),
    isArchived: Value(e.isArchived),
  );

  @override
  Category withMeta(Category e, SyncMeta meta) => e.copyWith(meta: meta);

  @override
  Future<Category?> findBySystemKey(String householdId, CategoryKey key) async {
    final row =
        await (activeQuery(householdId)
              ..where((t) => t.systemKey.equalsValue(key))
              ..limit(1))
            .getSingleOrNull();
    return row == null ? null : fromRow(row);
  }
}

class DriftExpenseRepository
    extends DriftSyncedRepository<$ExpensesTable, ExpenseRow, Expense>
    implements ExpenseRepository {
  DriftExpenseRepository(super.db, super.clock);

  @override
  TableInfo<$ExpensesTable, ExpenseRow> get table => db.expenses;

  @override
  String get entityName => 'expense';

  @override
  Future<void> restore(String id) => restoreDeleted(id);

  @override
  List<OrderingTerm Function($ExpensesTable)> get defaultOrder => [
    (t) => OrderingTerm.desc(t.spentAt),
    (t) => OrderingTerm.desc(t.id),
  ];

  @override
  Expense fromRow(ExpenseRow r) => Expense(
    meta: DriftSyncedRepository.metaOf(
      id: r.id,
      householdId: r.householdId,
      createdAt: r.createdAt,
      updatedAt: r.updatedAt,
      deletedAt: r.deletedAt,
      version: r.version,
    ),
    amount: Money(r.amountMinor, r.currency),
    categoryId: r.categoryId,
    channel: r.channel,
    spentAt: r.spentAt.toUtc(),
    memberId: r.memberId,
    necessity: r.necessity,
    envelopeId: r.envelopeId,
    isGift: r.isGift,
    isOstentation: r.isOstentation,
    fundedByDebt: r.fundedByDebt,
    note: r.note,
    habitId: r.habitId,
  );

  @override
  Insertable<ExpenseRow> toRow(Expense e) => ExpensesCompanion.insert(
    id: e.meta.id,
    householdId: e.meta.householdId,
    createdAt: e.meta.createdAt,
    updatedAt: e.meta.updatedAt,
    deletedAt: Value(e.meta.deletedAt),
    version: Value(e.meta.version),
    amountMinor: e.amount.minorUnits,
    currency: e.amount.currency,
    categoryId: e.categoryId,
    channel: e.channel,
    spentAt: e.spentAt,
    memberId: Value(e.memberId),
    necessity: Value(e.necessity),
    envelopeId: Value(e.envelopeId),
    isGift: Value(e.isGift),
    isOstentation: Value(e.isOstentation),
    fundedByDebt: Value(e.fundedByDebt),
    note: Value(e.note),
    habitId: Value(e.habitId),
  );

  @override
  Expense withMeta(Expense e, SyncMeta meta) => e.copyWith(meta: meta);

  @override
  Future<List<Expense>> listInRange(String householdId, DateRange range) async {
    final rows =
        await (activeQuery(householdId)..where(
              (t) =>
                  t.spentAt.isBiggerOrEqualValue(range.startInstant) &
                  t.spentAt.isSmallerThanValue(range.endInstantExclusive),
            ))
            .get();
    return rows.map(fromRow).toList();
  }

  @override
  Future<Expense?> latest(String householdId) async {
    final row = await (activeQuery(householdId)..limit(1)).getSingleOrNull();
    return row == null ? null : fromRow(row);
  }
}

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

class DriftExpenseTemplateRepository
    extends
        DriftSyncedRepository<
          $ExpenseTemplatesTable,
          ExpenseTemplateRow,
          ExpenseTemplate
        >
    implements ExpenseTemplateRepository {
  DriftExpenseTemplateRepository(super.db, super.clock);

  @override
  TableInfo<$ExpenseTemplatesTable, ExpenseTemplateRow> get table =>
      db.expenseTemplates;

  @override
  String get entityName => 'expense_template';

  @override
  List<OrderingTerm Function($ExpenseTemplatesTable)> get defaultOrder => [
    (t) => OrderingTerm.asc(t.sortOrder),
    (t) => OrderingTerm.asc(t.createdAt),
  ];

  @override
  ExpenseTemplate fromRow(ExpenseTemplateRow r) => ExpenseTemplate(
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
    categoryId: r.categoryId,
    channel: r.channel,
    necessity: r.necessity,
    habitId: r.habitId,
    sortOrder: r.sortOrder,
  );

  @override
  Insertable<ExpenseTemplateRow> toRow(ExpenseTemplate e) =>
      ExpenseTemplatesCompanion.insert(
        id: e.meta.id,
        householdId: e.meta.householdId,
        createdAt: e.meta.createdAt,
        updatedAt: e.meta.updatedAt,
        deletedAt: Value(e.meta.deletedAt),
        version: Value(e.meta.version),
        title: e.title,
        amountMinor: e.amount.minorUnits,
        currency: e.amount.currency,
        categoryId: e.categoryId,
        channel: e.channel,
        necessity: Value(e.necessity),
        habitId: Value(e.habitId),
        sortOrder: Value(e.sortOrder),
      );

  @override
  ExpenseTemplate withMeta(ExpenseTemplate e, SyncMeta meta) =>
      e.copyWith(meta: meta);
}

class DriftNecessityChangeRepository
    extends
        DriftSyncedRepository<
          $NecessityChangesTable,
          NecessityChangeRow,
          NecessityChange
        >
    implements NecessityChangeRepository {
  DriftNecessityChangeRepository(super.db, super.clock);

  @override
  TableInfo<$NecessityChangesTable, NecessityChangeRow> get table =>
      db.necessityChanges;

  @override
  String get entityName => 'necessity_change';

  @override
  NecessityChange fromRow(NecessityChangeRow r) => NecessityChange(
    meta: _meta(
      r.id,
      r.householdId,
      r.createdAt,
      r.updatedAt,
      r.deletedAt,
      r.version,
    ),
    categoryId: r.categoryId,
    from: r.fromNecessity,
    to: r.toNecessity,
    memberId: r.memberId,
  );

  @override
  Insertable<NecessityChangeRow> toRow(NecessityChange e) =>
      NecessityChangesCompanion.insert(
        id: e.meta.id,
        householdId: e.meta.householdId,
        createdAt: e.meta.createdAt,
        updatedAt: e.meta.updatedAt,
        deletedAt: Value(e.meta.deletedAt),
        version: Value(e.meta.version),
        categoryId: e.categoryId,
        fromNecessity: Value(e.from),
        toNecessity: Value(e.to),
        memberId: Value(e.memberId),
      );

  @override
  NecessityChange withMeta(NecessityChange e, SyncMeta meta) =>
      e.copyWith(meta: meta);

  @override
  Future<List<NecessityChange>> forCategory(String categoryId) async {
    final rows =
        await (db.select(table)
              ..where(
                (t) => t.categoryId.equals(categoryId) & t.deletedAt.isNull(),
              )
              ..orderBy(defaultOrder))
            .get();
    return rows.map(fromRow).toList();
  }
}

@Riverpod(keepAlive: true)
Future<ExpenseTemplateRepository> expenseTemplateRepository(Ref ref) async =>
    DriftExpenseTemplateRepository(
      await ref.watch(appDatabaseProvider.future),
      ref.watch(clockProvider),
    );

@Riverpod(keepAlive: true)
Future<NecessityChangeRepository> necessityChangeRepository(Ref ref) async =>
    DriftNecessityChangeRepository(
      await ref.watch(appDatabaseProvider.future),
      ref.watch(clockProvider),
    );

@Riverpod(keepAlive: true)
Future<CategoryRepository> categoryRepository(Ref ref) async =>
    DriftCategoryRepository(
      await ref.watch(appDatabaseProvider.future),
      ref.watch(clockProvider),
    );

@Riverpod(keepAlive: true)
Future<ExpenseRepository> expenseRepository(Ref ref) async =>
    DriftExpenseRepository(
      await ref.watch(appDatabaseProvider.future),
      ref.watch(clockProvider),
    );
