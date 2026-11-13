import 'package:test/test.dart';
import 'package:zanjir_core/zanjir_core.dart';

/// Reja bajarilishi (9-faza, ADR-0013): qadamlar ketma-ket, har biri aniq tasdiq bilan; kuchlanish yo'qligini
/// tekshirish — ikki alohida tasdiq (ko'rsatkich oldin sinalgan va kuchlanish yo'q); avtomatik belgilanmaydi.
void main() {
  const steps = [
    PlanStep(order: 1, kind: StepKind.openDevice, nodeIds: ['qf1'], params: {'action': 'OPEN'}),
    PlanStep(order: 2, kind: StepKind.lockAndTag, nodeIds: ['qf1']),
    PlanStep(
      order: 3,
      kind: StepKind.verifyNoVoltage,
      nodeIds: ['w1', 'qf1'],
      params: {'zone_node_id': 'w1', 'outside_node_id': 'qf1', 'pretest_on_known_live': true},
    ),
    PlanStep(order: 4, kind: StepKind.applyEarthing, nodeIds: ['w1', 'qf1']),
    PlanStep(order: 5, kind: StepKind.fenceAndSign, nodeIds: ['w1']),
  ];
  const ok = StepConfirmation(done: true);
  const verified = StepConfirmation(done: true, indicatorTestedOnLive: true, noVoltageConfirmed: true);

  group('JSON', () {
    test('qadam va ogohlantirish toJson → fromJson aynan tiklanadi', () {
      for (final s in steps) {
        final back = PlanStep.fromJson(s.toJson());
        expect(back.toJson(), s.toJson());
        expect(back.mandatory, isTrue);
      }
      const w = PlanWarning(WarningKind.cableDischarge, ['w1'], {'length_m': 22});
      expect(PlanWarning.fromJson(w.toJson()).toJson(), w.toJson());
    });

    test('noto\'g\'ri yoki noma\'lum qiymat — FormatException', () {
      expect(() => PlanStep.fromJson({'order': 1, 'kind': 'SKIP_ALL', 'node_ids': <String>[]}), throwsFormatException);
      expect(
        () => PlanStep.fromJson({'order': '1', 'kind': 'LOCK_AND_TAG', 'node_ids': <String>[]}),
        throwsFormatException,
      );
      expect(() => PlanStep.fromJson({'order': 1, 'kind': 'LOCK_AND_TAG'}), throwsFormatException);
      expect(() => PlanWarning.fromJson({'kind': 'X', 'node_ids': <String>[]}), throwsFormatException);
      // `mandatory: false` JSON'da bo'lsa ham hisobga olinmaydi — barcha qadamlar majburiy.
      expect(PlanStep.fromJson({...steps[2].toJson(), 'mandatory': false}).mandatory, isTrue);
      expect(StepKind.parse('VERIFY_NO_VOLTAGE'), StepKind.verifyNoVoltage);
      expect(WarningKind.parse('PEN_CONDUCTOR'), WarningKind.penConductor);
    });
  });

  group('checkStepCompletion', () {
    test('faqat navbatdagi qadam; bajarilgani qayta belgilanmaydi', () {
      expect(nextStepOrder(steps, {}), 1);
      expect(checkStepCompletion(steps, {}, 1, ok), isNull);
      expect(checkStepCompletion(steps, {}, 2, ok), 'out_of_order');
      expect(checkStepCompletion(steps, {1}, 1, ok), 'already_done');
      expect(checkStepCompletion(steps, {1}, 9, ok), 'unknown_step');
      expect(nextStepOrder(steps, {1, 2}), 3);
    });

    test('har bir qadam aniq tasdiq talab qiladi (standart — tasdiqlanmagan)', () {
      expect(const StepConfirmation().done, isFalse);
      expect(checkStepCompletion(steps, {}, 1, const StepConfirmation()), 'confirmation_required');
    });

    test('kuchlanish yo\'qligini tekshirish: ikkala tasdiq ham shart', () {
      const done = {1, 2};
      expect(checkStepCompletion(steps, done, 3, ok), 'indicator_pretest_required');
      expect(
        checkStepCompletion(steps, done, 3, const StepConfirmation(done: true, indicatorTestedOnLive: true)),
        'no_voltage_confirmation_required',
      );
      expect(
        checkStepCompletion(steps, done, 3, const StepConfirmation(done: true, noVoltageConfirmed: true)),
        'indicator_pretest_required',
      );
      expect(
        checkStepCompletion(
          steps,
          done,
          3,
          const StepConfirmation(indicatorTestedOnLive: true, noVoltageConfirmed: true),
        ),
        'confirmation_required',
      );
      expect(checkStepCompletion(steps, done, 3, verified), isNull);
    });

    test('kuchlanish tekshirilmaguncha yerga ulash va keyingilar mumkin emas', () {
      expect(checkStepCompletion(steps, {1, 2}, 4, ok), 'out_of_order');
      expect(checkStepCompletion(steps, {1, 2, 3}, 4, ok), isNull);
    });

    test('hammasi bajarilgandagina reja tugaydi', () {
      expect(allStepsDone(steps, {1, 2, 3, 4}), isFalse);
      expect(allStepsDone(steps, {1, 2, 3, 4, 5}), isTrue);
      expect(nextStepOrder(steps, {1, 2, 3, 4, 5}), isNull);
      expect(allStepsDone(const [], {}), isFalse, reason: 'qadamsiz reja bajarilgan hisoblanmaydi');
    });

    test('tasdiq JSON (audit payload)', () {
      expect(verified.toJson(), {'done': true, 'indicator_tested_on_live': true, 'no_voltage_confirmed': true});
      expect(ok.toJson(), {'done': true, 'indicator_tested_on_live': false, 'no_voltage_confirmed': false});
    });
  });
}
