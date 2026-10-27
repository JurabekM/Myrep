import 'package:baraka_daftari/app/l10n/l10n.dart';
import 'package:baraka_daftari/app/refresh.dart';
import 'package:baraka_daftari/app/widgets/labels.dart';
import 'package:baraka_daftari/app/widgets/money_input.dart';
import 'package:baraka_daftari/core/domain/enums.dart';
import 'package:baraka_daftari/core/errors/data_exceptions.dart';
import 'package:baraka_daftari/core/logging/app_log.dart';
import 'package:baraka_daftari/core/money/money.dart';
import 'package:baraka_daftari/core/time/calendar.dart';
import 'package:baraka_daftari/core/time/clock.dart';
import 'package:baraka_daftari/features/debts/data/debt_providers.dart';
import 'package:baraka_daftari/features/debts/domain/debt_math.dart';
import 'package:baraka_daftari/features/debts/domain/debt_service.dart';
import 'package:baraka_daftari/features/debts/domain/debts.dart';
import 'package:baraka_daftari/features/debts/presentation/debts_screen.dart';
import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

/// Yangi qarz (SPEC 2C.7, 2D.5, 2D.6): «to'xta va o'yla» → shartlar va
/// to'lov rejasi (majburiy) → haqiqiy narx.
class DebtNewScreen extends ConsumerStatefulWidget {
  const DebtNewScreen({super.key});

  @override
  ConsumerState<DebtNewScreen> createState() => _DebtNewScreenState();
}

class _DebtNewScreenState extends ConsumerState<DebtNewScreen> {
  int _step = 0;
  bool? _necessity;
  BorrowAlternative? _alternative;

  CreditorType _creditor = CreditorType.relative;
  final _name = TextEditingController();
  final _reason = TextEditingController();
  final _term = TextEditingController(text: '12');
  final _rate = TextEditingController();
  final _early = TextEditingController();
  Money? _principal;
  Money? _markup;
  DebtScheduleType _type = DebtScheduleType.manual;
  final List<Installment> _manual = [];
  bool _saving = false;

  LocalDate get _today => Tashkent.dateOf(ref.read(clockProvider).nowUtc());

  @override
  void dispose() {
    _name.dispose();
    _reason.dispose();
    _term.dispose();
    _rate.dispose();
    _early.dispose();
    super.dispose();
  }

  int get _rateBp => parsePercentBp(_rate.text) ?? 0;
  int get _termMonths => int.tryParse(_term.text) ?? 0;

  /// Joriy shakl bo'yicha reja; yaroqsiz bo'lsa `null`.
  List<Installment>? _schedule() {
    final p = _principal;
    if (p == null || !p.isPositive) return null;
    if (_type == DebtScheduleType.manual) {
      return _manual.isEmpty ? null : _manual;
    }
    if (_termMonths <= 0 || _termMonths > 600) return null;
    return buildSchedule(
      type: _type,
      principal: p,
      start: _today,
      termMonths: _termMonths,
      annualRateBp: _type == DebtScheduleType.fixedMarkup ? 0 : _rateBp,
      markup: _type == DebtScheduleType.fixedMarkup ? _markup : null,
    );
  }

  bool get _isRiba => isInterestBearing(
    hasMarkup: false,
    annualRateBp: _type == DebtScheduleType.fixedMarkup ? 0 : _rateBp,
    markup: _type == DebtScheduleType.fixedMarkup ? _markup : null,
  );

  Future<void> _pickPrincipal() async {
    final m = await showAmountSheet(
      context,
      currency: CurrencyCode.uzs,
      title: context.l10n.debtAmountLabel,
      initial: _principal,
    );
    if (m == null || !m.isPositive) return;
    setState(() {
      _principal = m;
      // Qo'lda reja: standart — bitta qator, 30 kundan keyin, to'liq summa.
      if (_manual.isEmpty) {
        _manual.add(
          Installment(
            dueOn: _today.plusDays(30),
            amount: m,
            interest: Money.zero(m.currency),
          ),
        );
      }
    });
  }

  Future<void> _addManualRow() async {
    final last = _manual.isEmpty ? _today : _manual.last.dueOn;
    final picked = await showDatePicker(
      context: context,
      firstDate: DateTime(_today.year - 1),
      lastDate: DateTime(_today.year + 30),
      initialDate: () {
        final d = last.plusMonths(1);
        return DateTime(d.year, d.month, d.day);
      }(),
    );
    if (picked == null || !mounted) return;
    final amount = await showAmountSheet(
      context,
      currency: CurrencyCode.uzs,
      title: context.l10n.manualRowAmount,
    );
    if (amount == null || !amount.isPositive) return;
    setState(() {
      _manual
        ..add(
          Installment(
            dueOn: LocalDate.fromDateTime(picked),
            amount: amount,
            interest: Money.zero(amount.currency),
          ),
        )
        ..sort((a, b) => a.dueOn.compareTo(b.dueOn));
    });
  }

  Future<void> _save() async {
    final l10n = context.l10n;
    final messenger = ScaffoldMessenger.of(context);
    final navigator = Navigator.of(context);
    setState(() => _saving = true);
    try {
      final overview = await ref.read(debtOverviewProvider.future);
      final schedule = _schedule()!;
      final income = overview.monthlyIncome;
      await (await ref.read(debtServiceProvider.future)).add(
        creditorType: _creditor,
        creditorName: _name.text,
        principal: _principal!,
        scheduleType: _type,
        termMonths: _type == DebtScheduleType.manual ? 0 : _termMonths,
        annualRateBp: _type == DebtScheduleType.fixedMarkup ? 0 : _rateBp,
        markup: _type == DebtScheduleType.fixedMarkup ? _markup : null,
        manual: _type == DebtScheduleType.manual ? _manual : const [],
        reason: _reason.text,
        earlyRepaymentTerms: _early.text.trim().isEmpty
            ? null
            : _early.text.trim(),
        check: BorrowCheck(
          isNecessity: _necessity ?? true,
          alternative: _alternative ?? BorrowAlternative.none,
          loadBp: income == null
              ? null
              : debtLoadBp(
                  overview.monthlyPayments + schedule.first.amount,
                  income,
                ),
        ),
      );
      refreshMoneyViews(ref);
      await recordDebtInventory(ref);
      navigator.pop();
    } on DomainRuleException catch (e) {
      AppLog.event('debt_rejected_${e.code}');
      messenger.showSnackBar(
        SnackBar(
          content: Text(
            e.code == DebtService.errScheduleRequired
                ? l10n.scheduleRequired
                : l10n.genericError,
          ),
        ),
      );
      if (mounted) setState(() => _saving = false);
    } on Object {
      AppLog.event('debt_save_failed');
      messenger.showSnackBar(SnackBar(content: Text(l10n.genericError)));
      if (mounted) setState(() => _saving = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    final l10n = context.l10n;
    return Scaffold(
      appBar: AppBar(title: Text(l10n.debtAdd)),
      body: Center(
        child: ConstrainedBox(
          constraints: const BoxConstraints(maxWidth: 620),
          child: _step == 0 ? _friction(context) : _form(context),
        ),
      ),
    );
  }

  Widget _friction(BuildContext context) {
    final l10n = context.l10n;
    final theme = Theme.of(context);
    Widget choice<T>(
      String key,
      T value,
      T? group,
      String label,
      void Function(T) on,
    ) => ChoiceChip(
      key: Key(key),
      label: Text(label),
      selected: value == group,
      onSelected: (_) => setState(() => on(value)),
    );
    return ListView(
      padding: const EdgeInsets.all(16),
      children: [
        Text(l10n.checkTitle, style: theme.textTheme.headlineSmall),
        Text(l10n.checkHint),
        const SizedBox(height: 16),
        Text(l10n.checkNecessity, style: theme.textTheme.titleSmall),
        Wrap(
          spacing: 8,
          children: [
            choice(
              'check-need',
              true,
              _necessity,
              l10n.checkNeed,
              (v) => _necessity = v,
            ),
            choice(
              'check-luxury',
              false,
              _necessity,
              l10n.checkLuxury,
              (v) => _necessity = v,
            ),
          ],
        ),
        const SizedBox(height: 16),
        Text(l10n.checkAlternative, style: theme.textTheme.titleSmall),
        Wrap(
          spacing: 8,
          runSpacing: 4,
          children: [
            for (final (a, label) in [
              (BorrowAlternative.reserve, l10n.altReserve),
              (BorrowAlternative.relative, l10n.altRelative),
              (BorrowAlternative.sellItem, l10n.altSell),
              (BorrowAlternative.none, l10n.altNone),
            ])
              choice(
                'alt-${a.name}',
                a,
                _alternative,
                label,
                (v) => _alternative = v,
              ),
          ],
        ),
        const SizedBox(height: 24),
        FilledButton(
          key: const Key('check-next'),
          onPressed: _necessity != null && _alternative != null
              ? () => setState(() => _step = 1)
              : null,
          child: Text(l10n.withdrawContinue),
        ),
      ],
    );
  }

  Widget _form(BuildContext context) {
    final l10n = context.l10n;
    final theme = Theme.of(context);
    final money = context.money;
    final schedule = _schedule();
    final cost = schedule == null || _principal == null
        ? null
        : DebtCost.of(_principal!, schedule);
    final covers =
        schedule != null &&
        Money.sum(schedule.map((i) => i.principal), CurrencyCode.uzs) ==
            _principal;
    final overview = ref.watch(debtOverviewProvider).valueOrNull;
    final goals = overview?.goals ?? const <Goal>[];
    final income = overview?.monthlyIncome;
    final valid =
        _name.text.trim().isNotEmpty && schedule != null && covers && !_saving;
    return ListView(
      padding: const EdgeInsets.fromLTRB(16, 8, 16, 32),
      children: [
        Text(l10n.debtCreditorLabel, style: theme.textTheme.labelLarge),
        Wrap(
          spacing: 6,
          runSpacing: 4,
          children: [
            for (final t in CreditorType.values)
              ChoiceChip(
                key: Key('creditor-${t.name}'),
                label: Text(l10n.creditorType(t)),
                selected: t == _creditor,
                onSelected: (_) => setState(() {
                  _creditor = t;
                  if (t == CreditorType.bank &&
                      _type == DebtScheduleType.manual) {
                    _type = DebtScheduleType.annuity;
                  }
                }),
              ),
          ],
        ),
        TextField(
          key: const Key('debt-name'),
          controller: _name,
          decoration: InputDecoration(labelText: l10n.debtCreditorName),
          onChanged: (_) => setState(() {}),
        ),
        const SizedBox(height: 8),
        OutlinedButton(
          key: const Key('debt-principal'),
          onPressed: _pickPrincipal,
          child: Text(
            _principal == null ? l10n.debtAmountLabel : money(_principal!),
          ),
        ),
        TextField(
          key: const Key('debt-reason'),
          controller: _reason,
          decoration: InputDecoration(labelText: l10n.debtReasonLabel),
        ),
        const SizedBox(height: 12),
        Text(l10n.debtScheduleLabel, style: theme.textTheme.titleSmall),
        Wrap(
          spacing: 6,
          runSpacing: 4,
          children: [
            for (final t in DebtScheduleType.values)
              ChoiceChip(
                key: Key('schedule-${t.name}'),
                label: Text(l10n.scheduleType(t)),
                selected: t == _type,
                onSelected: (_) => setState(() => _type = t),
              ),
          ],
        ),
        if (_type != DebtScheduleType.manual)
          TextField(
            key: const Key('debt-term'),
            controller: _term,
            keyboardType: TextInputType.number,
            inputFormatters: [FilteringTextInputFormatter.digitsOnly],
            decoration: InputDecoration(labelText: l10n.debtTermLabel),
            onChanged: (_) => setState(() {}),
          ),
        if (_type == DebtScheduleType.annuity ||
            _type == DebtScheduleType.differentiated) ...[
          TextField(
            key: const Key('debt-rate'),
            controller: _rate,
            keyboardType: const TextInputType.numberWithOptions(decimal: true),
            inputFormatters: [
              FilteringTextInputFormatter.allow(RegExp('[0-9.,]')),
            ],
            decoration: InputDecoration(labelText: l10n.debtRateLabel),
            onChanged: (_) => setState(() {}),
          ),
          TextField(
            key: const Key('debt-early'),
            controller: _early,
            decoration: InputDecoration(labelText: l10n.debtEarlyTerms),
          ),
        ],
        if (_type == DebtScheduleType.fixedMarkup)
          OutlinedButton(
            key: const Key('debt-markup'),
            onPressed: () async {
              final m = await showAmountSheet(
                context,
                currency: CurrencyCode.uzs,
                title: l10n.debtMarkupLabel,
              );
              if (m != null) setState(() => _markup = m);
            },
            child: Text(
              _markup == null
                  ? l10n.debtMarkupLabel
                  : '${l10n.debtMarkupLabel}: ${money(_markup!)}',
            ),
          ),
        if (_type == DebtScheduleType.manual) ...[
          for (final (i, row) in _manual.indexed)
            ListTile(
              key: Key('manual-row-$i'),
              dense: true,
              contentPadding: EdgeInsets.zero,
              title: Text(formatDate(row.dueOn)),
              trailing: Row(
                mainAxisSize: MainAxisSize.min,
                children: [
                  Text(money(row.amount)),
                  IconButton(
                    tooltip: l10n.delete,
                    icon: const Icon(Icons.close),
                    onPressed: () => setState(() => _manual.removeAt(i)),
                  ),
                ],
              ),
            ),
          Align(
            alignment: Alignment.centerLeft,
            child: TextButton.icon(
              key: const Key('manual-add'),
              icon: const Icon(Icons.add),
              label: Text(l10n.manualRowAdd),
              onPressed: _addManualRow,
            ),
          ),
          if (schedule != null && !covers)
            Text(
              l10n.planMustCover(
                money(
                  Money.sum(schedule.map((i) => i.amount), CurrencyCode.uzs),
                ),
                money(_principal!),
              ),
              key: const Key('plan-mismatch'),
              style: TextStyle(color: theme.colorScheme.error),
            ),
        ],
        if (_isRiba)
          Card(
            key: const Key('riba-warning'),
            color: theme.colorScheme.errorContainer,
            child: Padding(
              padding: const EdgeInsets.all(12),
              child: Row(
                children: [
                  Icon(Icons.flag, color: theme.colorScheme.error),
                  const SizedBox(width: 8),
                  Expanded(
                    child: Text(
                      l10n.debtRibaWarning,
                      style: TextStyle(
                        color: theme.colorScheme.onErrorContainer,
                      ),
                    ),
                  ),
                ],
              ),
            ),
          ),
        if (cost != null && covers) ...[
          const SizedBox(height: 8),
          CostCard(cost: cost, goals: goals),
          if (income != null && overview != null)
            Padding(
              padding: const EdgeInsets.only(top: 8),
              child: Text(
                l10n.checkLoad(
                  percentLabel(
                    debtLoadBp(
                          overview.monthlyPayments + schedule.first.amount,
                          income,
                        ) ??
                        0,
                  ),
                ),
                key: const Key('debt-load-preview'),
              ),
            ),
        ],
        const SizedBox(height: 16),
        FilledButton(
          key: const Key('debt-save'),
          onPressed: valid ? _save : null,
          child: Text(l10n.debtSaveAction),
        ),
        if (schedule == null)
          Padding(
            padding: const EdgeInsets.only(top: 8),
            child: Text(
              l10n.scheduleRequired,
              style: theme.textTheme.bodySmall,
            ),
          ),
      ],
    );
  }
}

/// «Asosiy summa → Jami to'lanadi → Ortiqcha to'lov» va imkoniyat narxi.
class CostCard extends StatelessWidget {
  const CostCard({required this.cost, required this.goals, super.key});

  final DebtCost cost;
  final List<Goal> goals;

  @override
  Widget build(BuildContext context) {
    final l10n = context.l10n;
    final theme = Theme.of(context);
    final money = context.money;
    Widget row(String label, Money m, {Color? color}) => Row(
      children: [
        Expanded(child: Text(label)),
        Text(money(m), style: TextStyle(color: color)),
      ],
    );
    return Card(
      key: const Key('cost-card'),
      child: Padding(
        padding: const EdgeInsets.all(16),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text(l10n.costTitle, style: theme.textTheme.titleSmall),
            const SizedBox(height: 6),
            row(l10n.costPrincipal, cost.principal),
            row(l10n.costTotal, cost.totalPaid),
            row(
              l10n.costOver,
              cost.overpayment,
              color: cost.overpayment.isPositive
                  ? theme.colorScheme.error
                  : null,
            ),
            if (cost.overpayment.isPositive)
              for (final g in goals)
                Padding(
                  padding: const EdgeInsets.only(top: 4),
                  child: Text(
                    l10n.costOpportunity(
                      g.title,
                      percentLabel(
                        opportunityBp(cost.overpayment, g.target) ?? 0,
                      ),
                    ),
                    style: theme.textTheme.bodySmall,
                  ),
                ),
          ],
        ),
      ),
    );
  }
}
