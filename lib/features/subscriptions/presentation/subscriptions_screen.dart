import 'package:baraka_daftari/app/l10n/l10n.dart';
import 'package:baraka_daftari/app/refresh.dart';
import 'package:baraka_daftari/app/widgets/labels.dart';
import 'package:baraka_daftari/app/widgets/money_input.dart';
import 'package:baraka_daftari/core/domain/enums.dart';
import 'package:baraka_daftari/core/logging/app_log.dart';
import 'package:baraka_daftari/core/money/money.dart';
import 'package:baraka_daftari/features/content/data/content_providers.dart';
import 'package:baraka_daftari/features/content/domain/content.dart';
import 'package:baraka_daftari/features/subscriptions/data/subscription_providers.dart';
import 'package:baraka_daftari/features/subscriptions/domain/subscription.dart';
import 'package:baraka_daftari/features/subscriptions/domain/subscription_service.dart';
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

/// Obunalar auditi (SPEC 2B.5): yillik narx, «Kerakmi?», unutilgan obuna.
class SubscriptionsScreen extends ConsumerWidget {
  const SubscriptionsScreen({super.key});

  Future<void> _act(
    WidgetRef ref,
    Future<void> Function(SubscriptionService s) action,
  ) async {
    try {
      await action(await ref.read(subscriptionServiceProvider.future));
      refreshMoneyViews(ref);
      await recordTaskEvent(ref, TaskTrigger.subscriptionsReviewed);
    } on Object {
      AppLog.event('subscription_action_failed');
    }
  }

  Future<void> _add(BuildContext context, WidgetRef ref) async {
    final l10n = context.l10n;
    final result = await showDialog<(String, SubscriptionCycle)>(
      context: context,
      builder: (_) => const _AddDialog(),
    );
    if (result == null || !context.mounted) return;
    final price = await showAmountSheet(
      context,
      currency: CurrencyCode.uzs,
      title: result.$1,
    );
    if (price == null || !price.isPositive) return;
    try {
      await (await ref.read(
        subscriptionServiceProvider.future,
      )).add(title: result.$1, price: price, cycle: result.$2);
      refreshMoneyViews(ref);
    } on Object {
      AppLog.event('subscription_add_failed');
      if (context.mounted) {
        ScaffoldMessenger.of(
          context,
        ).showSnackBar(SnackBar(content: Text(l10n.genericError)));
      }
    }
  }

  Future<void> _cancel(
    BuildContext context,
    WidgetRef ref,
    Subscription s,
  ) async {
    final l10n = context.l10n;
    final ok = await showDialog<bool>(
      context: context,
      builder: (context) => AlertDialog(
        content: Text(
          l10n.subscriptionCancelConfirm(s.title, context.money(s.yearly)),
        ),
        actions: [
          // «Bekor qilish» emas — «Bekor qildim» bilan adashmasin.
          TextButton(
            key: const Key('subscription-cancel-no'),
            onPressed: () => Navigator.pop(context, false),
            child: Text(l10n.notNow),
          ),
          FilledButton(
            key: const Key('subscription-cancel-ok'),
            onPressed: () => Navigator.pop(context, true),
            child: Text(l10n.subscriptionCancel),
          ),
        ],
      ),
    );
    if (ok ?? false) await _act(ref, (svc) => svc.cancel(s));
  }

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final l10n = context.l10n;
    final theme = Theme.of(context);
    final money = context.money;
    final list = ref.watch(subscriptionsProvider);
    final service = ref.watch(subscriptionServiceProvider).valueOrNull;
    return Scaffold(
      appBar: AppBar(title: Text(l10n.subscriptionsTitle)),
      floatingActionButton: FloatingActionButton.extended(
        key: const Key('subscription-add'),
        icon: const Icon(Icons.add),
        label: Text(l10n.subscriptionAdd),
        onPressed: () => _add(context, ref),
      ),
      body: switch (list) {
        AsyncData(:final value) when value.isEmpty => Center(
          child: Padding(
            padding: const EdgeInsets.all(24),
            child: Text(l10n.subscriptionsEmpty, textAlign: TextAlign.center),
          ),
        ),
        AsyncData(:final value) => ListView(
          padding: const EdgeInsets.fromLTRB(16, 8, 16, 96),
          children: [
            Text(l10n.subscriptionsHint),
            const SizedBox(height: 8),
            Text(
              l10n.subscriptionsAnnualTotal(
                money(SubscriptionService.annualTotal(value, CurrencyCode.uzs)),
              ),
              key: const Key('subscriptions-annual'),
              style: theme.textTheme.titleMedium,
            ),
            const SizedBox(height: 8),
            for (final s in value.where((s) => s.isActive))
              Card(
                key: Key('subscription-${s.meta.id}'),
                child: Padding(
                  padding: const EdgeInsets.fromLTRB(16, 12, 8, 4),
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Text(s.title, style: theme.textTheme.titleSmall),
                      Text(
                        l10n.subscriptionLine(
                          '${money(s.price)} · ${switch (s.cycle) {
                            SubscriptionCycle.monthly => l10n.cycleMonthly,
                            SubscriptionCycle.yearly => l10n.cycleYearly,
                          }}',
                          money(s.yearly),
                        ),
                      ),
                      if (service != null && service.isForgotten(s))
                        Text(
                          l10n.subscriptionForgotten(
                            s.daysSinceUse(service.today),
                          ),
                          key: Key('subscription-forgotten-${s.meta.id}'),
                          style: TextStyle(color: theme.colorScheme.tertiary),
                        )
                      else if (s.lastUsedOn != null)
                        Text(
                          l10n.subscriptionLastUsed(formatDate(s.lastUsedOn!)),
                          style: theme.textTheme.bodySmall,
                        ),
                      OverflowBar(
                        alignment: MainAxisAlignment.end,
                        children: [
                          TextButton(
                            key: Key('subscription-used-${s.meta.id}'),
                            onPressed: () =>
                                _act(ref, (svc) => svc.markUsed(s)),
                            child: Text(l10n.subscriptionUsed),
                          ),
                          TextButton(
                            key: Key('subscription-cancel-${s.meta.id}'),
                            onPressed: () => _cancel(context, ref, s),
                            child: Text(l10n.subscriptionCancel),
                          ),
                        ],
                      ),
                    ],
                  ),
                ),
              ),
            if (value.any((s) => !s.isActive)) ...[
              const SizedBox(height: 12),
              Text(
                l10n.subscriptionsCancelledHeader,
                style: theme.textTheme.titleSmall,
              ),
              for (final s in value.where((s) => !s.isActive))
                ListTile(
                  key: Key('subscription-cancelled-${s.meta.id}'),
                  contentPadding: EdgeInsets.zero,
                  leading: const Icon(Icons.check_circle_outline),
                  title: Text(s.title),
                  subtitle: Text(
                    l10n.subscriptionCancelledLine(money(s.yearly)),
                  ),
                ),
            ],
          ],
        ),
        AsyncError() => Center(child: Text(l10n.genericError)),
        _ => const Center(child: CircularProgressIndicator()),
      },
    );
  }
}

class _AddDialog extends StatefulWidget {
  const _AddDialog();

  @override
  State<_AddDialog> createState() => _AddDialogState();
}

class _AddDialogState extends State<_AddDialog> {
  final _title = TextEditingController();
  SubscriptionCycle _cycle = SubscriptionCycle.monthly;

  @override
  void dispose() {
    _title.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    final l10n = context.l10n;
    return AlertDialog(
      title: Text(l10n.subscriptionAdd),
      content: Column(
        mainAxisSize: MainAxisSize.min,
        children: [
          TextField(
            key: const Key('subscription-title'),
            controller: _title,
            autofocus: true,
            decoration: InputDecoration(labelText: l10n.titleLabel),
            onChanged: (_) => setState(() {}),
          ),
          const SizedBox(height: 12),
          SegmentedButton<SubscriptionCycle>(
            showSelectedIcon: false,
            segments: [
              ButtonSegment(
                value: SubscriptionCycle.monthly,
                label: Text(l10n.cycleMonthly),
              ),
              ButtonSegment(
                value: SubscriptionCycle.yearly,
                label: Text(l10n.cycleYearly),
              ),
            ],
            selected: {_cycle},
            onSelectionChanged: (s) => setState(() => _cycle = s.single),
          ),
        ],
      ),
      actions: [
        TextButton(
          onPressed: () => Navigator.pop(context),
          child: Text(l10n.cancel),
        ),
        FilledButton(
          key: const Key('subscription-next'),
          onPressed: _title.text.trim().isEmpty
              ? null
              : () => Navigator.pop(context, (_title.text.trim(), _cycle)),
          child: Text(l10n.save),
        ),
      ],
    );
  }
}
