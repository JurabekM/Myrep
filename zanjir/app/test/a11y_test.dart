import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:zanjir_core/zanjir_core.dart';

import 'support/harness.dart';

/// Accessibility (10-faza, ADR-0014): har bir asosiy ekranda Flutter guideline'lari —
/// tugma o'lchami (Android ≥ 48 dp), yorliqli bosiladigan elementlar (TalkBack), matn kontrasti (WCAG AA).
Future<void> checkGuidelines(WidgetTester tester, String screen) async {
  final handle = tester.ensureSemantics();
  for (final (name, g) in [
    ('tap target', androidTapTargetGuideline),
    ('label', labeledTapTargetGuideline),
    ('contrast', textContrastGuideline),
  ]) {
    await expectLater(tester, meetsGuideline(g), reason: '$screen: $name');
  }
  handle.dispose();
}

void main() {
  testWidgets('kirish ekrani (profil yo\'q)', (tester) async {
    final env = TestEnv();
    await tester.pumpWidget(env.app());
    await settle(tester);
    await checkGuidelines(tester, 'login');
    await goTo(tester, '/onboarding');
    await checkGuidelines(tester, 'onboarding');
    await env.dispose(tester);
  });

  testWidgets('asosiy ekranlar (LEAD, ochiq sessiya)', (tester) async {
    final (env, demo, sessionId) = await startWithSession(tester);
    final repos = await env.repos(tester);
    await env.io(
      tester,
      () => repos.measurements.record(
        sessionId: sessionId,
        nodeId: demo.xs1.id,
        type: MeasurementType.loopImpedance,
        instrumentId: demo.instrument.id,
        values: {'pair': 'L1-PE', 'zs_ohm': 0.84},
        enteredVia: EnteredVia.manual,
        normSetVersion: '0.1.0',
      ),
    );
    for (final route in [
      '/',
      '/sites/${demo.site.id}',
      '/nodes/${demo.xs1.id}',
      '/sites/${demo.site.id}/nodes/new',
      '/sites/${demo.site.id}/sessions/new',
      '/sessions/$sessionId/measure',
      '/sessions/$sessionId',
      '/sites/${demo.site.id}/plans',
      '/sites/${demo.site.id}/isolation',
      '/settings',
      '/settings/instruments/new',
    ]) {
      await goTo(tester, route);
      await checkGuidelines(tester, route);
    }
    await env.dispose(tester);
  });

  testWidgets('protokol va reja ekranlari', (tester) async {
    final (env, demo, sessionId) = await startWithSession(tester);
    final repos = await env.repos(tester);
    final plan = await env.io(tester, () async {
      await repos.sessions.close(sessionId);
      final g = await repos.graph.loadGraph(demo.site.id);
      final p = planIsolation(g, {demo.xs1.id}, earthingSystem: EarthingSystem.tnCS) as IsolationPlan;
      final row = await repos.isolationPlans.save(siteId: demo.site.id, plan: p);
      return repos.isolationPlans.approve(row.id);
    });
    await goTo(tester, '/sessions/$sessionId/protocol');
    await checkGuidelines(tester, 'protocol');
    await goTo(tester, '/plans/${plan.id}');
    await checkGuidelines(tester, 'plan');
    await tester.tap(find.byKey(const Key('step.1.mark')));
    await settle(tester);
    await checkGuidelines(tester, 'step dialog');
    // Katta shrift (×2) — protokol, reja va kuchlanish tekshiruvi dialogi.
    tester.platformDispatcher.textScaleFactorTestValue = 2.0;
    addTearDown(tester.platformDispatcher.clearTextScaleFactorTestValue);
    await goTo(tester, '/sessions/$sessionId/protocol');
    expect(tester.takeException(), isNull);
    await goTo(tester, '/plans/${plan.id}');
    expect(tester.takeException(), isNull);
    await env.dispose(tester);
  });

  testWidgets('katta shrift (tizim ×2): asosiy ekranlarda toshib chiqish yo\'q', (tester) async {
    tester.platformDispatcher.textScaleFactorTestValue = 2.0;
    addTearDown(tester.platformDispatcher.clearTextScaleFactorTestValue);
    final (env, demo, sessionId) = await startWithSession(tester);
    for (final route in [
      '/',
      '/sites/${demo.site.id}',
      '/nodes/${demo.xs1.id}',
      '/sessions/$sessionId/measure',
      '/sessions/$sessionId',
      '/sites/${demo.site.id}/plans',
      '/settings',
    ]) {
      await goTo(tester, route);
      expect(tester.takeException(), isNull, reason: route);
    }
    await env.dispose(tester);
  });
}
