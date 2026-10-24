import 'package:baraka_daftari/app/l10n/l10n.dart';
import 'package:baraka_daftari/app/refresh.dart';
import 'package:baraka_daftari/app/widgets/money_input.dart';
import 'package:baraka_daftari/core/errors/data_exceptions.dart';
import 'package:baraka_daftari/core/logging/app_log.dart';
import 'package:baraka_daftari/features/debts/data/debt_providers.dart';
import 'package:baraka_daftari/features/debts/domain/recovery_service.dart';
import 'package:baraka_daftari/features/household/domain/household.dart';
import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

/// «Qarzdan chiqish» rejimi: 70 / 20 / 10 ulushlari (SPEC 2D.1).
class RecoveryScreen extends ConsumerStatefulWidget {
  const RecoveryScreen({super.key});

  @override
  ConsumerState<RecoveryScreen> createState() => _RecoveryScreenState();
}

class _RecoveryScreenState extends ConsumerState<RecoveryScreen> {
  final _needs = TextEditingController();
  final _debt = TextEditingController();
  final _savings = TextEditingController();
  bool _loaded = false;
  bool _saving = false;

  @override
  void dispose() {
    _needs.dispose();
    _debt.dispose();
    _savings.dispose();
    super.dispose();
  }

  void _fill(RecoverySplit s) {
    _needs.text = '${s.needsBp ~/ 100}';
    _debt.text = '${s.debtBp ~/ 100}';
    _savings.text = '${s.savingsBp ~/ 100}';
  }

  int _pct(TextEditingController c) => int.tryParse(c.text.trim()) ?? 0;

  RecoverySplit get _split => RecoverySplit(
    needsBp: _pct(_needs) * 100,
    debtBp: _pct(_debt) * 100,
    savingsBp: _pct(_savings) * 100,
  );

  Future<void> _save() async {
    final l10n = context.l10n;
    final messenger = ScaffoldMessenger.of(context);
    final navigator = Navigator.of(context);
    setState(() => _saving = true);
    try {
      await (await ref.read(recoveryServiceProvider.future)).enable(_split);
      refreshMoneyViews(ref);
      navigator.pop();
    } on DomainRuleException catch (e) {
      AppLog.event('recovery_rejected_${e.code}');
      messenger.showSnackBar(
        SnackBar(
          content: Text(
            e.code == RecoveryService.errSavingsRequired
                ? l10n.recoverySavingsZero
                : l10n.genericError,
          ),
        ),
      );
      if (mounted) setState(() => _saving = false);
    }
  }

  Future<void> _disable() async {
    final navigator = Navigator.of(context);
    await (await ref.read(recoveryServiceProvider.future)).disable();
    refreshMoneyViews(ref);
    navigator.pop();
  }

  Widget _field(TextEditingController c, String label, Key key) => TextField(
    key: key,
    controller: c,
    keyboardType: TextInputType.number,
    inputFormatters: [
      FilteringTextInputFormatter.digitsOnly,
      LengthLimitingTextInputFormatter(3),
    ],
    decoration: InputDecoration(labelText: label),
    onChanged: (_) => setState(() {}),
  );

  @override
  Widget build(BuildContext context) {
    final l10n = context.l10n;
    final theme = Theme.of(context);
    final money = context.money;
    final state = ref.watch(recoveryStateProvider).valueOrNull;
    if (state == null) {
      return Scaffold(
        appBar: AppBar(title: Text(l10n.recoveryTitle)),
        body: const Center(child: CircularProgressIndicator()),
      );
    }
    if (!_loaded) {
      _fill(state.split);
      _loaded = true;
    }
    final split = _split;
    final savingsTooLow = split.savingsBp < RecoverySplit.minSavingsBp;
    final total = split.totalBp ~/ 100;
    final budget = state.budget == null
        ? null
        : RecoveryBudget.of(
            state.budget!.income,
            split.isValid ? split : state.split,
            state.budget!.mandatoryDebt,
          );
    return Scaffold(
      appBar: AppBar(title: Text(l10n.recoveryTitle)),
      body: ListView(
        padding: const EdgeInsets.fromLTRB(16, 8, 16, 32),
        children: [
          Text(l10n.recoveryOfferBody),
          const SizedBox(height: 8),
          Card(
            child: Padding(
              padding: const EdgeInsets.all(12),
              child: Text(
                l10n.recoveryExplain,
                style: theme.textTheme.bodyMedium?.copyWith(
                  fontStyle: FontStyle.italic,
                ),
              ),
            ),
          ),
          _field(_needs, l10n.recoveryNeeds, const Key('recovery-needs')),
          _field(_debt, l10n.recoveryDebt, const Key('recovery-debt')),
          _field(_savings, l10n.recoverySavings, const Key('recovery-savings')),
          const SizedBox(height: 8),
          if (savingsTooLow)
            Text(
              l10n.recoverySavingsZero,
              key: const Key('recovery-savings-error'),
              style: TextStyle(color: theme.colorScheme.error),
            )
          else if (total != 100)
            Text(
              l10n.recoveryTotalError(total),
              key: const Key('recovery-total-error'),
              style: TextStyle(color: theme.colorScheme.error),
            ),
          TextButton(
            key: const Key('recovery-standard'),
            onPressed: () => setState(() => _fill(RecoverySplit.standard)),
            child: Text(l10n.recoveryStandard),
          ),
          const SizedBox(height: 8),
          if (budget == null)
            Text(l10n.recoveryNoIncome, style: theme.textTheme.bodySmall)
          else
            Card(
              key: const Key('recovery-budget'),
              child: Padding(
                padding: const EdgeInsets.all(16),
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text(
                      l10n.recoveryBudgetTitle(money(budget.income)),
                      style: theme.textTheme.titleSmall,
                    ),
                    const SizedBox(height: 4),
                    Text(l10n.recoveryBudgetNeeds(money(budget.needs))),
                    Text(
                      '  ${l10n.recoveryBudgetMandatory(
                        money(budget.mandatoryDebt),
                      )}',
                    ),
                    Text(
                      '  ${l10n.recoveryBudgetHousehold(
                        money(budget.household),
                      )}',
                    ),
                    Text(l10n.recoveryBudgetDebt(money(budget.debtExtra))),
                    Text(l10n.recoveryBudgetSavings(money(budget.savings))),
                    if (budget.mandatoryExceedsNeeds)
                      Padding(
                        padding: const EdgeInsets.only(top: 8),
                        child: Text(
                          l10n.recoveryMandatoryOver,
                          style: TextStyle(color: theme.colorScheme.error),
                        ),
                      ),
                  ],
                ),
              ),
            ),
          const SizedBox(height: 16),
          FilledButton(
            key: const Key('recovery-save'),
            onPressed: _saving || !split.isValid ? null : _save,
            child: Text(l10n.recoverySaveEnable),
          ),
          if (state.isActive)
            TextButton(
              key: const Key('recovery-disable'),
              onPressed: _saving ? null : _disable,
              child: Text(l10n.recoveryDisable),
            ),
        ],
      ),
    );
  }
}
