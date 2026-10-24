import 'package:baraka_daftari/app/l10n/l10n.dart';
import 'package:baraka_daftari/app/refresh.dart';
import 'package:baraka_daftari/app/router/app_routes.dart';
import 'package:baraka_daftari/app/widgets/money_input.dart';
import 'package:baraka_daftari/core/logging/app_log.dart';
import 'package:baraka_daftari/features/content/data/content_providers.dart';
import 'package:baraka_daftari/features/content/domain/content.dart';
import 'package:baraka_daftari/features/vault/data/vault_providers.dart';
import 'package:baraka_daftari/features/vault/domain/vault_service.dart';
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';

/// O'ndan birlarni «1,4» ko'rinishiga.
String monthsLabel(int tenths) =>
    tenths % 10 == 0 ? '${tenths ~/ 10}' : '${tenths ~/ 10},${tenths % 10}';

/// Qorovul pul (zaxira progressi) va o'sadigan pul (tayyorgarlik
/// darvozasi) — SPEC 2C.3–2C.4.
class ReserveGrowthSection extends ConsumerWidget {
  const ReserveGrowthSection({required this.overview, super.key});

  final VaultOverview overview;

  Future<void> _estimate(BuildContext context, WidgetRef ref) async {
    final amount = await showAmountSheet(
      context,
      currency: overview.household.baseCurrency,
      title: context.l10n.reserveEstimateTitle,
    );
    if (amount == null || !amount.isPositive) return;
    await (await ref.read(
      essentialSpendServiceProvider.future,
    )).setEstimate(amount);
    refreshMoneyViews(ref);
  }

  Future<void> _deposit(BuildContext context, WidgetRef ref) async {
    final l10n = context.l10n;
    final messenger = ScaffoldMessenger.of(context);
    var bypass = false;
    if (!overview.gate.isOpen) {
      final ok = await showDialog<bool>(
        context: context,
        builder: (context) => AlertDialog(
          title: Text(l10n.gateBypassTitle),
          content: Text(l10n.gateBypassWarning),
          actions: [
            TextButton(
              onPressed: () => Navigator.pop(context, false),
              child: Text(l10n.notNow),
            ),
            FilledButton(
              key: const Key('gate-bypass-confirm'),
              onPressed: () => Navigator.pop(context, true),
              child: Text(l10n.gateBypassConfirm),
            ),
          ],
        ),
      );
      if (!(ok ?? false)) return;
      bypass = true;
      AppLog.event('gate_bypassed');
    }
    if (!context.mounted) return;
    final amount = await showAmountSheet(
      context,
      currency: overview.household.baseCurrency,
      title: l10n.growthDepositTitle,
    );
    if (amount == null || !amount.isPositive) return;
    try {
      await (await ref.read(
        vaultServiceProvider.future,
      )).depositGrowth(amount, bypassConfirmed: bypass);
      refreshMoneyViews(ref);
      await recordTaskEvent(ref, TaskTrigger.vaultFirstDeposit);
    } on Object {
      AppLog.event('growth_deposit_failed');
      messenger.showSnackBar(SnackBar(content: Text(l10n.genericError)));
    }
  }

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final l10n = context.l10n;
    final theme = Theme.of(context);
    final money = context.money;
    final reserve = overview.reserve;
    final gate = overview.gate;
    final months = monthsLabel(reserve.monthsTenths);
    Widget condition(String text, {required bool done}) => Row(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Icon(
          done ? Icons.check_circle : Icons.radio_button_unchecked,
          size: 20,
          color: done ? theme.colorScheme.primary : theme.colorScheme.outline,
        ),
        const SizedBox(width: 8),
        Expanded(child: Text(text)),
      ],
    );
    return Column(
      crossAxisAlignment: CrossAxisAlignment.stretch,
      children: [
        Card(
          key: const Key('reserve-card'),
          child: Padding(
            padding: const EdgeInsets.all(16),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Row(
                  children: [
                    const Icon(Icons.shield_outlined),
                    const SizedBox(width: 8),
                    Expanded(
                      child: Text(
                        l10n.reserveTitle,
                        style: theme.textTheme.titleMedium,
                      ),
                    ),
                    Text(
                      money(overview.reserveBalance),
                      key: const Key('reserve-balance'),
                      style: theme.textTheme.titleMedium,
                    ),
                  ],
                ),
                Text(l10n.reserveHint, style: theme.textTheme.bodySmall),
                const SizedBox(height: 8),
                if (reserve.needsEstimate) ...[
                  Text(l10n.reserveNeedsEstimate),
                  Align(
                    alignment: Alignment.centerLeft,
                    child: TextButton(
                      key: const Key('reserve-estimate'),
                      onPressed: () => _estimate(context, ref),
                      child: Text(l10n.reserveEstimateAction),
                    ),
                  ),
                ] else ...[
                  Text(
                    l10n.reserveMonths(months),
                    key: const Key('reserve-months'),
                    style: theme.textTheme.headlineSmall,
                  ),
                  const SizedBox(height: 4),
                  LinearProgressIndicator(
                    value: (reserve.monthsTenths / 60).clamp(0, 1).toDouble(),
                    minHeight: 8,
                    borderRadius: BorderRadius.circular(4),
                  ),
                  const SizedBox(height: 4),
                  Text(
                    l10n.reserveTarget(
                      money(reserve.target!),
                      money(reserve.monthlyEssential!),
                    ),
                    style: theme.textTheme.bodySmall,
                  ),
                  if (reserve.fromEstimate)
                    Text(
                      l10n.reserveFromEstimate,
                      style: theme.textTheme.bodySmall,
                    ),
                  if (reserve.isFull)
                    Text(l10n.reserveFull, key: const Key('reserve-full'))
                  else if (reserve.firstMilestoneReached)
                    Text(l10n.reserveMilestone3),
                ],
              ],
            ),
          ),
        ),
        const SizedBox(height: 12),
        Card(
          key: const Key('growth-card'),
          child: Padding(
            padding: const EdgeInsets.all(16),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Row(
                  children: [
                    Icon(gate.isOpen ? Icons.trending_up : Icons.lock_outline),
                    const SizedBox(width: 8),
                    Expanded(
                      child: Text(
                        l10n.growthTitle,
                        style: theme.textTheme.titleMedium,
                      ),
                    ),
                    Text(
                      money(overview.growthBalance),
                      key: const Key('growth-balance'),
                      style: theme.textTheme.titleMedium,
                    ),
                  ],
                ),
                Text(l10n.growthHint, style: theme.textTheme.bodySmall),
                const SizedBox(height: 8),
                if (!gate.ready) ...[
                  Text(l10n.gateTitle, style: theme.textTheme.titleSmall),
                  Text(l10n.gateHint, style: theme.textTheme.bodySmall),
                  const SizedBox(height: 6),
                  condition(
                    l10n.gateReserve(months),
                    done: gate.reserveReady,
                  ),
                  const SizedBox(height: 4),
                  condition(l10n.gateDebt, done: gate.debtReady),
                  if (gate.bypassed)
                    Padding(
                      padding: const EdgeInsets.only(top: 6),
                      child: Text(
                        l10n.gateBypassed,
                        style: TextStyle(color: theme.colorScheme.tertiary),
                      ),
                    ),
                ] else
                  Text(l10n.gateOpen, key: const Key('gate-open')),
                const SizedBox(height: 8),
                Wrap(
                  spacing: 8,
                  children: [
                    if (gate.isOpen)
                      FilledButton.tonal(
                        key: const Key('growth-deposit'),
                        onPressed: () => _deposit(context, ref),
                        child: Text(l10n.growthDeposit),
                      )
                    else
                      OutlinedButton(
                        key: const Key('growth-bypass'),
                        onPressed: () => _deposit(context, ref),
                        child: Text(l10n.gateBypass),
                      ),
                    TextButton(
                      key: const Key('vault-mouse'),
                      onPressed: () => context.push(AppRoutes.mouse),
                      child: Text(l10n.mouseTitle),
                    ),
                  ],
                ),
              ],
            ),
          ),
        ),
      ],
    );
  }
}
