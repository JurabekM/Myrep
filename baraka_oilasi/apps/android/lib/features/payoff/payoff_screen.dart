import 'dart:async';

import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../app/i18n.dart';
import '../../app/theme.dart';
import '../../core/core.dart';
import '../../core/query.dart';
import '../../shared/balance_chart.dart';
import '../../shared/debt_widgets.dart';
import '../../shared/format.dart';
import '../../shared/widgets.dart';

/// «Qarzdan chiqish» (uy/SPEC 2D.1, 2D.2, 2D.7, 2D.9): 70/20/10 rejimi, odatiy va qo'shimcha
/// to'lovli prognoz, yopish tartibi, «Qarzsiz kun» va sotiladigan buyumlar. Barcha hisob — yadroda.
class PayoffScreen extends ConsumerStatefulWidget {
  const PayoffScreen({required this.spaceId, super.key});

  final String spaceId;

  @override
  ConsumerState<PayoffScreen> createState() => _PayoffScreenState();
}

class _PayoffScreenState extends ConsumerState<PayoffScreen> {
  final _extra = TextEditingController();
  String? _applied;

  @override
  void dispose() {
    _extra.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    final id = widget.spaceId;
    final mode = ref.watch(query(['budget', id], (c) => c.budgetMode(spaceId: id)));
    final plan = ref.watch(
      query(
        ['planner', id, _applied],
        (c) => c.payoffPlanner(
          spaceId: id,
          input: PlannerInput(extraPerMonth: _applied),
        ),
      ),
    );
    final pl = plan.valueOrNull;
    return ScreenBody(
      mentorKey: 'mentor.debts',
      children: [
        if (mode.valueOrNull != null) _ModeCard(spaceId: id, mode: mode.valueOrNull!),
        if (mode.hasError) ErrorText(mode.error),
        if (plan.hasError) ErrorText(plan.error),
        if (pl != null && pl.debts.isEmpty) SectionCard(children: [Hint(context.t('payoff.noDebts'))]),
        if (pl != null && pl.debts.isNotEmpty) ...[
          SectionCard(
            children: [
              AmountField(label: context.t('payoff.extra'), controller: _extra, hint: pl.extraPerMonth.plain),
              const SizedBox(height: 8),
              Align(
                alignment: Alignment.centerLeft,
                child: FilledButton(
                  onPressed: () => setState(() => _applied = _extra.text.trim().isEmpty ? null : _extra.text),
                  child: Text(context.t('payoff.calculate')),
                ),
              ),
              const SizedBox(height: 8),
              Hint(context.t('payoff.source.${pl.extraSource}', {'amount': pl.extraPerMonth.formatted})),
            ],
          ),
          Kpi(
            label: context.t('payoff.debtFreeBase'),
            value: pl.base.payoffDate == null ? '—' : showDate(pl.base.payoffDate!),
            hint: context.t('payoff.months', {'count': pl.base.months}),
          ),
          Kpi(
            key: const Key('payoff-fast'),
            label: context.t('payoff.debtFreeFast'),
            value: pl.accelerated.payoffDate == null ? '—' : showDate(pl.accelerated.payoffDate!),
            hint: context.t('payoff.earlier', {'count': pl.monthsSaved}),
            accent: true,
          ),
          Kpi(
            label: context.t('payoff.saved'),
            value: pl.netSaved.formatted,
            accent: true,
            hint: pl.accelerated.fees.minor == '0'
                ? context.t('payoff.savedInterest', {'interest': pl.interestSaved.formatted})
                : context.t('payoff.savedDetail', {
                    'interest': pl.interestSaved.formatted,
                    'fees': pl.accelerated.fees.formatted,
                  }),
          ),
          if (pl.excludedForeign > 0) Hint(context.t('payoff.foreign', {'count': pl.excludedForeign})),
          SectionCard(children: [BalanceChart(points: pl.timeline)]),
          _OrderList(spaceId: id, debts: pl.debts),
          Card(
            child: ExpansionTile(
              title: Text(context.t('payoff.table')),
              childrenPadding: const EdgeInsets.fromLTRB(16, 0, 16, 16),
              children: [
                for (final r in pl.schedule)
                  Padding(
                    padding: const EdgeInsets.symmetric(vertical: 4),
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.stretch,
                      children: [
                        Text(showMonth(r.month), style: const TextStyle(fontWeight: FontWeight.w700)),
                        ValueRow(context.t('payoff.col.due'), r.due.formatted),
                        ValueRow(context.t('loan.col.interest'), r.interest.formatted),
                        ValueRow(context.t('loan.col.extra'), r.extra.formatted),
                        if (r.fee.minor != '0') ValueRow(context.t('payoff.col.fee'), r.fee.formatted),
                        ValueRow(context.t('loan.col.balance'), r.balance.formatted, strong: true),
                        const Divider(),
                      ],
                    ),
                  ),
              ],
            ),
          ),
          Hint(context.t('loan.estimate')),
        ],
        _Items(spaceId: id, debts: pl?.debts ?? const []),
      ],
    );
  }
}

/// Foiz (butun son) → bp. Pul emas; noto'g'ri qiymat yadroga yuborilmaydi.
int _toBp(String v) {
  if (!RegExp(r'^\d{1,3}$').hasMatch(v.trim())) throw const AppError(code: 'INVALID_NUMBER');
  return int.parse(v.trim()) * 100;
}

class _ModeCard extends ConsumerStatefulWidget {
  const _ModeCard({required this.spaceId, required this.mode});

  final String spaceId;
  final BudgetModeDto mode;

  @override
  ConsumerState<_ModeCard> createState() => _ModeCardState();
}

class _ModeCardState extends ConsumerState<_ModeCard> with ActionState {
  late final _h = TextEditingController(text: widget.mode.householdPercent);
  late final _e = TextEditingController(text: widget.mode.extraDebtPercent);
  late final _s = TextEditingController(text: widget.mode.savingsPercent);

  @override
  void dispose() {
    _h.dispose();
    _e.dispose();
    _s.dispose();
    super.dispose();
  }

  Future<void> _save(String mode) => act(
    () => ref
        .read(coreProvider)
        .setBudgetMode(
          spaceId: widget.spaceId,
          input: BudgetModeInput(
            mode: mode,
            householdBp: _toBp(_h.text),
            extraDebtBp: _toBp(_e.text),
            savingsBp: _toBp(_s.text),
          ),
        ),
  );

  Widget _part(String label, TextEditingController c, String amount, [List<String> notes = const []]) {
    final p = context.palette;
    return Container(
      margin: const EdgeInsets.only(bottom: 8),
      padding: const EdgeInsets.all(12),
      decoration: BoxDecoration(
        border: Border.all(color: p.line),
        borderRadius: BorderRadius.circular(10),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: [
          Row(
            children: [
              Expanded(child: Text(label)),
              SizedBox(
                width: 72,
                child: Field(
                  label: '%',
                  controller: c,
                  keyboardType: TextInputType.number,
                  textAlign: TextAlign.end,
                ),
              ),
            ],
          ),
          const SizedBox(height: 6),
          Text(amount, style: const TextStyle(fontSize: 18, fontWeight: FontWeight.w700)),
          for (final n in notes) Hint(n, color: n == context.t('mode.short') ? p.danger : null),
        ],
      ),
    );
  }

  @override
  Widget build(BuildContext context) {
    final m = widget.mode;
    final recovery = m.mode == 'DEBT_RECOVERY';
    final p = context.palette;
    return SectionCard(
      title: context.t('mode.${m.mode}'),
      children: [
        if (m.changedOn != null) Hint(context.t('mode.since', {'date': showDate(m.changedOn!)})),
        if (m.suggested)
          Container(
            margin: const EdgeInsets.symmetric(vertical: 8),
            padding: const EdgeInsets.all(12),
            decoration: BoxDecoration(
              border: Border.all(color: p.warn),
              borderRadius: BorderRadius.circular(10),
            ),
            child: Text(context.t('mode.suggest')),
          ),
        Hint(context.t('mode.why')),
        const SizedBox(height: 8),
        _part(context.t('mode.household'), _h, m.household.formatted, [
          context.t('mode.mandatory', {'amount': m.mandatoryDebtPayments.formatted}),
          if (m.householdShort) context.t('mode.short'),
        ]),
        _part(context.t('mode.extra'), _e, m.extraDebt.formatted),
        _part(context.t('mode.savings'), _s, m.savings.formatted, [context.t('mode.savingsMin')]),
        if (m.monthlyIncome == null) Hint(context.t('debts.loadUnknown')),
        ErrorText(error),
        Wrap(
          spacing: 8,
          children: [
            if (recovery || m.hasActiveDebt)
              FilledButton(
                onPressed: busy ? null : () => _save('DEBT_RECOVERY'),
                child: Text(recovery ? context.t('common.save') : context.t('mode.enable')),
              ),
            if (recovery)
              OutlinedButton(onPressed: busy ? null : () => _save('STANDARD'), child: Text(context.t('mode.disable'))),
          ],
        ),
      ],
    );
  }
}

class _OrderList extends ConsumerStatefulWidget {
  const _OrderList({required this.spaceId, required this.debts});

  final String spaceId;
  final List<PlannerDebtDto> debts;

  @override
  ConsumerState<_OrderList> createState() => _OrderListState();
}

class _OrderListState extends ConsumerState<_OrderList> with ActionState {
  void _move(int i, int d) {
    final ids = [for (final x in widget.debts) x.id];
    final j = i + d;
    final a = ids[i];
    ids[i] = ids[j];
    ids[j] = a;
    unawaited(act(() => ref.read(coreProvider).setDebtOrder(spaceId: widget.spaceId, debtIds: ids)));
  }

  @override
  Widget build(BuildContext context) {
    final debts = widget.debts;
    final p = context.palette;
    return SectionCard(
      title: context.t('payoff.order'),
      trailing: debts.any((d) => d.manualOrder)
          ? TextButton(
              onPressed: () => act(() => ref.read(coreProvider).resetDebtOrder(spaceId: widget.spaceId)),
              child: Text(context.t('payoff.orderReset')),
            )
          : null,
      children: [
        Hint(context.t('payoff.orderHint')),
        for (final (i, d) in debts.indexed)
          Padding(
            padding: const EdgeInsets.only(top: 8),
            child: Row(
              children: [
                SizedBox(
                  width: 28,
                  child: Text(
                    '${d.order}',
                    style: TextStyle(fontSize: 18, fontWeight: FontWeight.w700, color: p.accentText),
                  ),
                ),
                Expanded(
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Wrap(
                        spacing: 6,
                        children: [
                          Text(d.creditor, style: const TextStyle(fontWeight: FontWeight.w700)),
                          if (d.isRibo) Tag(context.t('debts.ribo'), tone: 'danger'),
                        ],
                      ),
                      Hint(
                        [
                          '${d.balance.formatted} · ${d.basePayoff == null ? '—' : showDate(d.basePayoff!)} → ${d.acceleratedPayoff == null ? '—' : showDate(d.acceleratedPayoff!)}',
                          if (d.monthsSaved > 0) context.t('payoff.earlier', {'count': d.monthsSaved}),
                          if (d.fees.minor != '0') context.t('payoff.feesShort', {'amount': d.fees.formatted}),
                        ].join(' · '),
                      ),
                    ],
                  ),
                ),
                IconButton(
                  tooltip: context.t('payoff.up', {'name': d.creditor}),
                  icon: const Icon(Icons.arrow_upward),
                  onPressed: i == 0 || busy ? null : () => _move(i, -1),
                ),
                IconButton(
                  tooltip: context.t('payoff.down', {'name': d.creditor}),
                  icon: const Icon(Icons.arrow_downward),
                  onPressed: i == debts.length - 1 || busy ? null : () => _move(i, 1),
                ),
              ],
            ),
          ),
        ErrorText(error),
      ],
    );
  }
}

class _Items extends ConsumerStatefulWidget {
  const _Items({required this.spaceId, required this.debts});

  final String spaceId;
  final List<PlannerDebtDto> debts;

  @override
  ConsumerState<_Items> createState() => _ItemsState();
}

class _ItemsState extends ConsumerState<_Items> with ActionState {
  final _title = TextEditingController();
  final _estimated = TextEditingController();

  @override
  void dispose() {
    _title.dispose();
    _estimated.dispose();
    super.dispose();
  }

  Future<void> _add() async {
    final r = await act(
      () => ref
          .read(coreProvider)
          .addSellableItem(
            spaceId: widget.spaceId,
            input: NewSellableItemInput(title: _title.text, estimated: _estimated.text, currency: 'UZS'),
          ),
    );
    if (r != null) {
      _title.clear();
      _estimated.clear();
    }
  }

  @override
  Widget build(BuildContext context) {
    final id = widget.spaceId;
    final items = ref.watch(query(['items', id], (c) => c.sellableItems(spaceId: id)));
    return SectionCard(
      title: context.t('items.title'),
      children: [
        Hint(context.t('items.intro')),
        for (final i in items.valueOrNull ?? <SellableItemDto>[]) _Item(spaceId: id, item: i, debts: widget.debts),
        const SizedBox(height: 8),
        Field(label: context.t('items.name'), controller: _title),
        const SizedBox(height: 8),
        AmountField(label: context.t('items.estimated'), controller: _estimated),
        ErrorText(items.error ?? error),
        Align(
          alignment: Alignment.centerLeft,
          child: OutlinedButton(onPressed: busy ? null : _add, child: Text(context.t('goals.add'))),
        ),
      ],
    );
  }
}

class _Item extends ConsumerStatefulWidget {
  const _Item({required this.spaceId, required this.item, required this.debts});

  final String spaceId;
  final SellableItemDto item;
  final List<PlannerDebtDto> debts;

  @override
  ConsumerState<_Item> createState() => _ItemState();
}

class _ItemState extends ConsumerState<_Item> with ActionState {
  late final _price = TextEditingController(text: widget.item.estimated.plain);
  late String _debtId = widget.debts.firstOrNull?.id ?? '';
  bool _open = false;

  @override
  void dispose() {
    _price.dispose();
    super.dispose();
  }

  Future<void> _sell() async {
    final r = await act(
      () => ref
          .read(coreProvider)
          .sellItem(
            spaceId: widget.spaceId,
            itemId: widget.item.id,
            input: SellItemInput(price: _price.text, debtId: _debtId.isEmpty ? null : _debtId),
          ),
    );
    if (r == null || !mounted) return;
    setState(() => _open = false);
    final rep = r.repayment;
    if (rep != null) await celebrateIfClosed(context, widget.spaceId, rep);
  }

  @override
  Widget build(BuildContext context) {
    final i = widget.item;
    final sold = i.status == 'SOLD';
    return Padding(
      padding: const EdgeInsets.only(top: 8),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: [
          Row(
            children: [
              Expanded(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text(i.title, style: const TextStyle(fontWeight: FontWeight.w700)),
                    Hint(
                      sold
                          ? context.t('items.sold', {
                              'amount': i.sold?.formatted ?? '',
                              'date': showDate(i.soldOn ?? ''),
                            })
                          : context.t('items.listed', {'amount': i.estimated.formatted}),
                    ),
                  ],
                ),
              ),
              if (!sold)
                TextButton(onPressed: () => setState(() => _open = !_open), child: Text(context.t('items.sell'))),
            ],
          ),
          if (_open) ...[
            const SizedBox(height: 8),
            AmountField(label: context.t('items.price'), controller: _price),
            const SizedBox(height: 8),
            Select<String>(
              label: context.t('items.toDebt'),
              items: [for (final d in widget.debts) (d.id, d.creditor), ('', context.t('items.noDebt'))],
              value: _debtId,
              onChanged: (v) => setState(() => _debtId = v ?? ''),
            ),
            ErrorText(error),
            Align(
              alignment: Alignment.centerLeft,
              child: FilledButton(onPressed: busy ? null : _sell, child: Text(context.t('common.save'))),
            ),
          ],
          const Divider(),
        ],
      ),
    );
  }
}
