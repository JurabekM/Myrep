import 'package:baraka_daftari/core/db/database_provider.dart';
import 'package:baraka_daftari/core/domain/sync_meta.dart';
import 'package:baraka_daftari/core/time/clock.dart';
import 'package:baraka_daftari/features/agreements/data/drift_agreement_repositories.dart';
import 'package:baraka_daftari/features/agreements/domain/accountability_service.dart';
import 'package:baraka_daftari/features/agreements/domain/agreement.dart';
import 'package:baraka_daftari/features/agreements/domain/agreement_service.dart';
import 'package:baraka_daftari/features/agreements/domain/journal.dart';
import 'package:baraka_daftari/features/debts/data/drift_debt_repositories.dart';
import 'package:baraka_daftari/features/household/data/drift_household_repository.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:riverpod_annotation/riverpod_annotation.dart';

part 'agreement_providers.g.dart';

@Riverpod(keepAlive: true)
Future<AgreementRepository> agreementRepository(Ref ref) async =>
    DriftAgreementRepository(
      await ref.watch(appDatabaseProvider.future),
      ref.watch(clockProvider),
    );

@Riverpod(keepAlive: true)
Future<AgreementVersionRepository> agreementVersionRepository(Ref ref) async =>
    DriftAgreementVersionRepository(
      await ref.watch(appDatabaseProvider.future),
      ref.watch(clockProvider),
    );

@Riverpod(keepAlive: true)
Future<JournalRepository> journalRepository(Ref ref) async =>
    DriftJournalRepository(
      await ref.watch(appDatabaseProvider.future),
      ref.watch(syncMetaFactoryProvider),
    );

@Riverpod(keepAlive: true)
Future<AgreementService> agreementService(Ref ref) async => AgreementService(
  households: await ref.watch(householdRepositoryProvider.future),
  agreements: await ref.watch(agreementRepositoryProvider.future),
  versions: await ref.watch(agreementVersionRepositoryProvider.future),
  journal: await ref.watch(journalRepositoryProvider.future),
  signers: await ref.watch(loanSignerRepositoryProvider.future),
  metaFactory: ref.watch(syncMetaFactoryProvider),
  clock: ref.watch(clockProvider),
);

/// Kelishuvlar ro'yxati.
@riverpod
Future<List<Agreement>> agreements(Ref ref) async =>
    (await ref.watch(agreementServiceProvider.future)).list();

/// Bitta kelishuv (javoblar, to'liqlik, imzolar, jurnal).
@riverpod
Future<AgreementView?> agreementView(Ref ref, String id) async {
  final s = await ref.watch(agreementServiceProvider.future);
  final a = await s.find(id);
  return a == null ? null : s.view(a);
}

/// Modul yozuviga (qarz, sheriklik) bog'langan kelishuv.
@riverpod
Future<AgreementView?> agreementBySource(
  Ref ref,
  AgreementSource source,
  String sourceId,
) async {
  final s = await ref.watch(agreementServiceProvider.future);
  final a = await s.bySource(source, sourceId);
  return a == null ? null : s.view(a);
}

/// Ko'rik, hodisa va nizo amallari (SPEC 2F.4–2F.8).
@Riverpod(keepAlive: true)
Future<AccountabilityService> accountabilityService(Ref ref) async =>
    AccountabilityService(
      agreements: await ref.watch(agreementServiceProvider.future),
      repo: await ref.watch(agreementRepositoryProvider.future),
      journal: await ref.watch(journalRepositoryProvider.future),
      clock: ref.watch(clockProvider),
    );

/// Bitta kelishuvning kengaytirilgan ko'rinishi (ko'rik, nizolar).
@riverpod
Future<AccountabilityView?> accountabilityView(Ref ref, String id) async {
  final s = await ref.watch(agreementServiceProvider.future);
  final a = await s.find(id);
  if (a == null) return null;
  return (await ref.watch(accountabilityServiceProvider.future)).view(a);
}

/// Kelishuvlar markazi: hamma kelishuvlar, ko'rik va nizo holati bilan.
@riverpod
Future<List<AccountabilityView>> agreementCenter(Ref ref) async {
  final list = await ref.watch(agreementsProvider.future);
  final s = await ref.watch(accountabilityServiceProvider.future);
  return [for (final a in list) await s.view(a)];
}
