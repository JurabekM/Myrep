import 'package:baraka_daftari/core/db/app_database.dart';
import 'package:baraka_daftari/core/db/database_provider.dart';
import 'package:baraka_daftari/core/db/synced_repository.dart';
import 'package:baraka_daftari/core/domain/enums.dart';
import 'package:baraka_daftari/core/domain/sync_meta.dart';
import 'package:baraka_daftari/core/errors/data_exceptions.dart';
import 'package:baraka_daftari/core/money/money.dart';
import 'package:baraka_daftari/core/time/clock.dart';
import 'package:baraka_daftari/features/vault/domain/vault.dart';
import 'package:drift/drift.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:riverpod_annotation/riverpod_annotation.dart';

part 'drift_vault_repository.g.dart';

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

class DriftAssetRepository
    extends DriftSyncedRepository<$AssetsTable, AssetRow, Asset>
    implements AssetRepository {
  DriftAssetRepository(super.db, super.clock);

  @override
  TableInfo<$AssetsTable, AssetRow> get table => db.assets;

  @override
  String get entityName => 'asset';

  @override
  Asset fromRow(AssetRow r) => Asset(
    meta: _meta(
      r.id,
      r.householdId,
      r.createdAt,
      r.updatedAt,
      r.deletedAt,
      r.version,
    ),
    type: r.type,
    unit: r.unit,
    acquiredAt: r.acquiredAt.toUtc(),
    quantity: r.quantity,
    currency: r.currency,
    name: r.name,
    vaultType: r.vaultType,
  );

  @override
  Insertable<AssetRow> toRow(Asset e) => AssetsCompanion.insert(
    id: e.meta.id,
    householdId: e.meta.householdId,
    createdAt: e.meta.createdAt,
    updatedAt: e.meta.updatedAt,
    deletedAt: Value(e.meta.deletedAt),
    version: Value(e.meta.version),
    type: e.type,
    unit: e.unit,
    acquiredAt: e.acquiredAt,
    quantity: Value(e.quantity),
    currency: Value(e.currency),
    name: Value(e.name),
    vaultType: Value(e.vaultType),
  );

  @override
  Asset withMeta(Asset e, SyncMeta meta) => e.copyWith(meta: meta);

  @override
  Future<List<Asset>> listVaults(String householdId) async {
    final rows =
        await (db.select(db.assets)..where(
              (t) =>
                  t.householdId.equals(householdId) &
                  t.deletedAt.isNull() &
                  t.type.equalsValue(AssetType.vault),
            ))
            .get();
    return rows.map(fromRow).toList();
  }

  @override
  Future<Asset?> findVault(String householdId, VaultType type) async {
    final row =
        await (db.select(db.assets)
              ..where(
                (t) =>
                    t.householdId.equals(householdId) &
                    t.deletedAt.isNull() &
                    t.type.equalsValue(AssetType.vault) &
                    (type == VaultType.qorovul
                        ? (t.vaultType.equalsValue(type) | t.vaultType.isNull())
                        : t.vaultType.equalsValue(type)),
              )
              ..orderBy([(t) => OrderingTerm.asc(t.createdAt)])
              ..limit(1))
            .getSingleOrNull();
    return row == null ? null : fromRow(row);
  }

  @override
  Future<Asset?> findFirstOfType(String householdId, AssetType type) async {
    final row =
        await (db.select(db.assets)
              ..where(
                (t) =>
                    t.householdId.equals(householdId) &
                    t.deletedAt.isNull() &
                    t.type.equalsValue(type),
              )
              ..orderBy([(t) => OrderingTerm.asc(t.createdAt)])
              ..limit(1))
            .getSingleOrNull();
    return row == null ? null : fromRow(row);
  }

  @override
  Future<AssetSnapshot> addSnapshot(AssetSnapshot s) async {
    await db
        .into(db.assetSnapshots)
        .insert(
          AssetSnapshotsCompanion.insert(
            id: s.meta.id,
            householdId: s.meta.householdId,
            createdAt: s.meta.createdAt,
            updatedAt: s.meta.updatedAt,
            assetId: s.assetId,
            quantity: s.quantity,
            takenAt: s.takenAt,
          ),
        );
    return s;
  }

  @override
  Future<List<AssetSnapshot>> listSnapshots(String assetId) async {
    final rows =
        await (db.select(db.assetSnapshots)
              ..where((t) => t.assetId.equals(assetId) & t.deletedAt.isNull())
              ..orderBy([(t) => OrderingTerm.asc(t.takenAt)]))
            .get();
    return [
      for (final r in rows)
        AssetSnapshot(
          meta: _meta(
            r.id,
            r.householdId,
            r.createdAt,
            r.updatedAt,
            r.deletedAt,
            r.version,
          ),
          assetId: r.assetId,
          quantity: r.quantity,
          takenAt: r.takenAt.toUtc(),
        ),
    ];
  }
}

class DriftVaultTransactionRepository
    extends
        DriftSyncedRepository<
          $VaultTransactionsTable,
          VaultTransactionRow,
          VaultTransaction
        >
    implements VaultTransactionRepository {
  DriftVaultTransactionRepository(super.db, super.clock);

  /// Pul olishda sabab ko'rsatilmagan.
  static const withdrawReasonRequired = 'vault_withdraw_reason_required';

  /// Summa musbat bo'lishi shart (yo'nalish `type` da).
  static const amountMustBePositive = 'vault_amount_must_be_positive';

  @override
  TableInfo<$VaultTransactionsTable, VaultTransactionRow> get table =>
      db.vaultTransactions;

  @override
  String get entityName => 'vault_transaction';

  @override
  List<OrderingTerm Function($VaultTransactionsTable)> get defaultOrder => [
    (t) => OrderingTerm.desc(t.occurredAt),
    (t) => OrderingTerm.desc(t.id),
  ];

  @override
  VaultTransaction fromRow(VaultTransactionRow r) => VaultTransaction(
    meta: _meta(
      r.id,
      r.householdId,
      r.createdAt,
      r.updatedAt,
      r.deletedAt,
      r.version,
    ),
    vaultAssetId: r.vaultAssetId,
    type: r.type,
    amount: Money(r.amountMinor, r.currency),
    reason: r.reason,
    occurredAt: r.occurredAt.toUtc(),
    reasonNote: r.reasonNote,
    incomeId: r.incomeId,
    memberId: r.memberId,
  );

  @override
  Insertable<VaultTransactionRow> toRow(VaultTransaction e) =>
      VaultTransactionsCompanion.insert(
        id: e.meta.id,
        householdId: e.meta.householdId,
        createdAt: e.meta.createdAt,
        updatedAt: e.meta.updatedAt,
        deletedAt: Value(e.meta.deletedAt),
        version: Value(e.meta.version),
        vaultAssetId: e.vaultAssetId,
        type: e.type,
        amountMinor: e.amount.minorUnits,
        currency: e.amount.currency,
        reason: e.reason,
        occurredAt: e.occurredAt,
        reasonNote: Value(e.reasonNote),
        incomeId: Value(e.incomeId),
        memberId: Value(e.memberId),
      );

  @override
  VaultTransaction withMeta(VaultTransaction e, SyncMeta meta) =>
      e.copyWith(meta: meta);

  void _validate(VaultTransaction e) {
    if (!e.amount.isPositive) {
      throw const DomainRuleException(amountMustBePositive);
    }
    if (e.type == VaultTransactionType.withdraw &&
        (e.reasonNote == null || e.reasonNote!.trim().isEmpty)) {
      throw const DomainRuleException(withdrawReasonRequired);
    }
  }

  @override
  Future<VaultTransaction> add(VaultTransaction entity) {
    _validate(entity);
    return super.add(entity);
  }

  @override
  Future<VaultTransaction> update(VaultTransaction entity) {
    _validate(entity);
    return super.update(entity);
  }

  @override
  Future<Money> balance(String vaultAssetId, CurrencyCode currency) async {
    final rows = await db
        .customSelect(
          'SELECT COALESCE(SUM(CASE WHEN type = ? THEN amount_minor '
          'ELSE -amount_minor END), 0) AS total '
          'FROM vault_transactions '
          'WHERE vault_asset_id = ? AND currency = ? AND deleted_at IS NULL',
          variables: [
            Variable<String>(VaultTransactionType.deposit.name),
            Variable<String>(vaultAssetId),
            Variable<String>(currency.name),
          ],
          readsFrom: {db.vaultTransactions},
        )
        .getSingle();
    return Money(rows.read<int>('total'), currency);
  }

  @override
  Future<List<VaultTransaction>> listForVault(String vaultAssetId) async {
    final rows =
        await (db.select(db.vaultTransactions)
              ..where(
                (t) =>
                    t.vaultAssetId.equals(vaultAssetId) & t.deletedAt.isNull(),
              )
              ..orderBy(defaultOrder))
            .get();
    return rows.map(fromRow).toList();
  }
}

class DriftAllocationRuleRepository
    extends
        DriftSyncedRepository<
          $AllocationRulesTable,
          AllocationRuleRow,
          AllocationRule
        >
    implements AllocationRuleRepository {
  DriftAllocationRuleRepository(super.db, super.clock);

  @override
  TableInfo<$AllocationRulesTable, AllocationRuleRow> get table =>
      db.allocationRules;

  @override
  String get entityName => 'allocation_rule';

  @override
  AllocationRule fromRow(AllocationRuleRow r) => AllocationRule(
    meta: _meta(
      r.id,
      r.householdId,
      r.createdAt,
      r.updatedAt,
      r.deletedAt,
      r.version,
    ),
    vaultAssetId: r.vaultAssetId,
    mode: r.mode,
    currency: r.currency,
    basisPoints: r.basisPoints,
    fixedAmount: r.fixedAmountMinor == null
        ? null
        : Money(r.fixedAmountMinor!, r.currency),
    isActive: r.isActive,
    progressionOfferedAt: r.progressionOfferedAt?.toUtc(),
  );

  @override
  Insertable<AllocationRuleRow> toRow(AllocationRule e) {
    final fixed = e.fixedAmount;
    if (fixed != null && fixed.currency != e.currency) {
      throw CurrencyMismatchException(e.currency, fixed.currency);
    }
    return AllocationRulesCompanion.insert(
      id: e.meta.id,
      householdId: e.meta.householdId,
      createdAt: e.meta.createdAt,
      updatedAt: e.meta.updatedAt,
      deletedAt: Value(e.meta.deletedAt),
      version: Value(e.meta.version),
      vaultAssetId: e.vaultAssetId,
      mode: e.mode,
      currency: e.currency,
      basisPoints: Value(e.basisPoints),
      fixedAmountMinor: Value(fixed?.minorUnits),
      isActive: Value(e.isActive),
      progressionOfferedAt: Value(e.progressionOfferedAt),
    );
  }

  @override
  AllocationRule withMeta(AllocationRule e, SyncMeta meta) =>
      e.copyWith(meta: meta);

  @override
  Future<AllocationRule?> activeFor(String vaultAssetId) async {
    final row =
        await (db.select(db.allocationRules)
              ..where(
                (t) =>
                    t.vaultAssetId.equals(vaultAssetId) &
                    t.deletedAt.isNull() &
                    t.isActive.equals(true),
              )
              ..orderBy([(t) => OrderingTerm.desc(t.updatedAt)])
              ..limit(1))
            .getSingleOrNull();
    return row == null ? null : fromRow(row);
  }
}

@Riverpod(keepAlive: true)
Future<AssetRepository> assetRepository(Ref ref) async => DriftAssetRepository(
  await ref.watch(appDatabaseProvider.future),
  ref.watch(clockProvider),
);

@Riverpod(keepAlive: true)
Future<VaultTransactionRepository> vaultTransactionRepository(Ref ref) async =>
    DriftVaultTransactionRepository(
      await ref.watch(appDatabaseProvider.future),
      ref.watch(clockProvider),
    );

@Riverpod(keepAlive: true)
Future<AllocationRuleRepository> allocationRuleRepository(Ref ref) async =>
    DriftAllocationRuleRepository(
      await ref.watch(appDatabaseProvider.future),
      ref.watch(clockProvider),
    );
