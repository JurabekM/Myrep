import 'package:baraka_daftari/app/l10n/l10n.dart';
import 'package:baraka_daftari/app/refresh.dart';
import 'package:baraka_daftari/app/router/app_routes.dart';
import 'package:baraka_daftari/app/widgets/labels.dart';
import 'package:baraka_daftari/app/widgets/money_input.dart';
import 'package:baraka_daftari/app/widgets/paged_list.dart';
import 'package:baraka_daftari/core/money/money.dart';
import 'package:baraka_daftari/core/time/calendar.dart';
import 'package:baraka_daftari/features/budget/domain/budget_math.dart';
import 'package:baraka_daftari/features/budget/presentation/rollup_card.dart';
import 'package:baraka_daftari/features/expenses/data/expense_providers.dart';
import 'package:baraka_daftari/features/expenses/domain/expense.dart';
import 'package:baraka_daftari/features/expenses/presentation/expense_views.dart';
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';

class ExpensesScreen extends ConsumerWidget {
  const ExpensesScreen({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final l10n = context.l10n;
    final expenses = ref.watch(monthExpensesProvider);
    final categories = {
      for (final c
          in ref.watch(expenseCategoriesProvider).valueOrNull ??
              const <Category>[])
        c.meta.id: c,
    };
    return Scaffold(
      appBar: AppBar(
        title: Text(l10n.expensesTitle),
        actions: [
          IconButton(
            key: const Key('nav-templates'),
            tooltip: l10n.templatesTitle,
            icon: const Icon(Icons.bolt),
            onPressed: () => context.push(AppRoutes.templates),
          ),
          IconButton(
            key: const Key('nav-categories'),
            tooltip: l10n.categoriesTitle,
            icon: const Icon(Icons.tune),
            onPressed: () => context.push(AppRoutes.categories),
          ),
        ],
      ),
      floatingActionButton: FloatingActionButton.extended(
        key: const Key('expenses-add'),
        icon: const Icon(Icons.add),
        label: Text(l10n.homeAddExpense),
        onPressed: () => context.push(AppRoutes.expenseNew),
      ),
      body: switch (expenses) {
        AsyncError() => Center(child: Text(l10n.genericError)),
        AsyncData(:final value) when value.isEmpty => Center(
          child: Text(l10n.expensesEmpty),
        ),
        AsyncData(:final value) => ListView(
          padding: const EdgeInsets.fromLTRB(16, 8, 16, 96),
          children: [
            const RollupCard(),
            const SizedBox(height: 8),
            Text(
              l10n.expensesTotal(
                context.money(
                  Money.sum(
                    value.map((e) => e.amount),
                    value.first.amount.currency,
                  ),
                ),
              ),
              key: const Key('expenses-total'),
              style: Theme.of(context).textTheme.titleMedium,
            ),
            const SizedBox(height: 8),
            Card(
              child: Column(
                children: [
                  PagedList(
                    count: value.length,
                    separator: const Divider(height: 1),
                    itemBuilder: (context, i) {
                      final e = value[i];
                      return Dismissible(
                        key: ValueKey(e.meta.id),
                        direction: DismissDirection.endToStart,
                        background: const ColoredBox(
                          color: Colors.transparent,
                          child: Icon(Icons.delete_outline),
                        ),
                        onDismissed: (_) async {
                          final service = await ref.read(
                            expenseServiceProvider.future,
                          );
                          await service.delete(e.meta.id);
                          refreshMoneyViews(ref);
                          if (!context.mounted) return;
                          // «Bekor qilish»: suring bilan o'chirish qaytariladi.
                          ScaffoldMessenger.of(context).showSnackBar(
                            SnackBar(
                              content: Text(l10n.expenseDeleted),
                              action: SnackBarAction(
                                key: const Key('expense-undo'),
                                label: l10n.undo,
                                onPressed: () async {
                                  await service.restore(e.meta.id);
                                  refreshMoneyViews(ref);
                                },
                              ),
                            ),
                          );
                        },
                        child: ListTile(
                          title: Text(
                            categories[e.categoryId] == null
                                ? l10n.catOther
                                : l10n.category(categories[e.categoryId]!),
                          ),
                          subtitle: Text(
                            [
                              formatDate(Tashkent.dateOf(e.spentAt)),
                              l10n.necessity(
                                effectiveNecessity(e, categories[e.categoryId]),
                              ),
                              if (e.isGift) l10n.flagGift,
                              if (e.isOstentation) l10n.flagOstentation,
                            ].join(' · '),
                          ),
                          leading:
                              isDebtFundedHavas(e, categories[e.categoryId])
                              ? Icon(
                                  Icons.flag,
                                  key: Key('debt-flag-${e.meta.id}'),
                                  color: Theme.of(context).colorScheme.error,
                                )
                              : null,
                          trailing: Text(
                            context.money(e.amount),
                            style: Theme.of(context).textTheme.titleSmall,
                          ),
                        ),
                      );
                    },
                  ),
                ],
              ),
            ),
          ],
        ),
        _ => const Center(child: CircularProgressIndicator()),
      },
    );
  }
}
