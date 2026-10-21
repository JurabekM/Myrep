import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../app/i18n.dart';
import '../../app/theme.dart';
import '../../core/core.dart';
import '../../core/query.dart';
import '../../shared/format.dart';
import '../../shared/widgets.dart';
import 'kk_agreement_parts.dart';

const _units = ['G', 'ML', 'MM', 'PCS'];
const _moves = ['PURCHASE', 'SALE', 'WRITE_OFF', 'COUNT'];

/// Tovarlar (kasbkor/SPEC 4.1–4.4): qoldiq, tannarx (o'rtacha yoki FIFO), qayta tiklash narxi va
/// «inflyatsiya yegan kapital», muzlagan tovar. Hamma hisob yadroda; UI faqat ko'rsatadi va matn yuboradi.
class KkStockScreen extends ConsumerStatefulWidget {
  const KkStockScreen({required this.spaceId, super.key});

  final String spaceId;

  @override
  ConsumerState<KkStockScreen> createState() => _KkStockScreenState();
}

class _KkStockScreenState extends ConsumerState<KkStockScreen> {
  bool _adding = false;

  /// Ochiq forma: tovar id va rejim (`PURCHASE` … yoki `EDIT`).
  (String, String)? _open;

  void _toggle(String id, String mode) => setState(() => _open = _open == (id, mode) ? null : (id, mode));

  @override
  Widget build(BuildContext context) {
    final sid = widget.spaceId;
    final q = ref.watch(query(['kkStock', sid], (c) => c.kkStock(spaceId: sid)));
    final s = q.valueOrNull;
    final pal = context.palette;
    return ScreenBody(
      mentorKey: 'mentor.kkStock',
      children: [
        Hint(context.t('kk.stock.intro')),
        if (q.hasError) ErrorText(q.error),
        if (s != null)
          Semantics(
            container: true,
            label: context.t('kk.stock.totals'),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.stretch,
              children: [
                Kpi(
                  key: const Key('kk-stock-value'),
                  label: context.t('kk.stock.bookValue'),
                  value: s.value.formatted,
                ),
                Kpi(
                  key: const Key('kk-stock-replacement'),
                  label: context.t('kk.stock.replacementValue'),
                  value: s.replacementValue.formatted,
                ),
                Kpi(
                  key: const Key('kk-stock-gap'),
                  label: context.t('kk.stock.gap'),
                  value: s.inflationGap.formatted,
                  hint: context.t('kk.stock.gapHint'),
                  accent: true,
                ),
                Card(
                  shape: s.frozenCount > 0
                      ? RoundedRectangleBorder(
                          borderRadius: BorderRadius.circular(12),
                          side: BorderSide(color: pal.warn),
                        )
                      : null,
                  child: Kpi(
                    key: const Key('kk-stock-frozen'),
                    label: context.t('kk.stock.frozenTotal'),
                    value: s.frozenValue.formatted,
                    hint: context.t('kk.stock.frozenCount', {'count': s.frozenCount}),
                  ),
                ),
              ],
            ),
          ),
        Align(
          alignment: Alignment.centerLeft,
          child: _adding
              ? OutlinedButton(
                  onPressed: () => setState(() => _adding = false),
                  child: Text(context.t('kk.stock.add')),
                )
              : FilledButton(
                  onPressed: () => setState(() => _adding = true),
                  child: Text(context.t('kk.stock.add')),
                ),
        ),
        if (_adding) _ItemForm(spaceId: sid, onDone: () => setState(() => _adding = false)),
        Semantics(
          header: true,
          child: Text(context.t('kk.stock.list'), style: const TextStyle(fontSize: 18, fontWeight: FontWeight.w700)),
        ),
        if (s != null && s.items.isEmpty) Hint(context.t('kk.stock.empty')),
        for (final item in s?.items ?? const <KkItemDto>[])
          _ItemCard(
            key: ValueKey(item.id),
            spaceId: sid,
            item: item,
            open: _open?.$1 == item.id ? _open!.$2 : null,
            onToggle: (m) => _toggle(item.id, m),
            onDone: () => setState(() => _open = null),
          ),
      ],
    );
  }
}

class _ItemCard extends ConsumerStatefulWidget {
  const _ItemCard({
    required this.spaceId,
    required this.item,
    required this.open,
    required this.onToggle,
    required this.onDone,
    super.key,
  });

  final String spaceId;
  final KkItemDto item;
  final String? open;
  final ValueChanged<String> onToggle;
  final VoidCallback onDone;

  @override
  ConsumerState<_ItemCard> createState() => _ItemCardState();
}

class _ItemCardState extends ConsumerState<_ItemCard> with ActionState {
  Future<void> _delete() =>
      act(() => ref.read(coreProvider).kkDeleteItem(spaceId: widget.spaceId, itemId: widget.item.id));

  @override
  Widget build(BuildContext context) {
    final item = widget.item;
    final pal = context.palette;
    final unit = context.t('kk.unit.${item.unit}');
    final open = widget.open;
    final rows = <(String, String)>[
      (context.t('kk.stock.bookValue'), item.value.formatted),
      (context.t('kk.stock.unitCost', {'unit': unit}), item.unitCost?.formatted ?? '—'),
      (context.t('kk.stock.replacementPrice', {'unit': unit}), item.replacementPrice?.formatted ?? '—'),
      (context.t('kk.stock.replacementValue'), item.replacementValue?.formatted ?? '—'),
      (context.t('kk.stock.gap'), item.inflationGap?.formatted ?? '—'),
      if (item.salePrice != null) (context.t('kk.stock.salePrice', {'unit': unit}), item.salePrice!.formatted),
    ];
    return Semantics(
      container: true,
      label: item.name,
      child: Card(
        key: Key('kk-item-${item.name}'),
        shape: kkWarnShape(context, warn: item.frozen),
        child: Padding(
          padding: const EdgeInsets.all(16),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.stretch,
            children: [
              Row(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Expanded(
                    child: Text.rich(
                      TextSpan(
                        children: [
                          TextSpan(
                            text: item.name,
                            style: const TextStyle(fontSize: 18, fontWeight: FontWeight.w700),
                          ),
                          TextSpan(
                            text: '  ${context.t('kk.stock.method.${item.method}')}',
                            style: TextStyle(color: pal.inkMuted, fontSize: 14),
                          ),
                        ],
                      ),
                    ),
                  ),
                  Text(
                    '${item.qty} $unit',
                    key: const Key('kk-item-qty'),
                    style: const TextStyle(
                      fontSize: 20,
                      fontWeight: FontWeight.w700,
                      fontFeatures: [FontFeature.tabularFigures()],
                    ),
                  ),
                ],
              ),
              const SizedBox(height: 4),
              for (final (label, value) in rows) ValueRow(label, value),
              if (item.saleBelowReplacement) KkNote(context.t('kk.stock.saleBelow')),
              if (item.belowMin) KkNote(context.t('kk.stock.belowMin', {'qty': item.minQty ?? '', 'unit': unit})),
              if (item.frozen)
                KkNote(
                  '${item.lastSaleOn != null ? context.t('kk.stock.frozenSince', {'date': showDate(item.lastSaleOn!), 'days': item.frozenDays}) : context.t('kk.stock.frozenNeverSold', {'days': item.frozenDays})} '
                  '${context.t('kk.stock.frozenOffer')}',
                ),
              const SizedBox(height: 8),
              Semantics(
                container: true,
                label: context.t('kk.stock.actions', {'name': item.name}),
                child: Wrap(
                  spacing: 8,
                  runSpacing: 8,
                  children: [
                    for (final m in _moves)
                      KkActionButton(
                        label: context.t('kk.stock.action.$m'),
                        active: open == m,
                        onPressed: () => widget.onToggle(m),
                      ),
                    KkActionButton(
                      label: context.t('kk.stock.edit'),
                      active: open == 'EDIT',
                      onPressed: () => widget.onToggle('EDIT'),
                    ),
                    if (item.moves.isEmpty)
                      Semantics(
                        label: context.t('kk.stock.deleteNamed', {'name': item.name}),
                        child: TextButton(
                          onPressed: busy ? null : _delete,
                          child: Text(context.t('kk.stock.delete')),
                        ),
                      ),
                  ],
                ),
              ),
              ErrorText(error),
              if (open != null && open != 'EDIT')
                _MoveForm(key: ValueKey(open), spaceId: widget.spaceId, item: item, kind: open, onDone: widget.onDone),
              if (open == 'EDIT') _ItemForm(spaceId: widget.spaceId, item: item, onDone: widget.onDone),
              if (item.moves.isNotEmpty)
                KkDetails(
                  summary: context.t('kk.stock.history', {'count': item.moves.length}),
                  children: [
                    for (final m in item.moves)
                      KkHistoryRow(
                        title: '${showDate(m.occurredOn)} · ${context.t('kk.stock.kind.${m.kind}')} · ${m.qty} $unit',
                        value: m.amount?.formatted ?? '—',
                        note: [
                          '${context.t('kk.stock.cost')}: ${m.cost.formatted}',
                          if (m.wallet != null) context.t('kk.wallet.${m.wallet}'),
                          if (m.reason != null) m.reason!,
                        ].join(' · '),
                      ),
                  ],
                ),
            ],
          ),
        ),
      ),
    );
  }
}

class _MoveForm extends ConsumerStatefulWidget {
  const _MoveForm({required this.spaceId, required this.item, required this.kind, required this.onDone, super.key});

  final String spaceId;
  final KkItemDto item;
  final String kind;
  final VoidCallback onDone;

  @override
  ConsumerState<_MoveForm> createState() => _MoveFormState();
}

class _MoveFormState extends ConsumerState<_MoveForm> with ActionState {
  final _qty = TextEditingController();
  final _amount = TextEditingController();
  final _reason = TextEditingController();
  late String _wallet = widget.kind == 'SALE' ? 'CASH' : 'CARD';
  String? _on;

  @override
  void dispose() {
    _qty.dispose();
    _amount.dispose();
    _reason.dispose();
    super.dispose();
  }

  Future<void> _save() async {
    final k = widget.kind;
    final r = await act(
      () => ref
          .read(coreProvider)
          .kkStockMove(
            spaceId: widget.spaceId,
            itemId: widget.item.id,
            input: KkStockMoveInput(
              kind: k,
              qty: _qty.text,
              amount: kkOpt(_amount.text),
              wallet: k == 'PURCHASE' || k == 'SALE' ? (_wallet == 'BEFORE' ? null : _wallet) : null,
              occurredOn: _on,
              reason: kkOpt(_reason.text),
            ),
          ),
    );
    if (r != null) widget.onDone();
  }

  @override
  Widget build(BuildContext context) {
    final k = widget.kind;
    final item = widget.item;
    final unit = context.t('kk.unit.${item.unit}');
    final amountHint = switch (k) {
      'SALE' when item.salePrice != null => context.t('kk.stock.saleAmountHint', {
        'price': item.salePrice!.formatted,
        'unit': unit,
      }),
      'COUNT' => context.t('kk.stock.foundValueHint'),
      _ => null,
    };
    final wallets = k == 'PURCHASE' ? ['CASH', 'CARD', 'BEFORE'] : ['CASH', 'CARD'];
    return Semantics(
      container: true,
      label: context.t('kk.stock.formTitle', {'action': context.t('kk.stock.action.$k'), 'name': item.name}),
      child: KkBox(
        children: [
          Field(
            label: k == 'COUNT'
                ? context.t('kk.stock.counted', {'unit': unit})
                : context.t('kk.stock.qty', {'unit': unit}),
            controller: _qty,
            keyboardType: const TextInputType.numberWithOptions(decimal: true),
          ),
          if (k == 'COUNT') Hint(context.t('kk.stock.bookQty', {'qty': item.qty, 'unit': unit})),
          if (k != 'WRITE_OFF') ...[
            const SizedBox(height: 12),
            AmountField(label: context.t('kk.stock.amount.$k'), controller: _amount),
            if (amountHint != null) Hint(amountHint),
          ],
          if (k == 'PURCHASE' || k == 'SALE') ...[
            const SizedBox(height: 12),
            KkToggleRow<String>(
              label: context.t(k == 'PURCHASE' ? 'kk.stock.paidFrom' : 'kk.stock.paidTo'),
              options: [
                for (final w in wallets)
                  (w, w == 'BEFORE' ? context.t('kk.stock.paidBefore') : context.t('kk.wallet.$w')),
              ],
              value: _wallet,
              onChanged: (w) => setState(() => _wallet = w),
            ),
          ],
          if (k == 'WRITE_OFF' || k == 'COUNT') ...[
            const SizedBox(height: 12),
            Field(label: context.t('kk.stock.reason'), controller: _reason),
            Hint(context.t('kk.stock.reasonHint.$k')),
          ],
          const SizedBox(height: 12),
          DateField(label: context.t('kk.date'), value: _on, onChanged: (v) => setState(() => _on = v)),
          ErrorText(error),
          const SizedBox(height: 8),
          Align(
            alignment: Alignment.centerLeft,
            child: FilledButton(onPressed: busy ? null : _save, child: Text(context.t('common.save'))),
          ),
        ],
      ),
    );
  }
}

class _ItemForm extends ConsumerStatefulWidget {
  const _ItemForm({required this.spaceId, required this.onDone, this.item});

  final String spaceId;
  final KkItemDto? item;
  final VoidCallback onDone;

  @override
  ConsumerState<_ItemForm> createState() => _ItemFormState();
}

class _ItemFormState extends ConsumerState<_ItemForm> with ActionState {
  late final _name = TextEditingController(text: widget.item?.name ?? '');
  late String _unit = widget.item?.unit ?? 'G';
  late String _method = widget.item?.method ?? 'AVERAGE';
  late final _sale = TextEditingController(text: widget.item?.salePrice?.plain ?? '');
  late final _price = TextEditingController(text: widget.item?.replacementPriceInput?.plain ?? '');
  late final _min = TextEditingController(text: widget.item?.minQty ?? '');
  late final _frozen = TextEditingController(text: '${widget.item?.frozenDays ?? 90}');

  @override
  void dispose() {
    for (final c in [_name, _sale, _price, _min, _frozen]) {
      c.dispose();
    }
    super.dispose();
  }

  Future<void> _save() async {
    final item = widget.item;
    final core = ref.read(coreProvider);
    final input = KkItemInput(
      name: _name.text,
      unit: _unit,
      method: _method,
      salePrice: kkOpt(_sale.text),
      replacementPrice: kkOpt(_price.text),
      minQty: kkOpt(_min.text),
      frozenDays: int.tryParse(_frozen.text.trim()),
      note: item?.note,
    );
    final r = await act(
      () => item == null
          ? core.kkAddItem(spaceId: widget.spaceId, input: input)
          : core.kkUpdateItem(spaceId: widget.spaceId, itemId: item.id, input: input),
    );
    if (r != null) widget.onDone();
  }

  @override
  Widget build(BuildContext context) {
    final item = widget.item;
    final unit = context.t('kk.unit.$_unit');
    final locked = (item?.moves.length ?? 0) > 0;
    return Semantics(
      container: true,
      label: item == null ? context.t('kk.stock.add') : context.t('kk.stock.editTitle', {'name': item.name}),
      child: KkBox(
        children: [
          Field(label: context.t('kk.stock.name'), controller: _name),
          const SizedBox(height: 12),
          Select<String>(
            label: context.t('kk.stock.unit'),
            items: [for (final u in _units) (u, context.t('kk.unit.$u'))],
            value: _unit,
            onChanged: item != null ? null : (v) => setState(() => _unit = v ?? _unit),
          ),
          const SizedBox(height: 12),
          KkToggleRow<String>(
            label: context.t('kk.stock.methodLabel'),
            options: [
              for (final m in ['AVERAGE', 'FIFO']) (m, context.t('kk.stock.method.$m')),
            ],
            value: _method,
            onChanged: locked ? null : (m) => setState(() => _method = m),
          ),
          Hint(context.t(locked ? 'kk.stock.methodLocked' : 'kk.stock.methodHint')),
          const SizedBox(height: 12),
          AmountField(label: context.t('kk.stock.salePrice', {'unit': unit}), controller: _sale),
          const SizedBox(height: 12),
          AmountField(label: context.t('kk.stock.currentPrice', {'unit': unit}), controller: _price),
          Hint(context.t('kk.stock.currentPriceHint')),
          const SizedBox(height: 12),
          Field(
            label: context.t('kk.stock.minQty', {'unit': unit}),
            controller: _min,
            keyboardType: const TextInputType.numberWithOptions(decimal: true),
          ),
          const SizedBox(height: 12),
          Field(label: context.t('kk.stock.frozenDays'), controller: _frozen, keyboardType: TextInputType.number),
          ErrorText(error),
          const SizedBox(height: 8),
          Align(
            alignment: Alignment.centerLeft,
            child: FilledButton(
              onPressed: busy ? null : _save,
              child: Text(item == null ? context.t('kk.stock.addButton') : context.t('common.save')),
            ),
          ),
        ],
      ),
    );
  }
}
