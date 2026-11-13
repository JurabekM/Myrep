import 'dart:collection';

import '../model/edge.dart';
import '../model/node.dart';

class GraphException implements Exception {
  const GraphException(this.message);
  final String message;

  @override
  String toString() => 'GraphException: $message';
}

/// Bitta obyektning o'zgarmas elektr grafi. Qirralar yo'nalishsiz.
class Graph {
  Graph(Iterable<Node> nodes, Iterable<Edge> edges) : edges = List.unmodifiable(edges) {
    String? siteId;
    for (final n in nodes) {
      siteId ??= n.siteId;
      if (n.siteId != siteId) throw GraphException('Tugun ${n.id} boshqa obyektda');
      if (_nodes.containsKey(n.id)) throw GraphException('Takrorlangan tugun: ${n.id}');
      _nodes[n.id] = n;
      _adj[n.id] = LinkedHashSet<String>();
    }
    final edgeIds = <String>{};
    for (final e in this.edges) {
      if (!edgeIds.add(e.id)) throw GraphException('Takrorlangan qirra: ${e.id}');
      if (e.siteId != siteId) throw GraphException('Qirra ${e.id} boshqa obyektda');
      final a = _adj[e.aNodeId];
      final b = _adj[e.bNodeId];
      if (a == null || b == null) throw GraphException('Qirra ${e.id}: tugun topilmadi');
      if (e.aNodeId == e.bNodeId) throw GraphException('Qirra ${e.id}: o\'z-o\'ziga ulangan');
      a.add(e.bNodeId);
      b.add(e.aNodeId);
    }
  }

  final Map<String, Node> _nodes = {};
  final Map<String, LinkedHashSet<String>> _adj = {};
  final List<Edge> edges;

  Iterable<Node> get nodes => _nodes.values;

  Node? node(String id) => _nodes[id];

  /// Qo'shni tugunlar (qirralar tartibida, takrorlanmasdan).
  List<String> neighbors(String id) {
    final adj = _adj[id];
    if (adj == null) throw ArgumentError.value(id, 'id', 'Grafda yo\'q');
    return List.unmodifiable(adj);
  }
}
