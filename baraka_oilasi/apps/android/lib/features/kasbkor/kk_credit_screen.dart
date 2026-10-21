import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../app/i18n.dart';
import '../../app/theme.dart';
import '../../core/core.dart';
import '../../core/query.dart';
import '../../shared/format.dart';
import '../../shared/widgets.dart';
import 'kk_common.dart';

String? _opt(String v) => v.trim().isEmpty ? null : v.trim();

/// Nasiya daftari (kasbkor/SPEC 5.2): narx savdo paytida qotiriladi, kechikish uchun ustama yo'q.
/// Yosh guruhlari, haftalik ko'rik (eslatma matni nusxalanadi — ilova o'zi yubormaydi), yangi nasiya.
class KkCreditScreen extends ConsumerWidget {
  const KkCreditScreen({required this.spaceId, super.key});

  final String spaceId;

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final book = ref.watch(query(['kkCredit', spaceId], (c) => c.kkCreditBook(spaceId: spaceId)));
    final b = book.valueOrNull;
    final review = b?.sales.where((s) => s.status == 'OVERDUE' || s.talkThisWeek).toList() ?? [];
    final p = context.palette;
    return ScreenBody(
      mentorKey: 'mentor.kkCredit',
      children: [
        Hint(context.t('kk.credit.intro')),
        if (book.hasError) ErrorText(book.error),
        if (b != null)
          SectionCard(
            title: context.t('kk.credit.aging'),
            children: [
              Text(
                b.aging.total.formatted,
                key: const Key('kk-credit-total'),
                style: TextStyle(fontSize: 24, fontWeight: FontWeight.w700, color: p.accent),
              ),
              const SizedBox(height: 8),
              for (final (k, m) in [
                ('current', b.aging.current),
                ('d1_30', b.aging.d130),
                ('d31_60', b.aging.d3160),
                ('d61_90', b.aging.d6190),
                ('d90_plus', b.aging.d90Plus),
              ])
                ValueRow(
                  context.t('kk.credit.bucket.$k'),
                  m.formatted,
                  key: Key('kk-credit-$k'),
                  valueColor: k == 'd90_plus' ? p.warn : null,
                ),
            ],
          ),
        if (review.isNotEmpty)
          SectionCard(
            title: context.t('kk.credit.review'),
            children: [
              Hint(context.t('kk.credit.reviewHint')),
              for (final s in review) _ReviewItem(key: ValueKey('review-${s.id}'), spaceId: spaceId, s: s),
            ],
          ),
        _NewSale(spaceId: spaceId),
        if (b != null && b.sales.isNotEmpty) ...[
          Semantics(
            header: true,
            child: Text(context.t('kk.credit.list'), style: const TextStyle(fontSize: 18, fontWeight: FontWeight.w700)),
          ),
          for (final s in b.sales) _SaleCard(key: ValueKey(s.id), spaceId: spaceId, s: s),
        ],
      ],
    );
  }
}

class _ReviewItem extends ConsumerStatefulWidget {
  const _ReviewItem({required this.spaceId, required this.s, super.key});

  final String spaceId;
  final KkCreditSaleDto s;

  @override
  ConsumerState<_ReviewItem> createState() => _ReviewItemState();
}

class _ReviewItemState extends ConsumerState<_ReviewItem> with ActionState {
  bool _copied = false;

  @override
  Widget build(BuildContext context) {
    final s = widget.s;
    final p = context.palette;
    final text = context.t('kk.credit.reminder', {
      'name': s.customerName,
      'item': s.item,
      'amount': s.nextDue?.amount.formatted ?? s.outstanding.formatted,
      'date': showDate(s.nextDue?.date ?? ''),
    });
    return Container(
      padding: const EdgeInsets.only(top: 12),
      margin: const EdgeInsets.only(top: 8),
      decoration: BoxDecoration(
        border: Border(top: BorderSide(color: p.line)),
      ),
      child: Semantics(
        container: true,
        label: '${s.customerName}: ${s.item}',
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.stretch,
          children: [
            Text.rich(
              TextSpan(
                children: [
                  TextSpan(
                    text: s.customerName,
                    style: const TextStyle(fontWeight: FontWeight.w600),
                  ),
                  TextSpan(text: ' · ${s.item} · ${s.outstanding.formatted}'),
                  if (s.status == 'OVERDUE')
                    TextSpan(
                      text: '  ${context.t('kk.credit.overdueDays', {'n': s.overdueDays})}',
                      style: TextStyle(color: p.warn),
                    ),
                  if (s.customerPhone != null)
                    TextSpan(
                      text: '  ${s.customerPhone}',
                      style: TextStyle(color: p.inkMuted),
                    ),
                ],
              ),
            ),
            const SizedBox(height: 8),
            Text(context.t('kk.credit.reminderLabel'), style: TextStyle(color: p.inkMuted, fontSize: 14)),
            Container(
              margin: const EdgeInsets.only(top: 4),
              padding: const EdgeInsets.all(10),
              decoration: BoxDecoration(
                color: p.paper,
                border: Border.all(color: p.fieldLine),
                borderRadius: BorderRadius.circular(8),
              ),
              child: SelectableText(text, style: const TextStyle(fontSize: 14)),
            ),
            Wrap(
              spacing: 8,
              crossAxisAlignment: WrapCrossAlignment.center,
              children: [
                TextButton.icon(
                  onPressed: () async {
                    await Clipboard.setData(ClipboardData(text: text));
                    if (mounted) setState(() => _copied = true);
                  },
                  icon: const Icon(Icons.copy, size: 18),
                  label: Text(context.t(_copied ? 'kk.credit.copied' : 'kk.credit.copy')),
                ),
                Row(
                  mainAxisSize: MainAxisSize.min,
                  children: [
                    Checkbox(
                      value: s.talkThisWeek,
                      onChanged: busy
                          ? null
                          : (v) => act(
                              () => ref
                                  .read(coreProvider)
                                  .kkCreditMark(spaceId: widget.spaceId, saleId: s.id, talk: v ?? false),
                            ),
                    ),
                    Flexible(child: Text(context.t('kk.credit.talk'))),
                  ],
                ),
              ],
            ),
            ErrorText(error),
          ],
        ),
      ),
    );
  }
}

class _NewSale extends ConsumerStatefulWidget {
  const _NewSale({required this.spaceId});

  final String spaceId;

  @override
  ConsumerState<_NewSale> createState() => _NewSaleState();
}

class _NewSaleState extends ConsumerState<_NewSale> with ActionState {
  bool _open = false;
  bool _newCustomer = false;
  String? _customerId;
  final _item = TextEditingController();
  final _cashPrice = TextEditingController();
  final _creditPrice = TextEditingController();
  final _installments = TextEditingController(text: '3');
  final _witness = TextEditingController();
  String? _soldOn;
  String? _firstDue;

  @override
  void dispose() {
    for (final c in [_item, _cashPrice, _creditPrice, _installments, _witness]) {
      c.dispose();
    }
    super.dispose();
  }

  void _reset() {
    for (final c in [_item, _cashPrice, _creditPrice, _witness]) {
      c.clear();
    }
    _installments.text = '3';
    _soldOn = null;
    _firstDue = null;
    _open = false;
  }

  Future<void> _save(String customerId) async {
    final r = await act(
      () => ref
          .read(coreProvider)
          .kkAddCreditSale(
            spaceId: widget.spaceId,
            input: KkCreditSaleInput(
              customerId: customerId,
              item: _item.text,
              cashPrice: _opt(_cashPrice.text),
              creditPrice: _creditPrice.text,
              installments: int.tryParse(_installments.text.trim()) ?? 0,
              soldOn: _soldOn,
              firstDue: _firstDue,
              witness: _opt(_witness.text),
            ),
          ),
    );
    if (r != null) setState(_reset);
  }

  @override
  Widget build(BuildContext context) {
    if (!_open) {
      return Align(
        alignment: Alignment.centerLeft,
        child: FilledButton(onPressed: () => setState(() => _open = true), child: Text(context.t('kk.credit.new'))),
      );
    }
    final sid = widget.spaceId;
    final customers = ref.watch(query(['kkCustomers', sid], (c) => c.kkCustomers(spaceId: sid))).valueOrNull;
    final customerId = _customerId ?? customers?.firstOrNull?.id ?? '';
    return SectionCard(
      title: context.t('kk.credit.new'),
      children: [
        Hint(context.t('kk.credit.newHint')),
        if (_newCustomer || (customers?.isEmpty ?? false)) ...[
          const SizedBox(height: 12),
          _NewCustomer(
            spaceId: sid,
            onDone: (id) => setState(() {
              _newCustomer = false;
              _customerId = id;
            }),
          ),
        ],
        if (customers != null && customers.isNotEmpty) ...[
          const SizedBox(height: 12),
          Select<String>(
            label: context.t('kk.credit.customer'),
            items: [for (final c in customers) (c.id, c.name)],
            value: customerId,
            onChanged: (v) => setState(() => _customerId = v),
          ),
          Align(
            alignment: Alignment.centerLeft,
            child: TextButton(
              onPressed: () => setState(() => _newCustomer = true),
              child: Text(context.t('kk.credit.addCustomer')),
            ),
          ),
          Field(label: context.t('kk.credit.item'), controller: _item),
          const SizedBox(height: 12),
          AmountField(label: context.t('kk.credit.cashPrice'), controller: _cashPrice),
          const SizedBox(height: 12),
          AmountField(label: context.t('kk.credit.creditPrice'), controller: _creditPrice),
          const SizedBox(height: 12),
          Field(
            label: context.t('kk.credit.installments'),
            controller: _installments,
            keyboardType: TextInputType.number,
            inputFormatters: [FilteringTextInputFormatter.digitsOnly],
          ),
          const SizedBox(height: 12),
          DateField(
            label: context.t('kk.credit.firstDue'),
            value: _firstDue,
            onChanged: (v) => setState(() => _firstDue = v),
          ),
          const SizedBox(height: 12),
          DateField(
            label: context.t('kk.credit.soldOn'),
            value: _soldOn,
            onChanged: (v) => setState(() => _soldOn = v),
          ),
          const SizedBox(height: 12),
          Field(label: context.t('kk.credit.witness'), controller: _witness),
          const SizedBox(height: 8),
          Hint(context.t('kk.credit.noSurcharge')),
          ErrorText(error),
          const SizedBox(height: 8),
          Wrap(
            spacing: 8,
            children: [
              TextButton(onPressed: () => setState(() => _open = false), child: Text(context.t('common.cancel'))),
              FilledButton(onPressed: busy ? null : () => _save(customerId), child: Text(context.t('common.save'))),
            ],
          ),
        ],
      ],
    );
  }
}

class _NewCustomer extends ConsumerStatefulWidget {
  const _NewCustomer({required this.spaceId, required this.onDone});

  final String spaceId;
  final ValueChanged<String> onDone;

  @override
  ConsumerState<_NewCustomer> createState() => _NewCustomerState();
}

class _NewCustomerState extends ConsumerState<_NewCustomer> with ActionState {
  final _name = TextEditingController();
  final _phone = TextEditingController();
  bool _consent = false;

  @override
  void dispose() {
    _name.dispose();
    _phone.dispose();
    super.dispose();
  }

  Future<void> _save() async {
    final r = await act(
      () => ref
          .read(coreProvider)
          .kkAddCustomer(
            spaceId: widget.spaceId,
            input: KkCustomerInput(name: _name.text, phone: _opt(_phone.text), phoneConsent: _consent),
          ),
    );
    if (r != null) widget.onDone(r.where((c) => c.name == _name.text.trim()).firstOrNull?.id ?? '');
  }

  @override
  Widget build(BuildContext context) => Container(
    padding: const EdgeInsets.all(12),
    decoration: BoxDecoration(
      border: Border.all(color: context.palette.line),
      borderRadius: BorderRadius.circular(10),
    ),
    child: Semantics(
      container: true,
      label: context.t('kk.credit.customerForm'),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: [
          Field(label: context.t('kk.credit.customerName'), controller: _name),
          const SizedBox(height: 12),
          Field(label: context.t('kk.credit.phone'), controller: _phone, keyboardType: TextInputType.phone),
          CheckboxListTile(
            contentPadding: EdgeInsets.zero,
            controlAffinity: ListTileControlAffinity.leading,
            value: _consent,
            title: Text(context.t('kk.credit.consent'), style: const TextStyle(fontSize: 14)),
            onChanged: (v) => setState(() => _consent = v ?? false),
          ),
          ErrorText(error),
          Align(
            alignment: Alignment.centerLeft,
            child: FilledButton(onPressed: busy ? null : _save, child: Text(context.t('kk.credit.saveCustomer'))),
          ),
        ],
      ),
    ),
  );
}

class _SaleCard extends ConsumerStatefulWidget {
  const _SaleCard({required this.spaceId, required this.s, super.key});

  final String spaceId;
  final KkCreditSaleDto s;

  @override
  ConsumerState<_SaleCard> createState() => _SaleCardState();
}

class _SaleCardState extends ConsumerState<_SaleCard> with ActionState {
  /// `pay`, `extend` yoki `forgive`.
  String? _action;
  final _amount = TextEditingController();
  final _months = TextEditingController(text: '1');
  String _wallet = 'CASH';

  @override
  void dispose() {
    _amount.dispose();
    _months.dispose();
    super.dispose();
  }

  void _toggle(String a) => setState(() {
    _action = _action == a ? null : a;
    _amount.text = a == 'pay' ? (widget.s.nextDue?.amount.plain ?? '') : '';
    error = null;
  });

  Future<void> _run() async {
    final core = ref.read(coreProvider);
    final s = widget.s;
    final sid = widget.spaceId;
    final r = await act(() {
      switch (_action) {
        case 'pay':
          return core.kkCreditPayment(
            spaceId: sid,
            saleId: s.id,
            input: KkCreditPaymentInput(amount: _amount.text, wallet: _wallet),
          );
        case 'extend':
          return core.kkCreditExtend(
            spaceId: sid,
            saleId: s.id,
            input: KkCreditExtendInput(months: int.tryParse(_months.text.trim()) ?? 0),
          );
        default:
          return core.kkCreditForgive(
            spaceId: sid,
            saleId: s.id,
            input: KkCreditForgiveInput(amount: _opt(_amount.text)),
          );
      }
    });
    if (r != null) {
      setState(() {
        _action = null;
        _amount.clear();
      });
    }
  }

  @override
  Widget build(BuildContext context) {
    final s = widget.s;
    final p = context.palette;
    final settled = s.status == 'SETTLED';
    final action = _action;
    final terms = [
      context.t('kk.credit.terms', {'price': s.creditPrice.formatted, 'n': s.installments, 'date': showDate(s.soldOn)}),
      if (s.creditMarkup != null)
        context.t('kk.credit.markup', {'cash': s.cashPrice?.formatted ?? '', 'diff': s.creditMarkup!.formatted}),
      if (s.witness != null) context.t('kk.credit.witnessShow', {'name': s.witness}),
    ].join(' · ');
    return Card(
      key: Key('kk-credit-sale-${s.customerName}'),
      child: Padding(
        padding: const EdgeInsets.all(16),
        child: Semantics(
          container: true,
          label: '${s.customerName}: ${s.item}',
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.stretch,
            children: [
              Text(
                '${s.customerName} · ${s.item}',
                style: const TextStyle(fontSize: 18, fontWeight: FontWeight.w700),
              ),
              Text(
                s.status == 'OVERDUE'
                    ? context.t('kk.credit.overdueDays', {'n': s.overdueDays})
                    : context.t('kk.credit.status.${s.status}'),
                key: const Key('kk-credit-status'),
                style: TextStyle(color: s.status == 'OVERDUE' ? p.warn : p.inkMuted, fontSize: 14),
              ),
              const SizedBox(height: 6),
              Hint(terms),
              const SizedBox(height: 6),
              ValueRow(
                context.t('kk.credit.outstanding'),
                s.outstanding.formatted,
                strong: true,
                key: const Key('kk-credit-outstanding'),
              ),
              if (s.nextDue != null)
                Hint(
                  context.t('kk.credit.next', {
                    'date': showDate(s.nextDue!.date),
                    'amount': s.nextDue!.amount.formatted,
                  }),
                ),
              Theme(
                data: Theme.of(context).copyWith(dividerColor: Colors.transparent),
                child: ExpansionTile(
                  tilePadding: EdgeInsets.zero,
                  childrenPadding: EdgeInsets.zero,
                  title: Text(context.t('kk.credit.schedule'), style: const TextStyle(fontSize: 14)),
                  children: [
                    for (final r in s.schedule)
                      Container(
                        padding: const EdgeInsets.symmetric(vertical: 4),
                        decoration: BoxDecoration(
                          border: Border(top: BorderSide(color: p.line)),
                        ),
                        child: Column(
                          crossAxisAlignment: CrossAxisAlignment.stretch,
                          children: [
                            Row(
                              children: [
                                Expanded(child: Text(showDate(r.due))),
                                Text(
                                  context.t('kk.credit.state.${r.state}'),
                                  style: TextStyle(color: r.state == 'OVERDUE' ? p.warn : p.inkMuted, fontSize: 14),
                                ),
                              ],
                            ),
                            ValueRow(context.t('kk.col.amount'), r.amount.formatted),
                            ValueRow(context.t('kk.credit.covered'), r.covered.formatted),
                          ],
                        ),
                      ),
                    for (final e in s.events)
                      Padding(
                        padding: const EdgeInsets.only(top: 4),
                        child: Hint(
                          [
                            showDate(e.occurredOn),
                            context.t('kk.credit.event.${e.kind}', {
                              'amount': e.amount?.formatted ?? '',
                              'n': e.months ?? 0,
                            }),
                            if (e.wallet != null) context.t('kk.wallet.${e.wallet}'),
                            ?e.note,
                          ].join(' · '),
                        ),
                      ),
                  ],
                ),
              ),
              if (!settled)
                Wrap(
                  spacing: 8,
                  runSpacing: 8,
                  children: [
                    for (final a in ['pay', 'extend', 'forgive'])
                      kkButton(
                        primary: a == 'pay',
                        onPressed: () => _toggle(a),
                        label: context.t('kk.credit.action.$a'),
                      ),
                    if (s.events.isEmpty)
                      Semantics(
                        label: context.t('kk.credit.deleteNamed', {'name': s.customerName, 'item': s.item}),
                        excludeSemantics: true,
                        button: true,
                        child: TextButton(
                          onPressed: busy
                              ? null
                              : () => act(
                                  () =>
                                      ref.read(coreProvider).kkDeleteCreditSale(spaceId: widget.spaceId, saleId: s.id),
                                ),
                          child: Text(context.t('kk.eq.delete')),
                        ),
                      ),
                  ],
                ),
              if (action != null)
                Container(
                  margin: const EdgeInsets.only(top: 12),
                  padding: const EdgeInsets.all(12),
                  decoration: BoxDecoration(
                    border: Border.all(color: p.line),
                    borderRadius: BorderRadius.circular(10),
                  ),
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.stretch,
                    children: [
                      if (action == 'extend')
                        Field(
                          label: context.t('kk.credit.months'),
                          controller: _months,
                          keyboardType: TextInputType.number,
                          inputFormatters: [FilteringTextInputFormatter.digitsOnly],
                        )
                      else
                        AmountField(
                          label: context.t(action == 'pay' ? 'common.amount' : 'kk.credit.forgiveAmount'),
                          controller: _amount,
                        ),
                      if (action == 'pay') ...[
                        const SizedBox(height: 12),
                        KkWalletPicker(
                          label: context.t('kk.walletLabel'),
                          value: _wallet,
                          onChanged: (w) => setState(() => _wallet = w),
                        ),
                      ],
                      const SizedBox(height: 8),
                      Hint(context.t('kk.credit.actionHint.$action')),
                      ErrorText(error),
                      const SizedBox(height: 8),
                      Align(
                        alignment: Alignment.centerLeft,
                        child: FilledButton(onPressed: busy ? null : _run, child: Text(context.t('common.save'))),
                      ),
                    ],
                  ),
                ),
              if (action == null) ErrorText(error),
            ],
          ),
        ),
      ),
    );
  }
}
