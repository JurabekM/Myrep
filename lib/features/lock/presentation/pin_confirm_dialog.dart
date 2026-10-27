import 'dart:async';

import 'package:baraka_daftari/app/l10n/l10n.dart';
import 'package:baraka_daftari/core/logging/app_log.dart';
import 'package:baraka_daftari/core/security/pin/pin_service.dart';
import 'package:baraka_daftari/core/time/clock.dart';
import 'package:baraka_daftari/features/lock/presentation/widgets/pin_pad.dart';
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

/// Muhim amaldan oldin PIN'ni qayta so'raydi. To'g'ri bo'lsa bir martalik
/// [PinApproval], bekor qilinsa `null`. Lockout qoidalari amal qiladi.
Future<PinApproval?> showPinConfirmDialog(BuildContext context) =>
    Navigator.of(context).push<PinApproval>(
      MaterialPageRoute(
        fullscreenDialog: true,
        builder: (_) => const PinConfirmScreen(),
      ),
    );

class PinConfirmScreen extends ConsumerStatefulWidget {
  const PinConfirmScreen({super.key});

  @override
  ConsumerState<PinConfirmScreen> createState() => _PinConfirmScreenState();
}

class _PinConfirmScreenState extends ConsumerState<PinConfirmScreen> {
  bool _busy = false;
  String? _message;

  Future<void> _onPin(String pin) async {
    setState(() {
      _busy = true;
      _message = null;
    });
    final l10n = context.l10n;
    try {
      final (check, approval) = await ref.read(pinServiceProvider).approve(pin);
      if (!mounted) return;
      switch (check) {
        case PinAccepted():
          Navigator.of(context).pop(approval);
          return;
        case PinRejected(:final attemptsBeforeLockout):
          _message = l10n.pinWrong(attemptsBeforeLockout);
        case PinLockedOut(:final until):
          final left = until.difference(ref.read(clockProvider).nowUtc());
          final s = left.isNegative ? 0 : left.inSeconds + 1;
          _message = l10n.pinLockedOut(
            '${(s ~/ 60).toString().padLeft(2, '0')}:'
            '${(s % 60).toString().padLeft(2, '0')}',
          );
      }
    } on Object {
      AppLog.event('pin_confirm_error');
      _message = l10n.pinErrorGeneric;
    }
    if (mounted) setState(() => _busy = false);
  }

  @override
  Widget build(BuildContext context) {
    final l10n = context.l10n;
    final theme = Theme.of(context);
    return Scaffold(
      appBar: AppBar(title: Text(l10n.pinConfirmTitle)),
      body: SafeArea(
        child: Center(
          child: SingleChildScrollView(
            padding: const EdgeInsets.all(16),
            child: Column(
              children: [
                SizedBox(
                  height: 48,
                  child: _message == null
                      ? null
                      : Text(
                          _message!,
                          key: const Key('pin-confirm-message'),
                          textAlign: TextAlign.center,
                          style: theme.textTheme.bodyMedium?.copyWith(
                            color: theme.colorScheme.error,
                          ),
                        ),
                ),
                PinPad(
                  enabled: !_busy,
                  onCompleted: (pin) => unawaited(_onPin(pin)),
                ),
              ],
            ),
          ),
        ),
      ),
    );
  }
}
