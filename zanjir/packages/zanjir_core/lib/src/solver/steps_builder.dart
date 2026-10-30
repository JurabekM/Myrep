import '../graph/graph.dart';
import '../model/enums.dart';
import 'plan.dart';

/// 5 ta texnik tadbir tartibidagi qadamlar (prompt 5.3, 7-band).
List<PlanStep> buildSteps({
  required Graph graph,
  required List<String> zone,
  required List<String> reachableSources,
  required List<String> cut,
  required List<EntryPoint> entries,
}) {
  final raw = <(StepKind, List<String>, Map<String, Object?>)>[];
  Map<String, Object?> label(String id) => {'label': graph.node(id)!.label};

  // 1. Teskari manbalarni to'xtatish: PV (avval AC, keyin DC), generator, UPS, akkumulyator.
  List<String> ofKind(NodeKind k) => [
    for (final s in reachableSources)
      if (graph.node(s)!.kind == k) s,
  ];
  for (final pv in ofKind(NodeKind.srcPvInverter)) {
    raw.add((StepKind.stopPvAc, [pv], label(pv)));
    raw.add((StepKind.stopPvDc, [pv], label(pv)));
  }
  for (final (kind, step) in const [
    (NodeKind.srcGenerator, StepKind.stopGenerator),
    (NodeKind.srcUps, StepKind.stopUps),
    (NodeKind.srcBattery, StepKind.stopBattery),
  ]) {
    for (final s in ofKind(kind)) {
      raw.add((step, [s], label(s)));
    }
  }

  // 2. Kesimdagi apparatlarni o'chirish; 3. blokirovka va plakat.
  for (final c in cut) {
    final kind = graph.node(c)!.kind;
    raw.add((
      StepKind.openDevice,
      [c],
      {'action': kind == NodeKind.fuse ? 'REMOVE_FUSE' : 'OPEN', ...label(c), 'node_kind': kind.code},
    ));
  }
  for (final c in cut) {
    raw.add((StepKind.lockAndTag, [c], const {'poster': 'DO_NOT_SWITCH_ON'}));
  }

  // 4. Har bir kirish nuqtasida kuchlanish yo'qligini tekshirish — majburiy; ko'rsatkich avval
  // kuchlanish borligi ma'lum joyda sinaladi. 5. Har bir tomonda yerga ulagich.
  List<String> ids(EntryPoint e) => [e.zoneNodeId, ?e.outsideNodeId];
  for (final e in entries) {
    raw.add((StepKind.verifyNoVoltage, ids(e), {...e.toJson(), 'pretest_on_known_live': true}));
  }
  for (final e in entries) {
    raw.add((StepKind.applyEarthing, ids(e), e.toJson()));
  }

  // 6. To'siq va "Shu yerda ishlang" plakati.
  raw.add((StepKind.fenceAndSign, zone, const {'poster': 'WORK_HERE'}));

  return [
    for (var i = 0; i < raw.length; i++)
      PlanStep(
        order: i + 1,
        kind: raw[i].$1,
        nodeIds: List.unmodifiable(raw[i].$2),
        params: Map.unmodifiable(raw[i].$3),
      ),
  ];
}
