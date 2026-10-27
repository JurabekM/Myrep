import 'dart:convert';

import 'package:baraka_daftari/core/db/app_database.dart';
import 'package:baraka_daftari/core/db/database_provider.dart';
import 'package:baraka_daftari/core/db/synced_repository.dart';
import 'package:baraka_daftari/core/domain/sync_meta.dart';
import 'package:baraka_daftari/core/money/money.dart';
import 'package:baraka_daftari/core/security/pin/pin_models.dart';
import 'package:baraka_daftari/core/time/clock.dart';
import 'package:baraka_daftari/features/household/domain/household.dart';
import 'package:drift/drift.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:riverpod_annotation/riverpod_annotation.dart';

part 'drift_household_repository.g.dart';

class DriftHouseholdRepository
    extends DriftSyncedRepository<$HouseholdsTable, HouseholdRow, Household>
    implements HouseholdRepository {
  DriftHouseholdRepository(super.db, super.clock);

  @override
  TableInfo<$HouseholdsTable, HouseholdRow> get table => db.households;

  @override
  String get entityName => 'household';

  @override
  Household fromRow(HouseholdRow r) => Household(
    meta: DriftSyncedRepository.metaOf(
      id: r.id,
      householdId: r.householdId,
      createdAt: r.createdAt,
      updatedAt: r.updatedAt,
      deletedAt: r.deletedAt,
      version: r.version,
    ),
    name: r.name,
    baseCurrency: r.baseCurrency,
    weekAnchor: r.weekAnchor,
    monthStartDay: r.monthStartDay,
    rescueBaselineStart: r.rescueBaselineStart,
    reserveMonthlyEstimate: r.reserveMonthlyEstimateMinor == null
        ? null
        : Money(r.reserveMonthlyEstimateMinor!, r.baseCurrency),
    gateBypassedAt: r.gateBypassedAt?.toUtc(),
    budgetMode: r.budgetMode,
    recoverySplit: RecoverySplit(
      needsBp: r.recoveryNeedsBp,
      debtBp: r.recoveryDebtBp,
      savingsBp: r.recoverySavingsBp,
    ),
    freedShareOfferPending: r.freedShareOfferPending,
    onboardedAt: r.onboardedAt?.toUtc(),
    incomeKind: r.incomeKind,
  );

  @override
  Insertable<HouseholdRow> toRow(Household e) => HouseholdsCompanion.insert(
    id: e.meta.id,
    householdId: e.meta.householdId,
    createdAt: e.meta.createdAt,
    updatedAt: e.meta.updatedAt,
    deletedAt: Value(e.meta.deletedAt),
    version: Value(e.meta.version),
    name: Value(e.name),
    baseCurrency: Value(e.baseCurrency),
    weekAnchor: Value(e.weekAnchor),
    monthStartDay: Value(e.monthStartDay),
    rescueBaselineStart: Value(e.rescueBaselineStart),
    reserveMonthlyEstimateMinor: Value(e.reserveMonthlyEstimate?.minorUnits),
    gateBypassedAt: Value(e.gateBypassedAt),
    budgetMode: Value(e.budgetMode),
    recoveryNeedsBp: Value(e.recoverySplit.needsBp),
    recoveryDebtBp: Value(e.recoverySplit.debtBp),
    recoverySavingsBp: Value(e.recoverySplit.savingsBp),
    freedShareOfferPending: Value(e.freedShareOfferPending),
    onboardedAt: Value(e.onboardedAt),
    incomeKind: Value(e.incomeKind),
  );

  @override
  Household withMeta(Household e, SyncMeta meta) => e.copyWith(meta: meta);

  @override
  Future<Household> current() async {
    final row =
        await (db.select(db.households)
              ..where((t) => t.deletedAt.isNull())
              ..orderBy([(t) => OrderingTerm.asc(t.createdAt)])
              ..limit(1))
            .getSingleOrNull();
    if (row == null) throw StateError("Uy xo'jaligi topilmadi (seed yo'q)");
    return fromRow(row);
  }
}

class DriftMemberRepository
    extends DriftSyncedRepository<$MembersTable, MemberRow, Member>
    implements MemberRepository {
  DriftMemberRepository(super.db, super.clock);

  @override
  TableInfo<$MembersTable, MemberRow> get table => db.members;

  @override
  String get entityName => 'member';

  @override
  List<OrderingTerm Function($MembersTable)> get defaultOrder => [
    (t) => OrderingTerm.desc(t.isOwner),
    (t) => OrderingTerm.asc(t.createdAt),
  ];

  @override
  Member fromRow(MemberRow r) => Member(
    meta: DriftSyncedRepository.metaOf(
      id: r.id,
      householdId: r.householdId,
      createdAt: r.createdAt,
      updatedAt: r.updatedAt,
      deletedAt: r.deletedAt,
      version: r.version,
    ),
    displayName: r.displayName,
    role: r.role,
    isOwner: r.isOwner,
    personalPin: switch (r.pinRecord) {
      final String json => PinRecord.fromJson(
        jsonDecode(json) as Map<String, dynamic>,
      ),
      null => null,
    },
  );

  @override
  Insertable<MemberRow> toRow(Member e) => MembersCompanion.insert(
    id: e.meta.id,
    householdId: e.meta.householdId,
    createdAt: e.meta.createdAt,
    updatedAt: e.meta.updatedAt,
    deletedAt: Value(e.meta.deletedAt),
    version: Value(e.meta.version),
    displayName: e.displayName,
    role: e.role,
    isOwner: Value(e.isOwner),
    pinRecord: Value(switch (e.personalPin) {
      final PinRecord p => jsonEncode(p.toJson()),
      null => null,
    }),
  );

  @override
  Member withMeta(Member e, SyncMeta meta) => e.copyWith(meta: meta);
}

@Riverpod(keepAlive: true)
Future<HouseholdRepository> householdRepository(Ref ref) async =>
    DriftHouseholdRepository(
      await ref.watch(appDatabaseProvider.future),
      ref.watch(clockProvider),
    );

@Riverpod(keepAlive: true)
Future<MemberRepository> memberRepository(Ref ref) async =>
    DriftMemberRepository(
      await ref.watch(appDatabaseProvider.future),
      ref.watch(clockProvider),
    );
