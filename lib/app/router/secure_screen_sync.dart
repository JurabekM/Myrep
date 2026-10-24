import 'dart:async';

import 'package:baraka_daftari/app/router/app_router.dart';
import 'package:baraka_daftari/app/router/app_routes.dart';
import 'package:baraka_daftari/core/logging/app_log.dart';
import 'package:baraka_daftari/core/security/security_bridge.dart';
import 'package:riverpod_annotation/riverpod_annotation.dart';

part 'secure_screen_sync.g.dart';

/// Marshrut darajasidagi FLAG_SECURE: joriy manzil [AppRoutes.secure] da
/// bo'lsa skrinshot va ekran yozuvi taqiqlanadi. Holat — oxirgi yuborilgan
/// qiymat.
@Riverpod(keepAlive: true)
class SecureScreenSync extends _$SecureScreenSync {
  @override
  bool build() {
    final router = ref.watch(appRouterProvider);

    // `currentConfiguration.uri` push qilingan ekranni emas, asosiy manzilni
    // beradi — shuning uchun eng yuqoridagi marshrut holati olinadi.
    String? topLocation() => router.routerDelegate.currentConfiguration.isEmpty
        ? null
        : router.state.matchedLocation;
    // Parametrli moliyaviy ekranlar (masalan, `/debts/:debtId`) naqsh
    // bo'yicha tekshiriladi.
    bool isSecure() =>
        AppRoutes.secure.contains(topLocation()) ||
        AppRoutes.securePatterns.contains(router.state.fullPath);

    void onRouteChanged() {
      final enabled = isSecure();
      if (enabled == state) return;
      state = enabled;
      unawaited(_send(enabled: enabled));
    }

    router.routerDelegate.addListener(onRouteChanged);
    ref.onDispose(() => router.routerDelegate.removeListener(onRouteChanged));

    // Boshlang'ich holat: konfiguratsiya hali bo'sh bo'lsa ham xavfsiz tomonda.
    final initial = topLocation() == null || isSecure();
    unawaited(_send(enabled: initial));
    return initial;
  }

  Future<void> _send({required bool enabled}) async {
    try {
      await ref.read(securityApiProvider).setSecureFlag(enabled: enabled);
    } on Object {
      AppLog.event('secure_flag_failed');
    }
  }
}
