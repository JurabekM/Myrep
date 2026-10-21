import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../app/i18n.dart';
import '../../app/theme.dart';
import '../../core/core.dart';
import '../../core/query.dart';
import '../../shared/files.dart';
import '../../shared/format.dart';
import '../../shared/widgets.dart';

const _taxBases = ['NONE', 'REVENUE', 'PROFIT', 'FIXED'];
const _split = ['reserve', 'working', 'expansion', 'sadaqa'];

String? _opt(String v) => v.trim().isEmpty ? null : v.trim();

MoneyDto _part(KkAllocationDto a, String k) => switch (k) {
  'reserve' => a.reserve,
  'working' => a.working,
  'expansion' => a.expansion,
  _ => a.sadaqa,
};

/// «Hisob kuni» (kasbkor/SPEC 4.5): oy yakunlari → soliq zaxirasi → egasi maoshi → qolgan pul va
/// taqsimot → bayonnoma. Hamma raqam yadrodan; bayonnoma yopilgandan keyin o'zgarmaydi.
class KkCloseScreen extends ConsumerStatefulWidget {
  const KkCloseScreen({required this.spaceId, super.key});

  final String spaceId;

  @override
  ConsumerState<KkCloseScreen> createState() => _KkCloseScreenState();
}

class _KkCloseScreenState extends ConsumerState<KkCloseScreen> {
  bool _editingRules = false;

  @override
  Widget build(BuildContext context) {
    final id = widget.spaceId;
    final draft = ref.watch(query(['kkClose', id], (c) => c.kkCloseDraft(spaceId: id)));
    final rules = ref.watch(query(['kkCloseRules', id], (c) => c.kkCloseRules(spaceId: id))).valueOrNull;
    final err = draft.hasError ? draft.error : null;
    final closed = err is AppError && err.code == 'ALREADY_CLOSED';
    return ScreenBody(
      mentorKey: 'mentor.kkClose',
      children: [
        Hint(context.t('kk.close.intro')),
        if (closed) SectionCard(children: [Text(context.t('kk.close.lastClosed'))]),
        if (err != null && !closed) ErrorText(err),
        if (rules != null)
          SectionCard(
            title: context.t('kk.close.rules'),
            trailing: TextButton(
              onPressed: () => setState(() => _editingRules = !_editingRules),
              child: Text(context.t('kk.close.rulesChange')),
            ),
            children: [
              _RulesSummary(rules),
              if (_editingRules)
                _RulesForm(
                  key: ValueKey(rules),
                  spaceId: id,
                  rules: rules,
                  onDone: () => setState(() => _editingRules = false),
                ),
            ],
          ),
        // Qayta so'rov xato bersa (masalan, oy yopildi), eski qoralama ko'rsatilmaydi.
        if (err == null && draft.valueOrNull != null)
          _Draft(key: ValueKey(draft.valueOrNull!.periodStart), spaceId: id, d: draft.valueOrNull!),
        _History(spaceId: id),
      ],
    );
  }
}

class _RulesSummary extends StatelessWidget {
  const _RulesSummary(this.rules);

  final KkCloseRulesDto rules;

  @override
  Widget build(BuildContext context) {
    final tax = switch (rules.taxBase) {
      'FIXED' => context.t('kk.close.taxFixedShow', {'amount': rules.taxFixed?.formatted ?? ''}),
      'NONE' => context.t('kk.close.taxNone'),
      _ => context.t('kk.close.taxShow.${rules.taxBase}', {'percent': rules.taxPercent}),
    };
    final split = context.t('kk.close.splitShow', {
      'reserve': rules.reservePercent,
      'working': rules.workingPercent,
      'expansion': rules.expansionPercent,
      'sadaqa': rules.sadaqaPercent,
    });
    return Text('$tax · $split');
  }
}

class _RulesForm extends ConsumerStatefulWidget {
  const _RulesForm({required this.spaceId, required this.rules, required this.onDone, super.key});

  final String spaceId;
  final KkCloseRulesDto rules;
  final VoidCallback onDone;

  @override
  ConsumerState<_RulesForm> createState() => _RulesFormState();
}

class _RulesFormState extends ConsumerState<_RulesForm> with ActionState {
  late String _base = widget.rules.taxBase;
  late final _taxPercent = TextEditingController(text: widget.rules.taxPercent);
  late final _taxFixed = TextEditingController(text: widget.rules.taxFixed?.plain ?? '');
  late final _parts = {
    'reserve': TextEditingController(text: widget.rules.reservePercent),
    'working': TextEditingController(text: widget.rules.workingPercent),
    'expansion': TextEditingController(text: widget.rules.expansionPercent),
    'sadaqa': TextEditingController(text: widget.rules.sadaqaPercent),
  };

  @override
  void dispose() {
    for (final c in [_taxPercent, _taxFixed, ..._parts.values]) {
      c.dispose();
    }
    super.dispose();
  }

  Future<void> _save() async {
    final r = await act(
      () => ref
          .read(coreProvider)
          .kkSetCloseRules(
            spaceId: widget.spaceId,
            input: KkCloseRulesInput(
              taxBase: _base,
              taxPercent: _base == 'REVENUE' || _base == 'PROFIT' ? _taxPercent.text : null,
              taxFixed: _base == 'FIXED' ? _taxFixed.text : null,
              reservePercent: _parts['reserve']!.text,
              workingPercent: _parts['working']!.text,
              expansionPercent: _parts['expansion']!.text,
              sadaqaPercent: _parts['sadaqa']!.text,
            ),
          ),
    );
    if (r != null) widget.onDone();
  }

  @override
  Widget build(BuildContext context) => Padding(
    padding: const EdgeInsets.only(top: 12),
    child: Semantics(
      container: true,
      label: context.t('kk.close.rulesForm'),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: [
          const Divider(),
          Text(context.t('kk.close.taxBase')),
          const SizedBox(height: 8),
          for (final b in _taxBases)
            ChoiceTile(
              label: context.t('kk.close.base.$b'),
              selected: _base == b,
              onTap: () => setState(() => _base = b),
            ),
          if (_base == 'REVENUE' || _base == 'PROFIT')
            Field(
              label: context.t('kk.close.taxPercent'),
              controller: _taxPercent,
              keyboardType: const TextInputType.numberWithOptions(decimal: true),
            ),
          if (_base == 'FIXED') AmountField(label: context.t('kk.close.taxFixed'), controller: _taxFixed),
          const SizedBox(height: 8),
          Hint(context.t('kk.close.taxDisclaimer')),
          const SizedBox(height: 12),
          Text(context.t('kk.close.splitLegend')),
          for (final k in _split)
            Padding(
              padding: const EdgeInsets.only(top: 8),
              child: Field(
                label: '${context.t('kk.close.part.$k')} (%)',
                controller: _parts[k]!,
                keyboardType: const TextInputType.numberWithOptions(decimal: true),
              ),
            ),
          ErrorText(error),
          const SizedBox(height: 8),
          Align(
            alignment: Alignment.centerLeft,
            child: FilledButton(onPressed: busy ? null : _save, child: Text(context.t('common.save'))),
          ),
        ],
      ),
    ),
  );
}

class _Draft extends ConsumerStatefulWidget {
  const _Draft({required this.spaceId, required this.d, super.key});

  final String spaceId;
  final KkCloseDraftDto d;

  @override
  ConsumerState<_Draft> createState() => _DraftState();
}

class _DraftState extends ConsumerState<_Draft> with ActionState {
  bool _carry = false;
  final _explanation = TextEditingController();

  @override
  void dispose() {
    _explanation.dispose();
    super.dispose();
  }

  Future<void> _close() => act(
    () => ref
        .read(coreProvider)
        .kkCloseMonth(
          spaceId: widget.spaceId,
          input: KkCloseInput(
            periodStart: widget.d.periodStart,
            carryOverdraw: _carry,
            explanation: _opt(_explanation.text),
          ),
        ),
  );

  @override
  Widget build(BuildContext context) {
    final d = widget.d;
    final pal = context.palette;
    final period = context.t('kk.period', {'from': showDate(d.periodStart), 'to': showDate(d.periodEnd)});
    final alloc = d.allocation;
    final salaryLeft = d.salaryRemaining;
    final overdrawn = d.overdrawn;
    return Semantics(
      container: true,
      label: context.t('kk.close.draft', {'period': period}),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: [
          SectionCard(
            title: context.t('kk.close.step1', {'period': period}),
            children: [
              ValueRow(context.t('kk.profit.revenue'), d.revenue.formatted),
              ValueRow(context.t('kk.close.expenses'), d.expenses.formatted),
              ValueRow(context.t('kk.trueProfitShort'), d.trueProfit.formatted),
              ValueRow(context.t('kk.profit.depreciation'), d.depreciation.formatted),
            ],
          ),
          const SizedBox(height: 12),
          SectionCard(
            title: context.t('kk.close.step2'),
            children: [
              ValueRow(
                context.t('kk.close.taxReserve'),
                '− ${d.tax.formatted}',
                key: const Key('kk-close-tax'),
              ),
              ValueRow(context.t('kk.close.ownerPay'), '− ${d.ownerPay.formatted}'),
              if (d.ownerSalary != null && salaryLeft != null && salaryLeft.minor != '0')
                Text(
                  context.t('kk.close.salaryNotPaid', {'amount': salaryLeft.formatted}),
                  style: TextStyle(color: pal.warn),
                ),
              if (overdrawn != null)
                CheckboxListTile(
                  contentPadding: EdgeInsets.zero,
                  controlAffinity: ListTileControlAffinity.leading,
                  value: _carry,
                  title: Text(context.t('kk.close.carry', {'amount': overdrawn.formatted})),
                  onChanged: (v) => setState(() => _carry = v ?? false),
                ),
            ],
          ),
          const SizedBox(height: 12),
          SectionCard(
            title: context.t('kk.close.step3'),
            children: [
              Hint(context.t('kk.close.remainingFormula')),
              const SizedBox(height: 6),
              Text(
                d.remaining.formatted,
                key: const Key('kk-close-remaining'),
                style: TextStyle(
                  fontSize: 28,
                  fontWeight: FontWeight.w700,
                  color: pal.accent,
                  fontFeatures: const [FontFeature.tabularFigures()],
                ),
              ),
              const SizedBox(height: 6),
              if (alloc != null)
                for (final k in _split)
                  ValueRow(context.t('kk.close.part.$k'), _part(alloc, k).formatted, key: Key('kk-close-$k'))
              else ...[
                Field(label: context.t('kk.close.explanation'), controller: _explanation, maxLines: 4),
                const SizedBox(height: 4),
                Text(context.t('kk.close.negative'), style: TextStyle(color: pal.warn)),
              ],
              if (d.reserveBelowDepreciation)
                Padding(
                  padding: const EdgeInsets.only(top: 8),
                  child: Text(
                    context.t('kk.close.reserveBelowDepreciation', {'amount': d.depreciation.formatted}),
                    style: TextStyle(color: pal.warn),
                  ),
                ),
            ],
          ),
          const SizedBox(height: 12),
          SectionCard(
            children: [
              Text(context.t('kk.close.finalWarning')),
              ErrorText(error),
              const SizedBox(height: 8),
              Align(
                alignment: Alignment.centerLeft,
                child: FilledButton(onPressed: busy ? null : _close, child: Text(context.t('kk.close.submit'))),
              ),
            ],
          ),
        ],
      ),
    );
  }
}

class _History extends ConsumerStatefulWidget {
  const _History({required this.spaceId});

  final String spaceId;

  @override
  ConsumerState<_History> createState() => _HistoryState();
}

class _HistoryState extends ConsumerState<_History> with ActionState {
  Future<void> _pdf(KkMonthCloseDto c) => act(() async {
    final bytes = await ref.read(coreProvider).kkMonthClosePdf(spaceId: widget.spaceId, closeId: c.id);
    await ref.read(shareFileProvider)(bytes, 'hisob-kuni-${c.summary.periodStart}.pdf', pdfMime);
  });

  @override
  Widget build(BuildContext context) {
    final id = widget.spaceId;
    final list = ref.watch(query(['kkCloses', id], (c) => c.kkMonthCloses(spaceId: id))).valueOrNull ?? const [];
    if (list.isEmpty) return const SizedBox.shrink();
    final pal = context.palette;
    return SectionCard(
      title: context.t('kk.close.history'),
      children: [
        for (final c in list)
          Builder(
            builder: (context) {
              final period = context.t('kk.period', {
                'from': showDate(c.summary.periodStart),
                'to': showDate(c.summary.periodEnd),
              });
              return Container(
                padding: const EdgeInsets.symmetric(vertical: 8),
                decoration: BoxDecoration(
                  border: Border(top: BorderSide(color: pal.line)),
                ),
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.stretch,
                  children: [
                    Text(period, style: const TextStyle(fontWeight: FontWeight.w600)),
                    ValueRow(context.t('kk.close.col.remaining'), c.summary.remaining.formatted),
                    ValueRow(
                      context.t('kk.close.col.reserve'),
                      c.summary.allocation?.reserve.formatted ?? '—',
                    ),
                    Row(
                      children: [
                        Expanded(
                          child: Hint('${context.t('kk.close.col.code')}: ${c.shortCode}'),
                        ),
                        Semantics(
                          label: context.t('kk.close.pdfNamed', {'period': period}),
                          excludeSemantics: true,
                          button: true,
                          child: OutlinedButton(
                            onPressed: busy ? null : () => _pdf(c),
                            child: Text(context.t('kk.close.pdf')),
                          ),
                        ),
                      ],
                    ),
                  ],
                ),
              );
            },
          ),
        ErrorText(error),
      ],
    );
  }
}
