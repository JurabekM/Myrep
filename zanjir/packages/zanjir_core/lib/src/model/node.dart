import 'enums.dart';
import 'frozen.dart';

/// Graf tuguni. `attrs` — o'zgarmas nusxa (masalan, `{"in_a":16,"curve":"C"}`).
class Node {
  Node({
    required this.id,
    required this.siteId,
    required this.kind,
    required this.label,
    Map<String, Object?> attrs = const {},
    this.verified = false,
    this.state,
    this.panelId,
  }) : attrs = freezeMap(attrs);

  final String id;
  final String siteId;
  final NodeKind kind;
  final String label;
  final Map<String, Object?> attrs;

  /// Dalada tasdiqlanganmi; standart — yo'q (konservativ).
  final bool verified;
  final SwitchState? state;
  final String? panelId;
}
