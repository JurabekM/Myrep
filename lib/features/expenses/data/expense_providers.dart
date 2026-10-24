import 'package:baraka_daftari/core/domain/sync_meta.dart';
import 'package:baraka_daftari/core/time/clock.dart';
import 'package:baraka_daftari/features/expenses/data/drift_expense_repository.dart';
import 'package:baraka_daftari/features/expenses/domain/expense_service.dart';
import 'package:baraka_daftari/features/household/data/drift_household_repository.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:riverpod_annotation/riverpod_annotation.dart';

part 'expense_providers.g.dart';

@Riverpod(keepAlive: true)
Future<ExpenseService> expenseService(Ref ref) async => ExpenseService(
  households: await ref.watch(householdRepositoryProvider.future),
  expenses: await ref.watch(expenseRepositoryProvider.future),
  categories: await ref.watch(categoryRepositoryProvider.future),
  templates: await ref.watch(expenseTemplateRepositoryProvider.future),
  necessityChanges: await ref.watch(necessityChangeRepositoryProvider.future),
  metaFactory: ref.watch(syncMetaFactoryProvider),
  clock: ref.watch(clockProvider),
);
