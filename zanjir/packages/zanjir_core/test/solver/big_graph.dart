import 'package:zanjir_core/zanjir_core.dart';

/// Katta realistik graf: 2 transformator + generator + PV, AVR, asosiy shina,
/// fiderlar → shitlar → guruh avtomatlari → kabellar → iste'molchilar, fiderlar orasida halqalar.
class BigGraph {
  BigGraph(this.graph, this.leafZone, this.feederZone, this.mainBusZone);
  final Graph graph;
  final Set<String> leafZone;
  final Set<String> feederZone;
  final Set<String> mainBusZone;
}

BigGraph buildBigGraph(int targetNodes) {
  final nodes = <Node>[];
  final edges = <Edge>[];
  var e = 0;
  void n(String id, NodeKind kind) => nodes.add(Node(id: id, siteId: 's', kind: kind, label: id, verified: true));
  void link(String a, String b) =>
      edges.add(Edge(id: 'e${e++}', siteId: 's', aNodeId: a, bNodeId: b, conductors: 'L1 L2 L3 N PE'));

  n('T1', NodeKind.srcTransformer);
  n('T2', NodeKind.srcTransformer);
  n('GEN', NodeKind.srcGenerator);
  n('QF_T1', NodeKind.breaker);
  n('QF_T2', NodeKind.breaker);
  n('QG', NodeKind.breaker);
  n('ATS', NodeKind.ats);
  n('MAIN', NodeKind.busbar);
  link('T1', 'QF_T1');
  link('T2', 'QF_T2');
  link('GEN', 'QG');
  link('QF_T1', 'ATS');
  link('QF_T2', 'ATS');
  link('QG', 'MAIN');
  link('ATS', 'MAIN');

  var f = 0;
  String? prevPanel;
  while (nodes.length < targetNodes) {
    final qf = 'QF_F$f';
    final cab = 'CAB_F$f';
    final panel = 'SHR$f';
    final bus = 'BUS$f';
    n(qf, NodeKind.breaker);
    n(cab, NodeKind.cable);
    n(panel, NodeKind.panel);
    n(bus, NodeKind.busbar);
    link('MAIN', qf);
    link(qf, cab);
    link(cab, panel);
    link(panel, bus);
    if (prevPanel != null && f % 5 == 0) {
      final tie = 'QS_TIE$f';
      n(tie, NodeKind.loadSwitch);
      link(prevPanel, tie);
      link(tie, panel);
    }
    if (f % 7 == 3) {
      final pv = 'PV$f';
      final qpv = 'QPV$f';
      n(pv, NodeKind.srcPvInverter);
      n(qpv, NodeKind.loadSwitch);
      link(pv, qpv);
      link(qpv, bus);
    }
    for (var g = 0; g < 8; g++) {
      final id = '${f}_$g';
      n('QF$id', g.isEven ? NodeKind.breaker : NodeKind.rcbo);
      n('CAB$id', NodeKind.cable);
      n('LOAD$id', g % 3 == 0 ? NodeKind.socketGroup : NodeKind.load);
      link(bus, 'QF$id');
      link('QF$id', 'CAB$id');
      link('CAB$id', 'LOAD$id');
    }
    prevPanel = panel;
    f++;
  }
  return BigGraph(Graph(nodes, edges), {'CAB${f ~/ 2}_3', 'LOAD${f ~/ 2}_3'}, {'SHR${f ~/ 2}', 'BUS${f ~/ 2}'}, {
    'MAIN',
  });
}
