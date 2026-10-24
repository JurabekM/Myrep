import 'package:baraka_daftari/core/db/database_provider.dart';
import 'package:baraka_daftari/core/domain/sync_meta.dart';
import 'package:baraka_daftari/core/time/clock.dart';
import 'package:baraka_daftari/features/audit/data/drift_monthly_report_repository.dart';
import 'package:baraka_daftari/features/budget/data/drift_budget_repositories.dart';
import 'package:baraka_daftari/features/budget/domain/budget.dart';
import 'package:baraka_daftari/features/budget/domain/havas_service.dart';
import 'package:baraka_daftari/features/budget/domain/insights_service.dart';
import 'package:baraka_daftari/features/budget/domain/rescue_service.dart';
import 'package:baraka_daftari/features/expenses/data/drift_expense_repository.dart';
import 'package:baraka_daftari/features/household/data/drift_household_repository.dart';
import 'package:baraka_daftari/features/household/data/household_providers.dart';
import 'package:baraka_daftari/features/obligations/data/drift_obligation_repository.dart';
import 'package:baraka_daftari/features/vault/data/vault_providers.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:riverpod_annotation/riverpod_annotation.dart';

part 'budget_providers.g.dart';

@Riverpod(keepAlive: true)
Future<HavasService> havasService(Ref ref) async => HavasService(
  households: await ref.watch(householdRepositoryProvider.future),
  members: await ref.watch(memberRepositoryProvider.future),
  limits: await ref.watch(havasLimitRepositoryProvider.future),
  consents: await ref.watch(limitConsentRepositoryProvider.future),
  memberPins: await ref.watch(memberPinServiceProvider.future),
  expenses: await ref.watch(expenseRepositoryProvider.future),
  categories: await ref.watch(categoryRepositoryProvider.future),
  metaFactory: ref.watch(syncMetaFactoryProvider),
  clock: ref.watch(clockProvider),
);

@Riverpod(keepAlive: true)
Future<InsightsService> insightsService(Ref ref) async => InsightsService(
  households: await ref.watch(householdRepositoryProvider.future),
  expenses: await ref.watch(expenseRepositoryProvider.future),
  categories: await ref.watch(categoryRepositoryProvider.future),
  obligations: await ref.watch(obligationRepositoryProvider.future),
  habits: await ref.watch(habitRepositoryProvider.future),
  treats: await ref.watch(scheduledTreatRepositoryProvider.future),
  metaFactory: ref.watch(syncMetaFactoryProvider),
  clock: ref.watch(clockProvider),
);

@riverpod
Future<HavasOverview> havasOverview(Ref ref) async {
  // Egasi hali yaratilmagan bo'lsa — yaratiladi (rozilik beradigan katta).
  await (await ref.watch(
    householdServiceProvider.future,
  )).members(ownerName: '');
  return (await ref.watch(havasServiceProvider.future)).overview();
}

@riverpod
Future<SpendingInsights> spendingInsights(Ref ref) async =>
    (await ref.watch(insightsServiceProvider.future)).spending();

@riverpod
Future<List<RollupLine<Habit>>> habitStats(Ref ref) async =>
    (await ref.watch(insightsServiceProvider.future)).habits();

@riverpod
Future<List<ScheduledTreat>> treats(Ref ref) async =>
    (await ref.watch(insightsServiceProvider.future)).treats();

@Riverpod(keepAlive: true)
Future<RescueService> rescueService(Ref ref) async => RescueService(
  households: await ref.watch(householdRepositoryProvider.future),
  expenses: await ref.watch(expenseRepositoryProvider.future),
  categories: await ref.watch(categoryRepositoryProvider.future),
  reports: DriftMonthlyReportRepository(
    await ref.watch(appDatabaseProvider.future),
    ref.watch(clockProvider),
  ),
  rescues: await ref.watch(savingsRescueRepositoryProvider.future),
  vault: await ref.watch(vaultServiceProvider.future),
  metaFactory: ref.watch(syncMetaFactoryProvider),
  clock: ref.watch(clockProvider),
);

@riverpod
Future<RescueOverview> rescueOverview(Ref ref) async =>
    (await ref.watch(rescueServiceProvider.future)).overview();
