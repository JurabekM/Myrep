import 'package:baraka_daftari/app/l10n/l10n.dart';
import 'package:baraka_daftari/app/refresh.dart';
import 'package:baraka_daftari/app/router/app_routes.dart';
import 'package:baraka_daftari/app/widgets/labels.dart';
import 'package:baraka_daftari/app/widgets/money_input.dart';
import 'package:baraka_daftari/app/widgets/paged_list.dart';
import 'package:baraka_daftari/app/widgets/text_prompt.dart';
import 'package:baraka_daftari/core/logging/app_log.dart';
import 'package:baraka_daftari/features/debts/data/debt_providers.dart';
import 'package:baraka_daftari/features/debts/domain/debt_math.dart';
import 'package:baraka_daftari/features/debts/domain/debt_service.dart';
import 'package:baraka_daftari/features/debts/domain/debts.dart';
import 'package:baraka_daftari/features/debts/presentation/debt_free_screen.dart';
import 'package:baraka_daftari/features/debts/presentation/debt_new_screen.dart';
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';

/// Bitta qarz: haqiqiy narx, to'lov rejasi, to'lovlar, yelkadoshlar, tilxat.
class DebtDetailScreen extends ConsumerWidget {
  const DebtDetailScreen({required this.debtId, super.key});

  final String debtId;

  void _refresh(WidgetRef ref) {
    ref.invalidate(debtViewProvider(debtId));
    refreshMoneyViews(ref);
  }

  Future<void> _pay(BuildContext context, WidgetRef ref, DebtView v) async {
    final l10n = context.l10n;
    final messenger = ScaffoldMessenger.of(context);
    final navigator = Navigator.of(context);
    // Oyna butun so'm oladi; bank jadvalidagi tiyin snapPayment bilan
    // tiklanadi.
    final entered = await showAmountSheet(
      context,
      currency: v.currency,
      title: l10n.debtPayTitle,
      initial: v.nextDue == null ? null : ceilToMajor(v.nextDue!),
      max: ceilToMajor(v.payoffAmount),
    );
    if (entered == null || !entered.isPositive || !context.mounted) return;
    final amount = snapPayment(
      entered,
      remaining: v.payoffAmount,
      next: v.nextDue,
    );
    String? contributorId;
    if (v.contributors.isNotEmpty) {
      final picked = await showDialog<String>(
        context: context,
        builder: (context) => SimpleDialog(
          title: Text(l10n.whoPaid),
          children: [
            SimpleDialogOption(
              key: const Key('who-paid-family'),
              onPressed: () => Navigator.pop(context, ''),
              child: Text(l10n.whoPaidFamily),
            ),
            for (final c in v.contributors)
              SimpleDialogOption(
                key: Key('who-paid-${c.meta.id}'),
                onPressed: () => Navigator.pop(context, c.meta.id),
                child: Text(c.name),
              ),
          ],
        ),
      );
      if (picked == null) return;
      contributorId = picked.isEmpty ? null : picked;
    }
    try {
      // Rejadagidan ko'pi — qo'shimcha (muddatidan oldin) to'lov: servis
      // o'zi ajratadi va rejani qayta quradi.
      final r = await (await ref.read(
        debtServiceProvider.future,
      )).pay(v.debt, amount, contributorId: contributorId);
      _refresh(ref);
      await showDebtClosed(navigator, ref, r);
    } on Object {
      AppLog.event('debt_pay_failed');
      messenger.showSnackBar(SnackBar(content: Text(l10n.genericError)));
    }
  }

  Future<void> _editFee(
    BuildContext context,
    WidgetRef ref,
    DebtView v,
  ) async {
    final l10n = context.l10n;
    final text = await showTextPrompt(
      context,
      title: l10n.payoffFeeLabel,
      label: l10n.payoffFeeLabel,
      fieldKey: const Key('debt-fee-field'),
      okKey: const Key('debt-fee-save'),
      initial: v.debt.prepayFeeBp == null
          ? ''
          : percentLabel(v.debt.prepayFeeBp!),
      keyboardType: const TextInputType.numberWithOptions(decimal: true),
    );
    if (text == null) return;
    final bp = text.trim().isEmpty ? 0 : parsePercentBp(text);
    if (bp == null) return;
    await (await ref.read(debtServiceProvider.future)).setPrepayFee(
      v.debt,
      bp,
    );
    _refresh(ref);
  }

  Future<void> _addContributor(
    BuildContext context,
    WidgetRef ref,
    DebtView v,
  ) async {
    final l10n = context.l10n;
    final name = await showTextPrompt(
      context,
      title: l10n.contributorAdd,
      label: l10n.memberName,
      fieldKey: const Key('contributor-name'),
      okKey: const Key('contributor-next'),
    );
    if (name == null || name.trim().isEmpty || !context.mounted) return;
    final share = await showAmountSheet(
      context,
      currency: v.currency,
      title: l10n.contributorShareTitle,
    );
    await (await ref.read(debtServiceProvider.future)).addContributor(
      v.debt,
      name: name,
      monthlyShare: share,
    );
    _refresh(ref);
  }

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final l10n = context.l10n;
    final theme = Theme.of(context);
    final money = context.money;
    final view = ref.watch(debtViewProvider(debtId));
    final goals = ref.watch(debtOverviewProvider).valueOrNull?.goals ?? [];
    return Scaffold(
      appBar: AppBar(title: Text(l10n.debtsTitle)),
      body: switch (view) {
        AsyncData(:final value?) => ListView(
          padding: const EdgeInsets.fromLTRB(16, 8, 16, 32),
          children: [
            Text(
              '${value.debt.creditorName} · '
              '${l10n.creditorType(value.debt.creditorType)}',
              style: theme.textTheme.titleLarge,
            ),
            if (value.debt.reason != null) Text(value.debt.reason!),
            Text(
              l10n.debtRemaining(money(value.debt.remaining)),
              key: const Key('debt-remaining'),
              style: theme.textTheme.titleMedium,
            ),
            if (value.debtFreeOn case final day?)
              Text(
                l10n.debtFreeOn(formatDate(day)),
                key: const Key('debt-free-on'),
              ),
            if (value.isInterestBearing)
              Padding(
                padding: const EdgeInsets.only(top: 6),
                child: Row(
                  children: [
                    Icon(Icons.flag, color: theme.colorScheme.error),
                    const SizedBox(width: 6),
                    Expanded(
                      child: Text(
                        l10n.debtRibaWarning,
                        style: TextStyle(color: theme.colorScheme.error),
                      ),
                    ),
                  ],
                ),
              ),
            const SizedBox(height: 8),
            CostCard(cost: value.cost, goals: goals),
            const SizedBox(height: 8),
            Wrap(
              spacing: 8,
              children: [
                if (value.isOpen)
                  FilledButton(
                    key: const Key('debt-pay'),
                    onPressed: () => _pay(context, ref, value),
                    child: Text(l10n.debtPay),
                  ),
                OutlinedButton.icon(
                  key: const Key('debt-receipt'),
                  icon: const Icon(Icons.description_outlined),
                  label: Text(l10n.debtReceipt),
                  onPressed: () =>
                      context.push(AppRoutes.debtReceipt(value.debt.meta.id)),
                ),
              ],
            ),
            if (value.isOpen)
              ListTile(
                key: const Key('debt-fee'),
                dense: true,
                contentPadding: EdgeInsets.zero,
                leading: const Icon(Icons.gavel_outlined),
                title: Text(
                  value.debt.prepayFeeBp == null
                      ? l10n.payoffNoFee
                      : l10n.payoffFeeValue(
                          percentLabel(value.debt.prepayFeeBp!),
                        ),
                ),
                subtitle: Text(l10n.payoffFeeLabel),
                trailing: const Icon(Icons.edit_outlined),
                onTap: () => _editFee(context, ref, value),
              ),
            const SizedBox(height: 12),
            Text(l10n.debtScheduleLabel, style: theme.textTheme.titleSmall),
            // Faqat rejadagi to'lovlar qatorlarni tartib bilan yopadi;
            // qo'shimcha to'lovlar rejani qayta quradi.
            for (final (k, i) in value.plan.indexed)
              () {
                final paid = k < value.paidRows;
                return ListTile(
                  dense: true,
                  contentPadding: EdgeInsets.zero,
                  leading: Icon(
                    paid ? Icons.check_circle : Icons.circle_outlined,
                    size: 18,
                    color: paid ? theme.colorScheme.primary : null,
                  ),
                  title: Text(formatDate(i.dueOn)),
                  subtitle: i.interest.isPositive
                      ? Text('${l10n.costOver}: ${money(i.interest)}')
                      : null,
                  trailing: Text(
                    paid
                        ? '${money(i.amount)} · ${l10n.debtPlanPaid}'
                        : money(i.amount),
                  ),
                );
              }(),
            const SizedBox(height: 12),
            Row(
              children: [
                Expanded(
                  child: Text(
                    l10n.contributorsTitle,
                    style: theme.textTheme.titleSmall,
                  ),
                ),
                TextButton(
                  key: const Key('contributor-add'),
                  onPressed: () => _addContributor(context, ref, value),
                  child: Text(l10n.contributorAdd),
                ),
              ],
            ),
            if (value.contributors.isEmpty)
              Text(l10n.contributorsHint, style: theme.textTheme.bodySmall),
            for (final c in value.contributors)
              ListTile(
                key: Key('contributor-${c.meta.id}'),
                dense: true,
                contentPadding: EdgeInsets.zero,
                leading: const Icon(Icons.link),
                title: Text(c.name),
                subtitle: Text(
                  c.monthlyShare == null
                      ? l10n.contributorPaid(money(value.paidBy(c.meta.id)))
                      : l10n.contributorLine(
                          money(c.monthlyShare!),
                          money(value.paidBy(c.meta.id)),
                        ),
                ),
              ),
            if (value.payments.isNotEmpty) ...[
              const SizedBox(height: 12),
              Text(
                l10n.debtPaymentsHeader,
                style: theme.textTheme.titleSmall,
              ),
              PagedList(
                count: value.payments.length,
                itemBuilder: (context, i) {
                  final p = value.payments[i];
                  return ListTile(
                    dense: true,
                    contentPadding: EdgeInsets.zero,
                    title: Text(money(p.amount)),
                    subtitle: Text(
                      [
                        formatDate(p.paidOn),
                        if (p.isPrepayment) l10n.debtPrepayment,
                        if (p.fee != null) l10n.debtFeeNote(money(p.fee!)),
                        if (_contributorName(value, p) case final n?) n,
                        if (p.note != null) p.note!,
                      ].join(' · '),
                    ),
                  );
                },
              ),
            ],
          ],
        ),
        AsyncData() || AsyncError() => Center(child: Text(l10n.genericError)),
        _ => const Center(child: CircularProgressIndicator()),
      },
    );
  }
}

String? _contributorName(DebtView v, DebtPayment p) {
  if (p.contributorId == null) return null;
  for (final c in v.contributors) {
    if (c.meta.id == p.contributorId) return c.name;
  }
  return null;
}
