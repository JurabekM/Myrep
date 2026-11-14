import 'package:flutter/material.dart';
import 'package:flutter_localizations/flutter_localizations.dart';

import 'core/app_state.dart';
import 'core/native.dart';
import 'ui/apk_screen.dart';
import 'ui/call_screen.dart';
import 'ui/check_screen.dart';
import 'ui/home_screen.dart';
import 'ui/theme.dart';

final navigatorKey = GlobalKey<NavigatorState>();

void main() {
  WidgetsFlutterBinding.ensureInitialized();
  runApp(const RostorApp());
  AppState.instance.init().then((_) async {
    // Ilova "APK ochish" yoki "Ulashish" orqali ishga tushgan bo'lsa.
    final first = await Native.takeIncoming();
    if (first != null) _route(first);
  });
  Native.onIncoming(_route);
}

void _route(Map<String, dynamic> incoming) {
  final nav = navigatorKey.currentState;
  if (nav == null) return;
  switch (incoming['type']) {
    case 'apk':
      nav.push(MaterialPageRoute(builder: (_) => ApkScreen(uri: incoming['uri'] as String)));
    case 'calls':
      // Ogohlantirish bir necha marta bosilsa ham ekran bitta bo'lsin.
      nav.popUntil((r) => r.isFirst);
      nav.push(MaterialPageRoute(builder: (_) => const CallScreen()));
    case 'text':
      nav.push(MaterialPageRoute(builder: (_) => CheckScreen(initialText: incoming['text'] as String?)));
  }
}

class RostorApp extends StatelessWidget {
  const RostorApp({super.key});

  @override
  Widget build(BuildContext context) => MaterialApp(
        title: 'ROSTOR-2',
        debugShowCheckedModeBanner: false,
        navigatorKey: navigatorKey,
        theme: buildTheme(),
        locale: const Locale('uz'),
        supportedLocales: const [Locale('uz')],
        localizationsDelegates: GlobalMaterialLocalizations.delegates,
        home: const HomeScreen(),
      );
}
