import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../app/i18n.dart';
import '../../app/theme.dart';
import '../../core/core.dart';
import '../../core/query.dart';
import '../../shared/format.dart';
import '../../shared/widgets.dart';

const _reasons = ['UNRECORDED_EXPENSE', 'CHANGE_ERROR', 'GIVEN_ON_CREDIT', 'OWNER_TOOK', 'UNKNOWN'];

String? _opt(String v) => v.trim().isEmpty ? null : v.trim();

/// Sotuvchi smenasi (ADR-0003, `kk_shift_close`): ochilish (oldingi smenada qolgani), o'z naqd
/// tushumi va nasiya to'lovlari → kutilgan; sanalgan → farq; egasiga topshirilgan → keyingi smenaga
/// qolgani.
class KkShiftScreen extends ConsumerWidget {
  const KkShiftScreen({required this.spaceId, super.key});

  final String spaceId;

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final id = spaceId;
    final draft = ref.watch(
      query(['kkShiftDraft', id, null, null, null], (c) => c.kkShiftDraft(spaceId: id, input: const KkShiftInput())),
    );
    final d = draft.hasError ? null : draft.valueOrNull;
    return ScreenBody(
      mentorKey: 'mentor.kkShift',
      children: [
        Hint(context.t('kk.shift.intro')),
        if (draft.hasError) ErrorText(draft.error),
        if (d?.closed ?? false)
          SectionCard(children: [Semantics(liveRegion: true, child: Text(context.t('kk.shift.closedToday')))]),
        if (d != null && !d.closed) _ShiftForm(key: ValueKey(d.day), spaceId: id, base: d),
        KkShiftsTable(spaceId: id, title: context.t('kk.shift.history')),
      ],
    );
  }
}

class _ShiftForm extends ConsumerStatefulWidget {
  const _ShiftForm({required this.spaceId, required this.base, super.key});

  final String spaceId;
  final KkShiftDto base;

  @override
  ConsumerState<_ShiftForm> createState() => _ShiftFormState();
}

class _ShiftFormState extends ConsumerState<_ShiftForm> with ActionState {
  final _opening = TextEditingController();
  final _counted = TextEditingController();
  final _handed = TextEditingController();
  final _note = TextEditingController();
  String? _reason;

  @override
  void initState() {
    super.initState();
    // Har o'zgarishda yadro qayta hisoblaydi (UI hisoblamaydi).
    for (final c in [_opening, _counted, _handed]) {
      c.addListener(() => setState(() {}));
    }
  }

  @override
  void dispose() {
    for (final c in [_opening, _counted, _handed, _note]) {
      c.dispose();
    }
    super.dispose();
  }

  String? get _openingValue => widget.base.openingKnown ? null : _opt(_opening.text);

  Future<void> _close() => act(
    () => ref
        .read(coreProvider)
        .kkCloseShift(
          spaceId: widget.spaceId,
          input: KkShiftInput(
            opening: _openingValue,
            counted: _opt(_counted.text),
            handedOver: _opt(_handed.text),
            reason: _reason,
            note: _opt(_note.text),
          ),
        ),
  );

  @override
  Widget build(BuildContext context) {
    final id = widget.spaceId;
    final base = widget.base;
    final pal = context.palette;
    final opening = _openingValue;
    final counted = _opt(_counted.text);
    final handed = _opt(_handed.text);
    final preview = ref.watch(
      query(
        ['kkShiftDraft', id, opening, counted, handed],
        (c) => c.kkShiftDraft(
          spaceId: id,
          input: KkShiftInput(opening: opening, counted: counted, handedOver: handed),
        ),
      ),
    );
    final p = preview.hasError ? base : (preview.valueOrNull ?? base);
    final diff = p.difference;
    final left = p.left;
    return SectionCard(
      title: context.t('kk.shift.day', {'date': showDate(p.day)}),
      semanticLabel: context.t('kk.shift.form'),
      children: [
        if (!base.openingKnown) ...[
          AmountField(label: context.t('kk.shift.openingInput'), controller: _opening),
          const SizedBox(height: 4),
          Hint(context.t('kk.shift.openingHint')),
          const SizedBox(height: 8),
        ],
        ValueRow(context.t('kk.shift.opening'), p.opening.formatted),
        ValueRow(context.t('kk.shift.cashSales'), '+ ${p.cashSales.formatted}'),
        ValueRow(context.t('kk.shift.creditPayments'), '+ ${p.creditPayments.formatted}'),
        ValueRow(
          context.t('kk.shift.expected'),
          p.expected.formatted,
          strong: true,
          key: const Key('kk-shift-expected'),
        ),
        const SizedBox(height: 4),
        Hint(context.t('kk.shift.cardInfo', {'amount': p.cardIn.formatted})),
        const SizedBox(height: 12),
        AmountField(label: context.t('kk.shift.counted'), controller: _counted),
        const SizedBox(height: 12),
        AmountField(label: context.t('kk.shift.handedOver'), controller: _handed),
        if (diff != null) ...[
          const SizedBox(height: 12),
          Semantics(
            liveRegion: true,
            child: Text(
              context.t('kk.cash.status.${p.status}', {'amount': diff.formatted}),
              key: const Key('kk-shift-difference'),
              style: TextStyle(fontSize: 18, color: p.status == 'EXACT' ? null : pal.warn),
            ),
          ),
          if (left != null) Text(context.t('kk.shift.left', {'amount': left.formatted})),
          if (p.suggestSearch) Text(context.t('kk.cash.suggestSearch'), style: TextStyle(color: pal.warn)),
        ],
        if (p.status != null && p.status != 'EXACT') ...[
          const SizedBox(height: 12),
          Text(context.t('kk.cash.reason')),
          const SizedBox(height: 8),
          for (final r in _reasons)
            ChoiceTile(
              label: context.t('kk.cash.reasons.$r'),
              selected: _reason == r,
              onTap: () => setState(() => _reason = r),
            ),
        ],
        const SizedBox(height: 12),
        Field(label: context.t('kk.note'), controller: _note),
        const SizedBox(height: 8),
        Hint(context.t('kk.shift.finalWarning')),
        ErrorText(error),
        const SizedBox(height: 8),
        Align(
          alignment: Alignment.centerLeft,
          child: FilledButton(onPressed: busy ? null : _close, child: Text(context.t('kk.shift.close'))),
        ),
      ],
    );
  }
}

/// Smenalar: egasida — barcha sotuvchilarniki («Kassa» bo'limida, `hideEmpty`), sotuvchida — o'ziniki.
class KkShiftsTable extends ConsumerWidget {
  const KkShiftsTable({required this.spaceId, required this.title, this.hideEmpty = false, super.key});

  final String spaceId;
  final String title;
  final bool hideEmpty;

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final id = spaceId;
    final pal = context.palette;
    final shifts = ref.watch(query(['kkShifts', id], (c) => c.kkShifts(spaceId: id)));
    final rows = shifts.hasError ? const <KkShiftRecordDto>[] : (shifts.valueOrNull ?? const <KkShiftRecordDto>[]);
    if (hideEmpty && rows.isEmpty) return const SizedBox.shrink();
    return SectionCard(
      title: title,
      children: [
        if (shifts.hasError) ErrorText(shifts.error),
        if (rows.isEmpty && !shifts.hasError) Hint(context.t('kk.shift.none')),
        for (final s in rows)
          Container(
            key: ValueKey(('kk-shift-row', s)),
            padding: const EdgeInsets.symmetric(vertical: 8),
            decoration: BoxDecoration(
              border: Border(top: BorderSide(color: pal.line)),
            ),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.stretch,
              children: [
                Text(
                  '${showDate(s.day)} · ${s.deviceName}',
                  style: const TextStyle(fontWeight: FontWeight.w600),
                ),
                ValueRow(context.t('kk.shift.expected'), s.expected.formatted),
                ValueRow(context.t('kk.cash.countedShort'), s.counted.formatted),
                ValueRow(
                  context.t('kk.cash.difference'),
                  s.difference.formatted,
                  valueColor: s.status == 'EXACT' ? null : pal.warn,
                ),
                ValueRow(context.t('kk.shift.handedShort'), s.handedOver.formatted),
                Text.rich(
                  TextSpan(
                    children: [
                      TextSpan(
                        text: '${context.t('kk.cash.reason')}: ',
                        style: TextStyle(color: pal.inkMuted),
                      ),
                      TextSpan(text: s.reason != null ? context.t('kk.cash.reasons.${s.reason}') : '—'),
                      if (s.note != null)
                        TextSpan(
                          text: ' · ${s.note}',
                          style: TextStyle(color: pal.inkMuted),
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
