import 'package:test/test.dart';
import 'package:zanjir_core/zanjir_core.dart';

import '../support/fixtures.dart';

const protective = {NodeKind.breaker, NodeKind.rcbo, NodeKind.fuse};

void main() {
  group('NodeKind', () {
    test('kodlar va toifalar', () {
      expect(NodeKind.parse('SRC_PV_INVERTER'), NodeKind.srcPvInverter);
      expect(NodeKind.srcPvInverter.code, 'SRC_PV_INVERTER');
      expect(NodeKind.values.where((k) => k.isSource), hasLength(7));
      expect(NodeKind.values.where((k) => k.isSwitching), hasLength(7));
      expect(NodeKind.cable.isSource || NodeKind.cable.isSwitching, isFalse);
      expect(() => NodeKind.parse('TOASTER'), throwsFormatException);
    });

    test('boshqa enum kodlari', () {
      expect(EarthingSystem.parse('TN-C-S'), EarthingSystem.tnCS);
      expect(MeasurementType.parse('RCD_TRIP'), MeasurementType.rcdTrip);
      expect(Verdict.needsReview.code, 'NEEDS_REVIEW');
      expect(() => EarthingSystem.parse('TN'), throwsFormatException);
      expect(() => MeasurementType.parse('X'), throwsFormatException);
    });
  });

  group('Graph', () {
    test('qo\'shnilar ikki tomonlama', () {
      final g = graphOf(
        [node('A', NodeKind.srcGrid), node('B', NodeKind.breaker), node('C', NodeKind.cable)],
        [
          ['A', 'B'],
          ['B', 'C'],
        ],
      );
      expect(g.neighbors('B'), unorderedEquals(['A', 'C']));
      expect(g.neighbors('A'), ['B']);
      expect(g.node('C')!.kind, NodeKind.cable);
      expect(g.node('Z'), isNull);
      expect(g.nodes, hasLength(3));
      expect(g.edges, hasLength(2));
    });

    test('noto\'g\'ri graf rad etiladi', () {
      expect(
        () => graphOf(
          [node('A', NodeKind.cable)],
          [
            ['A', 'X'],
          ],
        ),
        throwsA(isA<GraphException>()),
      );
      expect(
        () => graphOf(
          [node('A', NodeKind.cable)],
          [
            ['A', 'A'],
          ],
        ),
        throwsA(isA<GraphException>()),
      );
      expect(() => graphOf([node('A', NodeKind.cable), node('A', NodeKind.load)], []), throwsA(isA<GraphException>()));
      expect(
        () => graphOf([node('A', NodeKind.cable, siteId: 'other'), node('B', NodeKind.load)], []),
        throwsA(isA<GraphException>()),
      );
      expect(
        () => Graph(
          [node('A', NodeKind.cable), node('B', NodeKind.load)],
          [Edge(id: 'e', siteId: 'other', aNodeId: 'A', bNodeId: 'B', conductors: 'PE')],
        ),
        throwsA(isA<GraphException>()),
      );
      expect(
        () => Graph(
          [node('A', NodeKind.cable), node('B', NodeKind.load)],
          [
            Edge(id: 'e', siteId: 'site', aNodeId: 'A', bNodeId: 'B', conductors: 'PE'),
            Edge(id: 'e', siteId: 'site', aNodeId: 'B', bNodeId: 'A', conductors: 'PE'),
          ],
        ),
        throwsA(isA<GraphException>()),
      );
    });

    test('noma\'lum tugun uchun qo\'shnilar — xato', () {
      final g = graphOf([node('A', NodeKind.cable)], []);
      expect(() => g.neighbors('X'), throwsArgumentError);
    });
  });

  group('findUpstreamProtection', () {
    // GRID — QF0 — BUS — QF1 — CAB1 — SOCK1
    //               └── QF2 — CAB2
    final g = graphOf(
      [
        node('GRID', NodeKind.srcGrid),
        node('QF0', NodeKind.breaker),
        node('BUS', NodeKind.busbar),
        node('QF1', NodeKind.breaker),
        node('CAB1', NodeKind.cable),
        node('SOCK1', NodeKind.socketGroup),
        node('QF2', NodeKind.breaker),
        node('CAB2', NodeKind.cable),
      ],
      [
        ['GRID', 'QF0'],
        ['QF0', 'BUS'],
        ['BUS', 'QF1'],
        ['QF1', 'CAB1'],
        ['CAB1', 'SOCK1'],
        ['BUS', 'QF2'],
        ['QF2', 'CAB2'],
      ],
    );

    test('eng yaqin yuqoridagi apparat', () {
      final r = findUpstreamProtection(g, 'SOCK1', protective);
      expect(r.devices.map((n) => n.id), ['QF1']);
      expect(r.unprotectedPathToSource, isFalse);
    });

    test('pastdagi apparatlar hisobga olinmaydi', () {
      final r = findUpstreamProtection(g, 'BUS', protective);
      expect(r.devices.map((n) => n.id), ['QF0']);
    });

    test('tugunning o\'zi himoya apparati', () {
      final r = findUpstreamProtection(g, 'QF1', protective);
      expect(r.devices.map((n) => n.id), ['QF1']);
    });

    test('manbaga himoyasiz yo\'l', () {
      final g2 = graphOf(
        [
          node('GRID', NodeKind.srcGrid),
          node('CAB', NodeKind.cable),
          node('QF', NodeKind.breaker),
          node('GEN', NodeKind.srcGenerator),
        ],
        [
          ['GRID', 'QF'],
          ['QF', 'CAB'],
          ['CAB', 'GEN'],
        ],
      );
      final r = findUpstreamProtection(g2, 'CAB', protective);
      expect(r.unprotectedPathToSource, isTrue);
      expect(r.devices.map((n) => n.id), ['QF']);
    });

    test('tugunning o\'zi manba — himoyasiz', () {
      final r = findUpstreamProtection(g, 'GRID', protective);
      expect(r.unprotectedPathToSource, isTrue);
    });

    test('manbaga ulanmagan apparat — nomzod emas', () {
      final g3 = graphOf(
        [node('QF', NodeKind.breaker), node('CAB', NodeKind.cable)],
        [
          ['QF', 'CAB'],
        ],
      );
      expect(findUpstreamProtection(g3, 'CAB', protective).devices, isEmpty);
      expect(findUpstreamProtection(g3, 'QF', protective).devices, isEmpty);
    });

    test('ikki kirish — ikkala apparat nomzod', () {
      final g4 = graphOf(
        [
          node('T1', NodeKind.srcTransformer),
          node('T2', NodeKind.srcTransformer),
          node('QF1', NodeKind.breaker),
          node('QF2', NodeKind.breaker),
          node('BUS', NodeKind.busbar),
        ],
        [
          ['T1', 'QF1'],
          ['T2', 'QF2'],
          ['QF1', 'BUS'],
          ['QF2', 'BUS'],
        ],
      );
      final r = findUpstreamProtection(g4, 'BUS', protective);
      expect(r.devices.map((n) => n.id), unorderedEquals(['QF1', 'QF2']));
    });
  });

  group('sourceReachableAvoiding / component', () {
    final g = graphOf(
      [
        node('GRID', NodeKind.srcGrid),
        node('QD', NodeKind.rcd),
        node('QF', NodeKind.breaker),
        node('CAB', NodeKind.cable),
        node('ISO', NodeKind.load),
      ],
      [
        ['GRID', 'QD'],
        ['QD', 'QF'],
        ['QF', 'CAB'],
      ],
    );

    test('UZO barcha yo\'llarda', () {
      expect(sourceReachableAvoiding(g, 'CAB', {NodeKind.rcd, NodeKind.rcbo}), isFalse);
      expect(sourceReachableAvoiding(g, 'CAB', {NodeKind.fuse}), isTrue);
      // Boshlang'ich tugunning o'zi to'siq bo'lsa — manbaga yo'l yo'q.
      expect(sourceReachableAvoiding(g, 'QD', {NodeKind.rcd}), isFalse);
      expect(sourceReachableAvoiding(g, 'GRID', {NodeKind.rcd}), isTrue);
    });

    test('bog\'langan komponent', () {
      expect(component(g, 'CAB'), {'GRID', 'QD', 'QF', 'CAB'});
      expect(component(g, 'ISO'), {'ISO'});
    });
  });
}
