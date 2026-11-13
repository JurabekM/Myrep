import 'dart:collection';
import 'dart:ui';

import 'package:zanjir_core/zanjir_core.dart';

/// Daraxt qatori: manbadan BFS bo'yicha (birinchi topilgan ota), `depth` — chuqurlik.
class TreeRow {
  const TreeRow(this.node, this.depth);
  final Node node;
  final int depth;
}

class SiteTree {
  const SiteTree(this.rows, this.unconnected);
  final List<TreeRow> rows;

  /// Hech qaysi manbaga ulanmagan tugunlar.
  final List<Node> unconnected;
}

SiteTree buildTree(Graph g) {
  int byLabel(Node a, Node b) => a.label.compareTo(b.label);
  final children = <String, List<Node>>{};
  final seen = <String>{};
  final roots = g.nodes.where((n) => n.kind.isSource).toList()..sort(byLabel);
  final queue = Queue<String>();
  for (final r in roots) {
    if (seen.add(r.id)) queue.add(r.id);
  }
  while (queue.isNotEmpty) {
    final id = queue.removeFirst();
    final next = [
      for (final nb in g.neighbors(id))
        if (!seen.contains(nb)) g.node(nb)!,
    ]..sort(byLabel);
    for (final n in next) {
      seen.add(n.id);
      queue.add(n.id);
    }
    children[id] = next;
  }
  final rows = <TreeRow>[];
  void walk(Node n, int depth) {
    rows.add(TreeRow(n, depth));
    for (final c in children[n.id] ?? const <Node>[]) {
      walk(c, depth + 1);
    }
  }

  for (final r in roots) {
    walk(r, 0);
  }
  final unconnected = g.nodes.where((n) => !seen.contains(n.id)).toList()..sort(byLabel);
  return SiteTree(rows, unconnected);
}

/// Graf rejimi: qatlamlar — manbadan BFS chuqurligi; ulanmaganlar oxirgi qatorda.
class GraphLayout {
  GraphLayout(this.positions, this.size);
  final Map<String, Rect> positions;
  final Size size;

  static const nodeSize = Size(120, 48);
  static const gapX = 24.0;
  static const gapY = 56.0;

  factory GraphLayout.of(Graph g) {
    final tree = buildTree(g);
    final layers = <int, List<Node>>{};
    for (final r in tree.rows) {
      layers.putIfAbsent(r.depth, () => []).add(r.node);
    }
    if (tree.unconnected.isNotEmpty) layers[layers.length] = tree.unconnected;
    final positions = <String, Rect>{};
    var maxWidth = 0.0;
    for (final e in layers.entries) {
      for (var i = 0; i < e.value.length; i++) {
        final x = gapX + i * (nodeSize.width + gapX);
        final y = gapY / 2 + e.key * (nodeSize.height + gapY);
        positions[e.value[i].id] = Rect.fromLTWH(x, y, nodeSize.width, nodeSize.height);
        if (x + nodeSize.width + gapX > maxWidth) maxWidth = x + nodeSize.width + gapX;
      }
    }
    return GraphLayout(positions, Size(maxWidth, layers.length * (nodeSize.height + gapY) + gapY / 2));
  }

  String? hit(Offset p) {
    for (final e in positions.entries) {
      if (e.value.contains(p)) return e.key;
    }
    return null;
  }
}
