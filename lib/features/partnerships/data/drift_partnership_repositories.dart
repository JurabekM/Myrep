import 'package:baraka_daftari/core/db/app_database.dart';
import 'package:baraka_daftari/core/db/database_provider.dart';
import 'package:baraka_daftari/core/db/synced_repository.dart';
import 'package:baraka_daftari/core/domain/sync_meta.dart';
import 'package:baraka_daftari/core/money/money.dart';
import 'package:baraka_daftari/core/time/clock.dart';
import 'package:baraka_daftari/features/partnerships/domain/partnership.dart';
import 'package:drift/drift.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:riverpod_annotation/riverpod_annotation.dart';

part 'drift_partnership_repositories.g.dart';

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

class DriftPartnershipRepository
    extends
        DriftSyncedRepository<$PartnershipsTable, PartnershipRow, Partnership>
    implements PartnershipRepository {
  DriftPartnershipRepository(super.db, super.clock);

  @override
  TableInfo<$PartnershipsTable, PartnershipRow> get table => db.partnerships;

  @override
  String get entityName => 'partnership';

  @override
  List<OrderingTerm Function($PartnershipsTable)> get defaultOrder => [
    (t) => OrderingTerm.desc(t.createdAt),
  ];

  @override
  Partnership fromRow(PartnershipRow r) => Partnership(
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
    termMonths: r.termMonths,
    reportPeriod: r.reportPeriod,
    endTerms: r.endTerms,
    disputeTerms: r.disputeTerms,
    status: r.status,
    startDate: r.startDate,
    contractVersion: r.contractVersion,
    notDebtAcknowledged: r.notDebtAcknowledged,
    buyoutMonthly: r.buyoutMonthlyMinor == null
        ? null
        : Money(r.buyoutMonthlyMinor!, r.currency),
  );

  @override
  Insertable<PartnershipRow> toRow(Partnership e) =>
      PartnershipsCompanion.insert(
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
        termMonths: e.termMonths,
        reportPeriod: e.reportPeriod,
        endTerms: e.endTerms,
        disputeTerms: e.disputeTerms,
        startDate: Value(e.startDate),
        contractVersion: Value(e.contractVersion),
        notDebtAcknowledged: Value(e.notDebtAcknowledged),
        buyoutMonthlyMinor: Value(e.buyoutMonthly?.minorUnits),
      );

  @override
  Partnership withMeta(Partnership e, SyncMeta meta) => e.copyWith(meta: meta);
}

class DriftPartnerRepository
    extends DriftSyncedRepository<$PartnersTable, PartnerRow, Partner>
    implements PartnerRepository {
  DriftPartnerRepository(super.db, super.clock);

  @override
  TableInfo<$PartnersTable, PartnerRow> get table => db.partners;

  @override
  String get entityName => 'partner';

  @override
  Partner fromRow(PartnerRow r) => Partner(
    meta: _meta(
      r.id,
      r.householdId,
      r.createdAt,
      r.updatedAt,
      r.deletedAt,
      r.version,
    ),
    partnershipId: r.partnershipId,
    name: r.name,
    role: r.role,
    profitShareBp: r.profitShareBp,
    isMe: r.isMe,
    sortOrder: r.sortOrder,
  );

  @override
  Insertable<PartnerRow> toRow(Partner e) => PartnersCompanion.insert(
    id: e.meta.id,
    householdId: e.meta.householdId,
    createdAt: e.meta.createdAt,
    updatedAt: e.meta.updatedAt,
    deletedAt: Value(e.meta.deletedAt),
    version: Value(e.meta.version),
    partnershipId: e.partnershipId,
    name: e.name,
    role: e.role,
    profitShareBp: e.profitShareBp,
    isMe: Value(e.isMe),
    sortOrder: Value(e.sortOrder),
  );

  @override
  Partner withMeta(Partner e, SyncMeta meta) => e.copyWith(meta: meta);

  @override
  Future<List<Partner>> forPartnership(String partnershipId) async {
    final rows =
        await (db.select(table)
              ..where(
                (t) =>
                    t.partnershipId.equals(partnershipId) &
                    t.deletedAt.isNull(),
              )
              ..orderBy([(t) => OrderingTerm.asc(t.sortOrder)]))
            .get();
    return rows.map(fromRow).toList();
  }
}

class DriftCapitalContributionRepository
    extends
        DriftSyncedRepository<
          $CapitalContributionsTable,
          CapitalContributionRow,
          CapitalContribution
        >
    implements CapitalContributionRepository {
  DriftCapitalContributionRepository(super.db, super.clock);

  @override
  TableInfo<$CapitalContributionsTable, CapitalContributionRow> get table =>
      db.capitalContributions;

  @override
  String get entityName => 'capital_contribution';

  @override
  CapitalContribution fromRow(CapitalContributionRow r) => CapitalContribution(
    meta: _meta(
      r.id,
      r.householdId,
      r.createdAt,
      r.updatedAt,
      r.deletedAt,
      r.version,
    ),
    partnershipId: r.partnershipId,
    partnerId: r.partnerId,
    kind: r.kind,
    title: r.title,
    amount: Money(r.amountMinor, r.currency),
  );

  @override
  Insertable<CapitalContributionRow> toRow(CapitalContribution e) =>
      CapitalContributionsCompanion.insert(
        id: e.meta.id,
        householdId: e.meta.householdId,
        createdAt: e.meta.createdAt,
        updatedAt: e.meta.updatedAt,
        deletedAt: Value(e.meta.deletedAt),
        version: Value(e.meta.version),
        partnershipId: e.partnershipId,
        partnerId: e.partnerId,
        kind: e.kind,
        title: e.title,
        amountMinor: e.amount.minorUnits,
        currency: e.amount.currency,
      );

  @override
  CapitalContribution withMeta(CapitalContribution e, SyncMeta meta) =>
      e.copyWith(meta: meta);

  @override
  Future<List<CapitalContribution>> forPartnership(String id) async {
    final rows =
        await (db.select(table)
              ..where((t) => t.partnershipId.equals(id) & t.deletedAt.isNull())
              ..orderBy([(t) => OrderingTerm.asc(t.createdAt)]))
            .get();
    return rows.map(fromRow).toList();
  }
}

class DriftPartnershipContractRepository
    extends
        DriftSyncedRepository<
          $PartnershipContractsTable,
          PartnershipContractRow,
          PartnershipContract
        >
    implements PartnershipContractRepository {
  DriftPartnershipContractRepository(super.db, super.clock);

  @override
  TableInfo<$PartnershipContractsTable, PartnershipContractRow> get table =>
      db.partnershipContracts;

  @override
  String get entityName => 'partnership_contract';

  @override
  PartnershipContract fromRow(PartnershipContractRow r) => PartnershipContract(
    meta: _meta(
      r.id,
      r.householdId,
      r.createdAt,
      r.updatedAt,
      r.deletedAt,
      r.version,
    ),
    partnershipId: r.partnershipId,
    version: r.contractVersion,
    templateId: r.templateId,
    termsJson: r.termsJson,
  );

  @override
  Insertable<PartnershipContractRow> toRow(PartnershipContract e) =>
      PartnershipContractsCompanion.insert(
        id: e.meta.id,
        householdId: e.meta.householdId,
        createdAt: e.meta.createdAt,
        updatedAt: e.meta.updatedAt,
        deletedAt: Value(e.meta.deletedAt),
        version: Value(e.meta.version),
        partnershipId: e.partnershipId,
        contractVersion: e.version,
        templateId: e.templateId,
        termsJson: e.termsJson,
      );

  @override
  PartnershipContract withMeta(PartnershipContract e, SyncMeta meta) =>
      e.copyWith(meta: meta);

  @override
  Future<List<PartnershipContract>> forPartnership(String id) async {
    final rows =
        await (db.select(table)
              ..where((t) => t.partnershipId.equals(id) & t.deletedAt.isNull())
              ..orderBy([(t) => OrderingTerm.asc(t.contractVersion)]))
            .get();
    return rows.map(fromRow).toList();
  }
}

class DriftBuyoutPaymentRepository
    extends
        DriftSyncedRepository<
          $BuyoutPaymentsTable,
          BuyoutPaymentRow,
          BuyoutPayment
        >
    implements BuyoutPaymentRepository {
  DriftBuyoutPaymentRepository(super.db, super.clock);

  @override
  TableInfo<$BuyoutPaymentsTable, BuyoutPaymentRow> get table =>
      db.buyoutPayments;

  @override
  String get entityName => 'buyout_payment';

  @override
  BuyoutPayment fromRow(BuyoutPaymentRow r) => BuyoutPayment(
    meta: _meta(
      r.id,
      r.householdId,
      r.createdAt,
      r.updatedAt,
      r.deletedAt,
      r.version,
    ),
    partnershipId: r.partnershipId,
    amount: Money(r.amountMinor, r.currency),
    paidOn: r.paidOn,
  );

  @override
  Insertable<BuyoutPaymentRow> toRow(BuyoutPayment e) =>
      BuyoutPaymentsCompanion.insert(
        id: e.meta.id,
        householdId: e.meta.householdId,
        createdAt: e.meta.createdAt,
        updatedAt: e.meta.updatedAt,
        deletedAt: Value(e.meta.deletedAt),
        version: Value(e.meta.version),
        partnershipId: e.partnershipId,
        amountMinor: e.amount.minorUnits,
        currency: e.amount.currency,
        paidOn: e.paidOn,
      );

  @override
  BuyoutPayment withMeta(BuyoutPayment e, SyncMeta meta) =>
      e.copyWith(meta: meta);

  @override
  Future<List<BuyoutPayment>> forPartnership(String id) async {
    final rows =
        await (db.select(table)
              ..where((t) => t.partnershipId.equals(id) & t.deletedAt.isNull())
              ..orderBy([(t) => OrderingTerm.asc(t.paidOn)]))
            .get();
    return rows.map(fromRow).toList();
  }
}

class DriftPartnershipConsentRepository
    extends
        DriftSyncedRepository<
          $PartnershipConsentsTable,
          PartnershipConsentRow,
          PartnershipConsent
        >
    implements PartnershipConsentRepository {
  DriftPartnershipConsentRepository(super.db, super.clock);

  @override
  TableInfo<$PartnershipConsentsTable, PartnershipConsentRow> get table =>
      db.partnershipConsents;

  @override
  String get entityName => 'partnership_consent';

  @override
  PartnershipConsent fromRow(PartnershipConsentRow r) => PartnershipConsent(
    meta: _meta(
      r.id,
      r.householdId,
      r.createdAt,
      r.updatedAt,
      r.deletedAt,
      r.version,
    ),
    partnershipId: r.partnershipId,
    memberId: r.memberId,
  );

  @override
  Insertable<PartnershipConsentRow> toRow(PartnershipConsent e) =>
      PartnershipConsentsCompanion.insert(
        id: e.meta.id,
        householdId: e.meta.householdId,
        createdAt: e.meta.createdAt,
        updatedAt: e.meta.updatedAt,
        deletedAt: Value(e.meta.deletedAt),
        version: Value(e.meta.version),
        partnershipId: e.partnershipId,
        memberId: e.memberId,
      );

  @override
  PartnershipConsent withMeta(PartnershipConsent e, SyncMeta meta) =>
      e.copyWith(meta: meta);

  @override
  Future<List<PartnershipConsent>> forPartnership(String id) async {
    final rows = await (db.select(
      table,
    )..where((t) => t.partnershipId.equals(id) & t.deletedAt.isNull())).get();
    return rows.map(fromRow).toList();
  }
}

@Riverpod(keepAlive: true)
Future<PartnershipRepository> partnershipRepository(Ref ref) async =>
    DriftPartnershipRepository(
      await ref.watch(appDatabaseProvider.future),
      ref.watch(clockProvider),
    );

@Riverpod(keepAlive: true)
Future<PartnerRepository> partnerRepository(Ref ref) async =>
    DriftPartnerRepository(
      await ref.watch(appDatabaseProvider.future),
      ref.watch(clockProvider),
    );

@Riverpod(keepAlive: true)
Future<CapitalContributionRepository> capitalContributionRepository(
  Ref ref,
) async => DriftCapitalContributionRepository(
  await ref.watch(appDatabaseProvider.future),
  ref.watch(clockProvider),
);

@Riverpod(keepAlive: true)
Future<PartnershipContractRepository> partnershipContractRepository(
  Ref ref,
) async => DriftPartnershipContractRepository(
  await ref.watch(appDatabaseProvider.future),
  ref.watch(clockProvider),
);

@Riverpod(keepAlive: true)
Future<BuyoutPaymentRepository> buyoutPaymentRepository(Ref ref) async =>
    DriftBuyoutPaymentRepository(
      await ref.watch(appDatabaseProvider.future),
      ref.watch(clockProvider),
    );

@Riverpod(keepAlive: true)
Future<PartnershipConsentRepository> partnershipConsentRepository(
  Ref ref,
) async => DriftPartnershipConsentRepository(
  await ref.watch(appDatabaseProvider.future),
  ref.watch(clockProvider),
);
