import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../app/i18n.dart';
import '../app/theme.dart';
import '../core/core.dart';
import 'widgets.dart';

/// Kichik yorliq (badge): xavf, ogohlantirish yoki neytral.
class Tag extends StatelessWidget {
  const Tag(this.text, {this.tone = 'muted', super.key});

  final String text;

  /// `danger`, `warn` yoki `muted`.
  final String tone;

  @override
  Widget build(BuildContext context) {
    final p = context.palette;
    final c = switch (tone) {
      'danger' => p.danger,
      'warn' => p.warn,
      'accent' => p.accentText,
      _ => p.inkMuted,
    };
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 2),
      decoration: BoxDecoration(
        border: Border.all(color: tone == 'muted' ? p.line : c),
        borderRadius: BorderRadius.circular(6),
      ),
      child: Text(text, style: TextStyle(color: c, fontSize: 12)),
    );
  }
}

/// To'lov rejasi qatorlari: sana va summa matn sifatida yadroga yuboriladi (tekshiruv — yadroda).
class ScheduleEditor extends StatelessWidget {
  const ScheduleEditor({required this.rows, required this.onChanged, super.key});

  final List<ScheduleRow> rows;
  final VoidCallback onChanged;

  @override
  Widget build(BuildContext context) => Column(
    crossAxisAlignment: CrossAxisAlignment.stretch,
    children: [
      Text(context.t('receipt.schedule'), style: const TextStyle(fontWeight: FontWeight.w700)),
      const SizedBox(height: 8),
      for (final (i, r) in rows.indexed)
        Padding(
          padding: const EdgeInsets.only(bottom: 8),
          child: Row(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Expanded(
                child: DateField(
                  label: '${context.t('receipt.lineDate')} ${i + 1}',
                  value: r.date,
                  allowClear: false,
                  onChanged: (v) {
                    r.date = v;
                    onChanged();
                  },
                ),
              ),
              const SizedBox(width: 8),
              Expanded(
                child: AmountField(label: '${context.t('common.amount')} ${i + 1}', controller: r.amount),
              ),
              IconButton(
                tooltip: context.t('receipt.removeLine'),
                icon: const Icon(Icons.remove_circle_outline),
                onPressed: rows.length == 1
                    ? null
                    : () {
                        rows.removeAt(i).amount.dispose();
                        onChanged();
                      },
              ),
            ],
          ),
        ),
      Align(
        alignment: Alignment.centerLeft,
        child: OutlinedButton(
          onPressed: () {
            rows.add(ScheduleRow());
            onChanged();
          },
          child: Text(context.t('receipt.addLine')),
        ),
      ),
    ],
  );
}

/// Reja qatori (forma holati).
class ScheduleRow {
  ScheduleRow() : amount = TextEditingController();

  String? date;
  final TextEditingController amount;

  ScheduleLineInput toInput() => ScheduleLineInput(date: date ?? '', amount: amount.text);
}

const alternatives = ['QOROVUL', 'RELATIVE', 'SELL_ITEM'];

/// «To'xta va o'yla» savollari (uy/SPEC 2D.6). Taqiqlamaydi — faqat so'raydi.
class BorrowCheckFields extends StatelessWidget {
  const BorrowCheckFields({required this.value, required this.onChanged, super.key});

  final BorrowCheckInput value;
  final ValueChanged<BorrowCheckInput> onChanged;

  @override
  Widget build(BuildContext context) {
    final p = context.palette;
    return Container(
      padding: const EdgeInsets.all(12),
      decoration: BoxDecoration(
        border: Border.all(color: p.line),
        borderRadius: BorderRadius.circular(10),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: [
          Text(
            context.t('friction.title'),
            style: TextStyle(color: p.accentText, fontWeight: FontWeight.w700),
          ),
          const SizedBox(height: 4),
          Hint(context.t('friction.intro')),
          const SizedBox(height: 8),
          SegmentedChoice<String>(
            label: context.t('friction.need'),
            options: [
              for (final n in ['NECESSITY', 'LUXURY']) (n, context.t('friction.need.$n')),
            ],
            value: value.need,
            onChanged: (n) => onChanged(BorrowCheckInput(need: n, alternatives: value.alternatives)),
          ),
          const SizedBox(height: 8),
          Text(context.t('friction.alternatives')),
          for (final a in alternatives)
            CheckboxListTile(
              contentPadding: EdgeInsets.zero,
              dense: true,
              value: value.alternatives.contains(a),
              title: Text(context.t('friction.alt.$a')),
              onChanged: (on) => onChanged(
                BorrowCheckInput(
                  need: value.need,
                  alternatives: on ?? false
                      ? [...value.alternatives, a]
                      : value.alternatives.where((x) => x != a).toList(),
                ),
              ),
            ),
        ],
      ),
    );
  }
}

/// «To'xta va o'yla» natijasi: maslahatchi ogohlantirishlari, yuk va haqiqiy narx.
class FrictionResult extends StatelessWidget {
  const FrictionResult(this.preview, {super.key});

  final BorrowCheckDto preview;

  @override
  Widget build(BuildContext context) {
    final p = context.palette;
    return Semantics(
      liveRegion: true,
      child: Container(
        padding: const EdgeInsets.all(12),
        decoration: BoxDecoration(
          border: Border.all(color: p.warn),
          borderRadius: BorderRadius.circular(10),
        ),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.stretch,
          children: [
            Text(
              context.t('mentor.name'),
              style: TextStyle(color: p.accentText, fontWeight: FontWeight.w700),
            ),
            const SizedBox(height: 6),
            for (final w in preview.warnings)
              Text('• ${context.t('friction.warn.$w')}', style: TextStyle(color: w == 'RIBO' ? p.danger : null)),
            if (preview.warnings.isEmpty) Text('• ${context.t('friction.allClear')}'),
            if (preview.projectedLoadPercent != null)
              Text(context.t('friction.load', {'percent': preview.projectedLoadPercent})),
            Text(
              context.t('friction.cost', {
                'total': preview.trueCost.totalCost.formatted,
                'overpay': preview.trueCost.overpay.formatted,
              }),
            ),
            const SizedBox(height: 6),
            Hint(context.t('friction.notForbidden')),
          ],
        ),
      ),
    );
  }
}

/// Qarz yopildi (uy/SPEC 2D.9): nishonlash va bo'shagan oylik to'lovni «Kelajagim»ga yo'naltirish.
Future<void> celebrateIfClosed(BuildContext context, String spaceId, RepaymentResultDto r) async {
  if (!r.closed) return;
  await showBarakaDialog<void>(context, (_) => _Celebration(spaceId: spaceId, result: r));
}

class _Celebration extends ConsumerStatefulWidget {
  const _Celebration({required this.spaceId, required this.result});

  final String spaceId;
  final RepaymentResultDto result;

  @override
  ConsumerState<_Celebration> createState() => _CelebrationState();
}

class _CelebrationState extends ConsumerState<_Celebration> with ActionState {
  @override
  Widget build(BuildContext context) {
    final r = widget.result;
    final freed = r.freedMonthly;
    final p = context.palette;
    return AlertDialog(
      title: Text(
        r.debtFree ? context.t('celebrate.debtFree') : context.t('celebrate.closed'),
        style: TextStyle(color: p.accentText),
      ),
      content: Column(
        mainAxisSize: MainAxisSize.min,
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: [
          Text(r.debtFree ? context.t('celebrate.debtFreeText') : context.t('celebrate.closedText')),
          if (r.modeReturned) ...[const SizedBox(height: 8), Hint(context.t('celebrate.modeReturned'))],
          if (freed != null) ...[
            const SizedBox(height: 8),
            Text(context.t('celebrate.freed', {'amount': freed.formatted})),
          ],
          ErrorText(error),
        ],
      ),
      actions: [
        TextButton(onPressed: () => Navigator.of(context).pop(), child: Text(context.t('celebrate.later'))),
        if (freed != null)
          FilledButton(
            onPressed: busy
                ? null
                : () async {
                    final note = context.t('celebrate.vaultNote');
                    final ok = await act(
                      () => ref
                          .read(coreProvider)
                          .depositToVault(spaceId: widget.spaceId, amount: freed.plain, note: note),
                    );
                    if (ok != null && context.mounted) Navigator.of(context).pop();
                  },
            child: Text(context.t('celebrate.toVault')),
          ),
      ],
    );
  }
}
