import 'package:baraka_daftari/core/db/database_provider.dart';
import 'package:baraka_daftari/core/domain/sync_meta.dart';
import 'package:baraka_daftari/core/time/clock.dart';
import 'package:baraka_daftari/features/audit/data/drift_monthly_report_repository.dart';
import 'package:baraka_daftari/features/audit/domain/ledger_service.dart';
import 'package:baraka_daftari/features/expenses/data/drift_expense_repository.dart';
import 'package:baraka_daftari/features/household/data/drift_household_repository.dart';
import 'package:baraka_daftari/features/income/data/drift_income_repository.dart';
import 'package:baraka_daftari/features/obligations/data/drift_obligation_repository.dart';
import 'package:baraka_daftari/features/vault/data/drift_vault_repository.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:riverpod_annotation/riverpod_annotation.dart';

part 'audit_providers.g.dart';

@Riverpod(keepAlive: true)
Future<LedgerService> ledgerService(Ref ref) async => LedgerService(
  households: await ref.watch(householdRepositoryProvider.future),
  incomes: await ref.watch(incomeRepositoryProvider.future),
  expenses: await ref.watch(expenseRepositoryProvider.future),
  categories: await ref.watch(categoryRepositoryProvider.future),
  obligations: await ref.watch(obligationRepositoryProvider.future),
  assets: await ref.watch(assetRepositoryProvider.future),
  vaultTransactions: await ref.watch(vaultTransactionRepositoryProvider.future),
  reports: DriftMonthlyReportRepository(
    await ref.watch(appDatabaseProvider.future),
    ref.watch(clockProvider),
  ),
  metaFactory: ref.watch(syncMetaFactoryProvider),
  clock: ref.watch(clockProvider),
);

/// Bosh ekran ko'rsatkichlari. O'zgarishdan keyin `invalidateMoneyViews`.
@riverpod
Future<HomeKpis> homeKpis(Ref ref) async =>
    (await ref.watch(ledgerServiceProvider.future)).homeKpis();
