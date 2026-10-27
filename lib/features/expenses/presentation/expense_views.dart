import 'package:baraka_daftari/features/audit/data/audit_providers.dart';
import 'package:baraka_daftari/features/expenses/data/expense_providers.dart';
import 'package:baraka_daftari/features/expenses/domain/expense.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:riverpod_annotation/riverpod_annotation.dart';

part 'expense_views.g.dart';

/// Joriy oy (oylik kuni bo'yicha) xarajatlari, eng yangisi birinchi.
@riverpod
Future<List<Expense>> monthExpenses(Ref ref) async {
  final period = await (await ref.watch(
    ledgerServiceProvider.future,
  )).currentPeriod();
  return (await ref.watch(expenseServiceProvider.future)).listIn(period);
}

@riverpod
Future<List<Category>> expenseCategories(Ref ref) async =>
    (await ref.watch(expenseServiceProvider.future)).categories();

@riverpod
Future<List<ExpenseTemplate>> expenseTemplates(Ref ref) async =>
    (await ref.watch(expenseServiceProvider.future)).templates();

@riverpod
Future<Expense?> latestExpense(Ref ref) async =>
    (await ref.watch(expenseServiceProvider.future)).latest();

@riverpod
Future<List<NecessityChange>> necessityHistory(
  Ref ref,
  String categoryId,
) async => (await ref.watch(
  expenseServiceProvider.future,
)).necessityHistory(categoryId);
