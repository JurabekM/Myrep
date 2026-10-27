import 'package:baraka_daftari/app/router/app_router.dart';
import 'package:baraka_daftari/app/router/app_routes.dart';
import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';

import '../helpers/pump_app.dart';

/// Accessibility (MVP_PLAN Vazifa 15): 48dp+ tugmalar, TalkBack yorliqlari,
/// matn kontrasti va katta shrift — asosiy ekranlarda.
void largeText(WidgetTester tester) {
  tester.platformDispatcher.textScaleFactorTestValue = 2;
  addTearDown(tester.platformDispatcher.clearTextScaleFactorTestValue);
}

void main() {
  const screens = [
    AppRoutes.home,
    AppRoutes.incomeNew,
    AppRoutes.expenseNew,
    AppRoutes.vault,
    AppRoutes.debts,
    AppRoutes.debtNew,
    AppRoutes.settings,
    AppRoutes.backup,
    AppRoutes.partnerships,
    AppRoutes.agreements,
    AppRoutes.agreementOral,
  ];

  Future<void> checkGuidelines(WidgetTester tester) async {
    await expectLater(tester, meetsGuideline(androidTapTargetGuideline));
    await expectLater(tester, meetsGuideline(labeledTapTargetGuideline));
    await expectLater(tester, meetsGuideline(textContrastGuideline));
  }

  for (final route in screens) {
    testWidgets('$route: tugma 48dp, yorliq, kontrast', (tester) async {
      final handle = tester.ensureSemantics();
      final env = await pumpBarakaApp(tester);
      env.container.read(appRouterProvider).go(route);
      await tester.pumpAndSettle();
      await checkGuidelines(tester);
      handle.dispose();
    });
  }

  testWidgets('onboarding qadamlari: tugma 48dp, yorliq, kontrast', (
    tester,
  ) async {
    final handle = tester.ensureSemantics();
    await pumpBarakaApp(tester, onboarded: false);
    await checkGuidelines(tester);
    await tester.tap(find.byKey(const Key('ob-next')));
    await tester.pumpAndSettle();
    await checkGuidelines(tester);
    await tester.tap(find.byKey(const Key('ob-next')));
    await tester.pumpAndSettle();
    await checkGuidelines(tester);
    handle.dispose();
  });

  for (final route in [AppRoutes.home, AppRoutes.incomeNew, AppRoutes.debts]) {
    testWidgets('$route: katta shrift (200 %) — toshib ketish yoʻq', (
      tester,
    ) async {
      final env = await pumpBarakaApp(tester);
      largeText(tester);
      env.container.read(appRouterProvider).go(route);
      await tester.pumpAndSettle();
      expect(tester.takeException(), isNull);
    });
  }

  testWidgets('onboarding: katta shrift (200 %) — toshib ketish yoʻq', (
    tester,
  ) async {
    await pumpBarakaApp(tester, onboarded: false);
    largeText(tester);
    await tester.pumpAndSettle();
    for (var i = 0; i < 3; i++) {
      expect(tester.takeException(), isNull);
      await tester.tap(find.byKey(const Key('ob-next')));
      await tester.pumpAndSettle();
    }
    expect(tester.takeException(), isNull);
  });

  testWidgets('qulf: katta shriftda klaviatura aylantirib yetiladi', (
    tester,
  ) async {
    largeText(tester);
    await pumpBarakaApp(tester, unlock: false);
    expect(tester.takeException(), isNull);
    for (final digit in testPin.split('')) {
      final key = find.byKey(Key('pin-key-$digit'));
      await tester.ensureVisible(key);
      await tester.pumpAndSettle();
      await tester.tap(key);
      await tester.pump();
    }
    await tester.pumpAndSettle();
    expect(find.widgetWithText(AppBar, 'Bosh sahifa'), findsOneWidget);
  });
}
