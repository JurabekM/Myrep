import 'dart:io';

import 'package:baraka_daftari/app/app_info.dart';
import 'package:baraka_daftari/app/demo/demo_config.dart';
import 'package:baraka_daftari/app/router/app_router.dart';
import 'package:baraka_daftari/app/router/app_routes.dart';
import 'package:baraka_daftari/core/time/local_date.dart';
import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';

import '../helpers/pump_app.dart';

/// «Ilova haqida» (muallif, versiya, huquqlar) va demo yig'ish belgilari.
void main() {
  test('AppInfo versiyasi pubspec.yaml bilan bir xil', () {
    final pubspec = File('pubspec.yaml').readAsStringSync();
    final m = RegExp(
      r'^version:\s*(\S+)\+(\d+)',
      multiLine: true,
    ).firstMatch(pubspec)!;
    expect(AppInfo.version, m[1]);
    expect(AppInfo.build, int.parse(m[2]!));
  });

  testWidgets('sozlamalar → «Ilova haqida»: muallif, versiya, litsenziyalar', (
    tester,
  ) async {
    final env = await pumpBarakaApp(tester);
    env.container.read(appRouterProvider).go(AppRoutes.settings);
    await tester.pumpAndSettle();
    await tester.scrollUntilVisible(
      find.byKey(const Key('settings-about')),
      200,
      scrollable: find.byType(Scrollable).first,
    );
    await tester.tap(find.byKey(const Key('settings-about')));
    await tester.pumpAndSettle();

    expect(find.text('Versiya 1.0.0 (3)'), findsOneWidget);
    expect(find.text('Muallif: JurabekM'), findsOneWidget);
    expect(
      find.text('© 2026 JurabekM. Barcha huquqlar himoyalangan.'),
      findsOneWidget,
    );
    expect(find.byKey(const Key('about-demo')), findsNothing);
    expect(find.byKey(const Key('demo-banner')), findsNothing);

    await tester.scrollUntilVisible(
      find.byKey(const Key('about-licenses')),
      200,
      scrollable: find.byType(Scrollable).first,
    );
    await tester.tap(find.byKey(const Key('about-licenses')));
    await tester.pumpAndSettle();
    expect(find.byType(LicensePage), findsOneWidget);
  });

  testWidgets('demo: har ekranda «DEMO» va muallif, muddat «Ilova haqida»da', (
    tester,
  ) async {
    final env = await pumpBarakaApp(
      tester,
      extraOverrides: [
        demoConfigProvider.overrideWithValue(
          DemoConfig(enabled: true, until: LocalDate(2100, 1, 31)),
        ),
      ],
    );
    expect(find.byKey(const Key('demo-banner')), findsOneWidget);
    expect(
      find.text(
        'Demo versiya · © 2026 JurabekM · nashr qilish va tarqatish '
        'taqiqlanadi',
      ),
      findsOneWidget,
    );
    expect(find.text('Bosh sahifa'), findsOneWidget);

    env.container.read(appRouterProvider).go(AppRoutes.about);
    await tester.pumpAndSettle();
    expect(find.byKey(const Key('about-demo')), findsOneWidget);
  });

  testWidgets('demo muddati tugagach ilova ochilmaydi', (tester) async {
    await pumpBarakaApp(
      tester,
      unlock: false,
      extraOverrides: [
        demoConfigProvider.overrideWithValue(
          DemoConfig(enabled: true, until: LocalDate(2000, 1, 1)),
        ),
      ],
    );
    expect(find.byKey(const Key('demo-expired')), findsOneWidget);
    expect(find.text('Demo muddati tugadi'), findsOneWidget);
    expect(find.text('PIN kodni kiriting'), findsNothing);
  });

  test('oddiy yigʻishda demo oʻchiq', () {
    expect(DemoConfig.fromEnvironment().enabled, isFalse);
    expect(DemoConfig.off.expiredOn(LocalDate(2100, 1, 1)), isFalse);
  });
}
