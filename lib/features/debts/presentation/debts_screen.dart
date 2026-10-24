import 'package:baraka_daftari/app/l10n/l10n.dart';
import 'package:baraka_daftari/app/refresh.dart';
import 'package:baraka_daftari/app/router/app_routes.dart';
import 'package:baraka_daftari/app/widgets/labels.dart';
import 'package:baraka_daftari/app/widgets/money_input.dart';
import 'package:baraka_daftari/app/widgets/text_prompt.dart';
import 'package:baraka_daftari/core/logging/app_log.dart';
import 'package:baraka_daftari/core/money/money.dart';
import 'package:baraka_daftari/core/time/calendar.dart';
import 'package:baraka_daftari/core/time/clock.dart';
import 'package:baraka_daftari/features/content/data/content_providers.dart';
import 'package:baraka_daftari/features/content/domain/content.dart';
import 'package:baraka_daftari/features/debts/data/debt_providers.dart';
import 'package:baraka_daftari/features/debts/domain/debt_service.dart';
import 'package:baraka_daftari/features/debts/domain/debts.dart';
import 'package:baraka_daftari/features/debts/domain/payoff.dart';
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';

/// Qarz inventari (SPEC 2C.7): «Qarz — teshik emas, yara».
class DebtsScreen extends ConsumerWidget {
  const DebtsScreen({super.key});

  Future<void> _lend(BuildContext context, WidgetRef ref) async {
    final today = Tashkent.dateOf(ref.read(clockProvider).nowUtc());
    final draft = await showDialog<(String, LocalDate)>(
      context: context,
      builder: (_) => _LendDialog(initialDue: today.plusDays(30)),
    );
    if (draft == null || !context.mounted) return;
    final amount = await showAmountSheet(
      context,
      currency: CurrencyCode.uzs,
      title: context.l10n.lendTitle,
    );
    if (amount == null || !amount.isPositive) return;
    try {
      await (await ref.read(debtServiceProvider.future)).lend(
        debtorName: draft.$1,
        amount: amount,
        dueDate: draft.$2,
      );
      refreshMoneyViews(ref);
    } on Object {
      AppLog.event('lend_failed');
    }
  }

  Future<void> _receive(
    BuildContext context,
    WidgetRef ref,
    Receivable r,
  ) async {
    final amount = await showAmountSheet(
      context,
      currency: r.remaining.currency,
      title: context.l10n.lendReceive,
      initial: r.remaining,
      max: r.remaining,
    );
    if (amount == null || !amount.isPositive) return;
    await (await ref.read(debtServiceProvider.future)).receive(r, amount);
    refreshMoneyViews(ref);
  }

  Future<void> _addGoal(BuildContext context, WidgetRef ref) async {
    final l10n = context.l10n;
    final title = await showTextPrompt(
      context,
      title: l10n.goalAdd,
      label: l10n.titleLabel,
      fieldKey: const Key('goal-title'),
      okKey: const Key('goal-next'),
    );
    if (title == null || title.trim().isEmpty || !context.mounted) return;
    final target = await showAmountSheet(
      context,
      currency: CurrencyCode.uzs,
      title: l10n.goalTargetTitle,
    );
    if (target == null || !target.isPositive) return;
    await (await ref.read(debtServiceProvider.future)).addGoal(title, target);
    refreshMoneyViews(ref);
  }

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final l10n = context.l10n;
    final theme = Theme.of(context);
    final money = context.money;
    final overview = ref.watch(debtOverviewProvider);
    return Scaffold(
      appBar: AppBar(title: Text(l10n.debtsTitle)),
      floatingActionButton: FloatingActionButton.extended(
        key: const Key('debt-add'),
        icon: const Icon(Icons.add),
        label: Text(l10n.debtAdd),
        onPressed: () async {
          await context.push(AppRoutes.debtNew);
          refreshMoneyViews(ref);
        },
      ),
      body: switch (overview) {
        AsyncData(:final value) => ListView(
          padding: const EdgeInsets.fromLTRB(16, 8, 16, 96),
          children: [
            Text(l10n.debtsHint),
            const SizedBox(height: 8),
            Card(
              key: const Key('debts-summary'),
              child: Padding(
                padding: const EdgeInsets.all(16),
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text(
                      l10n.debtsTotal(money(value.totalDebt)),
                      style: theme.textTheme.titleMedium,
                    ),
                    Text(
                      value.loadBp == null
                          ? l10n.debtsLoadUnknown(money(value.monthlyPayments))
                          : l10n.debtsLoad(
                              money(value.monthlyPayments),
                              percentLabel(value.loadBp!),
                            ),
                      key: const Key('debts-load'),
                    ),
                    if (value.totalReceivable.isPositive)
                      Text(l10n.debtsLentTotal(money(value.totalReceivable))),
                    if (debtFreeDay(value) case final day?)
                      Text(
                        l10n.debtFreeOn(formatDate(day)),
                        key: const Key('debts-free-day'),
                      ),
                  ],
                ),
              ),
            ),
            const _RecoveryCard(),
            if (value.debts.isNotEmpty)
              Wrap(
                spacing: 8,
                children: [
                  OutlinedButton.icon(
                    key: const Key('debts-plan'),
                    icon: const Icon(Icons.timeline),
                    label: Text(l10n.payoffTitle),
                    onPressed: () => context.push(AppRoutes.debtPlan),
                  ),
                  OutlinedButton.icon(
                    key: const Key('debts-sellables'),
                    icon: const Icon(Icons.sell_outlined),
                    label: Text(l10n.sellablesTitle),
                    onPressed: () => context.push(AppRoutes.sellables),
                  ),
                ],
              ),
            const SizedBox(height: 12),
            Text(l10n.debtsBorrowed, style: theme.textTheme.titleSmall),
            if (value.debts.isEmpty)
              Padding(
                padding: const EdgeInsets.symmetric(vertical: 12),
                child: Text(l10n.debtsEmpty),
              ),
            for (final v in value.debts) _DebtTile(view: v),
            const SizedBox(height: 12),
            Row(
              children: [
                Expanded(
                  child: Text(
                    l10n.debtsLent,
                    style: theme.textTheme.titleSmall,
                  ),
                ),
                TextButton(
                  key: const Key('debt-lend'),
                  onPressed: () => _lend(context, ref),
                  child: Text(l10n.debtLend),
                ),
              ],
            ),
            for (final r in value.receivables)
              Card(
                key: Key('receivable-${r.meta.id}'),
                child: ListTile(
                  title: Text(r.debtorName),
                  subtitle: Text(
                    '${money(r.remaining)} · ${formatDate(r.dueDate)}',
                  ),
                  trailing: Wrap(
                    children: [
                      IconButton(
                        key: Key('receivable-receipt-${r.meta.id}'),
                        tooltip: l10n.debtReceipt,
                        icon: const Icon(Icons.description_outlined),
                        onPressed: () => context.push(
                          AppRoutes.receivableReceipt(r.meta.id),
                        ),
                      ),
                      TextButton(
                        key: Key('receivable-back-${r.meta.id}'),
                        onPressed: () => _receive(context, ref, r),
                        child: Text(l10n.lendReceive),
                      ),
                    ],
                  ),
                ),
              ),
            const SizedBox(height: 12),
            Row(
              children: [
                Expanded(
                  child: Text(
                    l10n.debtsGoals,
                    style: theme.textTheme.titleSmall,
                  ),
                ),
                TextButton(
                  key: const Key('goal-add'),
                  onPressed: () => _addGoal(context, ref),
                  child: Text(l10n.goalAdd),
                ),
              ],
            ),
            for (final g in value.goals)
              ListTile(
                dense: true,
                leading: const Icon(Icons.flag_outlined),
                title: Text(g.title),
                trailing: Text(money(g.target)),
              ),
          ],
        ),
        AsyncError() => Center(child: Text(l10n.genericError)),
        _ => const Center(child: CircularProgressIndicator()),
      },
    );
  }
}

class _DebtTile extends StatelessWidget {
  const _DebtTile({required this.view});

  final DebtView view;

  @override
  Widget build(BuildContext context) {
    final l10n = context.l10n;
    final money = context.money;
    final theme = Theme.of(context);
    final d = view.debt;
    final next = view.next;
    final due = view.nextDue;
    return Card(
      key: Key('debt-${d.meta.id}'),
      child: ListTile(
        leading: view.isInterestBearing
            ? Icon(Icons.flag, color: theme.colorScheme.error)
            : const Icon(Icons.receipt_long_outlined),
        title: Text('${d.creditorName} · ${l10n.creditorType(d.creditorType)}'),
        subtitle: Text(
          [
            l10n.debtRemaining(money(d.remaining)),
            if (next != null && due != null)
              l10n.debtNext(money(due), formatDate(next.dueOn)),
            if (view.isInterestBearing) l10n.debtInterestFlag,
          ].join('\n'),
        ),
        isThreeLine: true,
        trailing: const Icon(Icons.chevron_right),
        onTap: () => context.push(AppRoutes.debt(d.meta.id)),
      ),
    );
  }
}

class _LendDialog extends StatefulWidget {
  const _LendDialog({required this.initialDue});

  final LocalDate initialDue;

  @override
  State<_LendDialog> createState() => _LendDialogState();
}

class _LendDialogState extends State<_LendDialog> {
  final _name = TextEditingController();
  late LocalDate _due = widget.initialDue;

  @override
  void dispose() {
    _name.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    final l10n = context.l10n;
    return AlertDialog(
      title: Text(l10n.lendTitle),
      content: Column(
        mainAxisSize: MainAxisSize.min,
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text(l10n.lendHint, style: Theme.of(context).textTheme.bodySmall),
          TextField(
            key: const Key('lend-name'),
            controller: _name,
            autofocus: true,
            decoration: InputDecoration(labelText: l10n.lendDebtor),
            onChanged: (_) => setState(() {}),
          ),
          const SizedBox(height: 8),
          OutlinedButton(
            key: const Key('lend-due'),
            onPressed: () async {
              final picked = await showDatePicker(
                context: context,
                firstDate: DateTime(_due.year - 1),
                lastDate: DateTime(_due.year + 5),
                initialDate: DateTime(_due.year, _due.month, _due.day),
              );
              if (picked != null) {
                setState(() => _due = LocalDate.fromDateTime(picked));
              }
            },
            child: Text(l10n.lendDue(formatDate(_due))),
          ),
        ],
      ),
      actions: [
        TextButton(
          onPressed: () => Navigator.pop(context),
          child: Text(l10n.cancel),
        ),
        FilledButton(
          key: const Key('lend-next'),
          onPressed: _name.text.trim().isEmpty
              ? null
              : () => Navigator.pop(context, (_name.text.trim(), _due)),
          child: Text(l10n.save),
        ),
      ],
    );
  }
}

/// Bosh ekran: muddati yaqin to'lovlar va bergan qarzlar (xushmuomala).
class DueHomeCard extends ConsumerWidget {
  const DueHomeCard({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final o = ref.watch(debtOverviewProvider).valueOrNull;
    if (o == null) return const SizedBox.shrink();
    final today = Tashkent.dateOf(ref.watch(clockProvider).nowUtc());
    final limit = today.plusDays(3);
    final lines = <String>[];
    final l10n = context.l10n;
    final money = context.money;
    for (final v in o.debts) {
      final n = v.next;
      if (n != null && !n.dueOn.isAfter(limit)) {
        lines.add(
          l10n.dueDebt(
            v.debt.creditorName,
            money(v.nextDue ?? n.amount),
            formatDate(n.dueOn),
          ),
        );
      }
    }
    for (final r in o.receivables) {
      if (!r.dueDate.isAfter(limit)) {
        lines.add(
          l10n.dueReceivable(
            r.debtorName,
            money(r.remaining),
            formatDate(r.dueDate),
          ),
        );
      }
    }
    if (lines.isEmpty) return const SizedBox.shrink();
    return Card(
      key: const Key('home-due'),
      child: ListTile(
        leading: const Icon(Icons.event_outlined),
        title: Text(l10n.dueTitle),
        subtitle: Text(lines.join('\n')),
        onTap: () => context.push(AppRoutes.debts),
      ),
    );
  }
}

/// Umumiy «Qarzsiz kun» — ochiq qarzlar rejasining eng oxirgi to'lovi
/// (SPEC 2D.9; har to'lovdan keyin yangilanadi).
LocalDate? debtFreeDay(DebtOverview o) {
  LocalDate? out;
  for (final v in o.debts) {
    final d = v.debtFreeOn;
    if (d != null && (out == null || d.isAfter(out))) out = d;
  }
  return out;
}

/// «Qarzdan chiqish» rejimi: taklif, holat yoki bo'shagan 20 % taklifi.
class _RecoveryCard extends ConsumerWidget {
  const _RecoveryCard();

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final l10n = context.l10n;
    final s = ref.watch(recoveryStateProvider).valueOrNull;
    if (s == null) return const SizedBox.shrink();
    if (s.freedOffer) return const FreedShareCard();
    if (!s.isActive && !s.offerRecovery) return const SizedBox.shrink();
    return Card(
      key: const Key('recovery-card'),
      child: Padding(
        padding: const EdgeInsets.fromLTRB(16, 12, 8, 4),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Row(
              children: [
                const Icon(Icons.pie_chart_outline),
                const SizedBox(width: 8),
                Expanded(
                  child: Text(
                    l10n.recoveryTitle,
                    style: Theme.of(context).textTheme.titleSmall,
                  ),
                ),
              ],
            ),
            const SizedBox(height: 4),
            Text(
              s.isActive
                  ? l10n.recoveryActive(
                      percentLabel(s.split.needsBp),
                      percentLabel(s.split.debtBp),
                      percentLabel(s.split.savingsBp),
                    )
                  : l10n.recoveryOfferBody,
            ),
            Align(
              alignment: Alignment.centerRight,
              child: TextButton(
                key: const Key('recovery-open'),
                onPressed: () => context.push(AppRoutes.debtRecovery),
                child: Text(
                  s.isActive ? l10n.recoverySettings : l10n.recoveryEnable,
                ),
              ),
            ),
          ],
        ),
      ),
    );
  }
}

/// Hamma qarz yopilgach: bo'shagan 20 % ni «Kelajagim»ga (SPEC 2D.1).
class FreedShareCard extends ConsumerWidget {
  const FreedShareCard({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final l10n = context.l10n;
    final s = ref.watch(recoveryStateProvider).valueOrNull;
    if (s == null || !s.freedOffer) return const SizedBox.shrink();
    return Card(
      key: const Key('freed-share'),
      child: Padding(
        padding: const EdgeInsets.all(16),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text(
              l10n.freedShareTitle,
              style: Theme.of(context).textTheme.titleMedium,
            ),
            Text(l10n.freedShareBody(percentLabel(s.split.debtBp))),
            Row(
              mainAxisAlignment: MainAxisAlignment.end,
              children: [
                TextButton(
                  key: const Key('freed-share-dismiss'),
                  onPressed: () async {
                    await (await ref.read(
                      recoveryServiceProvider.future,
                    )).dismissFreedShare();
                    refreshMoneyViews(ref);
                  },
                  child: Text(l10n.notNow),
                ),
                FilledButton(
                  key: const Key('freed-share-accept'),
                  onPressed: () async {
                    await (await ref.read(
                      recoveryServiceProvider.future,
                    )).acceptFreedShare();
                    refreshMoneyViews(ref);
                  },
                  child: Text(l10n.freedShareAccept),
                ),
              ],
            ),
          ],
        ),
      ),
    );
  }
}

/// Bosh ekran: «Qarzsiz kun» (SPEC 2D.9) va rejim taklifi.
class DebtFreeHomeCard extends ConsumerWidget {
  const DebtFreeHomeCard({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final l10n = context.l10n;
    final money = context.money;
    final o = ref.watch(debtOverviewProvider).valueOrNull;
    final s = ref.watch(recoveryStateProvider).valueOrNull;
    if (o == null) return const SizedBox.shrink();
    if (o.debts.isEmpty) {
      return s != null && s.freedOffer
          ? const FreedShareCard()
          : const SizedBox.shrink();
    }
    final day = debtFreeDay(o);
    if (day == null) return const SizedBox.shrink();
    final extra = s?.monthlyExtra;
    final plan = planPayoff(
      [for (final v in o.debts) v.payoff],
      monthlyExtra: extra ?? Money.zero(o.totalDebt.currency),
    );
    final planned = plan.acceleratedDebtFree;
    return Card(
      key: const Key('home-debt-free'),
      child: ListTile(
        leading: const Icon(Icons.flag_circle_outlined),
        title: Text(l10n.homeDebtFree(formatDate(day))),
        subtitle: Text(
          [
            l10n.homeDebtFreeBody(money(o.totalDebt), plan.baselineMonths),
            if (planned != null && planned.isBefore(day))
              l10n.homeDebtFreePlan(formatDate(planned)),
            if (s != null && s.offerRecovery) l10n.homeRecoveryOffer,
          ].join('\n'),
        ),
        trailing: const Icon(Icons.chevron_right),
        onTap: () => context.push(AppRoutes.debtPlan),
      ),
    );
  }
}

/// Qarz qo'shilgach (masalan, yangi qarz ekranidan) vazifa hodisasi.
Future<void> recordDebtInventory(WidgetRef ref) =>
    recordTaskEvent(ref, TaskTrigger.debtInventoryCompleted);
