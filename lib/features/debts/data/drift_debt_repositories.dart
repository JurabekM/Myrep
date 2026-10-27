import 'package:baraka_daftari/core/db/app_database.dart';
import 'package:baraka_daftari/core/db/database_provider.dart';
import 'package:baraka_daftari/core/db/synced_repository.dart';
import 'package:baraka_daftari/core/domain/sync_meta.dart';
import 'package:baraka_daftari/core/money/money.dart';
import 'package:baraka_daftari/core/time/clock.dart';
import 'package:baraka_daftari/features/debts/domain/debts.dart';
import 'package:drift/drift.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:riverpod_annotation/riverpod_annotation.dart';

part 'drift_debt_repositories.g.dart';

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

class DriftDebtInstallmentRepository
    extends
        DriftSyncedRepository<
          $DebtInstallmentsTable,
          DebtInstallmentRow,
          DebtInstallment
        >
    implements DebtInstallmentRepository {
  DriftDebtInstallmentRepository(super.db, super.clock);

  @override
  TableInfo<$DebtInstallmentsTable, DebtInstallmentRow> get table =>
      db.debtInstallments;

  @override
  String get entityName => 'debt_installment';

  @override
  DebtInstallment fromRow(DebtInstallmentRow r) => DebtInstallment(
    meta: _meta(
      r.id,
      r.householdId,
      r.createdAt,
      r.updatedAt,
      r.deletedAt,
      r.version,
    ),
    debtId: r.debtId,
    dueOn: r.dueOn,
    amount: Money(r.amountMinor, r.currency),
    interest: Money(r.interestMinor, r.currency),
  );

  @override
  Insertable<DebtInstallmentRow> toRow(DebtInstallment e) =>
      DebtInstallmentsCompanion.insert(
        id: e.meta.id,
        householdId: e.meta.householdId,
        createdAt: e.meta.createdAt,
        updatedAt: e.meta.updatedAt,
        deletedAt: Value(e.meta.deletedAt),
        version: Value(e.meta.version),
        debtId: e.debtId,
        dueOn: e.dueOn,
        amountMinor: e.amount.minorUnits,
        interestMinor: Value(e.interest.minorUnits),
        currency: e.amount.currency,
      );

  @override
  DebtInstallment withMeta(DebtInstallment e, SyncMeta meta) =>
      e.copyWith(meta: meta);

  @override
  Future<List<DebtInstallment>> forDebt(String debtId) async {
    final rows =
        await (db.select(table)
              ..where((t) => t.debtId.equals(debtId) & t.deletedAt.isNull())
              ..orderBy([(t) => OrderingTerm.asc(t.dueOn)]))
            .get();
    return rows.map(fromRow).toList();
  }
}

class DriftDebtPaymentRepository
    extends
        DriftSyncedRepository<$DebtPaymentsTable, DebtPaymentRow, DebtPayment>
    implements DebtPaymentRepository {
  DriftDebtPaymentRepository(super.db, super.clock);

  @override
  TableInfo<$DebtPaymentsTable, DebtPaymentRow> get table => db.debtPayments;

  @override
  String get entityName => 'debt_payment';

  @override
  DebtPayment fromRow(DebtPaymentRow r) => DebtPayment(
    meta: _meta(
      r.id,
      r.householdId,
      r.createdAt,
      r.updatedAt,
      r.deletedAt,
      r.version,
    ),
    debtId: r.debtId,
    amount: Money(r.amountMinor, r.currency),
    paidOn: r.paidOn,
    isPrepayment: r.isPrepayment,
    note: r.note,
    fee: r.feeMinor == 0 ? null : Money(r.feeMinor, r.currency),
    contributorId: r.contributorId,
  );

  @override
  Insertable<DebtPaymentRow> toRow(DebtPayment e) =>
      DebtPaymentsCompanion.insert(
        id: e.meta.id,
        householdId: e.meta.householdId,
        createdAt: e.meta.createdAt,
        updatedAt: e.meta.updatedAt,
        deletedAt: Value(e.meta.deletedAt),
        version: Value(e.meta.version),
        debtId: e.debtId,
        amountMinor: e.amount.minorUnits,
        currency: e.amount.currency,
        paidOn: e.paidOn,
        isPrepayment: Value(e.isPrepayment),
        note: Value(e.note),
        feeMinor: Value(e.fee?.minorUnits ?? 0),
        contributorId: Value(e.contributorId),
      );

  @override
  DebtPayment withMeta(DebtPayment e, SyncMeta meta) => e.copyWith(meta: meta);

  @override
  Future<List<DebtPayment>> forDebt(String debtId) async {
    final rows =
        await (db.select(table)
              ..where((t) => t.debtId.equals(debtId) & t.deletedAt.isNull())
              ..orderBy([(t) => OrderingTerm.desc(t.paidOn)]))
            .get();
    return rows.map(fromRow).toList();
  }
}

class DriftReceivableRepository
    extends DriftSyncedRepository<$ReceivablesTable, ReceivableRow, Receivable>
    implements ReceivableRepository {
  DriftReceivableRepository(super.db, super.clock);

  @override
  TableInfo<$ReceivablesTable, ReceivableRow> get table => db.receivables;

  @override
  String get entityName => 'receivable';

  @override
  List<OrderingTerm Function($ReceivablesTable)> get defaultOrder => [
    (t) => OrderingTerm.asc(t.dueDate),
  ];

  @override
  Receivable fromRow(ReceivableRow r) => Receivable(
    meta: _meta(
      r.id,
      r.householdId,
      r.createdAt,
      r.updatedAt,
      r.deletedAt,
      r.version,
    ),
    debtorName: r.debtorName,
    principal: Money(r.principalMinor, r.currency),
    remaining: Money(r.remainingMinor, r.currency),
    dueDate: r.dueDate,
    reason: r.reason,
    note: r.note,
  );

  @override
  Insertable<ReceivableRow> toRow(Receivable e) => ReceivablesCompanion.insert(
    id: e.meta.id,
    householdId: e.meta.householdId,
    createdAt: e.meta.createdAt,
    updatedAt: e.meta.updatedAt,
    deletedAt: Value(e.meta.deletedAt),
    version: Value(e.meta.version),
    debtorName: e.debtorName,
    principalMinor: e.principal.minorUnits,
    remainingMinor: e.remaining.minorUnits,
    currency: e.principal.currency,
    dueDate: e.dueDate,
    reason: Value(e.reason),
    note: Value(e.note),
  );

  @override
  Receivable withMeta(Receivable e, SyncMeta meta) => e.copyWith(meta: meta);
}

class DriftGoalRepository
    extends DriftSyncedRepository<$GoalsTable, GoalRow, Goal>
    implements GoalRepository {
  DriftGoalRepository(super.db, super.clock);

  @override
  TableInfo<$GoalsTable, GoalRow> get table => db.goals;

  @override
  String get entityName => 'goal';

  @override
  List<OrderingTerm Function($GoalsTable)> get defaultOrder => [
    (t) => OrderingTerm.asc(t.createdAt),
  ];

  @override
  Goal fromRow(GoalRow r) => Goal(
    meta: _meta(
      r.id,
      r.householdId,
      r.createdAt,
      r.updatedAt,
      r.deletedAt,
      r.version,
    ),
    title: r.title,
    target: Money(r.targetMinor, r.currency),
    targetDate: r.targetDate,
  );

  @override
  Insertable<GoalRow> toRow(Goal e) => GoalsCompanion.insert(
    id: e.meta.id,
    householdId: e.meta.householdId,
    createdAt: e.meta.createdAt,
    updatedAt: e.meta.updatedAt,
    deletedAt: Value(e.meta.deletedAt),
    version: Value(e.meta.version),
    title: e.title,
    targetMinor: e.target.minorUnits,
    currency: e.target.currency,
    targetDate: Value(e.targetDate),
  );

  @override
  Goal withMeta(Goal e, SyncMeta meta) => e.copyWith(meta: meta);
}

class DriftLoanSignerRepository
    extends DriftSyncedRepository<$LoanSignersTable, LoanSignerRow, LoanSigner>
    implements LoanSignerRepository {
  DriftLoanSignerRepository(super.db, super.clock);

  @override
  TableInfo<$LoanSignersTable, LoanSignerRow> get table => db.loanSigners;

  @override
  String get entityName => 'loan_signer';

  @override
  List<OrderingTerm Function($LoanSignersTable)> get defaultOrder => [
    (t) => OrderingTerm.asc(t.createdAt),
  ];

  @override
  LoanSigner fromRow(LoanSignerRow r) => LoanSigner(
    meta: _meta(
      r.id,
      r.householdId,
      r.createdAt,
      r.updatedAt,
      r.deletedAt,
      r.version,
    ),
    documentId: r.documentId,
    role: r.role,
    name: r.name,
    signaturePng: r.signaturePng,
    signedAt: r.signedAt?.toUtc(),
  );

  @override
  Insertable<LoanSignerRow> toRow(LoanSigner e) => LoanSignersCompanion.insert(
    id: e.meta.id,
    householdId: e.meta.householdId,
    createdAt: e.meta.createdAt,
    updatedAt: e.meta.updatedAt,
    deletedAt: Value(e.meta.deletedAt),
    version: Value(e.meta.version),
    documentId: e.documentId,
    role: e.role,
    name: e.name,
    signaturePng: Value(
      e.signaturePng == null ? null : Uint8List.fromList(e.signaturePng!),
    ),
    signedAt: Value(e.signedAt),
  );

  @override
  LoanSigner withMeta(LoanSigner e, SyncMeta meta) => e.copyWith(meta: meta);

  @override
  Future<List<LoanSigner>> forDocument(String documentId) async {
    final rows =
        await (db.select(table)
              ..where(
                (t) => t.documentId.equals(documentId) & t.deletedAt.isNull(),
              )
              ..orderBy(defaultOrder))
            .get();
    return rows.map(fromRow).toList();
  }
}

class DriftDebtContributorRepository
    extends
        DriftSyncedRepository<
          $DebtContributorsTable,
          DebtContributorRow,
          DebtContributor
        >
    implements DebtContributorRepository {
  DriftDebtContributorRepository(super.db, super.clock);

  @override
  TableInfo<$DebtContributorsTable, DebtContributorRow> get table =>
      db.debtContributors;

  @override
  String get entityName => 'debt_contributor';

  @override
  DebtContributor fromRow(DebtContributorRow r) => DebtContributor(
    meta: _meta(
      r.id,
      r.householdId,
      r.createdAt,
      r.updatedAt,
      r.deletedAt,
      r.version,
    ),
    debtId: r.debtId,
    name: r.name,
    memberId: r.memberId,
    monthlyShare: r.monthlyShareMinor == null
        ? null
        : Money(r.monthlyShareMinor!, r.currency),
  );

  @override
  Insertable<DebtContributorRow> toRow(DebtContributor e) =>
      DebtContributorsCompanion.insert(
        id: e.meta.id,
        householdId: e.meta.householdId,
        createdAt: e.meta.createdAt,
        updatedAt: e.meta.updatedAt,
        deletedAt: Value(e.meta.deletedAt),
        version: Value(e.meta.version),
        debtId: e.debtId,
        name: e.name,
        memberId: Value(e.memberId),
        monthlyShareMinor: Value(e.monthlyShare?.minorUnits),
        // Ulushsiz yozuvda valyuta ahamiyatsiz — qarz valyutasi so'm.
        currency: e.monthlyShare?.currency ?? CurrencyCode.uzs,
      );

  @override
  DebtContributor withMeta(DebtContributor e, SyncMeta meta) =>
      e.copyWith(meta: meta);

  @override
  Future<List<DebtContributor>> forDebt(String debtId) async {
    final rows =
        await (db.select(table)
              ..where((t) => t.debtId.equals(debtId) & t.deletedAt.isNull())
              ..orderBy([(t) => OrderingTerm.asc(t.createdAt)]))
            .get();
    return rows.map(fromRow).toList();
  }
}

class DriftSellableItemRepository
    extends
        DriftSyncedRepository<
          $SellableItemsTable,
          SellableItemRow,
          SellableItem
        >
    implements SellableItemRepository {
  DriftSellableItemRepository(super.db, super.clock);

  @override
  TableInfo<$SellableItemsTable, SellableItemRow> get table => db.sellableItems;

  @override
  String get entityName => 'sellable_item';

  @override
  List<OrderingTerm Function($SellableItemsTable)> get defaultOrder => [
    (t) => OrderingTerm.asc(t.createdAt),
  ];

  @override
  SellableItem fromRow(SellableItemRow r) => SellableItem(
    meta: _meta(
      r.id,
      r.householdId,
      r.createdAt,
      r.updatedAt,
      r.deletedAt,
      r.version,
    ),
    name: r.name,
    estimated: Money(r.estimatedMinor, r.currency),
    status: r.status,
    soldFor: r.soldMinor == null ? null : Money(r.soldMinor!, r.currency),
    soldOn: r.soldOn,
    debtId: r.debtId,
    paymentId: r.paymentId,
  );

  @override
  Insertable<SellableItemRow> toRow(SellableItem e) =>
      SellableItemsCompanion.insert(
        id: e.meta.id,
        householdId: e.meta.householdId,
        createdAt: e.meta.createdAt,
        updatedAt: e.meta.updatedAt,
        deletedAt: Value(e.meta.deletedAt),
        version: Value(e.meta.version),
        name: e.name,
        estimatedMinor: e.estimated.minorUnits,
        currency: e.estimated.currency,
        status: e.status,
        soldMinor: Value(e.soldFor?.minorUnits),
        soldOn: Value(e.soldOn),
        debtId: Value(e.debtId),
        paymentId: Value(e.paymentId),
      );

  @override
  SellableItem withMeta(SellableItem e, SyncMeta meta) =>
      e.copyWith(meta: meta);
}

@Riverpod(keepAlive: true)
Future<DebtContributorRepository> debtContributorRepository(Ref ref) async =>
    DriftDebtContributorRepository(
      await ref.watch(appDatabaseProvider.future),
      ref.watch(clockProvider),
    );

@Riverpod(keepAlive: true)
Future<SellableItemRepository> sellableItemRepository(Ref ref) async =>
    DriftSellableItemRepository(
      await ref.watch(appDatabaseProvider.future),
      ref.watch(clockProvider),
    );

@Riverpod(keepAlive: true)
Future<DebtInstallmentRepository> debtInstallmentRepository(Ref ref) async =>
    DriftDebtInstallmentRepository(
      await ref.watch(appDatabaseProvider.future),
      ref.watch(clockProvider),
    );

@Riverpod(keepAlive: true)
Future<DebtPaymentRepository> debtPaymentRepository(Ref ref) async =>
    DriftDebtPaymentRepository(
      await ref.watch(appDatabaseProvider.future),
      ref.watch(clockProvider),
    );

@Riverpod(keepAlive: true)
Future<ReceivableRepository> receivableRepository(Ref ref) async =>
    DriftReceivableRepository(
      await ref.watch(appDatabaseProvider.future),
      ref.watch(clockProvider),
    );

@Riverpod(keepAlive: true)
Future<GoalRepository> goalRepository(Ref ref) async => DriftGoalRepository(
  await ref.watch(appDatabaseProvider.future),
  ref.watch(clockProvider),
);

@Riverpod(keepAlive: true)
Future<LoanSignerRepository> loanSignerRepository(Ref ref) async =>
    DriftLoanSignerRepository(
      await ref.watch(appDatabaseProvider.future),
      ref.watch(clockProvider),
    );
