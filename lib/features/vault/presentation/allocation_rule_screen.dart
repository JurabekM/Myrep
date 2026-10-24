import 'package:baraka_daftari/app/l10n/l10n.dart';
import 'package:baraka_daftari/app/refresh.dart';
import 'package:baraka_daftari/app/widgets/money_input.dart';
import 'package:baraka_daftari/core/domain/enums.dart';
import 'package:baraka_daftari/core/logging/app_log.dart';
import 'package:baraka_daftari/core/money/money.dart';
import 'package:baraka_daftari/features/vault/data/vault_providers.dart';
import 'package:baraka_daftari/features/vault/domain/vault_service.dart';
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

enum _Option { percent5, percent10, fixed }

/// Ulush sozlamalari: 5 % / 10 % / qat'iy summa (oyiga) + progressiv rejim.
class AllocationRuleScreen extends ConsumerStatefulWidget {
  const AllocationRuleScreen({super.key});

  @override
  ConsumerState<AllocationRuleScreen> createState() =>
      _AllocationRuleScreenState();
}

class _AllocationRuleScreenState extends ConsumerState<AllocationRuleScreen> {
  _Option? _option;
  bool _progressive = false;
  Money? _fixed;
  bool _saving = false;

  void _initFrom(VaultOverview o) {
    if (_option != null) return;
    final r = o.rule;
    _fixed = r.fixedAmount;
    _progressive = r.mode == AllocationMode.progressive;
    _option = r.basisPoints == null && r.fixedAmount != null
        ? _Option.fixed
        : (r.basisPoints ?? 0) >= VaultService.targetBasisPoints
        ? _Option.percent10
        : _Option.percent5;
  }

  void _select(_Option? v) => setState(() {
    _option = v;
    if (v == _Option.fixed) _progressive = false;
  });

  Future<void> _save(VaultOverview o) async {
    setState(() => _saving = true);
    final l10n = context.l10n;
    final messenger = ScaffoldMessenger.of(context);
    final navigator = Navigator.of(context);
    try {
      final service = await ref.read(vaultServiceProvider.future);
      final current = o.rule.basisPoints;
      switch (_option!) {
        case _Option.fixed:
          await service.updateRule(
            mode: AllocationMode.fixed,
            fixedAmount: _fixed,
          );
        case _Option.percent5:
        case _Option.percent10:
          final target = _option == _Option.percent10
              ? VaultService.targetBasisPoints
              : VaultService.defaultBasisPoints;
          // Progressiv rejimda erishilgan oraliq ulush (masalan, 7 %)
          // saqlanadi, agar foydalanuvchi variantni o'zgartirmagan bo'lsa.
          final keep =
              _progressive &&
              o.rule.mode == AllocationMode.progressive &&
              current != null &&
              _option == _Option.percent5 &&
              current < VaultService.targetBasisPoints;
          await service.updateRule(
            mode: _progressive
                ? AllocationMode.progressive
                : AllocationMode.fixed,
            basisPoints: keep ? current : target,
          );
      }
      refreshMoneyViews(ref);
      messenger.showSnackBar(SnackBar(content: Text(l10n.ruleSaved)));
      navigator.pop();
    } on Object {
      AppLog.event('rule_save_failed');
      messenger.showSnackBar(SnackBar(content: Text(l10n.genericError)));
      if (mounted) setState(() => _saving = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    final l10n = context.l10n;
    final overview = ref.watch(vaultOverviewProvider);
    return Scaffold(
      appBar: AppBar(title: Text(l10n.ruleTitle)),
      body: switch (overview) {
        AsyncData(:final value) => _body(context, value),
        AsyncError() => Center(child: Text(l10n.genericError)),
        _ => const Center(child: CircularProgressIndicator()),
      },
    );
  }

  Widget _body(BuildContext context, VaultOverview o) {
    _initFrom(o);
    final l10n = context.l10n;
    final canSave =
        !_saving && (_option != _Option.fixed || (_fixed?.isPositive ?? false));
    return Center(
      child: ConstrainedBox(
        constraints: const BoxConstraints(maxWidth: 620),
        child: ListView(
          padding: const EdgeInsets.symmetric(vertical: 8),
          children: [
            Column(
              children: [
                RadioListTile<_Option>(
                  key: const Key('rule-5'),
                  value: _Option.percent5,
                  groupValue: _option,
                  onChanged: _select,
                  title: Text(l10n.rulePercent5),
                ),
                RadioListTile<_Option>(
                  key: const Key('rule-10'),
                  value: _Option.percent10,
                  groupValue: _option,
                  onChanged: _select,
                  title: Text(l10n.rulePercent10),
                ),
                RadioListTile<_Option>(
                  key: const Key('rule-fixed'),
                  value: _Option.fixed,
                  groupValue: _option,
                  onChanged: _select,
                  title: Text(l10n.ruleFixed),
                  subtitle: Text(
                    _fixed == null
                        ? l10n.ruleFixedChoose
                        : l10n.ruleFixedAmount(context.money(_fixed!)),
                  ),
                  secondary: IconButton(
                    key: const Key('rule-fixed-edit'),
                    icon: const Icon(Icons.edit_outlined),
                    tooltip: l10n.ruleFixedChoose,
                    onPressed: () async {
                      final m = await showAmountSheet(
                        context,
                        currency: o.rule.currency,
                        title: l10n.ruleFixed,
                        initial: _fixed,
                      );
                      if (m != null) {
                        setState(() {
                          _fixed = m;
                          _option = _Option.fixed;
                          _progressive = false;
                        });
                      }
                    },
                  ),
                ),
              ],
            ),
            const Divider(),
            SwitchListTile(
              key: const Key('rule-progressive'),
              title: Text(l10n.ruleProgressive),
              subtitle: Text(l10n.ruleProgressiveHint),
              value: _progressive,
              onChanged: _option == _Option.fixed
                  ? null
                  : (v) => setState(() => _progressive = v),
            ),
            Padding(
              padding: const EdgeInsets.all(16),
              child: FilledButton(
                key: const Key('rule-save'),
                onPressed: canSave ? () => _save(o) : null,
                child: Text(l10n.ruleSave),
              ),
            ),
          ],
        ),
      ),
    );
  }
}
