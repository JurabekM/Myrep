import 'package:flutter/material.dart';
import 'package:flutter_localizations/flutter_localizations.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import 'core/providers.dart';
import 'l10n/gen/app_localizations.dart';
import 'router.dart';
import 'theme/app_theme.dart';

/// Katta shrift rejimi koeffitsienti (dala sharoiti, prompt 8-bo'lim).
const largeTextFactor = 1.3;

class ZanjirApp extends ConsumerWidget {
  const ZanjirApp({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final locale = ref.watch(localeProvider).value ?? 'uz';
    final large = ref.watch(largeTextProvider).value ?? false;
    return MaterialApp.router(
      onGenerateTitle: (context) => AppLocalizations.of(context).appTitle,
      theme: buildDarkTheme(),
      themeMode: ThemeMode.dark,
      locale: Locale(locale),
      supportedLocales: AppLocalizations.supportedLocales,
      localizationsDelegates: const [
        AppLocalizations.delegate,
        GlobalMaterialLocalizations.delegate,
        GlobalWidgetsLocalizations.delegate,
        GlobalCupertinoLocalizations.delegate,
      ],
      builder: (context, child) {
        if (!large) return child!;
        final mq = MediaQuery.of(context);
        return MediaQuery(
          data: mq.copyWith(textScaler: TextScaler.linear(mq.textScaler.scale(1) * largeTextFactor)),
          child: child!,
        );
      },
      routerConfig: ref.watch(routerProvider),
    );
  }
}
