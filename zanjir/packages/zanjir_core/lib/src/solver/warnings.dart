import '../graph/graph.dart';
import '../graph/traversal.dart';
import '../model/enums.dart';
import 'cut_costs.dart';
import 'plan.dart';

/// Prompt 5.3, 8-band. Ogohlantirishlar WarningKind tartibida.
List<PlanWarning> buildWarnings({
  required Graph graph,
  required List<String> zone,
  required List<String> reachableSources,
  required List<String> cut,
  required EarthingSystem? earthingSystem,
  required bool noSourceReachable,
}) {
  final zoneSet = zone.toSet();
  final out = <PlanWarning>[];

  final around = <String>{for (final z in zone) ...component(graph, z)};
  final unverified = [
    for (final id in around)
      if (!graph.node(id)!.verified) id,
  ]..sort();
  if (unverified.isNotEmpty) out.add(PlanWarning(WarningKind.unverifiedNode, unverified));

  final capacitors = [
    for (final z in zone)
      if (graph.node(z)!.kind == NodeKind.srcCapacitor) z,
  ];
  if (capacitors.isNotEmpty) out.add(PlanWarning(WarningKind.capacitorInZone, capacitors));

  // Kabel sig'imi: zonadagi har bir kabel uchun zaryadsizlantirish (uzunlik chegarasi yo'q — konservativ).
  for (final z in zone) {
    final n = graph.node(z)!;
    if (n.kind == NodeKind.cable)
      out.add(PlanWarning(WarningKind.cableDischarge, [z], {'length_m': n.attrs['length_m']}));
  }

  final pv = [
    for (final s in reachableSources)
      if (graph.node(s)!.kind == NodeKind.srcPvInverter) s,
  ];
  if (pv.isNotEmpty) out.add(PlanWarning(WarningKind.pvDcSide, pv));

  final penNodes = <String>{
    for (final e in graph.edges)
      if (e.conductors.split(RegExp(r'\s+')).contains('PEN'))
        for (final id in [e.aNodeId, e.bNodeId])
          if (zoneSet.contains(id)) id,
  }.toList()..sort();
  if (earthingSystem == EarthingSystem.tnC || penNodes.isNotEmpty) {
    out.add(PlanWarning(WarningKind.penConductor, penNodes, {'earthing_system': earthingSystem?.code}));
  }

  final risky = [
    for (final c in cut)
      if (warnInCut.contains(graph.node(c)!.kind)) c,
  ];
  if (risky.isNotEmpty) out.add(PlanWarning(WarningKind.contactorOrAtsInCut, risky));

  if (noSourceReachable) out.add(const PlanWarning(WarningKind.noSourceReachable, []));
  if (earthingSystem == null) out.add(const PlanWarning(WarningKind.earthingSystemUnknown, []));
  return out;
}
