import 'package:test/test.dart';
import 'package:zanjir_core/src/eval/rule_check.dart';
import 'package:zanjir_core/zanjir_core.dart';

void main() {
  Check run(
    NormRule rule,
    double value, {
    double marginPct = 0,
    double? base,
    double? factor,
    String? factorMissingReason,
  }) => checkRule(
    normId: 'N',
    rule: rule,
    value: value,
    marginPct: marginPct,
    base: base,
    factor: factor,
    factorMissingReason: factorMissingReason,
  );

  group('min', () {
    test('chegarada PASS, pastda FAIL, margin qat\'iylashtiradi', () {
      expect(run(const MinRule(0.5), 0.5).verdict, Verdict.pass);
      expect(run(const MinRule(0.5), 0.4999).verdict, Verdict.fail);
      expect(run(const MinRule(0.5), 0.5, marginPct: 10).verdict, Verdict.fail);
      final c = run(const MinRule(0.5), 1.0);
      expect(c.limit, 0.5);
      expect(c.slack, closeTo(1.0, 1e-12));
      expect(c.reason, isNull);
    });
  });

  group('max / max_time_ms', () {
    test('chegarada PASS, yuqorida FAIL', () {
      expect(run(const MaxRule(4), 4).verdict, Verdict.pass);
      expect(run(const MaxRule(4), 4.01).verdict, Verdict.fail);
      expect(run(const MaxRule(4), 4.01).reason, 'out_of_limit');
      expect(run(const MaxTimeRule(300), 300).verdict, Verdict.pass);
      expect(run(const MaxTimeRule(300), 280, marginPct: 10).verdict, Verdict.fail);
    });

    test('nol chegara — slack absolyut farq', () {
      final c = run(const MaxRule(0), 0);
      expect(c.verdict, Verdict.pass);
      expect(c.slack, 0);
    });

    test('suzuvchi nuqta xatosi chegarada PASS beradi', () {
      expect(run(const MaxRule(4), 2.5 * 1.6).verdict, Verdict.pass);
      expect(run(const MaxRule(0.3), 0.1 * 3).verdict, Verdict.pass);
    });
  });

  group('range', () {
    test('inklyuziv chegaralar', () {
      const r = RangeRule(min: 130, max: 500);
      expect(run(r, 130).verdict, Verdict.pass);
      expect(run(r, 500).verdict, Verdict.pass);
      expect(run(r, 129).verdict, Verdict.fail);
      expect(run(r, 501).verdict, Verdict.fail);
    });

    test('eksklyuziv chegaralar — aynan chegara FAIL', () {
      const r = RangeRule(min: 10, max: 20, minInclusive: false, maxInclusive: false);
      expect(run(r, 10).verdict, Verdict.fail);
      expect(run(r, 20).verdict, Verdict.fail);
      expect(run(r, 15).verdict, Verdict.pass);
    });

    test('nisbiy (idn_ma) — base kerak', () {
      const r = RangeRule(min: 0.5, max: 1.0, minInclusive: false, relativeTo: RangeBase.idnMa);
      expect(run(r, 21, base: 30).verdict, Verdict.pass);
      expect(run(r, 21, base: 30).limit, {'min': 15.0, 'max': 30.0});
      final c = run(r, 21);
      expect(c.verdict, Verdict.needsReview);
      expect(c.reason, 'device_attrs_missing');
    });

    test('margin oraliqni toraytiradi', () {
      const r = RangeRule(min: 100, max: 200);
      expect(run(r, 105, marginPct: 10).verdict, Verdict.fail);
      expect(run(r, 195, marginPct: 10).verdict, Verdict.fail);
      expect(run(r, 150, marginPct: 10).verdict, Verdict.pass);
    });

    test('nol pastki chegara', () {
      final c = run(const RangeRule(min: 0, max: 10), 0);
      expect(c.verdict, Verdict.pass);
      expect(c.slack, 0);
    });
  });

  group('max_product', () {
    test('ko\'paytma bilan solishtiriladi', () {
      const r = MaxProductRule(50, ProductFactor.upstreamRcdIdnA);
      expect(run(r, 500, factor: 0.1).verdict, Verdict.pass);
      expect(run(r, 501, factor: 0.1).verdict, Verdict.fail);
      expect(run(r, 400, factor: 0.1).value, closeTo(40, 1e-9));
    });

    test('ko\'paytuvchi yo\'q → NEEDS_REVIEW', () {
      const r = MaxProductRule(50, ProductFactor.upstreamRcdIdnA);
      expect(run(r, 1).verdict, Verdict.needsReview);
      expect(run(r, 1).reason, 'factor_unavailable');
      expect(run(r, 1, factorMissingReason: 'no_upstream_rcd').reason, 'no_upstream_rcd');
    });
  });

  group('combine', () {
    test('FAIL > NEEDS_REVIEW > PASS, keyin eng kichik zaxira', () {
      const a = Check(normId: 'A', verdict: Verdict.pass, slack: 0.5);
      const b = Check(normId: 'B', verdict: Verdict.pass, slack: 0.1);
      const c = Check(normId: 'C', verdict: Verdict.needsReview, reason: 'value_missing');
      const d = Check(normId: 'D', verdict: Verdict.fail, reason: 'out_of_limit', slack: -0.2);
      const e = Check(normId: 'E', verdict: Verdict.fail, reason: 'out_of_limit', slack: -0.5);
      expect(decisive([a, b]).normId, 'B');
      expect(decisive([a, c, b]).normId, 'C');
      expect(decisive([a, d, c, e]).normId, 'E');
      expect(decisive([const Check(normId: 'X', verdict: Verdict.pass), a]).normId, 'X');
    });

    test('bo\'sh ro\'yxat — xato', () {
      expect(() => decisive(const []), throwsStateError);
    });
  });
}
