/// Graf qirrasi (yo'nalishsiz). `conductors` — masalan, "L1 L2 L3 N PE".
class Edge {
  const Edge({
    required this.id,
    required this.siteId,
    required this.aNodeId,
    required this.bNodeId,
    required this.conductors,
  });

  final String id;
  final String siteId;
  final String aNodeId;
  final String bNodeId;
  final String conductors;
}
