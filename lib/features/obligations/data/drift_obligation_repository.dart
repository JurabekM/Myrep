import 'package:baraka_daftari/core/db/app_database.dart';
import 'package:baraka_daftari/core/db/database_provider.dart';
import 'package:baraka_daftari/core/db/synced_repository.dart';
import 'package:baraka_daftari/core/domain/enums.dart';
import 'package:baraka_daftari/core/domain/sync_meta.dart';
import 'package:baraka_daftari/core/money/money.dart';
import 'package:baraka_daftari/core/time/clock.dart';
import 'package:baraka_daftari/features/obligations/domain/obligation.dart';
import 'package:drift/drift.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:riverpod_annotation/riverpod_annotation.dart';

part 'drift_obligation_repository.g.dart';

class DriftObligationRepository
    extends DriftSyncedRepository<$ObligationsTable, ObligationRow, Obligation>
    implements ObligationRepository {
  DriftObligationRepository(super.db, super.clock);

  @override
  TableInfo<$ObligationsTable, ObligationRow> get table => db.obligations;

  @override
  String get entityName => 'obligation';

  @override
  List<OrderingTerm Function($ObligationsTable)> get defaultOrder => [
    (t) => OrderingTerm.asc(t.dayOfMonth),
    (t) => OrderingTerm.asc(t.createdAt),
  ];

  @override
  Obligation fromRow(ObligationRow r) => Obligation(
    meta: DriftSyncedRepository.metaOf(
      id: r.id,
      householdId: r.householdId,
      createdAt: r.createdAt,
      updatedAt: r.updatedAt,
      deletedAt: r.deletedAt,
      version: r.version,
    ),
    title: r.title,
    kind: r.kind,
    amount: Money(r.amountMinor, r.currency),
    dayOfMonth: r.dayOfMonth,
    categoryId: r.categoryId,
    debtId: r.debtId,
    isActive: r.isActive,
  );

  @override
  Insertable<ObligationRow> toRow(Obligation e) => ObligationsCompanion.insert(
    id: e.meta.id,
    householdId: e.meta.householdId,
    createdAt: e.meta.createdAt,
    updatedAt: e.meta.updatedAt,
    deletedAt: Value(e.meta.deletedAt),
    version: Value(e.meta.version),
    title: e.title,
    kind: e.kind,
    amountMinor: e.amount.minorUnits,
    currency: e.amount.currency,
    dayOfMonth: e.dayOfMonth,
    categoryId: Value(e.categoryId),
    debtId: Value(e.debtId),
    isActive: Value(e.isActive),
  );

  @override
  Obligation withMeta(Obligation e, SyncMeta meta) => e.copyWith(meta: meta);
}

class DriftDebtRepository
    extends DriftSyncedRepository<$DebtsTable, DebtRow, Debt>
    implements DebtRepository {
  DriftDebtRepository(super.db, super.clock);

  @override
  TableInfo<$DebtsTable, DebtRow> get table => db.debts;

  @override
  String get entityName => 'debt';

  @override
  Debt fromRow(DebtRow r) {
    Money? money(int? minor) => minor == null ? null : Money(minor, r.currency);
    return Debt(
      meta: DriftSyncedRepository.metaOf(
        id: r.id,
        householdId: r.householdId,
        createdAt: r.createdAt,
        updatedAt: r.updatedAt,
        deletedAt: r.deletedAt,
        version: r.version,
      ),
      creditorType: r.creditorType,
      creditorName: r.creditorName,
      principal: Money(r.principalMinor, r.currency),
      remaining: Money(r.remainingMinor, r.currency),
      monthlyPayment: money(r.monthlyPaymentMinor),
      dueDate: r.dueDate,
      reason: r.reason,
      hasMarkup: r.hasMarkup,
      totalPaid: money(r.totalPaidMinor),
      markupAmount: money(r.markupAmountMinor),
      earlyRepaymentTerms: r.earlyRepaymentTerms,
      priority: r.priority,
      note: r.note,
      scheduleType: r.scheduleType,
      termMonths: r.termMonths,
      annualRateBp: r.annualRateBp,
      startDate: r.startDate,
      borrowCheckJson: r.borrowCheck,
      payoffOrder: r.payoffOrder,
      prepayFeeBp: r.prepayFeeBp,
    );
  }

  @override
  Insertable<DebtRow> toRow(Debt e) {
    final currency = e.principal.currency;
    int? minor(Money? m) {
      if (m == null) return null;
      if (m.currency != currency) {
        throw CurrencyMismatchException(currency, m.currency);
      }
      return m.minorUnits;
    }

    return DebtsCompanion.insert(
      id: e.meta.id,
      householdId: e.meta.householdId,
      createdAt: e.meta.createdAt,
      updatedAt: e.meta.updatedAt,
      deletedAt: Value(e.meta.deletedAt),
      version: Value(e.meta.version),
      creditorType: e.creditorType,
      creditorName: e.creditorName,
      currency: currency,
      principalMinor: e.principal.minorUnits,
      remainingMinor: minor(e.remaining)!,
      monthlyPaymentMinor: Value(minor(e.monthlyPayment)),
      dueDate: Value(e.dueDate),
      reason: Value(e.reason),
      hasMarkup: Value(e.hasMarkup),
      totalPaidMinor: Value(minor(e.totalPaid)),
      markupAmountMinor: Value(minor(e.markupAmount)),
      earlyRepaymentTerms: Value(e.earlyRepaymentTerms),
      priority: Value(e.priority),
      note: Value(e.note),
      scheduleType: Value(e.scheduleType),
      termMonths: Value(e.termMonths),
      annualRateBp: Value(e.annualRateBp),
      startDate: Value(e.startDate),
      borrowCheck: Value(e.borrowCheckJson),
      payoffOrder: Value(e.payoffOrder),
      prepayFeeBp: Value(e.prepayFeeBp),
    );
  }

  @override
  Debt withMeta(Debt e, SyncMeta meta) => e.copyWith(meta: meta);

  @override
  Future<List<Debt>> listByCreditorType(
    String householdId,
    CreditorType type,
  ) async {
    final rows = await (activeQuery(
      householdId,
    )..where((t) => t.creditorType.equalsValue(type))).get();
    return rows.map(fromRow).toList();
  }
}

@Riverpod(keepAlive: true)
Future<ObligationRepository> obligationRepository(Ref ref) async =>
    DriftObligationRepository(
      await ref.watch(appDatabaseProvider.future),
      ref.watch(clockProvider),
    );

@Riverpod(keepAlive: true)
Future<DebtRepository> debtRepository(Ref ref) async => DriftDebtRepository(
  await ref.watch(appDatabaseProvider.future),
  ref.watch(clockProvider),
);
