import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../app/i18n.dart';
import '../../app/shell_state.dart';
import '../../app/theme.dart';
import '../../core/core.dart';
import '../../core/query.dart';
import '../../shared/format.dart';
import '../../shared/widgets.dart';
import '../home/home_screen.dart';
import 'kk_common.dart';
import 'kk_entry_sheet.dart';
import 'kk_salary_sheet.dart';

ProviderListenable<AsyncValue<KkOverviewDto>> kkOverviewQuery(String sid) =>
    query(['kk', sid], (c) => c.kkOverview(spaceId: sid));

/// Kasb-kor bosh sahifasi (kasbkor/SPEC 1, 2): 2-raqam — «Egasiga to'langan maosh»; pul oqimi
/// (haqiqiy foyda — K2), maosh kartasi, naqd kassa va karta, shu oy yozuvlari.
class KkHomeScreen extends ConsumerWidget {
  const KkHomeScreen({required this.spaceId, super.key});

  final String spaceId;

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final q = ref.watch(kkOverviewQuery(spaceId));
    final d = q.valueOrNull;
    final nudges = ref.watch(nudgesQuery(spaceId)).valueOrNull ?? [];
    final categories =
        ref.watch(query(['categories', spaceId], (c) => c.categories(spaceId: spaceId))).valueOrNull ?? <CategoryDto>[];
    final shell = ref.read(shellProvider.notifier);
    final p = context.palette;
    String category(String? id) {
      final c = categories.where((x) => x.id == id).firstOrNull;
      return c == null ? '' : (c.customName ?? context.t(c.nameKey));
    }

    if (d == null) {
      return q.hasError
          ? Padding(padding: const EdgeInsets.all(16), child: ErrorText(q.error))
          : const Center(child: CircularProgressIndicator());
    }
    return ScreenBody(
      mentorKey: 'mentor.kk',
      children: [
        if (nudges.isNotEmpty) Nudges(spaceId: spaceId, items: nudges),
        if (d.closeDue != null)
          _Reminder(
            key: const Key('kk-close-due'),
            text: context.t('kk.closeDue', {'date': showDate(d.closeDue!)}),
            action: context.t('kk.close.open'),
            onAction: () => shell.go('kkClose'),
            primary: true,
          ),
        Kpi(
          key: const Key('kk-true-profit'),
          label: context.t('kk.trueProfit'),
          value: d.profit.trueProfit.formatted,
          hint: context.t('kk.visibleProfitLine', {'amount': d.profit.visibleProfit.formatted}),
          accent: true,
        ),
        Kpi(
          key: const Key('kk-owner-paid'),
          label: context.t('kk.ownerPaid'),
          value: d.ownerPaid.formatted,
          hint: context.t('kk.ownerPaidSplit', {
            'salary': d.ownerSalaryTransferred.formatted,
            'draws': d.ownerDraws.formatted,
          }),
          accent: true,
        ),
        _ProfitCard(spaceId: spaceId, d: d),
        _SalaryCard(spaceId: spaceId, d: d),
        KkFigureCard(
          label: context.t('kk.cashFlow'),
          value: d.cashFlow.formatted,
          valueKey: const Key('kk-cash-flow'),
          lines: [
            (context.t('kk.cashFlowSplit', {'revenue': d.revenue.formatted, 'expenses': d.expenses.formatted}), false),
            (context.t('kk.cashFlowHint'), false),
            if (d.stockPurchases.minor != '0')
              (context.t('kk.stockPurchasesLine', {'amount': d.stockPurchases.formatted}), false),
          ],
        ),
        for (final w in kkWallets)
          KkFigureCard(
            label: context.t('kk.wallet.$w'),
            value: (w == 'CASH' ? d.cash : d.card).formatted,
            valueKey: Key('kk-wallet-$w'),
            warn: d.negativeWallets.contains(w),
            lines: [if (d.negativeWallets.contains(w)) (context.t('kk.negativeWallet'), true)],
          ),
        if (d.receivables.minor != '0')
          KkFigureCard(
            label: context.t('kk.receivables'),
            value: d.receivables.formatted,
            valueKey: const Key('kk-receivables'),
            lines: [
              if (d.receivablesOverdue.minor != '0')
                (context.t('kk.receivablesOverdue', {'amount': d.receivablesOverdue.formatted}), true),
            ],
            action: context.t('nav.kkCredit'),
            onAction: () => shell.go('kkCredit'),
          ),
        if (d.stockValue.minor != '0' || d.stockFrozenCount > 0)
          KkFigureCard(
            label: context.t('kk.stockValue'),
            value: d.stockValue.formatted,
            valueKey: const Key('kk-stock-value'),
            warn: d.stockFrozenCount > 0,
            lines: [
              if (d.stockFrozenCount > 0)
                (
                  context.t('kk.stockFrozen', {'amount': d.stockFrozenValue.formatted, 'count': d.stockFrozenCount}),
                  true,
                ),
            ],
            action: context.t('nav.kkStock'),
            onAction: () => shell.go('kkStock'),
          ),
        if (d.zakatReminder != null)
          _Reminder(
            key: const Key('kk-zakat-reminder'),
            text: context.t('kk.zakatReminder', {'date': showDate(d.zakatReminder!)}),
            action: context.t('nav.kkZakat'),
            onAction: () => shell.go('kkZakat'),
          ),
        if (d.scaleCheckDue)
          _Reminder(
            key: const Key('kk-scale-reminder'),
            text: context.t('kk.scaleReminder'),
            action: context.t('nav.kkMeasure'),
            onAction: () => shell.go('kkMeasure'),
          ),
        if (d.payables.minor != '0')
          KkFigureCard(
            label: context.t('kk.payables'),
            value: d.payables.formatted,
            valueKey: const Key('kk-payables'),
            lines: [
              if (d.payablesOverdue.minor != '0')
                (context.t('kk.payablesOverdue', {'amount': d.payablesOverdue.formatted}), true),
            ],
            action: context.t('nav.kkSuppliers'),
            onAction: () => shell.go('kkSuppliers'),
          ),
        if (d.wagesOwed.minor != '0')
          KkFigureCard(
            label: context.t('kk.wagesOwed'),
            value: d.wagesOwed.formatted,
            valueKey: const Key('kk-wages-owed'),
            action: context.t('nav.kkStaff'),
            onAction: () => shell.go('kkStaff'),
          ),
        Semantics(
          container: true,
          label: context.t('kk.actions'),
          child: Wrap(
            spacing: 8,
            runSpacing: 8,
            children: [
              for (final (i, a) in kkEntryModes.indexed)
                kkButton(
                  primary: i == 0,
                  onPressed: () => openKkEntry(context, spaceId, a),
                  label: context.t('kk.action.$a'),
                ),
            ],
          ),
        ),
        SectionCard(
          title: context.t('kk.entries'),
          children: [
            Hint(context.t('kk.period', {'from': showDate(d.periodStart), 'to': showDate(d.periodEnd)})),
            if (d.entries.isEmpty) ...[const SizedBox(height: 8), Hint(context.t('kk.noEntries'))],
            for (final e in d.entries)
              Container(
                padding: const EdgeInsets.symmetric(vertical: 8),
                decoration: BoxDecoration(
                  border: Border(top: BorderSide(color: p.line)),
                ),
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.stretch,
                  children: [
                    Row(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        Expanded(
                          child: Text('${showDate(e.occurredOn)} · ${context.t('kk.kind.${e.kind}')}'),
                        ),
                        Text(
                          e.amount.formatted,
                          style: TextStyle(
                            color: e.kind == 'SALE' ? p.accentText : null,
                            fontFeatures: const [FontFeature.tabularFigures()],
                          ),
                        ),
                      ],
                    ),
                    Hint(
                      [
                        context.t('kk.wallet.${e.wallet}') +
                            (e.toWallet == null ? '' : ' → ${context.t('kk.wallet.${e.toWallet}')}'),
                        category(e.categoryId),
                        ?e.note,
                      ].where((x) => x.isNotEmpty).join(' · '),
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

class _Reminder extends StatelessWidget {
  const _Reminder({
    required this.text,
    required this.action,
    required this.onAction,
    this.primary = false,
    super.key,
  });

  final String text;
  final String action;
  final VoidCallback onAction;
  final bool primary;

  @override
  Widget build(BuildContext context) => SectionCard(
    children: [
      Text(text),
      const SizedBox(height: 8),
      Align(
        alignment: Alignment.centerLeft,
        child: primary
            ? FilledButton(onPressed: onAction, child: Text(action))
            : OutlinedButton(onPressed: onAction, child: Text(action)),
      ),
    ],
  );
}

/// Haqiqiy foyda tarkibi (kasbkor/SPEC 3.1). Summalar yadrodan tayyor; UI faqat ko'rsatadi.
/// O'z mehnati bahosi egasi maoshi bilan yonma-yon.
class _ProfitCard extends StatefulWidget {
  const _ProfitCard({required this.spaceId, required this.d});

  final String spaceId;
  final KkOverviewDto d;

  @override
  State<_ProfitCard> createState() => _ProfitCardState();
}

class _ProfitCardState extends State<_ProfitCard> {
  bool _editing = false;

  /// Manfiy qiymat foydaga qo'shiladi (ortiqcha topilgan tovar, balansdan qimmat sotilgan uskuna):
  /// faqat belgi almashadi — hisob yo'q.
  String _signed(MoneyDto m) => kkNegative(m.minor) ? '+ ${m.formatted.substring(1)}' : '− ${m.formatted}';

  @override
  Widget build(BuildContext context) {
    final d = widget.d;
    final p = d.profit;
    final pal = context.palette;
    final rows = <(String, String, String?)>[
      (context.t('kk.profit.revenue'), p.revenue.formatted, null),
      (context.t('kk.profit.cogs'), '− ${p.cogs.formatted}', context.t('kk.profit.cogsHint')),
      if (p.stockLosses.minor != '0') (context.t('kk.profit.stockLosses'), _signed(p.stockLosses), null),
      (context.t('kk.profit.operating'), '− ${p.operatingExpenses.formatted}', null),
      (context.t('kk.profit.visible'), p.visibleProfit.formatted, null),
      (
        context.t('kk.profit.ownerLabor'),
        p.ownerLabor == null ? context.t('kk.profit.notSet') : '− ${p.ownerLabor!.formatted}',
        null,
      ),
      (
        context.t('kk.profit.familyLabor'),
        '− ${p.familyLabor.formatted}',
        p.familyLaborPaid.minor != '0'
            ? context.t('kk.profit.familyPaid', {'amount': p.familyLaborPaid.formatted})
            : null,
      ),
      (context.t('kk.profit.depreciation'), '− ${p.depreciation.formatted}', null),
      if (p.disposal.minor != '0') (context.t('kk.profit.disposal'), _signed(p.disposal), null),
    ];
    return SectionCard(
      title: context.t('kk.profit.title'),
      children: [
        Align(
          alignment: Alignment.centerLeft,
          child: TextButton(
            onPressed: () => setState(() => _editing = !_editing),
            child: Text(context.t(p.ownerLabor == null ? 'kk.ownerLaborSet' : 'kk.ownerLaborChange')),
          ),
        ),
        if (_editing)
          _AmountForm(
            spaceId: widget.spaceId,
            label: context.t('kk.ownerLaborAmount'),
            hint: context.t('kk.ownerLaborHint'),
            initial: p.ownerLabor?.plain ?? '',
            save: (core, amount) => core.kkSetOwnerLabor(spaceId: widget.spaceId, amount: amount),
            onDone: () => setState(() => _editing = false),
          ),
        if (p.ownerLabor == null) Text(context.t('kk.ownerLaborMissing'), style: TextStyle(color: pal.warn)),
        for (final (label, value, hint) in rows)
          Container(
            decoration: BoxDecoration(
              border: Border(top: BorderSide(color: pal.line)),
            ),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.stretch,
              children: [
                ValueRow(label, value),
                if (hint != null) Padding(padding: const EdgeInsets.only(bottom: 6), child: Hint(hint)),
              ],
            ),
          ),
        Container(
          decoration: BoxDecoration(
            border: Border(top: BorderSide(color: pal.line)),
          ),
          child: ValueRow(context.t('kk.trueProfitShort'), p.trueProfit.formatted, strong: true),
        ),
        const SizedBox(height: 8),
        Hint(
          context.t('kk.laborVsSalary', {
            'labor': p.ownerLabor?.formatted ?? '—',
            'salary': d.ownerSalary?.formatted ?? '—',
          }),
        ),
      ],
    );
  }
}

class _SalaryCard extends StatefulWidget {
  const _SalaryCard({required this.spaceId, required this.d});

  final String spaceId;
  final KkOverviewDto d;

  @override
  State<_SalaryCard> createState() => _SalaryCardState();
}

class _SalaryCardState extends State<_SalaryCard> {
  bool _editing = false;

  @override
  Widget build(BuildContext context) {
    final d = widget.d;
    final salary = d.ownerSalary;
    return SectionCard(
      title: context.t('kk.salary'),
      children: [
        Align(
          alignment: Alignment.centerLeft,
          child: TextButton(
            onPressed: () => setState(() => _editing = !_editing),
            child: Text(context.t(salary == null ? 'kk.salarySet' : 'kk.salaryChange')),
          ),
        ),
        if (_editing)
          _AmountForm(
            spaceId: widget.spaceId,
            label: context.t('kk.salaryAmount'),
            initial: salary?.plain ?? '',
            save: (core, amount) => core.kkSetOwnerSalary(spaceId: widget.spaceId, amount: amount),
            onDone: () => setState(() => _editing = false),
          ),
        if (salary == null)
          Hint(context.t('kk.salaryHint'))
        else ...[
          Text(context.t('kk.salaryMonthly', {'amount': salary.formatted})),
          Text(
            context.t('kk.salaryRemaining', {'amount': d.salaryRemaining?.formatted ?? ''}),
            key: const Key('kk-salary-remaining'),
          ),
          if (d.salaryCarry != null) Hint(context.t('kk.salaryCarry', {'amount': d.salaryCarry!.formatted})),
          if (d.overdrawn != null)
            Text(
              context.t('kk.overdrawn', {'amount': d.overdrawn!.formatted}),
              style: TextStyle(color: context.palette.warn),
            ),
          const SizedBox(height: 8),
          Align(
            alignment: Alignment.centerLeft,
            child: FilledButton(
              onPressed: () => openKkSalary(context, widget.spaceId, d),
              child: Text(context.t('kk.paySalary')),
            ),
          ),
        ],
      ],
    );
  }
}

/// Bitta summa kiritish formasi (egasi maoshi yoki o'z mehnati bahosi).
class _AmountForm extends ConsumerStatefulWidget {
  const _AmountForm({
    required this.spaceId,
    required this.label,
    required this.initial,
    required this.save,
    required this.onDone,
    this.hint,
  });

  final String spaceId;
  final String label;
  final String? hint;
  final String initial;
  final Future<Object?> Function(BarakaCore core, String amount) save;
  final VoidCallback onDone;

  @override
  ConsumerState<_AmountForm> createState() => _AmountFormState();
}

class _AmountFormState extends ConsumerState<_AmountForm> with ActionState {
  late final _amount = TextEditingController(text: widget.initial);

  @override
  void dispose() {
    _amount.dispose();
    super.dispose();
  }

  Future<void> _submit() async {
    final r = await act(() => widget.save(ref.read(coreProvider), _amount.text));
    if (r != null) widget.onDone();
  }

  @override
  Widget build(BuildContext context) => Padding(
    padding: const EdgeInsets.only(bottom: 12),
    child: Column(
      crossAxisAlignment: CrossAxisAlignment.stretch,
      children: [
        AmountField(label: widget.label, controller: _amount, hint: widget.hint),
        if (widget.hint != null) ...[const SizedBox(height: 4), Hint(widget.hint!)],
        ErrorText(error),
        const SizedBox(height: 8),
        Align(
          alignment: Alignment.centerLeft,
          child: FilledButton(onPressed: busy ? null : _submit, child: Text(context.t('common.save'))),
        ),
      ],
    ),
  );
}
