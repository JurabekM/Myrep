import 'package:baraka_daftari/core/domain/sync_meta.dart';
import 'package:baraka_daftari/core/time/clock.dart';
import 'package:baraka_daftari/features/agreements/data/agreement_providers.dart';
import 'package:baraka_daftari/features/debts/data/drift_debt_repositories.dart';
import 'package:baraka_daftari/features/debts/domain/debt_service.dart';
import 'package:baraka_daftari/features/debts/domain/debts.dart';
import 'package:baraka_daftari/features/debts/domain/loan_receipt_service.dart';
import 'package:baraka_daftari/features/debts/domain/recovery_service.dart';
import 'package:baraka_daftari/features/household/data/drift_household_repository.dart';
import 'package:baraka_daftari/features/income/data/drift_income_repository.dart';
import 'package:baraka_daftari/features/obligations/data/drift_obligation_repository.dart';
import 'package:baraka_daftari/features/vault/data/vault_providers.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:riverpod_annotation/riverpod_annotation.dart';

part 'debt_providers.g.dart';

@Riverpod(keepAlive: true)
Future<DebtService> debtService(Ref ref) async => DebtService(
  households: await ref.watch(householdRepositoryProvider.future),
  debts: await ref.watch(debtRepositoryProvider.future),
  installments: await ref.watch(debtInstallmentRepositoryProvider.future),
  payments: await ref.watch(debtPaymentRepositoryProvider.future),
  receivables: await ref.watch(receivableRepositoryProvider.future),
  goals: await ref.watch(goalRepositoryProvider.future),
  contributors: await ref.watch(debtContributorRepositoryProvider.future),
  sellables: await ref.watch(sellableItemRepositoryProvider.future),
  incomes: await ref.watch(incomeRepositoryProvider.future),
  metaFactory: ref.watch(syncMetaFactoryProvider),
  clock: ref.watch(clockProvider),
  agreements: await ref.watch(agreementServiceProvider.future),
);

@riverpod
Future<DebtOverview> debtOverview(Ref ref) async =>
    (await ref.watch(debtServiceProvider.future)).overview();

@Riverpod(keepAlive: true)
Future<LoanReceiptService> loanReceiptService(Ref ref) async =>
    LoanReceiptService(
      households: await ref.watch(householdRepositoryProvider.future),
      signers: await ref.watch(loanSignerRepositoryProvider.future),
      metaFactory: ref.watch(syncMetaFactoryProvider),
      clock: ref.watch(clockProvider),
    );

/// Bitta qarz (tafsilot ekrani).
@riverpod
Future<DebtView?> debtView(Ref ref, String debtId) async {
  final repo = await ref.watch(debtRepositoryProvider.future);
  final debt = await repo.findById(debtId);
  if (debt == null) return null;
  return (await ref.watch(debtServiceProvider.future)).view(debt);
}

/// Bitta bergan qarz (tilxat uchun).
@riverpod
Future<Receivable?> receivable(Ref ref, String id) async =>
    (await ref.watch(receivableRepositoryProvider.future)).findById(id);

@Riverpod(keepAlive: true)
Future<RecoveryService> recoveryService(Ref ref) async => RecoveryService(
  households: await ref.watch(householdRepositoryProvider.future),
  debts: await ref.watch(debtServiceProvider.future),
  vault: await ref.watch(vaultServiceProvider.future),
);

/// «Qarzdan chiqish» rejimi holati (SPEC 2D.1).
@riverpod
Future<RecoveryState> recoveryState(Ref ref) async =>
    (await ref.watch(recoveryServiceProvider.future)).state();

/// Sotiladigan buyumlar (SPEC 2D.7).
@riverpod
Future<List<SellableItem>> sellables(Ref ref) async =>
    (await ref.watch(debtServiceProvider.future)).sellables();
