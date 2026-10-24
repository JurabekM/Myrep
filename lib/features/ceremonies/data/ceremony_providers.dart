import 'package:baraka_daftari/core/domain/sync_meta.dart';
import 'package:baraka_daftari/core/time/clock.dart';
import 'package:baraka_daftari/features/ceremonies/data/drift_ceremony_repositories.dart';
import 'package:baraka_daftari/features/ceremonies/domain/ceremony.dart';
import 'package:baraka_daftari/features/ceremonies/domain/ceremony_service.dart';
import 'package:baraka_daftari/features/debts/data/debt_providers.dart';
import 'package:baraka_daftari/features/debts/data/drift_debt_repositories.dart';
import 'package:baraka_daftari/features/household/data/drift_household_repository.dart';
import 'package:baraka_daftari/features/household/data/household_providers.dart';
import 'package:baraka_daftari/features/household/presentation/member_views.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:riverpod_annotation/riverpod_annotation.dart';

part 'ceremony_providers.g.dart';

@Riverpod(keepAlive: true)
Future<CeremonyService> ceremonyService(Ref ref) async => CeremonyService(
  households: await ref.watch(householdRepositoryProvider.future),
  members: await ref.watch(memberRepositoryProvider.future),
  memberPins: await ref.watch(memberPinServiceProvider.future),
  plans: await ref.watch(ceremonyPlanRepositoryProvider.future),
  scenarios: await ref.watch(ceremonyScenarioRepositoryProvider.future),
  lines: await ref.watch(ceremonyBudgetLineRepositoryProvider.future),
  marks: await ref.watch(ceremonyDiscussionMarkRepositoryProvider.future),
  goals: await ref.watch(goalRepositoryProvider.future),
  contributions: await ref.watch(goalContributionRepositoryProvider.future),
  debts: await ref.watch(debtServiceProvider.future),
  metaFactory: ref.watch(syncMetaFactoryProvider),
  clock: ref.watch(clockProvider),
);

/// Marosim rejalari ro'yxati.
@riverpod
Future<List<CeremonyPlan>> ceremonyPlans(Ref ref) async =>
    (await ref.watch(ceremonyServiceProvider.future)).list();

/// Bitta reja (taqqoslash, muhokama, to'yona jamg'armasi).
@riverpod
Future<CeremonyView?> ceremonyView(Ref ref, String planId) async {
  // Egasi a'zo sifatida yaratilgan bo'lsin — muhokamada kattalar bo'sh
  // qolmasin (aks holda qarzli rejani tasdiqlab bo'lmasdi).
  await ref.watch(membersProvider.future);
  final repo = await ref.watch(ceremonyPlanRepositoryProvider.future);
  final plan = await repo.findById(planId);
  if (plan == null || plan.meta.deletedAt != null) return null;
  return (await ref.watch(ceremonyServiceProvider.future)).view(plan);
}
