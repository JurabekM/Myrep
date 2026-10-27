import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../app/i18n.dart';
import '../../app/theme.dart';
import '../../core/core.dart';
import '../../core/query.dart';
import '../../shared/format.dart';
import '../../shared/widgets.dart';
import '../learning/learning_screen.dart' show learningPaths, parseCount, showMinutes, toMinutes;
import '../venture/offer_check.dart';

const mfGoals = ['ABROAD', 'HOME'];
const mfAreas = ['WORK', 'LANGUAGE', 'DOCUMENTS', 'OTHER'];

/// Holat o'tishlari tugmalari (yadro `transition` qoidasi bilan bir xil; yopilgan reja — tugmasiz).
const _next = {
  'ACTIVE': ['PAUSED', 'DONE', 'DROPPED'],
  'PAUSED': ['ACTIVE', 'DONE', 'DROPPED'],
};

/// Musofir «O'zimga sarmoya» (8-tamoyil, musofir/SPEC 6A): bir soat qiymati ish valyutasida (uy
/// valyutasida — faqat kiritilgan kurs bilan), ikki maqsadli bilim rejasi (chet elda / uyda), «Ilm
/// zakoti» (hamyurtlarga yordam), kurs tekshiruvi (`jobAbroad` savoli bilan) va shu oy «Sarmoya»
/// qatori. Musofirning shaxsiy bo'limi; barcha summa yadrodan. Desktop `MfLearningScreen.tsx` bilan bir xil.
class MfLearningScreen extends ConsumerWidget {
  const MfLearningScreen({required this.spaceId, super.key});

  final String spaceId;

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final o = ref.watch(query(['mfLearning', spaceId], (c) => c.mfLearningOverview(spaceId: spaceId)));
    final d = o.valueOrNull;
    final p = context.palette;
    final s = d?.selfInvestment;
    return ScreenBody(
      mentorKey: 'mentor.mfLearning',
      children: [
        Card(
          color: p.sidebar,
          child: Padding(
            padding: const EdgeInsets.all(16),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(
                  context.t('mentor.name'),
                  style: TextStyle(color: p.accentText, fontWeight: FontWeight.w700),
                ),
                const SizedBox(height: 6),
                Text(context.t('mfl.intro')),
                const SizedBox(height: 8),
                Hint(context.t('mfl.example')),
              ],
            ),
          ),
        ),
        SectionCard(
          title: context.t('learn.tasks.title'),
          children: [
            for (final n in [1, 2, 3])
              Padding(
                padding: const EdgeInsets.only(bottom: 6),
                child: Text('$n. ${context.t('mfl.tasks.$n')}'),
              ),
          ],
        ),
        if (o.hasError) ErrorText(o.error),
        if (s != null)
          Kpi(
            key: const Key('mfl-self-investment'),
            label: context.t('mfl.invest.title'),
            value: s.sharePercent == null
                ? context.t('learn.selfInvestment.noIncome', {'total': s.total.formatted})
                : context.t('learn.selfInvestment.line', {'total': s.total.formatted, 'percent': s.sharePercent}),
            hint: context.t('mfl.invest.hint'),
          ),
        if (d != null) _HourCard(key: ValueKey(('mfl-hour', d.hourValue?.id)), spaceId: spaceId, data: d),
        if (d != null)
          SectionCard(
            title: context.t('mfl.plans.title'),
            trailing: TextButton(
              onPressed: () => showSheet<void>(context, (_) => MfPlanSheet(spaceId: spaceId, data: d)),
              child: Text(context.t('learn.plans.new')),
            ),
            children: [
              Hint(context.t('mfl.plans.hint')),
              if (d.plans.isEmpty) ...[const SizedBox(height: 8), Hint(context.t('mfl.plans.empty'))],
            ],
          ),
        if (d != null)
          for (final pl in d.plans) _PlanCard(key: ValueKey(('mfl-plan', pl.id)), spaceId: spaceId, plan: pl),
        if (d != null) _TeachingCard(spaceId: spaceId, data: d),
        SectionCard(
          title: context.t('mfl.course.title'),
          children: [
            Hint(context.t('mfl.course.hint')),
            const SizedBox(height: 8),
            Align(
              alignment: Alignment.centerLeft,
              child: OutlinedButton(
                key: const Key('mfl-course-check'),
                onPressed: () => openOfferCheck(context, mode: 'COURSE', askJobAbroad: true),
                child: Text(context.t('learn.plan.checkCourse')),
              ),
            ),
          ],
        ),
      ],
    );
  }
}

/// Bir soat qiymati (ish valyutasida): oxirgi to'liq oylar taklifi (AUTO) yoki qo'lda daromad va ish vaqti.
class _HourCard extends ConsumerStatefulWidget {
  const _HourCard({required this.spaceId, required this.data, super.key});

  final String spaceId;
  final MfLearningOverviewDto data;

  @override
  ConsumerState<_HourCard> createState() => _HourCardState();
}

class _HourCardState extends ConsumerState<_HourCard> with ActionState {
  late final MfHourDto? _hv = widget.data.hourValue;
  late final _income = TextEditingController(text: _hv?.incomeSource == 'MANUAL' ? _hv?.income.plain : '');
  late final _hours = TextEditingController(text: '${(_hv?.minutesPerDay ?? 600) ~/ 60}');
  late final _minutes = TextEditingController(text: '${(_hv?.minutesPerDay ?? 600) % 60}');
  late final _days = TextEditingController(text: '${_hv?.days ?? 22}');

  @override
  void dispose() {
    for (final c in [_income, _hours, _minutes, _days]) {
      c.dispose();
    }
    super.dispose();
  }

  Future<void> _save() async {
    await act(
      () => ref
          .read(coreProvider)
          .mfHourSave(
            spaceId: widget.spaceId,
            input: MfHourInput(
              income: _income.text.trim().isEmpty ? null : _income.text,
              minutesPerDay: toMinutes(_hours.text, _minutes.text),
              days: parseCount(_days.text, 2),
            ),
          ),
    );
  }

  @override
  Widget build(BuildContext context) {
    final hv = widget.data.hourValue;
    final id = widget.spaceId;
    final s = ref.watch(query(['mfHourSuggest', id], (c) => c.mfHourSuggest(spaceId: id))).valueOrNull;
    final p = context.palette;
    return SectionCard(
      title: context.t('mfl.hour.title'),
      children: [
        if (hv == null)
          Hint(context.t('mfl.hour.none'))
        else ...[
          Text(context.t('learn.hour.value'), style: TextStyle(color: p.inkMuted)),
          Text(
            hv.hourValue.formatted,
            key: const Key('mfl-hour-value'),
            style: TextStyle(fontSize: 26, fontWeight: FontWeight.w700, color: p.accent),
          ),
          ValueRow(context.t('learn.hour.double'), hv.doubleTarget.formatted, strong: true),
          _HomeView(hv.home),
          Text(
            context.t('mfl.hour.income', {
              'amount': hv.income.formatted,
              'source': hv.incomeSource == 'AUTO'
                  ? context.t('mfl.hour.source.AUTO', {'count': hv.months})
                  : context.t('learn.hour.source.MANUAL'),
            }),
          ),
          Hint(
            '${context.t('learn.hour.monthly', {'time': showMinutes(context, hv.monthlyMinutes)})} · '
            '${context.t('learn.hour.computedOn', {'date': showDate(hv.computedOn)})}',
          ),
          if (hv.overCeiling) ...[const SizedBox(height: 8), Hint(context.t('learn.hour.ceiling'))],
        ],
        const SizedBox(height: 12),
        Text(context.t('mfl.hour.months'), style: const TextStyle(fontWeight: FontWeight.w600)),
        if (s != null && s.months.isEmpty) Hint(context.t('mfl.hour.noMonths')),
        if (s != null)
          for (final m in s.months)
            Padding(
              key: ValueKey(('mfl-month', m.periodStart)),
              padding: const EdgeInsets.only(top: 4),
              child: Text(
                context.t('mfl.hour.monthLine', {
                  'period': context.t('kk.period', {'from': showDate(m.periodStart), 'to': showDate(m.periodEnd)}),
                  'total': m.total.formatted,
                }),
              ),
            ),
        const SizedBox(height: 12),
        AmountField(
          label: context.t('mfl.hour.incomeField', {'currency': widget.data.workCurrency}),
          controller: _income,
        ),
        if (s?.average != null) ...[
          const SizedBox(height: 4),
          Hint(context.t('learn.hour.suggest', {'count': s!.months.length, 'average': s.average!.formatted})),
        ],
        const SizedBox(height: 8),
        Row(
          children: [
            Expanded(
              child: Field(
                label: context.t('learn.hour.hours'),
                controller: _hours,
                keyboardType: TextInputType.number,
              ),
            ),
            const SizedBox(width: 12),
            Expanded(
              child: Field(
                label: context.t('learn.hour.minutes'),
                controller: _minutes,
                keyboardType: TextInputType.number,
              ),
            ),
          ],
        ),
        const SizedBox(height: 8),
        Field(label: context.t('learn.hour.days'), controller: _days, keyboardType: TextInputType.number),
        ErrorText(error),
        const SizedBox(height: 8),
        FilledButton(onPressed: busy ? null : _save, child: Text(context.t('learn.hour.save'))),
      ],
    );
  }
}

/// Uy valyutasidagi ko'rinish: faqat kurs bilan; kurs yo'q — qiymat yo'q, eski — ogohlantirish.
class _HomeView extends StatelessWidget {
  const _HomeView(this.h);

  final MfHourHomeDto h;

  @override
  Widget build(BuildContext context) {
    final p = context.palette;
    final r = h.rate;
    return Container(
      key: const Key('mfl-hour-home'),
      margin: const EdgeInsets.symmetric(vertical: 8),
      padding: const EdgeInsets.all(12),
      decoration: BoxDecoration(
        border: Border.all(color: p.line),
        borderRadius: BorderRadius.circular(10),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: [
          Hint(context.t('mfl.hour.home')),
          if (h.hourValue != null && h.doubleTarget != null && h.rateStatus != 'SAME_CURRENCY')
            Text(
              context.t('mfl.hour.homeValue', {'value': h.hourValue!.formatted, 'double': h.doubleTarget!.formatted}),
              style: const TextStyle(fontWeight: FontWeight.w600),
            ),
          if (r != null && !r.identity)
            Hint(
              context.t('mf.rateLine', {
                'from': r.fromCurrency,
                'rate': r.rate,
                'to': r.toCurrency,
                'date': showDate(r.rateOn),
              }),
            ),
          if (h.rateStatus != 'FRESH')
            Hint(
              context.t('mfl.hour.rate.${h.rateStatus}'),
              color: h.rateStatus == 'STALE' ? p.warn : null,
            ),
        ],
      ),
    );
  }
}

/// Reja kartasi: maqsad, holat, byudjet (ish valyutasida), boshlang'ich nuqta va natijani o'lchash.
class _PlanCard extends ConsumerStatefulWidget {
  const _PlanCard({required this.spaceId, required this.plan, super.key});

  final String spaceId;
  final MfLearningPlanDto plan;

  @override
  ConsumerState<_PlanCard> createState() => _PlanCardState();
}

class _PlanCardState extends ConsumerState<_PlanCard> with ActionState {
  MfLearningResultDto? _result;

  Future<void> _status(String to) => act(
    () => ref.read(coreProvider).mfLearningPlanSetStatus(spaceId: widget.spaceId, planId: widget.plan.id, status: to),
  );

  Future<void> _measure() async {
    setState(() => _result = null);
    final r = await act(
      () => ref.read(coreProvider).mfLearningPlanResult(spaceId: widget.spaceId, planId: widget.plan.id),
    );
    if (r != null) setState(() => _result = r);
  }

  @override
  Widget build(BuildContext context) {
    final pl = widget.plan;
    final p = context.palette;
    final open = pl.status == 'ACTIVE' || pl.status == 'PAUSED';
    final statusColor = switch (pl.status) {
      'ACTIVE' => p.accentText,
      'PAUSED' => p.warn,
      _ => p.inkMuted,
    };
    final result = _result;
    return SectionCard(
      title: pl.skill,
      semanticLabel: context.t('mfl.plan.label', {'skill': pl.skill}),
      trailing: Text(
        context.t('learn.status.${pl.status}'),
        key: const Key('mfl-plan-status'),
        style: TextStyle(color: statusColor, fontWeight: FontWeight.w700),
      ),
      children: [
        Text(
          '${context.t('mfl.goalShort.${pl.goal}')} — ${context.t('mfl.goal.${pl.goal}')}',
          key: const Key('mfl-plan-goal'),
          style: TextStyle(color: p.accentText),
        ),
        if (pl.purpose != null) Text(pl.purpose!),
        Hint(
          '${pl.paths.map((x) => context.t('learn.path.$x')).join(', ')} · '
          '${context.t('learn.plan.dates', {'start': showDate(pl.startOn), 'review': showDate(pl.reviewOn)})}',
        ),
        const SizedBox(height: 6),
        Text(context.t('learn.plan.weeklyTarget', {'time': showMinutes(context, pl.weeklyMinutes)})),
        if (pl.budget != null) Text(context.t('mfl.plan.budgetLine', {'budget': pl.budget!.formatted})),
        Text(
          pl.baselineHourValue != null
              ? context.t('learn.plan.baseline', {'value': pl.baselineHourValue!.formatted})
              : context.t('learn.plan.noBaseline'),
        ),
        if (pl.resultHourValue != null)
          Text(context.t('learn.plan.lastResult', {'value': pl.resultHourValue!.formatted})),
        if (pl.ventureIdeaTitle != null)
          Text(context.t('mfl.plan.ideaLine', {'title': pl.ventureIdeaTitle}), key: const Key('mfl-plan-idea')),
        if (pl.reviewDue) Text(context.t('learn.plan.reviewDue'), style: TextStyle(color: p.accentText)),
        if (pl.courseCheckSuggested && open) ...[
          const SizedBox(height: 6),
          Hint(context.t('learn.plan.courseHint')),
          Align(
            alignment: Alignment.centerLeft,
            child: OutlinedButton(
              onPressed: () => openOfferCheck(context, mode: 'COURSE', askJobAbroad: true),
              child: Text(context.t('learn.plan.checkCourse')),
            ),
          ),
        ],
        ErrorText(error),
        if (result != null) _ResultView(result),
        Wrap(
          spacing: 8,
          runSpacing: 8,
          children: [
            OutlinedButton(onPressed: busy ? null : _measure, child: Text(context.t('learn.result.measure'))),
            for (final to in _next[pl.status] ?? const <String>[])
              TextButton(onPressed: busy ? null : () => _status(to), child: Text(context.t('learn.action.$to'))),
          ],
        ),
      ],
    );
  }
}

/// Natija (Uy 2G.5 kabi): pasaysa yoki o'zgarmasa ham uyaltirilmaydi; o'sish va'da qilinmaydi.
class _ResultView extends StatelessWidget {
  const _ResultView(this.r);

  final MfLearningResultDto r;

  @override
  Widget build(BuildContext context) {
    final baseline = r.baseline;
    final diff = r.diff;
    final up = r.changeBp != null ? r.changeBp! > 0 : diff != null && diff.minor != '0' && !diff.minor.startsWith('-');
    return Semantics(
      liveRegion: true,
      child: Container(
        key: const Key('plan-result'),
        margin: const EdgeInsets.symmetric(vertical: 8),
        padding: const EdgeInsets.all(12),
        decoration: BoxDecoration(
          border: Border.all(color: context.palette.line),
          borderRadius: BorderRadius.circular(10),
        ),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.stretch,
          children: [
            Text(
              baseline != null
                  ? context.t('learn.result.line', {
                      'baseline': baseline.hourValue.formatted,
                      'current': r.current.hourValue.formatted,
                    })
                  : context.t('learn.result.currentOnly', {'current': r.current.hourValue.formatted}),
              style: const TextStyle(fontWeight: FontWeight.w700),
            ),
            if (baseline == null) Hint(context.t('learn.result.noBaseline')),
            if (baseline != null && diff != null)
              Text(
                r.changePercent != null
                    ? context.t('learn.result.diff', {'diff': diff.formatted, 'percent': r.changePercent})
                    : context.t('learn.result.diffOnly', {'diff': diff.formatted}),
              ),
            if (baseline != null) Hint(context.t(up ? 'learn.result.up' : 'learn.result.flat')),
          ],
        ),
      ),
    );
  }
}

/// «Ilm zakoti»: shu oy hamyurtlarga ish, til yoki hujjat bo'yicha yordam va boshqa o'rgatishlar.
class _TeachingCard extends StatelessWidget {
  const _TeachingCard({required this.spaceId, required this.data});

  final String spaceId;
  final MfLearningOverviewDto data;

  @override
  Widget build(BuildContext context) => SectionCard(
    title: context.t('learn.teach.title'),
    trailing: TextButton(
      onPressed: () => showSheet<void>(context, (_) => MfTeachingSheet(spaceId: spaceId)),
      child: Text(context.t('learn.teach.add')),
    ),
    children: [
      Hint(context.t('mfl.teach.hint')),
      const SizedBox(height: 8),
      Text(
        context.t('learn.teach.count', {'count': data.teachingCount}),
        key: const Key('mfl-teach-count'),
        style: const TextStyle(fontWeight: FontWeight.w700),
      ),
      if (data.teaching.isEmpty) Hint(context.t('learn.teach.empty')),
      for (final r in data.teaching)
        Padding(
          key: ValueKey(('mfl-teach', r.id)),
          padding: const EdgeInsets.only(top: 8),
          child: Text(
            [
              showDate(r.occurredOn),
              context.t('mfl.area.${r.area}'),
              r.topic,
              if (r.learner != null) context.t('learn.teach.to', {'learner': r.learner}),
              if (r.minutes != null) showMinutes(context, r.minutes!),
            ].join(' · '),
          ),
        ),
    ],
  );
}

/// Yangi reja: maqsad (chet elda / uyda), uyda — ixtiyoriy «Hunardan ishga» g'oyasi (standart — ish
/// boshlash summasiga bog'langani). Faol rejalar chegarasini yadro tekshiradi.
class MfPlanSheet extends ConsumerStatefulWidget {
  const MfPlanSheet({required this.spaceId, required this.data, super.key});

  final String spaceId;
  final MfLearningOverviewDto data;

  @override
  ConsumerState<MfPlanSheet> createState() => _MfPlanSheetState();
}

class _MfPlanSheetState extends ConsumerState<MfPlanSheet> with ActionState {
  String _goal = 'ABROAD';
  late String _idea = widget.data.startupIdeaId ?? '';
  final _skill = TextEditingController();
  final _purpose = TextEditingController();
  final _budget = TextEditingController();
  final _hours = TextEditingController();
  final _minutes = TextEditingController();
  final _paths = <String>[];
  String? _start;
  String? _review;

  @override
  void dispose() {
    for (final c in [_skill, _purpose, _budget, _hours, _minutes]) {
      c.dispose();
    }
    super.dispose();
  }

  Future<void> _create() async {
    final home = _goal == 'HOME';
    final r = await act(
      () => ref
          .read(coreProvider)
          .mfLearningPlanCreate(
            spaceId: widget.spaceId,
            input: MfLearningPlanInput(
              goal: _goal,
              skill: _skill.text,
              purpose: _purpose.text.trim().isEmpty ? null : _purpose.text,
              paths: List.of(_paths),
              budget: _budget.text.trim().isEmpty ? null : _budget.text,
              weeklyMinutes: toMinutes(_hours.text, _minutes.text),
              startOn: _start,
              reviewOn: _review,
              ventureIdeaId: home && _idea.isNotEmpty ? _idea : null,
            ),
          ),
    );
    if (r != null && mounted) Navigator.of(context).pop();
  }

  @override
  Widget build(BuildContext context) {
    final d = widget.data;
    return SingleChildScrollView(
      padding: const EdgeInsets.fromLTRB(20, 0, 20, 20),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: [
          Semantics(
            header: true,
            child: Text(
              context.t('learn.plan.dialog'),
              style: const TextStyle(fontSize: 20, fontWeight: FontWeight.w700),
            ),
          ),
          const SizedBox(height: 12),
          SegmentedChoice<String>(
            label: context.t('mfl.plan.goal'),
            options: [for (final g in mfGoals) (g, context.t('mfl.goalShort.$g'))],
            value: _goal,
            onChanged: (v) => setState(() => _goal = v),
          ),
          const SizedBox(height: 4),
          Text(context.t('mfl.goal.$_goal')),
          Hint(context.t('mfl.goalHint.$_goal')),
          const SizedBox(height: 8),
          Field(label: context.t('learn.plan.skill'), hint: context.t('mfl.plan.skillPlaceholder'), controller: _skill),
          const SizedBox(height: 8),
          Field(label: context.t('learn.plan.purpose'), controller: _purpose),
          if (_goal == 'HOME' && d.ideas.isNotEmpty) ...[
            const SizedBox(height: 8),
            Select<String>(
              key: const Key('mfl-plan-idea-select'),
              label: context.t('mfl.plan.idea'),
              items: [('', context.t('mfl.plan.noIdea')), for (final i in d.ideas) (i.id, i.title)],
              value: _idea,
              onChanged: (v) => setState(() => _idea = v ?? ''),
            ),
          ],
          const SizedBox(height: 12),
          Text(context.t('learn.plan.paths')),
          for (final x in learningPaths)
            CheckboxListTile(
              contentPadding: EdgeInsets.zero,
              dense: true,
              value: _paths.contains(x),
              title: Text(context.t('learn.path.$x')),
              onChanged: (on) => setState(() => on ?? false ? _paths.add(x) : _paths.remove(x)),
            ),
          if (_paths.contains('COURSE')) Hint(context.t('learn.plan.courseHint')),
          const SizedBox(height: 8),
          AmountField(label: context.t('mfl.plan.budget', {'currency': d.workCurrency}), controller: _budget),
          const SizedBox(height: 8),
          Row(
            children: [
              Expanded(
                child: Field(
                  label: context.t('learn.plan.weeklyHours'),
                  controller: _hours,
                  keyboardType: TextInputType.number,
                ),
              ),
              const SizedBox(width: 12),
              Expanded(
                child: Field(
                  label: context.t('learn.plan.weeklyMinutes'),
                  controller: _minutes,
                  keyboardType: TextInputType.number,
                ),
              ),
            ],
          ),
          const SizedBox(height: 8),
          DateField(label: context.t('learn.plan.start'), value: _start, onChanged: (v) => setState(() => _start = v)),
          const SizedBox(height: 8),
          DateField(
            label: context.t('learn.plan.review'),
            value: _review,
            onChanged: (v) => setState(() => _review = v),
          ),
          const SizedBox(height: 8),
          Hint(context.t('mfl.plans.hint')),
          ErrorText(error),
          const SizedBox(height: 12),
          Wrap(
            spacing: 8,
            children: [
              FilledButton(onPressed: busy ? null : _create, child: Text(context.t('learn.plan.create'))),
              TextButton(onPressed: () => Navigator.of(context).pop(), child: Text(context.t('common.cancel'))),
            ],
          ),
        ],
      ),
    );
  }
}

/// «Ilm zakoti» yozuvi: soha (ish, til, hujjatlar, boshqa), nimani, kimga (ixtiyoriy), qancha vaqt.
class MfTeachingSheet extends ConsumerStatefulWidget {
  const MfTeachingSheet({required this.spaceId, super.key});

  final String spaceId;

  @override
  ConsumerState<MfTeachingSheet> createState() => _MfTeachingSheetState();
}

class _MfTeachingSheetState extends ConsumerState<MfTeachingSheet> with ActionState {
  String _area = 'WORK';
  final _topic = TextEditingController();
  final _learner = TextEditingController();
  final _minutes = TextEditingController();
  String? _date;

  @override
  void dispose() {
    for (final c in [_topic, _learner, _minutes]) {
      c.dispose();
    }
    super.dispose();
  }

  Future<void> _save() async {
    final r = await act(
      () => ref
          .read(coreProvider)
          .mfTeachingAdd(
            spaceId: widget.spaceId,
            input: MfTeachingInput(
              occurredOn: _date,
              area: _area,
              learner: _learner.text.trim().isEmpty ? null : _learner.text,
              topic: _topic.text,
              minutes: _minutes.text.trim().isEmpty ? null : parseCount(_minutes.text, 4),
            ),
          ),
    );
    if (r != null && mounted) Navigator.of(context).pop();
  }

  @override
  Widget build(BuildContext context) => SingleChildScrollView(
    padding: const EdgeInsets.fromLTRB(20, 0, 20, 20),
    child: Column(
      crossAxisAlignment: CrossAxisAlignment.stretch,
      children: [
        Semantics(
          header: true,
          child: Text(
            context.t('learn.teach.dialog'),
            style: const TextStyle(fontSize: 20, fontWeight: FontWeight.w700),
          ),
        ),
        const SizedBox(height: 8),
        Hint(context.t('mfl.teach.hint')),
        const SizedBox(height: 12),
        SegmentedChoice<String>(
          label: context.t('mfl.teach.area'),
          options: [for (final a in mfAreas) (a, context.t('mfl.area.$a'))],
          value: _area,
          onChanged: (v) => setState(() => _area = v),
        ),
        const SizedBox(height: 8),
        Field(label: context.t('learn.teach.topic'), controller: _topic),
        const SizedBox(height: 8),
        Field(label: context.t('mfl.teach.learner'), controller: _learner),
        const SizedBox(height: 8),
        Field(label: context.t('learn.teach.minutes'), controller: _minutes, keyboardType: TextInputType.number),
        const SizedBox(height: 8),
        DateField(label: context.t('learn.teach.date'), value: _date, onChanged: (v) => setState(() => _date = v)),
        ErrorText(error),
        const SizedBox(height: 12),
        Wrap(
          spacing: 8,
          children: [
            FilledButton(onPressed: busy ? null : _save, child: Text(context.t('common.save'))),
            TextButton(onPressed: () => Navigator.of(context).pop(), child: Text(context.t('common.cancel'))),
          ],
        ),
      ],
    ),
  );
}
