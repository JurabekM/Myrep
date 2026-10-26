import 'dart:collection';

import '../model/enums.dart';
import '../model/node.dart';
import 'graph.dart';

/// Tugundan manba tomondagi eng yaqin himoya apparatlari.
/// Konservativ faraz: apparatlarning `state` holati hisobga olinmaydi.
class UpstreamProtection {
  const UpstreamProtection({required this.devices, required this.unprotectedPathToSource});

  /// Manbaga olib boradigan har bir yo'ldagi birinchi himoya apparati.
  final List<Node> devices;

  /// Himoya apparatisiz manbaga yetib boriladigan yo'l bor.
  final bool unprotectedPathToSource;
}

UpstreamProtection findUpstreamProtection(Graph g, String startId, Set<NodeKind> protective) {
  final start = g.node(startId) ?? (throw ArgumentError.value(startId, 'startId', 'Grafda yo\'q'));
  if (protective.contains(start.kind)) {
    final up = _sourceReachable(g, start.id, const {});
    return UpstreamProtection(devices: up ? [start] : const [], unprotectedPathToSource: false);
  }

  // Himoya apparatlarigacha bo'lgan hudud va uning chegarasidagi apparatlar.
  final region = <String>{start.id};
  final frontier = <String>{};
  final queue = Queue<String>()..add(start.id);
  var unprotected = false;
  while (queue.isNotEmpty) {
    final id = queue.removeFirst();
    if (g.node(id)!.kind.isSource) unprotected = true;
    for (final nb in g.neighbors(id)) {
      if (region.contains(nb)) continue;
      if (protective.contains(g.node(nb)!.kind)) {
        frontier.add(nb);
      } else {
        region.add(nb);
        queue.add(nb);
      }
    }
  }
  // Hududga qaytmasdan manbaga yetadigan apparat — yuqorida turibdi.
  final devices = [
    for (final d in frontier)
      if (_sourceReachable(g, d, region)) g.node(d)!,
  ];
  return UpstreamProtection(devices: devices, unprotectedPathToSource: unprotected);
}

/// `blockedKinds` turidagi tugunlardan o'tmasdan manbaga yetib bo'ladimi.
/// Boshlang'ich tugunning o'zi to'siq bo'lsa — yo'q.
bool sourceReachableAvoiding(Graph g, String startId, Set<NodeKind> blockedKinds) {
  final start = g.node(startId) ?? (throw ArgumentError.value(startId, 'startId', 'Grafda yo\'q'));
  if (blockedKinds.contains(start.kind)) return false;
  final blocked = {
    for (final n in g.nodes)
      if (blockedKinds.contains(n.kind)) n.id,
  };
  return _sourceReachable(g, startId, blocked);
}

/// Tugun joylashgan bog'langan komponent.
Set<String> component(Graph g, String startId) {
  final seen = <String>{startId};
  final queue = Queue<String>()..add(startId);
  while (queue.isNotEmpty) {
    for (final nb in g.neighbors(queue.removeFirst())) {
      if (seen.add(nb)) queue.add(nb);
    }
  }
  return seen;
}

bool _sourceReachable(Graph g, String startId, Set<String> blocked) {
  final seen = <String>{startId};
  final queue = Queue<String>()..add(startId);
  while (queue.isNotEmpty) {
    final id = queue.removeFirst();
    if (g.node(id)!.kind.isSource) return true;
    for (final nb in g.neighbors(id)) {
      if (!blocked.contains(nb) && seen.add(nb)) queue.add(nb);
    }
  }
  return false;
}
