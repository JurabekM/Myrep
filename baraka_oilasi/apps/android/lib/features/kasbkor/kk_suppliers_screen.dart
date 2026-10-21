import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../app/i18n.dart';
import '../../core/core.dart';
import '../../core/query.dart';
import '../../shared/format.dart';
import '../../shared/widgets.dart';
import 'kk_agreement_parts.dart';

/// Ta'minotchilar (kasbkor/SPEC 7.1 `SUPPLY`): narx kelishuvda qotiriladi, yetkazish — nasiyaga tovar
/// (tovar bog'lansa — qoldiqqa kiradi), to'lov eng erta muddatdan yopiladi; kechikish uchun jarima yo'q.
class KkSuppliersScreen extends ConsumerStatefulWidget {
  const KkSuppliersScreen({required this.spaceId, super.key});

  final String spaceId;

  @override
  ConsumerState<KkSuppliersScreen> createState() => _KkSuppliersScreenState();
}

class _KkSuppliersScreenState extends ConsumerState<KkSuppliersScreen> {
  bool _adding = false;
  (String, String)? _open;

  @override
  Widget build(BuildContext context) {
    final sid = widget.spaceId;
    final q = ref.watch(query(['kkSuppliers', sid], (c) => c.kkSuppliers(spaceId: sid)));
    final s = q.valueOrNull;
    return ScreenBody(
      mentorKey: 'mentor.kkSuppliers',
      children: [
        Hint(context.t('kk.supply.intro')),
        TemplateReviewNote(s?.templateReview),
        if (q.hasError) ErrorText(q.error),
        if (s != null)
          Semantics(
            container: true,
            label: context.t('kk.supply.totals'),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.stretch,
              children: [
                Kpi(
                  key: const Key('kk-supply-outstanding'),
                  label: context.t('kk.supply.outstanding'),
                  value: s.outstanding.formatted,
                  accent: true,
                ),
                Card(
                  shape: kkWarnShape(context, warn: s.overdue.minor != '0'),
                  child: Kpi(
                    key: const Key('kk-supply-overdue'),
                    label: context.t('kk.supply.overdue'),
                    value: s.overdue.formatted,
                  ),
                ),
                Kpi(
                  key: const Key('kk-supply-due-soon'),
                  label: context.t('kk.supply.dueSoon'),
                  value: s.dueSoon.formatted,
                ),
              ],
            ),
          ),
        Align(
          alignment: Alignment.centerLeft,
          child: KkActionButton(
            label: context.t('kk.supply.add'),
            active: !_adding,
            onPressed: () => setState(() => _adding = !_adding),
          ),
        ),
        if (_adding) _SupplierForm(spaceId: sid, onDone: () => setState(() => _adding = false)),
        Semantics(
          header: true,
          child: Text(context.t('kk.supply.list'), style: const TextStyle(fontSize: 18, fontWeight: FontWeight.w700)),
        ),
        if (s != null && s.suppliers.isEmpty) Hint(context.t('kk.supply.empty')),
        for (final x in s?.suppliers ?? const <KkSupplierDto>[])
          _SupplierCard(
            key: ValueKey(x.id),
            spaceId: sid,
            x: x,
            open: _open?.$1 == x.id ? _open!.$2 : null,
            onToggle: (m) => setState(() => _open = _open == (x.id, m) ? null : (x.id, m)),
            onDone: () => setState(() => _open = null),
          ),
      ],
    );
  }
}

class _SupplierCard extends StatelessWidget {
  const _SupplierCard({
    required this.spaceId,
    required this.x,
    required this.open,
    required this.onToggle,
    required this.onDone,
    super.key,
  });

  final String spaceId;
  final KkSupplierDto x;
  final String? open;
  final ValueChanged<String> onToggle;
  final VoidCallback onDone;

  @override
  Widget build(BuildContext context) {
    final a = x.agreement;
    final active = a.status != 'ENDED';
    final signed = a.signedVersions > 0;
    final unit = x.terms.unit == null ? null : context.t('kk.unit.${x.terms.unit}');
    final price = x.terms.unitPrice;
    Widget action(String m, String label) =>
        KkActionButton(label: label, active: open == m, onPressed: () => onToggle(m));
    return Semantics(
      container: true,
      label: x.name,
      child: Card(
        key: Key('kk-supplier-${x.name}'),
        shape: kkWarnShape(context, warn: x.overdue.minor != '0'),
        child: Padding(
          padding: const EdgeInsets.all(16),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.stretch,
            children: [
              Text(x.name, style: const TextStyle(fontSize: 18, fontWeight: FontWeight.w700)),
              AgreementStatus(a, testKey: 'kk-supplier-status'),
              const SizedBox(height: 4),
              ValueRow(context.t('kk.supply.goods'), x.terms.itemName ?? x.terms.goods ?? '—'),
              ValueRow(
                context.t('kk.supply.priceRow'),
                price == null
                    ? context.t('kk.supply.priceEach')
                    : unit == null
                    ? price.formatted
                    : '${price.formatted} / $unit',
              ),
              ValueRow(
                context.t('kk.supply.paymentRow'),
                context.t('kk.supply.paymentDaysValue', {'n': x.terms.paymentDays}),
              ),
              ValueRow(
                context.t('kk.supply.outstanding'),
                x.outstanding.formatted,
                key: const Key('kk-supplier-outstanding'),
              ),
              if (x.nextDue != null)
                ValueRow(
                  context.t('kk.supply.nextDue'),
                  context.t('kk.supply.nextDueValue', {
                    'date': showDate(x.nextDue!.date),
                    'amount': x.nextDue!.amount.formatted,
                  }),
                ),
              if (x.overdue.minor != '0') KkNote(context.t('kk.supply.overdueNote', {'amount': x.overdue.formatted})),
              const SizedBox(height: 8),
              Semantics(
                container: true,
                label: context.t('kk.agr.actions', {'name': x.name}),
                child: Wrap(
                  spacing: 8,
                  runSpacing: 8,
                  children: [
                    if (a.canSign) action('SIGN', context.t('kk.agr.sign')),
                    if (signed && active) action('DELIVERY', context.t('kk.supply.delivery')),
                    if (signed && x.outstanding.minor != '0') action('PAYMENT', context.t('kk.supply.payment')),
                    if (active) action('EDIT', context.t('kk.agr.edit')),
                    if (signed && active) action('END', context.t('kk.supply.end')),
                  ],
                ),
              ),
              const SizedBox(height: 8),
              AgreementFileActions(spaceId: spaceId, id: x.id, name: x.name, state: a),
              if (open == 'SIGN') SignForm(spaceId: spaceId, id: x.id, name: x.name, state: a, onDone: onDone),
              if (open == 'DELIVERY') _DeliveryForm(spaceId: spaceId, x: x, onDone: onDone),
              if (open == 'PAYMENT') _PaymentForm(spaceId: spaceId, x: x, onDone: onDone),
              if (open == 'EDIT') _SupplierForm(spaceId: spaceId, x: x, onDone: onDone),
              if (open == 'END') EndForm(spaceId: spaceId, id: x.id, name: x.name, onDone: onDone),
              if (x.deliveries.isNotEmpty)
                KkDetails(
                  summary: context.t('kk.supply.history', {'count': x.deliveries.length + x.payments.length}),
                  children: [
                    for (final d in x.deliveries)
                      KkHistoryRow(
                        title: '${showDate(d.deliveredOn)} · ${context.t('kk.supply.kind.DELIVERY')}',
                        value: d.amount.formatted,
                        note: [
                          if (d.qty != null && unit != null) '${d.qty} $unit',
                          context.t('kk.supply.state.${d.state}', {
                            'date': showDate(d.dueOn),
                            'days': d.overdueDays,
                          }),
                        ].join(' · '),
                      ),
                    for (final p in x.payments)
                      KkHistoryRow(
                        title: '${showDate(p.paidOn)} · ${context.t('kk.supply.kind.PAYMENT')}',
                        value: p.amount.formatted,
                        note: context.t('kk.wallet.${p.wallet}'),
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

class _DeliveryForm extends ConsumerStatefulWidget {
  const _DeliveryForm({required this.spaceId, required this.x, required this.onDone});

  final String spaceId;
  final KkSupplierDto x;
  final VoidCallback onDone;

  @override
  ConsumerState<_DeliveryForm> createState() => _DeliveryFormState();
}

class _DeliveryFormState extends ConsumerState<_DeliveryForm> with ActionState {
  final _qty = TextEditingController();
  final _amount = TextEditingController();
  String? _on;

  @override
  void dispose() {
    _qty.dispose();
    _amount.dispose();
    super.dispose();
  }

  Future<void> _save() async {
    final r = await act(
      () => ref
          .read(coreProvider)
          .kkSupplyDelivery(
            spaceId: widget.spaceId,
            id: widget.x.id,
            input: KkDeliveryInput(deliveredOn: _on, qty: kkOpt(_qty.text), amount: kkOpt(_amount.text)),
          ),
    );
    if (r != null) widget.onDone();
  }

  @override
  Widget build(BuildContext context) {
    final x = widget.x;
    final unit = x.terms.unit == null ? null : context.t('kk.unit.${x.terms.unit}');
    return Semantics(
      container: true,
      label: context.t('kk.supply.deliveryTitle', {'name': x.name}),
      child: KkBox(
        children: [
          Hint(context.t('kk.supply.deliveryHint', {'n': x.terms.paymentDays})),
          if (unit != null) ...[
            const SizedBox(height: 12),
            Field(
              label: context.t('kk.stock.qty', {'unit': unit}),
              controller: _qty,
              keyboardType: const TextInputType.numberWithOptions(decimal: true),
            ),
          ],
          const SizedBox(height: 12),
          AmountField(
            label: context.t(
              x.terms.unitPrice != null && unit != null ? 'kk.supply.amountOptional' : 'kk.supply.amount',
            ),
            controller: _amount,
          ),
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

class _PaymentForm extends ConsumerStatefulWidget {
  const _PaymentForm({required this.spaceId, required this.x, required this.onDone});

  final String spaceId;
  final KkSupplierDto x;
  final VoidCallback onDone;

  @override
  ConsumerState<_PaymentForm> createState() => _PaymentFormState();
}

class _PaymentFormState extends ConsumerState<_PaymentForm> with ActionState {
  late final _amount = TextEditingController(text: widget.x.nextDue?.amount.plain ?? '');
  String _wallet = 'CARD';
  String? _on;

  @override
  void dispose() {
    _amount.dispose();
    super.dispose();
  }

  Future<void> _save() async {
    final r = await act(
      () => ref
          .read(coreProvider)
          .kkSupplyPayment(
            spaceId: widget.spaceId,
            id: widget.x.id,
            input: KkSupplyPaymentInput(amount: kkOpt(_amount.text), wallet: _wallet, paidOn: _on),
          ),
    );
    if (r != null) widget.onDone();
  }

  @override
  Widget build(BuildContext context) => Semantics(
    container: true,
    label: context.t('kk.supply.paymentTitle', {'name': widget.x.name}),
    child: KkBox(
      children: [
        AmountField(label: context.t('kk.supply.amount'), controller: _amount),
        const SizedBox(height: 12),
        KkToggleRow<String>(
          label: context.t('kk.staff.fromWallet'),
          options: [
            for (final w in ['CASH', 'CARD']) (w, context.t('kk.wallet.$w')),
          ],
          value: _wallet,
          onChanged: (w) => setState(() => _wallet = w),
        ),
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

class _SupplierForm extends ConsumerStatefulWidget {
  const _SupplierForm({required this.spaceId, required this.onDone, this.x});

  final String spaceId;
  final KkSupplierDto? x;
  final VoidCallback onDone;

  @override
  ConsumerState<_SupplierForm> createState() => _SupplierFormState();
}

class _SupplierFormState extends ConsumerState<_SupplierForm> with ActionState {
  late final KkSupplierDto? x = widget.x;
  late final _name = TextEditingController(text: x?.name ?? '');
  late final _phone = TextEditingController(text: x?.phone ?? '');
  late bool _consent = x?.phone != null;
  late final _goods = TextEditingController(text: x?.terms.goods ?? '');
  late String _itemId = x?.terms.itemId ?? '';
  late final _price = TextEditingController(text: x?.terms.unitPrice?.plain ?? '');
  late final _days = TextEditingController(text: '${x?.terms.paymentDays ?? 30}');
  late final _delivery = TextEditingController(text: x?.terms.delivery ?? '');
  late final _returns = TextEditingController(text: x?.terms.returns ?? '');
  late String? _startedOn = x?.agreement.startedOn;
  late final _arbiter = TextEditingController(text: x?.terms.arbiter ?? '');
  late String? _reviewOn = x?.agreement.reviewOn;

  @override
  void dispose() {
    for (final c in [_name, _phone, _goods, _price, _days, _delivery, _returns, _arbiter]) {
      c.dispose();
    }
    super.dispose();
  }

  Future<void> _save() async {
    final core = ref.read(coreProvider);
    final input = KkSupplierInput(
      name: _name.text,
      phone: kkOpt(_phone.text),
      phoneConsent: _consent,
      goods: kkOpt(_goods.text),
      itemId: _itemId.isEmpty ? null : _itemId,
      unitPrice: kkOpt(_price.text),
      paymentDays: int.tryParse(_days.text.trim()) ?? 0,
      delivery: kkOpt(_delivery.text),
      returns: kkOpt(_returns.text),
      startedOn: _startedOn,
      arbiter: kkOpt(_arbiter.text),
      reviewOn: _reviewOn,
      note: x?.terms.note,
    );
    final r = await act(
      () => x == null
          ? core.kkAddSupplier(spaceId: widget.spaceId, input: input)
          : core.kkUpdateSupplier(spaceId: widget.spaceId, id: x!.id, input: input),
    );
    if (r != null) widget.onDone();
  }

  @override
  Widget build(BuildContext context) {
    final sid = widget.spaceId;
    final items = ref.watch(query(['kkStock', sid], (c) => c.kkStock(spaceId: sid))).valueOrNull?.items ?? [];
    final item = items.where((i) => i.id == _itemId).firstOrNull;
    final startLocked = x != null && x!.agreement.signedVersions > 0;
    const gap = SizedBox(height: 12);
    return Semantics(
      container: true,
      label: x == null ? context.t('kk.supply.add') : context.t('kk.agr.editTitle', {'name': x!.name}),
      child: KkBox(
        children: [
          Field(label: context.t('kk.supply.name'), controller: _name),
          gap,
          PhoneFields(phone: _phone, consent: _consent, onConsent: (v) => setState(() => _consent = v)),
          Select<String>(
            label: context.t('kk.supply.item'),
            items: [('', context.t('kk.supply.noItem')), for (final i in items) (i.id, i.name)],
            value: _itemId,
            onChanged: (v) => setState(() => _itemId = v ?? ''),
          ),
          Hint(context.t(_itemId.isEmpty ? 'kk.supply.noItemHint' : 'kk.supply.itemHint')),
          gap,
          Field(label: context.t('kk.supply.goods'), controller: _goods),
          gap,
          AmountField(
            label: item == null
                ? context.t('kk.supply.price')
                : context.t('kk.supply.priceUnit', {'unit': context.t('kk.unit.${item.unit}')}),
            controller: _price,
          ),
          gap,
          Field(label: context.t('kk.supply.paymentDays'), controller: _days, keyboardType: TextInputType.number),
          gap,
          Field(label: context.t('kk.supply.deliveryTerms'), controller: _delivery),
          gap,
          Field(label: context.t('kk.supply.returns'), controller: _returns),
          gap,
          if (startLocked)
            ValueRow(context.t('kk.supply.startedOn'), showDate(_startedOn ?? ''))
          else
            DateField(
              label: context.t('kk.supply.startedOn'),
              value: _startedOn,
              onChanged: (v) => setState(() => _startedOn = v),
            ),
          gap,
          Field(label: context.t('kk.agr.arbiter'), controller: _arbiter),
          gap,
          DateField(
            label: context.t('kk.agr.reviewOn'),
            value: _reviewOn,
            onChanged: (v) => setState(() => _reviewOn = v),
          ),
          ErrorText(error),
          const SizedBox(height: 8),
          Align(
            alignment: Alignment.centerLeft,
            child: FilledButton(
              onPressed: busy ? null : _save,
              child: Text(x == null ? context.t('kk.supply.addButton') : context.t('common.save')),
            ),
          ),
        ],
      ),
    );
  }
}
