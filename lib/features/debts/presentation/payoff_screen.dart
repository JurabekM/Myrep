import 'package:baraka_daftari/app/l10n/l10n.dart';
import 'package:baraka_daftari/app/refresh.dart';
import 'package:baraka_daftari/app/router/app_routes.dart';
import 'package:baraka_daftari/app/widgets/labels.dart';
import 'package:baraka_daftari/app/widgets/money_input.dart';
import 'package:baraka_daftari/core/errors/data_exceptions.dart';
import 'package:baraka_daftari/core/logging/app_log.dart';
import 'package:baraka_daftari/core/money/money.dart';
import 'package:baraka_daftari/features/budget/data/budget_providers.dart';
import 'package:baraka_daftari/features/debts/data/debt_providers.dart';
import 'package:baraka_daftari/features/debts/domain/debt_service.dart';
import 'package:baraka_daftari/features/debts/domain/payoff.dart';
import 'package:baraka_daftari/features/debts/presentation/debt_free_screen.dart';
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';

/// Qarzdan chiqish rejalovchisi (SPEC 2D.2): odatiy va qo'shimcha to'lovli
/// grafik yonma-yon, «N oy erta» va «X so'm tejaldi», yopish tartibi.
class PayoffScreen extends ConsumerStatefulWidget {
  const PayoffScreen({super.key});

  @override
  ConsumerState<PayoffScreen> createState() => _PayoffScreenState();
}

class _PayoffScreenState extends ConsumerState<PayoffScreen> {
  /// Foydalanuvchi o'zgartirmaguncha — rejim ulushi (20 %).
  Money? _monthly;
  Money? _lump;
  String? _expanded;

  Future<void> _editMonthly(Money current) async {
    final m = await showAmountSheet(
      context,
      currency: current.currency,
      title: context.l10n.payoffMonthlyTitle,
      initial: current,
    );
    if (m != null) setState(() => _monthly = m);
  }

  Future<void> _editLump(Money current) async {
    final m = await showAmountSheet(
      context,
      currency: current.currency,
      title: context.l10n.payoffLumpTitle,
      initial: current,
    );
    if (m != null) setState(() => _lump = m);
  }

  Future<void> _move(List<DebtView> ordered, int i, int delta) async {
    final ids = [for (final v in ordered) v.debt.meta.id];
    final id = ids.removeAt(i);
    ids.insert(i + delta, id);
    await (await ref.read(debtServiceProvider.future)).setPayoffOrder(ids);
    refreshMoneyViews(ref);
  }

  Future<void> _resetOrder() async {
    await (await ref.read(debtServiceProvider.future)).setPayoffOrder(
      const [],
    );
    refreshMoneyViews(ref);
  }

  /// Qutqarilgan pulni tartibdagi birinchi qarzga (SPEC 2D.2).
  Future<void> _applyRescue(DebtView first) async {
    final l10n = context.l10n;
    final messenger = ScaffoldMessenger.of(context);
    final navigator = Navigator.of(context);
    final money = context.money;
    try {
      final debts = await ref.read(debtServiceProvider.future);
      final rescue = await ref.read(rescueServiceProvider.future);
      DebtPaymentResult? result;
      final moved = await rescue.transferWeekTo((amount) async {
        result = await debts.pay(first.debt, amount, extraOnly: true);
        return result!.payments.last.meta.id;
      }, max: first.maxExtra);
      refreshMoneyViews(ref);
      messenger.showSnackBar(
        SnackBar(
          content: Text(
            l10n.payoffApplied(money(moved), first.debt.creditorName),
          ),
        ),
      );
      if (result != null && result!.closed) {
        await showDebtClosed(navigator, ref, result!);
      }
    } on DomainRuleException catch (e) {
      AppLog.event('payoff_rescue_${e.code}');
      messenger.showSnackBar(SnackBar(content: Text(l10n.genericError)));
    }
  }

  @override
  Widget build(BuildContext context) {
    final l10n = context.l10n;
    final theme = Theme.of(context);
    final money = context.money;
    final overview = ref.watch(debtOverviewProvider);
    final recovery = ref.watch(recoveryStateProvider).valueOrNull;
    final rescue = ref.watch(rescueOverviewProvider).valueOrNull;
    final sold = ref.watch(sellablesProvider).valueOrNull ?? const [];
    return Scaffold(
      appBar: AppBar(title: Text(l10n.payoffTitle)),
      body: switch (overview) {
        AsyncData(:final value) when value.debts.isEmpty => Center(
          child: Text(l10n.debtsEmpty),
        ),
        AsyncData(:final value) => () {
          final c = value.totalDebt.currency;
          final zero = Money.zero(c);
          final ordered = value.debts;
          final soldSum = Money.sum([
            for (final s in sold)
              if (s.awaitsApplying) s.soldFor!,
          ], c);
          final rescueAvail = rescue?.week.available ?? zero;
          final monthly = _monthly ?? recovery?.monthlyExtra ?? zero;
          final lump = _lump ?? zero;
          final plan = planPayoff(
            [for (final v in ordered) v.payoff],
            monthlyExtra: monthly,
            lumpSum: lump,
          );
          final byId = {for (final d in plan.debts) d.id: d};
          return ListView(
            padding: const EdgeInsets.fromLTRB(16, 8, 16, 32),
            children: [
              Card(
                key: const Key('payoff-summary'),
                child: Padding(
                  padding: const EdgeInsets.all(16),
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Text(
                        l10n.payoffDebtFree(
                          formatDate(plan.baselineDebtFree!),
                          formatDate(plan.acceleratedDebtFree!),
                        ),
                        key: const Key('payoff-debt-free'),
                        style: theme.textTheme.titleMedium,
                      ),
                      Text(
                        [
                          if (plan.baselineMonths > plan.acceleratedMonths)
                            l10n.payoffEarly(
                              plan.baselineMonths - plan.acceleratedMonths,
                            )
                          else
                            l10n.payoffSameEnd,
                          if (plan.savedTotal(c).isPositive)
                            l10n.payoffSaved(money(plan.savedTotal(c))),
                        ].join(' · '),
                        key: const Key('payoff-result'),
                      ),
                      const SizedBox(height: 8),
                      Wrap(
                        spacing: 8,
                        runSpacing: 4,
                        children: [
                          OutlinedButton(
                            key: const Key('payoff-monthly'),
                            onPressed: () => _editMonthly(monthly),
                            child: Text(l10n.payoffMonthly(money(monthly))),
                          ),
                          OutlinedButton(
                            key: const Key('payoff-lump'),
                            onPressed: () => _editLump(lump),
                            child: Text(l10n.payoffLump(money(lump))),
                          ),
                        ],
                      ),
                      const SizedBox(height: 4),
                      Text(
                        l10n.payoffEstimate,
                        style: theme.textTheme.bodySmall,
                      ),
                    ],
                  ),
                ),
              ),
              const SizedBox(height: 12),
              Text(l10n.payoffSources, style: theme.textTheme.titleSmall),
              ListTile(
                dense: true,
                contentPadding: EdgeInsets.zero,
                leading: const Icon(Icons.pie_chart_outline),
                title: Text(
                  recovery != null && recovery.isActive
                      ? l10n.payoffSourceShare(
                          percentLabel(recovery.split.debtBp),
                          money(recovery.monthlyExtra),
                        )
                      : l10n.payoffSourceShareOff,
                ),
                onTap: () => context.push(AppRoutes.debtRecovery),
              ),
              ListTile(
                dense: true,
                contentPadding: EdgeInsets.zero,
                leading: const Icon(Icons.shield_outlined),
                title: Text(l10n.payoffSourceRescue(money(rescueAvail))),
                trailing: TextButton(
                  key: const Key('payoff-apply-rescue'),
                  onPressed: rescueAvail.isPositive
                      ? () => _applyRescue(ordered.first)
                      : null,
                  child: Text(l10n.payoffApply),
                ),
              ),
              ListTile(
                dense: true,
                contentPadding: EdgeInsets.zero,
                leading: const Icon(Icons.sell_outlined),
                title: Text(l10n.payoffSourceSold(money(soldSum))),
                trailing: const Icon(Icons.chevron_right),
                onTap: () => context.push(AppRoutes.sellables),
              ),
              const SizedBox(height: 12),
              Row(
                children: [
                  Expanded(
                    child: Text(
                      l10n.payoffOrder,
                      style: theme.textTheme.titleSmall,
                    ),
                  ),
                  TextButton(
                    key: const Key('payoff-order-reset'),
                    onPressed: _resetOrder,
                    child: Text(l10n.payoffOrderReset),
                  ),
                ],
              ),
              Text(l10n.payoffOrderHint, style: theme.textTheme.bodySmall),
              for (final (i, v) in ordered.indexed)
                _PayoffTile(
                  index: i,
                  view: v,
                  result: byId[v.debt.meta.id]!,
                  expanded: _expanded == v.debt.meta.id,
                  onToggle: () => setState(
                    () => _expanded = _expanded == v.debt.meta.id
                        ? null
                        : v.debt.meta.id,
                  ),
                  onUp: i == 0 ? null : () => _move(ordered, i, -1),
                  onDown: i == ordered.length - 1
                      ? null
                      : () => _move(ordered, i, 1),
                ),
            ],
          );
        }(),
        AsyncError() => Center(child: Text(l10n.genericError)),
        _ => const Center(child: CircularProgressIndicator()),
      },
    );
  }
}

class _PayoffTile extends StatelessWidget {
  const _PayoffTile({
    required this.index,
    required this.view,
    required this.result,
    required this.expanded,
    required this.onToggle,
    this.onUp,
    this.onDown,
  });

  final int index;
  final DebtView view;
  final PayoffComparison result;
  final bool expanded;
  final VoidCallback onToggle;
  final VoidCallback? onUp;
  final VoidCallback? onDown;

  @override
  Widget build(BuildContext context) {
    final l10n = context.l10n;
    final money = context.money;
    final theme = Theme.of(context);
    final d = view.debt;
    final base = result.baseline;
    final acc = result.accelerated;
    return Card(
      key: Key('payoff-debt-${d.meta.id}'),
      child: Padding(
        padding: const EdgeInsets.fromLTRB(12, 8, 4, 8),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Row(
              children: [
                CircleAvatar(radius: 12, child: Text('${index + 1}')),
                const SizedBox(width: 8),
                if (view.isInterestBearing)
                  Padding(
                    padding: const EdgeInsets.only(right: 4),
                    child: Icon(
                      Icons.flag,
                      size: 18,
                      color: theme.colorScheme.error,
                    ),
                  ),
                Expanded(
                  child: Text(
                    '${d.creditorName} · ${l10n.creditorType(d.creditorType)}',
                    style: theme.textTheme.titleSmall,
                  ),
                ),
                IconButton(
                  key: Key('payoff-up-${d.meta.id}'),
                  tooltip: l10n.payoffUp,
                  onPressed: onUp,
                  icon: const Icon(Icons.arrow_upward),
                ),
                IconButton(
                  key: Key('payoff-down-${d.meta.id}'),
                  tooltip: l10n.payoffDown,
                  onPressed: onDown,
                  icon: const Icon(Icons.arrow_downward),
                ),
              ],
            ),
            Text(
              '${l10n.payoffBaseline}: ${l10n.payoffMonths(base.months)}, '
              '${formatDate(base.endDate!)} · ${money(base.totalPaid)}',
            ),
            Text(
              '${l10n.payoffAccelerated}: ${l10n.payoffMonths(acc.months)}, '
              '${formatDate(acc.endDate!)} · ${money(acc.totalPaid)}',
            ),
            Text(
              [
                if (result.monthsEarly > 0)
                  l10n.payoffEarly(result.monthsEarly)
                else
                  l10n.payoffSameEnd,
                if (result.saved.isPositive)
                  l10n.payoffSaved(money(result.saved)),
                if (acc.totalFees.isPositive)
                  l10n.payoffFees(money(acc.totalFees)),
              ].join(' · '),
              key: Key('payoff-gain-${d.meta.id}'),
              style: TextStyle(color: theme.colorScheme.primary),
            ),
            TextButton(
              key: Key('payoff-table-${d.meta.id}'),
              onPressed: onToggle,
              child: Text(l10n.payoffShowTable),
            ),
            if (expanded) _SideBySide(base: base, acc: acc),
          ],
        ),
      ),
    );
  }
}

/// Odatiy va tezlashtirilgan grafik yonma-yon (oyma-oy).
class _SideBySide extends StatelessWidget {
  const _SideBySide({required this.base, required this.acc});

  final PayoffSchedule base;
  final PayoffSchedule acc;

  @override
  Widget build(BuildContext context) {
    final l10n = context.l10n;
    final money = context.money;
    final style = Theme.of(context).textTheme.bodySmall;
    final head = Theme.of(context).textTheme.labelSmall;
    return Padding(
      padding: const EdgeInsets.only(right: 8),
      child: Table(
        columnWidths: const {
          0: IntrinsicColumnWidth(),
          1: FlexColumnWidth(),
          2: FlexColumnWidth(),
        },
        children: [
          TableRow(
            children: [
              const SizedBox.shrink(),
              Text(l10n.payoffBaseline, style: head, textAlign: TextAlign.end),
              Text(
                l10n.payoffAccelerated,
                style: head,
                textAlign: TextAlign.end,
              ),
            ],
          ),
          for (var k = 0; k < base.months; k++)
            TableRow(
              children: [
                Padding(
                  padding: const EdgeInsets.only(right: 8, top: 2),
                  child: Text(formatDate(base.steps[k].dueOn), style: style),
                ),
                Text(
                  money(base.steps[k].total),
                  style: style,
                  textAlign: TextAlign.end,
                ),
                Text(
                  k < acc.months ? money(acc.steps[k].total) : '—',
                  style: style,
                  textAlign: TextAlign.end,
                ),
              ],
            ),
        ],
      ),
    );
  }
}
