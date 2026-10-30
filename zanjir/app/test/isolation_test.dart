import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:zanjir_core/zanjir_core.dart';

import 'support/harness.dart';

void main() {
  testWidgets('reja: kuchlanish yo\'qligini tekshirish qadami doim bor va majburiy', (tester) async {
    final (env, demo, _) = await startWithSession(tester);
    await goTo(tester, '/sites/${demo.site.id}/isolation');
    await tester.tap(find.byKey(Key('zone.${demo.xs1.id}')));
    await settle(tester);
    await reveal(tester, find.byKey(const Key('isolation.build')));
    await tester.tap(find.byKey(const Key('isolation.build')));
    await settle(tester);
    await reveal(tester, find.textContaining('kuchlanish yo\'qligini tekshiring'));
    expect(find.textContaining('XS1 ← QF1: kuchlanish yo\'qligini tekshiring'), findsOneWidget);
    expect(find.text('Majburiy'), findsOneWidget);
    expect(find.textContaining('QF1: o\'chiring'), findsOneWidget);
    expect(find.textContaining('Yoqilmasin! Odamlar ishlamoqda'), findsOneWidget);
    expect(find.textContaining('faqat tavsiya beradi'), findsOneWidget);
    expect(find.textContaining('ishlash xavfsiz'), findsNothing);
    await env.dispose(tester);
  });

  testWidgets('kommutatsiya apparatisiz yo\'l — reja tuzilmaydi, yo\'l ko\'rsatiladi', (tester) async {
    final (env, demo, _) = await startWithSession(tester);
    final repos = await env.repos(tester);
    await env.io(tester, () async {
      final m = await repos.graph.addNode(siteId: demo.site.id, kind: NodeKind.load, label: 'M1', verified: true);
      await repos.graph.addEdge(siteId: demo.site.id, aNodeId: demo.grid.id, bNodeId: m.id, conductors: 'L1 N PE');
    });
    await goTo(tester, '/sites/${demo.site.id}/isolation');
    await tester.tap(find.text('M1'));
    await settle(tester);
    await reveal(tester, find.byKey(const Key('isolation.build')));
    await tester.tap(find.byKey(const Key('isolation.build')));
    await settle(tester);
    await reveal(tester, find.text('Reja tuzib bo\'lmadi'));
    expect(find.textContaining('TP-1 → M1'), findsOneWidget);
    await env.dispose(tester);
  });

  testWidgets('graf o\'zgarsa — reja STALE, hech qanday amal yo\'q', (tester) async {
    final (env, demo, _) = await startWithSession(tester);
    final repos = await env.repos(tester);
    final plan = await env.io(tester, () async {
      final g = await repos.graph.loadGraph(demo.site.id);
      final p = planIsolation(g, {demo.xs1.id}, earthingSystem: EarthingSystem.tnCS) as IsolationPlan;
      final row = await repos.isolationPlans.save(siteId: demo.site.id, plan: p);
      await repos.isolationPlans.approve(row.id);
      await repos.isolationPlans.completeStep(row.id, 1, const StepConfirmation(done: true));
      await repos.graph.addNode(siteId: demo.site.id, kind: NodeKind.load, label: 'M2');
      return row;
    });
    await goTo(tester, '/sites/${demo.site.id}/plans');
    expect(find.text('Eskirgan'), findsOneWidget);
    await tester.tap(find.byKey(Key('plan.${plan.id}')));
    await settle(tester);
    expect(find.byKey(const Key('plan.stale')), findsOneWidget);
    for (final key in ['plan.approve', 'plan.execute', 'plan.cancel', 'step.2.mark']) {
      expect(find.byKey(Key(key)), findsNothing, reason: key);
    }
    expect(find.textContaining('Bajarildi:'), findsOneWidget, reason: 'bajarilgan qadam tarixi saqlanadi');
    await env.dispose(tester);
  });

  testWidgets('bekor qilish — tasdiq bilan', (tester) async {
    final (env, demo, _) = await startWithSession(tester);
    final repos = await env.repos(tester);
    final plan = await env.io(tester, () async {
      final g = await repos.graph.loadGraph(demo.site.id);
      final p = planIsolation(g, {demo.xs1.id}, earthingSystem: EarthingSystem.tnCS) as IsolationPlan;
      return repos.isolationPlans.save(siteId: demo.site.id, plan: p);
    });
    await goTo(tester, '/plans/${plan.id}');
    await reveal(tester, find.byKey(const Key('plan.cancel')));
    await tester.tap(find.byKey(const Key('plan.cancel')));
    await settle(tester);
    await tester.tap(find.byKey(const Key('plan.confirmCancel')));
    await settle(tester);
    expect(find.text('Bekor qilingan'), findsOneWidget);
    expect(find.byKey(const Key('plan.approve')), findsNothing);
    await env.dispose(tester);
  });
}
