import 'package:flutter/material.dart';
import 'package:flutter_localizations/flutter_localizations.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';

import '../core/core.dart';
import '../core/prefs.dart';
import '../features/lock/lock_screen.dart';
import '../features/setup/setup_screen.dart';
import 'i18n.dart';
import 'shell.dart';
import 'theme.dart';

/// Shu qurilmaning ko'rinish sozlamalari (shrift, mavzu, til) — `PrefsStore` da saqlanadi.
final displayProvider = StateProvider<DisplayPrefs>((ref) => ref.read(servicesProvider).prefs.read());

/// Sessiya holatiga qarab yo'nalish: onboarding → qulf → ilova (desktop `App.tsx`).
final routerProvider = Provider<GoRouter>((ref) {
  final refresh = ValueNotifier<int>(0);
  ref
    ..listen(sessionProvider, (_, _) => refresh.value++)
    ..onDispose(refresh.dispose);
  return GoRouter(
    refreshListenable: refresh,
    initialLocation: '/',
    redirect: (context, state) {
      final s = ref.read(sessionProvider).valueOrNull;
      if (s == null) return null;
      final target = !s.initialized ? '/setup' : (!s.unlocked ? '/lock' : '/');
      return state.matchedLocation == target ? null : target;
    },
    routes: [
      GoRoute(path: '/', builder: (_, _) => const Shell()),
      GoRoute(path: '/setup', builder: (_, _) => const SetupScreen()),
      GoRoute(
        path: '/lock',
        builder: (_, _) => Consumer(
          builder: (context, ref, _) => LockScreen(lockedUntil: ref.watch(sessionProvider).valueOrNull?.lockedUntil),
        ),
      ),
    ],
  );
});

class BarakaApp extends ConsumerWidget {
  const BarakaApp({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final display = ref.watch(displayProvider);
    final tr = ref.watch(trProvider).valueOrNull;
    final session = ref.watch(sessionProvider);
    // Matnlar yoki sessiya holati yuklanguncha — faqat fon (oq chaqnashsiz).
    if (tr == null || !session.hasValue) {
      return ColoredBox(color: (display.dark ? BarakaPalette.dark : BarakaPalette.light).paper);
    }
    return MaterialApp.router(
      title: 'Baraka Dastur',
      debugShowCheckedModeBanner: false,
      theme: barakaTheme(dark: display.dark),
      locale: tr.flutterLocale,
      supportedLocales: const [
        Locale('uz'),
        Locale.fromSubtags(languageCode: 'uz', scriptCode: 'Cyrl'),
        Locale('ru'),
      ],
      localizationsDelegates: GlobalMaterialLocalizations.delegates,
      routerConfig: ref.watch(routerProvider),
      builder: (context, child) {
        final mq = MediaQuery.of(context);
        // Shrift masshtabi: tizimnikiga qo'shimcha (100–150 %).
        final scale = mq.textScaler.scale(1) * display.fontScale / 100;
        return MediaQuery(
          data: mq.copyWith(textScaler: TextScaler.linear(scale)),
          child: TrScope(tr: tr, child: child ?? const SizedBox.shrink()),
        );
      },
    );
  }
}
