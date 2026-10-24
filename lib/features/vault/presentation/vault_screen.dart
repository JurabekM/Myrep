import 'dart:async';

import 'package:baraka_daftari/app/l10n/l10n.dart';
import 'package:baraka_daftari/app/refresh.dart';
import 'package:baraka_daftari/app/router/app_routes.dart';
import 'package:baraka_daftari/app/widgets/money_input.dart';
import 'package:baraka_daftari/app/widgets/settings_actions.dart';
import 'package:baraka_daftari/core/domain/enums.dart';
import 'package:baraka_daftari/core/logging/app_log.dart';
import 'package:baraka_daftari/core/time/calendar.dart';
import 'package:baraka_daftari/features/content/data/content_providers.dart';
import 'package:baraka_daftari/features/content/domain/content.dart';
import 'package:baraka_daftari/features/vault/data/vault_providers.dart';
import 'package:baraka_daftari/features/vault/domain/vault.dart';
import 'package:baraka_daftari/features/vault/domain/vault_service.dart';
import 'package:baraka_daftari/features/vault/presentation/reserve_section.dart';
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';

/// «Kelajagim» (SPEC 2.2): avval odat ko'rsatkichi, keyin balans va tarix.
class VaultScreen extends ConsumerStatefulWidget {
  const VaultScreen({super.key});

  @override
  ConsumerState<VaultScreen> createState() => _VaultScreenState();
}

class _VaultScreenState extends ConsumerState<VaultScreen> {
  @override
  void initState() {
    super.initState();
    // Haftalik vazifa: «Kelajagim» kartasi ochildi.
    unawaited(recordTaskEvent(ref, TaskTrigger.vaultOpened));
  }

  @override
  Widget build(BuildContext context) {
    final l10n = context.l10n;
    final overview = ref.watch(vaultOverviewProvider);
    return Scaffold(
      appBar: AppBar(
        title: Text(l10n.vaultTitle),
        actions: const [SettingsActions()],
      ),
      body: switch (overview) {
        AsyncData(:final value) => _VaultBody(value),
        AsyncError() => Center(child: Text(l10n.genericError)),
        _ => const Center(child: CircularProgressIndicator()),
      },
    );
  }
}

/// `500` → `5`, `650` → `6,5`.
String percentText(int basisPoints) {
  final whole = basisPoints ~/ 100;
  final rest = basisPoints % 100;
  if (rest == 0) return '$whole';
  final frac = rest.toString().padLeft(2, '0').replaceFirst(RegExp(r'0$'), '');
  return '$whole,$frac';
}

class _VaultBody extends ConsumerWidget {
  const _VaultBody(this.o);

  final VaultOverview o;

  Future<void> _run(
    BuildContext context,
    WidgetRef ref,
    Future<void> Function(VaultService) action, {
    String? done,
  }) async {
    final messenger = ScaffoldMessenger.of(context);
    final error = context.l10n.genericError;
    try {
      await action(await ref.read(vaultServiceProvider.future));
      refreshMoneyViews(ref);
      if (done != null) {
        messenger.showSnackBar(SnackBar(content: Text(done)));
      }
    } on Object {
      AppLog.event('vault_action_failed');
      messenger.showSnackBar(SnackBar(content: Text(error)));
    }
  }

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final l10n = context.l10n;
    final theme = Theme.of(context);
    final scheme = theme.colorScheme;
    final rule = o.rule;
    final ruleText = rule.fixedAmount != null && rule.basisPoints == null
        ? l10n.vaultRuleSummaryFixed(context.money(rule.fixedAmount!))
        : l10n.vaultRuleSummaryPercent(
            percentText(rule.basisPoints ?? VaultService.defaultBasisPoints),
          );
    final offer = o.progressionOffer;

    return Center(
      child: ConstrainedBox(
        constraints: const BoxConstraints(maxWidth: 620),
        child: ListView(
          padding: const EdgeInsets.all(16),
          children: [
            // 1. Odat — miqdordan oldin.
            Card(
              key: const Key('vault-habit'),
              color: scheme.primaryContainer,
              child: Padding(
                padding: const EdgeInsets.all(20),
                child: Column(
                  children: [
                    Text(
                      l10n.vaultHabitWeeks(o.habit.currentStreakWeeks),
                      key: const Key('vault-streak'),
                      style: theme.textTheme.displaySmall?.copyWith(
                        color: scheme.onPrimaryContainer,
                        fontWeight: FontWeight.w600,
                      ),
                    ),
                    Text(
                      l10n.vaultHabitCaption,
                      style: theme.textTheme.titleMedium?.copyWith(
                        color: scheme.onPrimaryContainer,
                      ),
                    ),
                    const SizedBox(height: 8),
                    Text(
                      o.habit.thisWeekDone
                          ? l10n.vaultThisWeekDone
                          : l10n.vaultThisWeekPending,
                      textAlign: TextAlign.center,
                      style: theme.textTheme.bodyMedium?.copyWith(
                        color: scheme.onPrimaryContainer,
                      ),
                    ),
                    Text(
                      l10n.vaultHabitTotal(o.habit.totalWeeks),
                      style: theme.textTheme.bodySmall?.copyWith(
                        color: scheme.onPrimaryContainer,
                      ),
                    ),
                  ],
                ),
              ),
            ),
            const SizedBox(height: 12),
            if (offer != null) ...[
              Card(
                key: const Key('vault-progression'),
                color: scheme.tertiaryContainer,
                child: Padding(
                  padding: const EdgeInsets.fromLTRB(16, 12, 8, 4),
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Text(
                        l10n.vaultProgressionTitle,
                        style: theme.textTheme.titleSmall?.copyWith(
                          color: scheme.onTertiaryContainer,
                        ),
                      ),
                      Text(
                        l10n.vaultProgressionBody(
                          VaultService.weeksForProgression,
                          percentText(offer),
                        ),
                        style: TextStyle(color: scheme.onTertiaryContainer),
                      ),
                      OverflowBar(
                        alignment: MainAxisAlignment.end,
                        children: [
                          TextButton(
                            key: const Key('progression-decline'),
                            onPressed: () => _run(
                              context,
                              ref,
                              (s) => s.answerProgression(accept: false),
                            ),
                            child: Text(l10n.vaultProgressionDecline),
                          ),
                          FilledButton(
                            key: const Key('progression-accept'),
                            onPressed: () => _run(
                              context,
                              ref,
                              (s) => s.answerProgression(accept: true),
                              done: l10n.ruleSaved,
                            ),
                            child: Text(l10n.vaultProgressionAccept),
                          ),
                        ],
                      ),
                    ],
                  ),
                ),
              ),
              const SizedBox(height: 12),
            ],
            // 2. Balans va qoida.
            Card(
              child: Padding(
                padding: const EdgeInsets.all(16),
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text(
                      l10n.vaultBalanceLabel,
                      style: theme.textTheme.labelLarge,
                    ),
                    const SizedBox(height: 4),
                    FittedBox(
                      fit: BoxFit.scaleDown,
                      alignment: Alignment.centerLeft,
                      child: Text(
                        context.money(o.balance),
                        key: const Key('vault-balance'),
                        style: theme.textTheme.headlineMedium,
                      ),
                    ),
                    const SizedBox(height: 8),
                    Text(
                      rule.mode == AllocationMode.progressive
                          ? '$ruleText · ${l10n.vaultRuleProgressiveTag}'
                          : ruleText,
                      key: const Key('vault-rule'),
                      style: theme.textTheme.bodyMedium,
                    ),
                    const SizedBox(height: 8),
                    Wrap(
                      spacing: 8,
                      runSpacing: 8,
                      children: [
                        OutlinedButton.icon(
                          key: const Key('vault-edit-rule'),
                          icon: const Icon(Icons.tune),
                          label: Text(l10n.vaultRuleEdit),
                          onPressed: () => context.push(AppRoutes.vaultRule),
                        ),
                        OutlinedButton.icon(
                          key: const Key('vault-withdraw'),
                          icon: const Icon(Icons.outbox_outlined),
                          label: Text(l10n.vaultWithdraw),
                          onPressed: o.balance.isPositive
                              ? () => context.push(AppRoutes.vaultWithdraw)
                              : null,
                        ),
                        OutlinedButton.icon(
                          key: const Key('vault-lump-sum'),
                          icon: const Icon(Icons.fort_outlined),
                          label: Text(l10n.lumpOpen),
                          onPressed: () => context.push(AppRoutes.vaultLumpSum),
                        ),
                      ],
                    ),
                  ],
                ),
              ),
            ),
            // 3. Qorovul / o'sadigan (SPEC 2C.3–2C.4).
            const SizedBox(height: 12),
            ReserveGrowthSection(overview: o),
            if (!o.hasInitialBalance) ...[
              const SizedBox(height: 12),
              Card(
                key: const Key('vault-initial'),
                child: Padding(
                  padding: const EdgeInsets.fromLTRB(16, 12, 8, 4),
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Text(
                        l10n.vaultInitialTitle,
                        style: theme.textTheme.titleSmall,
                      ),
                      const SizedBox(height: 4),
                      Text(l10n.vaultInitialBody),
                      Align(
                        alignment: Alignment.centerRight,
                        child: TextButton(
                          key: const Key('vault-initial-action'),
                          onPressed: () async {
                            final amount = await showAmountSheet(
                              context,
                              currency: o.household.baseCurrency,
                              title: l10n.vaultInitialTitle,
                            );
                            if (amount == null || !context.mounted) return;
                            await _run(
                              context,
                              ref,
                              (s) => s.setInitialBalance(amount),
                              done: l10n.vaultInitialSaved,
                            );
                          },
                          child: Text(l10n.vaultInitialAction),
                        ),
                      ),
                    ],
                  ),
                ),
              ),
            ],
            const SizedBox(height: 20),
            Text(l10n.vaultHistory, style: theme.textTheme.titleMedium),
            const SizedBox(height: 4),
            if (o.history.isEmpty)
              Padding(
                padding: const EdgeInsets.symmetric(vertical: 12),
                child: Text(
                  l10n.vaultHistoryEmpty,
                  style: TextStyle(color: scheme.onSurfaceVariant),
                ),
              )
            else
              Card(
                child: Column(
                  children: [
                    for (final (i, t) in o.history.indexed) ...[
                      if (i > 0) const Divider(height: 1),
                      _HistoryTile(t),
                    ],
                  ],
                ),
              ),
          ],
        ),
      ),
    );
  }
}

class _HistoryTile extends StatelessWidget {
  const _HistoryTile(this.t);

  final VaultTransaction t;

  @override
  Widget build(BuildContext context) {
    final l10n = context.l10n;
    final theme = Theme.of(context);
    final deposit = t.type == VaultTransactionType.deposit;
    final title = switch (t.reason) {
      VaultTransactionReason.incomeShare => l10n.vaultReasonIncomeShare,
      VaultTransactionReason.initial => l10n.vaultReasonInitial,
      VaultTransactionReason.manual => l10n.vaultReasonManual,
      VaultTransactionReason.rescue => l10n.vaultReasonRescue,
      VaultTransactionReason.withdrawal => l10n.vaultReasonWithdrawal(
        t.reasonNote ?? '',
      ),
    };
    final date = Tashkent.dateOf(t.occurredAt);
    final dateText =
        '${date.day.toString().padLeft(2, '0')}.'
        '${date.month.toString().padLeft(2, '0')}.${date.year}';
    final amount = context.money(t.amount);
    return ListTile(
      leading: Icon(
        deposit ? Icons.south_west : Icons.north_east,
        color: deposit ? theme.colorScheme.primary : theme.colorScheme.outline,
      ),
      title: Text(title),
      subtitle: Text(dateText),
      trailing: Text(
        deposit ? '+$amount' : '−$amount',
        style: theme.textTheme.titleSmall,
      ),
    );
  }
}
