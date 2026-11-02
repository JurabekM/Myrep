import 'package:flutter/material.dart';
import 'package:flutter_localizations/flutter_localizations.dart';

import 'state/app_state.dart';
import 'theme.dart';
import 'ui/forecast_screen.dart';
import 'ui/guide_screen.dart';
import 'ui/home_screen.dart';
import 'ui/onboarding_screen.dart';

class HavoRadarApp extends StatelessWidget {
  const HavoRadarApp({super.key, required this.state});

  final AppState state;

  @override
  Widget build(BuildContext context) => AppScope(
        state: state,
        child: ListenableBuilder(
          listenable: state,
          builder: (context, _) => MaterialApp(
            title: 'HavoRadar',
            debugShowCheckedModeBanner: false,
            locale: const Locale('uz'),
            supportedLocales: const [Locale('uz'), Locale('en')],
            localizationsDelegates: GlobalMaterialLocalizations.delegates,
            theme: buildTheme(Tokens.light, Brightness.light),
            darkTheme: buildTheme(Tokens.dark, Brightness.dark),
            themeMode: state.settings.lightTheme ? ThemeMode.light : ThemeMode.dark,
            home: !state.ready
                ? const _Splash()
                : state.fatalError != null
                    ? _FatalError(state: state)
                    : state.settings.onboardingDone
                        ? const Shell()
                        : const OnboardingScreen(),
          ),
        ),
      );
}

class _Splash extends StatelessWidget {
  const _Splash();

  @override
  Widget build(BuildContext context) => Scaffold(
        body: Center(child: Icon(Icons.wb_sunny_outlined, size: 72, color: context.tokens.accent)),
      );
}

class _FatalError extends StatelessWidget {
  const _FatalError({required this.state});

  final AppState state;

  @override
  Widget build(BuildContext context) {
    final t = context.tokens;
    return Scaffold(
      body: SafeArea(
        child: Center(
          child: Padding(
            padding: const EdgeInsets.all(24),
            child: Column(
              mainAxisSize: MainAxisSize.min,
              children: [
                Icon(Icons.error_outline, size: 56, color: t.danger),
                const SizedBox(height: 12),
                Text(state.fatalError!, textAlign: TextAlign.center, style: TextStyle(color: t.ink)),
                const SizedBox(height: 16),
                FilledButton(onPressed: state.init, child: const Text('Qayta urinish')),
              ],
            ),
          ),
        ),
      ),
    );
  }
}

/// Asosiy navigatsiya: Radar, Prognoz, Ma'lumotnoma.
class Shell extends StatefulWidget {
  const Shell({super.key});

  @override
  State<Shell> createState() => _ShellState();
}

class _ShellState extends State<Shell> with WidgetsBindingObserver {
  int index = 0;

  @override
  void initState() {
    super.initState();
    WidgetsBinding.instance.addObserver(this);
  }

  @override
  void dispose() {
    WidgetsBinding.instance.removeObserver(this);
    super.dispose();
  }

  @override
  void didChangeAppLifecycleState(AppLifecycleState lifecycle) {
    if (lifecycle == AppLifecycleState.resumed) {
      final state = AppScope.read(context);
      state.recheckNotifications();
      // Fon vazifasi yangi ma'lumot olgan bo'lishi mumkin — eskirgan bo'lsa yangilaymiz.
      final last = state.lastSync;
      if (state.snapshot == null || last == null || DateTime.now().difference(last) > const Duration(hours: 1)) {
        state.refresh();
      }
    }
  }

  @override
  void didChangeDependencies() {
    super.didChangeDependencies();
    final state = AppScope.of(context);
    // Bildirishnoma bosilgan bo'lsa — tegishli joyni Radar'da ochamiz.
    if (state.pendingPlaceId != null && state.snapshot != null) {
      final id = state.takePendingPlace()!;
      WidgetsBinding.instance.addPostFrameCallback((_) {
        if (!mounted) return;
        Navigator.of(context).popUntil((r) => r.isFirst);
        if (state.snapshot?.place(id) != null) state.viewPlace(id);
        setState(() => index = 0);
      });
    }
  }

  @override
  Widget build(BuildContext context) {
    final pages = [
      HomeScreen(onShowForecast: () => setState(() => index = 1)),
      const ForecastScreen(),
      const GuideScreen(),
    ];
    return Scaffold(
      body: IndexedStack(index: index, children: pages),
      bottomNavigationBar: NavigationBar(
        selectedIndex: index,
        onDestinationSelected: (i) => setState(() => index = i),
        destinations: const [
          NavigationDestination(icon: Icon(Icons.radar_outlined), selectedIcon: Icon(Icons.radar), label: 'Radar'),
          NavigationDestination(icon: Icon(Icons.calendar_month_outlined), selectedIcon: Icon(Icons.calendar_month), label: 'Prognoz'),
          NavigationDestination(icon: Icon(Icons.menu_book_outlined), selectedIcon: Icon(Icons.menu_book), label: "Ma'lumotnoma"),
        ],
      ),
    );
  }
}
