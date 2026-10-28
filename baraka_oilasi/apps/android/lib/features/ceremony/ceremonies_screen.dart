import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../app/i18n.dart';
import '../../app/theme.dart';
import '../../core/core.dart';
import '../../core/query.dart';
import '../../shared/debt_widgets.dart';
import '../../shared/files.dart';
import '../../shared/format.dart';
import '../../shared/widgets.dart';

const ceremonyKinds = ['TOY', 'BESHIK_TOY', 'SUNNAT_TOY', 'MARAKA', 'OTHER'];
const fundingSources = ['SAVINGS', 'FAMILY', 'EXPECTED_GIFTS', 'DEBT'];
const _pressureCards = 4;

String? _opt(String v) => v.trim().isEmpty ? null : v;

/// Mehmonlar soni — pul emas, butun son; noto'g'ri qiymat yadroga yuborilmaydi.
int _guests(String v) {
  if (!RegExp(r'^\d{1,6}$').hasMatch(v.trim())) throw const AppError(code: 'INVALID_GUESTS', field: 'guests');
  return int.parse(v.trim());
}

/// To'y va marosimlarni rejalash (uy/SPEC 2D.8): 2–3 stsenariy, moliyalash manbalari,
/// qarz bo'lsa — «Buni qarzsiz qanday o'tkazamiz?» oilaviy muhokamasi, smeta PDF.
class CeremoniesScreen extends ConsumerWidget {
  const CeremoniesScreen({required this.spaceId, super.key});

  final String spaceId;

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final list = ref.watch(query(['ceremonies', spaceId], (c) => c.ceremonies(spaceId: spaceId)));
    void open(String id, String title) => pushScreen(context, title, (_) => CeremonyDetail(spaceId: spaceId, id: id));
    return ScreenBody(
      mentorKey: 'mentor.ceremonies',
      children: [
        const _PressureCard(),
        if (list.hasError) ErrorText(list.error),
        for (final c in list.valueOrNull ?? <CeremonySummaryDto>[])
          Card(
            child: ListTile(
              contentPadding: const EdgeInsets.symmetric(horizontal: 16, vertical: 8),
              title: Text(c.title, style: const TextStyle(fontWeight: FontWeight.w700)),
              subtitle: Padding(
                padding: const EdgeInsets.only(top: 6),
                child: Wrap(
                  spacing: 6,
                  runSpacing: 6,
                  crossAxisAlignment: WrapCrossAlignment.center,
                  children: [
                    Hint(
                      '${context.t('ceremony.kind.${c.kind}')}${c.plannedOn == null ? '' : ' · ${showDate(c.plannedOn!)}'}',
                    ),
                    if (c.hasDebt) Tag(context.t('ceremony.withDebt'), tone: 'danger'),
                    Tag(context.t('ceremony.status.${c.status}')),
                  ],
                ),
              ),
              trailing: Text(
                c.total?.formatted ?? '',
                style: TextStyle(color: context.palette.accentText, fontWeight: FontWeight.w700),
              ),
              onTap: () => open(c.id, c.title),
            ),
          ),
        _CreateForm(spaceId: spaceId, onCreated: open),
        _GiftGoals(spaceId: spaceId),
      ],
    );
  }
}

class _PressureCard extends StatefulWidget {
  const _PressureCard({this.seed = 0});

  final int seed;

  @override
  State<_PressureCard> createState() => _PressureCardState();
}

class _PressureCardState extends State<_PressureCard> {
  late int _i = widget.seed % _pressureCards;

  @override
  Widget build(BuildContext context) => Card(
    color: context.palette.sidebar,
    child: Padding(
      padding: const EdgeInsets.all(16),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text(
            context.t('mentor.name'),
            style: TextStyle(color: context.palette.accentText, fontWeight: FontWeight.w700),
          ),
          const SizedBox(height: 6),
          Text(context.t('ceremony.pressure.$_i')),
          TextButton(
            onPressed: () => setState(() => _i = (_i + 1) % _pressureCards),
            child: Text(context.t('ceremony.pressure.next')),
          ),
        ],
      ),
    ),
  );
}

class _CreateForm extends ConsumerStatefulWidget {
  const _CreateForm({required this.spaceId, required this.onCreated});

  final String spaceId;
  final void Function(String id, String title) onCreated;

  @override
  ConsumerState<_CreateForm> createState() => _CreateFormState();
}

class _CreateFormState extends ConsumerState<_CreateForm> with ActionState {
  String _kind = 'TOY';
  String? _date;
  final _title = TextEditingController();
  final _scenario = TextEditingController();
  final _guestsC = TextEditingController();

  @override
  void dispose() {
    _title.dispose();
    _scenario.dispose();
    _guestsC.dispose();
    super.dispose();
  }

  Future<void> _create() async {
    final c = await act(
      () async => ref
          .read(coreProvider)
          .createCeremony(
            spaceId: widget.spaceId,
            input: NewCeremonyInput(
              kind: _kind,
              title: _title.text,
              plannedOn: _date,
              scenarioName: _scenario.text,
              guests: _guests(_guestsC.text),
            ),
          ),
    );
    if (c == null) return;
    if (mounted) {
      _title.clear();
      _scenario.clear();
      _guestsC.clear();
    }
    widget.onCreated(c.id, c.title);
  }

  @override
  Widget build(BuildContext context) => SectionCard(
    title: context.t('ceremony.new'),
    children: [
      Select<String>(
        label: context.t('ceremony.kindLabel'),
        items: [for (final k in ceremonyKinds) (k, context.t('ceremony.kind.$k'))],
        value: _kind,
        onChanged: (v) => setState(() => _kind = v ?? _kind),
      ),
      const SizedBox(height: 12),
      Field(label: context.t('ceremony.name'), controller: _title),
      const SizedBox(height: 12),
      DateField(label: context.t('ceremony.date'), value: _date, onChanged: (v) => setState(() => _date = v)),
      const SizedBox(height: 12),
      Field(
        label: context.t('ceremony.firstScenario'),
        hint: context.t('ceremony.scenarioHint'),
        controller: _scenario,
      ),
      const SizedBox(height: 12),
      Field(label: context.t('ceremony.guests'), controller: _guestsC, keyboardType: TextInputType.number),
      ErrorText(error),
      const SizedBox(height: 8),
      Align(
        alignment: Alignment.centerLeft,
        child: FilledButton(onPressed: busy ? null : _create, child: Text(context.t('ceremony.create'))),
      ),
    ],
  );
}

/// Bitta marosim: sozlamalar, stsenariylar, muhokama, tasdiqlash va smeta PDF.
class CeremonyDetail extends ConsumerStatefulWidget {
  const CeremonyDetail({required this.spaceId, required this.id, super.key});

  final String spaceId;
  final String id;

  @override
  ConsumerState<CeremonyDetail> createState() => _CeremonyDetailState();
}

class _CeremonyDetailState extends ConsumerState<CeremonyDetail> with ActionState {
  @override
  Widget build(BuildContext context) {
    final sid = widget.spaceId;
    final id = widget.id;
    final q = ref.watch(query(['ceremony', sid, id], (c) => c.ceremony(spaceId: sid, ceremonyId: id)));
    final c = q.valueOrNull;
    if (c == null) return AsyncView(value: q, data: (_) => const SizedBox.shrink());
    final core = ref.read(coreProvider);
    final locked = c.status == 'CONFIRMED';
    final selected = c.scenarios.where((s) => s.selected).firstOrNull;
    final p = context.palette;
    return ScreenBody(
      children: [
        Wrap(
          spacing: 8,
          runSpacing: 6,
          crossAxisAlignment: WrapCrossAlignment.center,
          children: [
            Hint('${context.t('ceremony.kind.${c.kind}')}${c.plannedOn == null ? '' : ' · ${showDate(c.plannedOn!)}'}'),
            Tag(context.t('ceremony.status.${c.status}'), tone: locked ? 'accent' : 'muted'),
          ],
        ),
        _Settings(key: ValueKey('settings-${c.title}-${c.plannedOn}'), spaceId: sid, c: c),
        if (c.giftsWarning)
          Container(
            padding: const EdgeInsets.all(12),
            decoration: BoxDecoration(
              border: Border.all(color: p.warn),
              borderRadius: BorderRadius.circular(10),
            ),
            child: Text(context.t('ceremony.giftsWarning')),
          ),
        for (final s in c.scenarios)
          _Scenario(
            key: ValueKey('${s.id}-${s.name}-${s.guests}'),
            spaceId: sid,
            ceremonyId: id,
            s: s,
            locked: locked,
            canDelete: c.scenarios.length > 1,
          ),
        if (!locked && c.scenarios.length < 3)
          Wrap(
            spacing: 8,
            children: [
              OutlinedButton(
                onPressed: () => act(
                  () => core.addScenario(
                    spaceId: sid,
                    ceremonyId: id,
                    input: ScenarioInput(name: context.t('ceremony.newScenario'), guests: 0, copyFrom: selected?.id),
                  ),
                ),
                child: Text(context.t('ceremony.addScenarioCopy')),
              ),
              OutlinedButton(
                onPressed: () => act(
                  () => core.addScenario(
                    spaceId: sid,
                    ceremonyId: id,
                    input: ScenarioInput(name: context.t('ceremony.newScenario'), guests: 0),
                  ),
                ),
                child: Text(context.t('ceremony.addScenarioEmpty')),
              ),
            ],
          ),
        if (c.discussion.required_ || c.discussion.answers.any((a) => a.note.isNotEmpty))
          _Discussion(key: ValueKey('disc-${c.status}'), spaceId: sid, c: c),
        SectionCard(
          children: [
            if (c.confirmBlocker != null) Hint(context.t('ceremony.blocker.${c.confirmBlocker}')),
            const SizedBox(height: 8),
            Wrap(
              spacing: 8,
              runSpacing: 8,
              children: [
                if (!locked)
                  FilledButton(
                    onPressed: !c.canConfirm || busy
                        ? null
                        : () => act(() => core.confirmCeremony(spaceId: sid, ceremonyId: id)),
                    child: Text(context.t('ceremony.confirm')),
                  ),
                if (c.status != 'DRAFT')
                  OutlinedButton(
                    onPressed: () => act(() => core.reopenCeremony(spaceId: sid, ceremonyId: id)),
                    child: Text(context.t('ceremony.reopen')),
                  ),
                OutlinedButton(
                  onPressed: busy
                      ? null
                      : () => act(() async {
                          final bytes = await core.ceremonyEstimatePdf(spaceId: sid, ceremonyId: id);
                          await ref.read(shareFileProvider)(bytes, 'smeta.pdf', pdfMime);
                        }),
                  child: Text(context.t('ceremony.pdf')),
                ),
              ],
            ),
            ErrorText(error),
          ],
        ),
        _PressureCard(seed: c.title.length),
      ],
    );
  }
}

class _Settings extends ConsumerStatefulWidget {
  const _Settings({required this.spaceId, required this.c, super.key});

  final String spaceId;
  final CeremonyDto c;

  @override
  ConsumerState<_Settings> createState() => _SettingsState();
}

class _SettingsState extends ConsumerState<_Settings> with ActionState {
  late final _title = TextEditingController(text: widget.c.title);
  late String? _date = widget.c.plannedOn;
  late final _capacity = TextEditingController(
    text: widget.c.capacitySource == 'MANUAL' ? widget.c.monthlyCapacity.plain : '',
  );

  @override
  void dispose() {
    _title.dispose();
    _capacity.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) => SectionCard(
    children: [
      Field(label: context.t('ceremony.name'), controller: _title),
      const SizedBox(height: 12),
      DateField(label: context.t('ceremony.date'), value: _date, onChanged: (v) => setState(() => _date = v)),
      const SizedBox(height: 12),
      AmountField(label: context.t('ceremony.capacity'), controller: _capacity, hint: widget.c.monthlyCapacity.plain),
      const SizedBox(height: 4),
      Hint(
        context.t('ceremony.capacitySource.${widget.c.capacitySource}', {
          'amount': widget.c.monthlyCapacity.formatted,
        }),
      ),
      ErrorText(error),
      Align(
        alignment: Alignment.centerLeft,
        child: OutlinedButton(
          onPressed: busy
              ? null
              : () => act(
                  () => ref
                      .read(coreProvider)
                      .updateCeremony(
                        spaceId: widget.spaceId,
                        ceremonyId: widget.c.id,
                        input: CeremonyUpdateInput(
                          title: _title.text,
                          plannedOn: _date,
                          monthlyCapacity: _opt(_capacity.text),
                        ),
                      ),
                ),
          child: Text(context.t('common.save')),
        ),
      ),
    ],
  );
}

class _Scenario extends ConsumerStatefulWidget {
  const _Scenario({
    required this.spaceId,
    required this.ceremonyId,
    required this.s,
    required this.locked,
    required this.canDelete,
    super.key,
  });

  final String spaceId;
  final String ceremonyId;
  final ScenarioDto s;
  final bool locked;
  final bool canDelete;

  @override
  ConsumerState<_Scenario> createState() => _ScenarioState();
}

class _ScenarioState extends ConsumerState<_Scenario> with ActionState {
  late final _name = TextEditingController(text: widget.s.name);
  late final _guestsC = TextEditingController(text: '${widget.s.guests}');
  final _lineTitle = TextEditingController();
  final _lineAmount = TextEditingController();
  String _kind = 'ONE_OFF';
  String _source = 'SAVINGS';

  @override
  void dispose() {
    for (final c in [_name, _guestsC, _lineTitle, _lineAmount]) {
      c.dispose();
    }
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    final s = widget.s;
    final core = ref.read(coreProvider);
    final sid = widget.spaceId;
    final cid = widget.ceremonyId;
    final locked = widget.locked;
    final p = context.palette;
    final bySource = {
      'SAVINGS': s.bySource.savings,
      'FAMILY': s.bySource.family,
      'EXPECTED_GIFTS': s.bySource.expectedGifts,
      'DEBT': s.bySource.debt,
    };
    return Card(
      shape: RoundedRectangleBorder(
        borderRadius: BorderRadius.circular(16),
        side: BorderSide(color: s.selected ? p.accent : p.line, width: s.selected ? 2 : 1),
      ),
      child: Padding(
        padding: const EdgeInsets.all(16),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.stretch,
          children: [
            Semantics(
              container: true,
              label: s.name,
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.stretch,
                children: [
                  TextField(
                    controller: _name,
                    enabled: !locked,
                    style: const TextStyle(fontWeight: FontWeight.w700),
                    decoration: InputDecoration(labelText: context.t('ceremony.scenario')),
                  ),
                  const SizedBox(height: 8),
                  Row(
                    children: [
                      Expanded(
                        child: TextField(
                          controller: _guestsC,
                          enabled: !locked,
                          keyboardType: TextInputType.number,
                          decoration: InputDecoration(labelText: context.t('ceremony.guests')),
                        ),
                      ),
                      if (!locked) ...[
                        const SizedBox(width: 8),
                        OutlinedButton(
                          onPressed: () => act(
                            () async => core.updateScenario(
                              spaceId: sid,
                              ceremonyId: cid,
                              scenarioId: s.id,
                              input: ScenarioInput(name: _name.text, guests: _guests(_guestsC.text)),
                            ),
                          ),
                          child: Text(context.t('common.save')),
                        ),
                      ],
                    ],
                  ),
                ],
              ),
            ),
            const SizedBox(height: 8),
            for (final x in s.lines)
              Row(
                children: [
                  Expanded(
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        Text(x.title),
                        Hint(
                          '${x.kind == 'PER_GUEST' ? '${x.amount.formatted} × ${s.guests}' : context.t('ceremony.oneOff')} · ${context.t('ceremony.source.${x.source}')}',
                        ),
                      ],
                    ),
                  ),
                  Text(x.total.formatted, style: TextStyle(color: x.source == 'DEBT' ? p.danger : null)),
                  if (!locked)
                    IconButton(
                      tooltip: context.t('ceremony.deleteLine', {'title': x.title}),
                      icon: const Icon(Icons.close),
                      onPressed: () => act(() => core.deleteCeremonyLine(spaceId: sid, ceremonyId: cid, lineId: x.id)),
                    ),
                ],
              ),
            if (!locked)
              Container(
                margin: const EdgeInsets.only(top: 8),
                padding: const EdgeInsets.all(12),
                decoration: BoxDecoration(
                  border: Border.all(color: p.line),
                  borderRadius: BorderRadius.circular(10),
                ),
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.stretch,
                  children: [
                    Field(label: context.t('ceremony.lineTitle'), controller: _lineTitle),
                    const SizedBox(height: 8),
                    Select<String>(
                      label: context.t('ceremony.lineKind'),
                      items: [
                        ('ONE_OFF', context.t('ceremony.oneOff')),
                        ('PER_GUEST', context.t('ceremony.perGuest')),
                      ],
                      value: _kind,
                      onChanged: (v) => setState(() => _kind = v ?? _kind),
                    ),
                    const SizedBox(height: 8),
                    Select<String>(
                      label: context.t('ceremony.lineSource'),
                      items: [for (final x in fundingSources) (x, context.t('ceremony.source.$x'))],
                      value: _source,
                      onChanged: (v) => setState(() => _source = v ?? _source),
                    ),
                    const SizedBox(height: 8),
                    AmountField(label: context.t('ceremony.lineAmount'), controller: _lineAmount),
                    if (_source == 'DEBT') Hint(context.t('ceremony.debtHint'), color: p.danger),
                    Align(
                      alignment: Alignment.centerLeft,
                      child: OutlinedButton(
                        onPressed: busy
                            ? null
                            : () async {
                                final r = await act(
                                  () => core.addCeremonyLine(
                                    spaceId: sid,
                                    ceremonyId: cid,
                                    scenarioId: s.id,
                                    input: NewCeremonyLineInput(
                                      title: _lineTitle.text,
                                      kind: _kind,
                                      amount: _lineAmount.text,
                                      source: _source,
                                    ),
                                  ),
                                );
                                if (r != null) {
                                  _lineTitle.clear();
                                  _lineAmount.clear();
                                }
                              },
                        child: Text(context.t('goals.add')),
                      ),
                    ),
                  ],
                ),
              ),
            const SizedBox(height: 8),
            for (final x in fundingSources)
              ValueRow(
                context.t('ceremony.source.$x'),
                bySource[x]!.formatted,
                valueColor: x == 'DEBT' && s.hasDebt ? p.danger : null,
              ),
            ValueRow(context.t('ceremony.total'), s.total.formatted, strong: true, valueColor: p.accentText),
            const SizedBox(height: 6),
            if (!s.hasDebt)
              Text(context.t('ceremony.noDebt'))
            else if (s.notRepayable)
              Text(context.t('ceremony.notRepayable'), style: TextStyle(color: p.danger))
            else
              Text(
                context.t('ceremony.payoff', {
                  'count': s.payoffMonths ?? 0,
                  'date': s.payoffDate == null ? '' : showMonth(s.payoffDate!),
                }),
              ),
            if (s.savedVsMax.minor != '0') ...[
              Text(
                context.t('ceremony.saved', {'amount': s.savedVsMax.formatted}),
                style: TextStyle(color: p.accentText),
              ),
              for (final g in s.goalEquivalents)
                Text(
                  context.t('ceremony.savedGoal', {'title': g.title, 'percent': g.percent}),
                  style: TextStyle(color: p.accentText),
                ),
            ],
            const SizedBox(height: 8),
            Wrap(
              spacing: 8,
              children: [
                if (s.selected)
                  Text(
                    '✓ ${context.t('ceremony.selected')}',
                    style: TextStyle(color: p.accentText, fontWeight: FontWeight.w700),
                  )
                else if (!locked)
                  OutlinedButton(
                    onPressed: () => act(() => core.selectScenario(spaceId: sid, ceremonyId: cid, scenarioId: s.id)),
                    child: Text(context.t('ceremony.select')),
                  ),
                if (!locked && widget.canDelete)
                  TextButton(
                    onPressed: () => act(() => core.deleteScenario(spaceId: sid, ceremonyId: cid, scenarioId: s.id)),
                    child: Text(context.t('ceremony.deleteScenario')),
                  ),
              ],
            ),
            ErrorText(error),
          ],
        ),
      ),
    );
  }
}

class _Discussion extends ConsumerStatefulWidget {
  const _Discussion({required this.spaceId, required this.c, super.key});

  final String spaceId;
  final CeremonyDto c;

  @override
  ConsumerState<_Discussion> createState() => _DiscussionState();
}

class _DiscussionState extends ConsumerState<_Discussion> with ActionState {
  late final List<TextEditingController> _notes = [
    for (final a in widget.c.discussion.answers) TextEditingController(text: a.note),
  ];

  @override
  void dispose() {
    for (final c in _notes) {
      c.dispose();
    }
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    final c = widget.c;
    final locked = c.status == 'CONFIRMED';
    final core = ref.read(coreProvider);
    final p = context.palette;
    return SectionCard(
      title: context.t('ceremony.discussion'),
      children: [
        Hint(context.t('ceremony.discussionIntro')),
        for (final (i, a) in c.discussion.answers.indexed)
          Padding(
            padding: const EdgeInsets.only(top: 12),
            child: TextField(
              controller: _notes[i],
              enabled: !locked,
              minLines: 2,
              maxLines: 5,
              decoration: InputDecoration(labelText: context.t('ceremony.question.${a.key}')),
            ),
          ),
        if (!locked)
          Align(
            alignment: Alignment.centerLeft,
            child: OutlinedButton(
              onPressed: () => act(
                () => core.saveDiscussion(
                  spaceId: widget.spaceId,
                  ceremonyId: c.id,
                  answers: [
                    for (final (i, a) in c.discussion.answers.indexed)
                      DiscussionAnswerDto(key: a.key, note: _notes[i].text),
                  ],
                ),
              ),
              child: Text(context.t('ceremony.saveAnswers')),
            ),
          ),
        const SizedBox(height: 8),
        for (final m in c.discussion.adults)
          Row(
            children: [
              Expanded(child: Text(m.name)),
              if (m.agreedOn != null)
                Text(
                  '✓ ${context.t('ceremony.agreed', {'date': showDate(m.agreedOn!)})}',
                  style: TextStyle(color: p.accentText),
                )
              else if (!locked)
                OutlinedButton(
                  onPressed: () => act(
                    () => core.agreeDiscussion(spaceId: widget.spaceId, ceremonyId: c.id, memberId: m.memberId),
                  ),
                  child: Text(context.t('ceremony.agree', {'name': m.name})),
                ),
            ],
          ),
        if (c.status == 'DISCUSSED') Text(context.t('ceremony.discussionDone'), style: TextStyle(color: p.accentText)),
        ErrorText(error),
      ],
    );
  }
}

/// To'yona o'rniga jamg'arma (uy/SPEC 2D.8): yosh oila maqsadiga mehmonlar hissasi.
class _GiftGoals extends ConsumerWidget {
  const _GiftGoals({required this.spaceId});

  final String spaceId;

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final goals =
        ref.watch(query(['debts', spaceId], (c) => c.debtsOverview(spaceId: spaceId))).valueOrNull?.goals ?? [];
    return SectionCard(
      title: context.t('ceremony.giftGoal'),
      children: [
        Hint(context.t('ceremony.giftGoalIntro')),
        if (goals.isEmpty) Hint(context.t('ceremony.noGoals')),
        for (final g in goals) _GiftGoal(spaceId: spaceId, g: g),
      ],
    );
  }
}

class _GiftGoal extends ConsumerStatefulWidget {
  const _GiftGoal({required this.spaceId, required this.g});

  final String spaceId;
  final GoalDto g;

  @override
  ConsumerState<_GiftGoal> createState() => _GiftGoalState();
}

class _GiftGoalState extends ConsumerState<_GiftGoal> with ActionState {
  final _who = TextEditingController();
  final _amount = TextEditingController();
  bool _copied = false;

  @override
  void dispose() {
    _who.dispose();
    _amount.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    final g = widget.g;
    final p = context.palette;
    final share = context.t('ceremony.shareText', {
      'title': g.title,
      'target': g.target.formatted,
      'collected': g.collected.formatted,
    });
    return Container(
      margin: const EdgeInsets.only(top: 8),
      padding: const EdgeInsets.all(12),
      decoration: BoxDecoration(
        border: Border.all(color: p.line),
        borderRadius: BorderRadius.circular(10),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: [
          Text(g.title, style: const TextStyle(fontWeight: FontWeight.w700)),
          Text('${g.collected.formatted} / ${g.target.formatted} · ${g.collectedPercent}%'),
          for (final x in g.contributions) Hint('${x.contributor} — ${x.amount.formatted}, ${showDate(x.givenOn)}'),
          const SizedBox(height: 8),
          Field(label: context.t('ceremony.guestName'), controller: _who),
          const SizedBox(height: 8),
          AmountField(label: context.t('ceremony.giftAmount'), controller: _amount),
          Align(
            alignment: Alignment.centerLeft,
            child: OutlinedButton(
              onPressed: busy
                  ? null
                  : () async {
                      final r = await act(
                        () => ref
                            .read(coreProvider)
                            .addGoalContribution(
                              spaceId: widget.spaceId,
                              goalId: g.id,
                              input: NewGoalContributionInput(contributor: _who.text, amount: _amount.text),
                            ),
                      );
                      if (r != null) {
                        _who.clear();
                        _amount.clear();
                      }
                    },
              child: Text(context.t('goals.add')),
            ),
          ),
          const SizedBox(height: 8),
          Container(
            padding: const EdgeInsets.all(8),
            color: p.sidebar,
            child: Text(share, style: const TextStyle(fontSize: 13)),
          ),
          Align(
            alignment: Alignment.centerLeft,
            child: TextButton(
              onPressed: () async {
                await Clipboard.setData(ClipboardData(text: share));
                setState(() => _copied = true);
              },
              child: Text(_copied ? context.t('ceremony.copied') : context.t('ceremony.copy')),
            ),
          ),
          ErrorText(error),
        ],
      ),
    );
  }
}
