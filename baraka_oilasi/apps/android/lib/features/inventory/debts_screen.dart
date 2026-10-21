import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../app/i18n.dart';
import '../../app/theme.dart';
import '../../core/core.dart';
import '../../core/query.dart';
import '../../shared/debt_widgets.dart';
import '../../shared/files.dart';
import '../../shared/format.dart';
import '../../shared/widgets.dart';

const creditorTypes = ['BANK', 'SHOP', 'RELATIVE', 'FRIEND', 'OTHER'];
const planKinds = ['MANUAL', 'ANNUITY', 'DIFFERENTIATED', 'FIXED_MARKUP'];

String? _opt(String v) => v.trim().isEmpty ? null : v;

/// Qarzlar ro'yxati — «yaraning hajmi» (uy/SPEC 2C.7, 2D.3, 2D.5, 2D.6). Barcha summalar,
/// foizlar, qoldiq va eslatmalar yadroda hisoblanadi; bu ekran faqat ko'rsatadi va so'raydi.
class DebtsScreen extends ConsumerStatefulWidget {
  const DebtsScreen({required this.spaceId, super.key});

  final String spaceId;

  @override
  ConsumerState<DebtsScreen> createState() => _DebtsScreenState();
}

class _DebtsScreenState extends ConsumerState<DebtsScreen> {
  String? _adding;

  @override
  Widget build(BuildContext context) {
    final id = widget.spaceId;
    final ov = ref.watch(query(['debts', id], (c) => c.debtsOverview(spaceId: id)));
    final o = ov.valueOrNull;
    final p = context.palette;
    return ScreenBody(
      mentorKey: 'mentor.inventory',
      children: [
        Wrap(
          spacing: 8,
          runSpacing: 8,
          children: [
            FilledButton(onPressed: () => setState(() => _adding = 'debt'), child: Text(context.t('debts.addDebt'))),
            OutlinedButton(
              onPressed: () => setState(() => _adding = 'receivable'),
              child: Text(context.t('debts.addReceivable')),
            ),
          ],
        ),
        if (ov.hasError) ErrorText(ov.error),
        if (o != null) ...[
          Kpi(
            label: context.t('debts.total'),
            value: o.totalDebt.isEmpty ? context.t('debts.none') : o.totalDebt.map((m) => m.formatted).join('\n'),
          ),
          Kpi(
            key: const Key('debts-load'),
            label: context.t('debts.load'),
            value: o.loadPercent == null ? context.t('debts.loadUnknown') : '${o.loadPercent}%',
            hint: [
              if (o.loadPercent != null)
                context.t('debts.loadOf', {'due': o.monthlyDue.formatted, 'income': o.monthlyIncome?.formatted ?? ''}),
              if (o.loadExcludesForeign) context.t('debts.loadForeign'),
            ].join('\n'),
            accent: o.loadHigh,
          ),
          Kpi(
            label: context.t('debts.receivableTotal'),
            value: o.totalReceivable.isEmpty
                ? context.t('debts.none')
                : o.totalReceivable.map((m) => m.formatted).join('\n'),
          ),
          if (o.hasRiboDebt)
            Container(
              padding: const EdgeInsets.all(12),
              decoration: BoxDecoration(
                border: Border.all(color: p.danger),
                borderRadius: BorderRadius.circular(10),
              ),
              child: Text(context.t('debts.riboBanner'), style: TextStyle(color: p.danger)),
            ),
        ],
        if (_adding == 'debt') _AddDebtForm(spaceId: id, onDone: () => setState(() => _adding = null)),
        if (_adding == 'receivable') _AddReceivableForm(spaceId: id, onDone: () => setState(() => _adding = null)),
        if (o != null) ...[
          _H2(context.t('debts.myDebts')),
          if (o.debts.isEmpty) Hint(context.t('debts.emptyDebts')),
          for (final d in o.debts) _DebtCard(spaceId: id, debt: d),
          _H2(context.t('debts.receivables')),
          if (o.receivables.isEmpty) Hint(context.t('debts.emptyReceivables')),
          for (final r in o.receivables) _ReceivableCard(spaceId: id, item: r),
          _Goals(spaceId: id, goals: o.goals),
        ],
      ],
    );
  }
}

class _H2 extends StatelessWidget {
  const _H2(this.text);

  final String text;

  @override
  Widget build(BuildContext context) => Semantics(
    header: true,
    child: Text(text, style: const TextStyle(fontSize: 18, fontWeight: FontWeight.w700)),
  );
}

class _StatusLine extends StatelessWidget {
  const _StatusLine(this.s, {this.gentle = false});

  final PlanStatusDto s;
  final bool gentle;

  @override
  Widget build(BuildContext context) {
    final p = context.palette;
    return Column(
      crossAxisAlignment: CrossAxisAlignment.stretch,
      children: [
        ValueRow(context.t('debts.remaining'), s.remaining.formatted, strong: true, valueColor: p.accentText),
        if (s.nextDue != null)
          ValueRow(context.t('debts.nextDue'), '${showDate(s.nextDue!.date)} — ${s.nextDue!.amount.formatted}'),
        if (s.reminder != null)
          Padding(
            padding: const EdgeInsets.only(top: 4),
            child: Text(
              context.t('debts.reminder.${gentle ? 'gentle.' : ''}${s.reminder}', {'amount': s.overdue.formatted}),
              style: TextStyle(color: s.reminder == 'OVERDUE' ? p.danger : p.warn),
            ),
          ),
      ],
    );
  }
}

class _PlanDetails extends StatelessWidget {
  const _PlanDetails({required this.plan, required this.payments});

  final List<PlanLineDto> plan;
  final List<RepaymentDto> payments;

  @override
  Widget build(BuildContext context) => ExpansionTile(
    tilePadding: EdgeInsets.zero,
    title: Hint(context.t('debts.planAndPayments', {'plan': plan.length, 'paid': payments.length})),
    children: [
      for (final l in plan) ValueRow(showDate(l.date), l.amount.formatted),
      if (payments.isNotEmpty) const Divider(),
      for (final pm in payments)
        ValueRow(
          '${showDate(pm.date)}${pm.isPrepayment ? ' · ${context.t('debts.prepayment')}' : ''}',
          '${pm.amount.formatted}${pm.journalShortCode == null ? '' : '  ${pm.journalShortCode}'}',
        ),
    ],
  );
}

Future<void> _receiptPdf(WidgetRef ref, String spaceId, String agreementId) async {
  final bytes = await ref.read(coreProvider).loanReceiptPdf(spaceId: spaceId, agreementId: agreementId);
  await ref.read(shareFileProvider)(bytes, 'tilxat.pdf', pdfMime);
}

class _DebtCard extends ConsumerStatefulWidget {
  const _DebtCard({required this.spaceId, required this.debt});

  final String spaceId;
  final DebtDto debt;

  @override
  ConsumerState<_DebtCard> createState() => _DebtCardState();
}

class _DebtCardState extends ConsumerState<_DebtCard> with ActionState {
  bool _paying = false;

  @override
  Widget build(BuildContext context) {
    final d = widget.debt;
    final tc = d.trueCost;
    final p = context.palette;
    return SectionCard(
      semanticLabel: d.creditor,
      title: d.creditor,
      children: [
        Wrap(
          spacing: 6,
          runSpacing: 6,
          children: [
            Tag(context.t('debts.creditor.${d.creditorType}')),
            if (d.isRibo) Tag(context.t('debts.ribo'), tone: 'danger'),
            if (d.status == 'CLOSED') Tag(context.t('debts.closed')),
            if (d.agreementId != null) Tag(context.t('debts.withReceipt')),
          ],
        ),
        if (d.reason != null) Padding(padding: const EdgeInsets.only(top: 6), child: Hint(d.reason!)),
        const SizedBox(height: 8),
        _StatusLine(d.statusInfo),
        const SizedBox(height: 8),
        Text.rich(
          TextSpan(
            children: [
              TextSpan(
                text: '${context.t('debts.trueCost')}: ',
                style: TextStyle(color: p.inkMuted),
              ),
              TextSpan(text: '${tc.originalPrincipal.formatted} → ${tc.totalCost.formatted} → '),
              TextSpan(
                text: context.t('debts.overpay', {'amount': tc.overpay.formatted, 'percent': tc.overpayPercent}),
                style: TextStyle(color: tc.overpay.minor == '0' ? null : p.danger),
              ),
            ],
          ),
        ),
        for (final g in tc.goalEquivalents)
          Text(
            context.t('debts.goalEquivalent', {'title': g.title, 'percent': g.percent}),
            style: TextStyle(color: p.accentText, fontSize: 14),
          ),
        if (d.borrowWarnings.isNotEmpty)
          Hint(
            '${context.t('debts.checkedWith')}: ${d.borrowWarnings.map((w) => context.t('friction.warn.$w')).join(' · ')}',
          ),
        _PlanDetails(plan: d.plan, payments: d.payments),
        Wrap(
          spacing: 8,
          children: [
            if (d.status == 'ACTIVE')
              OutlinedButton(
                onPressed: () => setState(() => _paying = !_paying),
                child: Text(context.t('debts.recordPayment')),
              ),
            if (d.agreementId != null)
              OutlinedButton(
                onPressed: busy ? null : () => act(() => _receiptPdf(ref, widget.spaceId, d.agreementId!)),
                child: Text(context.t('debts.receiptPdf')),
              ),
          ],
        ),
        ErrorText(error),
        if (_paying)
          _PaymentForm(
            spaceId: widget.spaceId,
            ownerType: 'DEBT',
            id: d.id,
            contributors: d.contributors,
            onDone: () => setState(() => _paying = false),
          ),
        if (d.status == 'ACTIVE') _Contributors(spaceId: widget.spaceId, debtId: d.id, items: d.contributors),
      ],
    );
  }
}

class _ReceivableCard extends ConsumerStatefulWidget {
  const _ReceivableCard({required this.spaceId, required this.item});

  final String spaceId;
  final ReceivableDto item;

  @override
  ConsumerState<_ReceivableCard> createState() => _ReceivableCardState();
}

class _ReceivableCardState extends ConsumerState<_ReceivableCard> with ActionState {
  bool _paying = false;

  @override
  Widget build(BuildContext context) {
    final r = widget.item;
    return SectionCard(
      semanticLabel: r.debtor,
      title: r.debtor,
      children: [
        Wrap(
          spacing: 6,
          children: [
            Tag(context.t('debts.hasana')),
            if (r.status == 'CLOSED') Tag(context.t('debts.closed')),
          ],
        ),
        const SizedBox(height: 6),
        Hint('${r.amount.formatted}, ${showDate(r.lentOn)}'),
        const SizedBox(height: 8),
        _StatusLine(r.statusInfo, gentle: true),
        _PlanDetails(plan: r.plan, payments: r.payments),
        Wrap(
          spacing: 8,
          children: [
            if (r.status == 'ACTIVE')
              OutlinedButton(
                onPressed: () => setState(() => _paying = !_paying),
                child: Text(context.t('debts.recordReturn')),
              ),
            if (r.agreementId != null)
              OutlinedButton(
                onPressed: busy ? null : () => act(() => _receiptPdf(ref, widget.spaceId, r.agreementId!)),
                child: Text(context.t('debts.receiptPdf')),
              ),
          ],
        ),
        ErrorText(error),
        if (_paying)
          _PaymentForm(
            spaceId: widget.spaceId,
            ownerType: 'RECEIVABLE',
            id: r.id,
            contributors: const [],
            onDone: () => setState(() => _paying = false),
          ),
      ],
    );
  }
}

class _PaymentForm extends ConsumerStatefulWidget {
  const _PaymentForm({
    required this.spaceId,
    required this.ownerType,
    required this.id,
    required this.contributors,
    required this.onDone,
  });

  final String spaceId;
  final String ownerType;
  final String id;
  final List<ContributorDto> contributors;
  final VoidCallback onDone;

  @override
  ConsumerState<_PaymentForm> createState() => _PaymentFormState();
}

class _PaymentFormState extends ConsumerState<_PaymentForm> with ActionState {
  final _amount = TextEditingController();
  String? _date;
  bool _prepayment = false;
  String? _payer;

  @override
  void dispose() {
    _amount.dispose();
    super.dispose();
  }

  Future<void> _save() async {
    final r = await act(
      () => ref
          .read(coreProvider)
          .recordRepayment(
            spaceId: widget.spaceId,
            ownerType: widget.ownerType,
            id: widget.id,
            input: RepaymentInput(amount: _amount.text, date: _date, isPrepayment: _prepayment, contributorId: _payer),
          ),
    );
    if (r == null || !mounted) return;
    widget.onDone();
    await celebrateIfClosed(context, widget.spaceId, r);
  }

  @override
  Widget build(BuildContext context) => Container(
    margin: const EdgeInsets.only(top: 8),
    padding: const EdgeInsets.all(12),
    decoration: BoxDecoration(
      border: Border.all(color: context.palette.line),
      borderRadius: BorderRadius.circular(10),
    ),
    child: Column(
      crossAxisAlignment: CrossAxisAlignment.stretch,
      children: [
        AmountField(label: context.t('common.amount'), controller: _amount),
        const SizedBox(height: 8),
        DateField(label: context.t('debts.paidOn'), value: _date, onChanged: (v) => setState(() => _date = v)),
        if (widget.contributors.isNotEmpty) ...[
          const SizedBox(height: 8),
          Select<String>(
            label: context.t('debts.payer'),
            items: [('', context.t('debts.payerSelf')), for (final c in widget.contributors) (c.id, c.name)],
            value: _payer ?? '',
            onChanged: (v) => setState(() => _payer = (v ?? '').isEmpty ? null : v),
          ),
        ],
        if (widget.ownerType == 'DEBT')
          CheckboxListTile(
            contentPadding: EdgeInsets.zero,
            value: _prepayment,
            title: Text(context.t('debts.prepayment')),
            onChanged: (v) => setState(() => _prepayment = v ?? false),
          ),
        ErrorText(error),
        FilledButton(onPressed: busy ? null : _save, child: Text(context.t('common.save'))),
      ],
    ),
  );
}

/// Qarzni to'lashga yelkadoshlar (uy/SPEC 2D.4): oylik ulush va to'lagani.
class _Contributors extends ConsumerStatefulWidget {
  const _Contributors({required this.spaceId, required this.debtId, required this.items});

  final String spaceId;
  final String debtId;
  final List<ContributorDto> items;

  @override
  ConsumerState<_Contributors> createState() => _ContributorsState();
}

class _ContributorsState extends ConsumerState<_Contributors> with ActionState {
  final _name = TextEditingController();
  final _share = TextEditingController();
  bool _open = false;

  @override
  void dispose() {
    _name.dispose();
    _share.dispose();
    super.dispose();
  }

  Future<void> _add() async {
    final r = await act(
      () => ref
          .read(coreProvider)
          .addContributor(
            spaceId: widget.spaceId,
            debtId: widget.debtId,
            input: NewContributorInput(name: _name.text, monthlyShare: _opt(_share.text)),
          ),
    );
    if (r != null) {
      _name.clear();
      _share.clear();
      setState(() => _open = false);
    }
  }

  @override
  Widget build(BuildContext context) => Column(
    crossAxisAlignment: CrossAxisAlignment.stretch,
    children: [
      for (final c in widget.items)
        ValueRow(
          '${c.name}${c.monthlyShare == null ? '' : ' · ${context.t('debts.share', {'amount': c.monthlyShare!.formatted})}'}',
          context.t('debts.contributorPaid', {'amount': c.paid.formatted}),
        ),
      if (!_open)
        Align(
          alignment: Alignment.centerLeft,
          child: TextButton(
            onPressed: () => setState(() => _open = true),
            child: Text(context.t('debts.addContributor')),
          ),
        )
      else ...[
        const SizedBox(height: 8),
        Field(label: context.t('debts.contributorName'), controller: _name),
        const SizedBox(height: 8),
        AmountField(label: context.t('debts.contributorShare'), controller: _share),
        ErrorText(error),
        Align(
          alignment: Alignment.centerLeft,
          child: OutlinedButton(onPressed: busy ? null : _add, child: Text(context.t('goals.add'))),
        ),
      ],
    ],
  );
}

class _AddDebtForm extends ConsumerStatefulWidget {
  const _AddDebtForm({required this.spaceId, required this.onDone});

  final String spaceId;
  final VoidCallback onDone;

  @override
  ConsumerState<_AddDebtForm> createState() => _AddDebtFormState();
}

class _AddDebtFormState extends ConsumerState<_AddDebtForm> with ActionState {
  String _creditorType = 'RELATIVE';
  String _planKind = 'MANUAL';
  String? _firstDate;
  bool _isNew = false;
  final _creditor = TextEditingController();
  final _reason = TextEditingController();
  final _principal = TextEditingController();
  final _annualBp = TextEditingController(text: '2400');
  final _months = TextEditingController(text: '12');
  final _markup = TextEditingController();
  final _original = TextEditingController();
  final _paidBefore = TextEditingController();
  final _terms = TextEditingController();
  final _feeBp = TextEditingController();
  final _schedule = [ScheduleRow()];
  BorrowCheckInput _check = const BorrowCheckInput(need: 'NECESSITY', alternatives: []);
  BorrowCheckDto? _preview;

  List<TextEditingController> get _controllers => [
    _creditor,
    _reason,
    _principal,
    _annualBp,
    _months,
    _markup,
    _original,
    _paidBefore,
    _terms,
    _feeBp,
  ];

  @override
  void initState() {
    super.initState();
    // Har qanday o'zgarishdan keyin «to'xta va o'yla» natijasi qayta so'raladi.
    for (final c in _controllers) {
      c.addListener(_reset);
    }
  }

  void _reset() {
    if (_preview != null) setState(() => _preview = null);
  }

  @override
  void dispose() {
    for (final c in [..._controllers, ..._schedule.map((r) => r.amount)]) {
      c.dispose();
    }
    super.dispose();
  }

  bool get _bank => _planKind == 'ANNUITY' || _planKind == 'DIFFERENTIATED';
  bool get _generated => _planKind != 'MANUAL';

  /// bp va oylar — pul emas, butun son; noto'g'ri qiymat yadroga yuborilmaydi.
  NewDebtInput _input() {
    final digits = RegExp(r'^\d+$');
    if ((_generated && (!digits.hasMatch(_months.text) || (_bank && !digits.hasMatch(_annualBp.text)))) ||
        (_feeBp.text.trim().isNotEmpty && !digits.hasMatch(_feeBp.text.trim()))) {
      throw const AppError(code: 'INVALID_NUMBER');
    }
    return NewDebtInput(
      creditorType: _creditorType,
      creditor: _creditor.text,
      reason: _opt(_reason.text),
      currency: 'UZS',
      principal: _principal.text,
      originalPrincipal: _opt(_original.text),
      paidBefore: _opt(_paidBefore.text),
      planKind: _planKind,
      annualBp: _bank ? int.parse(_annualBp.text) : null,
      markup: _bank ? null : _opt(_markup.text),
      months: _generated ? int.parse(_months.text) : null,
      firstDate: _firstDate,
      schedule: _generated ? [] : [for (final r in _schedule) r.toInput()],
      earlyRepaymentTerms: _opt(_terms.text),
      prepaymentFeeBp: _feeBp.text.trim().isEmpty ? null : int.parse(_feeBp.text.trim()),
      isNew: _isNew,
      borrowCheck: _isNew ? _check : null,
    );
  }

  Future<void> _run() async {
    final core = ref.read(coreProvider);
    await act(() async {
      final i = _input();
      if (i.isNew && _preview == null) {
        final pv = await core.previewBorrowCheck(spaceId: widget.spaceId, input: i);
        setState(() => _preview = pv);
        return;
      }
      await core.addDebt(spaceId: widget.spaceId, input: i);
      widget.onDone();
    });
  }

  @override
  Widget build(BuildContext context) {
    final p = context.palette;
    return SectionCard(
      title: context.t('debts.addDebt'),
      children: [
        Select<String>(
          label: context.t('debts.creditorType'),
          items: [for (final c in creditorTypes) (c, context.t('debts.creditor.$c'))],
          value: _creditorType,
          onChanged: (v) => setState(() {
            _creditorType = v ?? _creditorType;
            _preview = null;
          }),
        ),
        const SizedBox(height: 12),
        Field(label: context.t('debts.creditorName'), controller: _creditor),
        const SizedBox(height: 12),
        AmountField(label: context.t('debts.principal'), controller: _principal),
        const SizedBox(height: 12),
        Field(label: context.t('debts.reason'), hint: context.t('debts.reasonHint'), controller: _reason),
        const SizedBox(height: 12),
        Select<String>(
          label: context.t('debts.planKind'),
          items: [for (final k in planKinds) (k, context.t('debts.plan.$k'))],
          value: _planKind,
          onChanged: (v) => setState(() {
            _planKind = v ?? _planKind;
            _preview = null;
          }),
        ),
        const SizedBox(height: 12),
        DateField(
          label: _generated ? context.t('debts.firstPayment') : context.t('debts.startedOn'),
          value: _firstDate,
          onChanged: (v) => setState(() {
            _firstDate = v;
            _preview = null;
          }),
        ),
        const SizedBox(height: 12),
        if (_bank)
          Field(label: context.t('loan.rateBp'), controller: _annualBp, keyboardType: TextInputType.number)
        else
          AmountField(label: context.t('debts.markup'), controller: _markup),
        if (_generated) ...[
          const SizedBox(height: 12),
          Field(label: context.t('loan.months'), controller: _months, keyboardType: TextInputType.number),
        ],
        if (_bank || _markup.text.trim().isNotEmpty)
          Padding(
            padding: const EdgeInsets.only(top: 8),
            child: Text(context.t('debts.riboHint'), style: TextStyle(color: p.danger, fontSize: 14)),
          ),
        if (!_generated) ...[
          const SizedBox(height: 12),
          ScheduleEditor(
            rows: _schedule,
            onChanged: () => setState(() => _preview = null),
          ),
        ],
        ExpansionTile(
          tilePadding: EdgeInsets.zero,
          title: Hint(context.t('debts.history')),
          children: [
            AmountField(label: context.t('debts.original'), controller: _original),
            const SizedBox(height: 8),
            AmountField(label: context.t('debts.paidBefore'), controller: _paidBefore),
            if (_creditorType == 'BANK') ...[
              const SizedBox(height: 8),
              Field(label: context.t('debts.terms'), controller: _terms),
              const SizedBox(height: 8),
              Field(label: context.t('debts.feeBp'), controller: _feeBp, keyboardType: TextInputType.number),
            ],
            const SizedBox(height: 8),
          ],
        ),
        CheckboxListTile(
          contentPadding: EdgeInsets.zero,
          value: _isNew,
          title: Text(context.t('debts.isNew')),
          onChanged: (v) => setState(() {
            _isNew = v ?? false;
            _preview = null;
          }),
        ),
        if (_isNew)
          BorrowCheckFields(
            value: _check,
            onChanged: (v) => setState(() {
              _check = v;
              _preview = null;
            }),
          ),
        if (_preview != null) ...[const SizedBox(height: 8), FrictionResult(_preview!)],
        ErrorText(error),
        const SizedBox(height: 8),
        Wrap(
          spacing: 8,
          children: [
            FilledButton(
              onPressed: busy ? null : _run,
              child: Text(
                _isNew && _preview == null
                    ? context.t('friction.check')
                    : _preview != null
                    ? context.t('friction.confirm')
                    : context.t('common.save'),
              ),
            ),
            TextButton(onPressed: widget.onDone, child: Text(context.t('common.cancel'))),
          ],
        ),
      ],
    );
  }
}

class _AddReceivableForm extends ConsumerStatefulWidget {
  const _AddReceivableForm({required this.spaceId, required this.onDone});

  final String spaceId;
  final VoidCallback onDone;

  @override
  ConsumerState<_AddReceivableForm> createState() => _AddReceivableFormState();
}

class _AddReceivableFormState extends ConsumerState<_AddReceivableForm> with ActionState {
  final _debtor = TextEditingController();
  final _amount = TextEditingController();
  final _note = TextEditingController();
  String? _lentOn;
  final _schedule = [ScheduleRow()];

  @override
  void dispose() {
    for (final c in [_debtor, _amount, _note, ..._schedule.map((r) => r.amount)]) {
      c.dispose();
    }
    super.dispose();
  }

  Future<void> _save() async {
    final r = await act(
      () => ref
          .read(coreProvider)
          .addReceivable(
            spaceId: widget.spaceId,
            input: NewReceivableInput(
              debtor: _debtor.text,
              currency: 'UZS',
              amount: _amount.text,
              lentOn: _lentOn,
              schedule: [for (final r in _schedule) r.toInput()],
              note: _opt(_note.text),
            ),
          ),
    );
    if (r != null) widget.onDone();
  }

  @override
  Widget build(BuildContext context) => SectionCard(
    title: context.t('debts.addReceivable'),
    children: [
      Hint(context.t('debts.receivableIntro')),
      const SizedBox(height: 12),
      Field(label: context.t('debts.debtor'), controller: _debtor),
      const SizedBox(height: 12),
      AmountField(label: context.t('common.amount'), controller: _amount),
      const SizedBox(height: 12),
      DateField(label: context.t('debts.lentOn'), value: _lentOn, onChanged: (v) => setState(() => _lentOn = v)),
      const SizedBox(height: 12),
      Field(label: context.t('common.note'), controller: _note),
      const SizedBox(height: 12),
      ScheduleEditor(rows: _schedule, onChanged: () => setState(() {})),
      ErrorText(error),
      const SizedBox(height: 8),
      Wrap(
        spacing: 8,
        children: [
          FilledButton(onPressed: busy ? null : _save, child: Text(context.t('common.save'))),
          TextButton(onPressed: widget.onDone, child: Text(context.t('common.cancel'))),
        ],
      ),
    ],
  );
}

class _Goals extends ConsumerStatefulWidget {
  const _Goals({required this.spaceId, required this.goals});

  final String spaceId;
  final List<GoalDto> goals;

  @override
  ConsumerState<_Goals> createState() => _GoalsState();
}

class _GoalsState extends ConsumerState<_Goals> with ActionState {
  final _title = TextEditingController();
  final _target = TextEditingController();

  @override
  void dispose() {
    _title.dispose();
    _target.dispose();
    super.dispose();
  }

  Future<void> _add() async {
    final r = await act(
      () => ref
          .read(coreProvider)
          .addGoal(
            spaceId: widget.spaceId,
            input: NewGoalInput(title: _title.text, target: _target.text, currency: 'UZS'),
          ),
    );
    if (r != null) {
      _title.clear();
      _target.clear();
    }
  }

  @override
  Widget build(BuildContext context) => SectionCard(
    title: context.t('goals.title'),
    children: [
      Hint(context.t('goals.intro')),
      for (final g in widget.goals)
        Row(
          children: [
            Expanded(child: ValueRow(g.title, g.target.formatted)),
            IconButton(
              tooltip: context.t('receipt.removeLine'),
              icon: const Icon(Icons.delete_outline),
              onPressed: () => act(() => ref.read(coreProvider).deleteGoal(spaceId: widget.spaceId, goalId: g.id)),
            ),
          ],
        ),
      const SizedBox(height: 8),
      Field(label: context.t('goals.name'), controller: _title),
      const SizedBox(height: 8),
      AmountField(label: context.t('goals.target'), controller: _target),
      ErrorText(error),
      Align(
        alignment: Alignment.centerLeft,
        child: OutlinedButton(onPressed: busy ? null : _add, child: Text(context.t('goals.add'))),
      ),
    ],
  );
}
