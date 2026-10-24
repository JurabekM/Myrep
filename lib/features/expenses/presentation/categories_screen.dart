import 'package:baraka_daftari/app/l10n/l10n.dart';
import 'package:baraka_daftari/app/refresh.dart';
import 'package:baraka_daftari/app/widgets/labels.dart';
import 'package:baraka_daftari/core/domain/enums.dart';
import 'package:baraka_daftari/core/logging/app_log.dart';
import 'package:baraka_daftari/core/time/calendar.dart';
import 'package:baraka_daftari/features/expenses/data/expense_providers.dart';
import 'package:baraka_daftari/features/expenses/domain/expense.dart';
import 'package:baraka_daftari/features/expenses/presentation/expense_new_screen.dart';
import 'package:baraka_daftari/features/expenses/presentation/expense_views.dart';
import 'package:baraka_daftari/features/household/domain/household.dart';
import 'package:baraka_daftari/features/household/presentation/member_views.dart';
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

/// Kategoriyalarning standart toifasi va o'zgarishlar tarixi (SPEC 2B.2).
class CategoriesScreen extends ConsumerWidget {
  const CategoriesScreen({super.key});

  Future<void> _change(
    BuildContext context,
    WidgetRef ref,
    Category c,
    Necessity n,
  ) async {
    final messenger = ScaffoldMessenger.of(context);
    final error = context.l10n.genericError;
    final members = await ref.read(membersProvider.future);
    if (!context.mounted) return;
    var who = members.length == 1 ? members.single.meta.id : null;
    if (members.length > 1) {
      who = await showDialog<String>(
        context: context,
        builder: (context) => SimpleDialog(
          title: Text(context.l10n.whoChanges),
          children: [
            for (final m in members)
              SimpleDialogOption(
                key: Key('who-${m.meta.id}'),
                onPressed: () => Navigator.pop(context, m.meta.id),
                child: Text(context.l10n.member(m)),
              ),
          ],
        ),
      );
      if (who == null) return;
    }
    try {
      await (await ref.read(
        expenseServiceProvider.future,
      )).setCategoryNecessity(c, n, memberId: who);
      ref
        ..invalidate(expenseCategoriesProvider)
        ..invalidate(necessityHistoryProvider(c.meta.id));
      refreshMoneyViews(ref);
    } on Object {
      AppLog.event('category_necessity_failed');
      messenger.showSnackBar(SnackBar(content: Text(error)));
    }
  }

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final l10n = context.l10n;
    final categories = ref.watch(expenseCategoriesProvider);
    return Scaffold(
      appBar: AppBar(title: Text(l10n.categoriesTitle)),
      body: switch (categories) {
        AsyncData(:final value) => ListView(
          padding: const EdgeInsets.fromLTRB(16, 8, 16, 24),
          children: [
            Text(l10n.categoriesHint),
            const SizedBox(height: 8),
            for (final c in value)
              Card(
                key: Key('category-row-${c.systemKey?.name ?? c.meta.id}'),
                child: Padding(
                  padding: const EdgeInsets.fromLTRB(16, 8, 8, 8),
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Row(
                        children: [
                          Expanded(
                            child: Text(
                              l10n.category(c),
                              style: Theme.of(context).textTheme.titleSmall,
                            ),
                          ),
                          IconButton(
                            key: Key('history-${c.meta.id}'),
                            tooltip: l10n.categoryHistory,
                            icon: const Icon(Icons.history),
                            onPressed: () => showModalBottomSheet<void>(
                              context: context,
                              showDragHandle: true,
                              builder: (_) => _HistorySheet(category: c),
                            ),
                          ),
                        ],
                      ),
                      if (c.systemKey == CategoryKey.sadaqa)
                        Text(l10n.necessitySadaqaNote)
                      else
                        NecessitySelector(
                          value: c.defaultNecessity,
                          onChanged: (n) => _change(context, ref, c, n),
                        ),
                    ],
                  ),
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

class _HistorySheet extends ConsumerWidget {
  const _HistorySheet({required this.category});

  final Category category;

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final l10n = context.l10n;
    final history = ref.watch(necessityHistoryProvider(category.meta.id));
    final members = {
      for (final m
          in ref.watch(membersProvider).valueOrNull ?? const <Member>[])
        m.meta.id: m,
    };
    return SafeArea(
      child: Padding(
        padding: const EdgeInsets.fromLTRB(16, 0, 16, 16),
        child: Column(
          mainAxisSize: MainAxisSize.min,
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text(
              '${l10n.category(category)} — ${l10n.categoryHistory}',
              style: Theme.of(context).textTheme.titleMedium,
            ),
            const SizedBox(height: 8),
            switch (history) {
              AsyncData(:final value) when value.isEmpty => Text(
                l10n.categoryHistoryEmpty,
              ),
              AsyncData(:final value) => Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  for (final h in value)
                    Padding(
                      padding: const EdgeInsets.symmetric(vertical: 4),
                      child: Text(
                        l10n.categoryHistoryItem(
                          formatDate(Tashkent.dateOf(h.meta.createdAt)),
                          l10n.necessity(h.from),
                          l10n.necessity(h.to),
                          members[h.memberId] == null
                              ? '—'
                              : l10n.member(members[h.memberId]!),
                        ),
                      ),
                    ),
                ],
              ),
              _ => const LinearProgressIndicator(),
            },
          ],
        ),
      ),
    );
  }
}
