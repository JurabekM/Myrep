import 'dart:collection';

import 'package:meta/meta.dart';

import '../graph/graph.dart';
import '../model/enums.dart';
import 'cut_costs.dart';
import 'edmonds_karp.dart';
import 'plan.dart';
import 'snapshot.dart';
import 'steps_builder.dart';
import 'warnings.dart';

/// Solver versiyasi `isolation_plan.solver_version` ga yoziladi. Algoritm yoki narxlar o'zgarsa oshiriladi.
const String solverVersion = '1.0.0';

/// Xato hodisalari uchun log (maxfiy ma'lumotsiz: faqat tugun ID'lari).
typedef SolverLog = void Function(String event, Map<String, Object?> data);

/// Ish zonasi `zone` ni barcha manbalardan ajratish rejasi (prompt 5.3).
/// Konservativ faraz: apparatlarning joriy `state` holati hisobga olinmaydi.
IsolationResult planIsolation(
  Graph graph,
  Set<String> zone, {
  EarthingSystem? earthingSystem,
  SolverLog? log,
  @visibleForTesting Set<String> Function(Set<String> cut)? debugMutateCut,
}) {
  if (zone.isEmpty) throw ArgumentError.value(zone, 'zone', 'bo\'sh');
  for (final z in zone) {
    if (graph.node(z) == null) throw ArgumentError.value(z, 'zone', 'grafda yo\'q');
  }
  final hash = graphSnapshotHash(graph, earthingSystem: earthingSystem);
  final targets = zone.toList()..sort();
  final adj = _sortedAdjacency(graph);

  List<PlanWarning> warnings({List<String> sources = const [], List<String> cut = const [], bool noSource = false}) =>
      buildWarnings(
        graph: graph,
        zone: targets,
        reachableSources: sources,
        cut: cut,
        earthingSystem: earthingSystem,
        noSourceReachable: noSource,
      );
  IsolationBlocked blocked(BlockReason reason, List<String> path, List<String> sources) => IsolationBlocked(
    solverVersion: solverVersion,
    targetNodeIds: targets,
    graphSnapshotHash: hash,
    warnings: warnings(sources: sources),
    reason: reason,
    path: List.unmodifiable(path),
  );

  // Zona ichidagi manba (kondensator bundan mustasno — u zaryadsizlantiriladi).
  for (final z in targets) {
    final kind = graph.node(z)!.kind;
    if (kind.isSource && kind != NodeKind.srcCapacitor) return blocked(BlockReason.sourceInZone, [z], const []);
  }

  // 2. S_r — zonaga yetib boradigan manbalar (yo'nalishsiz graf: zona bilan bir komponentda).
  final aroundZone = _reach(adj, targets, const {});
  final sources = [
    for (final id in aroundZone)
      if (!zone.contains(id) && graph.node(id)!.kind.isSource) id,
  ]..sort();

  var cut = <String>[];
  if (sources.isNotEmpty) {
    final result = _minCut(graph, adj, sources, zone);
    if (result == null) {
      final unswitched = {
        for (final n in graph.nodes)
          if (cutCosts.containsKey(n.kind) && !zone.contains(n.id)) n.id,
      };
      return blocked(BlockReason.noSwitchingDevice, _path(adj, sources, zone, unswitched)!, sources);
    }
    final chosen = debugMutateCut?.call(result) ?? result;
    // 6. Mustaqil tekshiruv: kesimni olib tashlab, BFS qayta.
    final leak = _path(adj, sources, zone, chosen);
    if (leak != null) {
      log?.call('isolation_cut_verification_failed', {'zone': targets, 'cut': chosen.toList()..sort(), 'path': leak});
      return blocked(BlockReason.verificationFailed, leak, sources);
    }
    cut = chosen.toList()..sort();
  }

  final entries = _entryPoints(adj, sources, zone, targets);
  return IsolationPlan(
    solverVersion: solverVersion,
    targetNodeIds: targets,
    graphSnapshotHash: hash,
    warnings: List.unmodifiable(warnings(sources: sources, cut: cut, noSource: sources.isEmpty)),
    cut: List.unmodifiable([
      for (final c in cut)
        CutDevice(
          nodeId: c,
          kind: graph.node(c)!.kind,
          cost: cutCosts[graph.node(c)!.kind]!,
          label: graph.node(c)!.label,
        ),
    ]),
    cost: cut.fold(0, (sum, c) => sum + cutCosts[graph.node(c)!.kind]!),
    reachableSources: List.unmodifiable(sources),
    entryPoints: List.unmodifiable(entries),
    steps: List.unmodifiable(
      buildSteps(graph: graph, zone: targets, reachableSources: sources, cut: cut, entries: entries),
    ),
  );
}

/// 3–4. Tugunlarni `v_in → v_out` ga bo'lib, Edmonds–Karp bilan minimal kesim.
/// Oqim cheksiz bo'lsa — null. Teng narxli kesimlardan zonaga eng yaqini olinadi.
Set<String>? _minCut(Graph graph, Map<String, List<String>> adj, List<String> sources, Set<String> zone) {
  final ids = adj.keys.toList();
  final index = {for (var i = 0; i < ids.length; i++) ids[i]: i};
  int costOf(String id) => zone.contains(id) ? -1 : (cutCosts[graph.node(id)!.kind] ?? -1);
  final finiteSum = ids.fold(0, (sum, id) => sum + (costOf(id) < 0 ? 0 : costOf(id)));
  final inf = finiteSum + 1;

  final net = FlowNetwork(2 * ids.length + 2);
  final superSource = 2 * ids.length;
  final superSink = superSource + 1;
  for (var i = 0; i < ids.length; i++) {
    final c = costOf(ids[i]);
    net.addArc(2 * i, 2 * i + 1, c < 0 ? inf : c);
    for (final nb in adj[ids[i]]!) {
      net.addArc(2 * i + 1, 2 * index[nb]!, inf);
    }
  }
  for (final s in sources) {
    net.addArc(superSource, 2 * index[s]!, inf);
  }
  for (final z in zone.toList()..sort()) {
    net.addArc(2 * index[z]!, superSink, inf);
  }

  final flow = net.maxFlow(superSource, superSink, limit: inf);
  if (flow >= inf) return null;
  final sinkSide = net.canReach(superSink);
  return {
    for (var i = 0; i < ids.length; i++)
      if (!sinkSide.contains(2 * i) && sinkSide.contains(2 * i + 1)) ids[i],
  };
}

Map<String, List<String>> _sortedAdjacency(Graph graph) {
  final ids = [for (final n in graph.nodes) n.id]..sort();
  return {for (final id in ids) id: graph.neighbors(id).toList()..sort()};
}

/// `start` dan `blocked` ga kirmasdan yetib boriladigan tugunlar.
Set<String> _reach(Map<String, List<String>> adj, List<String> start, Set<String> blocked) {
  final seen = <String>{...start};
  final queue = Queue<String>.of(start);
  while (queue.isNotEmpty) {
    for (final nb in adj[queue.removeFirst()]!) {
      if (!blocked.contains(nb) && seen.add(nb)) queue.add(nb);
    }
  }
  return seen;
}

/// Manbalardan zonaga `blocked` tugunlardan o'tmaydigan eng qisqa yo'l (bo'lmasa — null).
List<String>? _path(Map<String, List<String>> adj, List<String> sources, Set<String> zone, Set<String> blocked) {
  final parent = <String, String?>{for (final s in sources) s: null};
  final queue = Queue<String>.of(sources);
  while (queue.isNotEmpty) {
    final id = queue.removeFirst();
    if (zone.contains(id)) {
      final path = <String>[];
      for (String? v = id; v != null; v = parent[v]) {
        path.add(v);
      }
      return path.reversed.toList();
    }
    for (final nb in adj[id]!) {
      if (!blocked.contains(nb) && !parent.containsKey(nb)) {
        parent[nb] = id;
        queue.add(nb);
      }
    }
  }
  return null;
}

/// Kirish nuqtalari: zonaga qo'shni, manbadan zonaga kirmasdan yetib boriladigan tugunlar.
/// Manba topilmasa — har bir zona tugunining o'zi (tekshirish baribir majburiy).
List<EntryPoint> _entryPoints(
  Map<String, List<String>> adj,
  List<String> sources,
  Set<String> zone,
  List<String> targets,
) {
  if (sources.isEmpty) return [for (final z in targets) EntryPoint(z, null)];
  final live = _reach(adj, sources, zone);
  return [
    for (final z in targets)
      for (final nb in adj[z]!)
        if (!zone.contains(nb) && live.contains(nb)) EntryPoint(z, nb),
  ];
}
