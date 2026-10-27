import 'package:baraka_daftari/core/domain/sync_meta.dart';
import 'package:baraka_daftari/core/time/clock.dart';
import 'package:baraka_daftari/features/agreements/data/agreement_providers.dart';
import 'package:baraka_daftari/features/debts/data/drift_debt_repositories.dart';
import 'package:baraka_daftari/features/household/data/drift_household_repository.dart';
import 'package:baraka_daftari/features/household/data/household_providers.dart';
import 'package:baraka_daftari/features/household/presentation/member_views.dart';
import 'package:baraka_daftari/features/income/data/drift_income_repository.dart';
import 'package:baraka_daftari/features/partnerships/data/drift_partnership_repositories.dart';
import 'package:baraka_daftari/features/partnerships/data/drift_venture_repositories.dart';
import 'package:baraka_daftari/features/partnerships/domain/partnership.dart';
import 'package:baraka_daftari/features/partnerships/domain/partnership_service.dart';
import 'package:baraka_daftari/features/partnerships/domain/venture.dart';
import 'package:baraka_daftari/features/partnerships/domain/venture_service.dart';
import 'package:baraka_daftari/features/vault/data/vault_providers.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:riverpod_annotation/riverpod_annotation.dart';

part 'partnership_providers.g.dart';

@Riverpod(keepAlive: true)
Future<PartnershipService> partnershipService(Ref ref) async {
  final vault = await ref.watch(vaultServiceProvider.future);
  return PartnershipService(
    households: await ref.watch(householdRepositoryProvider.future),
    members: await ref.watch(memberRepositoryProvider.future),
    memberPins: await ref.watch(memberPinServiceProvider.future),
    partnerships: await ref.watch(partnershipRepositoryProvider.future),
    partners: await ref.watch(partnerRepositoryProvider.future),
    capital: await ref.watch(capitalContributionRepositoryProvider.future),
    contracts: await ref.watch(partnershipContractRepositoryProvider.future),
    signers: await ref.watch(loanSignerRepositoryProvider.future),
    buyouts: await ref.watch(buyoutPaymentRepositoryProvider.future),
    consents: await ref.watch(partnershipConsentRepositoryProvider.future),
    gate: () async => (await vault.overview()).gate,
    metaFactory: ref.watch(syncMetaFactoryProvider),
    clock: ref.watch(clockProvider),
    agreements: await ref.watch(agreementServiceProvider.future),
  );
}

/// Sherikliklar ro'yxati.
@riverpod
Future<List<Partnership>> partnerships(Ref ref) async =>
    (await ref.watch(partnershipServiceProvider.future)).list();

/// Bitta sheriklik (shartnoma, imzolar, rozilik, buyout).
@riverpod
Future<PartnershipView?> partnershipView(Ref ref, String id) async {
  // Egasi a'zo sifatida yaratilsin — oilaviy rozilikda kattalar bo'sh
  // qolmasin.
  await ref.watch(membersProvider.future);
  final repo = await ref.watch(partnershipRepositoryProvider.future);
  final p = await repo.findById(id);
  if (p == null || p.meta.deletedAt != null) return null;
  return (await ref.watch(partnershipServiceProvider.future)).view(p);
}

@Riverpod(keepAlive: true)
Future<VentureLedgerService> ventureLedgerService(Ref ref) async =>
    VentureLedgerService(
      partnerships: await ref.watch(partnershipServiceProvider.future),
      partnershipRepo: await ref.watch(partnershipRepositoryProvider.future),
      entries: await ref.watch(ventureEntryRepositoryProvider.future),
      periods: await ref.watch(venturePeriodRepositoryProvider.future),
      shares: await ref.watch(distributionShareRepositoryProvider.future),
      buyouts: await ref.watch(buyoutPaymentRepositoryProvider.future),
      incomes: await ref.watch(incomeRepositoryProvider.future),
      metaFactory: ref.watch(syncMetaFactoryProvider),
      clock: ref.watch(clockProvider),
      agreements: await ref.watch(agreementServiceProvider.future),
    );

/// Sheriklik kassa daftari.
@riverpod
Future<LedgerView?> ledgerView(Ref ref, String partnershipId) async {
  await ref.watch(membersProvider.future);
  final s = await ref.watch(ventureLedgerServiceProvider.future);
  final p = await s.find(partnershipId);
  return p == null ? null : s.view(p);
}

@Riverpod(keepAlive: true)
Future<IdeaService> ideaService(Ref ref) async => IdeaService(
  households: await ref.watch(householdRepositoryProvider.future),
  skills: await ref.watch(skillRepositoryProvider.future),
  ideas: await ref.watch(ventureIdeaRepositoryProvider.future),
  capex: await ref.watch(ideaCapexItemRepositoryProvider.future),
  metaFactory: ref.watch(syncMetaFactoryProvider),
);

/// «Hunardan ishga»: hunarlar va g'oyalar.
@riverpod
Future<(List<Skill>, List<IdeaView>)> ideasOverview(Ref ref) async {
  final s = await ref.watch(ideaServiceProvider.future);
  return (await s.skills(), await s.ideas());
}

@Riverpod(keepAlive: true)
Future<OfferCheckService> offerCheckService(Ref ref) async => OfferCheckService(
  households: await ref.watch(householdRepositoryProvider.future),
  checks: await ref.watch(offerCheckRepositoryProvider.future),
  metaFactory: ref.watch(syncMetaFactoryProvider),
  clock: ref.watch(clockProvider),
);

/// Saqlangan taklif tekshiruvlari.
@riverpod
Future<List<OfferCheckRecord>> offerChecks(Ref ref) async =>
    (await ref.watch(offerCheckServiceProvider.future)).history();
