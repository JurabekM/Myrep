import 'dart:async';

import 'package:baraka_daftari/app/l10n/l10n.dart';
import 'package:baraka_daftari/app/widgets/brand_logo.dart';
import 'package:baraka_daftari/app/widgets/settings_actions.dart';
import 'package:baraka_daftari/core/logging/app_log.dart';
import 'package:baraka_daftari/core/security/pin/pin_service.dart';
import 'package:baraka_daftari/core/security/security_bridge.dart';
import 'package:baraka_daftari/core/security/security_settings.dart';
import 'package:baraka_daftari/core/time/clock.dart';
import 'package:baraka_daftari/features/lock/domain/lock_status.dart';
import 'package:baraka_daftari/features/lock/presentation/app_lock_controller.dart';
import 'package:baraka_daftari/features/lock/presentation/widgets/integrity_banner.dart';
import 'package:baraka_daftari/features/lock/presentation/widgets/lock_layout.dart';
import 'package:baraka_daftari/features/lock/presentation/widgets/pin_pad.dart';
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

class LockScreen extends ConsumerStatefulWidget {
  const LockScreen({super.key});

  @override
  ConsumerState<LockScreen> createState() => _LockScreenState();
}

class _LockScreenState extends ConsumerState<LockScreen> {
  bool _busy = false;
  String? _message;
  DateTime? _lockedUntil;
  Timer? _ticker;
  bool _biometricReady = false;
  bool _autoPromptDone = false;

  @override
  void initState() {
    super.initState();
    unawaited(_prepare());
  }

  @override
  void dispose() {
    _ticker?.cancel();
    super.dispose();
  }

  Future<void> _prepare() async {
    try {
      final until = await ref.read(pinServiceProvider).activeLockoutUntil();
      if (until != null) _startCountdown(until);
      final settings = await ref
          .read(securitySettingsRepositoryProvider)
          .load();
      if (settings.biometricEnabled) {
        final availability = await ref
            .read(securityApiProvider)
            .getBiometricAvailability();
        _biometricReady = availability == BiometricAvailability.available;
      }
    } on Object {
      AppLog.event('lock_prepare_failed');
    }
    if (!mounted) return;
    setState(() {});
    _maybeAutoPrompt();
  }

  /// Biometriya yoqilgan bo'lsa, ekran ochilishi bilan bir marta so'raladi.
  void _maybeAutoPrompt() {
    if (_autoPromptDone || !_biometricReady) return;
    if (ref.read(appLockControllerProvider) != LockStatus.locked) return;
    _autoPromptDone = true;
    unawaited(_biometric());
  }

  void _startCountdown(DateTime until) {
    _ticker?.cancel();
    _lockedUntil = until;
    _ticker = Timer.periodic(const Duration(seconds: 1), (_) {
      if (!mounted) return;
      final now = ref.read(clockProvider).nowUtc();
      setState(() {
        if (!now.isBefore(_lockedUntil!)) {
          _lockedUntil = null;
          _message = null;
          _ticker?.cancel();
        }
      });
    });
  }

  Future<void> _onPin(String pin) async {
    setState(() {
      _busy = true;
      _message = null;
    });
    try {
      final result = await ref.read(pinServiceProvider).verify(pin);
      if (!mounted) return;
      switch (result) {
        case PinAccepted():
          ref.read(appLockControllerProvider.notifier).unlock();
        case PinRejected(:final attemptsBeforeLockout):
          _message = context.l10n.pinWrong(attemptsBeforeLockout);
        case PinLockedOut(:final until):
          _startCountdown(until);
      }
    } on Object {
      AppLog.event('pin_verify_error');
      if (mounted) _message = context.l10n.pinErrorGeneric;
    }
    if (mounted) setState(() => _busy = false);
  }

  Future<void> _biometric() async {
    final l10n = context.l10n;
    try {
      final outcome = await ref
          .read(securityApiProvider)
          .authenticate(
            l10n.biometricPromptTitle,
            l10n.biometricPromptSubtitle,
            l10n.biometricPromptCancel,
          );
      if (!mounted) return;
      switch (outcome) {
        case BiometricOutcome.success:
          await ref.read(pinServiceProvider).resetFailures();
          ref.read(appLockControllerProvider.notifier).unlock();
        case BiometricOutcome.lockedOut:
          setState(() => _message = l10n.biometricLockedOut);
        case BiometricOutcome.failed:
        case BiometricOutcome.cancelled:
        case BiometricOutcome.unavailable:
          break;
      }
    } on Object {
      AppLog.event('biometric_error');
    }
  }

  String _remaining() {
    final left = _lockedUntil!.difference(ref.read(clockProvider).nowUtc());
    final ms = left.inMilliseconds;
    final seconds = ms <= 0 ? 0 : (ms + 999) ~/ 1000;
    final mm = (seconds ~/ 60).toString().padLeft(2, '0');
    final ss = (seconds % 60).toString().padLeft(2, '0');
    return '$mm:$ss';
  }

  @override
  Widget build(BuildContext context) {
    final l10n = context.l10n;
    final status = ref.watch(appLockControllerProvider);
    ref.listen(appLockControllerProvider, (_, next) {
      if (next == LockStatus.locked) _maybeAutoPrompt();
    });
    final theme = Theme.of(context);
    final lockedOut = _lockedUntil != null;
    final info = lockedOut ? l10n.pinLockedOut(_remaining()) : _message;

    return Scaffold(
      appBar: AppBar(actions: const [SettingsActions()]),
      body: status == LockStatus.loading
          ? const Center(child: CircularProgressIndicator())
          : LockLayout(
              header: [
                const IntegrityBanner(),
                const Center(child: BrandLogo()),
                const SizedBox(height: 12),
                Text(
                  l10n.appTitle,
                  style: theme.textTheme.headlineMedium,
                  textAlign: TextAlign.center,
                ),
                const SizedBox(height: 4),
                Text(
                  l10n.lockGreeting,
                  style: theme.textTheme.bodyMedium?.copyWith(
                    color: theme.colorScheme.onSurfaceVariant,
                  ),
                  textAlign: TextAlign.center,
                ),
                const SizedBox(height: 24),
                Text(
                  _busy ? l10n.pinVerifying : l10n.lockEnterPin,
                  style: theme.textTheme.titleMedium,
                  textAlign: TextAlign.center,
                ),
              ],
              message: info,
              pad: PinPad(
                key: const Key('lock-pin-pad'),
                enabled: !_busy && !lockedOut,
                onCompleted: _onPin,
                onBiometric: _biometricReady ? _biometric : null,
              ),
            ),
    );
  }
}
