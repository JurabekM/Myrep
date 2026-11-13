import 'dart:math';

import 'package:test/test.dart';
import 'package:zanjir_core/zanjir_core.dart';

import '../support/fixtures.dart';

/// 1000 ta tasodifiy grafda solver natijasi to'liq qidiruv (brute force) bilan solishtiriladi.
void main() {
  const cuttable = {
    NodeKind.loadSwitch: 1,
    NodeKind.fuse: 2,
    NodeKind.breaker: 3,
    NodeKind.rcbo: 3,
    NodeKind.rcd: 5,
    NodeKind.contactor: 50,
    NodeKind.ats: 50,
  };
  const otherKinds = [
    NodeKind.busbar,
    NodeKind.panel,
    NodeKind.cable,
    NodeKind.load,
    NodeKind.socketGroup,
    NodeKind.peBar,
  ];
  const sourceKinds = [
    NodeKind.srcGrid,
    NodeKind.srcTransformer,
    NodeKind.srcGenerator,
    NodeKind.srcPvInverter,
    NodeKind.srcUps,
    NodeKind.srcBattery,
  ];

  test('1000 ta tasodifiy graf: optimal, to\'g\'ri, deterministik', () {
    final rnd = Random(20261026);
    var plans = 0;
    var blocked = 0;
    var noSource = 0;
    for (var iter = 0; iter < 1000; iter++) {
      final n = 4 + rnd.nextInt(18);
      final nodes = <Node>[];
      for (var i = 0; i < n; i++) {
        final r = rnd.nextDouble();
        final kind = r < 0.15
            ? sourceKinds[rnd.nextInt(sourceKinds.length)]
            : r < 0.6
            ? cuttable.keys.elementAt(rnd.nextInt(cuttable.length))
            : otherKinds[rnd.nextInt(otherKinds.length)];
        nodes.add(node('N${i.toString().padLeft(2, '0')}', kind, verified: rnd.nextDouble() > 0.1));
      }
      final links = <List<String>>{};
      for (var i = 1; i < n; i++) {
        if (rnd.nextDouble() < 0.9) links.add([nodes[rnd.nextInt(i)].id, nodes[i].id]);
      }
      for (var k = rnd.nextInt(n ~/ 2 + 1); k > 0; k--) {
        final a = rnd.nextInt(n);
        final b = rnd.nextInt(n);
        if (a != b) links.add([nodes[min(a, b)].id, nodes[max(a, b)].id]);
      }
      final uniqueLinks = {for (final l in links) l.join('|'): l}.values.toList();
      final g = graphOf(nodes, uniqueLinks);
      final candidates = [
        for (final x in nodes)
          if (!x.kind.isSource) x.id,
      ];
      if (candidates.isEmpty) continue;
      final zone = {for (var k = 1 + rnd.nextInt(2); k > 0; k--) candidates[rnd.nextInt(candidates.length)]};

      final r = planIsolation(g, zone, earthingSystem: EarthingSystem.tnS);
      final brute = _bruteForce(g, zone, cuttable);
      final reason = 'iter $iter, zone $zone, edges $uniqueLinks';

      // Tartibni aralashtirsak ham natija bir xil.
      final shuffled = Graph(g.nodes.toList()..shuffle(rnd), g.edges.toList()..shuffle(rnd));
      expect(
        canonicalJson(planIsolation(shuffled, zone, earthingSystem: EarthingSystem.tnS).toJson()),
        canonicalJson(r.toJson()),
        reason: reason,
      );

      switch (r) {
        case IsolationPlan():
          plans++;
          expect(brute, isNotNull, reason: reason);
          expect(r.cost, brute, reason: 'minimal narx: $reason');
          final cut = {for (final c in r.cut) c.nodeId};
          expect(cut.intersection(zone), isEmpty, reason: reason);
          for (final c in r.cut) {
            expect(cuttable[c.kind], c.cost, reason: reason);
          }
          expect(_reaches(g, zone, cut), isFalse, reason: 'kesimdan keyin manba yetmasligi kerak: $reason');
          if (r.reachableSources.isEmpty) noSource++;
          _checkSteps(r, reason);
        case IsolationBlocked():
          blocked++;
          expect(r.reason, BlockReason.noSwitchingDevice, reason: reason);
          expect(brute, isNull, reason: reason);
          final path = r.path;
          expect(g.node(path.first)!.kind.isSource, isTrue, reason: reason);
          expect(zone, contains(path.last), reason: reason);
          for (var i = 0; i + 1 < path.length; i++) {
            expect(g.neighbors(path[i]), contains(path[i + 1]), reason: reason);
          }
          for (final id in path.skip(1)) {
            expect(zone.contains(id) || !cuttable.containsKey(g.node(id)!.kind), isTrue, reason: reason);
          }
      }
    }
    // Generator ikkala natijani ham yetarlicha hosil qilsin.
    expect(plans, greaterThan(300));
    expect(blocked, greaterThan(50));
    expect(noSource, greaterThan(10));
  });
}

void _checkSteps(IsolationPlan p, String reason) {
  final order = [
    {StepKind.stopPvAc, StepKind.stopPvDc, StepKind.stopGenerator, StepKind.stopUps, StepKind.stopBattery},
    {StepKind.openDevice},
    {StepKind.lockAndTag},
    {StepKind.verifyNoVoltage},
    {StepKind.applyEarthing},
    {StepKind.fenceAndSign},
  ];
  int phase(StepKind k) => order.indexWhere((s) => s.contains(k));
  for (var i = 1; i < p.steps.length; i++) {
    expect(phase(p.steps[i].kind), greaterThanOrEqualTo(phase(p.steps[i - 1].kind)), reason: reason);
    expect(p.steps[i].order, i + 1);
  }
  final verify = p.steps.where((s) => s.kind == StepKind.verifyNoVoltage).toList();
  expect(verify, isNotEmpty, reason: 'kuchlanish yo\'qligini tekshirish majburiy: $reason');
  expect(verify.every((s) => s.mandatory && s.params['pretest_on_known_live'] == true), isTrue);
  expect(p.steps.where((s) => s.kind == StepKind.applyEarthing).length, verify.length, reason: reason);
  expect(p.steps.last.kind, StepKind.fenceAndSign);
  final opened = {for (final s in p.steps.where((s) => s.kind == StepKind.openDevice)) ...s.nodeIds};
  final locked = {for (final s in p.steps.where((s) => s.kind == StepKind.lockAndTag)) ...s.nodeIds};
  expect(opened, {for (final c in p.cut) c.nodeId}, reason: reason);
  expect(locked, opened, reason: reason);
}

/// Kommutatsiya apparatlari to'plamlari bo'yicha minimal narx; ajratib bo'lmasa — null.
int? _bruteForce(Graph g, Set<String> zone, Map<NodeKind, int> costs) {
  final devices = [
    for (final n in g.nodes)
      if (costs.containsKey(n.kind) && !zone.contains(n.id)) n,
  ];
  int? best;
  for (var mask = 0; mask < (1 << devices.length); mask++) {
    var cost = 0;
    final cut = <String>{};
    for (var i = 0; i < devices.length; i++) {
      if (mask & (1 << i) != 0) {
        cost += costs[devices[i].kind]!;
        cut.add(devices[i].id);
      }
    }
    if (best != null && cost >= best) continue;
    if (!_reaches(g, zone, cut)) best = cost;
  }
  return best;
}

/// Kesimdan tashqari tugunlar orqali biror manba (zonadan tashqaridagi) zonaga yetadimi.
bool _reaches(Graph g, Set<String> zone, Set<String> cut) {
  final seen = <String>{};
  final queue = <String>[
    for (final n in g.nodes)
      if (n.kind.isSource && !zone.contains(n.id)) n.id,
  ];
  seen.addAll(queue);
  while (queue.isNotEmpty) {
    final id = queue.removeLast();
    if (zone.contains(id)) return true;
    for (final nb in g.neighbors(id)) {
      if (!cut.contains(nb) && seen.add(nb)) queue.add(nb);
    }
  }
  return false;
}
