import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../app/i18n.dart';
import '../../app/theme.dart';
import '../../core/core.dart';
import '../../core/query.dart';
import '../../shared/format.dart';
import '../../shared/widgets.dart';

/// «Kelajagim»: odat (streak) summadan oldin; pul olish — PIN va sabab bilan (friction).
class VaultScreen extends ConsumerStatefulWidget {
  const VaultScreen({required this.spaceId, super.key});

  final String spaceId;

  @override
  ConsumerState<VaultScreen> createState() => _VaultScreenState();
}

class _VaultScreenState extends ConsumerState<VaultScreen> with ActionState {
  final _amount = TextEditingController();
  final _reason = TextEditingController();
  final _pin = TextEditingController();
  final _initial = TextEditingController();
  bool _withdrawing = false;

  @override
  void dispose() {
    for (final c in [_amount, _reason, _pin, _initial]) {
      c.dispose();
    }
    super.dispose();
  }

  Future<void> _withdraw() async {
    final secret = await ref.read(sessionActionsProvider).secret();
    final r = await act(
      () => ref
          .read(coreProvider)
          .withdrawFromVault(
            platformSecret: secret,
            spaceId: widget.spaceId,
            pin: _pin.text,
            amount: _amount.text,
            reason: _reason.text,
          ),
    );
    _pin.clear();
    if (r != null) {
      setState(() => _withdrawing = false);
      _amount.clear();
      _reason.clear();
    }
  }

  Future<void> _addInitial() async {
    final r = await act(
      () => ref.read(coreProvider).recordInitialBalance(spaceId: widget.spaceId, amount: _initial.text),
    );
    if (r != null) _initial.clear();
  }

  @override
  Widget build(BuildContext context) {
    final id = widget.spaceId;
    final v = ref.watch(query(['vault', id], (c) => c.vault(spaceId: id))).valueOrNull;
    final p = context.palette;
    return ScreenBody(
      mentorKey: 'mentor.vault',
      children: [
        Kpi(
          label: context.t('vault.habitFirst'),
          value: v == null ? '…' : context.t('home.streak', {'count': v.streak.currentWeeks}),
          hint: v == null ? null : '${context.t('vault.balance')}: ${v.balance.formatted}',
        ),
        if (v != null && v.history.isEmpty)
          SectionCard(
            children: [
              AmountField(label: context.t('vault.initial'), controller: _initial),
              const SizedBox(height: 8),
              Align(
                alignment: Alignment.centerRight,
                child: OutlinedButton(onPressed: busy ? null : _addInitial, child: Text(context.t('common.save'))),
              ),
            ],
          ),
        if (_withdrawing)
          SectionCard(
            children: [
              Text(context.t('vault.withdrawHint'), style: TextStyle(color: p.warn)),
              const SizedBox(height: 4),
              Hint(context.t('vault.notForStudy')),
              const SizedBox(height: 12),
              AmountField(label: context.t('common.amount'), controller: _amount),
              const SizedBox(height: 12),
              Field(label: context.t('vault.reason'), controller: _reason),
              const SizedBox(height: 12),
              PinField(label: context.t('lock.pin'), controller: _pin),
              ErrorText(error),
              const SizedBox(height: 8),
              Row(
                mainAxisAlignment: MainAxisAlignment.end,
                children: [
                  TextButton(
                    onPressed: () => setState(() => _withdrawing = false),
                    child: Text(context.t('common.cancel')),
                  ),
                  const SizedBox(width: 8),
                  FilledButton(onPressed: busy ? null : _withdraw, child: Text(context.t('vault.withdraw'))),
                ],
              ),
            ],
          )
        else
          Align(
            alignment: Alignment.centerLeft,
            child: OutlinedButton(
              onPressed: () => setState(() => _withdrawing = true),
              child: Text(context.t('vault.withdraw')),
            ),
          ),
        if (!_withdrawing) ErrorText(error),
        SectionCard(
          title: context.t('vault.history'),
          children: [
            for (final h in v?.history ?? <VaultTxDto>[]) ValueRow(showDate(h.occurredOn), h.amount.formatted),
          ],
        ),
      ],
    );
  }
}
