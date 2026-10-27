import 'dart:async';

import 'package:baraka_daftari/core/logging/app_log.dart';
import 'package:baraka_daftari/core/security/pin/pin_service.dart';
import 'package:baraka_daftari/core/security/security_settings.dart';
import 'package:baraka_daftari/core/time/clock.dart';
import 'package:baraka_daftari/core/widget/widget_bridge.dart';
import 'package:baraka_daftari/features/lock/domain/lock_status.dart';
import 'package:flutter/widgets.dart';
import 'package:riverpod_annotation/riverpod_annotation.dart';

part 'app_lock_controller.g.dart';

/// Ilova qulfi holati va fon → qaytish tsikli.
///
/// Ilova fonga o'tgan paytdan boshlab [SecuritySettings.lockTimeoutMinutes]
/// (standart 2 daqiqa) o'tsa, qaytishda qayta qulflanadi.
@Riverpod(keepAlive: true)
class AppLockController extends _$AppLockController {
  DateTime? _backgroundedAt;
  Duration _timeout = const Duration(minutes: 2);

  @override
  LockStatus build() {
    final listener = AppLifecycleListener(onStateChange: _onLifecycleChanged);
    ref.onDispose(listener.dispose);
    unawaited(_init());
    return LockStatus.loading;
  }

  Future<void> _init() async {
    try {
      final settings = await ref
          .read(securitySettingsRepositoryProvider)
          .load();
      _timeout = Duration(minutes: settings.lockTimeoutMinutes);
      final hasPin = await ref.read(pinServiceProvider).isPinSet();
      state = hasPin ? LockStatus.locked : LockStatus.needsSetup;
    } on Object {
      // O'qib bo'lmasa ham ilova ochiq qolmaydi.
      AppLog.event('lock_init_failed');
      state = LockStatus.locked;
    }
  }

  void _onLifecycleChanged(AppLifecycleState lifecycle) {
    if (state != LockStatus.unlocked) return;
    final now = ref.read(clockProvider).nowUtc();
    switch (lifecycle) {
      case AppLifecycleState.hidden:
      case AppLifecycleState.paused:
        if (_backgroundedAt == null) {
          _backgroundedAt = now;
          ref.read(widgetVisibilityProvider).openFor(now, _timeout);
        }
      case AppLifecycleState.resumed:
        final since = _backgroundedAt;
        _backgroundedAt = null;
        if (since != null && now.difference(since) >= _timeout) {
          lock();
        } else {
          ref.read(widgetVisibilityProvider).openFor(now, _timeout);
        }
      case AppLifecycleState.inactive:
      case AppLifecycleState.detached:
        break;
    }
  }

  void unlock() {
    _backgroundedAt = null;
    state = LockStatus.unlocked;
    ref
        .read(widgetVisibilityProvider)
        .openFor(ref.read(clockProvider).nowUtc(), _timeout);
  }

  void lock() {
    _backgroundedAt = null;
    state = LockStatus.locked;
    ref.read(widgetVisibilityProvider).locked();
  }
}
