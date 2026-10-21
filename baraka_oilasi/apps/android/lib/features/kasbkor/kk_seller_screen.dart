import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../app/i18n.dart';
import '../../app/theme.dart';
import '../../core/core.dart';
import '../../core/query.dart';
import '../../shared/widgets.dart';

const _channels = ['CASH', 'CARD'];

String? _opt(String v) => v.trim().isEmpty ? null : v.trim();

/// Sotuvchi qurilmasi (ADR-0003): katalogdan yoki erkin summa bilan sotuv, bugungi o'z yozuvlari.
/// Foyda, chiqim va «egasi oldi» bu qurilmada yo'q — yadro ularni umuman bermaydi.
class KkSellerScreen extends ConsumerWidget {
  const KkSellerScreen({required this.spaceId, super.key});

  final String spaceId;

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final id = spaceId;
    final pal = context.palette;
    final day = ref.watch(query(['kkSellerDay', id], (c) => c.kkSellerDay(spaceId: id)));
    final d = day.hasError ? null : day.valueOrNull;
    return ScreenBody(
      mentorKey: 'mentor.kkSeller',
      children: [
        Hint(context.t('kk.seller.intro')),
        if (day.hasError) ErrorText(day.error),
        if (d?.shiftClosed ?? false)
          SectionCard(
            key: const Key('kk-seller-closed'),
            children: [Semantics(liveRegion: true, child: Text(context.t('kk.seller.shiftClosed')))],
          )
        else
          _SaleForm(spaceId: id),
        if (d != null)
          SectionCard(
            title: context.t('kk.seller.today'),
            children: [
              Text(
                context.t('kk.seller.totals', {'cash': d.cash.formatted, 'card': d.card.formatted}),
                key: const Key('kk-seller-totals'),
                style: const TextStyle(fontFeatures: [FontFeature.tabularFigures()]),
              ),
              if (d.sales.isEmpty) ...[const SizedBox(height: 8), Hint(context.t('kk.seller.empty'))],
              for (final s in d.sales)
                Container(
                  key: ValueKey(('kk-seller-row', s)),
                  padding: const EdgeInsets.symmetric(vertical: 8),
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
                              TextSpan(text: s.label.isEmpty ? context.t('kk.seller.noNote') : s.label),
                              if (s.qty != null)
                                TextSpan(
                                  text: ' · ${s.qty}',
                                  style: TextStyle(color: pal.inkMuted),
                                ),
                              if (s.kind == 'CREDIT_PAYMENT')
                                TextSpan(
                                  text: ' · ${context.t('kk.seller.creditPayment')}',
                                  style: TextStyle(color: pal.inkMuted),
                                ),
                            ],
                          ),
                        ),
                      ),
                      const SizedBox(width: 12),
                      Text.rich(
                        TextSpan(
                          children: [
                            TextSpan(
                              text: s.amount.formatted,
                              style: const TextStyle(fontFeatures: [FontFeature.tabularFigures()]),
                            ),
                            TextSpan(
                              text: ' · ${context.t('kk.channel.${s.channel}')}',
                              style: TextStyle(color: pal.inkMuted),
                            ),
                          ],
                        ),
                      ),
                    ],
                  ),
                ),
            ],
          ),
      ],
    );
  }
}

class _ChannelPicker extends StatelessWidget {
  const _ChannelPicker({required this.value, required this.onChanged});

  final String value;
  final ValueChanged<String> onChanged;

  @override
  Widget build(BuildContext context) => SegmentedChoice<String>(
    label: context.t('kk.seller.channel'),
    options: [for (final c in _channels) (c, context.t('kk.channel.$c'))],
    value: value,
    onChanged: onChanged,
  );
}

class _SaleForm extends ConsumerStatefulWidget {
  const _SaleForm({required this.spaceId});

  final String spaceId;

  @override
  ConsumerState<_SaleForm> createState() => _SaleFormState();
}

class _SaleFormState extends ConsumerState<_SaleForm> with ActionState {
  String _itemId = '';
  String _channel = 'CASH';
  final _qty = TextEditingController();
  final _amount = TextEditingController();
  final _note = TextEditingController();

  @override
  void dispose() {
    for (final c in [_qty, _amount, _note]) {
      c.dispose();
    }
    super.dispose();
  }

  Future<void> _save() async {
    final item = _itemId.isEmpty ? null : _itemId;
    final r = await act(
      () => ref
          .read(coreProvider)
          .kkSellerSale(
            spaceId: widget.spaceId,
            input: KkSellerSaleInput(
              itemId: item,
              qty: item == null ? null : _qty.text,
              amount: _opt(_amount.text),
              channel: _channel,
              note: _opt(_note.text),
            ),
          ),
    );
    if (r != null) {
      _qty.clear();
      _amount.clear();
      _note.clear();
    }
  }

  @override
  Widget build(BuildContext context) {
    final id = widget.spaceId;
    final catalog = ref.watch(query(['kkCatalog', id], (c) => c.kkCatalog(spaceId: id))).valueOrNull ?? const [];
    final item = catalog.where((i) => i.id == _itemId).firstOrNull;
    return SectionCard(
      semanticLabel: context.t('kk.seller.form'),
      children: [
        Select<String>(
          label: context.t('kk.seller.item'),
          items: [
            ('', context.t('kk.seller.freeAmount')),
            for (final i in catalog)
              (
                i.id,
                i.salePrice != null
                    ? context.t('kk.seller.itemPrice', {
                        'name': i.name,
                        'price': i.salePrice!.formatted,
                        'unit': context.t('kk.unit.${i.unit}'),
                      })
                    : i.name,
              ),
          ],
          value: _itemId,
          onChanged: (v) => setState(() => _itemId = v ?? ''),
        ),
        if (item != null) ...[
          const SizedBox(height: 12),
          Field(
            label: context.t('kk.seller.qty', {'unit': context.t('kk.unit.${item.unit}')}),
            controller: _qty,
            keyboardType: const TextInputType.numberWithOptions(decimal: true),
          ),
        ],
        const SizedBox(height: 12),
        AmountField(
          label: context.t(item != null ? 'kk.seller.amountOptional' : 'kk.seller.amount'),
          controller: _amount,
        ),
        const SizedBox(height: 12),
        _ChannelPicker(value: _channel, onChanged: (c) => setState(() => _channel = c)),
        const SizedBox(height: 12),
        Field(label: context.t('kk.note'), controller: _note),
        ErrorText(error),
        const SizedBox(height: 8),
        Align(
          alignment: Alignment.centerLeft,
          child: FilledButton(onPressed: busy ? null : _save, child: Text(context.t('kk.seller.save'))),
        ),
      ],
    );
  }
}

/// Sotuvchi uchun nasiya daftari: faqat qoldiq va to'lov qabul qilish.
class KkSellerCreditScreen extends ConsumerWidget {
  const KkSellerCreditScreen({required this.spaceId, super.key});

  final String spaceId;

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final id = spaceId;
    final book = ref.watch(query(['kkCredit', id], (c) => c.kkCreditBook(spaceId: id)));
    final sales = book.hasError ? const <KkCreditSaleDto>[] : (book.valueOrNull?.sales ?? const <KkCreditSaleDto>[]);
    final open = sales.where((s) => s.outstanding.minor != '0').toList();
    return ScreenBody(
      mentorKey: 'mentor.kkSellerCredit',
      children: [
        Hint(context.t('kk.seller.creditIntro')),
        if (book.hasError) ErrorText(book.error),
        if (book.hasValue && !book.hasError && open.isEmpty)
          SectionCard(children: [Hint(context.t('kk.seller.creditEmpty'))]),
        for (final s in open) _CreditRow(key: ValueKey(s.id), spaceId: id, s: s),
      ],
    );
  }
}

class _CreditRow extends ConsumerStatefulWidget {
  const _CreditRow({required this.spaceId, required this.s, super.key});

  final String spaceId;
  final KkCreditSaleDto s;

  @override
  ConsumerState<_CreditRow> createState() => _CreditRowState();
}

class _CreditRowState extends ConsumerState<_CreditRow> with ActionState {
  final _amount = TextEditingController();
  String _wallet = 'CASH';

  @override
  void dispose() {
    _amount.dispose();
    super.dispose();
  }

  Future<void> _pay() async {
    final r = await act(
      () => ref
          .read(coreProvider)
          .kkCreditPayment(
            spaceId: widget.spaceId,
            saleId: widget.s.id,
            input: KkCreditPaymentInput(amount: _amount.text, wallet: _wallet),
          ),
    );
    if (r != null) _amount.clear();
  }

  @override
  Widget build(BuildContext context) {
    final s = widget.s;
    final pal = context.palette;
    return SectionCard(
      key: Key('kk-seller-credit-${s.customerName}'),
      semanticLabel: '${s.customerName}: ${s.item}',
      children: [
        Text.rich(
          TextSpan(
            children: [
              TextSpan(
                text: s.customerName,
                style: const TextStyle(fontSize: 18, fontWeight: FontWeight.w700),
              ),
              TextSpan(
                text: ' · ${s.item}',
                style: TextStyle(color: pal.inkMuted),
              ),
            ],
          ),
        ),
        Text(
          context.t('kk.seller.outstanding', {'amount': s.outstanding.formatted}),
          style: TextStyle(color: s.status == 'OVERDUE' ? pal.warn : pal.inkMuted),
        ),
        const SizedBox(height: 12),
        AmountField(label: context.t('kk.seller.payAmount'), controller: _amount),
        const SizedBox(height: 12),
        _ChannelPicker(value: _wallet, onChanged: (c) => setState(() => _wallet = c)),
        ErrorText(error),
        const SizedBox(height: 8),
        Align(
          alignment: Alignment.centerLeft,
          child: FilledButton(onPressed: busy ? null : _pay, child: Text(context.t('kk.seller.pay'))),
        ),
      ],
    );
  }
}
