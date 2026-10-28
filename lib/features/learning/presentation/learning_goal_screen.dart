import 'package:baraka_daftari/app/l10n/l10n.dart';
import 'package:baraka_daftari/app/widgets/money_input.dart';
import 'package:baraka_daftari/core/domain/enums.dart';
import 'package:baraka_daftari/core/errors/data_exceptions.dart';
import 'package:baraka_daftari/core/logging/app_log.dart';
import 'package:baraka_daftari/core/money/money.dart';
import 'package:baraka_daftari/features/content/data/content_providers.dart';
import 'package:baraka_daftari/features/content/domain/content.dart';
import 'package:baraka_daftari/features/content/presentation/content_widgets.dart';
import 'package:baraka_daftari/features/learning/data/learning_providers.dart';
import 'package:baraka_daftari/features/learning/domain/course_check.dart';
import 'package:baraka_daftari/features/learning/domain/learning.dart';
import 'package:baraka_daftari/features/learning/domain/learning_math.dart';
import 'package:baraka_daftari/features/learning/domain/learning_service.dart';
import 'package:baraka_daftari/features/learning/presentation/learning_widgets.dart';
import 'package:baraka_daftari/features/partnerships/domain/offer_check.dart';
import 'package:baraka_daftari/features/partnerships/presentation/offer_check_screen.dart';
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

String courseQuestionText(AppLocalizations l10n, CourseQuestion q) =>
    switch (q) {
      CourseQuestion.incomePromise => l10n.lnCourseQIncome,
      CourseQuestion.pressure => l10n.lnCourseQPressure,
      CourseQuestion.referralIncome => l10n.lnCourseQReferral,
      CourseQuestion.secretMethod => l10n.lnCourseQSecret,
      CourseQuestion.curriculumShown => l10n.lnCourseQCurriculum,
      CourseQuestion.teacherPractices => l10n.lnCourseQTeacher,
      CourseQuestion.refundTerms => l10n.lnCourseQRefund,
    };

String courseSignText(AppLocalizations l10n, ScamSign s) => switch (s) {
  ScamSign.guaranteedHighReturn => l10n.lnCourseSignIncome,
  ScamSign.urgency => l10n.lnCourseSignUrgency,
  ScamSign.recruitmentIncome => l10n.lnCourseSignReferral,
  ScamSign.noRealBusiness => l10n.lnCourseSignNoSkill,
  ScamSign.hardExit => l10n.lnCourseSignRefund,
};

Color verdictColor(BuildContext context, OfferVerdict v) {
  final scheme = Theme.of(context).colorScheme;
  return switch (v) {
    OfferVerdict.green => scheme.primaryContainer,
    OfferVerdict.yellow => scheme.tertiaryContainer,
    OfferVerdict.red => scheme.errorContainer,
  };
}

/// O'qish maqsadi: yo'llar (SPEC 2H.3), qoplanish (2H.4), kurs tekshiruvi
/// (2H.5).
class LearningGoalScreen extends ConsumerWidget {
  const LearningGoalScreen({required this.id, super.key});

  final String id;

  Future<void> _run(
    BuildContext context,
    WidgetRef ref,
    Future<void> Function(LearningService s) action,
  ) async {
    final l10n = context.l10n;
    final messenger = ScaffoldMessenger.of(context);
    try {
      await action(await ref.read(learningServiceProvider.future));
      ref.invalidate(learningOverviewProvider);
    } on Object catch (e) {
      AppLog.event('learning_goal_action_failed');
      messenger.showSnackBar(SnackBar(content: Text(learningError(l10n, e))));
    }
  }

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final l10n = context.l10n;
    final data = ref.watch(learningOverviewProvider);
    final view = data.valueOrNull?.goals
        .where((g) => g.goal.meta.id == id)
        .firstOrNull;
    if (view == null) {
      return Scaffold(
        appBar: AppBar(title: Text(l10n.lnGoalsTitle)),
        body: data.isLoading
            ? const Center(child: CircularProgressIndicator())
            : Center(child: Text(l10n.genericError)),
      );
    }
    final goal = view.goal;
    final theme = Theme.of(context);
    final money = context.money;
    return Scaffold(
      appBar: AppBar(
        title: Text(goal.title),
        actions: [
          PopupMenuButton<LearningGoalStatus>(
            key: const Key('ln-goal-menu'),
            onSelected: (s) =>
                _run(context, ref, (svc) => svc.setGoalStatus(goal, s)),
            itemBuilder: (_) => [
              if (goal.status == LearningGoalStatus.active) ...[
                PopupMenuItem(
                  value: LearningGoalStatus.done,
                  child: Text(l10n.lnGoalMarkDone),
                ),
                PopupMenuItem(
                  value: LearningGoalStatus.dropped,
                  child: Text(l10n.lnGoalDrop),
                ),
              ] else
                PopupMenuItem(
                  value: LearningGoalStatus.active,
                  child: Text(l10n.lnGoalReopen),
                ),
            ],
          ),
        ],
      ),
      floatingActionButton: goal.status == LearningGoalStatus.active
          ? FloatingActionButton.extended(
              key: const Key('ln-item-add'),
              icon: const Icon(Icons.add),
              label: Text(l10n.lnItemAdd),
              onPressed: () => showModalBottomSheet<void>(
                context: context,
                isScrollControlled: true,
                showDragHandle: true,
                builder: (_) => _ItemSheet(goal: goal),
              ),
            )
          : null,
      body: ListView(
        padding: const EdgeInsets.fromLTRB(16, 8, 16, 96),
        children: [
          const ContentDisclaimer(),
          Text(
            l10n.lnGoalRange(
              money(goal.baseHourly),
              money(goal.targetHourly),
            ),
            style: theme.textTheme.titleMedium,
          ),
          if (goal.why case final w?) Text(w),
          const SizedBox(height: 4),
          Align(
            alignment: Alignment.centerLeft,
            child: LearningChip(learningGoalStatusLabel(l10n, goal.status)),
          ),
          if (view.payback case final p?) ...[
            const SizedBox(height: 8),
            _PaybackCard(payback: p, goal: goal),
          ],
          const SizedBox(height: 16),
          Text(l10n.lnItemsTitle, style: theme.textTheme.titleMedium),
          if (view.items.isEmpty)
            Padding(
              padding: const EdgeInsets.only(top: 4),
              child: Text(l10n.lnItemsEmpty),
            ),
          for (final item in view.items)
            _ItemCard(
              item: item,
              onStatus: (s) => _changeStatus(context, ref, item, s),
              onCheck: () => showModalBottomSheet<void>(
                context: context,
                isScrollControlled: true,
                showDragHandle: true,
                builder: (_) => _CourseSheet(item: item),
              ),
            ),
        ],
      ),
    );
  }

  Future<void> _changeStatus(
    BuildContext context,
    WidgetRef ref,
    LearningItem item,
    LearningItemStatus status,
  ) async {
    final l10n = context.l10n;
    String? outcome;
    var confirmRed = false;
    if (status == LearningItemStatus.done) {
      outcome = await _askOutcome(context);
      if (outcome == null) return;
    }
    if (!context.mounted) return;
    if (status == LearningItemStatus.inProgress &&
        item.kind == LearningItemKind.course &&
        item.courseVerdict == OfferVerdict.red) {
      final ok = await showDialog<bool>(
        context: context,
        builder: (context) => AlertDialog(
          title: Text(l10n.lnCourseRedConfirmTitle),
          content: Text(l10n.lnCourseRedConfirmBody),
          actions: [
            TextButton(
              onPressed: () => Navigator.pop(context, false),
              child: Text(l10n.cancel),
            ),
            FilledButton(
              key: const Key('ln-red-confirm'),
              onPressed: () => Navigator.pop(context, true),
              child: Text(l10n.lnCourseRedConfirmYes),
            ),
          ],
        ),
      );
      if (ok != true) return;
      confirmRed = true;
    }
    if (!context.mounted) return;
    await _run(
      context,
      ref,
      (s) => s.setItemStatus(
        item,
        status,
        outcome: outcome,
        confirmRedCourse: confirmRed,
      ),
    );
  }

  Future<String?> _askOutcome(BuildContext context) => showDialog<String>(
    context: context,
    builder: (_) => const _OutcomeDialog(),
  );
}

/// «Tugatdim»: erishilgan natija (SPEC 2H.3). Bo'sh natijada oyna
/// yopilmaydi — xato maydon ostida chiqadi.
class _OutcomeDialog extends StatefulWidget {
  const _OutcomeDialog();

  @override
  State<_OutcomeDialog> createState() => _OutcomeDialogState();
}

class _OutcomeDialogState extends State<_OutcomeDialog> {
  // Oyna yopilish animatsiyasi tugaguncha kontroller tirik qoladi.
  final _controller = TextEditingController();
  var _empty = false;

  @override
  void dispose() {
    _controller.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    final l10n = context.l10n;
    return AlertDialog(
      title: Text(l10n.lnItemOutcome),
      content: TextField(
        key: const Key('ln-item-outcome'),
        controller: _controller,
        maxLines: 3,
        autofocus: true,
        onChanged: (_) {
          if (_empty) setState(() => _empty = false);
        },
        decoration: InputDecoration(
          errorText: _empty ? l10n.lnErrOutcome : null,
        ),
      ),
      actions: [
        TextButton(
          onPressed: () => Navigator.pop(context),
          child: Text(l10n.cancel),
        ),
        FilledButton(
          key: const Key('ln-item-outcome-save'),
          onPressed: () {
            if (_controller.text.trim().isEmpty) {
              setState(() => _empty = true);
              return;
            }
            Navigator.pop(context, _controller.text);
          },
          child: Text(l10n.save),
        ),
      ],
    );
  }
}

/// Qoplanish taxmini (SPEC 2H.4): shartli matn, va'da emas.
class _PaybackCard extends StatelessWidget {
  const _PaybackCard({required this.payback, required this.goal});

  final SkillPayback payback;
  final LearningGoal goal;

  @override
  Widget build(BuildContext context) {
    final l10n = context.l10n;
    final money = context.money;
    final theme = Theme.of(context);
    final p = payback;
    final months = p.paybackMonths;
    return Card(
      key: const Key('ln-payback'),
      child: Padding(
        padding: const EdgeInsets.all(16),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text(l10n.lnPaybackTitle, style: theme.textTheme.titleSmall),
            const SizedBox(height: 4),
            if (p.totalInvest.isZero)
              Text(l10n.lnPaybackFree, key: const Key('ln-payback-free'))
            else ...[
              Text(
                l10n.lnPaybackInvest(
                  money(p.totalInvest - p.timeCost),
                  money(p.timeCost),
                  money(p.totalInvest),
                ),
              ),
              if (months == null)
                Text(l10n.lnPaybackNever, key: const Key('ln-payback-never'))
              else ...[
                Text(
                  l10n.lnPaybackGain(money(estimateDisplay(p.monthlyGain))),
                  key: const Key('ln-payback-gain'),
                ),
                Text(
                  l10n.lnPaybackMonths(months),
                  key: const Key('ln-payback-months'),
                ),
              ],
            ],
            const SizedBox(height: 4),
            Text(l10n.lnPaybackNote, style: theme.textTheme.bodySmall),
          ],
        ),
      ),
    );
  }
}

class _ItemCard extends StatelessWidget {
  const _ItemCard({
    required this.item,
    required this.onStatus,
    required this.onCheck,
  });

  final LearningItem item;
  final ValueChanged<LearningItemStatus> onStatus;
  final VoidCallback onCheck;

  @override
  Widget build(BuildContext context) {
    final l10n = context.l10n;
    final money = context.money;
    final open =
        item.status == LearningItemStatus.planned ||
        item.status == LearningItemStatus.inProgress;
    final isCourse = item.kind == LearningItemKind.course;
    return Card(
      key: Key('ln-item-${item.meta.id}'),
      child: Padding(
        padding: const EdgeInsets.fromLTRB(12, 8, 4, 8),
        child: Row(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Padding(
              padding: const EdgeInsets.only(top: 4, right: 12),
              child: Icon(learningKindIcon(item.kind)),
            ),
            Expanded(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text(
                    '${learningKindLabel(l10n, item.kind)}: ${item.title}',
                    style: Theme.of(context).textTheme.titleSmall,
                  ),
                  Text(l10n.lnItemPurposeLabel(item.purpose)),
                  if (item.outcome case final o?)
                    Text(l10n.lnItemOutcomeLabel(o)),
                  Text(
                    [
                      learningItemStatusLabel(l10n, item.status),
                      if (item.cost case final c?) money(c),
                      if (item.studyMinutes case final m?)
                        durationLabel(l10n, m),
                    ].join(' · '),
                  ),
                  if (isCourse && item.courseVerdict != null)
                    Padding(
                      padding: const EdgeInsets.only(top: 4),
                      child: LearningChip(
                        offerVerdictLabel(l10n, item.courseVerdict!),
                        key: Key(
                          'ln-item-verdict-${item.courseVerdict!.name}',
                        ),
                        color: verdictColor(context, item.courseVerdict!),
                      ),
                    ),
                ],
              ),
            ),
            if (open || isCourse)
              PopupMenuButton<String>(
                key: Key('ln-item-menu-${item.meta.id}'),
                onSelected: (v) => switch (v) {
                  'check' => onCheck(),
                  _ => onStatus(LearningItemStatus.values.byName(v)),
                },
                itemBuilder: (_) => [
                  if (isCourse && open)
                    PopupMenuItem(
                      key: const Key('ln-item-action-check'),
                      value: 'check',
                      child: Text(l10n.lnCourseCheck),
                    ),
                  if (item.status == LearningItemStatus.planned)
                    PopupMenuItem(
                      key: const Key('ln-item-action-inProgress'),
                      value: LearningItemStatus.inProgress.name,
                      child: Text(l10n.lnItemStart),
                    ),
                  if (open) ...[
                    PopupMenuItem(
                      key: const Key('ln-item-action-done'),
                      value: LearningItemStatus.done.name,
                      child: Text(l10n.lnItemFinish),
                    ),
                    PopupMenuItem(
                      key: const Key('ln-item-action-dropped'),
                      value: LearningItemStatus.dropped.name,
                      child: Text(l10n.lnItemDrop),
                    ),
                  ],
                ],
              ),
          ],
        ),
      ),
    );
  }
}

/// Yangi o'qish yo'li (SPEC 2H.3).
class _ItemSheet extends ConsumerStatefulWidget {
  const _ItemSheet({required this.goal});

  final LearningGoal goal;

  @override
  ConsumerState<_ItemSheet> createState() => _ItemSheetState();
}

class _ItemSheetState extends ConsumerState<_ItemSheet> {
  final _title = TextEditingController();
  final _purpose = TextEditingController();
  final _hours = TextEditingController();
  LearningItemKind _kind = LearningItemKind.book;
  Money? _cost;
  String? _error;

  @override
  void dispose() {
    _title.dispose();
    _purpose.dispose();
    _hours.dispose();
    super.dispose();
  }

  Future<void> _save() async {
    final l10n = context.l10n;
    final text = _hours.text.trim();
    final minutes = text.isEmpty ? null : parseHoursToMinutes(text);
    if (text.isNotEmpty && minutes == null) {
      setState(() => _error = l10n.lnErrAmount);
      return;
    }
    try {
      await (await ref.read(learningServiceProvider.future)).addItem(
        goalId: widget.goal.meta.id,
        kind: _kind,
        title: _title.text,
        purpose: _purpose.text,
        cost: _cost,
        studyMinutes: minutes,
      );
      ref.invalidate(learningOverviewProvider);
      await recordTaskEvent(ref, TaskTrigger.learningPathAdded);
      if (mounted) Navigator.pop(context);
    } on Object catch (e) {
      AppLog.event('learning_item_save_failed');
      setState(() => _error = learningError(l10n, e));
    }
  }

  @override
  Widget build(BuildContext context) {
    final l10n = context.l10n;
    final money = context.money;
    final theme = Theme.of(context);
    return Padding(
      padding: EdgeInsets.fromLTRB(
        16,
        0,
        16,
        16 + MediaQuery.viewInsetsOf(context).bottom,
      ),
      child: SingleChildScrollView(
        child: Column(
          mainAxisSize: MainAxisSize.min,
          crossAxisAlignment: CrossAxisAlignment.stretch,
          children: [
            Text(l10n.lnItemAdd, style: theme.textTheme.titleMedium),
            const SizedBox(height: 8),
            Wrap(
              spacing: 8,
              children: [
                for (final k in LearningItemKind.values)
                  ChoiceChip(
                    key: Key('ln-item-kind-${k.name}'),
                    avatar: Icon(learningKindIcon(k), size: 18),
                    label: Text(learningKindLabel(l10n, k)),
                    selected: _kind == k,
                    onSelected: (_) => setState(() => _kind = k),
                  ),
              ],
            ),
            TextField(
              key: const Key('ln-item-title'),
              controller: _title,
              decoration: InputDecoration(labelText: l10n.lnItemTitle),
            ),
            TextField(
              key: const Key('ln-item-purpose'),
              controller: _purpose,
              maxLines: 2,
              decoration: InputDecoration(
                labelText: l10n.lnItemPurpose,
                helperText: l10n.lnItemPurposeHint,
                helperMaxLines: 2,
              ),
            ),
            ListTile(
              key: const Key('ln-item-cost'),
              contentPadding: EdgeInsets.zero,
              title: Text(l10n.lnItemCost),
              subtitle: Text(_cost == null ? '—' : money(_cost!)),
              trailing: const Icon(Icons.edit_outlined),
              onTap: () async {
                final a = await showAmountSheet(
                  context,
                  currency: widget.goal.baseHourly.currency,
                  title: l10n.lnItemCost,
                  initial: _cost,
                );
                if (a != null && mounted) setState(() => _cost = a);
              },
            ),
            if (_cost case final c? when c.isPositive)
              Text(
                l10n.lnItemNoDebt,
                key: const Key('ln-item-no-debt'),
                style: theme.textTheme.bodySmall,
              ),
            TextField(
              key: const Key('ln-item-hours'),
              controller: _hours,
              keyboardType: const TextInputType.numberWithOptions(
                decimal: true,
              ),
              decoration: InputDecoration(labelText: l10n.lnItemStudyHours),
            ),
            if (_error case final e?)
              Padding(
                padding: const EdgeInsets.only(top: 8),
                child: Text(
                  e,
                  key: const Key('ln-item-error'),
                  style: TextStyle(color: theme.colorScheme.error),
                ),
              ),
            const SizedBox(height: 12),
            FilledButton(
              key: const Key('ln-item-save'),
              onPressed: _save,
              child: Text(l10n.save),
            ),
          ],
        ),
      ),
    );
  }
}

/// Kurs tekshiruvi (SPEC 2H.5): 7 savol → besh belgi va baho.
class _CourseSheet extends ConsumerStatefulWidget {
  const _CourseSheet({required this.item});

  final LearningItem item;

  @override
  ConsumerState<_CourseSheet> createState() => _CourseSheetState();
}

class _CourseSheetState extends ConsumerState<_CourseSheet> {
  late final Map<CourseQuestion, OfferAnswer> _answers = courseAnswersFromJson(
    widget.item.courseAnswersJson,
  );

  Future<void> _save() async {
    final l10n = context.l10n;
    final messenger = ScaffoldMessenger.of(context);
    try {
      await (await ref.read(
        learningServiceProvider.future,
      )).saveCourseCheck(widget.item, _answers);
      ref.invalidate(learningOverviewProvider);
      if (mounted) Navigator.pop(context);
    } on DomainRuleException catch (e) {
      messenger.showSnackBar(SnackBar(content: Text(learningError(l10n, e))));
    } on Object {
      AppLog.event('course_check_save_failed');
      messenger.showSnackBar(SnackBar(content: Text(l10n.genericError)));
    }
  }

  @override
  Widget build(BuildContext context) {
    final l10n = context.l10n;
    final theme = Theme.of(context);
    final e = evaluateCourse(_answers);
    return Padding(
      padding: const EdgeInsets.fromLTRB(16, 0, 16, 16),
      child: ListView(
        shrinkWrap: true,
        children: [
          Text(l10n.lnCourseTitle, style: theme.textTheme.titleMedium),
          Text(widget.item.title),
          const SizedBox(height: 8),
          for (final q in CourseQuestion.values) ...[
            Text(courseQuestionText(l10n, q)),
            const SizedBox(height: 4),
            SegmentedButton<OfferAnswer>(
              key: Key('ln-course-q-${q.name}'),
              emptySelectionAllowed: true,
              showSelectedIcon: false,
              segments: [
                for (final (a, label) in [
                  (OfferAnswer.yes, l10n.offerYes),
                  (OfferAnswer.no, l10n.offerNo),
                  (OfferAnswer.unknown, l10n.offerUnknown),
                ])
                  ButtonSegment(
                    value: a,
                    label: Text(
                      label,
                      key: Key('ln-course-${q.name}-${a.name}'),
                    ),
                  ),
              ],
              selected: {?_answers[q]},
              onSelectionChanged: (s) => setState(() {
                if (s.isEmpty) {
                  _answers.remove(q);
                } else {
                  _answers[q] = s.single;
                }
              }),
            ),
            const SizedBox(height: 12),
          ],
          Card(
            key: Key('ln-course-result-${e.verdict.name}'),
            color: verdictColor(context, e.verdict),
            child: Padding(
              padding: const EdgeInsets.all(12),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text(
                    switch (e.verdict) {
                      OfferVerdict.green => l10n.lnCourseGreen,
                      OfferVerdict.yellow => l10n.lnCourseYellow,
                      OfferVerdict.red => l10n.lnCourseRed,
                    },
                    style: theme.textTheme.titleSmall,
                  ),
                  for (final s in e.signs)
                    Padding(
                      padding: const EdgeInsets.only(top: 4),
                      child: Text(
                        '• ${courseSignText(l10n, s)}',
                        key: Key('ln-course-sign-${s.name}'),
                      ),
                    ),
                ],
              ),
            ),
          ),
          const SizedBox(height: 8),
          FilledButton(
            key: const Key('ln-course-save'),
            onPressed: _save,
            child: Text(l10n.lnCourseSave),
          ),
        ],
      ),
    );
  }
}
