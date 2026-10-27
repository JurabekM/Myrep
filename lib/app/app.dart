import 'package:baraka_daftari/app/demo/demo_gate.dart';
import 'package:baraka_daftari/app/l10n/gen/app_localizations.dart';
import 'package:baraka_daftari/app/router/app_router.dart';
import 'package:baraka_daftari/app/router/secure_screen_sync.dart';
import 'package:baraka_daftari/app/settings/settings_controller.dart';
import 'package:baraka_daftari/app/theme/app_theme.dart';
import 'package:baraka_daftari/core/security/integrity/integrity_service.dart';
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

class BarakaApp extends ConsumerWidget {
  const BarakaApp({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final settings = ref.watch(settingsControllerProvider);
    final router = ref.watch(appRouterProvider);
    // Marshrut darajasidagi FLAG_SECURE va bir martalik integrity tekshiruvi.
    ref
      ..watch(secureScreenSyncProvider)
      ..watch(integrityRisksProvider);

    return MaterialApp.router(
      onGenerateTitle: (context) => AppLocalizations.of(context).appTitle,
      debugShowCheckedModeBanner: false,
      theme: AppTheme.light(),
      darkTheme: AppTheme.dark(),
      themeMode: settings.themeMode,
      locale: settings.language.locale,
      supportedLocales: AppLocalizations.supportedLocales,
      localizationsDelegates: AppLocalizations.localizationsDelegates,
      routerConfig: router,
      // Demo yig'ishda «DEMO» belgisi va muddat (oddiy reliz'da o'zgarishsiz).
      builder: (context, child) => DemoGate(child: child ?? const SizedBox()),
    );
  }
}
