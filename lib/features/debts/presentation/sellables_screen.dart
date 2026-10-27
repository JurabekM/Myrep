import 'package:baraka_daftari/app/l10n/l10n.dart';
import 'package:baraka_daftari/app/refresh.dart';
import 'package:baraka_daftari/app/widgets/money_input.dart';
import 'package:baraka_daftari/app/widgets/text_prompt.dart';
import 'package:baraka_daftari/core/logging/app_log.dart';
import 'package:baraka_daftari/core/money/money.dart';
import 'package:baraka_daftari/features/debts/data/debt_providers.dart';
import 'package:baraka_daftari/features/debts/domain/debt_service.dart';
import 'package:baraka_daftari/features/debts/domain/debts.dart';
import 'package:baraka_daftari/features/debts/presentation/debt_free_screen.dart';
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

/// «Sotiladigan buyumlar» (SPEC 2D.7): sotilgan puli bir bosishda qarzga.
class SellablesScreen extends ConsumerWidget {
  const SellablesScreen({super.key});

  Future<void> _add(BuildContext context, WidgetRef ref) async {
    final l10n = context.l10n;
    final name = await showTextPrompt(
      context,
      title: l10n.sellableAdd,
      label: l10n.sellableName,
      fieldKey: const Key('sellable-name'),
      okKey: const Key('sellable-next'),
    );
    if (name == null || name.trim().isEmpty || !context.mounted) return;
    final estimate = await showAmountSheet(
      context,
      currency: CurrencyCode.uzs,
      title: l10n.sellableEstimate,
    );
    if (estimate == null) return;
    await (await ref.read(debtServiceProvider.future)).addSellable(
      name,
      estimate,
    );
    refreshMoneyViews(ref);
  }

  Future<void> _sold(
    BuildContext context,
    WidgetRef ref,
    SellableItem item,
  ) async {
    final price = await showAmountSheet(
      context,
      currency: item.estimated.currency,
      title: context.l10n.sellableSoldPrice,
      initial: item.estimated.isPositive ? item.estimated : null,
    );
    if (price == null || !price.isPositive) return;
    await (await ref.read(debtServiceProvider.future)).markSold(item, price);
    refreshMoneyViews(ref);
  }

  Future<void> _apply(
    BuildContext context,
    WidgetRef ref,
    SellableItem item,
  ) async {
    final l10n = context.l10n;
    final messenger = ScaffoldMessenger.of(context);
    final navigator = Navigator.of(context);
    final money = context.money;
    final debts = await ref.read(debtOverviewProvider.future);
    if (debts.debts.isEmpty || !context.mounted) return;
    // Standart — yopish tartibidagi birinchi qarz (eng qimmati).
    final target = debts.debts.length == 1
        ? debts.debts.single
        : await showDialog<DebtView>(
            context: context,
            builder: (context) => SimpleDialog(
              title: Text(l10n.sellableChooseDebt),
              children: [
                for (final v in debts.debts)
                  SimpleDialogOption(
                    key: Key('sellable-debt-${v.debt.meta.id}'),
                    onPressed: () => Navigator.pop(context, v),
                    child: Text(
                      '${v.debt.creditorName} · ${money(v.debt.remaining)}',
                    ),
                  ),
              ],
            ),
          );
    if (target == null) return;
    try {
      final r = await (await ref.read(
        debtServiceProvider.future,
      )).applySale(item, target.debt);
      refreshMoneyViews(ref);
      messenger.showSnackBar(
        SnackBar(
          content: Text(
            l10n.payoffApplied(
              money(r.payments.last.amount),
              target.debt.creditorName,
            ),
          ),
        ),
      );
      await showDebtClosed(navigator, ref, r);
    } on Object {
      AppLog.event('sellable_apply_failed');
      messenger.showSnackBar(SnackBar(content: Text(l10n.genericError)));
    }
  }

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final l10n = context.l10n;
    final money = context.money;
    final items = ref.watch(sellablesProvider);
    final debts = ref.watch(debtOverviewProvider).valueOrNull;
    final names = {
      for (final v in debts?.debts ?? const <DebtView>[])
        v.debt.meta.id: v.debt.creditorName,
    };
    return Scaffold(
      appBar: AppBar(title: Text(l10n.sellablesTitle)),
      floatingActionButton: FloatingActionButton.extended(
        key: const Key('sellable-add'),
        icon: const Icon(Icons.add),
        label: Text(l10n.sellableAdd),
        onPressed: () => _add(context, ref),
      ),
      body: switch (items) {
        AsyncData(:final value) => ListView(
          padding: const EdgeInsets.fromLTRB(16, 8, 16, 96),
          children: [
            Text(l10n.sellablesHint),
            const SizedBox(height: 8),
            if (value.isEmpty)
              Padding(
                padding: const EdgeInsets.symmetric(vertical: 12),
                child: Text(l10n.sellablesEmpty),
              ),
            for (final s in value)
              Card(
                key: Key('sellable-${s.meta.id}'),
                child: ListTile(
                  leading: Icon(
                    s.isSold ? Icons.check_circle_outline : Icons.sell_outlined,
                  ),
                  title: Text(s.name),
                  subtitle: Text(
                    !s.isSold
                        ? l10n.sellableListed(money(s.estimated))
                        : s.debtId == null
                        ? l10n.sellableSold(money(s.soldFor!))
                        : l10n.sellableAppliedTo(
                            money(s.soldFor!),
                            names[s.debtId] ?? '—',
                          ),
                  ),
                  trailing: !s.isSold
                      ? TextButton(
                          key: Key('sellable-sold-${s.meta.id}'),
                          onPressed: () => _sold(context, ref, s),
                          child: Text(l10n.sellableMarkSold),
                        )
                      : s.awaitsApplying && names.isNotEmpty
                      ? FilledButton(
                          key: Key('sellable-apply-${s.meta.id}'),
                          onPressed: () => _apply(context, ref, s),
                          child: Text(l10n.payoffApply),
                        )
                      : null,
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
