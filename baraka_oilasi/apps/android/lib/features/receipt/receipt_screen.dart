import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../app/i18n.dart';
import '../../app/theme.dart';
import '../../core/core.dart';
import '../../shared/debt_widgets.dart';
import '../../shared/files.dart';
import '../../shared/widgets.dart';

/// Qarz tilxati (uy/SPEC 2D.5) = `Agreement(type = LOAN)`: foizsiz, to'lov rejasi majburiy, guvohlar
/// bilan. Saqlanganda kelishuv, jurnal va qarz yozuvi yaratiladi; PDF ulashish oynasi orqali
/// saqlanadi yoki yuboriladi. Tekshiruv va formatlash yadroda.
class ReceiptScreen extends ConsumerStatefulWidget {
  const ReceiptScreen({required this.spaceId, super.key});

  final String spaceId;

  @override
  ConsumerState<ReceiptScreen> createState() => _ReceiptScreenState();
}

class _ReceiptScreenState extends ConsumerState<ReceiptScreen> with ActionState {
  String _direction = 'BORROWED';
  String _creditorType = 'FRIEND';
  final _lender = TextEditingController();
  final _borrower = TextEditingController();
  final _amount = TextEditingController();
  final _place = TextEditingController();
  final _witnesses = TextEditingController();
  final _note = TextEditingController();
  final _schedule = [ScheduleRow()];
  BorrowCheckInput _check = const BorrowCheckInput(need: 'NECESSITY', alternatives: []);
  IssuedReceiptDto? _issued;

  @override
  void dispose() {
    for (final c in [_lender, _borrower, _amount, _place, _witnesses, _note, ..._schedule.map((r) => r.amount)]) {
      c.dispose();
    }
    super.dispose();
  }

  Future<void> _save() async {
    final borrowed = _direction == 'BORROWED';
    final core = ref.read(coreProvider);
    final r = await act(() async {
      final receipt = await core.issueLoanReceipt(
        spaceId: widget.spaceId,
        input: IssueLoanReceiptInput(
          direction: _direction,
          creditorType: borrowed ? _creditorType : null,
          receipt: LoanReceiptInput(
            lender: _lender.text,
            borrower: _borrower.text,
            amount: _amount.text,
            currency: 'UZS',
            place: _place.text,
            schedule: [for (final r in _schedule) r.toInput()],
            witnesses: _witnesses.text.split(','),
            note: _note.text.trim().isEmpty ? null : _note.text,
          ),
          isNew: borrowed,
          borrowCheck: borrowed ? _check : null,
        ),
      );
      // Tilxat saqlandi; ulashish bekor qilinsa ham keyin «Qarzlar» ekranidan olinadi.
      final pdf = await core.loanReceiptPdf(spaceId: widget.spaceId, agreementId: receipt.agreementId);
      await ref.read(shareFileProvider)(pdf, 'tilxat-${receipt.shortCode}.pdf', pdfMime);
      return receipt;
    });
    if (r != null) setState(() => _issued = r);
  }

  @override
  Widget build(BuildContext context) {
    final issued = _issued;
    if (issued != null) {
      return ScreenBody(
        children: [
          SectionCard(
            children: [
              Text(context.t('receipt.saved')),
              const SizedBox(height: 8),
              Hint(context.t('receipt.code')),
              SelectableText(
                issued.shortCode,
                key: const Key('receipt-code'),
                style: TextStyle(fontSize: 22, letterSpacing: 2, color: context.palette.accentText),
              ),
              const SizedBox(height: 8),
              Align(
                alignment: Alignment.centerLeft,
                child: OutlinedButton(
                  onPressed: () => setState(() => _issued = null),
                  child: Text(context.t('receipt.another')),
                ),
              ),
            ],
          ),
        ],
      );
    }
    final borrowed = _direction == 'BORROWED';
    return ScreenBody(
      mentorKey: 'mentor.receipt',
      children: [
        Hint(context.t('receipt.intro')),
        SectionCard(
          children: [
            Text(context.t('receipt.direction')),
            for (final d in ['BORROWED', 'LENT'])
              ChoiceTile(
                label: context.t('receipt.direction.$d'),
                selected: _direction == d,
                onTap: () => setState(() => _direction = d),
              ),
            const SizedBox(height: 8),
            Field(label: context.t('receipt.lender'), controller: _lender),
            const SizedBox(height: 12),
            Field(label: context.t('receipt.borrower'), controller: _borrower),
            const SizedBox(height: 12),
            AmountField(label: context.t('receipt.amount'), controller: _amount),
            const SizedBox(height: 12),
            Field(label: context.t('receipt.place'), controller: _place),
            const SizedBox(height: 12),
            ScheduleEditor(rows: _schedule, onChanged: () => setState(() {})),
            const SizedBox(height: 12),
            Field(label: context.t('receipt.witnesses'), controller: _witnesses),
            const SizedBox(height: 12),
            Field(label: context.t('common.note'), controller: _note),
            if (borrowed) ...[
              const SizedBox(height: 12),
              Select<String>(
                label: context.t('debts.creditorType'),
                items: [
                  for (final c in ['RELATIVE', 'FRIEND', 'OTHER']) (c, context.t('debts.creditor.$c')),
                ],
                value: _creditorType,
                onChanged: (v) => setState(() => _creditorType = v ?? _creditorType),
              ),
              const SizedBox(height: 12),
              BorrowCheckFields(value: _check, onChanged: (v) => setState(() => _check = v)),
            ],
            ErrorText(error),
            const SizedBox(height: 8),
            FilledButton(onPressed: busy ? null : _save, child: Text(context.t('receipt.save'))),
          ],
        ),
      ],
    );
  }
}
