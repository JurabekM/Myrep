import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../app/i18n.dart';
import '../../app/shell_state.dart';
import '../../app/theme.dart';
import '../../core/core.dart';
import '../../core/query.dart';
import '../../shared/json.dart';
import '../../shared/widgets.dart';

const ideaScenarios = ['PESSIMISTIC', 'BASE', 'OPTIMISTIC'];

/// Foiz matni → basis points (butun son; pul emas).
int percentToBp(String v, {String field = 'workerShareBp'}) {
  final m = RegExp(r'^(\d{1,3})(?:[.,](\d{1,2}))?$').firstMatch(v.trim());
  if (m == null) throw AppError(code: 'INVALID_PERCENT', field: field);
  return int.parse(m.group(1)!) * 100 + int.parse((m.group(2) ?? '').padRight(2, '0'));
}

/// «Hunardan ishga» (uy/SPEC 2E.4): oiladagi bekor yotgan hunar → mini biznes-hisob, uch stsenariy,
/// qoplanish muddati; bir bosishda sheriklik qoralamasi.
class IdeasScreen extends ConsumerStatefulWidget {
  const IdeasScreen({required this.spaceId, super.key});

  final String spaceId;

  @override
  ConsumerState<IdeasScreen> createState() => _IdeasScreenState();
}

class _IdeasScreenState extends ConsumerState<IdeasScreen> {
  /// `null` — yopiq, `''` — yangi g'oya, aks holda — tahrirlanayotgan g'oya id'si.
  String? _editing;

  @override
  Widget build(BuildContext context) {
    final id = widget.spaceId;
    final ideas = ref.watch(query(['ideas', id], (c) => c.ventureIdeas(spaceId: id)));
    final list = ideas.valueOrNull ?? <VentureIdeaDto>[];
    final editing = _editing;
    return ScreenBody(
      mentorKey: 'mentor.ideas',
      children: [
        Align(
          alignment: Alignment.centerLeft,
          child: FilledButton(onPressed: () => setState(() => _editing = ''), child: Text(context.t('ideas.new'))),
        ),
        Card(
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
                Text(context.t('ideas.intro')),
              ],
            ),
          ),
        ),
        _Skills(spaceId: id),
        if (editing != null)
          _IdeaEditor(
            key: ValueKey('editor-$editing'),
            spaceId: id,
            idea: list.where((i) => i.id == editing).firstOrNull,
            onDone: () => setState(() => _editing = null),
          ),
        if (ideas.hasError) ErrorText(ideas.error),
        for (final i in list) _IdeaCard(spaceId: id, idea: i, onEdit: () => setState(() => _editing = i.id)),
      ],
    );
  }
}

class _Skills extends ConsumerStatefulWidget {
  const _Skills({required this.spaceId});

  final String spaceId;

  @override
  ConsumerState<_Skills> createState() => _SkillsState();
}

class _SkillsState extends ConsumerState<_Skills> with ActionState {
  final _title = TextEditingController();
  String? _memberId;

  @override
  void dispose() {
    _title.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    final id = widget.spaceId;
    final skills = ref.watch(query(['skills', id], (c) => c.skills(spaceId: id))).valueOrNull ?? [];
    final members = ref.watch(query(['household'], (c) => c.household())).valueOrNull?.members ?? [];
    final core = ref.read(coreProvider);
    return SectionCard(
      title: context.t('ideas.skills'),
      children: [
        Hint(context.t('ideas.skillsHint')),
        const SizedBox(height: 8),
        Wrap(
          spacing: 8,
          runSpacing: 8,
          children: [
            for (final s in skills)
              InputChip(
                label: Text('${s.title}${s.memberName == null ? '' : ' · ${s.memberName}'}'),
                onDeleted: () => act(() => core.deleteSkill(spaceId: id, skillId: s.id)),
                deleteButtonTooltipMessage: context.t('ideas.removeSkill', {'name': s.title}),
              ),
          ],
        ),
        const SizedBox(height: 8),
        Field(label: context.t('ideas.skill'), hint: context.t('ideas.skillPlaceholder'), controller: _title),
        const SizedBox(height: 8),
        Select<String>(
          label: context.t('ideas.who'),
          items: [('', '—'), for (final m in members) (m.id, m.displayName)],
          value: _memberId ?? '',
          onChanged: (v) => setState(() => _memberId = (v ?? '').isEmpty ? null : v),
        ),
        ErrorText(error),
        Align(
          alignment: Alignment.centerLeft,
          child: OutlinedButton(
            onPressed: busy
                ? null
                : () async {
                    final r = await act(
                      () => core.addSkill(
                        spaceId: id,
                        input: SkillInput(memberId: _memberId, title: _title.text),
                      ),
                    );
                    if (r != null) {
                      _title.clear();
                      setState(() => _memberId = null);
                    }
                  },
            child: Text('+ ${context.t('ideas.addSkill')}'),
          ),
        ),
      ],
    );
  }
}

class _CapexRow {
  _CapexRow([String title = '', String amount = ''])
    : title = TextEditingController(text: title),
      amount = TextEditingController(text: amount);

  final TextEditingController title;
  final TextEditingController amount;
}

class _IdeaEditor extends ConsumerStatefulWidget {
  const _IdeaEditor({required this.spaceId, required this.idea, required this.onDone, super.key});

  final String spaceId;
  final VentureIdeaDto? idea;
  final VoidCallback onDone;

  @override
  ConsumerState<_IdeaEditor> createState() => _IdeaEditorState();
}

class _IdeaEditorState extends ConsumerState<_IdeaEditor> with ActionState {
  late final _title = TextEditingController(text: widget.idea?.title ?? '');
  late String? _skillId = widget.idea?.skillId;
  late final List<_CapexRow> _capex = widget.idea == null
      ? [_CapexRow()]
      : [for (final c in widget.idea!.capexLines) _CapexRow(c.title, c.amount.plain)];
  late final Map<String, (TextEditingController, TextEditingController)> _sc = {
    for (final n in ideaScenarios)
      n: (
        TextEditingController(text: _scenario(n)?.income.plain ?? ''),
        TextEditingController(text: _scenario(n)?.expense.plain ?? ''),
      ),
  };
  late bool _partnered = widget.idea == null || widget.idea!.workerShareBp != null;
  late final _share = TextEditingController(
    text: widget.idea?.workerShareBp == null ? '50' : _bpText(widget.idea!.workerShareBp!),
  );

  IdeaScenarioDto? _scenario(String n) => widget.idea?.scenarios.where((s) => s.name == n).firstOrNull;

  static String _bpText(int bp) =>
      bp % 100 == 0 ? '${bp ~/ 100}' : '${bp ~/ 100},${(bp % 100).toString().padLeft(2, '0')}';

  @override
  void dispose() {
    for (final c in [
      _title,
      _share,
      ..._capex.expand((r) => [r.title, r.amount]),
      ..._sc.values.expand((p) => [p.$1, p.$2]),
    ]) {
      c.dispose();
    }
    super.dispose();
  }

  VentureIdeaInput _input() => VentureIdeaInput(
    title: _title.text,
    skillId: _skillId,
    capex: [
      for (final r in _capex)
        if (r.title.text.trim().isNotEmpty || r.amount.text.trim().isNotEmpty)
          CapexLineInput(title: r.title.text, amount: r.amount.text),
    ],
    scenarios: [
      for (final n in ideaScenarios) IdeaScenarioInput(name: n, income: _sc[n]!.$1.text, expense: _sc[n]!.$2.text),
    ],
    workerShareBp: _partnered ? percentToBp(_share.text) : null,
  );

  Future<void> _save() async {
    final core = ref.read(coreProvider);
    final idea = widget.idea;
    final r = await act(
      () async => idea == null
          ? core.createVentureIdea(spaceId: widget.spaceId, input: _input())
          : core.updateVentureIdea(spaceId: widget.spaceId, ideaId: idea.id, input: _input()),
    );
    if (r != null) widget.onDone();
  }

  @override
  Widget build(BuildContext context) {
    final id = widget.spaceId;
    final skills = ref.watch(query(['skills', id], (c) => c.skills(spaceId: id))).valueOrNull ?? [];
    return SectionCard(
      title: context.t('ideas.editor'),
      children: [
        Field(label: context.t('ideas.ideaTitle'), controller: _title),
        const SizedBox(height: 12),
        Select<String>(
          label: context.t('ideas.skill'),
          items: [('', '—'), for (final s in skills) (s.id, s.title)],
          value: _skillId ?? '',
          onChanged: (v) => setState(() => _skillId = (v ?? '').isEmpty ? null : v),
        ),
        const SizedBox(height: 16),
        Text(context.t('ideas.capex'), style: const TextStyle(fontWeight: FontWeight.w700)),
        Hint(context.t('ideas.capexHint')),
        for (final (i, r) in _capex.indexed)
          Padding(
            padding: const EdgeInsets.only(top: 8),
            child: Row(
              children: [
                Expanded(
                  child: Field(label: context.t('ideas.capexItem', {'n': i + 1}), controller: r.title),
                ),
                const SizedBox(width: 8),
                Expanded(
                  child: AmountField(label: context.t('ideas.capexAmount', {'n': i + 1}), controller: r.amount),
                ),
                IconButton(
                  tooltip: context.t('receipt.removeLine'),
                  icon: const Icon(Icons.close),
                  onPressed: () => setState(() => _capex.removeAt(i)),
                ),
              ],
            ),
          ),
        Align(
          alignment: Alignment.centerLeft,
          child: TextButton(
            onPressed: () => setState(() => _capex.add(_CapexRow())),
            child: Text('+ ${context.t('ideas.addCapex')}'),
          ),
        ),
        const SizedBox(height: 8),
        Text(context.t('ideas.scenarios'), style: const TextStyle(fontWeight: FontWeight.w700)),
        Hint(context.t('ideas.scenariosHint')),
        for (final n in ideaScenarios)
          Container(
            margin: const EdgeInsets.only(top: 8),
            padding: const EdgeInsets.all(12),
            decoration: BoxDecoration(
              border: Border.all(color: context.palette.line),
              borderRadius: BorderRadius.circular(10),
            ),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.stretch,
              children: [
                Text(context.t('ideas.scenario.$n'), style: const TextStyle(fontWeight: FontWeight.w700)),
                const SizedBox(height: 8),
                AmountField(label: context.t('ideas.monthlyIncome'), controller: _sc[n]!.$1),
                const SizedBox(height: 8),
                AmountField(label: context.t('ideas.monthlyExpense'), controller: _sc[n]!.$2),
              ],
            ),
          ),
        CheckboxListTile(
          contentPadding: EdgeInsets.zero,
          value: _partnered,
          title: Text(context.t('ideas.partnered')),
          onChanged: (v) => setState(() => _partnered = v ?? false),
        ),
        if (_partnered)
          Field(
            label: context.t('ideas.workerShare'),
            controller: _share,
            keyboardType: const TextInputType.numberWithOptions(decimal: true),
          ),
        ErrorText(error),
        const SizedBox(height: 8),
        Wrap(
          spacing: 8,
          children: [
            FilledButton(onPressed: busy ? null : _save, child: Text(context.t('ideas.calculate'))),
            TextButton(onPressed: widget.onDone, child: Text(context.t('common.cancel'))),
          ],
        ),
      ],
    );
  }
}

class _IdeaCard extends ConsumerStatefulWidget {
  const _IdeaCard({required this.spaceId, required this.idea, required this.onEdit});

  final String spaceId;
  final VentureIdeaDto idea;
  final VoidCallback onEdit;

  @override
  ConsumerState<_IdeaCard> createState() => _IdeaCardState();
}

class _IdeaCardState extends ConsumerState<_IdeaCard> with ActionState {
  bool _drafting = false;
  final _provider = TextEditingController();
  final _me = TextEditingController();

  @override
  void dispose() {
    _provider.dispose();
    _me.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    final idea = widget.idea;
    final core = ref.read(coreProvider);
    final shell = ref.read(shellProvider.notifier);
    final p = context.palette;
    String months(int? n) => n == null ? context.t('ideas.never') : context.t('ideas.months', {'n': n});
    final partnered = idea.workerShareBp != null;
    return SectionCard(
      title: idea.title,
      children: [
        if (idea.skillTitle != null) Hint(idea.skillTitle!),
        ValueRow(context.t('ideas.capexTotal'), idea.capex.formatted, strong: true, valueColor: p.accentText),
        for (final s in idea.scenarios)
          Container(
            margin: const EdgeInsets.only(top: 8),
            padding: const EdgeInsets.only(top: 8),
            decoration: BoxDecoration(
              border: Border(top: BorderSide(color: p.line)),
            ),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.stretch,
              children: [
                Text(context.t('ideas.scenario.${s.name}'), style: const TextStyle(fontWeight: FontWeight.w700)),
                ValueRow(
                  context.t('ideas.net'),
                  s.net.formatted,
                  valueColor: s.net.minor.startsWith('-') ? p.danger : null,
                ),
                ValueRow(context.t('ideas.payback'), months(s.paybackMonths), strong: true),
                if (partnered) ...[
                  ValueRow(context.t('ideas.worker'), s.workerMonthly?.formatted ?? ''),
                  ValueRow(context.t('ideas.investor'), s.investorMonthly?.formatted ?? ''),
                  ValueRow(context.t('ideas.investorPayback'), months(s.investorPaybackMonths)),
                ],
              ],
            ),
          ),
        for (final w in idea.warnings) Text(context.t('ideas.warning.$w'), style: TextStyle(color: p.warn)),
        const SizedBox(height: 6),
        Hint(context.t('ideas.disclaimer')),
        if (_drafting) ...[
          const SizedBox(height: 8),
          Field(label: context.t('ideas.providerName'), controller: _provider),
          const SizedBox(height: 8),
          Field(label: context.t('ideas.myName'), controller: _me),
          const SizedBox(height: 8),
          Align(
            alignment: Alignment.centerLeft,
            child: FilledButton(
              onPressed: busy
                  ? null
                  : () async {
                      final r = await act(
                        () => core.draftPartnershipFromIdea(
                          spaceId: widget.spaceId,
                          ideaId: idea.id,
                          input: IdeaDraftInput(capitalProviderName: _provider.text, myName: _me.text),
                        ),
                      );
                      if (r != null) shell.go('partnerships', focus: {'id': decodeJs(r).s('id'), 'tab': 'contract'});
                    },
              child: Text(context.t('ideas.createDraft')),
            ),
          ),
        ],
        ErrorText(error),
        const SizedBox(height: 8),
        Wrap(
          spacing: 8,
          runSpacing: 8,
          children: [
            if (idea.partnershipId != null)
              OutlinedButton(
                onPressed: () => shell.go('partnerships', focus: {'id': idea.partnershipId!, 'tab': 'contract'}),
                child: Text(context.t('ideas.openDraft')),
              )
            else if (!_drafting)
              FilledButton(
                onPressed: () => setState(() => _drafting = true),
                child: Text(context.t('ideas.toContract')),
              ),
            OutlinedButton(onPressed: widget.onEdit, child: Text(context.t('ideas.edit'))),
            TextButton(
              onPressed: () => act(() => core.deleteVentureIdea(spaceId: widget.spaceId, ideaId: idea.id)),
              child: Text(context.t('ideas.delete')),
            ),
          ],
        ),
      ],
    );
  }
}
