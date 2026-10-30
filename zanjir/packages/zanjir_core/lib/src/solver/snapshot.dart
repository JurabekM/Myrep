import '../crypto/canonical_json.dart';
import '../crypto/sha256.dart';
import '../graph/graph.dart';
import '../model/enums.dart';
import 'plan.dart';

/// Kanonik graf: tugunlar va qirralar ID bo'yicha saralangan, qirra uchlari tartiblangan.
/// Apparat holati (`state`) kirmaydi — solver uni hisobga olmaydi, rejani bajarish uni o'zgartiradi.
Map<String, Object?> canonicalGraph(Graph graph, {EarthingSystem? earthingSystem}) {
  final nodes = graph.nodes.toList()..sort((a, b) => a.id.compareTo(b.id));
  final edges = graph.edges.toList()..sort((a, b) => a.id.compareTo(b.id));
  return {
    'schema': 'zanjir.graph/1',
    'earthing_system': earthingSystem?.code,
    'nodes': [
      for (final n in nodes)
        {
          'id': n.id,
          'kind': n.kind.code,
          'label': n.label,
          'attrs': n.attrs,
          'verified': n.verified,
          'panel_id': n.panelId,
        },
    ],
    'edges': [
      for (final e in edges)
        {
          'id': e.id,
          'a': e.aNodeId.compareTo(e.bNodeId) <= 0 ? e.aNodeId : e.bNodeId,
          'b': e.aNodeId.compareTo(e.bNodeId) <= 0 ? e.bNodeId : e.aNodeId,
          'conductors': e.conductors,
        },
    ],
  };
}

String graphSnapshotHash(Graph graph, {EarthingSystem? earthingSystem}) =>
    sha256Hex(canonicalJsonBytes(canonicalGraph(graph, earthingSystem: earthingSystem)));

/// Reja tuzilgandan keyin graf o'zgarganmi (→ STALE).
bool isPlanStale(IsolationResult plan, Graph graph, {EarthingSystem? earthingSystem}) =>
    plan.graphSnapshotHash != graphSnapshotHash(graph, earthingSystem: earthingSystem);
