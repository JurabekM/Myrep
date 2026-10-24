import 'dart:async';

import 'package:baraka_daftari/app/l10n/l10n.dart';
import 'package:baraka_daftari/app/refresh.dart';
import 'package:baraka_daftari/app/widgets/money_input.dart';
import 'package:baraka_daftari/core/domain/enums.dart';
import 'package:baraka_daftari/core/errors/data_exceptions.dart';
import 'package:baraka_daftari/core/logging/app_log.dart';
import 'package:baraka_daftari/core/money/money.dart';
import 'package:baraka_daftari/core/money/money_format.dart';
import 'package:baraka_daftari/features/lock/presentation/pin_confirm_dialog.dart';
import 'package:baraka_daftari/features/vault/data/vault_providers.dart';
import 'package:baraka_daftari/features/vault/domain/reserve.dart';
import 'package:baraka_daftari/features/vault/domain/vault_service.dart';
import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

/// «Kelajagim»dan pul olish (SPEC 2.2): eslatma → summa va sabab (majburiy)
/// → o'ylash pauzasi → PIN qayta so'raladi.
class WithdrawScreen extends ConsumerStatefulWidget {
  const WithdrawScreen({super.key});

  /// O'ylash pauzasi (SPEC 2.2: «pauza qo'yiladi»).
  static const pause = Duration(seconds: 5);

  @override
  ConsumerState<WithdrawScreen> createState() => _WithdrawScreenState();
}

class _WithdrawScreenState extends ConsumerState<WithdrawScreen> {
  final _amount = TextEditingController();
  final _reason = TextEditingController();
  bool _busy = false;
  VaultType _from = VaultType.qorovul;
  bool _emergency = false;

  @override
  void dispose() {
    _amount.dispose();
    _reason.dispose();
    super.dispose();
  }

  Money? _parsed(VaultOverview o) =>
      MoneyParser.tryParse(_amount.text, o.balance.currency);

  /// Tanlangan jamg'arma balansi.
  Money _available(VaultOverview o) =>
      _from == VaultType.qorovul ? o.reserveBalance : o.growthBalance;

  bool _valid(VaultOverview o) {
    final m = _parsed(o);
    return m != null &&
        m.isPositive &&
        m <= _available(o) &&
        _reason.text.trim().isNotEmpty &&
        // SPEC 2C.3: «bu haqiqatan favqulodda holatmi?»
        (_from != VaultType.qorovul || _emergency);
  }

  Future<void> _submit(VaultOverview o) async {
    final amount = _parsed(o)!;
    final confirmed = await showDialog<bool>(
      context: context,
      barrierDismissible: false,
      builder: (_) => _PauseDialog(amount: context.money(amount)),
    );
    if (confirmed != true || !mounted) return;
    final approval = await showPinConfirmDialog(context);
    if (approval == null || !mounted) return;

    setState(() => _busy = true);
    final l10n = context.l10n;
    final messenger = ScaffoldMessenger.of(context);
    final navigator = Navigator.of(context);
    final text = context.money(amount);
    try {
      final service = await ref.read(vaultServiceProvider.future);
      await service.withdraw(
        amount: amount,
        reason: _reason.text,
        approval: approval,
        from: _from,
        emergencyConfirmed: _emergency,
      );
      refreshMoneyViews(ref);
      messenger.showSnackBar(SnackBar(content: Text(l10n.withdrawDone(text))));
      if (_from == VaultType.qorovul && mounted) {
        // Qayta to'ldirish rejasi taklifi (SPEC 2C.3).
        final plan = refillPlan(amount);
        await showDialog<void>(
          context: context,
          builder: (context) => AlertDialog(
            key: const Key('refill-plan'),
            title: Text(l10n.refillTitle),
            content: Text(
              l10n.refillPlan(context.money(plan.monthly), plan.months),
            ),
            actions: [
              FilledButton(
                onPressed: () => Navigator.pop(context),
                child: Text(l10n.ok),
              ),
            ],
          ),
        );
      }
      navigator.pop();
    } on DomainRuleException catch (e) {
      AppLog.event('withdraw_rejected_${e.code}');
      messenger.showSnackBar(
        SnackBar(
          content: Text(
            e.code == VaultService.errInsufficient
                ? l10n.withdrawErrorAmount
                : l10n.genericError,
          ),
        ),
      );
      if (mounted) setState(() => _busy = false);
    } on Object {
      AppLog.event('withdraw_failed');
      messenger.showSnackBar(SnackBar(content: Text(l10n.genericError)));
      if (mounted) setState(() => _busy = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    final l10n = context.l10n;
    final overview = ref.watch(vaultOverviewProvider);
    return Scaffold(
      appBar: AppBar(title: Text(l10n.withdrawTitle)),
      body: switch (overview) {
        AsyncData(:final value) => _body(context, value),
        AsyncError() => Center(child: Text(l10n.genericError)),
        _ => const Center(child: CircularProgressIndicator()),
      },
    );
  }

  Widget _body(BuildContext context, VaultOverview o) {
    final l10n = context.l10n;
    final theme = Theme.of(context);
    final parsed = _parsed(o);
    final tooMuch = parsed != null && parsed > _available(o);
    return Center(
      child: ConstrainedBox(
        constraints: const BoxConstraints(maxWidth: 620),
        child: ListView(
          padding: const EdgeInsets.all(16),
          children: [
            Card(
              color: theme.colorScheme.tertiaryContainer,
              child: Padding(
                padding: const EdgeInsets.all(16),
                child: Text(
                  l10n.withdrawReminder,
                  key: const Key('withdraw-reminder'),
                  style: theme.textTheme.bodyLarge?.copyWith(
                    color: theme.colorScheme.onTertiaryContainer,
                  ),
                ),
              ),
            ),
            const SizedBox(height: 16),
            if (o.growthBalance.isPositive) ...[
              Text(l10n.withdrawFrom, style: theme.textTheme.labelLarge),
              const SizedBox(height: 4),
              SegmentedButton<VaultType>(
                key: const Key('withdraw-from'),
                showSelectedIcon: false,
                segments: [
                  ButtonSegment(
                    value: VaultType.qorovul,
                    label: Text(l10n.reserveTitle),
                  ),
                  ButtonSegment(
                    value: VaultType.osadigan,
                    label: Text(l10n.growthTitle),
                  ),
                ],
                selected: {_from},
                onSelectionChanged: (v) => setState(() => _from = v.single),
              ),
              const SizedBox(height: 12),
            ],
            Text(l10n.withdrawAvailable(context.money(_available(o)))),
            const SizedBox(height: 12),
            TextField(
              key: const Key('withdraw-amount'),
              controller: _amount,
              keyboardType: TextInputType.number,
              inputFormatters: [FilteringTextInputFormatter.digitsOnly],
              decoration: InputDecoration(
                labelText: l10n.withdrawAmountLabel,
                border: const OutlineInputBorder(),
                errorText: tooMuch ? l10n.withdrawErrorAmount : null,
              ),
              onChanged: (_) => setState(() {}),
            ),
            const SizedBox(height: 12),
            TextField(
              key: const Key('withdraw-reason'),
              controller: _reason,
              maxLength: 200,
              decoration: InputDecoration(
                labelText: l10n.withdrawReasonLabel,
                hintText: l10n.withdrawReasonHint,
                border: const OutlineInputBorder(),
              ),
              onChanged: (_) => setState(() {}),
            ),
            if (_from == VaultType.qorovul)
              CheckboxListTile(
                key: const Key('withdraw-emergency'),
                contentPadding: EdgeInsets.zero,
                controlAffinity: ListTileControlAffinity.leading,
                title: Text(l10n.withdrawEmergency),
                subtitle: Text(l10n.withdrawEmergencyHint),
                value: _emergency,
                onChanged: (v) => setState(() => _emergency = v ?? false),
              ),
            const SizedBox(height: 8),
            FilledButton(
              key: const Key('withdraw-continue'),
              onPressed: !_busy && _valid(o) ? () => _submit(o) : null,
              child: Text(l10n.withdrawContinue),
            ),
          ],
        ),
      ),
    );
  }
}

class _PauseDialog extends StatefulWidget {
  const _PauseDialog({required this.amount});

  final String amount;

  @override
  State<_PauseDialog> createState() => _PauseDialogState();
}

class _PauseDialogState extends State<_PauseDialog> {
  late int _left = WithdrawScreen.pause.inSeconds;
  Timer? _timer;

  @override
  void initState() {
    super.initState();
    _timer = Timer.periodic(const Duration(seconds: 1), (t) {
      setState(() => _left--);
      if (_left <= 0) t.cancel();
    });
  }

  @override
  void dispose() {
    _timer?.cancel();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    final l10n = context.l10n;
    return AlertDialog(
      title: Text(l10n.withdrawPauseTitle),
      content: Text(l10n.withdrawPauseBody(widget.amount)),
      actions: [
        TextButton(
          key: const Key('withdraw-pause-cancel'),
          onPressed: () => Navigator.of(context).pop(false),
          child: Text(l10n.withdrawPauseCancel),
        ),
        FilledButton(
          key: const Key('withdraw-pause-confirm'),
          onPressed: _left > 0 ? null : () => Navigator.of(context).pop(true),
          child: Text(
            _left > 0
                ? l10n.withdrawPauseWait(_left)
                : l10n.withdrawPauseConfirm,
          ),
        ),
      ],
    );
  }
}
