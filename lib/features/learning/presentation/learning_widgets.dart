import 'package:baraka_daftari/app/l10n/l10n.dart';
import 'package:baraka_daftari/app/widgets/labels.dart';
import 'package:baraka_daftari/app/widgets/money_input.dart';
import 'package:baraka_daftari/core/domain/enums.dart';
import 'package:baraka_daftari/core/errors/data_exceptions.dart';
import 'package:baraka_daftari/core/logging/app_log.dart';
import 'package:baraka_daftari/core/money/money.dart';
import 'package:baraka_daftari/features/content/data/content_providers.dart';
import 'package:baraka_daftari/features/content/domain/content.dart';
import 'package:baraka_daftari/features/learning/data/learning_providers.dart';
import 'package:baraka_daftari/features/learning/domain/learning.dart';
import 'package:baraka_daftari/features/learning/domain/learning_math.dart';
import 'package:baraka_daftari/features/learning/domain/learning_service.dart';
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

/// «9» / «7,5» / «7.25» soat → daqiqa; noto'g'ri — `null`.
int? parseHoursToMinutes(String text) {
  final m = RegExp(r'^(\d{1,2})(?:[.,](\d{1,2}))?$').firstMatch(text.trim());
  if (m == null) return null;
  final frac = m[2] ?? '';
  final fracMinutes = frac.isEmpty
      ? 0
      : MoneyRounding.mulDiv(int.parse(frac), 60, frac.length == 1 ? 10 : 100);
  return int.parse(m[1]!) * 60 + fracMinutes;
}

/// Daqiqa → soat bir xonali kasr bilan: 450 → «7,5», 540 → «9».
String hoursLabel(int minutes) {
  final tenths = (minutes * 10 + 30) ~/ 60;
  final rest = tenths % 10;
  return rest == 0 ? '${tenths ~/ 10}' : '${tenths ~/ 10},$rest';
}

String learningError(AppLocalizations l10n, Object e) => switch (e) {
  DomainRuleException(code: LearningMath.errInvalidHours) => l10n.lnErrHours,
  DomainRuleException(code: LearningMath.errInvalidAmount) => l10n.lnErrAmount,
  DomainRuleException(code: LearningService.errNoHourly) => l10n.lnErrNoHourly,
  DomainRuleException(code: LearningService.errTitleRequired) =>
    l10n.lnErrTitle,
  DomainRuleException(code: LearningService.errPurposeRequired) =>
    l10n.lnErrPurpose,
  DomainRuleException(code: LearningService.errOutcomeRequired) =>
    l10n.lnErrOutcome,
  DomainRuleException(code: LearningService.errTeachingRequired) =>
    l10n.lnErrTeaching,
  _ => l10n.genericError,
};

String learningKindLabel(AppLocalizations l10n, LearningItemKind k) =>
    switch (k) {
      LearningItemKind.book => l10n.lnKindBook,
      LearningItemKind.mentor => l10n.lnKindMentor,
      LearningItemKind.course => l10n.lnKindCourse,
      LearningItemKind.practice => l10n.lnKindPractice,
    };

IconData learningKindIcon(LearningItemKind k) => switch (k) {
  LearningItemKind.book => Icons.menu_book_outlined,
  LearningItemKind.mentor => Icons.chat_bubble_outline,
  LearningItemKind.course => Icons.school_outlined,
  LearningItemKind.practice => Icons.build_outlined,
};

String learningItemStatusLabel(AppLocalizations l10n, LearningItemStatus s) =>
    switch (s) {
      LearningItemStatus.planned => l10n.lnItemStatusPlanned,
      LearningItemStatus.inProgress => l10n.lnItemStatusInProgress,
      LearningItemStatus.done => l10n.lnItemStatusDone,
      LearningItemStatus.dropped => l10n.lnItemStatusDropped,
    };

String learningGoalStatusLabel(AppLocalizations l10n, LearningGoalStatus s) =>
    switch (s) {
      LearningGoalStatus.active => l10n.lnGoalStatusActive,
      LearningGoalStatus.done => l10n.lnGoalStatusDone,
      LearningGoalStatus.dropped => l10n.lnGoalStatusDropped,
    };

/// Soat qiymati natijasi (SPEC 2H.1): qiymat, ikki barobar maqsad, chegara.
class HourlyResultView extends StatelessWidget {
  const HourlyResultView({required this.value, this.previous, super.key});

  final HourlyValue value;

  /// Avvalgi hisobdagi soat qiymati (o'zgarishni ko'rsatish uchun).
  final Money? previous;

  @override
  Widget build(BuildContext context) {
    final l10n = context.l10n;
    final money = context.money;
    final theme = Theme.of(context);
    return Column(
      key: const Key('ln-hourly-result'),
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Text(
          l10n.lnHourlyValue(money(value.hourly)),
          style: theme.textTheme.titleMedium,
        ),
        if (previous case final p? when p != value.hourly)
          Text(l10n.lnHourlyChange(money(p), money(value.hourly))),
        const SizedBox(height: 4),
        Text(l10n.lnHourlyDoubled(money(value.doubledHourly))),
        Text(l10n.lnHourlyLoad(percentLabel(value.loadBp))),
        Text(l10n.lnHourlyCeiling(money(value.ceilingIncome))),
        const SizedBox(height: 8),
        Text(
          value.doubleByHoursFeasible
              ? l10n.lnHourlyCanDouble
              : l10n.lnHourlyNoDouble,
          key: Key('ln-hourly-feasible-${value.doubleByHoursFeasible}'),
        ),
        const SizedBox(height: 4),
        Text(l10n.lnHourlyExplain, style: theme.textTheme.bodySmall),
      ],
    );
  }
}

/// Yangi o'qish maqsadi (SPEC 2H.2). Saqlangan maqsad yoki `null`.
Future<LearningGoal?> showLearningGoalDialog(
  BuildContext context,
  WidgetRef ref, {
  required Money baseHourly,
}) => showDialog<LearningGoal>(
  context: context,
  builder: (_) => _GoalDialog(baseHourly: baseHourly),
);

class _GoalDialog extends ConsumerStatefulWidget {
  const _GoalDialog({required this.baseHourly});

  final Money baseHourly;

  @override
  ConsumerState<_GoalDialog> createState() => _GoalDialogState();
}

class _GoalDialogState extends ConsumerState<_GoalDialog> {
  final _title = TextEditingController();
  final _why = TextEditingController();
  late Money _target = widget.baseHourly.times(2);
  String? _error;

  @override
  void dispose() {
    _title.dispose();
    _why.dispose();
    super.dispose();
  }

  Future<void> _save() async {
    final l10n = context.l10n;
    try {
      final goal = await (await ref.read(
        learningServiceProvider.future,
      )).createGoal(title: _title.text, why: _why.text, targetHourly: _target);
      ref.invalidate(learningOverviewProvider);
      await recordTaskEvent(ref, TaskTrigger.learningGoalSet);
      if (mounted) Navigator.pop(context, goal);
    } on Object catch (e) {
      AppLog.event('learning_goal_save_failed');
      setState(() => _error = learningError(l10n, e));
    }
  }

  @override
  Widget build(BuildContext context) {
    final l10n = context.l10n;
    final money = context.money;
    return AlertDialog(
      title: Text(l10n.lnGoalNew),
      content: SingleChildScrollView(
        child: Column(
          mainAxisSize: MainAxisSize.min,
          crossAxisAlignment: CrossAxisAlignment.stretch,
          children: [
            TextField(
              key: const Key('ln-goal-title'),
              controller: _title,
              decoration: InputDecoration(labelText: l10n.lnGoalTitleField),
            ),
            TextField(
              key: const Key('ln-goal-why'),
              controller: _why,
              maxLines: 2,
              decoration: InputDecoration(labelText: l10n.lnGoalWhy),
            ),
            ListTile(
              key: const Key('ln-goal-target'),
              contentPadding: EdgeInsets.zero,
              title: Text(l10n.lnGoalTarget),
              subtitle: Text(
                l10n.lnGoalRange(money(widget.baseHourly), money(_target)),
              ),
              trailing: const Icon(Icons.edit_outlined),
              onTap: () async {
                final a = await showAmountSheet(
                  context,
                  currency: widget.baseHourly.currency,
                  title: l10n.lnGoalTarget,
                  initial: _target,
                );
                if (a != null && mounted) setState(() => _target = a);
              },
            ),
            if (_error case final e?)
              Text(
                e,
                key: const Key('ln-goal-error'),
                style: TextStyle(color: Theme.of(context).colorScheme.error),
              ),
          ],
        ),
      ),
      actions: [
        TextButton(
          onPressed: () => Navigator.pop(context),
          child: Text(l10n.cancel),
        ),
        FilledButton(
          key: const Key('ln-goal-save'),
          onPressed: _save,
          child: Text(l10n.save),
        ),
      ],
    );
  }
}

/// «O'rgatganlarim» yozuvi (SPEC 2H.6).
Future<void> showTeachingDialog(BuildContext context) =>
    showDialog<void>(context: context, builder: (_) => const _TeachingDialog());

class _TeachingDialog extends ConsumerStatefulWidget {
  const _TeachingDialog();

  @override
  ConsumerState<_TeachingDialog> createState() => _TeachingDialogState();
}

class _TeachingDialogState extends ConsumerState<_TeachingDialog> {
  final _learner = TextEditingController();
  final _topic = TextEditingController();
  final _minutes = TextEditingController();
  final _note = TextEditingController();
  String? _error;

  @override
  void dispose() {
    _learner.dispose();
    _topic.dispose();
    _minutes.dispose();
    _note.dispose();
    super.dispose();
  }

  Future<void> _save() async {
    final l10n = context.l10n;
    final text = _minutes.text.trim();
    final minutes = text.isEmpty ? null : int.tryParse(text);
    if (text.isNotEmpty && minutes == null) {
      setState(() => _error = l10n.lnErrAmount);
      return;
    }
    try {
      await (await ref.read(learningServiceProvider.future)).logTeaching(
        learner: _learner.text,
        topic: _topic.text,
        minutes: minutes,
        note: _note.text,
      );
      ref.invalidate(learningOverviewProvider);
      await recordTaskEvent(ref, TaskTrigger.teachingLogged);
      if (mounted) Navigator.pop(context);
    } on Object catch (e) {
      AppLog.event('teaching_save_failed');
      setState(() => _error = learningError(l10n, e));
    }
  }

  @override
  Widget build(BuildContext context) {
    final l10n = context.l10n;
    return AlertDialog(
      title: Text(l10n.lnTeachTitle),
      content: SingleChildScrollView(
        child: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            TextField(
              key: const Key('ln-teach-learner'),
              controller: _learner,
              decoration: InputDecoration(labelText: l10n.lnTeachLearner),
            ),
            TextField(
              key: const Key('ln-teach-topic'),
              controller: _topic,
              decoration: InputDecoration(labelText: l10n.lnTeachTopic),
            ),
            TextField(
              key: const Key('ln-teach-minutes'),
              controller: _minutes,
              keyboardType: TextInputType.number,
              decoration: InputDecoration(labelText: l10n.lnTeachMinutes),
            ),
            TextField(
              key: const Key('ln-teach-note'),
              controller: _note,
              decoration: InputDecoration(labelText: l10n.lnTeachNote),
            ),
            if (_error case final e?)
              Text(
                e,
                key: const Key('ln-teach-error'),
                style: TextStyle(color: Theme.of(context).colorScheme.error),
              ),
          ],
        ),
      ),
      actions: [
        TextButton(
          onPressed: () => Navigator.pop(context),
          child: Text(l10n.cancel),
        ),
        FilledButton(
          key: const Key('ln-teach-save'),
          onPressed: _save,
          child: Text(l10n.save),
        ),
      ],
    );
  }
}

/// Kichik holat yorlig'i.
class LearningChip extends StatelessWidget {
  const LearningChip(this.label, {this.color, super.key});

  final String label;
  final Color? color;

  @override
  Widget build(BuildContext context) => Chip(
    label: Text(label),
    visualDensity: VisualDensity.compact,
    backgroundColor: color,
  );
}
