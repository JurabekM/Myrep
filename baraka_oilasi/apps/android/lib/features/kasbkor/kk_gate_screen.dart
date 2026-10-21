import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../app/i18n.dart';
import '../../app/shell_state.dart';
import '../../app/theme.dart';
import '../../core/core.dart';
import '../../core/query.dart';
import '../../shared/widgets.dart';
import '../venture/offer_check.dart';

const _usable = ['RESERVE', 'WORKING', 'EXPANSION', 'SADAQA'];

String? _opt(String v) => v.trim().isEmpty ? null : v.trim();

/// Kengayish darvozasi (kasbkor/SPEC 6): beshala shart va har biri uchun keyingi qadam; «Hisob kuni»
/// konvertlari (soliq zaxirasi — 8.2); foizli kreditga halol muqobillar. Hisob yadroda.
class KkGateScreen extends ConsumerWidget {
  const KkGateScreen({required this.spaceId, super.key});

  final String spaceId;

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final id = spaceId;
    final gate = ref.watch(query(['kkGate', id], (c) => c.kkGate(spaceId: id)));
    final settings = ref.watch(query(['kkGrowthSettings', id], (c) => c.kkGrowthSettings(spaceId: id))).valueOrNull;
    final g = gate.valueOrNull;
    final pal = context.palette;
    return ScreenBody(
      mentorKey: 'mentor.kkGate',
      children: [
        Hint(context.t('kk.gate.intro')),
        if (gate.hasError) ErrorText(gate.error),
        if (g != null) ...[
          Card(
            key: const Key('kk-gate-status'),
            shape: RoundedRectangleBorder(
              borderRadius: BorderRadius.circular(12),
              side: BorderSide(color: g.open ? pal.accent : pal.warn),
            ),
            child: Padding(
              padding: const EdgeInsets.all(16),
              child: Semantics(
                liveRegion: true,
                child: Text(
                  g.open ? context.t('kk.gate.open') : context.t('kk.gate.closed', {'count': g.reasons.length}),
                  style: TextStyle(
                    fontSize: 20,
                    fontWeight: FontWeight.w700,
                    color: g.open ? pal.accentText : pal.warn,
                  ),
                ),
              ),
            ),
          ),
          _Conditions(g),
          _Funds(spaceId: id, g: g),
        ],
        const _Alternatives(),
        if (settings != null) _Thresholds(key: ValueKey(settings), spaceId: id, s: settings),
      ],
    );
  }
}

class _Conditions extends ConsumerWidget {
  const _Conditions(this.g);

  final KkGateDto g;

  String _detail(BuildContext context, String code) => switch (code) {
    'RESERVE' =>
      g.requiredReserve != null
          ? context.t('kk.gate.detail.RESERVE', {
              'reserve': g.reserve.formatted,
              'required': g.requiredReserve!.formatted,
              'months': g.requiredMonths,
              'coverage': g.coverageMonths ?? '—',
            })
          : context.t('kk.gate.detail.RESERVE_NO_HISTORY', {'reserve': g.reserve.formatted}),
    'PROFIT' =>
      g.trueProfits.isNotEmpty
          ? context.t('kk.gate.detail.PROFIT', {'list': g.trueProfits.map((p) => p.formatted).join(' · ')})
          : context.t('kk.gate.detail.PROFIT_NONE'),
    'RECEIVABLES' => context.t('kk.gate.detail.RECEIVABLES', {
      'bad': g.badDebtPercent,
      'max': g.maxBadPercent,
      'amount': g.receivables90.formatted,
    }),
    'INTEREST_DEBT' =>
      g.hasInterestDebt
          ? context.t(g.hasPayoffPlan ? 'kk.gate.detail.DEBT_PLAN' : 'kk.gate.detail.DEBT_NO_PLAN')
          : context.t('kk.gate.detail.NO_DEBT'),
    _ => context.t('kk.gate.detail.PLAN', {'count': g.plans}),
  };

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final pal = context.palette;
    return SectionCard(
      title: context.t('kk.gate.conditions'),
      children: [
        for (final (i, c) in g.conditions.indexed)
          Container(
            key: Key('kk-gate-${c.code}'),
            padding: const EdgeInsets.symmetric(vertical: 10),
            decoration: BoxDecoration(
              border: Border(top: BorderSide(color: pal.line)),
            ),
            child: Row(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                ExcludeSemantics(
                  child: Text(
                    c.ok ? '✓' : '✗',
                    style: TextStyle(fontSize: 18, color: c.ok ? pal.accentText : pal.warn),
                  ),
                ),
                const SizedBox(width: 12),
                Expanded(
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.stretch,
                    children: [
                      Semantics(
                        label:
                            '${i + 1}. ${context.t('kk.gate.cond.${c.code}')}, '
                            '${context.t(c.ok ? 'kk.gate.met' : 'kk.gate.notMet')}',
                        excludeSemantics: true,
                        child: Text(
                          '${i + 1}. ${context.t('kk.gate.cond.${c.code}')}',
                          style: const TextStyle(fontWeight: FontWeight.w600),
                        ),
                      ),
                      Hint(_detail(context, c.code)),
                      if (!c.ok) Text(context.t('kk.gate.next.${c.code}'), style: TextStyle(color: pal.warn)),
                      if (c.code == 'PLAN')
                        Align(
                          alignment: Alignment.centerLeft,
                          child: OutlinedButton(
                            onPressed: () => ref.read(shellProvider.notifier).go('ideas'),
                            child: Text(context.t('kk.gate.planButton')),
                          ),
                        ),
                    ],
                  ),
                ),
              ],
            ),
          ),
      ],
    );
  }
}

class _Funds extends ConsumerStatefulWidget {
  const _Funds({required this.spaceId, required this.g});

  final String spaceId;
  final KkGateDto g;

  @override
  ConsumerState<_Funds> createState() => _FundsState();
}

class _FundsState extends ConsumerState<_Funds> with ActionState {
  String _fund = 'RESERVE';
  final _amount = TextEditingController();
  final _note = TextEditingController();

  @override
  void dispose() {
    _amount.dispose();
    _note.dispose();
    super.dispose();
  }

  Future<void> _use() async {
    final r = await act(
      () => ref
          .read(coreProvider)
          .kkUseFund(
            spaceId: widget.spaceId,
            input: KkFundUseInput(fund: _fund, amount: _amount.text, note: _opt(_note.text)),
          ),
    );
    if (r != null) {
      _amount.clear();
      _note.clear();
    }
  }

  @override
  Widget build(BuildContext context) {
    final pal = context.palette;
    return SectionCard(
      title: context.t('kk.funds.title'),
      children: [
        Hint(context.t('kk.funds.intro')),
        const SizedBox(height: 8),
        for (final f in widget.g.funds)
          Container(
            margin: const EdgeInsets.only(top: 8),
            padding: const EdgeInsets.all(12),
            decoration: BoxDecoration(
              border: Border.all(color: pal.line),
              borderRadius: BorderRadius.circular(8),
            ),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Hint(context.t('kk.funds.name.${f.fund}')),
                Text(
                  f.balance.formatted,
                  key: Key('kk-fund-${f.fund}'),
                  style: const TextStyle(
                    fontSize: 20,
                    fontWeight: FontWeight.w700,
                    fontFeatures: [FontFeature.tabularFigures()],
                  ),
                ),
                Hint(context.t('kk.funds.flow', {'added': f.added.formatted, 'used': f.used.formatted})),
              ],
            ),
          ),
        const SizedBox(height: 8),
        Hint(context.t('kk.funds.taxHint')),
        const Divider(height: 24),
        Semantics(
          container: true,
          label: context.t('kk.funds.use'),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.stretch,
            children: [
              Select<String>(
                label: context.t('kk.funds.fund'),
                items: [for (final f in _usable) (f, context.t('kk.funds.name.$f'))],
                value: _fund,
                onChanged: (v) => setState(() => _fund = v ?? _fund),
              ),
              const SizedBox(height: 12),
              AmountField(label: context.t('kk.funds.amount'), controller: _amount),
              const SizedBox(height: 12),
              Field(label: context.t('kk.funds.note'), controller: _note),
              ErrorText(error),
              const SizedBox(height: 8),
              Align(
                alignment: Alignment.centerLeft,
                child: FilledButton(onPressed: busy ? null : _use, child: Text(context.t('kk.funds.useButton'))),
              ),
            ],
          ),
        ),
      ],
    );
  }
}

class _Alternatives extends ConsumerWidget {
  const _Alternatives();

  @override
  Widget build(BuildContext context, WidgetRef ref) => SectionCard(
    title: context.t('kk.gate.altTitle'),
    children: [
      for (final k in ['SAVINGS', 'PARTNERSHIP', 'SUPPLIER', 'QARZ'])
        Padding(padding: const EdgeInsets.only(bottom: 4), child: Text('• ${context.t('kk.gate.alt.$k')}')),
      const SizedBox(height: 4),
      Hint(context.t('kk.gate.altNoAds')),
      const SizedBox(height: 8),
      Wrap(
        spacing: 8,
        runSpacing: 8,
        children: [
          OutlinedButton(
            onPressed: () => ref.read(shellProvider.notifier).go('kkSuppliers'),
            child: Text(context.t('nav.kkSuppliers')),
          ),
          OutlinedButton(onPressed: () => openOfferCheck(context), child: Text(context.t('kk.gate.checkOffer'))),
        ],
      ),
    ],
  );
}

/// Darvoza chegaralari (OQ-K6): boshqa sozlamalar o'zgarmaydi.
class _Thresholds extends ConsumerStatefulWidget {
  const _Thresholds({required this.spaceId, required this.s, super.key});

  final String spaceId;
  final KkGrowthSettingsDto s;

  @override
  ConsumerState<_Thresholds> createState() => _ThresholdsState();
}

class _ThresholdsState extends ConsumerState<_Thresholds> with ActionState {
  late final _months = TextEditingController(text: '${widget.s.reserveMonths}');
  late final _bad = TextEditingController(text: widget.s.maxBadPercent);

  @override
  void dispose() {
    _months.dispose();
    _bad.dispose();
    super.dispose();
  }

  Future<void> _save() {
    final s = widget.s;
    return act(
      () => ref
          .read(coreProvider)
          .kkSetGrowthSettings(
            spaceId: widget.spaceId,
            input: KkGrowthSettingsInput(
              reserveMonths: int.tryParse(_months.text.trim()) ?? 0,
              maxBadPercent: _bad.text,
              zakatMonth: s.zakatMonth,
              zakatDay: s.zakatDay,
              goldPrice: s.goldPrice?.plain,
              nisabGrams: s.nisabGrams,
              stockValuation: s.stockValuation,
              scaleReminder: s.scaleReminder,
            ),
          ),
    );
  }

  @override
  Widget build(BuildContext context) => SectionCard(
    title: context.t('kk.gate.thresholds'),
    children: [
      Field(label: context.t('kk.gate.reserveMonths'), controller: _months, keyboardType: TextInputType.number),
      const SizedBox(height: 12),
      Field(
        label: context.t('kk.gate.maxBad'),
        controller: _bad,
        keyboardType: const TextInputType.numberWithOptions(decimal: true),
      ),
      ErrorText(error),
      const SizedBox(height: 8),
      Align(
        alignment: Alignment.centerLeft,
        child: OutlinedButton(onPressed: busy ? null : _save, child: Text(context.t('common.save'))),
      ),
    ],
  );
}
