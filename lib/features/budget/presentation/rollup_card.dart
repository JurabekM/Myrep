import 'package:baraka_daftari/app/l10n/l10n.dart';
import 'package:baraka_daftari/app/widgets/labels.dart';
import 'package:baraka_daftari/app/widgets/money_input.dart';
import 'package:baraka_daftari/features/budget/data/budget_providers.dart';
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

/// Jamlash effekti (SPEC 2B.1): mayda kategoriyalar haftasiga / oyiga /
/// yiliga va «ijarangizning X%i».
class RollupCard extends ConsumerWidget {
  const RollupCard({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final insights = ref.watch(spendingInsightsProvider).valueOrNull;
    if (insights == null || insights.lines.isEmpty) {
      return const SizedBox.shrink();
    }
    final l10n = context.l10n;
    final theme = Theme.of(context);
    final money = context.money;
    final reference = insights.reference;
    return Card(
      key: const Key('rollup-card'),
      child: Padding(
        padding: const EdgeInsets.all(16),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text(l10n.rollupTitle, style: theme.textTheme.titleMedium),
            Text(
              l10n.rollupWindow,
              style: theme.textTheme.bodySmall?.copyWith(
                color: theme.colorScheme.onSurfaceVariant,
              ),
            ),
            for (final line in insights.lines.take(5)) ...[
              const SizedBox(height: 10),
              Text(
                l10n.category(line.subject),
                style: theme.textTheme.labelLarge,
              ),
              Text(
                l10n.rollupLine(
                  money(line.rollup.perWeek),
                  money(line.rollup.perMonth),
                  money(line.rollup.perYear),
                ),
                key: Key('rollup-${line.subject.meta.id}'),
              ),
              if (reference != null)
                switch (insights.shareOfReference(line.rollup.perMonth)) {
                  final int bp when bp > 0 => Text(
                    l10n.rollupShare(reference.title, percentLabel(bp)),
                    style: theme.textTheme.bodySmall?.copyWith(
                      color: theme.colorScheme.tertiary,
                    ),
                  ),
                  _ => const SizedBox.shrink(),
                },
            ],
          ],
        ),
      ),
    );
  }
}
