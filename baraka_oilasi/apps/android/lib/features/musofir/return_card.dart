import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../app/i18n.dart';
import '../../app/theme.dart';
import '../../core/core.dart';
import '../../core/query.dart';
import '../../shared/format.dart';
import '../../shared/widgets.dart';
import '../venture/offer_check.dart' show verdictColor;
import 'decision_screen.dart';

const _broughtCurrencies = ['UZS', 'USD', 'EUR', 'RUB', 'KRW', 'KZT', 'TRY', 'GBP'];

/// «Qaytdim» va sovutish davri (musofir/SPEC 6.3, 7-qonun): qaytgandan keyin 90 kun katta qarorlar
/// oldidan tekshiruv. Qaror taqiqlanmaydi — tanlov o'zgarmas jurnalga yoziladi (oilaga yuborilmaydi).
class ReturnCard extends ConsumerStatefulWidget {
  const ReturnCard({required this.spaceId, required this.d, required this.homeCurrency, super.key});

  final String spaceId;
  final MfOverviewDto d;
  final String homeCurrency;

  @override
  ConsumerState<ReturnCard> createState() => _ReturnCardState();
}

class _ReturnCardState extends ConsumerState<ReturnCard> with ActionState {
  bool _editing = false;

  Future<void> _clear() => act(
    () => ref
        .read(coreProvider)
        .mfSetReturn(
          spaceId: widget.spaceId,
          input: const MfReturnInput(),
        ),
  );

  @override
  Widget build(BuildContext context) {
    final c = widget.d.cooling;
    final pal = context.palette;
    return SectionCard(
      title: context.t('mf.return.title'),
      children: [
        if (_editing)
          _ReturnForm(
            spaceId: widget.spaceId,
            d: widget.d,
            homeCurrency: widget.homeCurrency,
            onDone: () => setState(() => _editing = false),
          )
        else if (c != null) ...[
          Text(
            c.inCooling
                ? context.t('mf.return.cooling', {
                    'count': c.daysLeft,
                    'date': c.endsOn == null ? '' : showDate(c.endsOn!),
                  })
                : context.t('mf.return.over', {'date': c.endsOn == null ? '' : showDate(c.endsOn!)}),
            key: const Key('mf-cooling'),
            style: TextStyle(color: c.inCooling ? pal.warn : pal.accentText),
          ),
          const SizedBox(height: 4),
          Hint(
            [
              context.t('mf.return.returnedLine', {'date': showDate(c.returnedOn)}),
              if (c.broughtHome != null) context.t('mf.return.broughtLine', {'amount': c.broughtHome!.formatted}),
            ].join(' · '),
          ),
          if (c.broughtRate != null && c.broughtValue != null)
            Hint(context.t('mf.return.valueLine', {'amount': c.broughtValue!.formatted, 'rate': c.broughtRate})),
          const SizedBox(height: 4),
          if (c.wall != null)
            Column(
              key: const Key('mf-wall'),
              crossAxisAlignment: CrossAxisAlignment.stretch,
              children: [
                Text(context.t('mf.return.wallLine', {'wall': c.wall!.formatted})),
                if (c.free != null)
                  Text(
                    context.t('mf.return.freeLine', {'free': c.free!.formatted}),
                    style: TextStyle(color: pal.accentText, fontWeight: FontWeight.w600),
                  ),
                if (c.wallAvgMonthly != null)
                  Hint(
                    context.t('mf.return.wallHint', {'avg': c.wallAvgMonthly!.formatted, 'count': c.wallMonthsUsed}),
                  ),
              ],
            )
          else
            Hint(context.t('mf.return.noWall')),
          if (c.inCooling) Hint(context.t('mf.return.rule')),
          ErrorText(error),
          const SizedBox(height: 8),
          Wrap(
            spacing: 8,
            runSpacing: 8,
            children: [
              OutlinedButton(
                onPressed: () => setState(() => _editing = true),
                child: Text(context.t('mf.return.change')),
              ),
              OutlinedButton(onPressed: busy ? null : _clear, child: Text(context.t('mf.return.unmark'))),
            ],
          ),
        ] else ...[
          Hint(context.t('mf.return.intro')),
          const SizedBox(height: 8),
          Align(
            alignment: Alignment.centerLeft,
            child: OutlinedButton(
              onPressed: () => setState(() => _editing = true),
              child: Text(context.t('mf.return.mark')),
            ),
          ),
        ],
        const Divider(height: 24),
        _DecisionsLog(spaceId: widget.spaceId, homeCurrency: widget.homeCurrency),
      ],
    );
  }
}

class _ReturnForm extends ConsumerStatefulWidget {
  const _ReturnForm({required this.spaceId, required this.d, required this.homeCurrency, required this.onDone});

  final String spaceId;
  final MfOverviewDto d;
  final String homeCurrency;
  final VoidCallback onDone;

  @override
  ConsumerState<_ReturnForm> createState() => _ReturnFormState();
}

class _ReturnFormState extends ConsumerState<_ReturnForm> with ActionState {
  late String? _on = widget.d.cooling?.returnedOn;
  late final _brought = TextEditingController(text: widget.d.cooling?.broughtHome?.plain);
  late String _currency = widget.d.cooling?.broughtHome?.currency ?? widget.homeCurrency;
  final _rate = TextEditingController();

  @override
  void dispose() {
    _brought.dispose();
    _rate.dispose();
    super.dispose();
  }

  bool get _foreign => _currency != widget.homeCurrency;

  Future<void> _save() async {
    final r = await act(
      () => ref
          .read(coreProvider)
          .mfSetReturn(
            spaceId: widget.spaceId,
            input: MfReturnInput(
              returnedOn: _on,
              broughtHome: _brought.text.trim().isEmpty ? null : _brought.text.trim(),
              broughtCurrency: _currency,
              broughtRate: _foreign && _rate.text.trim().isNotEmpty ? _rate.text.trim() : null,
            ),
          ),
    );
    if (r != null) widget.onDone();
  }

  @override
  Widget build(BuildContext context) {
    final currencies = {..._broughtCurrencies, widget.homeCurrency, _currency}.toList();
    return Column(
      crossAxisAlignment: CrossAxisAlignment.stretch,
      children: [
        DateField(
          label: context.t('mf.return.date'),
          value: _on,
          allowClear: false,
          onChanged: (v) => setState(() => _on = v),
        ),
        const SizedBox(height: 12),
        AmountField(label: context.t('mf.return.brought', {'currency': _currency}), controller: _brought),
        const SizedBox(height: 12),
        Select<String>(
          label: context.t('mf.return.currency'),
          items: [for (final c in currencies) (c, c)],
          value: _currency,
          onChanged: (v) => setState(() => _currency = v ?? _currency),
        ),
        if (_foreign) ...[
          const SizedBox(height: 12),
          Field(
            label: context.t('mf.return.rate', {'currency': _currency, 'home': widget.homeCurrency}),
            controller: _rate,
            keyboardType: const TextInputType.numberWithOptions(decimal: true),
          ),
        ],
        Hint(context.t('mf.return.broughtHint')),
        ErrorText(error),
        const SizedBox(height: 8),
        Wrap(
          spacing: 8,
          children: [
            FilledButton(onPressed: busy || _on == null ? null : _save, child: Text(context.t('common.save'))),
            TextButton(onPressed: widget.onDone, child: Text(context.t('common.cancel'))),
          ],
        ),
      ],
    );
  }
}

/// Katta qarorlar jurnali (o'zgarmas): tekshiruv natijasi va musofirning tanlovi.
class _DecisionsLog extends ConsumerWidget {
  const _DecisionsLog({required this.spaceId, required this.homeCurrency});

  final String spaceId;
  final String homeCurrency;

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final q = ref.watch(query(['mfDecisions', spaceId], (c) => c.mfDecisions(spaceId: spaceId)));
    final list = q.valueOrNull ?? const <MfDecisionDto>[];
    return Column(
      crossAxisAlignment: CrossAxisAlignment.stretch,
      children: [
        Text(context.t('mf.decision.log'), style: const TextStyle(fontWeight: FontWeight.w700)),
        Hint(context.t('mf.decision.intro')),
        if (q.hasError) ErrorText(q.error),
        for (final x in list) _DecisionRow(spaceId: spaceId, x: x),
        const SizedBox(height: 8),
        Align(
          alignment: Alignment.centerLeft,
          child: FilledButton(
            onPressed: () => openDecisionCheck(context, spaceId, homeCurrency),
            child: Text(context.t('mf.decision.open')),
          ),
        ),
      ],
    );
  }
}

class _DecisionRow extends ConsumerStatefulWidget {
  const _DecisionRow({required this.spaceId, required this.x});

  final String spaceId;
  final MfDecisionDto x;

  @override
  ConsumerState<_DecisionRow> createState() => _DecisionRowState();
}

class _DecisionRowState extends ConsumerState<_DecisionRow> with ActionState {
  /// Qaror natijasi (M4): bir marta — «qildim» yoki «qilmadim»; o'zgarmas.
  Future<void> _set(String o) => act(
    () => ref
        .read(coreProvider)
        .mfSetOutcome(
          spaceId: widget.spaceId,
          decisionId: widget.x.id,
          input: MfOutcomeInput(outcome: o),
        ),
  );

  @override
  Widget build(BuildContext context) {
    final x = widget.x;
    final outcome = x.outcome;
    final pal = context.palette;
    return Container(
      key: const Key('mf-decision'),
      padding: const EdgeInsets.symmetric(vertical: 6),
      decoration: BoxDecoration(
        border: Border(top: BorderSide(color: pal.line)),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: [
          Text('${showDate(x.decidedOn)} · ${x.title} · ${x.amount.formatted}'),
          Text.rich(
            TextSpan(
              children: [
                TextSpan(
                  text: context.t('mf.verdict.${x.verdict}'),
                  style: TextStyle(color: verdictColor(context, x.verdict)),
                ),
                TextSpan(text: ' · ${context.t('mf.choice.${x.choice}')}'),
              ],
            ),
          ),
          if (outcome != null)
            Hint(
              context.t('mf.outcome.line.${outcome.outcome}', {'date': showDate(outcome.outcomeOn)}),
              key: const Key('mf-decision-outcome'),
            )
          else
            Semantics(
              container: true,
              label: context.t('mf.outcome.ask'),
              child: Wrap(
                spacing: 8,
                crossAxisAlignment: WrapCrossAlignment.center,
                children: [
                  Hint(context.t('mf.outcome.ask')),
                  for (final o in ['DONE', 'DROPPED'])
                    TextButton(onPressed: busy ? null : () => _set(o), child: Text(context.t('mf.outcome.$o'))),
                ],
              ),
            ),
          ErrorText(error),
        ],
      ),
    );
  }
}
