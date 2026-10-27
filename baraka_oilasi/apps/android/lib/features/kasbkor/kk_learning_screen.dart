import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../app/i18n.dart';
import '../../app/theme.dart';
import '../../core/core.dart';
import '../../core/query.dart';
import '../../shared/format.dart';
import '../../shared/widgets.dart';
import '../learning/learning_screen.dart' show parseCount, showMinutes, toMinutes;
import '../venture/offer_check.dart';

/// Kasb-kor «O'zimga sarmoya» (8-tamoyil, kasbkor/SPEC 8A): egasining bir soati (yopilgan oylardan),
/// «O'zim qilaymi yoki o'rgatib topshiraymi?», «Ilm zakoti» (xodimga o'rgatish), kurs tekshiruvi va
/// «Sarmoya (o'qish)» qatori. Egasi bo'limi — sotuvchi menyusida yo'q (soat qiymati foydadan).
/// Barcha summa yadrodan; UI faqat ko'rsatadi. Desktop `KkLearningScreen.tsx` bilan bir xil.
class KkLearningScreen extends ConsumerWidget {
  const KkLearningScreen({required this.spaceId, super.key});

  final String spaceId;

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final o = ref.watch(query(['kkLearning', spaceId], (c) => c.kkLearningOverview(spaceId: spaceId)));
    final d = o.valueOrNull;
    final p = context.palette;
    return ScreenBody(
      mentorKey: 'mentor.kkLearning',
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
                Text(context.t('kkl.intro')),
                const SizedBox(height: 8),
                Hint(context.t('kkl.example')),
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
                child: Text('$n. ${context.t('kkl.tasks.$n')}'),
              ),
          ],
        ),
        if (o.hasError) ErrorText(o.error),
        if (d != null)
          Kpi(
            key: const Key('kkl-self-investment'),
            label: context.t('kkl.invest.title'),
            value: d.selfInvestment.formatted,
            hint: context.t('kkl.invest.hint'),
          ),
        if (d != null) _OwnerHourCard(key: ValueKey(('kkl-hour', d.hourValue?.id)), spaceId: spaceId, hv: d.hourValue),
        if (d != null) _DelegateCard(spaceId: spaceId, data: d),
        if (d != null) _TeachingCard(spaceId: spaceId, data: d),
        SectionCard(
          title: context.t('kkl.course.title'),
          children: [
            Hint(context.t('kkl.course.hint')),
            const SizedBox(height: 8),
            Align(
              alignment: Alignment.centerLeft,
              child: OutlinedButton(
                onPressed: () => openOfferCheck(context, mode: 'COURSE'),
                child: Text(context.t('learn.plan.checkCourse')),
              ),
            ),
          ],
        ),
      ],
    );
  }
}

/// Egasining bir soati (8A.1): yopilgan oylar taklifi (AUTO) yoki qo'lda topgani va ish vaqti.
class _OwnerHourCard extends ConsumerStatefulWidget {
  const _OwnerHourCard({required this.spaceId, required this.hv, super.key});

  final String spaceId;
  final KkOwnerHourDto? hv;

  @override
  ConsumerState<_OwnerHourCard> createState() => _OwnerHourCardState();
}

class _OwnerHourCardState extends ConsumerState<_OwnerHourCard> with ActionState {
  late final KkOwnerHourDto? _hv = widget.hv;
  late final _income = TextEditingController(text: _hv?.incomeSource == 'MANUAL' ? _hv?.income.plain : '');
  late final _hours = TextEditingController(text: '${(_hv?.minutesPerDay ?? 600) ~/ 60}');
  late final _minutes = TextEditingController(text: '${(_hv?.minutesPerDay ?? 600) % 60}');
  late final _days = TextEditingController(text: '${_hv?.days ?? 26}');

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
          .kkOwnerHourSave(
            spaceId: widget.spaceId,
            input: KkOwnerHourInput(
              income: _income.text.trim().isEmpty ? null : _income.text,
              minutesPerDay: toMinutes(_hours.text, _minutes.text),
              days: parseCount(_days.text, 2),
            ),
          ),
    );
  }

  @override
  Widget build(BuildContext context) {
    final hv = widget.hv;
    final id = widget.spaceId;
    final s = ref.watch(query(['kkOwnerSuggest', id], (c) => c.kkOwnerHourSuggest(spaceId: id))).valueOrNull;
    final p = context.palette;
    return SectionCard(
      title: context.t('kkl.hour.title'),
      children: [
        if (hv == null)
          Hint(context.t('kkl.hour.none'))
        else ...[
          Text(context.t('learn.hour.value'), style: TextStyle(color: p.inkMuted)),
          Text(
            hv.hourValue.formatted,
            key: const Key('kkl-hour-value'),
            style: TextStyle(fontSize: 26, fontWeight: FontWeight.w700, color: p.accent),
          ),
          ValueRow(context.t('learn.hour.double'), hv.doubleTarget.formatted, strong: true),
          Text(
            context.t('kkl.hour.income', {
              'amount': hv.income.formatted,
              'source': hv.incomeSource == 'AUTO'
                  ? context.t('kkl.hour.source.AUTO', {'count': hv.months})
                  : context.t('kkl.hour.source.MANUAL'),
            }),
          ),
          Hint(
            '${context.t('learn.hour.monthly', {'time': showMinutes(context, hv.monthlyMinutes)})} · '
            '${context.t('learn.hour.computedOn', {'date': showDate(hv.computedOn)})}',
          ),
          if (hv.overCeiling) ...[const SizedBox(height: 8), Hint(context.t('learn.hour.ceiling'))],
        ],
        const SizedBox(height: 12),
        Text(context.t('kkl.hour.months'), style: const TextStyle(fontWeight: FontWeight.w600)),
        if (s != null && s.months.isEmpty) Hint(context.t('kkl.hour.noMonths')),
        if (s != null)
          for (final m in s.months)
            Padding(
              key: ValueKey(('kkl-month', m.periodStart)),
              padding: const EdgeInsets.only(top: 4),
              child: Text(
                context.t('kkl.hour.monthLine', {
                  'period': context.t('kk.period', {'from': showDate(m.periodStart), 'to': showDate(m.periodEnd)}),
                  'labor': m.ownerLabor.formatted,
                  'profit': m.trueProfit.formatted,
                  'earned': m.earnings.formatted,
                }),
              ),
            ),
        const SizedBox(height: 4),
        Hint(context.t('kkl.hour.salaryNote')),
        const SizedBox(height: 12),
        AmountField(label: context.t('kkl.hour.incomeField'), controller: _income),
        if (s?.average != null) ...[
          const SizedBox(height: 4),
          Hint(context.t('kkl.hour.suggest', {'count': s!.months.length, 'average': s.average!.formatted})),
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

/// «O'zim qilaymi yoki o'rgatib topshiraymi?» (8A.2): hisob yadroda, qaror xodim kartochkasiga
/// bog'lanishi mumkin.
class _DelegateCard extends ConsumerStatefulWidget {
  const _DelegateCard({required this.spaceId, required this.data});

  final String spaceId;
  final KkLearningOverviewDto data;

  @override
  ConsumerState<_DelegateCard> createState() => _DelegateCardState();
}

class _DelegateCardState extends ConsumerState<_DelegateCard> with ActionState {
  final _task = TextEditingController();
  final _owner = TextEditingController();
  final _helper = TextEditingController();
  final _taskHours = TextEditingController();
  final _taskMinutes = TextEditingController();
  final _trainHours = TextEditingController();
  final _trainMinutes = TextEditingController();
  final _money = TextEditingController();
  String _staff = '';
  KkDelegateResultDto? _result;

  List<TextEditingController> get _all => [
    _task,
    _owner,
    _helper,
    _taskHours,
    _taskMinutes,
    _trainHours,
    _trainMinutes,
    _money,
  ];

  @override
  void dispose() {
    for (final c in _all) {
      c.dispose();
    }
    super.dispose();
  }

  KkDelegateInput _input() => KkDelegateInput(
    task: _task.text,
    agreementId: _staff.isEmpty ? null : _staff,
    ownerHourValue: _owner.text.trim().isEmpty ? null : _owner.text,
    taskMinutes: toMinutes(_taskHours.text, _taskMinutes.text),
    helperHourCost: _helper.text,
    trainingMoney: _money.text.trim().isEmpty ? null : _money.text,
    trainingMinutes: toMinutes(_trainHours.text, _trainMinutes.text),
  );

  Future<void> _calc() async {
    final r = await act(() => ref.read(coreProvider).kkDelegateCalc(spaceId: widget.spaceId, input: _input()));
    if (r != null) setState(() => _result = r);
  }

  Future<void> _save() async {
    final r = await act(() => ref.read(coreProvider).kkDelegationSave(spaceId: widget.spaceId, input: _input()));
    if (r != null) {
      for (final c in _all) {
        c.clear();
      }
      setState(() {
        _staff = '';
        _result = r.result;
      });
    }
  }

  Widget _pair(String a, TextEditingController ca, String b, TextEditingController cb) => Row(
    children: [
      Expanded(
        child: Field(label: a, controller: ca, keyboardType: TextInputType.number),
      ),
      const SizedBox(width: 12),
      Expanded(
        child: Field(label: b, controller: cb, keyboardType: TextInputType.number),
      ),
    ],
  );

  @override
  Widget build(BuildContext context) {
    final d = widget.data;
    return SectionCard(
      title: context.t('kkl.del.title'),
      children: [
        Hint(context.t('kkl.del.hint')),
        const SizedBox(height: 12),
        Field(label: context.t('kkl.del.task'), hint: context.t('kkl.del.taskPlaceholder'), controller: _task),
        const SizedBox(height: 8),
        Select<String>(
          label: context.t('kkl.del.staff'),
          items: [('', context.t('kkl.del.noStaff')), for (final s in d.staff) (s.id, s.name)],
          value: _staff,
          onChanged: (v) => setState(() => _staff = v ?? ''),
        ),
        const SizedBox(height: 8),
        AmountField(label: context.t('kkl.del.owner'), controller: _owner),
        const SizedBox(height: 8),
        AmountField(label: context.t('kkl.del.helper'), controller: _helper),
        const SizedBox(height: 8),
        _pair(context.t('kkl.del.taskHours'), _taskHours, context.t('kkl.del.minutes'), _taskMinutes),
        const SizedBox(height: 8),
        _pair(context.t('kkl.del.trainingHours'), _trainHours, context.t('kkl.del.minutes'), _trainMinutes),
        const SizedBox(height: 8),
        AmountField(label: context.t('kkl.del.trainingMoney'), controller: _money),
        ErrorText(error),
        const SizedBox(height: 8),
        Wrap(
          spacing: 8,
          runSpacing: 8,
          children: [
            FilledButton(onPressed: busy ? null : _calc, child: Text(context.t('kkl.del.calc'))),
            OutlinedButton(onPressed: busy ? null : _save, child: Text(context.t('kkl.del.save'))),
          ],
        ),
        if (_result != null) _DelegateResult(_result!),
        const SizedBox(height: 12),
        Text(context.t('kkl.del.saved'), style: const TextStyle(fontWeight: FontWeight.w600)),
        if (d.delegations.isEmpty) Hint(context.t('kkl.del.empty')),
        for (final x in d.delegations) _DelegationRow(key: ValueKey(('kkl-del', x.id)), spaceId: widget.spaceId, d: x),
      ],
    );
  }
}

String _payback(BuildContext context, KkDelegateResultDto r) => switch (r.paybackMonths) {
  null => '—',
  0 => context.t('kkl.del.now'),
  final n => context.t('kkl.del.months', {'count': n}),
};

class _DelegateResult extends StatelessWidget {
  const _DelegateResult(this.r);

  final KkDelegateResultDto r;

  @override
  Widget build(BuildContext context) {
    final p = context.palette;
    final delegate = r.verdict == 'DELEGATE';
    return Semantics(
      liveRegion: true,
      child: Container(
        key: const Key('kkl-delegate-result'),
        margin: const EdgeInsets.only(top: 12),
        padding: const EdgeInsets.all(12),
        decoration: BoxDecoration(
          border: Border.all(color: p.line),
          borderRadius: BorderRadius.circular(10),
        ),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.stretch,
          children: [
            Text(context.t('kkl.del.result'), style: const TextStyle(fontWeight: FontWeight.w600)),
            ValueRow(context.t('kkl.del.benefit'), r.monthlyBenefit.formatted, key: const Key('kkl-benefit')),
            ValueRow(context.t('kkl.del.fullCost'), r.fullCost.formatted),
            Hint(context.t('kkl.del.timeCost', {'amount': r.trainingTimeCost.formatted})),
            if (delegate)
              ValueRow(
                context.t('kkl.del.payback'),
                _payback(context, r),
                strong: true,
                valueColor: p.accentText,
                key: const Key('kkl-payback'),
              ),
            const SizedBox(height: 6),
            Text(
              delegate
                  ? context.t('kkl.del.verdict.DELEGATE', {'benefit': r.monthlyBenefit.formatted})
                  : context.t('kkl.del.verdict.SELF_CHEAPER'),
              key: const Key('kkl-verdict'),
              style: TextStyle(color: delegate ? p.ink : p.warn),
            ),
          ],
        ),
      ),
    );
  }
}

class _DelegationRow extends ConsumerStatefulWidget {
  const _DelegationRow({required this.spaceId, required this.d, super.key});

  final String spaceId;
  final KkDelegationDto d;

  @override
  ConsumerState<_DelegationRow> createState() => _DelegationRowState();
}

class _DelegationRowState extends ConsumerState<_DelegationRow> with ActionState {
  /// O'chirishdan oldin tasdiq (tasodifiy bosishdan himoya).
  Future<void> _delete() async {
    final yes = await showBarakaDialog<bool>(
      context,
      (ctx) => AlertDialog(
        content: Text(ctx.t('kkl.del.confirm', {'task': widget.d.task})),
        actions: [
          TextButton(onPressed: () => Navigator.of(ctx).pop(false), child: Text(ctx.t('common.cancel'))),
          TextButton(onPressed: () => Navigator.of(ctx).pop(true), child: Text(ctx.t('kkl.del.confirmYes'))),
        ],
      ),
    );
    if (yes ?? false) {
      await act(() => ref.read(coreProvider).kkDelegationDelete(spaceId: widget.spaceId, id: widget.d.id));
    }
  }

  @override
  Widget build(BuildContext context) {
    final d = widget.d;
    final p = context.palette;
    final delegate = d.result.verdict == 'DELEGATE';
    return Container(
      padding: const EdgeInsets.symmetric(vertical: 8),
      decoration: BoxDecoration(
        border: Border(top: BorderSide(color: p.line)),
      ),
      child: Semantics(
        container: true,
        label: context.t('kkl.del.label', {'task': d.task}),
        child: Row(
          children: [
            Expanded(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text(
                    [d.task, if (d.staffName != null) d.staffName!].join(' · '),
                    style: const TextStyle(fontWeight: FontWeight.w600),
                  ),
                  Hint(
                    context.t('kkl.del.line', {
                      'time': showMinutes(context, d.taskMinutes),
                      'helper': d.helperHourCost.formatted,
                      'date': showDate(d.decidedOn),
                    }),
                  ),
                  Text(
                    delegate ? _payback(context, d.result) : context.t('kkl.del.verdict.SELF_CHEAPER'),
                    style: TextStyle(color: delegate ? p.accentText : p.warn),
                  ),
                  ErrorText(error),
                ],
              ),
            ),
            TextButton(
              onPressed: busy ? null : _delete,
              child: Text(context.t('kkl.del.delete')),
            ),
          ],
        ),
      ),
    );
  }
}

/// «Ilm zakoti» (8A.3): shu oy xodimlarga va boshqalarga o'rgatilgani. Pul hisobi yo'q.
class _TeachingCard extends StatelessWidget {
  const _TeachingCard({required this.spaceId, required this.data});

  final String spaceId;
  final KkLearningOverviewDto data;

  @override
  Widget build(BuildContext context) => SectionCard(
    title: context.t('learn.teach.title'),
    trailing: TextButton(
      onPressed: () => showSheet<void>(context, (_) => KkTeachingSheet(spaceId: spaceId, staff: data.staff)),
      child: Text(context.t('learn.teach.add')),
    ),
    children: [
      Hint(context.t('kkl.teach.hint')),
      const SizedBox(height: 8),
      Text(
        context.t('learn.teach.count', {'count': data.teachingCount}),
        key: const Key('kkl-teach-count'),
        style: const TextStyle(fontWeight: FontWeight.w700),
      ),
      if (data.teaching.isEmpty) Hint(context.t('learn.teach.empty')),
      for (final r in data.teaching)
        Padding(
          key: ValueKey(('kkl-teach', r.id)),
          padding: const EdgeInsets.only(top: 8),
          child: Text(
            [
              showDate(r.occurredOn),
              r.topic,
              if (r.learner != null) context.t('learn.teach.to', {'learner': r.learner}),
              if (r.minutes != null) showMinutes(context, r.minutes!),
            ].join(' · '),
          ),
        ),
    ],
  );
}

/// «Ilm zakoti» yozuvi: kimga — xodim kartochkasidan yoki boshqa kishi (ism ixtiyoriy).
class KkTeachingSheet extends ConsumerStatefulWidget {
  const KkTeachingSheet({required this.spaceId, required this.staff, super.key});

  final String spaceId;
  final List<KkStaffOptionDto> staff;

  @override
  ConsumerState<KkTeachingSheet> createState() => _KkTeachingSheetState();
}

class _KkTeachingSheetState extends ConsumerState<KkTeachingSheet> with ActionState {
  late String _staff = widget.staff.firstOrNull?.id ?? '';
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
          .kkTeachingAdd(
            spaceId: widget.spaceId,
            input: KkTeachingInput(
              occurredOn: _date,
              agreementId: _staff.isEmpty ? null : _staff,
              learner: _staff.isNotEmpty || _learner.text.trim().isEmpty ? null : _learner.text,
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
        Hint(context.t('kkl.teach.hint')),
        const SizedBox(height: 12),
        Field(label: context.t('learn.teach.topic'), controller: _topic),
        const SizedBox(height: 8),
        Select<String>(
          label: context.t('kkl.teach.staff'),
          items: [for (final s in widget.staff) (s.id, s.name), ('', context.t('kkl.teach.other'))],
          value: _staff,
          onChanged: (v) => setState(() => _staff = v ?? ''),
        ),
        if (_staff.isEmpty) ...[
          const SizedBox(height: 8),
          Field(label: context.t('kkl.teach.learner'), controller: _learner),
        ],
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
