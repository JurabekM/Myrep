import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../app/i18n.dart';
import '../../app/theme.dart';
import '../../core/core.dart';
import '../../core/query.dart';
import '../../shared/format.dart';
import '../../shared/widgets.dart';

Color _tone(BuildContext context, String status) => switch (status) {
  'CLEARED' || 'ON_TRACK' => context.palette.accentText,
  'BEHIND' => context.palette.warn,
  _ => context.palette.inkMuted,
};

/// Yo'l qarzidan chiqish (musofir/SPEC 6.1, 4-qonun): Uy makonidagi U8 qarzi «yo'l qarzi» deb
/// belgilanadi; uyda «Qarz to'lovi» maqsadidan to'lanadi. Reja (necha oyda yopiladi) — yadrodan.
class TravelDebtCard extends ConsumerStatefulWidget {
  const TravelDebtCard({required this.spaceId, super.key});

  final String spaceId;

  @override
  ConsumerState<TravelDebtCard> createState() => _TravelDebtCardState();
}

class _TravelDebtCardState extends ConsumerState<TravelDebtCard> {
  bool _editing = false;

  @override
  Widget build(BuildContext context) {
    final sid = widget.spaceId;
    final q = ref.watch(query(['mfTravelDebt', sid], (c) => c.mfTravelDebt(spaceId: sid)));
    final d = q.valueOrNull;
    return SectionCard(
      title: context.t('mf.travel.title'),
      children: [
        if (q.hasError) ErrorText(q.error),
        if (d != null && _editing)
          _TravelDebtForm(spaceId: sid, d: d, onDone: () => setState(() => _editing = false))
        else if (d != null) ...[
          _TravelDebtView(d),
          if (d.debt != null || d.candidates.isNotEmpty) ...[
            const SizedBox(height: 8),
            Align(
              alignment: Alignment.centerLeft,
              child: OutlinedButton(
                onPressed: () => setState(() => _editing = true),
                child: Text(context.t(d.debt != null ? 'mf.travel.change' : 'mf.travel.choose')),
              ),
            ),
          ],
        ],
      ],
    );
  }
}

class _TravelDebtView extends StatelessWidget {
  const _TravelDebtView(this.d);

  final MfTravelDebtDto d;

  @override
  Widget build(BuildContext context) {
    final debt = d.debt;
    if (debt == null) {
      return Hint(context.t(d.candidates.isEmpty ? 'mf.travel.noDebts' : 'mf.travel.intro'));
    }
    final p = d.plan;
    return Column(
      crossAxisAlignment: CrossAxisAlignment.stretch,
      children: [
        Text.rich(
          TextSpan(
            children: [
              TextSpan(
                text: debt.creditor,
                style: const TextStyle(fontWeight: FontWeight.w600),
              ),
              if (debt.reason != null)
                TextSpan(
                  text: ' · ${debt.reason}',
                  style: TextStyle(color: context.palette.inkMuted),
                ),
            ],
          ),
        ),
        if (p != null) ...[
          const SizedBox(height: 6),
          Text(
            context.t('mf.travel.status.${p.status}', {
              'months': p.monthsToClear ?? 0,
              'date': p.clearOn == null ? '' : showDate(p.clearOn!),
              'target': d.targetMonths,
              'amount': p.requiredMonthly.formatted,
            }),
            key: const Key('mf-travel-status'),
            style: TextStyle(color: _tone(context, p.status)),
          ),
          ValueRow(context.t('mf.travel.outstanding'), debt.outstanding.formatted),
          ValueRow(context.t('mf.travel.available'), p.available.formatted),
          ValueRow(
            context.t('mf.travel.remaining'),
            p.remaining.formatted,
            strong: true,
            key: const Key('mf-travel-remaining'),
          ),
          if (p.avgMonthly != null)
            ValueRow(context.t('mf.travel.avg', {'count': p.monthsUsed}), p.avgMonthly!.formatted),
          ValueRow(context.t('mf.travel.required', {'count': d.targetMonths}), p.requiredMonthly.formatted),
          if (p.status == 'BEHIND') Hint(context.t('mf.travel.raiseShare')),
        ],
        const SizedBox(height: 4),
        Hint(context.t('mf.travel.payWhere')),
      ],
    );
  }
}

class _TravelDebtForm extends ConsumerStatefulWidget {
  const _TravelDebtForm({required this.spaceId, required this.d, required this.onDone});

  final String spaceId;
  final MfTravelDebtDto d;
  final VoidCallback onDone;

  @override
  ConsumerState<_TravelDebtForm> createState() => _TravelDebtFormState();
}

class _TravelDebtFormState extends ConsumerState<_TravelDebtForm> with ActionState {
  late String _debtId = widget.d.debt?.id ?? widget.d.candidates.firstOrNull?.id ?? '';
  late final _months = TextEditingController(text: '${widget.d.targetMonths}');

  @override
  void dispose() {
    _months.dispose();
    super.dispose();
  }

  Future<void> _save(String? id) async {
    final r = await act(
      () => ref
          .read(coreProvider)
          .mfSetTravelDebt(
            spaceId: widget.spaceId,
            input: MfTravelDebtInput(debtId: id, targetMonths: int.tryParse(_months.text.trim())),
          ),
    );
    if (r != null) widget.onDone();
  }

  @override
  Widget build(BuildContext context) {
    final d = widget.d;
    final debt = d.debt;
    final options = debt != null && !d.candidates.any((c) => c.id == debt.id) ? [debt, ...d.candidates] : d.candidates;
    return Column(
      crossAxisAlignment: CrossAxisAlignment.stretch,
      children: [
        Select<String>(
          label: context.t('mf.travel.which'),
          items: [for (final c in options) (c.id, '${c.creditor} · ${c.outstanding.formatted}')],
          value: _debtId,
          onChanged: (v) => setState(() => _debtId = v ?? _debtId),
        ),
        const SizedBox(height: 12),
        Field(
          label: context.t('mf.travel.targetMonths'),
          controller: _months,
          keyboardType: TextInputType.number,
        ),
        Hint(context.t('mf.travel.targetHint')),
        ErrorText(error),
        const SizedBox(height: 8),
        Wrap(
          spacing: 8,
          runSpacing: 8,
          children: [
            FilledButton(
              onPressed: busy || _debtId.isEmpty ? null : () => _save(_debtId),
              child: Text(context.t('common.save')),
            ),
            if (debt != null)
              OutlinedButton(onPressed: busy ? null : () => _save(null), child: Text(context.t('mf.travel.unmark'))),
            TextButton(onPressed: widget.onDone, child: Text(context.t('common.cancel'))),
          ],
        ),
      ],
    );
  }
}
