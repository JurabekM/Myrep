import 'package:baraka_daftari/app/l10n/l10n.dart';
import 'package:baraka_daftari/app/refresh.dart';
import 'package:baraka_daftari/app/widgets/labels.dart';
import 'package:baraka_daftari/app/widgets/money_input.dart';
import 'package:baraka_daftari/core/logging/app_log.dart';
import 'package:baraka_daftari/core/money/money.dart';
import 'package:baraka_daftari/core/time/calendar.dart';
import 'package:baraka_daftari/core/time/clock.dart';
import 'package:baraka_daftari/features/budget/data/budget_providers.dart';
import 'package:baraka_daftari/features/budget/domain/rescue.dart';
import 'package:baraka_daftari/features/household/data/household_providers.dart';
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

/// Qutqarilganni «Kelajagim»ga o'tkazish (bir bosishda).
Future<void> transferRescue(BuildContext context, WidgetRef ref) async {
  final l10n = context.l10n;
  final messenger = ScaffoldMessenger.of(context);
  final money = context.money;
  try {
    final amount = await (await ref.read(
      rescueServiceProvider.future,
    )).transferWeek();
    refreshMoneyViews(ref);
    messenger.showSnackBar(
      SnackBar(content: Text(l10n.rescueTransferDone(money(amount)))),
    );
  } on Object {
    AppLog.event('rescue_transfer_failed');
    messenger.showSnackBar(SnackBar(content: Text(l10n.genericError)));
  }
}

/// «Qutqarilgan pul» (SPEC 2B.7): hafta va oy, tarkibi, bazaviy oy.
class RescueScreen extends ConsumerWidget {
  const RescueScreen({super.key});

  Future<void> _pickBaseline(BuildContext context, WidgetRef ref) async {
    final household = await (await ref.read(
      householdServiceProvider.future,
    )).household();
    if (!context.mounted) return;
    final calendar = household.calendar;
    var month = calendar.monthOf(
      Tashkent.dateOf(ref.read(clockProvider).nowUtc()),
    );
    final months = <DateRange>[];
    for (var i = 0; i < 12; i++) {
      month = calendar.monthOf(month.start.plusDays(-1));
      months.add(month);
    }
    final picked = await showDialog<DateRange>(
      context: context,
      builder: (context) => SimpleDialog(
        title: Text(context.l10n.rescueBaselinePick),
        children: [
          for (final m in months)
            SimpleDialogOption(
              onPressed: () => Navigator.pop(context, m),
              child: Text(periodLabel(context, m)),
            ),
        ],
      ),
    );
    if (picked == null) return;
    await (await ref.read(rescueServiceProvider.future)).setBaseline(
      picked.start,
    );
    ref.invalidate(rescueOverviewProvider);
  }

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final l10n = context.l10n;
    final overview = ref.watch(rescueOverviewProvider);
    return Scaffold(
      appBar: AppBar(title: Text(l10n.rescueTitle)),
      body: switch (overview) {
        AsyncData(:final value) => ListView(
          padding: const EdgeInsets.fromLTRB(16, 8, 16, 32),
          children: [
            _BreakdownCard(
              key: const Key('rescue-week'),
              title: l10n.rescueThisWeek,
              b: value.week,
            ),
            if (value.week.available.isPositive)
              Padding(
                padding: const EdgeInsets.only(top: 8),
                child: FilledButton.icon(
                  key: const Key('rescue-transfer'),
                  icon: const Icon(Icons.account_balance_wallet_outlined),
                  label: Text(
                    l10n.rescueTransfer(context.money(value.week.available)),
                  ),
                  onPressed: () => transferRescue(context, ref),
                ),
              ),
            const SizedBox(height: 12),
            _BreakdownCard(
              key: const Key('rescue-month'),
              title: l10n.rescueThisMonth,
              b: value.month,
            ),
            const SizedBox(height: 12),
            Text(
              value.baseline == null
                  ? l10n.rescueNoBaseline
                  : l10n.rescueBaseline(periodLabel(context, value.baseline!)),
              key: const Key('rescue-baseline'),
            ),
            Align(
              alignment: Alignment.centerLeft,
              child: TextButton(
                key: const Key('rescue-baseline-pick'),
                onPressed: () => _pickBaseline(context, ref),
                child: Text(l10n.rescueBaselinePick),
              ),
            ),
            Text(
              l10n.rescueFormula,
              style: Theme.of(context).textTheme.bodySmall,
            ),
          ],
        ),
        AsyncError() => Center(child: Text(l10n.genericError)),
        _ => const Center(child: CircularProgressIndicator()),
      },
    );
  }
}

class _BreakdownCard extends StatelessWidget {
  const _BreakdownCard({required this.title, required this.b, super.key});

  final String title;
  final RescueBreakdown b;

  @override
  Widget build(BuildContext context) {
    final l10n = context.l10n;
    final theme = Theme.of(context);
    final money = context.money;
    Widget row(String label, Money amount) => Padding(
      padding: const EdgeInsets.symmetric(vertical: 2),
      child: Row(
        children: [
          Expanded(child: Text(label)),
          Text(money(amount)),
        ],
      ),
    );
    return Card(
      child: Padding(
        padding: const EdgeInsets.all(16),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text(title, style: theme.textTheme.titleSmall),
            Text(
              money(b.total),
              style: theme.textTheme.headlineSmall?.copyWith(
                color: theme.colorScheme.primary,
              ),
            ),
            const SizedBox(height: 8),
            if (b.hasBaseline) row(l10n.rescueHavas, b.havasShown),
            row(l10n.rescueSubscriptions, b.subscriptions),
            row(l10n.rescueEnvelopes, b.envelopes),
            if (b.transferred.isPositive)
              row(l10n.rescueTransferredLine, b.transferred),
            if (b.spentMore)
              Padding(
                padding: const EdgeInsets.only(top: 8),
                child: Text(
                  l10n.rescueSpentMore,
                  style: theme.textTheme.bodySmall,
                ),
              ),
          ],
        ),
      ),
    );
  }
}
