import 'dart:io';

import 'package:test/test.dart';
import 'package:yaml/yaml.dart';
import 'package:zanjir_core/zanjir_core.dart';

import '../support/fixtures.dart';

/// Golden holatlar: `test/golden/*.cases.yaml` (format — insulation.cases.yaml boshida).
void main() {
  final graphs = toPlain(loadYaml(File('test/golden/graphs.yaml').readAsStringSync())) as Map<String, Object?>;
  final caseFiles =
      Directory('test/golden').listSync().whereType<File>().where((f) => f.path.endsWith('.cases.yaml')).toList()
        ..sort((a, b) => a.path.compareTo(b.path));
  final baseSet = loadV0();
  final normCoverage = <String, int>{};

  for (final file in caseFiles) {
    final cases = (toPlain(loadYaml(file.readAsStringSync())) as List).cast<Map<String, Object?>>();
    group(file.uri.pathSegments.last, () {
      for (final c in cases) {
        final expectedNorm = c['norm'] as String?;
        final expectedChecks = (c['checks'] as Map<String, Object?>?) ?? const {};
        for (final id in {?expectedNorm, ...expectedChecks.keys}) {
          normCoverage[id] = (normCoverage[id] ?? 0) + 1;
        }

        test(c['name'], () {
          final r = _run(c, graphs, baseSet);
          expect(r.verdict.code, c['expect'], reason: 'detail: ${r.detail}');
          if (expectedNorm != null) expect(r.normId, expectedNorm, reason: 'detail: ${r.detail}');
          if (c['reason'] != null) expect(r.detail['reason'], c['reason'], reason: 'detail: ${r.detail}');
          final checks = (r.detail['checks'] as List?)?.cast<Map<String, Object?>>() ?? const [];
          for (final e in expectedChecks.entries) {
            final check = checks.where((ch) => ch['norm_id'] == e.key);
            expect(check, isNotEmpty, reason: '${e.key} tekshirilmagan: ${r.detail}');
            expect(check.first['verdict'], e.value, reason: '${e.key}: ${r.detail}');
          }

          // Umumiy invariantlar.
          expect(r.normSetVersion, baseSet.version);
          expect(r.detail['norm_set_version'], baseSet.version);
          expect(r.detail['inputs'], c['values']);
          if (r.verdict == Verdict.pass) {
            expect(r.normId, isNotNull, reason: 'PASS hal qiluvchi normasiz bo\'lmaydi');
            expect(r.detail['reason'], isNull);
          } else {
            expect(r.detail['reason'], isA<String>());
          }
        });
      }
    });
  }

  test('har bir normaga kamida 3 ta golden holat', () {
    for (final n in baseSet.norms) {
      expect(normCoverage[n.id] ?? 0, greaterThanOrEqualTo(3), reason: n.id);
    }
  });
}

EvalResult _run(Map<String, Object?> c, Map<String, Object?> graphs, NormSet baseSet) {
  final g = graphs[c['graph'] ?? 'tn'] as Map<String, Object?>;
  final siteSpec = {...g['site'] as Map<String, Object?>, ...?(c['site'] as Map<String, Object?>?)};
  final site = Site(
    id: 'site',
    name: 'Golden',
    earthingSystem: switch (siteSpec['earthing_system']) {
      final String s => EarthingSystem.parse(s),
      _ => null,
    },
    u0Volts: (siteSpec['u0_volts'] as num?)?.toDouble(),
  );

  final attrOverrides = (c['attrs'] as Map<String, Object?>?) ?? const {};
  final nodes = <Node>[
    for (final e in (g['nodes'] as Map<String, Object?>).entries)
      () {
        final spec = e.value as Map<String, Object?>;
        final attrs = {...?(spec['attrs'] as Map<String, Object?>?)};
        (attrOverrides[e.key] as Map<String, Object?>?)?.forEach((k, v) => v == null ? attrs.remove(k) : attrs[k] = v);
        return node(e.key, NodeKind.parse(spec['kind'] as String), attrs: attrs);
      }(),
  ];
  final removed = {for (final l in (c['remove_edges'] as List?) ?? const []) (l as List).join('|')};
  final links = [
    for (final l in (g['edges'] as List).cast<List<Object?>>())
      if (!removed.contains(l.join('|'))) l.cast<String>(),
  ];
  final graph = graphOf(nodes, links);

  final normOverrides = c['norm_set'] as Map<String, Object?>?;
  final normSet = normOverrides == null ? baseSet : v0With((d) => d.addAll(normOverrides));

  final sessionSpec = (c['session'] as Map<String, Object?>?) ?? const {'ambient_temp_c': 20};
  final session = MeasurementSession(
    id: 'sess',
    siteId: 'site',
    kind: SessionKind.davriy,
    engineerId: 'eng',
    ambientTempC: (sessionSpec['ambient_temp_c'] as num?)?.toDouble(),
  );
  final nodeId = c['node'] as String;
  final measurement = Measurement(
    id: 'm',
    sessionId: 'sess',
    nodeId: nodeId,
    type: MeasurementType.parse(c['type'] as String),
    instrumentId: 'ins',
    values: (c['values'] as Map<String, Object?>?) ?? const {},
    enteredVia: EnteredVia.manual,
  );
  final settingsSpec = (c['settings'] as Map<String, Object?>?) ?? const {};
  return evaluate(
    measurement: measurement,
    node: graph.node(nodeId)!,
    site: site,
    session: session,
    normSet: normSet,
    graph: graph,
    settings: EvalSettings(kCorr: (settingsSpec['k_corr'] as num?)?.toDouble() ?? 1.0),
  );
}
