import 'package:baraka_daftari/core/domain/sync_meta.dart';
import 'package:baraka_daftari/core/time/clock.dart';
import 'package:baraka_daftari/features/budget/data/drift_budget_repositories.dart';
import 'package:baraka_daftari/features/household/data/drift_household_repository.dart';
import 'package:baraka_daftari/features/subscriptions/data/drift_subscription_repository.dart';
import 'package:baraka_daftari/features/subscriptions/domain/subscription.dart';
import 'package:baraka_daftari/features/subscriptions/domain/subscription_service.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:riverpod_annotation/riverpod_annotation.dart';

part 'subscription_providers.g.dart';

@Riverpod(keepAlive: true)
Future<SubscriptionService> subscriptionService(Ref ref) async =>
    SubscriptionService(
      households: await ref.watch(householdRepositoryProvider.future),
      subscriptions: await ref.watch(subscriptionRepositoryProvider.future),
      rescues: await ref.watch(savingsRescueRepositoryProvider.future),
      metaFactory: ref.watch(syncMetaFactoryProvider),
      clock: ref.watch(clockProvider),
    );

@riverpod
Future<List<Subscription>> subscriptions(Ref ref) async =>
    (await ref.watch(subscriptionServiceProvider.future)).list();
