import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../app/i18n.dart';
import '../../app/theme.dart';
import '../../core/core.dart';
import '../../core/query.dart';
import '../../shared/format.dart';
import '../../shared/widgets.dart';
import 'kk_shift_screen.dart' show KkShiftsTable;

const _reasons = ['UNRECORDED_EXPENSE', 'CHANGE_ERROR', 'GIVEN_ON_CREDIT', 'OWNER_TOOK', 'UNKNOWN'];

/// Kunlik kassa yopish (kasbkor/SPEC 5.1): ochilish → naqd tushum, chiqim, «egasi oldi», kartaga
/// topshirilgan → kutilgan → sanalgan → farq. Hisob yadroda; yopilgan kun o'zgarmaydi.
class KkCashScreen extends ConsumerWidget {
  const KkCashScreen({required this.spaceId, super.key});

  final String spaceId;

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final draft = ref.watch(query(['kkCash', spaceId], (c) => c.kkCashDraft(spaceId: spaceId)));
    final err = draft.error;
    final closed = err is AppError && err.code == 'CASH_DAY_CLOSED';
    final d = draft.valueOrNull;
    return ScreenBody(
      mentorKey: 'mentor.kkCash',
      children: [
        Hint(context.t('kk.cash.intro')),
        if (closed)
          Semantics(liveRegion: true, child: SectionCard(children: [Text(context.t('kk.cash.todayClosed'))]))
        else if (err != null)
          ErrorText(err)
        else if (d != null)
          _CloseForm(key: ValueKey(d.day), spaceId: spaceId, d: d),
        _History(spaceId: spaceId),
        KkShiftsTable(spaceId: spaceId, title: context.t('kk.shift.sellers'), hideEmpty: true),
      ],
    );
  }
}

class _CloseForm extends ConsumerStatefulWidget {
  const _CloseForm({required this.spaceId, required this.d, super.key});

  final String spaceId;
  final KkCashDraftDto d;

  @override
  ConsumerState<_CloseForm> createState() => _CloseFormState();
}

class _CloseFormState extends ConsumerState<_CloseForm> with ActionState {
  final _counted = TextEditingController();
  final _note = TextEditingController();
  String? _reason;
  KkCashDraftDto? _checked;
  String _checkedFor = '';

  @override
  void initState() {
    super.initState();
    // Sanalgan summa o'zgarsa, eski tekshiruv natijasi tashlanadi.
    _counted.addListener(() {
      if (_checked != null && _counted.text != _checkedFor) setState(() => _checked = null);
    });
  }

  @override
  void dispose() {
    _counted.dispose();
    _note.dispose();
    super.dispose();
  }

  Future<void> _check() async {
    final counted = _counted.text;
    final r = await act(
      () => ref.read(coreProvider).kkCashDraft(spaceId: widget.spaceId, day: widget.d.day, counted: counted),
    );
    if (r != null) {
      setState(() {
        _checked = r;
        _checkedFor = counted;
      });
    }
  }

  Future<void> _close() async {
    final note = _note.text.trim();
    await act(
      () => ref
          .read(coreProvider)
          .kkCloseCashDay(
            spaceId: widget.spaceId,
            input: KkCashCloseInput(
              day: widget.d.day,
              counted: _counted.text,
              reason: _reason,
              note: note.isEmpty ? null : note,
            ),
          ),
    );
  }

  @override
  Widget build(BuildContext context) {
    final d = widget.d;
    final p = context.palette;
    final checked = _checked;
    final status = checked?.status;
    return Column(
      crossAxisAlignment: CrossAxisAlignment.stretch,
      children: [
        SectionCard(
          title: context.t('kk.cash.day', {'date': showDate(d.day)}),
          children: [
            ValueRow(context.t('kk.cash.opening'), d.opening.formatted, key: const Key('kk-cash-opening')),
            ValueRow(context.t('kk.cash.sales'), '+ ${d.cashSales.formatted}'),
            ValueRow(context.t('kk.cash.expenses'), '− ${d.cashExpenses.formatted}'),
            ValueRow(context.t('kk.cash.ownerDraws'), '− ${d.ownerDraws.formatted}'),
            ValueRow(context.t('kk.cash.handedOver'), '− ${d.handedOver.formatted}'),
            if (d.otherIn.minor != '0') ValueRow(context.t('kk.cash.otherIn'), '+ ${d.otherIn.formatted}'),
            if (d.otherOut.minor != '0') ValueRow(context.t('kk.cash.otherOut'), '− ${d.otherOut.formatted}'),
            Container(
              decoration: BoxDecoration(
                border: Border(top: BorderSide(color: p.line)),
              ),
              child: ValueRow(
                context.t('kk.cash.expected'),
                d.expected.formatted,
                strong: true,
                key: const Key('kk-cash-expected'),
              ),
            ),
          ],
        ),
        const SizedBox(height: 12),
        SectionCard(
          semanticLabel: context.t('kk.cash.countForm'),
          children: [
            AmountField(label: context.t('kk.cash.counted'), controller: _counted),
            const SizedBox(height: 8),
            Align(
              alignment: Alignment.centerLeft,
              child: OutlinedButton(
                onPressed: busy ? null : _check,
                child: Text(context.t('kk.cash.check')),
              ),
            ),
            if (checked == null) ErrorText(error),
            if (checked != null && checked.difference != null) ...[
              const SizedBox(height: 12),
              Semantics(
                liveRegion: true,
                child: Text(
                  context.t('kk.cash.status.$status', {'amount': checked.difference!.formatted}),
                  key: const Key('kk-cash-difference'),
                  style: TextStyle(fontSize: 18, color: status == 'EXACT' ? null : p.warn),
                ),
              ),
              if (checked.suggestSearch) ...[
                const SizedBox(height: 6),
                Text(context.t('kk.cash.suggestSearch'), style: TextStyle(color: p.warn)),
              ],
              if (status != 'EXACT') ...[
                const SizedBox(height: 12),
                Text(context.t('kk.cash.reason')),
                const SizedBox(height: 6),
                for (final r in _reasons)
                  ChoiceTile(
                    label: context.t('kk.cash.reasons.$r'),
                    selected: _reason == r,
                    onTap: () => setState(() => _reason = r),
                  ),
                Field(label: context.t('kk.note'), controller: _note),
              ],
              const SizedBox(height: 8),
              Hint(context.t('kk.cash.finalWarning')),
              ErrorText(error),
              const SizedBox(height: 8),
              Align(
                alignment: Alignment.centerLeft,
                child: FilledButton(onPressed: busy ? null : _close, child: Text(context.t('kk.cash.close'))),
              ),
            ],
          ],
        ),
      ],
    );
  }
}

class _History extends ConsumerWidget {
  const _History({required this.spaceId});

  final String spaceId;

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final days = ref.watch(query(['kkCashDays', spaceId], (c) => c.kkCashDays(spaceId: spaceId))).valueOrNull;
    if (days == null || days.isEmpty) return const SizedBox.shrink();
    final p = context.palette;
    return SectionCard(
      title: context.t('kk.cash.history'),
      children: [
        for (final c in days.take(31))
          Container(
            padding: const EdgeInsets.symmetric(vertical: 6),
            decoration: BoxDecoration(
              border: Border(top: BorderSide(color: p.line)),
            ),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.stretch,
              children: [
                Text(showDate(c.day), style: const TextStyle(fontWeight: FontWeight.w600)),
                ValueRow(context.t('kk.cash.expected'), c.expected.formatted),
                ValueRow(context.t('kk.cash.countedShort'), c.counted.formatted),
                ValueRow(
                  context.t('kk.cash.difference'),
                  c.difference.formatted,
                  valueColor: c.status == 'EXACT' ? null : p.warn,
                ),
                if (c.reason != null)
                  Hint('${context.t('kk.cash.reason')}: ${context.t('kk.cash.reasons.${c.reason}')}'),
                if (c.note != null) Hint(c.note!),
              ],
            ),
          ),
      ],
    );
  }
}
