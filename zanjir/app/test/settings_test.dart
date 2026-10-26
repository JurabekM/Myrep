import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:zanjir_app/app.dart';
import 'package:zanjir_data/zanjir_data.dart';

import 'support/harness.dart';

Future<TestEnv> openSettings(WidgetTester tester, {String role = 'LEAD'}) async {
  tester.view.physicalSize = const Size(1080, 2400);
  tester.view.devicePixelRatio = 2.5;
  addTearDown(tester.view.reset);
  final env = TestEnv();
  await env.createProfile(tester);
  if (role != 'LEAD') {
    // Ikkinchi foydalanuvchi shu qurilmada (masalan, muhandis).
    final repos = await env.repos(tester);
    final user = await env.io(tester, () => repos.users.create(fullName: 'Muhandis', phone: '+998', role: role));
    await env.io(tester, () => LocalPrefRepository(env.db).set(LocalPrefRepository.userId, user.id));
    env.profile = null;
  }
  await tester.pumpWidget(env.app());
  await settle(tester);
  await goTo(tester, '/settings');
  return env;
}

void main() {
  testWidgets('LEAD: k_corr tekshiriladi va saqlanadi; normalar tekshirilmagani ko\'rsatiladi', (tester) async {
    final env = await openSettings(tester);
    expect(find.text('Normalar hali litsenziyali muhandis tomonidan tekshirilmagan'), findsOneWidget);
    expect(find.text('Normalar versiyasi: 0.1.0'), findsOneWidget);

    await tester.enterText(find.byKey(const Key('settings.kCorr')), '1,2');
    await tester.tap(find.byKey(const Key('settings.saveEval')));
    await settle(tester);
    expect(find.text('k_corr (0; 1] oralig\'ida bo\'lishi kerak'), findsOneWidget);

    await tester.enterText(find.byKey(const Key('settings.kCorr')), '0,8');
    await tester.enterText(find.byKey(const Key('settings.margin')), '5');
    await tester.tap(find.byKey(const Key('settings.saveEval')));
    await settle(tester);
    expect(find.text('Saqlandi'), findsOneWidget);
    final repos = await env.repos(tester);
    final s = await env.io(tester, repos.settings.current);
    expect((s.kCorr, s.marginPct), (0.8, 5.0));
    await env.dispose(tester);
  });

  testWidgets('ENGINEER: baholash sozlamalari o\'zgartirilmaydi', (tester) async {
    final env = await openSettings(tester, role: 'ENGINEER');
    expect(find.text('Faqat ish rahbari (LEAD) yoki administrator o\'zgartiradi'), findsOneWidget);
    final field = tester.widget<TextFormField>(find.byKey(const Key('settings.kCorr')));
    expect(field.enabled, isFalse);
    expect(find.byKey(const Key('settings.saveEval')), findsNothing);
    await env.dispose(tester);
  });

  testWidgets('til (uz → ru) va katta shrift saqlanadi', (tester) async {
    final env = await openSettings(tester);
    await tester.tap(find.text('Русский'));
    await settle(tester);
    expect(find.text('Настройки'), findsOneWidget);
    expect(find.textContaining('только рекомендации'), findsNothing, reason: 'sozlamalar ekranida banner yo\'q');
    await tester.tap(find.byKey(const Key('settings.largeText')));
    await settle(tester);
    final scale = MediaQuery.textScalerOf(tester.element(find.text('Настройки'))).scale(10);
    expect(scale, closeTo(10 * largeTextFactor, 0.01));
    expect(await env.io(tester, () => LocalPrefRepository(env.db).get(LocalPrefRepository.locale)), 'ru');
    expect(await env.io(tester, () => LocalPrefRepository(env.db).get(LocalPrefRepository.largeText)), '1');
    await env.dispose(tester);
  });
}
