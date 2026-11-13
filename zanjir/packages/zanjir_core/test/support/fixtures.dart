import 'dart:io';

import 'package:yaml/yaml.dart';
import 'package:zanjir_core/zanjir_core.dart';

/// `norms/v0.yaml` — testlar package ildizidan ishga tushadi.
final String v0Yaml = File('../../norms/v0.yaml').readAsStringSync();

NormSet loadV0() => NormSet.fromYaml(v0Yaml);

Node node(
  String id,
  NodeKind kind, {
  Map<String, Object?> attrs = const {},
  bool verified = true,
  String siteId = 'site',
}) => Node(id: id, siteId: siteId, kind: kind, label: id, attrs: attrs, verified: verified);

/// Qirralar: `[['A', 'B'], ['B', 'C']]`.
Graph graphOf(List<Node> nodes, List<List<String>> links, {String siteId = 'site'}) {
  var i = 0;
  return Graph(nodes, [
    for (final l in links)
      Edge(id: 'e${i++}', siteId: siteId, aNodeId: l[0], bNodeId: l[1], conductors: 'L1 L2 L3 N PE'),
  ]);
}

/// YAML → oddiy Dart qiymatlari (Map/List).
Object? toPlain(Object? y) => switch (y) {
  final YamlMap m => {for (final e in m.entries) e.key as String: toPlain(e.value)},
  final YamlList l => [for (final v in l) toPlain(v)],
  _ => y,
};

/// Oddiy qiymat → JSON matni (JSON — YAML ning qism to'plami).
String toJsonText(Object? v) => switch (v) {
  null => 'null',
  final String s => '"${s.replaceAll('\\', '\\\\').replaceAll('"', '\\"')}"',
  final Map<String, Object?> m =>
    '{${m.entries.map((e) => '${toJsonText(e.key)}: ${toJsonText(e.value)}').join(', ')}}',
  final List<Object?> l => '[${l.map(toJsonText).join(', ')}]',
  _ => '$v',
};

/// v0.yaml ni o'zgartirib qayta yuklash (testlar uchun).
String mutateV0(void Function(Map<String, Object?> doc) change) {
  final doc = toPlain(loadYaml(v0Yaml)) as Map<String, Object?>;
  change(doc);
  return toJsonText(doc);
}

NormSet v0With(void Function(Map<String, Object?> doc) change) => NormSet.fromYaml(mutateV0(change));
