import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../app/i18n.dart';
import '../../app/theme.dart';
import '../../core/core.dart';
import '../../core/query.dart';
import '../../shared/format.dart';
import '../../shared/widgets.dart';
import '../venture/offer_check.dart';

const learningPaths = ['BOOK', 'MENTOR', 'COURSE', 'PRACTICE'];

/// Holat o'tishlari tugmalari (yadro `transition` qoidasi bilan bir xil; yopilgan reja — tugmasiz).
const _next = {
  'ACTIVE': ['PAUSED', 'DONE', 'DROPPED'],
  'PAUSED': ['ACTIVE', 'DONE', 'DROPPED'],
};

/// Butun son maydoni: faqat raqamlar, ko'pi bilan `maxDigits` ta. Noto'g'ri — 0 (yadro tegishli
/// xatoni qaytaradi: `INVALID_TIME`, `INVALID_WORK_DAYS`). Desktop `learning/time.ts` bilan bir xil.
int parseCount(String s, int maxDigits) {
  final v = s.trim();
  return RegExp('^\\d{1,$maxDigits}\$').hasMatch(v) ? int.parse(v) : 0;
}

/// Soat (≤ 3 raqam) va daqiqa (0–59) maydonlari → butun daqiqa (vaqt, pul emas). Bo'sh maydon — 0;
/// noto'g'ri qiymat — hammasi 0: yadro `INVALID_TIME` qaytaradi. Desktop bilan bir xil.
int toMinutes(String hours, String minutes) {
  final h = hours.trim();
  final m = minutes.trim();
  if ((h.isNotEmpty && !RegExp(r'^\d{1,3}$').hasMatch(h)) || (m.isNotEmpty && !RegExp(r'^\d{1,2}$').hasMatch(m))) {
    return 0;
  }
  final mm = m.isEmpty ? 0 : int.parse(m);
  if (mm > 59) return 0;
  return (h.isEmpty ? 0 : int.parse(h)) * 60 + mm;
}

/// Daqiqani «2 soat 30 daqiqa» ko'rinishida.
String showMinutes(BuildContext context, int total) {
  final h = total ~/ 60;
  final m = total % 60;
  if (h > 0 && m > 0) return context.t('learn.duration.hm', {'h': h, 'm': m});
  if (h > 0) return context.t('learn.duration.h', {'h': h});
  return context.t('learn.duration.m', {'m': m});
}

/// O'zimga sarmoya ma'lumoti (xarajat formasi ham shu so'rovdan foydalanadi).
ProviderListenable<AsyncValue<LearningOverviewDto>> learningQuery(String spaceId) =>
    query(['learning', spaceId], (c) => c.learningOverview(spaceId: spaceId));

/// «O'zimga sarmoya» (8-tamoyil, uy/SPEC 2G): «Bir soatim qancha?», bilim rejalari, «Ilm zakoti» va
/// oylik «O'zimga sarmoya» qatori. Barcha summa va foizlar yadrodan; UI faqat ko'rsatadi.
class LearningScreen extends ConsumerWidget {
  const LearningScreen({required this.spaceId, super.key});

  final String spaceId;

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final o = ref.watch(learningQuery(spaceId));
    final d = o.valueOrNull;
    final p = context.palette;
    final names = {for (final m in d?.members ?? <LearningMemberDto>[]) m.memberId: m.displayName};
    return ScreenBody(
      mentorKey: 'mentor.learning',
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
                Text(context.t('learn.intro')),
                const SizedBox(height: 8),
                Hint(context.t('learn.example')),
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
                child: Text('$n. ${context.t('learn.tasks.$n')}'),
              ),
          ],
        ),
        if (o.hasError) ErrorText(o.error),
        if (d != null) _SelfInvestmentCard(d.selfInvestment),
        if (d != null)
          for (final m in d.members) _HourCard(key: ValueKey(('hour', m.memberId)), spaceId: spaceId, member: m),
        if (d != null)
          SectionCard(
            title: context.t('learn.plans.title'),
            trailing: TextButton(
              onPressed: () => showSheet<void>(context, (_) => PlanSheet(spaceId: spaceId, members: d.members)),
              child: Text(context.t('learn.plans.new')),
            ),
            children: [
              Hint(context.t('learn.plan.money')),
              if (d.plans.isEmpty) ...[const SizedBox(height: 8), Hint(context.t('learn.plans.empty'))],
            ],
          ),
        if (d != null)
          for (final pl in d.plans)
            _PlanCard(key: ValueKey(('plan', pl.id)), spaceId: spaceId, plan: pl, memberName: names[pl.memberId] ?? ''),
        if (d != null) _TeachingCard(spaceId: spaceId, data: d, names: names),
      ],
    );
  }
}

class _SelfInvestmentCard extends StatelessWidget {
  const _SelfInvestmentCard(this.s);

  final SelfInvestmentDto s;

  @override
  Widget build(BuildContext context) => Kpi(
    key: const Key('learn-self-investment'),
    label: context.t('learn.selfInvestment.title'),
    value: s.sharePercent == null
        ? context.t('learn.selfInvestment.noIncome', {'total': s.total.formatted})
        : context.t('learn.selfInvestment.line', {'total': s.total.formatted, 'percent': s.sharePercent}),
    hint: context.t('learn.selfInvestment.hint'),
  );
}

/// «Bir soatim qancha?» (2G.1): oxirgi hisob, taklif (AUTO) yoki qo'lda daromad, ish vaqti.
class _HourCard extends ConsumerStatefulWidget {
  const _HourCard({required this.spaceId, required this.member, super.key});

  final String spaceId;
  final LearningMemberDto member;

  @override
  ConsumerState<_HourCard> createState() => _HourCardState();
}

class _HourCardState extends ConsumerState<_HourCard> with ActionState {
  late final HourValueDto? _hv = widget.member.hourValue;
  late final _income = TextEditingController(text: _hv?.incomeSource == 'MANUAL' ? _hv?.income.plain : '');
  late final _hours = TextEditingController(text: '${(_hv?.minutesPerDay ?? 480) ~/ 60}');
  late final _minutes = TextEditingController(text: '${(_hv?.minutesPerDay ?? 480) % 60}');
  late final _days = TextEditingController(text: '${_hv?.days ?? 22}');

  @override
  void dispose() {
    for (final c in [_income, _hours, _minutes, _days]) {
      c.dispose();
    }
    super.dispose();
  }

  Future<void> _save() async {
    final days = parseCount(_days.text, 2);
    await act(
      () => ref
          .read(coreProvider)
          .hourValueSave(
            spaceId: widget.spaceId,
            input: HourValueInput(
              memberId: widget.member.memberId,
              income: _income.text.trim().isEmpty ? null : _income.text,
              minutesPerDay: toMinutes(_hours.text, _minutes.text),
              days: days,
            ),
          ),
    );
  }

  @override
  Widget build(BuildContext context) {
    final m = widget.member;
    final hv = m.hourValue;
    final id = widget.spaceId;
    final suggest = ref
        .watch(query(['hourSuggest', id, m.memberId], (c) => c.hourValueSuggest(spaceId: id, memberId: m.memberId)))
        .valueOrNull;
    final p = context.palette;
    return SectionCard(
      title: context.t('learn.hour.cardLabel', {'name': m.displayName}),
      children: [
        if (hv == null)
          Hint(context.t('learn.hour.none'))
        else ...[
          Text(context.t('learn.hour.value'), style: TextStyle(color: p.inkMuted)),
          Text(
            hv.hourValue.formatted,
            key: const Key('hour-value'),
            style: TextStyle(fontSize: 26, fontWeight: FontWeight.w700, color: p.accent),
          ),
          ValueRow(context.t('learn.hour.double'), hv.doubleTarget.formatted, strong: true),
          Text(
            context.t('learn.hour.income', {
              'amount': hv.income.formatted,
              'source': context.t('learn.hour.source.${hv.incomeSource}'),
            }),
          ),
          Hint(
            '${context.t('learn.hour.monthly', {'time': showMinutes(context, hv.monthlyMinutes)})} · '
            '${context.t('learn.hour.computedOn', {'date': showDate(hv.computedOn)})}',
          ),
          if (hv.overCeiling) ...[
            const SizedBox(height: 8),
            Container(
              key: const Key('hour-ceiling'),
              padding: const EdgeInsets.all(12),
              decoration: BoxDecoration(
                color: p.sidebar,
                borderRadius: BorderRadius.circular(10),
                border: Border.all(color: p.line),
              ),
              child: Text.rich(
                TextSpan(
                  children: [
                    TextSpan(
                      text: '${context.t('mentor.name')}: ',
                      style: TextStyle(color: p.accentText, fontWeight: FontWeight.w700),
                    ),
                    TextSpan(text: context.t('learn.hour.ceiling')),
                  ],
                ),
              ),
            ),
          ],
        ],
        const SizedBox(height: 12),
        AmountField(label: context.t('learn.hour.incomeField'), controller: _income),
        const SizedBox(height: 4),
        Hint(
          suggest?.average != null
              ? context.t('learn.hour.suggest', {
                  'count': suggest!.months.length,
                  'average': suggest.average!.formatted,
                })
              : context.t('learn.hour.noSuggest'),
        ),
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

/// Bilim rejasi kartasi (2G.2, 2G.5): holat, o'qish vaqti, byudjet va sarflangani, natijani o'lchash.
class _PlanCard extends ConsumerStatefulWidget {
  const _PlanCard({required this.spaceId, required this.plan, required this.memberName, super.key});

  final String spaceId;
  final LearningPlanDto plan;
  final String memberName;

  @override
  ConsumerState<_PlanCard> createState() => _PlanCardState();
}

class _PlanCardState extends ConsumerState<_PlanCard> with ActionState {
  final _hours = TextEditingController();
  final _minutes = TextEditingController();
  LearningResultDto? _result;

  @override
  void dispose() {
    _hours.dispose();
    _minutes.dispose();
    super.dispose();
  }

  Future<void> _status(String to) => act(
    () => ref.read(coreProvider).learningPlanSetStatus(spaceId: widget.spaceId, planId: widget.plan.id, status: to),
  );

  Future<void> _study() async {
    final r = await act(
      () => ref
          .read(coreProvider)
          .studyLogAdd(
            spaceId: widget.spaceId,
            planId: widget.plan.id,
            input: StudyLogInput(minutes: toMinutes(_hours.text, _minutes.text)),
          ),
    );
    if (r != null) {
      _hours.clear();
      _minutes.clear();
    }
  }

  Future<void> _measure() async {
    setState(() => _result = null);
    final r = await act(
      () => ref.read(coreProvider).learningPlanResult(spaceId: widget.spaceId, planId: widget.plan.id),
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
      semanticLabel: context.t('learn.plan.cardLabel', {'skill': pl.skill}),
      trailing: Text(
        context.t('learn.status.${pl.status}'),
        key: const Key('plan-status'),
        style: TextStyle(color: statusColor, fontWeight: FontWeight.w700),
      ),
      children: [
        Hint(widget.memberName),
        if (pl.purpose != null) Text(pl.purpose!),
        Hint(
          '${pl.paths.map((x) => context.t('learn.path.$x')).join(', ')} · '
          '${context.t('learn.plan.dates', {'start': showDate(pl.startOn), 'review': showDate(pl.reviewOn)})}',
        ),
        const SizedBox(height: 6),
        Text(context.t('learn.plan.weeklyTarget', {'time': showMinutes(context, pl.weeklyMinutes)})),
        Text(context.t('learn.plan.studied', {'time': showMinutes(context, pl.studyMinutes)})),
        Text(
          pl.budget != null
              ? context.t('learn.plan.budgetLine', {'budget': pl.budget!.formatted, 'spent': pl.spent.formatted})
              : context.t('learn.plan.spentLine', {'spent': pl.spent.formatted}),
        ),
        Text(
          pl.baselineHourValue != null
              ? context.t('learn.plan.baseline', {'value': pl.baselineHourValue!.formatted})
              : context.t('learn.plan.noBaseline'),
        ),
        if (pl.resultHourValue != null)
          Text(context.t('learn.plan.lastResult', {'value': pl.resultHourValue!.formatted})),
        if (pl.reviewDue) Text(context.t('learn.plan.reviewDue'), style: TextStyle(color: p.accentText)),
        if (pl.courseCheckSuggested && open) ...[
          const SizedBox(height: 6),
          Hint(context.t('learn.plan.courseHint')),
          Align(
            alignment: Alignment.centerLeft,
            child: OutlinedButton(
              onPressed: () => openOfferCheck(context, mode: 'COURSE'),
              child: Text(context.t('learn.plan.checkCourse')),
            ),
          ),
        ],
        if (open) ...[
          const SizedBox(height: 10),
          Text(context.t('learn.study.title'), style: const TextStyle(fontWeight: FontWeight.w700)),
          Row(
            children: [
              Expanded(
                child: Field(
                  label: context.t('learn.study.hours'),
                  controller: _hours,
                  keyboardType: TextInputType.number,
                ),
              ),
              const SizedBox(width: 12),
              Expanded(
                child: Field(
                  label: context.t('learn.study.minutes'),
                  controller: _minutes,
                  keyboardType: TextInputType.number,
                ),
              ),
            ],
          ),
          Align(
            alignment: Alignment.centerLeft,
            child: TextButton(onPressed: busy ? null : _study, child: Text(context.t('learn.study.add'))),
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

/// Natija (2G.5): pasaysa yoki o'zgarmasa ham uyaltirilmaydi.
class _ResultView extends StatelessWidget {
  const _ResultView(this.r);

  final LearningResultDto r;

  @override
  Widget build(BuildContext context) {
    final baseline = r.baseline;
    // Belgi yadro bergan bazis punktdan (yo'q bo'lsa — farq matnidan); UI hech narsa hisoblamaydi.
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
            // Boshlang'ich nuqta yo'q — solishtirib bo'lmaydi: betaraf izoh, «o'sish yo'q» emas.
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

/// «Ilm zakoti» (2G.6): shu oydagi o'rgatish yozuvlari va ularning soni. Pul hisobi yo'q.
class _TeachingCard extends StatelessWidget {
  const _TeachingCard({required this.spaceId, required this.data, required this.names});

  final String spaceId;
  final LearningOverviewDto data;
  final Map<String, String> names;

  @override
  Widget build(BuildContext context) => SectionCard(
    title: context.t('learn.teach.title'),
    trailing: TextButton(
      onPressed: () => showSheet<void>(context, (_) => TeachingSheet(spaceId: spaceId, members: data.members)),
      child: Text(context.t('learn.teach.add')),
    ),
    children: [
      Hint(context.t('learn.teach.hint')),
      const SizedBox(height: 8),
      Text(
        context.t('learn.teach.count', {'count': data.teachingCount}),
        key: const Key('teach-count'),
        style: const TextStyle(fontWeight: FontWeight.w700),
      ),
      if (data.teaching.isEmpty) Hint(context.t('learn.teach.empty')),
      for (final r in data.teaching)
        Padding(
          key: ValueKey(('teach', r.id)),
          padding: const EdgeInsets.only(top: 8),
          child: Text(
            [
              showDate(r.occurredOn),
              r.topic,
              names[r.memberId] ?? '',
              if (r.learner != null) context.t('learn.teach.to', {'learner': r.learner}),
              if (r.minutes != null) showMinutes(context, r.minutes!),
            ].where((s) => s.isNotEmpty).join(' · '),
          ),
        ),
    ],
  );
}

/// Yangi bilim rejasi (2G.2): bir a'zoda ko'pi bilan 2 ta faol reja — chegarani yadro tekshiradi.
class PlanSheet extends ConsumerStatefulWidget {
  const PlanSheet({required this.spaceId, required this.members, super.key});

  final String spaceId;
  final List<LearningMemberDto> members;

  @override
  ConsumerState<PlanSheet> createState() => _PlanSheetState();
}

class _PlanSheetState extends ConsumerState<PlanSheet> with ActionState {
  late String? _member = widget.members.firstOrNull?.memberId;
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
    final r = await act(
      () => ref
          .read(coreProvider)
          .learningPlanCreate(
            spaceId: widget.spaceId,
            input: LearningPlanInput(
              memberId: _member ?? '',
              skill: _skill.text,
              purpose: _purpose.text.trim().isEmpty ? null : _purpose.text,
              paths: List.of(_paths),
              budget: _budget.text.trim().isEmpty ? null : _budget.text,
              weeklyMinutes: toMinutes(_hours.text, _minutes.text),
              startOn: _start,
              reviewOn: _review,
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
            context.t('learn.plan.dialog'),
            style: const TextStyle(fontSize: 20, fontWeight: FontWeight.w700),
          ),
        ),
        const SizedBox(height: 12),
        if (widget.members.length > 1) ...[
          Select<String>(
            label: context.t('learn.plan.member'),
            items: [for (final m in widget.members) (m.memberId, m.displayName)],
            value: _member,
            onChanged: (v) => setState(() => _member = v),
          ),
          const SizedBox(height: 8),
        ],
        Field(label: context.t('learn.plan.skill'), hint: context.t('learn.plan.skillPlaceholder'), controller: _skill),
        const SizedBox(height: 8),
        Field(label: context.t('learn.plan.purpose'), controller: _purpose),
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
        AmountField(label: context.t('learn.plan.budget'), controller: _budget),
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
        DateField(label: context.t('learn.plan.review'), value: _review, onChanged: (v) => setState(() => _review = v)),
        const SizedBox(height: 8),
        Hint(context.t('learn.plan.money')),
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

/// «Ilm zakoti» yozuvi (2G.6): kimga (ixtiyoriy), nimani, qancha vaqt.
class TeachingSheet extends ConsumerStatefulWidget {
  const TeachingSheet({required this.spaceId, required this.members, super.key});

  final String spaceId;
  final List<LearningMemberDto> members;

  @override
  ConsumerState<TeachingSheet> createState() => _TeachingSheetState();
}

class _TeachingSheetState extends ConsumerState<TeachingSheet> with ActionState {
  late String? _member = widget.members.firstOrNull?.memberId;
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
          .teachingLogAdd(
            spaceId: widget.spaceId,
            input: TeachingLogInput(
              memberId: _member ?? '',
              occurredOn: _date,
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
        Hint(context.t('learn.teach.hint')),
        const SizedBox(height: 12),
        if (widget.members.length > 1) ...[
          Select<String>(
            label: context.t('learn.teach.member'),
            items: [for (final m in widget.members) (m.memberId, m.displayName)],
            value: _member,
            onChanged: (v) => setState(() => _member = v),
          ),
          const SizedBox(height: 8),
        ],
        Field(label: context.t('learn.teach.topic'), controller: _topic),
        const SizedBox(height: 8),
        Field(label: context.t('learn.teach.learner'), controller: _learner),
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
