import 'package:baraka_daftari/app/l10n/l10n.dart';
import 'package:baraka_daftari/app/refresh.dart';
import 'package:baraka_daftari/app/widgets/labels.dart';
import 'package:baraka_daftari/app/widgets/money_input.dart';
import 'package:baraka_daftari/core/domain/enums.dart';
import 'package:baraka_daftari/core/logging/app_log.dart';
import 'package:baraka_daftari/core/money/money.dart';
import 'package:baraka_daftari/core/time/calendar.dart';
import 'package:baraka_daftari/features/audit/data/audit_providers.dart';
import 'package:baraka_daftari/features/audit/domain/ledger_service.dart';
import 'package:baraka_daftari/features/audit/domain/month_ledger.dart';
import 'package:baraka_daftari/features/content/data/content_providers.dart';
import 'package:baraka_daftari/features/content/domain/content.dart';
import 'package:baraka_daftari/features/expenses/data/expense_providers.dart';
import 'package:baraka_daftari/features/expenses/domain/expense.dart';
import 'package:baraka_daftari/features/vault/data/vault_providers.dart';
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:riverpod_annotation/riverpod_annotation.dart';

part 'audit_screen.g.dart';

/// Audit ma'lumotlari: o'tgan oy, hisob va kategoriyalar.
typedef AuditData = ({
  DateRange period,
  MonthLedger ledger,
  List<Category> categories,
});

@riverpod
Future<AuditData> auditData(Ref ref) async {
  final ledger = await ref.watch(ledgerServiceProvider.future);
  final period = await ledger.previousPeriod();
  return (
    period: period,
    ledger: await ledger.ledgerFor(period),
    categories: await (await ref.watch(
      expenseServiceProvider.future,
    )).categories(),
  );
}

/// Oylik audit ustasi (SPEC 2.3): daromad → majburiyatlar → kategoriyalar
/// bo'yicha xarajat → «izohsiz qolgan summa».
class AuditScreen extends ConsumerStatefulWidget {
  const AuditScreen({super.key});

  @override
  ConsumerState<AuditScreen> createState() => _AuditScreenState();
}

class _AuditScreenState extends ConsumerState<AuditScreen> {
  int _step = 0;

  Future<void> _run(Future<void> Function(LedgerService) action) async {
    final messenger = ScaffoldMessenger.of(context);
    final error = context.l10n.genericError;
    try {
      await action(await ref.read(ledgerServiceProvider.future));
      ref.invalidate(auditDataProvider);
      refreshMoneyViews(ref);
    } on Object {
      AppLog.event('audit_action_failed');
      messenger.showSnackBar(SnackBar(content: Text(error)));
    }
  }

  Future<void> _addIncome(AuditData d) async {
    final amount = await showAmountSheet(
      context,
      currency: d.ledger.currency,
      title: context.l10n.auditAddIncome,
    );
    if (amount == null) return;
    await _run((s) async {
      final incomes = await ref.read(incomeServiceProvider.future);
      await incomes.add(
        amount: amount,
        source: IncomeSource.other,
        channel: PaymentChannel.cash,
        receivedAt: s.instantInside(d.period),
      );
    });
  }

  Future<void> _addExpense(AuditData d, Category c) async {
    final l10n = context.l10n;
    final amount = await showAmountSheet(
      context,
      currency: d.ledger.currency,
      title: l10n.auditAddTo(l10n.category(c)),
    );
    if (amount == null) return;
    await _run((s) async {
      final expenses = await ref.read(expenseServiceProvider.future);
      await expenses.add(
        amount: amount,
        categoryId: c.meta.id,
        channel: PaymentChannel.cash,
        spentAt: s.instantInside(d.period),
      );
    });
  }

  @override
  Widget build(BuildContext context) {
    final l10n = context.l10n;
    final data = ref.watch(auditDataProvider);
    return Scaffold(
      appBar: AppBar(title: Text(l10n.auditTitle)),
      body: switch (data) {
        AsyncError() => Center(child: Text(l10n.genericError)),
        AsyncData(:final value) => _wizard(context, value),
        _ => const Center(child: CircularProgressIndicator()),
      },
    );
  }

  Widget _wizard(BuildContext context, AuditData d) {
    final l10n = context.l10n;
    final theme = Theme.of(context);
    final steps = [
      l10n.auditStepIncome,
      l10n.auditStepObligations,
      l10n.auditStepExpenses,
      l10n.auditStepResult,
    ];
    final last = d.period.endExclusive.plusDays(-1);
    return Center(
      child: ConstrainedBox(
        constraints: const BoxConstraints(maxWidth: 620),
        child: Column(
          children: [
            Padding(
              padding: const EdgeInsets.fromLTRB(16, 8, 16, 0),
              child: Text(
                l10n.auditPeriod(formatDate(d.period.start), formatDate(last)),
                key: const Key('audit-period'),
                style: theme.textTheme.titleSmall,
              ),
            ),
            Padding(
              padding: const EdgeInsets.all(8),
              child: Row(
                children: [
                  for (final (i, s) in steps.indexed)
                    Expanded(
                      child: Column(
                        children: [
                          CircleAvatar(
                            radius: 14,
                            backgroundColor: i <= _step
                                ? theme.colorScheme.primary
                                : theme.colorScheme.outlineVariant,
                            child: Text(
                              '${i + 1}',
                              style: TextStyle(
                                color: theme.colorScheme.onPrimary,
                                fontSize: 13,
                              ),
                            ),
                          ),
                          const SizedBox(height: 2),
                          Text(
                            s,
                            style: theme.textTheme.labelSmall,
                            textAlign: TextAlign.center,
                          ),
                        ],
                      ),
                    ),
                ],
              ),
            ),
            const Divider(height: 1),
            Expanded(
              child: ListView(
                padding: const EdgeInsets.all(16),
                children: switch (_step) {
                  0 => _incomeStep(context, d),
                  1 => _obligationsStep(context, d),
                  2 => _expensesStep(context, d),
                  _ => _resultStep(context, d),
                },
              ),
            ),
            SafeArea(
              top: false,
              child: Padding(
                padding: const EdgeInsets.fromLTRB(16, 4, 16, 12),
                child: Row(
                  // Tor ekranda ham sig'adi: tugmalar Flexible, oraliq
                  // spaceBetween bilan (Spacer + Flexible tugmani o'rtaga
                  // surib qo'yardi — qurilmada ko'rilgan).
                  mainAxisAlignment: MainAxisAlignment.spaceBetween,
                  children: [
                    if (_step > 0)
                      Flexible(
                        child: TextButton(
                          key: const Key('audit-back'),
                          onPressed: () => setState(() => _step--),
                          child: Text(l10n.back),
                        ),
                      )
                    else
                      const SizedBox.shrink(),
                    const SizedBox(width: 8),
                    Flexible(
                      flex: 3,
                      child: _step < 3
                          ? FilledButton(
                              key: const Key('audit-next'),
                              onPressed: () => setState(() => _step++),
                              child: Text(l10n.next),
                            )
                          : FilledButton(
                              key: const Key('audit-finish'),
                              onPressed: () async {
                                final navigator = Navigator.of(context);
                                final messenger = ScaffoldMessenger.of(context);
                                await _run((s) => s.completeAudit(d.period));
                                await recordTaskEvent(
                                  ref,
                                  TaskTrigger.auditCompleted,
                                );
                                messenger.showSnackBar(
                                  SnackBar(content: Text(l10n.auditFinished)),
                                );
                                navigator.pop();
                              },
                              child: Text(l10n.auditFinish),
                            ),
                    ),
                  ],
                ),
              ),
            ),
          ],
        ),
      ),
    );
  }

  List<Widget> _incomeStep(BuildContext context, AuditData d) {
    final l10n = context.l10n;
    return [
      Text(l10n.auditIncomeHint),
      const SizedBox(height: 16),
      Text(
        context.money(d.ledger.income),
        key: const Key('audit-income'),
        style: Theme.of(context).textTheme.headlineMedium,
      ),
      if (d.ledger.riboIncome.isPositive)
        Text(
          l10n.auditRiboIncome(context.money(d.ledger.riboIncome)),
          key: const Key('audit-ribo-income'),
        ),
      const SizedBox(height: 16),
      OutlinedButton.icon(
        key: const Key('audit-add-income'),
        icon: const Icon(Icons.add),
        label: Text(l10n.auditAddIncome),
        onPressed: () => _addIncome(d),
      ),
    ];
  }

  List<Widget> _obligationsStep(BuildContext context, AuditData d) {
    final l10n = context.l10n;
    return [
      Text(l10n.auditObligationsHint),
      const SizedBox(height: 12),
      for (final line in d.ledger.obligations)
        ListTile(
          contentPadding: EdgeInsets.zero,
          title: Text(line.obligation.title),
          subtitle: Text(
            l10n.auditObligationLine(
              l10n.obligationKind(line.obligation.kind),
              context.money(line.obligation.amount),
              context.money(line.recorded),
            ),
          ),
        ),
      if (d.ledger.obligations.isEmpty) Text(l10n.obligationsEmpty),
    ];
  }

  List<Widget> _expensesStep(BuildContext context, AuditData d) {
    final l10n = context.l10n;
    final zero = Money.zero(d.ledger.currency);
    return [
      Text(l10n.auditExpensesHint),
      const SizedBox(height: 8),
      for (final c in d.categories)
        ListTile(
          key: Key('audit-cat-${c.systemKey?.name ?? c.meta.id}'),
          contentPadding: EdgeInsets.zero,
          title: Text(l10n.category(c)),
          subtitle: Text(
            context.money(d.ledger.expensesByCategory[c.meta.id] ?? zero),
          ),
          trailing: IconButton(
            tooltip: l10n.auditAddTo(l10n.category(c)),
            icon: const Icon(Icons.add_circle_outline),
            onPressed: () => _addExpense(d, c),
          ),
        ),
    ];
  }

  List<Widget> _resultStep(BuildContext context, AuditData d) {
    final l10n = context.l10n;
    final theme = Theme.of(context);
    final l = d.ledger;
    final u = l.unexplained;
    Widget row(String label, Money m) => Padding(
      padding: const EdgeInsets.symmetric(vertical: 4),
      child: Row(
        children: [
          Expanded(child: Text(label)),
          Text(context.money(m)),
        ],
      ),
    );
    return [
      row(l10n.auditIncome, l.income),
      row('− ${l10n.auditObligations}', l.obligationsUnrecorded),
      row('− ${l10n.auditExpenses}', l.expenses),
      row('− ${l10n.auditSavings}', l.netSavings),
      const Divider(),
      Card(
        color: theme.colorScheme.tertiaryContainer,
        child: Padding(
          padding: const EdgeInsets.all(16),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Text(
                l10n.auditUnexplained,
                style: theme.textTheme.titleSmall?.copyWith(
                  color: theme.colorScheme.onTertiaryContainer,
                ),
              ),
              Text(
                context.money(u),
                key: const Key('audit-unexplained'),
                style: theme.textTheme.headlineMedium?.copyWith(
                  color: theme.colorScheme.onTertiaryContainer,
                ),
              ),
              if (!u.isZero) ...[
                const SizedBox(height: 4),
                Text(
                  u.isNegative
                      ? l10n.auditNegativeHint
                      : l10n.auditUnexplainedHint,
                  style: TextStyle(
                    color: theme.colorScheme.onTertiaryContainer,
                  ),
                ),
              ],
            ],
          ),
        ),
      ),
      if (u.isPositive) ...[
        const SizedBox(height: 8),
        FilledButton.tonal(
          key: const Key('audit-mark-small'),
          onPressed: () => _run((s) => s.markUnexplainedAsDailySmall(d.period)),
          child: Text(l10n.auditMarkSmall),
        ),
        TextButton(
          key: const Key('audit-distribute'),
          onPressed: () => setState(() => _step = 2),
          child: Text(l10n.auditDistribute),
        ),
      ],
      if (u.isNegative)
        TextButton(
          onPressed: () => setState(() => _step = 0),
          child: Text(l10n.auditAddIncome),
        ),
    ];
  }
}
