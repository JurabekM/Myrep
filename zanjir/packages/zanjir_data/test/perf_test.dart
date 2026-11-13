@Tags(['perf'])
library;

import 'package:test/test.dart';
import 'package:zanjir_core/zanjir_core.dart';
import 'package:zanjir_data/zanjir_data.dart';

import 'support/harness.dart';

/// Unumdorlik byudjetlari (10-faza, ADR-0014). Byudjetlar CI mashinasi uchun ~3× zaxira bilan; o'rta Android qurilma
/// talablari: o'lchovni saqlash < 200 ms (≤ 10 s kiritish talabining kichik qismi), 2000 tugunli graf.
void main() {
  test('katta obyekt (2000 tugun): graf yuklash, o\'lchov yozish, xulosa', () async {
    final db = memoryDb();
    addTearDown(db.close);
    final org = await Org.create(db, 'P');
    final s = await SmallSite.create(org);
    final r = org.repos;
    // 2000 tugun: shit → 40 ta avtomat → har birida kabel va rozetka zanjiri.
    var parent = s.qf1;
    final sockets = <NodeRow>[];
    await db.transaction(() async {
      for (var i = 0; i < 666; i++) {
        final qf = await r.graph.addNode(
          siteId: s.site.id,
          kind: NodeKind.breaker,
          label: 'QF$i',
          attrs: {'in_a': 16, 'curve': 'C'},
          verified: true,
        );
        final w = await r.graph.addNode(
          siteId: s.site.id,
          kind: NodeKind.cable,
          label: 'W$i',
          attrs: {'circuit_role': 'final', 'circuit_class': 'wiring', 'length_m': 20},
          verified: true,
        );
        final xs = await r.graph.addNode(
          siteId: s.site.id,
          kind: NodeKind.socketGroup,
          label: 'XS$i',
          attrs: {'circuit_role': 'final'},
          verified: true,
        );
        await r.graph.addEdge(siteId: s.site.id, aNodeId: parent.id, bNodeId: qf.id, conductors: 'L1 N PE');
        await r.graph.addEdge(siteId: s.site.id, aNodeId: qf.id, bNodeId: w.id, conductors: 'L1 N PE');
        await r.graph.addEdge(siteId: s.site.id, aNodeId: w.id, bNodeId: xs.id, conductors: 'L1 N PE');
        sockets.add(xs);
        if (i % 40 == 39) parent = qf; // daraxt chuqurligi
      }
    });
    final load = Stopwatch()..start();
    final g = await r.graph.loadGraph(s.site.id);
    load.stop();
    expect(g.nodes.length, greaterThanOrEqualTo(2000));

    final session = await r.sessions.start(siteId: s.site.id, kind: SessionKind.davriy, engineerId: org.user.id);
    final rec = Stopwatch()..start();
    const n = 100;
    for (var i = 0; i < n; i++) {
      await r.measurements.record(
        sessionId: session.id,
        nodeId: sockets[i * 6].id,
        type: MeasurementType.loopImpedance,
        instrumentId: s.instrument.id,
        values: {'pair': 'L1-PE', 'zs_ohm': 0.5},
        enteredVia: EnteredVia.manual,
        normSetVersion: '0.3.0',
      );
    }
    rec.stop();
    final perRecord = rec.elapsedMilliseconds / n;
    final summary = Stopwatch()..start();
    expect(await r.measurements.forSession(session.id), hasLength(n));
    summary.stop();
    final plan = Stopwatch()..start();
    final p = planIsolation(g, {sockets[300].id}, earthingSystem: EarthingSystem.tnCS);
    plan.stop();
    expect(p, isA<IsolationPlan>());
    // ignore: avoid_print — CI logida raqamlar ko'rinsin.
    print(
      'graf yuklash: ${load.elapsedMilliseconds} ms; o\'lchov yozish: ${perRecord.toStringAsFixed(1)} ms; '
      'xulosa: ${summary.elapsedMilliseconds} ms; reja: ${plan.elapsedMilliseconds} ms',
    );
    expect(load.elapsedMilliseconds, lessThan(1500));
    expect(perRecord, lessThan(200));
    expect(summary.elapsedMilliseconds, lessThan(500));
    expect(plan.elapsedMilliseconds, lessThan(1500));
  });
}
