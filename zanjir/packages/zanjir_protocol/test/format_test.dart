import 'package:test/test.dart';
import 'package:zanjir_core/zanjir_core.dart';
import 'package:zanjir_protocol/zanjir_protocol.dart';

void main() {
  test('formatDecimal', () {
    expect(formatDecimal(0.84), '0,84');
    expect(formatDecimal(16.0), '16');
    expect(formatDecimal(1.43750001), '1,4375');
    expect(formatDecimal(-2.5), '-2,5');
  });

  test('summarizeValues — har bir o\'lchov turi', () {
    expect(
      summarizeValues(MeasurementType.insulation, {
        'pairs': [
          {'pair': 'L1-N', 'mohm': 520},
          {'pair': 'L1-PE'},
        ],
      }),
      'L1-N: 520 MΩ, L1-PE: — MΩ',
    );
    expect(summarizeValues(MeasurementType.loopImpedance, {'pair': 'L1-PE', 'zs_ohm': 0.42}), 'L1-PE Zs 0,42 Ω');
    expect(
      summarizeValues(MeasurementType.rcdTrip, {'multiplier': 1, 'trip_time_ms': 24, 'trip_current_ma': 21}),
      '1·IΔn: 24 ms / 21 mA',
    );
    expect(summarizeValues(MeasurementType.rcdTrip, {}), '?·IΔn: —');
    expect(summarizeValues(MeasurementType.earthResistance, {'r_ohm': 3.2}), 'R 3,2 Ω · ψ —');
    expect(summarizeValues(MeasurementType.continuityBonding, {'r_ohm': 0.05}), 'R 0,05 Ω');
    expect(summarizeValues(MeasurementType.loopImpedance, {'not_applicable_reason': 'yo\'q'}), 'yo\'q');
  });

  test('verdictCounts — barcha kalitlar, PASS standart emas', () {
    expect(verdictCounts([]), {'total': 0, 'PASS': 0, 'FAIL': 0, 'NEEDS_REVIEW': 0, 'NOT_APPLICABLE': 0});
    expect(verdictCounts([Verdict.fail, Verdict.fail, Verdict.needsReview]), {
      'total': 3,
      'PASS': 0,
      'FAIL': 2,
      'NEEDS_REVIEW': 1,
      'NOT_APPLICABLE': 0,
    });
  });
}
