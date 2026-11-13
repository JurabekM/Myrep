import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:qr_flutter/qr_flutter.dart';
import 'package:zanjir_app/features/sites/sites_screen.dart';
import 'package:zanjir_core/zanjir_core.dart';

import 'support/harness.dart';

void main() {
  testWidgets('daraxt: chuqurlik, ulanmagan tugunlar; graf rejimi; tugun kartasi, QR, nusxalash', (tester) async {
    final (env, demo, _) = await startWithSession(tester);
    final repos = await env.repos(tester);
    await env.io(tester, () => repos.graph.addNode(siteId: demo.site.id, kind: NodeKind.load, label: 'M9'));
    await goTo(tester, '/sites/${demo.site.id}');
    expect(find.text('TP-1'), findsOneWidget);
    expect(find.text('XS1'), findsOneWidget);
    expect(find.text('Manbaga ulanmagan'), findsOneWidget);
    // M9 tasdiqlanmagan — ogohlantirish belgisi.
    expect(find.byTooltip('Tasdiqlanmagan'), findsOneWidget);

    await tester.tap(find.text('Graf'));
    await settle(tester);
    expect(find.byType(CustomPaint), findsWidgets);

    await tester.tap(find.text('Daraxt'));
    await settle(tester);
    await tester.tap(find.text('QF1'));
    await settle(tester);
    expect(find.text('Avtomat'), findsOneWidget);
    expect(find.byType(QrImageView), findsOneWidget);
    expect(find.text('Nominal tok In, A'), findsOneWidget);

    await tester.tap(find.byKey(const Key('node.duplicate')));
    await settle(tester);
    expect(find.text('QF2'), findsOneWidget);
    expect(find.text('Tasdiqlanmagan'), findsOneWidget);
    await env.dispose(tester);
  });

  testWidgets('kod bo\'yicha ochish (QR matni)', (tester) async {
    final (env, demo, _) = await startWithSession(tester);
    await tester.tap(find.byTooltip('Kod bo\'yicha ochish'));
    await settle(tester);
    await tester.enterText(find.byKey(const Key('openByCode.field')), 'zanjir://app/n/${demo.qf1.id}');
    await tester.tap(find.text('Ochish'));
    await settle(tester);
    expect(find.text('QF1'), findsWidgets);
    expect(find.byType(QrImageView), findsOneWidget);
    await env.dispose(tester);
  });

  testWidgets('tugun formasi: tanlanmagan "Selektiv" yozilmaydi; tahrirlash noma\'lum atributlarni saqlaydi', (
    tester,
  ) async {
    final (env, demo, _) = await startWithSession(tester);
    final repos = await env.repos(tester);
    await goTo(tester, '/sites/${demo.site.id}/nodes/new');
    await tester.tap(find.byKey(const Key('node.kind')));
    await settle(tester);
    final menu = find.byType(Scrollable).last;
    final uzo = find.descendant(of: menu, matching: find.text('UZO'));
    for (var i = 0; i < 20 && uzo.evaluate().isEmpty; i++) {
      await tester.drag(menu, const Offset(0, -120));
      await tester.pump();
    }
    await tester.tap(uzo.last);
    await settle(tester);
    await tester.enterText(find.byKey(const Key('node.label')), 'QD1');
    await tester.enterText(find.byKey(const Key('node.attr.idn_ma')), '30');
    await reveal(tester, find.byKey(const Key('node.save')));
    await tester.tap(find.byKey(const Key('node.save')));
    await settle(tester);
    final qd = (await env.io(tester, () => repos.graph.nodes(demo.site.id))).firstWhere((n) => n.label == 'QD1');
    expect(qd.kind, NodeKind.rcd);
    expect(qd.attrs, {'idn_ma': 30}, reason: 'selective kiritilmagan — natija NEEDS_REVIEW bo\'lishi uchun');

    final custom = await env.io(
      tester,
      () => repos.graph.updateNode(demo.qf1.copyWith(attrs: {'in_a': 16, 'curve': 'C', 'manufacturer': 'ABB'})),
    );
    await goTo(tester, '/sites/${demo.site.id}/nodes/${custom.id}/edit');
    await tester.enterText(find.byKey(const Key('node.attr.in_a')), '20');
    await reveal(tester, find.byKey(const Key('node.save')));
    await tester.tap(find.byKey(const Key('node.save')));
    await settle(tester);
    final updated = await env.io(tester, () => repos.graph.getNode(custom.id));
    expect(updated!.attrs, {'in_a': 20, 'curve': 'C', 'manufacturer': 'ABB'});
    await env.dispose(tester);
  });

  test('nodeIdFromCode', () {
    expect(nodeIdFromCode('zanjir://app/n/abc'), 'abc');
    expect(nodeIdFromCode(' abc '), 'abc');
    expect(nodeIdFromCode('zanjir://app/x/abc'), isNull);
    expect(nodeIdFromCode(''), isNull);
  });
}
