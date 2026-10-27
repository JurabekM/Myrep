import 'package:baraka_daftari/core/db/app_database.dart';
import 'package:baraka_daftari/core/db/database_provider.dart';
import 'package:baraka_daftari/core/db/synced_repository.dart';
import 'package:baraka_daftari/core/domain/sync_meta.dart';
import 'package:baraka_daftari/core/money/money.dart';
import 'package:baraka_daftari/core/time/clock.dart';
import 'package:baraka_daftari/features/subscriptions/domain/subscription.dart';
import 'package:drift/drift.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:riverpod_annotation/riverpod_annotation.dart';

part 'drift_subscription_repository.g.dart';

class DriftSubscriptionRepository
    extends
        DriftSyncedRepository<
          $SubscriptionsTable,
          SubscriptionRow,
          Subscription
        >
    implements SubscriptionRepository {
  DriftSubscriptionRepository(super.db, super.clock);

  @override
  TableInfo<$SubscriptionsTable, SubscriptionRow> get table => db.subscriptions;

  @override
  String get entityName => 'subscription';

  @override
  List<OrderingTerm Function($SubscriptionsTable)> get defaultOrder => [
    (t) => OrderingTerm.asc(t.createdAt),
  ];

  @override
  Subscription fromRow(SubscriptionRow r) => Subscription(
    meta: DriftSyncedRepository.metaOf(
      id: r.id,
      householdId: r.householdId,
      createdAt: r.createdAt,
      updatedAt: r.updatedAt,
      deletedAt: r.deletedAt,
      version: r.version,
    ),
    title: r.title,
    price: Money(r.amountMinor, r.currency),
    cycle: r.cycle,
    startedOn: r.startedOn,
    lastUsedOn: r.lastUsedOn,
    cancelledOn: r.cancelledOn,
  );

  @override
  Insertable<SubscriptionRow> toRow(Subscription e) =>
      SubscriptionsCompanion.insert(
        id: e.meta.id,
        householdId: e.meta.householdId,
        createdAt: e.meta.createdAt,
        updatedAt: e.meta.updatedAt,
        deletedAt: Value(e.meta.deletedAt),
        version: Value(e.meta.version),
        title: e.title,
        amountMinor: e.price.minorUnits,
        currency: e.price.currency,
        cycle: e.cycle,
        startedOn: e.startedOn,
        lastUsedOn: Value(e.lastUsedOn),
        cancelledOn: Value(e.cancelledOn),
      );

  @override
  Subscription withMeta(Subscription e, SyncMeta meta) =>
      e.copyWith(meta: meta);
}

@Riverpod(keepAlive: true)
Future<SubscriptionRepository> subscriptionRepository(Ref ref) async =>
    DriftSubscriptionRepository(
      await ref.watch(appDatabaseProvider.future),
      ref.watch(clockProvider),
    );
