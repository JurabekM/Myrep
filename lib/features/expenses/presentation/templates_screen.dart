import 'package:baraka_daftari/app/l10n/l10n.dart';
import 'package:baraka_daftari/app/refresh.dart';
import 'package:baraka_daftari/app/router/app_routes.dart';
import 'package:baraka_daftari/app/widgets/labels.dart';
import 'package:baraka_daftari/app/widgets/money_input.dart';
import 'package:baraka_daftari/features/expenses/data/expense_providers.dart';
import 'package:baraka_daftari/features/expenses/domain/expense.dart';
import 'package:baraka_daftari/features/expenses/presentation/expense_views.dart';
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';

/// Xarajat shablonlari ro'yxati. Yangi shablon xarajat ekranidan
/// («Shablon sifatida ham saqlash») qo'shiladi.
class TemplatesScreen extends ConsumerWidget {
  const TemplatesScreen({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final l10n = context.l10n;
    final templates = ref.watch(expenseTemplatesProvider);
    final categories = {
      for (final c
          in ref.watch(expenseCategoriesProvider).valueOrNull ??
              const <Category>[])
        c.meta.id: c,
    };
    return Scaffold(
      appBar: AppBar(title: Text(l10n.templatesTitle)),
      floatingActionButton: FloatingActionButton.extended(
        key: const Key('templates-add'),
        icon: const Icon(Icons.add),
        label: Text(l10n.templateAdd),
        onPressed: () => context.push(AppRoutes.expenseNew),
      ),
      body: switch (templates) {
        AsyncData(:final value) when value.isEmpty => Center(
          child: Padding(
            padding: const EdgeInsets.all(24),
            child: Text(l10n.quickEmpty, textAlign: TextAlign.center),
          ),
        ),
        AsyncData(:final value) => ListView(
          padding: const EdgeInsets.fromLTRB(16, 8, 16, 96),
          children: [
            Card(
              child: Column(
                children: [
                  for (final (i, t) in value.indexed) ...[
                    if (i > 0) const Divider(height: 1),
                    ListTile(
                      key: Key('template-row-${t.meta.id}'),
                      leading: const Icon(Icons.bolt),
                      title: Text(t.title),
                      subtitle: Text(
                        categories[t.categoryId] == null
                            ? ''
                            : l10n.category(categories[t.categoryId]!),
                      ),
                      trailing: Row(
                        mainAxisSize: MainAxisSize.min,
                        children: [
                          Text(context.money(t.amount)),
                          IconButton(
                            key: Key('template-delete-${t.meta.id}'),
                            tooltip: l10n.delete,
                            icon: const Icon(Icons.delete_outline),
                            onPressed: () async {
                              await (await ref.read(
                                expenseServiceProvider.future,
                              )).deleteTemplate(t.meta.id);
                              refreshMoneyViews(ref);
                            },
                          ),
                        ],
                      ),
                    ),
                  ],
                ],
              ),
            ),
          ],
        ),
        AsyncError() => Center(child: Text(l10n.genericError)),
        _ => const Center(child: CircularProgressIndicator()),
      },
    );
  }
}
