import 'dart:async';

import 'package:baraka_daftari/app/l10n/l10n.dart';
import 'package:baraka_daftari/app/widgets/settings_actions.dart';
import 'package:baraka_daftari/core/logging/app_log.dart';
import 'package:baraka_daftari/core/security/pin/pin_policy.dart';
import 'package:baraka_daftari/core/security/pin/pin_service.dart';
import 'package:baraka_daftari/core/security/security_bridge.dart';
import 'package:baraka_daftari/core/security/security_settings.dart';
import 'package:baraka_daftari/features/lock/presentation/app_lock_controller.dart';
import 'package:baraka_daftari/features/lock/presentation/widgets/integrity_banner.dart';
import 'package:baraka_daftari/features/lock/presentation/widgets/lock_layout.dart';
import 'package:baraka_daftari/features/lock/presentation/widgets/pin_pad.dart';
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

enum _Step { enter, confirm, saving, biometricOffer }

/// Birinchi ishga tushirish: PIN (6 raqam) o'rnatiladi, keyin biometriya
/// ixtiyoriy yoqiladi.
class PinSetupScreen extends ConsumerStatefulWidget {
  const PinSetupScreen({super.key});

  @override
  ConsumerState<PinSetupScreen> createState() => _PinSetupScreenState();
}

class _PinSetupScreenState extends ConsumerState<PinSetupScreen> {
  _Step _step = _Step.enter;
  String? _first;
  String? _message;
  int _padGeneration = 0;

  void _restart(String message) => setState(() {
    _step = _Step.enter;
    _first = null;
    _message = message;
    _padGeneration++;
  });

  Future<void> _onPin(String pin) async {
    final l10n = context.l10n;
    if (_step == _Step.enter) {
      if (PinPolicy.validate(pin) != null) {
        setState(() {
          _message = l10n.pinTooSimple;
          _padGeneration++;
        });
        return;
      }
      setState(() {
        _first = pin;
        _step = _Step.confirm;
        _message = null;
        _padGeneration++;
      });
      return;
    }
    if (pin != _first) {
      _restart(l10n.pinSetupMismatch);
      return;
    }
    setState(() => _step = _Step.saving);
    try {
      await ref.read(pinServiceProvider).setPin(pin);
      _first = null;
      final availability = await ref
          .read(securityApiProvider)
          .getBiometricAvailability();
      if (!mounted) return;
      if (availability == BiometricAvailability.available) {
        setState(() => _step = _Step.biometricOffer);
      } else {
        _finish();
      }
    } on Object {
      AppLog.event('pin_setup_failed');
      if (mounted) _restart(l10n.pinErrorGeneric);
    }
  }

  Future<void> _enableBiometric() async {
    final l10n = context.l10n;
    try {
      final outcome = await ref
          .read(securityApiProvider)
          .authenticate(
            l10n.biometricPromptTitle,
            l10n.biometricPromptSubtitle,
            l10n.biometricPromptCancel,
          );
      if (outcome == BiometricOutcome.success) {
        final repo = ref.read(securitySettingsRepositoryProvider);
        await repo.save(
          (await repo.load()).copyWith(biometricEnabled: true),
        );
      }
    } on Object {
      AppLog.event('biometric_enable_failed');
    }
    _finish();
  }

  void _finish() {
    if (!mounted) return;
    ref.read(appLockControllerProvider.notifier).unlock();
  }

  @override
  Widget build(BuildContext context) {
    final l10n = context.l10n;
    final theme = Theme.of(context);
    return Scaffold(
      appBar: AppBar(
        title: Text(l10n.pinSetupTitle),
        actions: const [SettingsActions()],
      ),
      body: switch (_step) {
        _Step.biometricOffer => _BiometricOffer(
          onEnable: () => unawaited(_enableBiometric()),
          onLater: _finish,
        ),
        _ => LockLayout(
          header: [
            const IntegrityBanner(),
            Text(
              switch (_step) {
                _Step.confirm => l10n.pinSetupConfirm,
                _Step.saving => l10n.pinSetupSaving,
                _ => l10n.pinSetupEnter,
              },
              key: const Key('setup-prompt'),
              style: theme.textTheme.titleMedium,
              textAlign: TextAlign.center,
            ),
            const SizedBox(height: 8),
            Text(
              l10n.pinSetupNote,
              style: theme.textTheme.bodyMedium?.copyWith(
                color: theme.colorScheme.onSurfaceVariant,
              ),
              textAlign: TextAlign.center,
            ),
          ],
          message: _message,
          pad: PinPad(
            key: ValueKey('setup-pad-$_padGeneration'),
            enabled: _step != _Step.saving,
            onCompleted: (pin) => unawaited(_onPin(pin)),
          ),
        ),
      },
    );
  }
}

class _BiometricOffer extends StatelessWidget {
  const _BiometricOffer({required this.onEnable, required this.onLater});

  final VoidCallback onEnable;
  final VoidCallback onLater;

  @override
  Widget build(BuildContext context) {
    final l10n = context.l10n;
    final theme = Theme.of(context);
    return SafeArea(
      child: Center(
        child: SingleChildScrollView(
          padding: const EdgeInsets.all(24),
          child: ConstrainedBox(
            constraints: const BoxConstraints(maxWidth: 420),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.stretch,
              children: [
                Icon(
                  Icons.fingerprint,
                  size: 72,
                  color: theme.colorScheme.primary,
                ),
                const SizedBox(height: 16),
                Text(
                  l10n.biometricOfferTitle,
                  style: theme.textTheme.titleLarge,
                  textAlign: TextAlign.center,
                ),
                const SizedBox(height: 8),
                Text(
                  l10n.biometricOfferBody,
                  style: theme.textTheme.bodyLarge,
                  textAlign: TextAlign.center,
                ),
                const SizedBox(height: 24),
                FilledButton(
                  key: const Key('biometric-enable'),
                  onPressed: onEnable,
                  child: Text(l10n.biometricEnable),
                ),
                const SizedBox(height: 8),
                TextButton(
                  key: const Key('biometric-later'),
                  onPressed: onLater,
                  child: Text(l10n.biometricLater),
                ),
              ],
            ),
          ),
        ),
      ),
    );
  }
}
