import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:zanjir_core/zanjir_core.dart';

import '../support/harness.dart';

/// Ajratish rejasi oqimi (9-faza mezoni; widget testi va qurilmadagi integration_test uchun umumiy):
/// zona → reja → qoralama → tasdiqlash → qadamlar ketma-ket (kuchlanish tekshiruvi — ikki tasdiq) → yakunlash.
/// Majburiy qadamni o'tkazib yuborib yoki tasdiqsiz belgilab bo'lmasligi tekshiriladi.
Future<void> runIsolationFlow(WidgetTester tester, TestEnv env, DemoSite demo) async {
  Future<void> tapKey(String key) async {
    final f = find.byKey(Key(key));
    // Dangasa ro'yxatda hali qurilmagan bo'lsa — aylantirib topiladi.
    if (f.evaluate().isEmpty) await reveal(tester, f);
    await tester.ensureVisible(f);
    await tester.pump();
    await tester.tap(f);
    await settle(tester);
  }

  bool enabled(String key) => tester.widget<ButtonStyleButton>(find.byKey(Key(key))).onPressed != null;

  await goTo(tester, '/sites/${demo.site.id}/plans');
  expect(find.text('Hali reja yo\'q'), findsOneWidget);
  await tapKey('plans.new');
  await tapKey('zone.${demo.xs1.id}');
  await tapKey('isolation.build');
  await tapKey('isolation.save');

  // Qoralama: qadamlarni belgilab bo'lmaydi, avval tasdiqlash kerak.
  expect(find.text('Qoralama'), findsOneWidget);
  expect(find.textContaining('.mark'), findsNothing);
  expect(find.byKey(const Key('step.1.mark')), findsNothing);
  await tapKey('plan.approve');
  expect(find.textContaining('javobgarlik naryad beruvchi va ish rahbarida'), findsOneWidget);
  await tester.tap(find.byKey(const Key('plan.confirmApprove')));
  await settle(tester);
  expect(find.text('Tasdiqlangan'), findsOneWidget);

  final repos = await env.repos(tester);
  final plan = (await env.io(tester, () => repos.isolationPlans.forSite(demo.site.id))).single;
  final steps = repos.isolationPlans.steps(plan);
  final verify = steps.firstWhere((s) => s.kind == StepKind.verifyNoVoltage);

  for (final s in steps) {
    // Faqat navbatdagi qadam belgilanadi — keyingilarida tugma yo'q.
    for (final later in steps.where((x) => x.order > s.order)) {
      expect(find.byKey(Key('step.${later.order}.mark')), findsNothing, reason: 'qadam ${later.order}');
    }
    await tapKey('step.${s.order}.mark');
    expect(enabled('confirm.submit'), isFalse, reason: 'hech narsa oldindan belgilanmagan');
    if (s.order == verify.order) {
      expect(find.text('Bu qadamni o\'tkazib yuborib bo\'lmaydi. Ikkala bandni o\'zingiz belgilang.'), findsOneWidget);
      expect(tester.widget<CheckboxListTile>(find.byKey(const Key('confirm.indicator'))).value, isFalse);
      expect(tester.widget<CheckboxListTile>(find.byKey(const Key('confirm.noVoltage'))).value, isFalse);
      await tester.tap(find.byKey(const Key('confirm.noVoltage')));
      await settle(tester);
      expect(enabled('confirm.submit'), isFalse, reason: 'ko\'rsatkich oldin sinalmagan');
      await tester.tap(find.byKey(const Key('confirm.indicator')));
    } else {
      await tester.tap(find.byKey(const Key('confirm.done')));
    }
    await settle(tester);
    expect(enabled('confirm.submit'), isTrue);
    await tester.tap(find.byKey(const Key('confirm.submit')));
    await settle(tester);
    expect(find.byKey(Key('step.${s.order}.mark')), findsNothing);
    if (s.order != steps.last.order) expect(find.byKey(const Key('plan.execute')), findsNothing);
  }

  await tapKey('plan.execute');
  await tester.tap(find.byKey(const Key('plan.confirmExecute')));
  await settle(tester);
  expect(find.text('Bajarilgan'), findsOneWidget);
  expect(find.byKey(const Key('plan.cancel')), findsNothing);
  expect(find.textContaining('faqat tavsiya beradi'), findsOneWidget);
  expect(find.textContaining('ishlash xavfsiz'), findsNothing);

  final done = await env.io(tester, () => repos.isolationPlans.doneSteps(plan.id));
  expect(done.keys.toSet(), {for (final s in steps) s.order});
  final types = (await env.io(tester, repos.audit.events)).map((e) => e.eventType).toList();
  expect(types.where((t) => t == 'PLAN_STEP_DONE'), hasLength(steps.length));
  expect(types, containsAllInOrder(['PLAN_CREATED', 'PLAN_APPROVED', 'PLAN_EXECUTED']));
}
