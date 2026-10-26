import 'package:test/test.dart';
import 'package:zanjir_core/zanjir_core.dart';

import '../support/fixtures.dart';

String mutate(void Function(Map<String, Object?> doc) change) => mutateV0(change);

List<Map<String, Object?>> norms(Map<String, Object?> doc) => (doc['norms'] as List).cast<Map<String, Object?>>();

Map<String, Object?> normById(Map<String, Object?> doc, String id) => norms(doc).firstWhere((n) => n['id'] == id);

void main() {
  group('v0.yaml', () {
    late NormSet set;
    setUp(() => set = loadV0());

    test('asosiy maydonlar', () {
      expect(set.version, '0.1.0');
      expect(set.marginPct, 0);
      expect(set.isReviewed, isFalse, reason: 'Claude reviewed_by ni to\'ldirmaydi');
      expect(set.norms, hasLength(21));
      expect(set.tripMultipliers.forCurve('B'), 5);
      expect(set.tripMultipliers.forCurve('C'), 10);
      expect(set.tripMultipliers.forCurve('D'), 20);
      expect(set.tripMultipliers.forCurve('K'), isNull);
      expect(set.tripMultipliers.status, NormStatus.needsVerification);
    });

    test('qoida turlari to\'g\'ri o\'qiladi', () {
      final byId = {for (final n in set.norms) n.id: n};
      expect(byId['INS-WIRING']!.rule, isA<MinRule>().having((r) => r.value, 'value', 0.5));
      expect(byId['INS-WIRING']!.testVoltageV, 1000);
      expect(byId['INS-WIRING']!.status, NormStatus.sourceSeen);
      expect(byId['BOND-CONTACT']!.rule, isA<MaxRule>().having((r) => r.value, 'value', 0.05));
      expect(byId['LOOP-TN-FINAL']!.rule, isA<MaxTimeRule>().having((r) => r.valueMs, 'ms', 400));
      final ramp = byId['RCD-RAMP']!.rule as RangeRule;
      expect((ramp.min, ramp.max, ramp.minInclusive, ramp.maxInclusive), (0.5, 1.0, false, true));
      expect(ramp.relativeTo, RangeBase.idnMa);
      final sel = byId['RCD-1X-S']!.rule as RangeRule;
      expect((sel.minInclusive, sel.maxInclusive, sel.relativeTo), (true, true, null));
      final tt = byId['EARTH-TT']!.rule as MaxProductRule;
      expect((tt.value, tt.factor), (50.0, ProductFactor.upstreamRcdIdnA));
      expect(byId['EARTH-TT']!.unit, NormUnit.v);
    });

    test('applies_to', () {
      final final220 = set.norms.firstWhere((n) => n.id == 'LOOP-TN-FINAL').appliesTo;
      expect(final220.nodeKinds, contains(NodeKind.socketGroup));
      expect(final220.earthingSystems, {EarthingSystem.tnC, EarthingSystem.tnS, EarthingSystem.tnCS});
      expect((final220.u0Min, final220.u0Max), (220, 220));
      expect(final220.attrs, {
        'circuit_role': ['final'],
      });
      final rcd = set.norms.firstWhere((n) => n.id == 'RCD-1X').appliesTo;
      expect(rcd.values, {
        'multiplier': [1.0],
      });
      expect(rcd.attrs, {
        'selective': [false],
      });
      final bond = set.norms.firstWhere((n) => n.id == 'BOND-CONTACT').appliesTo;
      expect(bond.earthingSystems, isNull);
      expect(bond.u0Min, isNull);
    });

    test('manba', () {
      final n = set.norms.firstWhere((n) => n.id == 'EARTH-NEUTRAL-380');
      expect(n.source.doc, 'ПУЭ');
      expect(n.source.clause, '1.7.101');
      expect(n.source.note, isNotNull);
    });
  });

  group('rad etish', () {
    void rejects(String why, void Function(Map<String, Object?> doc) change) {
      test(why, () {
        expect(() => NormSet.fromYaml(mutate(change)), throwsA(isA<NormFormatException>()));
      });
    }

    test('YAML emas / xarita emas', () {
      expect(() => NormSet.fromYaml('- 1\n- 2'), throwsA(isA<NormFormatException>()));
      expect(() => NormSet.fromYaml('a: [1'), throwsA(isA<NormFormatException>()));
    });

    rejects('noma\'lum yuqori maydon', (d) => d['extra'] = 1);
    rejects('schema_version boshqa', (d) => d['schema_version'] = 2);
    rejects('version semver emas', (d) => d['version'] = 'v1');
    rejects('reviewed_by yo\'q', (d) => d.remove('reviewed_by'));
    rejects('reviewed_at noto\'g\'ri sana', (d) => d['reviewed_at'] = '26.10.2026');
    rejects('margin_pct manfiy', (d) => d['margin_pct'] = -1);
    rejects('margin_pct > 50', (d) => d['margin_pct'] = 51);
    rejects('margin_pct son emas', (d) => d['margin_pct'] = 'nol');
    rejects('trip_multipliers egri chiziq yo\'q', (d) => (d['trip_multipliers'] as Map).remove('C'));
    rejects('trip_multipliers nol', (d) => (d['trip_multipliers'] as Map)['B'] = 0);
    rejects('normalar bo\'sh', (d) => d['norms'] = <Object?>[]);
    rejects('normalar ro\'yxat emas', (d) => d['norms'] = {'a': 1});
    rejects('takrorlangan ID', (d) => norms(d).add(Map.of(norms(d).first)));
    rejects('ID formati', (d) => norms(d).first['id'] = 'ins wiring');
    rejects('noma\'lum norma maydoni', (d) => norms(d).first['magic'] = 1);
    rejects('noma\'lum measurement_type', (d) => norms(d).first['measurement_type'] = 'VOLTAGE');
    rejects('noma\'lum node_kind', (d) => (norms(d).first['applies_to'] as Map)['node_kinds'] = ['TOASTER']);
    rejects('node_kinds bo\'sh', (d) => (norms(d).first['applies_to'] as Map)['node_kinds'] = <Object?>[]);
    rejects('noma\'lum earthing_system', (d) => (norms(d).first['applies_to'] as Map)['earthing_systems'] = ['TN']);
    rejects('u0 min > max', (d) => (norms(d).first['applies_to'] as Map)['u0_volts'] = {'min': 300, 'max': 200});
    rejects(
      'attrs qiymati ro\'yxat emas',
      (d) => (norms(d).first['applies_to'] as Map)['attrs'] = {'circuit_class': 'wiring'},
    );
    rejects(
      'attrs ro\'yxati bo\'sh',
      (d) => (norms(d).first['applies_to'] as Map)['attrs'] = {'circuit_class': <Object?>[]},
    );
    rejects(
      'values elementi xarita',
      (d) => (norms(d).first['applies_to'] as Map)['values'] = {
        'x': [
          {'a': 1},
        ],
      },
    );
    rejects('noma\'lum qoida turi', (d) => norms(d).first['rule'] = {'type': 'avg', 'value': 1});
    rejects('min qoidada value yo\'q', (d) => norms(d).first['rule'] = {'type': 'min'});
    rejects('manfiy chegara', (d) => norms(d).first['rule'] = {'type': 'min', 'value': -1});
    rejects('range min > max', (d) => normById(d, 'RCD-1X-S')['rule'] = {'type': 'range', 'min': 500, 'max': 130});
    rejects(
      'range noma\'lum relative_to',
      (d) => normById(d, 'RCD-RAMP')['rule'] = {'type': 'range', 'min': 0.5, 'max': 1, 'relative_to': 'in_a'},
    );
    rejects('max_product factor yo\'q', (d) => normById(d, 'EARTH-TT')['rule'] = {'type': 'max_product', 'value': 50});
    rejects(
      'max_product noma\'lum factor',
      (d) => normById(d, 'EARTH-TT')['rule'] = {'type': 'max_product', 'value': 50, 'factor': 'x'},
    );
    rejects('izolyatsiyada test_voltage_v yo\'q', (d) => norms(d).first.remove('test_voltage_v'));
    rejects('noma\'lum birlik', (d) => norms(d).first['unit'] = 'kOhm');
    rejects('noma\'lum status', (d) => norms(d).first['status'] = 'verified');
    rejects('manba bandi bo\'sh', (d) => norms(d).first['source'] = {'doc': 'ПУЭ', 'clause': ''});
    rejects('title bo\'sh', (d) => norms(d).first['title'] = '');
  });

  test('to\'liq tekshirilgan to\'plam isReviewed = true', () {
    final yaml = mutate((d) {
      d['reviewed_by'] = 'Muhandis, guvohnoma 000';
      d['reviewed_at'] = '2026-01-01';
    });
    expect(NormSet.fromYaml(yaml).isReviewed, isTrue);
  });

  test('bo\'sh joydan iborat reviewed_by — tekshirilmagan', () {
    final yaml = mutate((d) {
      d['reviewed_by'] = '   ';
      d['reviewed_at'] = '2026-01-01';
    });
    expect(NormSet.fromYaml(yaml).isReviewed, isFalse);
  });
}
