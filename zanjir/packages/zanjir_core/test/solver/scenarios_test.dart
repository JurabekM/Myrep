import 'package:test/test.dart';
import 'package:zanjir_core/zanjir_core.dart';

import '../support/fixtures.dart';

/// Prompt 5.3 va 2-faza: 7 ta majburiy stsenariy + chekka holatlar.
void main() {
  IsolationPlan plan(Graph g, Set<String> zone, {EarthingSystem? es = EarthingSystem.tnS}) {
    final r = planIsolation(g, zone, earthingSystem: es);
    expect(r, isA<IsolationPlan>(), reason: r is IsolationBlocked ? '${r.reason} ${r.path}' : '');
    return r as IsolationPlan;
  }

  List<String> cutIds(IsolationPlan p) => [for (final c in p.cut) c.nodeId];
  List<StepKind> kinds(IsolationPlan p) => [for (final s in p.steps) s.kind];
  Set<WarningKind> warnings(IsolationResult r) => {for (final w in r.warnings) w.kind};

  group('1. Radial', () {
    Graph radial({bool withSwitch = false, SwitchState? qf1State}) => graphOf(
      [
        node('GRID', NodeKind.srcGrid),
        node('QF0', NodeKind.breaker),
        node('BUS', NodeKind.busbar),
        if (withSwitch) node('QS1', NodeKind.loadSwitch),
        Node(id: 'QF1', siteId: 'site', kind: NodeKind.breaker, label: 'QF1', verified: true, state: qf1State),
        node('CAB1', NodeKind.cable, attrs: {'length_m': 22}),
        node('LOAD1', NodeKind.load),
        node('QF2', NodeKind.breaker),
        node('CAB2', NodeKind.cable),
      ],
      [
        ['GRID', 'QF0'],
        ['QF0', 'BUS'],
        if (withSwitch) ...[
          ['BUS', 'QS1'],
          ['QS1', 'QF1'],
        ] else
          ['BUS', 'QF1'],
        ['QF1', 'CAB1'],
        ['CAB1', 'LOAD1'],
        ['BUS', 'QF2'],
        ['QF2', 'CAB2'],
      ],
    );

    test('teng narxli kesimlardan zonaga yaqini (QF1, QF0 emas)', () {
      final p = plan(radial(), {'CAB1', 'LOAD1'});
      expect(cutIds(p), ['QF1']);
      expect(p.cost, 3);
      expect(p.reachableSources, ['GRID']);
      expect(p.entryPoints.map((e) => (e.zoneNodeId, e.outsideNodeId)), [('CAB1', 'QF1')]);
      expect(kinds(p), [
        StepKind.openDevice,
        StepKind.lockAndTag,
        StepKind.verifyNoVoltage,
        StepKind.applyEarthing,
        StepKind.fenceAndSign,
      ]);
      expect([for (final s in p.steps) s.order], [1, 2, 3, 4, 5]);
      expect(p.steps[0].params, {'action': 'OPEN', 'label': 'QF1', 'node_kind': 'BREAKER'});
      expect(p.steps[1].params, {'poster': 'DO_NOT_SWITCH_ON'});
      expect(p.steps[2].params, {'zone_node_id': 'CAB1', 'outside_node_id': 'QF1', 'pretest_on_known_live': true});
      expect(p.steps[4].params, {'poster': 'WORK_HERE'});
      expect(p.steps.every((s) => s.mandatory), isTrue);
      final cable = p.warnings.singleWhere((w) => w.kind == WarningKind.cableDischarge);
      expect(cable.nodeIds, ['CAB1']);
      expect(cable.params, {'length_m': 22});
      expect(p.solverVersion, solverVersion);
      expect(p.targetNodeIds, ['CAB1', 'LOAD1']);
    });

    test('arzonroq apparat uzoqroq bo\'lsa ham tanlanadi (SWITCH = 1 < BREAKER = 3)', () {
      final p = plan(radial(withSwitch: true), {'CAB1'});
      expect(cutIds(p), ['QS1']);
      expect(p.cost, 1);
    });

    test('apparat holati (OPEN) hisobga olinmaydi — konservativ', () {
      final open = plan(radial(qf1State: SwitchState.open), {'CAB1', 'LOAD1'});
      expect(cutIds(open), ['QF1']);
      expect(open.graphSnapshotHash, plan(radial(), {'CAB1', 'LOAD1'}).graphSnapshotHash);
    });
  });

  group('2. Ikki kirishli AVR (ATS)', () {
    final g = graphOf(
      [
        node('T1', NodeKind.srcTransformer),
        node('T2', NodeKind.srcTransformer),
        node('QF1', NodeKind.breaker),
        node('QF2', NodeKind.breaker),
        node('ATS1', NodeKind.ats),
        node('BUS', NodeKind.busbar),
        node('QF3', NodeKind.breaker),
        node('LOAD', NodeKind.load),
      ],
      [
        ['T1', 'QF1'],
        ['T2', 'QF2'],
        ['QF1', 'ATS1'],
        ['QF2', 'ATS1'],
        ['ATS1', 'BUS'],
        ['BUS', 'QF3'],
        ['QF3', 'LOAD'],
      ],
    );

    test('ikkala kirish avtomati (3+3) AVR (50) dan arzon', () {
      final p = plan(g, {'BUS'});
      expect(cutIds(p), ['QF1', 'QF2']);
      expect(p.cost, 6);
      expect(p.reachableSources, ['T1', 'T2']);
      expect(warnings(p), isNot(contains(WarningKind.contactorOrAtsInCut)));
    });

    test('zona pastda — bitta avtomat', () {
      expect(cutIds(plan(g, {'LOAD'})), ['QF3']);
    });

    test('kirish avtomatlari yo\'q — AVR kesiladi va ogohlantirish', () {
      final g2 = graphOf(
        [
          node('T1', NodeKind.srcTransformer),
          node('T2', NodeKind.srcTransformer),
          node('ATS1', NodeKind.ats),
          node('BUS', NodeKind.busbar),
        ],
        [
          ['T1', 'ATS1'],
          ['T2', 'ATS1'],
          ['ATS1', 'BUS'],
        ],
      );
      final p = plan(g2, {'BUS'});
      expect(cutIds(p), ['ATS1']);
      expect(p.cost, 50);
      expect(p.warnings.singleWhere((w) => w.kind == WarningKind.contactorOrAtsInCut).nodeIds, ['ATS1']);
    });
  });

  group('3. PV teskari ta\'minot', () {
    final g = graphOf(
      [
        node('GRID', NodeKind.srcGrid),
        node('QF0', NodeKind.breaker),
        node('BUS', NodeKind.busbar),
        node('QF1', NodeKind.breaker),
        node('DB', NodeKind.panel),
        node('QF2', NodeKind.breaker),
        node('LOAD', NodeKind.load),
        node('PV', NodeKind.srcPvInverter, attrs: {'anti_islanding': true}),
        node('QPV', NodeKind.loadSwitch),
      ],
      [
        ['GRID', 'QF0'],
        ['QF0', 'BUS'],
        ['BUS', 'QF1'],
        ['QF1', 'DB'],
        ['DB', 'QF2'],
        ['QF2', 'LOAD'],
        ['PV', 'QPV'],
        ['QPV', 'DB'],
      ],
    );

    test('tarmoq va PV tomonidan kesiladi, PV avval AC, keyin DC to\'xtatiladi', () {
      final p = plan(g, {'DB'});
      expect(cutIds(p), ['QF1', 'QPV'], reason: 'QF0+QPV ham 4, lekin QF1 zonaga yaqin');
      expect(p.cost, 4);
      expect(p.reachableSources, ['GRID', 'PV']);
      expect(kinds(p), [
        StepKind.stopPvAc,
        StepKind.stopPvDc,
        StepKind.openDevice,
        StepKind.openDevice,
        StepKind.lockAndTag,
        StepKind.lockAndTag,
        StepKind.verifyNoVoltage,
        StepKind.verifyNoVoltage,
        StepKind.applyEarthing,
        StepKind.applyEarthing,
        StepKind.fenceAndSign,
      ]);
      expect(p.steps[0].nodeIds, ['PV']);
      expect(p.steps[3].params['action'], 'OPEN');
      expect(p.entryPoints.map((e) => (e.zoneNodeId, e.outsideNodeId)), [('DB', 'QF1'), ('DB', 'QPV')]);
      expect(p.warnings.singleWhere((w) => w.kind == WarningKind.pvDcSide).nodeIds, ['PV']);
    });

    test('zona pastda — QF2 ikkala manbani kesadi, PV baribir to\'xtatiladi', () {
      final p = plan(g, {'LOAD'});
      expect(cutIds(p), ['QF2']);
      expect(p.reachableSources, ['GRID', 'PV']);
      expect(kinds(p).take(2), [StepKind.stopPvAc, StepKind.stopPvDc]);
    });
  });

  group('4. UPS aylanma yo\'li (bypass)', () {
    final g = graphOf(
      [
        node('GRID', NodeKind.srcGrid),
        node('QF0', NodeKind.breaker),
        node('BUS1', NodeKind.busbar),
        node('QF_IN', NodeKind.breaker),
        node('UPS', NodeKind.srcUps),
        node('QF_OUT', NodeKind.breaker),
        node('BUS2', NodeKind.busbar),
        node('QS_BYP', NodeKind.loadSwitch),
        node('QF_L', NodeKind.breaker),
        node('LOAD', NodeKind.load),
      ],
      [
        ['GRID', 'QF0'],
        ['QF0', 'BUS1'],
        ['BUS1', 'QF_IN'],
        ['QF_IN', 'UPS'],
        ['UPS', 'QF_OUT'],
        ['QF_OUT', 'BUS2'],
        ['BUS1', 'QS_BYP'],
        ['QS_BYP', 'BUS2'],
        ['BUS2', 'QF_L'],
        ['QF_L', 'LOAD'],
      ],
    );

    test('UPS chiqishi va bypass birga kesiladi, UPS to\'xtatiladi', () {
      final p = plan(g, {'BUS2'});
      expect(cutIds(p), ['QF_OUT', 'QS_BYP']);
      expect(p.cost, 4);
      expect(p.reachableSources, ['GRID', 'UPS']);
      expect(p.steps.first.kind, StepKind.stopUps);
      expect(p.steps.first.nodeIds, ['UPS']);
      expect(p.entryPoints.map((e) => e.outsideNodeId), ['QF_OUT', 'QS_BYP'], reason: 'QF_L — pastda, kirish emas');
    });
  });

  group('5. Ikki fiderli halqa', () {
    final g = graphOf(
      [
        node('SUB', NodeKind.srcTransformer),
        node('BUSS', NodeKind.busbar),
        node('QFA', NodeKind.breaker),
        node('SWA1', NodeKind.loadSwitch),
        node('RMU1', NodeKind.busbar),
        node('SWA2', NodeKind.loadSwitch),
        node('CABZ', NodeKind.cable),
        node('SWB2', NodeKind.loadSwitch),
        node('RMU2', NodeKind.busbar),
        node('SWB1', NodeKind.loadSwitch),
        node('QFB', NodeKind.breaker),
      ],
      [
        ['SUB', 'BUSS'],
        ['BUSS', 'QFA'],
        ['QFA', 'SWA1'],
        ['SWA1', 'RMU1'],
        ['RMU1', 'SWA2'],
        ['SWA2', 'CABZ'],
        ['CABZ', 'SWB2'],
        ['SWB2', 'RMU2'],
        ['RMU2', 'SWB1'],
        ['SWB1', 'QFB'],
        ['QFB', 'BUSS'],
      ],
    );

    test('ikkala tomondan zonaga eng yaqin ajratgichlar', () {
      final p = plan(g, {'CABZ'});
      expect(cutIds(p), ['SWA2', 'SWB2']);
      expect(p.cost, 2);
      expect(kinds(p).where((k) => k == StepKind.verifyNoVoltage), hasLength(2));
      expect(kinds(p).where((k) => k == StepKind.applyEarthing), hasLength(2));
    });
  });

  group('6. Qo\'lda almashtiriladigan generator', () {
    final g = graphOf(
      [
        node('GRID', NodeKind.srcGrid),
        node('QF1', NodeKind.breaker),
        node('QS_CO', NodeKind.loadSwitch),
        node('BUS', NodeKind.busbar),
        node('QF2', NodeKind.breaker),
        node('LOAD', NodeKind.load),
        node('GEN', NodeKind.srcGenerator),
        node('QG', NodeKind.breaker),
      ],
      [
        ['GRID', 'QF1'],
        ['QF1', 'QS_CO'],
        ['GEN', 'QG'],
        ['QG', 'QS_CO'],
        ['QS_CO', 'BUS'],
        ['BUS', 'QF2'],
        ['QF2', 'LOAD'],
      ],
    );

    test('almashtirgich ikkala manbani ham ajratadi, generator to\'xtatiladi', () {
      final p = plan(g, {'BUS'});
      expect(cutIds(p), ['QS_CO']);
      expect(p.cost, 1);
      expect(p.reachableSources, ['GEN', 'GRID']);
      expect(p.steps.first.kind, StepKind.stopGenerator);
      expect(p.steps.first.nodeIds, ['GEN']);
    });
  });

  group('7. Kommutatsiya apparatisiz yo\'l → Blocked', () {
    test('yo\'lning o\'zi ko\'rsatiladi', () {
      final g = graphOf(
        [
          node('GRID', NodeKind.srcGrid),
          node('BUS', NodeKind.busbar),
          node('CAB', NodeKind.cable),
          node('LOAD', NodeKind.load),
        ],
        [
          ['GRID', 'BUS'],
          ['BUS', 'CAB'],
          ['CAB', 'LOAD'],
        ],
      );
      final r = planIsolation(g, {'LOAD'});
      expect(r, isA<IsolationBlocked>());
      final b = r as IsolationBlocked;
      expect(b.reason, BlockReason.noSwitchingDevice);
      expect(b.path, ['GRID', 'BUS', 'CAB', 'LOAD']);
      expect(b.graphSnapshotHash, graphSnapshotHash(g));
    });

    test('bitta manba himoyalangan, ikkinchisi yo\'q — himoyasiz yo\'l', () {
      final g = graphOf(
        [
          node('GRID', NodeKind.srcGrid),
          node('QF', NodeKind.breaker),
          node('BUS', NodeKind.busbar),
          node('LOAD', NodeKind.load),
          node('GEN', NodeKind.srcGenerator),
          node('CABG', NodeKind.cable),
        ],
        [
          ['GRID', 'QF'],
          ['QF', 'BUS'],
          ['BUS', 'LOAD'],
          ['GEN', 'CABG'],
          ['CABG', 'BUS'],
        ],
      );
      final b = planIsolation(g, {'LOAD'}) as IsolationBlocked;
      expect(b.reason, BlockReason.noSwitchingDevice);
      expect(b.path, ['GEN', 'CABG', 'BUS', 'LOAD']);
    });
  });

  group('chekka holatlar', () {
    test('manba zona ichida → Blocked', () {
      final g = graphOf(
        [node('GEN', NodeKind.srcGenerator), node('QG', NodeKind.breaker), node('BUS', NodeKind.busbar)],
        [
          ['GEN', 'QG'],
          ['QG', 'BUS'],
        ],
      );
      final b = planIsolation(g, {'GEN', 'BUS'}) as IsolationBlocked;
      expect(b.reason, BlockReason.sourceInZone);
      expect(b.path, ['GEN']);
    });

    test('zona ichidagi kondensator — ogohlantirish, manba hisoblanmaydi', () {
      final g = graphOf(
        [
          node('GRID', NodeKind.srcGrid),
          node('QF', NodeKind.breaker),
          node('BUS', NodeKind.busbar),
          node('CAP', NodeKind.srcCapacitor),
        ],
        [
          ['GRID', 'QF'],
          ['QF', 'BUS'],
          ['BUS', 'CAP'],
        ],
      );
      final p = plan(g, {'BUS', 'CAP'});
      expect(cutIds(p), ['QF']);
      expect(p.reachableSources, ['GRID']);
      expect(p.warnings.singleWhere((w) => w.kind == WarningKind.capacitorInZone).nodeIds, ['CAP']);
    });

    test('hech qaysi manba yetib bormaydi — kesim yo\'q, lekin tekshirish va yerga ulash majburiy', () {
      final g = graphOf(
        [node('CAB', NodeKind.cable), node('LOAD', NodeKind.load), node('GRID', NodeKind.srcGrid)],
        [
          ['CAB', 'LOAD'],
        ],
      );
      final p = plan(g, {'CAB', 'LOAD'});
      expect(p.cut, isEmpty);
      expect(p.cost, 0);
      expect(p.reachableSources, isEmpty);
      expect(warnings(p), contains(WarningKind.noSourceReachable));
      expect(kinds(p), [
        StepKind.verifyNoVoltage,
        StepKind.verifyNoVoltage,
        StepKind.applyEarthing,
        StepKind.applyEarthing,
        StepKind.fenceAndSign,
      ]);
      expect(p.steps.first.params, {'zone_node_id': 'CAB', 'outside_node_id': null, 'pretest_on_known_live': true});
    });

    test('saqlagich — olib qo\'yiladi (REMOVE_FUSE)', () {
      final g = graphOf(
        [node('GRID', NodeKind.srcGrid), node('FU', NodeKind.fuse), node('LOAD', NodeKind.load)],
        [
          ['GRID', 'FU'],
          ['FU', 'LOAD'],
        ],
      );
      final p = plan(g, {'LOAD'});
      expect(p.cost, 2);
      expect(p.steps.first.params['action'], 'REMOVE_FUSE');
    });

    test('kontaktor kesimda — ogohlantirish; UZO narxi 5', () {
      final g = graphOf(
        [
          node('GRID', NodeKind.srcGrid),
          node('KM', NodeKind.contactor),
          node('QD', NodeKind.rcd),
          node('LOAD', NodeKind.load),
        ],
        [
          ['GRID', 'KM'],
          ['KM', 'QD'],
          ['QD', 'LOAD'],
        ],
      );
      final p = plan(g, {'LOAD'});
      expect(cutIds(p), ['QD']);
      expect(p.cost, 5);
      final kmOnly = plan(
        graphOf(
          [node('GRID', NodeKind.srcGrid), node('KM', NodeKind.contactor), node('LOAD', NodeKind.load)],
          [
            ['GRID', 'KM'],
            ['KM', 'LOAD'],
          ],
        ),
        {'LOAD'},
      );
      expect(cutIds(kmOnly), ['KM']);
      expect(warnings(kmOnly), contains(WarningKind.contactorOrAtsInCut));
    });

    test('tasdiqlanmagan tugunlar (zona komponentida) — ogohlantirish', () {
      final g = graphOf(
        [
          node('GRID', NodeKind.srcGrid),
          node('QF', NodeKind.breaker, verified: false),
          node('LOAD', NodeKind.load),
          node('OTHER', NodeKind.load, verified: false),
        ],
        [
          ['GRID', 'QF'],
          ['QF', 'LOAD'],
        ],
      );
      final p = plan(g, {'LOAD'});
      expect(p.warnings.singleWhere((w) => w.kind == WarningKind.unverifiedNode).nodeIds, ['QF']);
    });

    test('PEN: TN-C tizimi, PEN o\'tkazgichli qirra, yerga ulash tizimi noma\'lum', () {
      Graph g(String conductors) => Graph(
        [node('GRID', NodeKind.srcGrid), node('QF', NodeKind.breaker), node('LOAD', NodeKind.load)],
        [
          const Edge(id: 'e1', siteId: 'site', aNodeId: 'GRID', bNodeId: 'QF', conductors: 'L1 N PE'),
          Edge(id: 'e2', siteId: 'site', aNodeId: 'QF', bNodeId: 'LOAD', conductors: conductors),
        ],
      );
      expect(warnings(plan(g('L1 N PE'), {'LOAD'})), isNot(contains(WarningKind.penConductor)));
      expect(warnings(plan(g('L1 N PE'), {'LOAD'}, es: EarthingSystem.tnC)), contains(WarningKind.penConductor));
      final pen = plan(g('L1 L2 L3 PEN'), {'LOAD'}).warnings.singleWhere((w) => w.kind == WarningKind.penConductor);
      expect(pen.nodeIds, ['LOAD']);
      expect(warnings(plan(g('L1 N PE'), {'LOAD'}, es: null)), contains(WarningKind.earthingSystemUnknown));
    });

    test('noto\'g\'ri zona — ArgumentError', () {
      final g = graphOf([node('A', NodeKind.load)], []);
      expect(() => planIsolation(g, {}), throwsArgumentError);
      expect(() => planIsolation(g, {'X'}), throwsArgumentError);
    });

    test('mustaqil tekshiruv: noto\'g\'ri kesim → Blocked va xato logga yoziladi', () {
      final g = graphOf(
        [node('GRID', NodeKind.srcGrid), node('QF', NodeKind.breaker), node('LOAD', NodeKind.load)],
        [
          ['GRID', 'QF'],
          ['QF', 'LOAD'],
        ],
      );
      final logged = <(String, Map<String, Object?>)>[];
      final r = planIsolation(
        g,
        {'LOAD'},
        log: (event, data) => logged.add((event, data)),
        debugMutateCut: (cut) => const {},
      );
      expect(r, isA<IsolationBlocked>());
      final b = r as IsolationBlocked;
      expect(b.reason, BlockReason.verificationFailed);
      expect(b.path, ['GRID', 'QF', 'LOAD']);
      expect(logged.single.$1, 'isolation_cut_verification_failed');
      expect(logged.single.$2['path'], ['GRID', 'QF', 'LOAD']);
    });
  });

  group('graph_snapshot_hash va STALE', () {
    Graph build({
      String label = 'QF',
      Map<String, Object?> attrs = const {},
      bool extra = false,
      bool reverse = false,
    }) {
      final nodes = [
        node('GRID', NodeKind.srcGrid),
        Node(id: 'QF', siteId: 'site', kind: NodeKind.breaker, label: label, attrs: attrs, verified: true),
        node('LOAD', NodeKind.load),
        if (extra) node('X', NodeKind.load),
      ];
      final edges = [
        const Edge(id: 'e1', siteId: 'site', aNodeId: 'GRID', bNodeId: 'QF', conductors: 'L1 N PE'),
        const Edge(id: 'e2', siteId: 'site', aNodeId: 'QF', bNodeId: 'LOAD', conductors: 'L1 N PE'),
      ];
      return reverse ? Graph(nodes.reversed, edges.reversed) : Graph(nodes, edges);
    }

    test('tartib va qirra yo\'nalishiga bog\'liq emas', () {
      expect(graphSnapshotHash(build()), graphSnapshotHash(build(reverse: true)));
      final flipped = Graph(build().nodes, const [
        Edge(id: 'e1', siteId: 'site', aNodeId: 'QF', bNodeId: 'GRID', conductors: 'L1 N PE'),
        Edge(id: 'e2', siteId: 'site', aNodeId: 'LOAD', bNodeId: 'QF', conductors: 'L1 N PE'),
      ]);
      expect(graphSnapshotHash(flipped), graphSnapshotHash(build()));
      expect(graphSnapshotHash(build()), matches(RegExp(r'^[0-9a-f]{64}$')));
    });

    test('graf o\'zgarsa — reja STALE', () {
      final p = planIsolation(build(), {'LOAD'});
      expect(isPlanStale(p, build()), isFalse);
      expect(isPlanStale(p, build(reverse: true)), isFalse);
      expect(isPlanStale(p, build(label: 'QF-1')), isTrue);
      expect(isPlanStale(p, build(attrs: {'in_a': 16})), isTrue);
      expect(isPlanStale(p, build(extra: true)), isTrue);
      expect(isPlanStale(p, build(), earthingSystem: EarthingSystem.tnC), isTrue);
    });

    test('kanonik graf tarkibi', () {
      expect(canonicalGraph(build(attrs: {'in_a': 16, 'curve': 'C'}), earthingSystem: EarthingSystem.tnS), {
        'schema': 'zanjir.graph/1',
        'earthing_system': 'TN-S',
        'nodes': [
          {
            'id': 'GRID',
            'kind': 'SRC_GRID',
            'label': 'GRID',
            'attrs': <String, Object?>{},
            'verified': true,
            'panel_id': null,
          },
          {
            'id': 'LOAD',
            'kind': 'LOAD',
            'label': 'LOAD',
            'attrs': <String, Object?>{},
            'verified': true,
            'panel_id': null,
          },
          {
            'id': 'QF',
            'kind': 'BREAKER',
            'label': 'QF',
            'attrs': {'in_a': 16, 'curve': 'C'},
            'verified': true,
            'panel_id': null,
          },
        ],
        'edges': [
          {'id': 'e1', 'a': 'GRID', 'b': 'QF', 'conductors': 'L1 N PE'},
          {'id': 'e2', 'a': 'LOAD', 'b': 'QF', 'conductors': 'L1 N PE'},
        ],
      });
    });
  });

  test('toJson — deterministik va kanonik JSON ga o\'giriladi', () {
    final g = graphOf(
      [node('GRID', NodeKind.srcGrid), node('QF', NodeKind.breaker), node('LOAD', NodeKind.load)],
      [
        ['GRID', 'QF'],
        ['QF', 'LOAD'],
      ],
    );
    final a = planIsolation(g, {'LOAD'}).toJson();
    final b = planIsolation(Graph(g.nodes.toList().reversed, g.edges.reversed), {'LOAD'}).toJson();
    expect(canonicalJson(a), canonicalJson(b));
    expect(a['status'], 'PLAN');
    expect(a['solver_version'], solverVersion);
    expect((a['steps'] as List).length, 5);
    final blocked = planIsolation(
      graphOf(
        [node('GRID', NodeKind.srcGrid), node('LOAD', NodeKind.load)],
        [
          ['GRID', 'LOAD'],
        ],
      ),
      {'LOAD'},
    ).toJson();
    expect(blocked['status'], 'BLOCKED');
    expect(blocked['reason'], 'no_switching_device');
    expect(blocked['path'], ['GRID', 'LOAD']);
  });
}
