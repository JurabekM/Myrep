import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../app/i18n.dart';
import '../../app/theme.dart';
import '../../core/core.dart';
import '../../core/query.dart';
import '../../shared/format.dart';
import '../../shared/widgets.dart';
import 'mf_entry_sheet.dart';
import 'purpose_shares.dart';

ProviderListenable<AsyncValue<MfTwoShoresDto>> mfTwoShoresQuery(String mfSpaceId) =>
    query(['mfTwoShores', mfSpaceId], (c) => c.mfTwoShores(spaceId: mfSpaceId));

/// Maqsadlar qoldig'i (yadrodan tayyor): olingan, sarflangan, qoldiq. Telefon uchun — har maqsad
/// alohida blok.
class PurposesTable extends StatelessWidget {
  const PurposesTable(this.v, {super.key});

  final MfTwoShoresDto v;

  @override
  Widget build(BuildContext context) {
    final pal = context.palette;
    if (v.purposes.isEmpty) return Hint(context.t('mf.shores.noneYet'));
    Widget block(
      String title,
      String received,
      String spent,
      String balance, {
      Color? tone,
      Key? key,
      bool strong = false,
    }) => Container(
      margin: const EdgeInsets.only(top: 8),
      padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 4),
      decoration: BoxDecoration(
        border: Border.all(color: pal.line),
        borderRadius: BorderRadius.circular(8),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: [
          Padding(
            padding: const EdgeInsets.only(top: 6),
            child: Text(title, style: TextStyle(fontWeight: strong ? FontWeight.w700 : FontWeight.w600)),
          ),
          ValueRow(context.t('mf.shores.received'), received),
          ValueRow(context.t('mf.shores.spent'), spent),
          ValueRow(context.t('mf.shores.balance'), balance, strong: true, valueColor: tone, key: key),
        ],
      ),
    );
    return Column(
      crossAxisAlignment: CrossAxisAlignment.stretch,
      children: [
        for (final p in v.purposes)
          KeyedSubtree(
            key: Key('mf-purpose-${p.purpose}'),
            child: block(
              context.t('mf.purpose.${p.purpose}'),
              p.received.formatted,
              p.spent.formatted,
              p.balance.formatted,
              tone: p.overspent ? pal.warn : null,
            ),
          ),
        block(
          context.t('mf.shores.total'),
          v.received.formatted,
          v.spent.formatted,
          v.balance.formatted,
          key: const Key('mf-shores-balance'),
          strong: true,
        ),
      ],
    );
  }
}

/// Uy tomoni «Ikki qirg'oq» (musofir/SPEC 5): kelgan pulni qabul qilish (Uy makonida daromad),
/// maqsad bo'yicha xarajat va maqsadlar qoldig'i. Uydagi oila qurilmasida (ADR-0004) musofirning
/// shaxsiy ma'lumoti yo'q — bu ekran faqat yuborilganlar bilan ishlaydi.
class TwoShoresScreen extends ConsumerWidget {
  const TwoShoresScreen({required this.mfSpaceId, required this.uySpaceId, super.key});

  final String mfSpaceId;
  final String uySpaceId;

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final v = ref.watch(mfTwoShoresQuery(mfSpaceId));
    final members = ref.watch(query(['household'], (c) => c.household())).valueOrNull?.members ?? const [];
    final d = v.valueOrNull;
    final pal = context.palette;
    return ScreenBody(
      mentorKey: 'mentor.twoShores',
      children: [
        Hint(context.t('mf.shores.intro')),
        if (v.hasError) ErrorText(v.error),
        if (d != null) ...[
          if (d.overspent)
            Container(
              key: const Key('mf-shores-overspent'),
              padding: const EdgeInsets.all(12),
              decoration: BoxDecoration(
                border: Border.all(color: pal.warn),
                borderRadius: BorderRadius.circular(10),
              ),
              child: Text(context.t('mf.shores.overspent')),
            ),
          SectionCard(title: context.t('mf.shores.purposes'), children: [PurposesTable(d)]),
          SectionCard(
            title: context.t('mf.shores.incoming'),
            trailing: d.pending > 0
                ? Text(context.t('mf.shores.pending', {'count': d.pending}), style: TextStyle(color: pal.warn))
                : null,
            children: [
              if (d.remittances.isEmpty) Hint(context.t('mf.shores.noRemittances')),
              for (final r in d.remittances)
                _Remittance(key: ValueKey(r.moveId), mfSpaceId: mfSpaceId, r: r, members: members),
            ],
          ),
          _SpendForm(mfSpaceId: mfSpaceId, uySpaceId: uySpaceId),
          if (d.spends.isNotEmpty) _Spends(uySpaceId: uySpaceId, v: d),
        ],
      ],
    );
  }
}

Widget _channel(BuildContext context, String value, ValueChanged<String> onChanged) => SegmentedChoice<String>(
  label: context.t('mf.channel'),
  options: [
    for (final c in ['CARD', 'CASH']) (c, context.t('kk.channel.$c')),
  ],
  value: value,
  onChanged: onChanged,
);

class _Remittance extends ConsumerStatefulWidget {
  const _Remittance({required this.mfSpaceId, required this.r, required this.members, super.key});

  final String mfSpaceId;
  final MfRemittanceDto r;
  final List<MemberDto> members;

  @override
  ConsumerState<_Remittance> createState() => _RemittanceState();
}

class _RemittanceState extends ConsumerState<_Remittance> with ActionState {
  late final _received = TextEditingController(text: widget.r.expected?.plain);
  String _memberId = '';
  String _channelValue = 'CARD';

  @override
  void dispose() {
    _received.dispose();
    super.dispose();
  }

  Future<void> _confirm() => act(
    () => ref
        .read(coreProvider)
        .mfConfirmReceipt(
          spaceId: widget.mfSpaceId,
          moveId: widget.r.moveId,
          input: MfReceiptInput(
            received: _received.text,
            channel: _channelValue,
            memberId: _memberId.isEmpty ? null : _memberId,
          ),
        ),
  );

  @override
  Widget build(BuildContext context) {
    final r = widget.r;
    final pal = context.palette;
    final receipt = r.receipt;
    final sentOn = context.t('mf.shores.sentOn', {'date': showDate(r.sentOn)});
    return Semantics(
      container: true,
      label: sentOn,
      child: Container(
        key: const Key('mf-remittance'),
        padding: const EdgeInsets.symmetric(vertical: 10),
        decoration: BoxDecoration(
          border: Border(top: BorderSide(color: pal.line)),
        ),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.stretch,
          children: [
            Text.rich(
              TextSpan(
                children: [
                  TextSpan(
                    text: sentOn,
                    style: const TextStyle(fontWeight: FontWeight.w600),
                  ),
                  TextSpan(text: ' · ${r.sent.formatted}'),
                  if (r.note != null)
                    TextSpan(
                      text: ' · ${r.note}',
                      style: TextStyle(color: pal.inkMuted),
                    ),
                ],
              ),
            ),
            if (receipt != null)
              Text(
                [
                  context.t('mf.shores.receivedLine', {
                    'amount': receipt.received.formatted,
                    'date': showDate(receipt.receivedOn),
                  }),
                  ?receipt.memberName,
                ].join(' · '),
                style: TextStyle(color: pal.accentText),
              )
            else
              Text(context.t('mf.shores.onTheWay'), style: TextStyle(color: pal.warn)),
            Hint(r.shares.map((s) => '${context.t('mf.purpose.${s.purpose}')} ${s.percent} %').join(' · ')),
            if (r.allocation.isNotEmpty)
              Hint(
                r.allocation.map((a) => '${context.t('mf.purpose.${a.purpose}')}: ${a.amount.formatted}').join(' · '),
              ),
            if (receipt == null) ...[
              const SizedBox(height: 8),
              AmountField(label: context.t('mf.shores.receivedAmount'), controller: _received),
              const SizedBox(height: 12),
              Select<String>(
                label: context.t('mf.shores.who'),
                items: [('', '—'), for (final m in widget.members) (m.id, m.displayName)],
                value: _memberId,
                onChanged: (v) => setState(() => _memberId = v ?? ''),
              ),
              const SizedBox(height: 12),
              _channel(context, _channelValue, (v) => setState(() => _channelValue = v)),
              ErrorText(error),
              const SizedBox(height: 8),
              Align(
                alignment: Alignment.centerLeft,
                child: FilledButton(onPressed: busy ? null : _confirm, child: Text(context.t('mf.shores.confirm'))),
              ),
            ],
          ],
        ),
      ),
    );
  }
}

/// Maqsad bo'yicha xarajat. «Qarz to'lovi» maqsadida — Uy qarzlaridan biriga U8 to'lovi (yo'l qarzi,
/// musofir/SPEC 6.1): kategoriya o'rniga qarz tanlanadi.
class _SpendForm extends ConsumerStatefulWidget {
  const _SpendForm({required this.mfSpaceId, required this.uySpaceId});

  final String mfSpaceId;
  final String uySpaceId;

  @override
  ConsumerState<_SpendForm> createState() => _SpendFormState();
}

class _SpendFormState extends ConsumerState<_SpendForm> with ActionState {
  String _purpose = 'HOUSEHOLD';
  final _amount = TextEditingController();
  final _note = TextEditingController();
  String? _categoryId;
  String? _debtId;
  String _channelValue = 'CASH';

  @override
  void dispose() {
    _amount.dispose();
    _note.dispose();
    super.dispose();
  }

  Future<void> _save(List<CategoryDto> categories, List<DebtDto> active) async {
    final core = ref.read(coreProvider);
    final note = _note.text.trim().isEmpty ? null : _note.text.trim();
    final r = await act(
      () => _purpose == 'DEBT'
          ? core.mfPayDebt(
              spaceId: widget.mfSpaceId,
              input: MfDebtPaymentInput(
                debtId: _debtId ?? active.firstOrNull?.id ?? '',
                amount: _amount.text,
                note: note,
              ),
            )
          : core.mfRecordSpend(
              spaceId: widget.mfSpaceId,
              input: MfSpendInput(
                purpose: _purpose,
                amount: _amount.text,
                categoryId: _categoryId ?? categories.firstOrNull?.id ?? '',
                channel: _channelValue,
                note: note,
              ),
            ),
    );
    if (r != null) {
      _amount.clear();
      _note.clear();
    }
  }

  @override
  Widget build(BuildContext context) {
    final uy = widget.uySpaceId;
    final isDebt = _purpose == 'DEBT';
    final categories = ref.watch(categoriesQuery(uy)).valueOrNull ?? const <CategoryDto>[];
    final debtsQ = isDebt ? ref.watch(query(['debts', uy], (c) => c.debtsOverview(spaceId: uy))) : null;
    final active = [
      for (final d in debtsQ?.valueOrNull?.debts ?? const <DebtDto>[])
        if (d.status == 'ACTIVE') d,
    ];
    return SectionCard(
      title: context.t('mf.shores.spendForm'),
      children: [
        Select<String>(
          label: context.t('mf.shores.purpose'),
          items: [for (final p in mfPurposes) (p, context.t('mf.purpose.$p'))],
          value: _purpose,
          onChanged: (v) => setState(() => _purpose = v ?? _purpose),
        ),
        const SizedBox(height: 12),
        AmountField(label: context.t('common.amount'), controller: _amount),
        const SizedBox(height: 12),
        if (isDebt) ...[
          Select<String>(
            label: context.t('mf.shores.debt'),
            items: [for (final d in active) (d.id, '${d.creditor} · ${d.balance.formatted}')],
            value: _debtId ?? active.firstOrNull?.id,
            onChanged: (v) => setState(() => _debtId = v),
          ),
          if (debtsQ?.hasValue == true && active.isEmpty)
            Hint(context.t('mf.shores.noDebts'), color: context.palette.warn),
        ] else ...[
          Select<String>(
            label: context.t('kk.category'),
            items: [for (final c in categories) (c.id, c.customName ?? context.t(c.nameKey))],
            value: _categoryId ?? categories.firstOrNull?.id,
            onChanged: (v) => setState(() => _categoryId = v),
          ),
          const SizedBox(height: 12),
          _channel(context, _channelValue, (v) => setState(() => _channelValue = v)),
        ],
        const SizedBox(height: 12),
        Field(label: context.t('kk.note'), controller: _note),
        ErrorText(error),
        const SizedBox(height: 8),
        Align(
          alignment: Alignment.centerLeft,
          child: FilledButton(
            onPressed: busy ? null : () => _save(categories, active),
            child: Text(context.t(isDebt ? 'mf.shores.payDebt' : 'mf.shores.saveSpend')),
          ),
        ),
      ],
    );
  }
}

class _Spends extends ConsumerWidget {
  const _Spends({required this.uySpaceId, required this.v});

  final String uySpaceId;
  final MfTwoShoresDto v;

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final categories = ref.watch(categoriesQuery(uySpaceId)).valueOrNull ?? const <CategoryDto>[];
    final pal = context.palette;
    return SectionCard(
      title: context.t('mf.shores.spends'),
      children: [
        for (final s in v.spends)
          Container(
            key: ValueKey(('mf-spend', s)),
            padding: const EdgeInsets.symmetric(vertical: 6),
            decoration: BoxDecoration(
              border: Border(top: BorderSide(color: pal.line)),
            ),
            child: Row(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Expanded(
                  child: Text.rich(
                    TextSpan(
                      children: [
                        TextSpan(text: '${showDate(s.occurredOn)} · ${context.t('mf.purpose.${s.purpose}')}'),
                        TextSpan(
                          text:
                              ' · ${[
                                if (s.kind == 'DEBT_PAYMENT') context.t('mf.shores.paidTo', {'creditor': s.creditor ?? ''}) else categoryName(context, categories, s.categoryId),
                                ?s.note,
                              ].where((x) => x.isNotEmpty).join(' · ')}',
                          style: TextStyle(color: pal.inkMuted),
                        ),
                      ],
                    ),
                  ),
                ),
                const SizedBox(width: 8),
                Text(s.amount.formatted, style: const TextStyle(fontFeatures: [FontFeature.tabularFigures()])),
              ],
            ),
          ),
      ],
    );
  }
}
