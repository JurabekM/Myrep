import 'package:flutter/material.dart';
import 'package:drift/drift.dart' show Value;
import 'package:flutter_test/flutter_test.dart';
import 'package:zanjir_core/zanjir_core.dart';

import 'support/harness.dart';

Future<void> pickPoint(WidgetTester tester, String label) async {
  await tester.tap(find.byKey(const Key('measure.point')));
  await settle(tester);
  await tester.tap(find.text(label).last);
  await settle(tester);
}

Future<void> save(WidgetTester tester) async {
  await reveal(tester, find.byKey(const Key('measure.save')));
  await tester.tap(find.byKey(const Key('measure.save')));
  await settle(tester, frames: 30);
}

void main() {
  testWidgets('sirtmoq: PASS va FAIL, natija rangi, keyingi nuqtaga avtomatik o\'tish', (tester) async {
    final (env, demo, sessionId) = await startWithSession(tester);
    await goTo(tester, '/sessions/$sessionId/measure');
    await pickPoint(tester, 'XS1 · Rozetkalar guruhi');
    await tester.enterText(find.byKey(const Key('measure.zs')), '0,84');
    await save(tester);
    expect(find.text('Normada'), findsOneWidget);
    expect(find.text('LOOP-TN-FINAL'), findsOneWidget);
    expect(find.text('Chegara: 1,375'), findsOneWidget);
    // XS1 ro'yxatda oxirgi — keyingisi birinchi (QF1).
    expect(find.text('QF1 · Avtomat'), findsOneWidget);

    await pickPoint(tester, 'XS1 · Rozetkalar guruhi');
    await tester.enterText(find.byKey(const Key('measure.zs')), '2');
    await save(tester);
    expect(find.text('Normadan tashqari'), findsOneWidget);
    expect(find.text('Zs ruxsat etilganidan katta'), findsOneWidget);
    await env.dispose(tester);
  });

  testWidgets('UZO: "O\'chdi/O\'chmadi" tanlanmasa — Ko\'rib chiqish kerak (standart PASS yo\'q)', (tester) async {
    final (env, demo, sessionId) = await startWithSession(tester);
    final repos = await env.repos(tester);
    await env.io(
      tester,
      () => repos.graph.addNode(
        siteId: demo.site.id,
        kind: NodeKind.rcd,
        label: 'QD1',
        attrs: {'in_a': 40, 'idn_ma': 30, 'selective': false},
      ),
    );
    await goTo(tester, '/sessions/$sessionId/measure');
    await pickPoint(tester, 'QD1 · UZO');
    await tester.enterText(find.byKey(const Key('measure.time')), '24');
    await tester.enterText(find.byKey(const Key('measure.current')), '21');
    await save(tester);
    expect(find.text('Ko\'rib chiqish kerak'), findsOneWidget);
    expect(find.text('Qiymat kiritilmagan'), findsOneWidget);

    await pickPoint(tester, 'QD1 · UZO');
    await reveal(tester, find.text('O\'chdi'));
    await tester.tap(find.text('O\'chdi'));
    await tester.enterText(find.byKey(const Key('measure.time')), '24');
    await tester.enterText(find.byKey(const Key('measure.current')), '21');
    await save(tester);
    expect(find.text('Normada'), findsOneWidget);
    await env.dispose(tester);
  });

  testWidgets('yerga ulash: ψ oldindan to\'ldirilmaydi; qo\'llanilmaydi; harorat yo\'q — izolyatsiya', (tester) async {
    final (env, demo, sessionId) = await startWithSession(tester, temp: null);
    final repos = await env.repos(tester);
    await env.io(
      tester,
      () => repos.graph.addNode(
        siteId: demo.site.id,
        kind: NodeKind.earthElectrode,
        label: 'GZ1',
        attrs: {'role': 'neutral'},
      ),
    );
    await goTo(tester, '/sessions/$sessionId/measure');
    await pickPoint(tester, 'GZ1 · Yerga ulagich');
    await tester.enterText(find.byKey(const Key('measure.earth')), '3,1');
    await save(tester);
    expect(find.text('Mavsumiy koeffitsient kiritilmagan'), findsOneWidget);

    await pickPoint(tester, 'GZ1 · Yerga ulagich');
    await reveal(tester, find.widgetWithText(OutlinedButton, 'Qo\'llanilmaydi'));
    await tester.tap(find.widgetWithText(OutlinedButton, 'Qo\'llanilmaydi'));
    await settle(tester);
    await tester.enterText(find.byKey(const Key('measure.naReason')), 'Demontaj qilingan');
    await tester.tap(find.widgetWithText(FilledButton, 'Saqlash').last);
    await settle(tester, frames: 30);
    expect(find.text('Qo\'llanilmaydi deb belgilangan'), findsOneWidget);

    final measurements = await env.io(tester, () => repos.measurements.forSession(sessionId));
    expect(measurements.map((m) => m.verdict), [Verdict.needsReview, Verdict.notApplicable]);
    await env.dispose(tester);
  });

  testWidgets('muddati o\'tgan asbob — ogohlantirish; qayta o\'lchash supersedes bilan', (tester) async {
    final (env, demo, sessionId) = await startWithSession(tester);
    final repos = await env.repos(tester);
    final first = await env.io(
      tester,
      () => repos.measurements.record(
        sessionId: sessionId,
        nodeId: demo.xs1.id,
        type: MeasurementType.loopImpedance,
        instrumentId: demo.instrument.id,
        values: {'pair': 'L1-PE', 'zs_ohm': 8.4},
        enteredVia: EnteredVia.manual,
        normSetVersion: '0.2.0',
      ),
    );
    await env.io(
      tester,
      () => repos.instruments.update(demo.instrument.copyWith(verifiedUntil: Value(DateTime.utc(2026, 1, 1)))),
    );
    await goTo(tester, '/sessions/$sessionId');
    await tester.longPress(find.byKey(Key('summary.m.${first.id}')));
    await settle(tester);
    expect(find.textContaining('Xato o\'lchov o\'chirilmaydi'), findsOneWidget);
    expect(find.textContaining('Qiyoslash muddati o\'tgan'), findsOneWidget);
    await tester.enterText(find.byKey(const Key('measure.zs')), '0,84');
    await save(tester);
    final list = await env.io(tester, () => repos.measurements.forSession(sessionId));
    expect(list.single.supersedesId, first.id);
    expect(list.single.verdict, Verdict.pass);
    await env.dispose(tester);
  });
}
