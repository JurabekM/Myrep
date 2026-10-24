import 'package:baraka_daftari/core/domain/sync_meta.dart';
import 'package:baraka_daftari/core/time/clock.dart';
import 'package:baraka_daftari/features/debts/domain/debt_service.dart';
import 'package:baraka_daftari/features/expenses/data/drift_expense_repository.dart';
import 'package:baraka_daftari/features/household/data/drift_household_repository.dart';
import 'package:baraka_daftari/features/income/data/drift_income_repository.dart';
import 'package:baraka_daftari/features/income/domain/income_service.dart';
import 'package:baraka_daftari/features/obligations/data/drift_obligation_repository.dart';
import 'package:baraka_daftari/features/vault/data/drift_vault_repository.dart';
import 'package:baraka_daftari/features/vault/domain/essential_spend.dart';
import 'package:baraka_daftari/features/vault/domain/vault_service.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:riverpod_annotation/riverpod_annotation.dart';

part 'vault_providers.g.dart';

@Riverpod(keepAlive: true)
Future<EssentialSpendService> essentialSpendService(Ref ref) async =>
    EssentialSpendService(
      households: await ref.watch(householdRepositoryProvider.future),
      expenses: await ref.watch(expenseRepositoryProvider.future),
      categories: await ref.watch(categoryRepositoryProvider.future),
      clock: ref.watch(clockProvider),
    );

/// Qarz sharti (4-qonun, SPEC 2C.4): ochiq foizli qarz yo'q.
@Riverpod(keepAlive: true)
Future<DebtReadiness> debtReadiness(Ref ref) async => DebtDataReadiness(
  await ref.watch(debtRepositoryProvider.future),
  await ref.watch(householdRepositoryProvider.future),
);

@Riverpod(keepAlive: true)
Future<VaultService> vaultService(Ref ref) async {
  final essentials = await ref.watch(essentialSpendServiceProvider.future);
  return VaultService(
    households: await ref.watch(householdRepositoryProvider.future),
    assets: await ref.watch(assetRepositoryProvider.future),
    transactions: await ref.watch(vaultTransactionRepositoryProvider.future),
    rules: await ref.watch(allocationRuleRepositoryProvider.future),
    metaFactory: ref.watch(syncMetaFactoryProvider),
    clock: ref.watch(clockProvider),
    essentials: essentials.monthly,
    debtReadiness: await ref.watch(debtReadinessProvider.future),
  );
}

@Riverpod(keepAlive: true)
Future<IncomeService> incomeService(Ref ref) async => IncomeService(
  households: await ref.watch(householdRepositoryProvider.future),
  incomes: await ref.watch(incomeRepositoryProvider.future),
  metaFactory: ref.watch(syncMetaFactoryProvider),
  clock: ref.watch(clockProvider),
);

/// «Kelajagim» holati. O'zgarishdan keyin `ref.invalidate` qilinadi.
@riverpod
Future<VaultOverview> vaultOverview(Ref ref) async =>
    (await ref.watch(vaultServiceProvider.future)).overview();
