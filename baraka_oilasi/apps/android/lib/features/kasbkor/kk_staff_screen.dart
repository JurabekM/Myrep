import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../app/i18n.dart';
import '../../app/theme.dart';
import '../../core/core.dart';
import '../../core/query.dart';
import '../../shared/files.dart';
import '../../shared/format.dart';
import '../../shared/widgets.dart';
import 'kk_agreement_parts.dart';

/// Xodimlar (kasbkor/SPEC 7.2): `EMPLOYMENT` kelishuvi (9 savol), imzolangan versiyalar, foizsiz va
/// jarimasiz avans, haq to'lovi, oylik hisob varaqchasi. Hisob yadroda; UI faqat ko'rsatadi.
class KkStaffScreen extends ConsumerStatefulWidget {
  const KkStaffScreen({required this.spaceId, super.key});

  final String spaceId;

  @override
  ConsumerState<KkStaffScreen> createState() => _KkStaffScreenState();
}

class _KkStaffScreenState extends ConsumerState<KkStaffScreen> {
  bool _adding = false;
  (String, String)? _open;

  @override
  Widget build(BuildContext context) {
    final sid = widget.spaceId;
    final q = ref.watch(query(['kkStaff', sid], (c) => c.kkStaff(spaceId: sid)));
    final s = q.valueOrNull;
    return ScreenBody(
      mentorKey: 'mentor.kkStaff',
      children: [
        Hint(context.t('kk.staff.intro')),
        TemplateReviewNote(s?.templateReview),
        if (q.hasError) ErrorText(q.error),
        if (s != null)
          Semantics(
            container: true,
            label: context.t('kk.staff.totals'),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.stretch,
              children: [
                Kpi(
                  key: const Key('kk-staff-owed'),
                  label: context.t('kk.staff.owed'),
                  value: s.owed.formatted,
                  hint: context.t('kk.staff.owedHint'),
                  accent: true,
                ),
                Kpi(
                  key: const Key('kk-staff-advances'),
                  label: context.t('kk.staff.advances'),
                  value: s.advancesOutstanding.formatted,
                  hint: context.t('kk.staff.advancesHint'),
                ),
              ],
            ),
          ),
        Align(
          alignment: Alignment.centerLeft,
          child: KkActionButton(
            label: context.t('kk.staff.add'),
            active: !_adding,
            onPressed: () => setState(() => _adding = !_adding),
          ),
        ),
        if (_adding) _EmployeeForm(spaceId: sid, onDone: () => setState(() => _adding = false)),
        Semantics(
          header: true,
          child: Text(context.t('kk.staff.list'), style: const TextStyle(fontSize: 18, fontWeight: FontWeight.w700)),
        ),
        if (s != null && s.employees.isEmpty) Hint(context.t('kk.staff.empty')),
        for (final e in s?.employees ?? const <KkEmployeeDto>[])
          _EmployeeCard(
            key: ValueKey(e.id),
            spaceId: sid,
            e: e,
            open: _open?.$1 == e.id ? _open!.$2 : null,
            onToggle: (m) => setState(() => _open = _open == (e.id, m) ? null : (e.id, m)),
            onDone: () => setState(() => _open = null),
          ),
      ],
    );
  }
}

class _EmployeeCard extends ConsumerStatefulWidget {
  const _EmployeeCard({
    required this.spaceId,
    required this.e,
    required this.open,
    required this.onToggle,
    required this.onDone,
    super.key,
  });

  final String spaceId;
  final KkEmployeeDto e;
  final String? open;
  final ValueChanged<String> onToggle;
  final VoidCallback onDone;

  @override
  ConsumerState<_EmployeeCard> createState() => _EmployeeCardState();
}

class _EmployeeCardState extends ConsumerState<_EmployeeCard> with ActionState {
  /// Hisob varaqchasi PDF (oy boshi sanasi bilan).
  Future<void> _slip(String month) => act(() async {
    final bytes = await ref.read(coreProvider).kkPayslipPdf(spaceId: widget.spaceId, id: widget.e.id, month: month);
    await ref.read(shareFileProvider)(bytes, 'varaqcha-$month.pdf', pdfMime);
  });

  @override
  Widget build(BuildContext context) {
    final e = widget.e;
    final sid = widget.spaceId;
    final open = widget.open;
    final a = e.agreement;
    final active = a.status != 'ENDED';
    final signed = a.signedVersions > 0;
    final pal = context.palette;
    Widget action(String m, String label) =>
        KkActionButton(label: label, active: open == m, onPressed: () => widget.onToggle(m));
    return Semantics(
      container: true,
      label: e.name,
      child: Card(
        key: Key('kk-employee-${e.name}'),
        child: Padding(
          padding: const EdgeInsets.all(16),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.stretch,
            children: [
              Text.rich(
                TextSpan(
                  children: [
                    TextSpan(
                      text: e.name,
                      style: const TextStyle(fontSize: 18, fontWeight: FontWeight.w700),
                    ),
                    if (e.terms.role != null)
                      TextSpan(
                        text: '  ${e.terms.role}',
                        style: TextStyle(color: pal.inkMuted, fontSize: 14),
                      ),
                  ],
                ),
              ),
              AgreementStatus(a, testKey: 'kk-employee-status'),
              const SizedBox(height: 4),
              ValueRow(context.t('kk.staff.salary'), e.terms.salary.formatted),
              ValueRow(context.t('kk.staff.payDayRow'), context.t('kk.staff.payDayValue', {'day': e.terms.payDay})),
              ValueRow(context.t('kk.staff.dueNow'), e.dueNow.formatted, key: const Key('kk-employee-due')),
              ValueRow(context.t('kk.staff.balance'), e.balance.formatted),
              ValueRow(context.t('kk.staff.advances'), e.advancesOutstanding.formatted),
              const SizedBox(height: 8),
              Semantics(
                container: true,
                label: context.t('kk.agr.actions', {'name': e.name}),
                child: Wrap(
                  spacing: 8,
                  runSpacing: 8,
                  children: [
                    if (a.canSign) action('SIGN', context.t('kk.agr.sign')),
                    if (signed && active) action('ADVANCE', context.t('kk.staff.advance')),
                    if (signed) action('PAY', context.t('kk.staff.pay')),
                    if (active) action('EDIT', context.t('kk.agr.edit')),
                    if (signed && active) action('END', context.t('kk.staff.end')),
                  ],
                ),
              ),
              const SizedBox(height: 8),
              AgreementFileActions(spaceId: sid, id: e.id, name: e.name, state: a),
              if (open == 'SIGN') SignForm(spaceId: sid, id: e.id, name: e.name, state: a, onDone: widget.onDone),
              if (open == 'ADVANCE') _AdvanceForm(spaceId: sid, e: e, onDone: widget.onDone),
              if (open == 'PAY') _PayForm(spaceId: sid, e: e, onDone: widget.onDone),
              if (open == 'EDIT') _EmployeeForm(spaceId: sid, e: e, onDone: widget.onDone),
              if (open == 'END') EndForm(spaceId: sid, id: e.id, name: e.name, onDone: widget.onDone),
              if (e.months.isNotEmpty && signed)
                KkDetails(
                  summary: context.t('kk.staff.months'),
                  children: [
                    for (final m in e.months)
                      Container(
                        padding: const EdgeInsets.symmetric(vertical: 6),
                        decoration: BoxDecoration(
                          border: Border(top: BorderSide(color: pal.line)),
                        ),
                        child: Column(
                          crossAxisAlignment: CrossAxisAlignment.stretch,
                          children: [
                            Text(
                              '${showDate(m.periodStart)} — ${showDate(m.periodEnd)}',
                              style: const TextStyle(fontWeight: FontWeight.w600),
                            ),
                            ValueRow(context.t('kk.staff.salary'), m.salary.formatted),
                            ValueRow(context.t('kk.staff.col.deducted'), m.deducted.formatted),
                            ValueRow(context.t('kk.staff.col.paid'), m.paid.formatted),
                            ValueRow(context.t('kk.staff.col.balance'), m.balance.formatted),
                            Align(
                              alignment: Alignment.centerLeft,
                              child: Semantics(
                                label: context.t('kk.staff.slipNamed', {'period': showDate(m.periodStart)}),
                                child: TextButton(
                                  onPressed: busy ? null : () => _slip(m.periodStart),
                                  child: Text(context.t('kk.staff.slip')),
                                ),
                              ),
                            ),
                          ],
                        ),
                      ),
                    ErrorText(error),
                  ],
                ),
              if (e.advances.isNotEmpty)
                KkDetails(
                  summary: context.t('kk.staff.advanceList', {'count': e.advances.length}),
                  children: [
                    for (final x in e.advances)
                      Padding(
                        padding: const EdgeInsets.only(bottom: 4),
                        child: Text(
                          context.t('kk.staff.advanceLine', {
                            'date': showDate(x.givenOn),
                            'amount': x.amount.formatted,
                            'n': x.installments,
                            'outstanding': x.outstanding.formatted,
                          }),
                        ),
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

/// Hamyon tanlovi: naqd kassa yoki karta.
Widget _walletPicker(BuildContext context, String value, ValueChanged<String> onChanged) => KkToggleRow<String>(
  label: context.t('kk.staff.fromWallet'),
  options: [
    for (final w in ['CASH', 'CARD']) (w, context.t('kk.wallet.$w')),
  ],
  value: value,
  onChanged: onChanged,
);

class _AdvanceForm extends ConsumerStatefulWidget {
  const _AdvanceForm({required this.spaceId, required this.e, required this.onDone});

  final String spaceId;
  final KkEmployeeDto e;
  final VoidCallback onDone;

  @override
  ConsumerState<_AdvanceForm> createState() => _AdvanceFormState();
}

class _AdvanceFormState extends ConsumerState<_AdvanceForm> with ActionState {
  final _amount = TextEditingController();
  int _n = 1;
  String? _startOn;
  String _wallet = 'CASH';
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
          .kkStaffAdvance(
            spaceId: widget.spaceId,
            id: widget.e.id,
            input: KkAdvanceInput(
              amount: _amount.text,
              installments: _n,
              startOn: _startOn,
              wallet: _wallet,
              occurredOn: _on,
            ),
          ),
    );
    if (r != null) widget.onDone();
  }

  @override
  Widget build(BuildContext context) {
    final t = widget.e.terms;
    final max = t.maxAdvanceInstallments;
    return Semantics(
      container: true,
      label: context.t('kk.staff.advanceTitle', {'name': widget.e.name}),
      child: KkBox(
        children: [
          Hint(
            t.maxAdvance != null
                ? context.t('kk.staff.advanceRule', {'max': t.maxAdvance!.formatted, 'n': max})
                : context.t('kk.staff.advanceRuleNoLimit', {'n': max}),
          ),
          const SizedBox(height: 12),
          AmountField(label: context.t('kk.staff.amount'), controller: _amount),
          const SizedBox(height: 12),
          Select<int>(
            label: context.t('kk.staff.installments'),
            items: [
              for (var i = 1; i <= max; i++) (i, context.t('kk.staff.installmentsValue', {'n': i})),
            ],
            value: _n,
            onChanged: (v) => setState(() => _n = v ?? _n),
          ),
          const SizedBox(height: 12),
          DateField(
            label: context.t('kk.staff.startOn'),
            value: _startOn,
            onChanged: (v) => setState(() => _startOn = v),
          ),
          const SizedBox(height: 12),
          DateField(label: context.t('kk.date'), value: _on, onChanged: (v) => setState(() => _on = v)),
          const SizedBox(height: 12),
          _walletPicker(context, _wallet, (w) => setState(() => _wallet = w)),
          ErrorText(error),
          const SizedBox(height: 8),
          Align(
            alignment: Alignment.centerLeft,
            child: FilledButton(onPressed: busy ? null : _save, child: Text(context.t('kk.staff.advanceSave'))),
          ),
        ],
      ),
    );
  }
}

class _PayForm extends ConsumerStatefulWidget {
  const _PayForm({required this.spaceId, required this.e, required this.onDone});

  final String spaceId;
  final KkEmployeeDto e;
  final VoidCallback onDone;

  @override
  ConsumerState<_PayForm> createState() => _PayFormState();
}

class _PayFormState extends ConsumerState<_PayForm> with ActionState {
  late final _amount = TextEditingController(text: widget.e.dueNow.minor == '0' ? '' : widget.e.dueNow.plain);
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
          .kkStaffPay(
            spaceId: widget.spaceId,
            id: widget.e.id,
            input: KkWageInput(amount: kkOpt(_amount.text), wallet: _wallet, occurredOn: _on),
          ),
    );
    if (r != null) widget.onDone();
  }

  @override
  Widget build(BuildContext context) => Semantics(
    container: true,
    label: context.t('kk.staff.payTitle', {'name': widget.e.name}),
    child: KkBox(
      children: [
        AmountField(label: context.t('kk.staff.amount'), controller: _amount),
        const SizedBox(height: 12),
        _walletPicker(context, _wallet, (w) => setState(() => _wallet = w)),
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

class _EmployeeForm extends ConsumerStatefulWidget {
  const _EmployeeForm({required this.spaceId, required this.onDone, this.e});

  final String spaceId;
  final KkEmployeeDto? e;
  final VoidCallback onDone;

  @override
  ConsumerState<_EmployeeForm> createState() => _EmployeeFormState();
}

class _EmployeeFormState extends ConsumerState<_EmployeeForm> with ActionState {
  late final KkEmployeeDto? e = widget.e;
  late final _name = TextEditingController(text: e?.name ?? '');
  late final _role = TextEditingController(text: e?.terms.role ?? '');
  late final _phone = TextEditingController(text: e?.phone ?? '');
  late bool _consent = e?.phone != null;
  late final _duties = TextEditingController(text: e?.terms.duties ?? '');
  late final _hours = TextEditingController(text: e?.terms.hours ?? '');
  late final _salary = TextEditingController(text: e?.terms.salary.plain ?? '');
  late final _payDay = TextEditingController(text: '${e?.terms.payDay ?? 5}');
  late final _notice = TextEditingController(text: '${e?.terms.noticeDays ?? 14}');
  late final _maxAdvance = TextEditingController(text: e?.terms.maxAdvance?.plain ?? '');
  late final _maxN = TextEditingController(text: '${e?.terms.maxAdvanceInstallments ?? 3}');
  late String? _startedOn = e?.agreement.startedOn;
  late final _opening = TextEditingController(
    text: e != null && e!.terms.openingBalance.minor != '0' ? e!.terms.openingBalance.plain : '',
  );
  late final _arbiter = TextEditingController(text: e?.terms.arbiter ?? '');
  late String? _reviewOn = e?.agreement.reviewOn;

  @override
  void dispose() {
    for (final c in [
      _name,
      _role,
      _phone,
      _duties,
      _hours,
      _salary,
      _payDay,
      _notice,
      _maxAdvance,
      _maxN,
      _opening,
      _arbiter,
    ]) {
      c.dispose();
    }
    super.dispose();
  }

  Future<void> _save() async {
    final core = ref.read(coreProvider);
    final input = KkEmployeeInput(
      name: _name.text,
      role: kkOpt(_role.text),
      phone: kkOpt(_phone.text),
      phoneConsent: _consent,
      duties: kkOpt(_duties.text),
      hours: kkOpt(_hours.text),
      salary: _salary.text,
      payDay: int.tryParse(_payDay.text.trim()) ?? 0,
      noticeDays: int.tryParse(_notice.text.trim()) ?? 0,
      maxAdvance: kkOpt(_maxAdvance.text),
      maxAdvanceInstallments: int.tryParse(_maxN.text.trim()),
      startedOn: _startedOn,
      openingBalance: kkOpt(_opening.text),
      arbiter: kkOpt(_arbiter.text),
      reviewOn: _reviewOn,
      note: e?.terms.note,
    );
    final r = await act(
      () => e == null
          ? core.kkAddEmployee(spaceId: widget.spaceId, input: input)
          : core.kkUpdateEmployee(spaceId: widget.spaceId, id: e!.id, input: input),
    );
    if (r != null) widget.onDone();
  }

  @override
  Widget build(BuildContext context) {
    const gap = SizedBox(height: 12);
    final startLocked = e != null && e!.agreement.signedVersions > 0;
    return Semantics(
      container: true,
      label: e == null ? context.t('kk.staff.add') : context.t('kk.agr.editTitle', {'name': e!.name}),
      child: KkBox(
        children: [
          Hint(context.t('kk.staff.formHint')),
          gap,
          Field(label: context.t('kk.staff.name'), controller: _name),
          gap,
          Field(label: context.t('kk.staff.role'), controller: _role),
          gap,
          PhoneFields(phone: _phone, consent: _consent, onConsent: (v) => setState(() => _consent = v)),
          Field(label: context.t('kk.staff.duties'), controller: _duties, maxLines: 3),
          gap,
          Field(label: context.t('kk.staff.hours'), controller: _hours),
          gap,
          AmountField(label: context.t('kk.staff.salary'), controller: _salary),
          gap,
          Field(label: context.t('kk.staff.payDay'), controller: _payDay, keyboardType: TextInputType.number),
          gap,
          AmountField(label: context.t('kk.staff.maxAdvance'), controller: _maxAdvance),
          gap,
          Field(label: context.t('kk.staff.maxInstallments'), controller: _maxN, keyboardType: TextInputType.number),
          gap,
          Field(label: context.t('kk.staff.noticeDays'), controller: _notice, keyboardType: TextInputType.number),
          gap,
          if (startLocked)
            ValueRow(context.t('kk.staff.startedOn'), showDate(_startedOn ?? ''))
          else
            DateField(
              label: context.t('kk.staff.startedOn'),
              value: _startedOn,
              onChanged: (v) => setState(() => _startedOn = v),
            ),
          gap,
          AmountField(label: context.t('kk.staff.opening'), controller: _opening),
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
              child: Text(e == null ? context.t('kk.staff.addButton') : context.t('common.save')),
            ),
          ),
        ],
      ),
    );
  }
}
