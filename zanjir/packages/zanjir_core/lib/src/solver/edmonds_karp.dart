import 'dart:collection';

/// Butun sonli sig'imli yo'naltirilgan tarmoq va Edmonds–Karp maksimal oqimi.
class FlowNetwork {
  FlowNetwork(int vertices) : _adj = List.generate(vertices, (_) => <int>[]);

  final List<List<int>> _adj;
  final List<int> _to = [];
  final List<int> _cap = [];

  int get vertexCount => _adj.length;

  /// `u → v` yoy (`cap`) va teskari qoldiq yoy (0).
  void addArc(int u, int v, int cap) {
    _adj[u].add(_to.length);
    _to.add(v);
    _cap.add(cap);
    _adj[v].add(_to.length);
    _to.add(u);
    _cap.add(0);
  }

  /// Maksimal oqim; `limit` ga yetsa to'xtaydi (cheksiz oqimni aniqlash uchun).
  int maxFlow(int s, int t, {required int limit}) {
    var flow = 0;
    final parentArc = List<int>.filled(vertexCount, -1);
    while (flow < limit) {
      parentArc.fillRange(0, vertexCount, -1);
      parentArc[s] = -2;
      final queue = Queue<int>()..add(s);
      while (queue.isNotEmpty && parentArc[t] == -1) {
        final u = queue.removeFirst();
        for (final a in _adj[u]) {
          final v = _to[a];
          if (_cap[a] > 0 && parentArc[v] == -1) {
            parentArc[v] = a;
            queue.add(v);
          }
        }
      }
      if (parentArc[t] == -1) break;
      var bottleneck = limit - flow;
      for (var v = t; v != s; v = _to[parentArc[v] ^ 1]) {
        if (_cap[parentArc[v]] < bottleneck) bottleneck = _cap[parentArc[v]];
      }
      for (var v = t; v != s; v = _to[parentArc[v] ^ 1]) {
        _cap[parentArc[v]] -= bottleneck;
        _cap[parentArc[v] ^ 1] += bottleneck;
      }
      flow += bottleneck;
    }
    return flow;
  }

  /// Qoldiq tarmoqda `t` ga yetib boradigan uchlar (oqimdan keyin). Shu to'plam bo'yicha kesim —
  /// minimal kesimlar ichida `t` ga eng yaqini.
  Set<int> canReach(int t) {
    final seen = <int>{t};
    final queue = Queue<int>()..add(t);
    while (queue.isNotEmpty) {
      final v = queue.removeFirst();
      for (final a in _adj[v]) {
        // `a` — v dan chiquvchi yoy; teskari yoy `a ^ 1` (u → v) da qoldiq bo'lsa, u → t mumkin.
        final u = _to[a];
        if (_cap[a ^ 1] > 0 && seen.add(u)) queue.add(u);
      }
    }
    return seen;
  }
}
