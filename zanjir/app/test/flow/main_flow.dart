import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:zanjir_core/zanjir_core.dart';

import '../support/harness.dart';

/// Asosiy oqim (widget testi va qurilmadagi integration_test uchun umumiy):
/// oflayn profil → asbob → obyekt → graf (3 tugun) → sessiya → o'lchov (PASS) → xulosa → sessiyani yopish.
Future<void> runMainFlow(WidgetTester tester, TestEnv env) async {
  Future<void> tapText(String text) async {
    await tester.ensureVisible(find.text(text).last);
    await tester.tap(find.text(text).last);
    await settle(tester);
  }

  Future<void> tapKey(String key) async {
    await tester.ensureVisible(find.byKey(Key(key)));
    await tester.tap(find.byKey(Key(key)));
    await settle(tester);
  }

  /// Dropdown menyusidan element tanlash (uzun menyu ikki tomonga aylantiriladi).
  Future<void> choose(String dropdownKey, String item) async {
    await tapKey(dropdownKey);
    final menu = find.byType(Scrollable).last;
    final target = find.descendant(of: menu, matching: find.text(item));
    for (final dy in [-120.0, 120.0]) {
      for (var i = 0; i < 25 && target.evaluate().isEmpty; i++) {
        await tester.drag(menu, Offset(0, dy));
        await tester.pump();
      }
    }
    await tester.tap(target.last);
    await settle(tester);
  }

  Future<void> addNode({
    required String kind,
    required String label,
    String? connectTo,
    Map<String, String> attrs = const {},
  }) async {
    await tapKey('site.addNode');
    await choose('node.kind', kind);
    await tester.enterText(find.byKey(const Key('node.label')), label);
    for (final e in attrs.entries) {
      final field = find.byKey(Key('node.attr.${e.key}'));
      if (tester.widget(field) is TextFormField) {
        await tester.enterText(field, e.value);
      } else {
        await choose('node.attr.${e.key}', e.value);
      }
    }
    if (connectTo != null) await choose('node.connectTo', connectTo);
    await tapKey('node.verified');
    await tapKey('node.save');
  }

  // 1. Profil.
  await tester.pumpWidget(env.app());
  await settle(tester);
  await tapText('Oflayn profil yaratish');
  await tester.enterText(find.byKey(const Key('onboarding.lab')), 'Elektrolab');
  await tester.enterText(find.byKey(const Key('onboarding.name')), 'Karimov A.');
  await tester.enterText(find.byKey(const Key('onboarding.phone')), '+998901234567');
  await tapKey('onboarding.create');
  await settle(tester, frames: 40);
  expect(find.text('Hozircha obyekt yo\'q'), findsOneWidget);

  // 2. Asbob.
  await tester.tap(find.byTooltip('Sozlamalar'));
  await settle(tester);
  expect(find.text('Normalar hali litsenziyali muhandis tomonidan tekshirilmagan'), findsOneWidget);
  await tapKey('settings.addInstrument');
  await tester.enterText(find.byKey(const Key('instrument.model')), 'MI 3152');
  await tester.enterText(find.byKey(const Key('instrument.serial')), 'SN-001');
  await tester.enterText(find.byKey(const Key('instrument.until')), '2027-03-01');
  await tapKey('instrument.save');
  expect(find.textContaining('MI 3152 · SN-001'), findsOneWidget);
  await tester.tap(find.byType(BackButton));
  await settle(tester);

  // 3. Obyekt.
  await tapKey('sites.add');
  await tester.enterText(find.byKey(const Key('site.name')), 'Savdo markazi');
  await choose('site.earthing', 'TN-C-S');
  await tapKey('site.save');
  expect(find.text('Savdo markazi'), findsWidgets);

  // 4. Graf.
  await addNode(kind: 'Tarmoq (kirish)', label: 'TP-1');
  await addNode(
    kind: 'Avtomat',
    label: 'QF1',
    connectTo: 'TP-1 · Tarmoq (kirish)',
    attrs: {'in_a': '16', 'curve': 'C'},
  );
  await addNode(
    kind: 'Rozetkalar guruhi',
    label: 'XS1',
    connectTo: 'QF1 · Avtomat',
    attrs: {'circuit_role': 'Oxirgi zanjir'},
  );
  expect(find.text('XS1'), findsOneWidget);

  // 5. Sessiya.
  await tapText('Sessiyalar');
  await tapKey('site.startSession');
  await tester.enterText(find.byKey(const Key('session.temp')), '21,5');
  await tapKey('session.start');
  await settle(tester, frames: 30);
  expect(find.text('O\'lchov kiritish'), findsOneWidget);

  // 6. O'lchov: XS1, Zs = 0,84 Ω → Normada.
  await choose('measure.point', 'XS1 · Rozetkalar guruhi');
  await tester.enterText(find.byKey(const Key('measure.zs')), '0,84');
  await tapKey('measure.save');
  await settle(tester, frames: 30);
  expect(find.byKey(const Key('measure.result')), findsOneWidget);
  expect(find.text('Normada'), findsOneWidget);
  expect(find.textContaining('XS1'), findsWidgets);

  // 7. Xulosa va yopish.
  await tester.tap(find.byTooltip('Sessiya xulosasi'));
  await settle(tester);
  expect(find.text('1 ta o\'lchov'), findsOneWidget);
  await tapKey('summary.close');
  await tapKey('summary.confirmClose');
  expect(find.textContaining('Sessiya yopilgan'), findsOneWidget);
  expect(find.text('Protokol'), findsOneWidget);

  // Ma'lumot bazada: PASS, audit zanjiri butun.
  final repos = await env.repos(tester);
  final sessions = await env.io(tester, () async {
    final site = (await repos.sites.list()).single;
    return repos.sessions.forSite(site.id);
  });
  final ms = await env.io(tester, () => repos.measurements.forSession(sessions.single.id));
  expect(ms.single.verdict, Verdict.pass);
  expect((await env.io(tester, repos.audit.verify)).ok, isTrue);
}
