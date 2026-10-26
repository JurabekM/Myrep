import 'package:test/test.dart';
import 'package:zanjir_core/zanjir_core.dart';

import '../support/fixtures.dart';

/// Golden holatlarda qamrab olinmagan chekka holatlar va kontrakt.
void main() {
  final set = loadV0();
  final graph = graphOf(
    [
      node('GRID', NodeKind.srcGrid),
      node('QF1', NodeKind.breaker, attrs: {'in_a': 16, 'curve': 'C'}),
      node('CAB1', NodeKind.cable, attrs: {'circuit_role': 'final', 'circuit_class': 'wiring'}),
      node('PE1', NodeKind.peBar),
    ],
    [
      ['GRID', 'QF1'],
      ['QF1', 'CAB1'],
    ],
  );
  const site = Site(id: 'site', name: 'S', earthingSystem: EarthingSystem.tnCS, u0Volts: 220);
  const session = MeasurementSession(
    id: 'sess',
    siteId: 'site',
    kind: SessionKind.davriy,
    engineerId: 'eng',
    ambientTempC: 20,
  );

  Measurement m(String nodeId, MeasurementType type, Map<String, Object?> values) => Measurement(
    id: 'm',
    sessionId: 'sess',
    nodeId: nodeId,
    type: type,
    instrumentId: 'ins',
    values: values,
    enteredVia: EnteredVia.manual,
  );

  EvalResult run(
    Measurement meas, {
    NormSet? normSet,
    Site s = site,
    MeasurementSession sess = session,
    EvalSettings settings = const EvalSettings(),
  }) => evaluate(
    measurement: meas,
    node: graph.node(meas.nodeId)!,
    site: s,
    session: sess,
    normSet: normSet ?? set,
    graph: graph,
    settings: settings,
  );

  final loop = m('CAB1', MeasurementType.loopImpedance, {'pair': 'L1-PE', 'zs_ohm': 0.84});

  group('kontrakt', () {
    test('tugun o\'lchovga mos kelmasa — ArgumentError', () {
      expect(
        () => evaluate(
          measurement: loop,
          node: graph.node('QF1')!,
          site: site,
          session: session,
          normSet: set,
          graph: graph,
        ),
        throwsArgumentError,
      );
    });

    test('tugun boshqa obyektda — ArgumentError', () {
      expect(
        () => run(
          loop,
          s: const Site(id: 'other', name: 'X'),
        ),
        throwsArgumentError,
      );
    });

    test('sessiya boshqa obyektda — ArgumentError', () {
      expect(
        () => run(
          loop,
          sess: const MeasurementSession(id: 's', siteId: 'other', kind: SessionKind.davriy, engineerId: 'e'),
        ),
        throwsArgumentError,
      );
    });

    test('sessiya ID mos emas — ArgumentError', () {
      expect(
        () => run(
          loop,
          sess: const MeasurementSession(id: 'x', siteId: 'site', kind: SessionKind.davriy, engineerId: 'e'),
        ),
        throwsArgumentError,
      );
    });

    test('tugun grafda yo\'q — ArgumentError', () {
      expect(
        () => evaluate(
          measurement: m('ZZ', MeasurementType.loopImpedance, const {}),
          node: node('ZZ', NodeKind.cable),
          site: site,
          session: session,
          normSet: set,
          graph: graph,
        ),
        throwsArgumentError,
      );
    });

    test('k_corr (0; 1] oralig\'idan tashqarida — ArgumentError', () {
      expect(() => run(loop, settings: const EvalSettings(kCorr: 0)), throwsArgumentError);
      expect(() => run(loop, settings: const EvalSettings(kCorr: 1.2)), throwsArgumentError);
      expect(() => run(loop, settings: const EvalSettings(kCorr: double.nan)), throwsArgumentError);
    });
  });

  group('eval_detail', () {
    test('formula, chegara, kirish qiymatlari, norma va versiya yoziladi', () {
      final r = run(loop);
      expect(r.verdict, Verdict.pass);
      expect(r.normId, 'LOOP-TN-FINAL');
      final d = r.detail;
      expect(d['norm_set_version'], '0.1.0');
      expect(d['margin_pct'], 0);
      expect(d['k_corr'], 1.0);
      expect(d['measurement_type'], 'LOOP_IMPEDANCE');
      expect(d['node_kind'], 'CABLE');
      expect(d['site'], {'earthing_system': 'TN-C-S', 'u0_volts': 220.0});
      expect(d['inputs'], {'pair': 'L1-PE', 'zs_ohm': 0.84});
      expect(d['matched_norms'], ['LOOP-TN-FINAL']);
      expect(d['strictest_norm_id'], 'LOOP-TN-FINAL');
      final check = (d['checks'] as List).single as Map<String, Object?>;
      expect(check['formula'], 'Zs ≤ k_corr · U0 / (k · In) · (1 − margin)');
      expect(check['limit'], closeTo(1.375, 1e-12));
      expect(check['value'], 0.84);
      expect(check['devices'], [
        {
          'id': 'QF1',
          'kind': 'BREAKER',
          'in_a': 16,
          'curve': 'C',
          'trip_multiplier': 10.0,
          'ia_a': 160.0,
          'zs_max_ohm': 1.375,
        },
      ]);
    });

    test('deterministik: bir xil kirish — bir xil natija', () {
      final a = run(loop);
      final b = run(loop);
      expect(a.verdict, b.verdict);
      expect(a.detail.toString(), b.detail.toString());
    });

    test('aniqlanmagan normalar va yetishmayotgan kalitlar ro\'yxati', () {
      final r = run(
        loop,
        s: const Site(id: 'site', name: 'S', earthingSystem: EarthingSystem.tnCS),
      );
      expect(r.verdict, Verdict.needsReview);
      expect(r.normId, isNull);
      final unknown = r.detail['unknown_norms'] as Map<String, Object?>;
      expect(unknown['LOOP-TN-FINAL'], ['site.u0_volts']);
    });

    test('kirish qiymatlari nusxa — keyingi o\'zgarish natijaga ta\'sir qilmaydi', () {
      final values = <String, Object?>{'pair': 'L1-PE', 'zs_ohm': 0.84};
      final r = run(m('CAB1', MeasurementType.loopImpedance, values));
      values['zs_ohm'] = 99.0;
      expect((r.detail['inputs'] as Map)['zs_ohm'], 0.84);
      expect(() => (r.detail['site'] as Map)['u0_volts'] = 1, throwsUnsupportedError);
      expect(() => (r.detail['checks'] as List).clear(), throwsUnsupportedError);
    });
  });

  group('maxsus norma to\'plamlari', () {
    test('sirtmoq: U0 sharti yo\'q norma va U0 kiritilmagan obyekt → NEEDS_REVIEW', () {
      final custom = v0With((d) {
        for (final n in (d['norms'] as List).cast<Map<String, Object?>>()) {
          (n['applies_to'] as Map<String, Object?>).remove('u0_volts');
        }
      });
      final r = run(
        loop,
        normSet: custom,
        s: const Site(id: 'site', name: 'S', earthingSystem: EarthingSystem.tnCS),
      );
      expect(r.verdict, Verdict.needsReview);
      expect(r.detail['reason'], 'value_missing');
      expect((r.detail['checks'] as List).single, containsPair('field', 'site.u0_volts'));
    });

    test('sirtmoq: bir nechta norma mos kelsa — eng qisqa vaqt talab qilingani', () {
      final custom = v0With((d) {
        for (final n in (d['norms'] as List).cast<Map<String, Object?>>()) {
          (n['applies_to'] as Map<String, Object?>).remove('u0_volts');
        }
      });
      final r = run(loop, normSet: custom);
      expect(r.verdict, Verdict.pass);
      expect(r.detail['matched_norms'], [
        'LOOP-TN-FINAL',
        'LOOP-TN-OTHER-U0-127',
        'LOOP-TN-OTHER-U0-380',
        'LOOP-TN-OTHER-U0-GT380',
      ]);
      expect(r.normId, 'LOOP-TN-OTHER-U0-GT380');
    });

    test('sirtmoq: vaqt qoidasi bo\'lmagan norma qat\'iyroq hisoblanmaydi', () {
      final custom = v0With((d) {
        final norms = (d['norms'] as List).cast<Map<String, Object?>>();
        final fin = norms.firstWhere((n) => n['id'] == 'LOOP-TN-FINAL');
        norms.add({
          ...fin,
          'id': 'LOOP-CUSTOM',
          'rule': {'type': 'max', 'value': 1},
          'unit': 'Ohm',
        });
      });
      final r = run(loop, normSet: custom);
      expect(r.detail['matched_norms'], ['LOOP-TN-FINAL', 'LOOP-CUSTOM']);
      expect(r.normId, 'LOOP-TN-FINAL');
    });

    test('mos kelgan bir nechta norma — eng qat\'iysi hal qiluvchi', () {
      final custom = v0With((d) {
        final norms = (d['norms'] as List).cast<Map<String, Object?>>();
        final bond = norms.firstWhere((n) => n['id'] == 'BOND-CONTACT');
        norms.add({
          ...bond,
          'id': 'BOND-STRICT',
          'rule': {'type': 'max', 'value': 0.02},
        });
      });
      final r = run(m('PE1', MeasurementType.continuityBonding, {'r_ohm': 0.03}), normSet: custom);
      expect(r.verdict, Verdict.fail);
      expect(r.normId, 'BOND-STRICT');
      expect(r.detail['matched_norms'], ['BOND-CONTACT', 'BOND-STRICT']);
      final ok = run(m('PE1', MeasurementType.continuityBonding, {'r_ohm': 0.01}), normSet: custom);
      expect(ok.verdict, Verdict.pass);
      expect(ok.normId, 'BOND-STRICT', reason: 'eng kichik zaxira — eng qat\'iy');
      expect(ok.detail['strictest_norm_id'], 'BOND-STRICT');
    });

    test('bog\'lanish: min qoidali qo\'shimcha norma ham tekshiriladi', () {
      final custom = v0With((d) {
        final norms = (d['norms'] as List).cast<Map<String, Object?>>();
        final bond = norms.firstWhere((n) => n['id'] == 'BOND-CONTACT');
        norms.add({
          ...bond,
          'id': 'BOND-MIN',
          'rule': {'type': 'min', 'value': 0.001},
        });
      });
      final r = run(m('PE1', MeasurementType.continuityBonding, {'r_ohm': 0.03}), normSet: custom);
      expect(r.verdict, Verdict.pass);
    });
  });
}
