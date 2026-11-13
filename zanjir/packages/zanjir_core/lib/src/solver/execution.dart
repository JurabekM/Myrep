import 'plan.dart';

/// Bitta qadamning bajarilganini tasdiqlash. Barcha maydonlar standart holatda `false` — UI hech narsani oldindan
/// belgilamaydi (CLAUDE.md, 2-qoida). Kuchlanish yo'qligini tekshirishda ikkala qo'shimcha tasdiq ham majburiy:
/// ko'rsatkich oldin kuchlanish borligi ma'lum joyda sinalgan va tekshirilgan joyda kuchlanish yo'q (prompt 5.3).
class StepConfirmation {
  const StepConfirmation({this.done = false, this.indicatorTestedOnLive = false, this.noVoltageConfirmed = false});
  final bool done;
  final bool indicatorTestedOnLive;
  final bool noVoltageConfirmed;

  Map<String, Object?> toJson() => {
    'done': done,
    'indicator_tested_on_live': indicatorTestedOnLive,
    'no_voltage_confirmed': noVoltageConfirmed,
  };
}

/// Navbatdagi (eng kichik bajarilmagan) qadam tartibi; hammasi bajarilgan bo'lsa `null`.
int? nextStepOrder(List<PlanStep> steps, Set<int> done) {
  int? next;
  for (final s in steps) {
    if (!done.contains(s.order) && (next == null || s.order < next)) next = s.order;
  }
  return next;
}

/// Qadamni bajarilgan deb belgilash mumkinmi: `null` — mumkin, aks holda sabab kodi
/// (`unknown_step`, `already_done`, `out_of_order`, `confirmation_required`, `indicator_pretest_required`,
/// `no_voltage_confirmation_required`). Qadamlar faqat ketma-ket — o'tkazib yuborib bo'lmaydi.
String? checkStepCompletion(List<PlanStep> steps, Set<int> done, int order, StepConfirmation c) {
  final step = steps.where((s) => s.order == order).firstOrNull;
  if (step == null) return 'unknown_step';
  if (done.contains(order)) return 'already_done';
  if (nextStepOrder(steps, done) != order) return 'out_of_order';
  if (!c.done) return 'confirmation_required';
  if (step.kind == StepKind.verifyNoVoltage) {
    if (!c.indicatorTestedOnLive) return 'indicator_pretest_required';
    if (!c.noVoltageConfirmed) return 'no_voltage_confirmation_required';
  }
  return null;
}

/// Barcha qadamlar bajarilganmi (qadamsiz reja — yo'q).
bool allStepsDone(List<PlanStep> steps, Set<int> done) => steps.isNotEmpty && nextStepOrder(steps, done) == null;
