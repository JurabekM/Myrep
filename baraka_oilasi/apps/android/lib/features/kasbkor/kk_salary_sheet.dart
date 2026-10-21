import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../app/i18n.dart';
import '../../core/core.dart';
import '../../shared/widgets.dart';
import 'kk_common.dart';

void openKkSalary(BuildContext context, String spaceId, KkOverviewDto overview) =>
    showSheet<void>(context, (_) => KkSalarySheet(spaceId: spaceId, overview: overview));

/// Egasi maoshini Uy makoniga o'tkazish (BARAKA_OILASI 4.6): bitta atomar yozuv — Kasb-kor'da chiqim
/// («maosh»), Uy'da daromad. Keyin Uy'dagi odatiy 1-qonun ulushi taklifi.
class KkSalarySheet extends ConsumerStatefulWidget {
  const KkSalarySheet({required this.spaceId, required this.overview, super.key});

  final String spaceId;
  final KkOverviewDto overview;

  @override
  ConsumerState<KkSalarySheet> createState() => _KkSalarySheetState();
}

class _KkSalarySheetState extends ConsumerState<KkSalarySheet> with ActionState {
  late final _amount = TextEditingController(text: widget.overview.salaryRemaining?.plain ?? '');
  String _wallet = 'CARD';
  KkSalaryPaidDto? _paid;

  @override
  void dispose() {
    _amount.dispose();
    super.dispose();
  }

  Future<void> _pay() async {
    final text = _amount.text.trim();
    final r = await act(
      () => ref
          .read(coreProvider)
          .kkPayOwnerSalary(
            spaceId: widget.spaceId,
            input: KkSalaryInput(amount: text.isEmpty ? null : text, wallet: _wallet),
          ),
    );
    if (r != null) setState(() => _paid = r);
  }

  /// Taklif qilingan ulush yadrodan `plain` ko'rinishida olinadi va o'zgarishsiz qaytariladi.
  Future<void> _allocate(KkSalaryPaidDto p) async {
    final r = await act(
      () => ref
          .read(coreProvider)
          .allocateToVault(
            spaceId: p.uySpaceId,
            incomeId: p.uyIncome.income.id,
            amount: p.uyIncome.suggestedShare.plain,
          ),
    );
    if (r != null && mounted) Navigator.of(context).pop();
  }

  @override
  Widget build(BuildContext context) {
    final paid = _paid;
    return SingleChildScrollView(
      padding: const EdgeInsets.fromLTRB(20, 0, 20, 20),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: [
          KkSheetTitle(context.t('kk.paySalary')),
          if (paid == null) ...[
            Hint(context.t('kk.paySalaryHint')),
            const SizedBox(height: 12),
            AmountField(label: context.t('common.amount'), controller: _amount, autofocus: true),
            const SizedBox(height: 12),
            KkWalletPicker(
              label: context.t('kk.fromWallet'),
              value: _wallet,
              onChanged: (w) => setState(() => _wallet = w),
            ),
            ErrorText(error),
            const SizedBox(height: 16),
            Row(
              mainAxisAlignment: MainAxisAlignment.end,
              children: [
                TextButton(onPressed: () => Navigator.of(context).pop(), child: Text(context.t('common.cancel'))),
                const SizedBox(width: 8),
                FilledButton(onPressed: busy ? null : _pay, child: Text(context.t('kk.transfer'))),
              ],
            ),
          ] else ...[
            Semantics(
              liveRegion: true,
              child: Text(context.t('kk.salaryPaid', {'amount': paid.uyIncome.income.amount.formatted})),
            ),
            const SizedBox(height: 12),
            Text(
              context.t('income.shareOffer', {'amount': paid.uyIncome.suggestedShare.formatted}),
              style: const TextStyle(fontSize: 18),
            ),
            ErrorText(error),
            const SizedBox(height: 16),
            Wrap(
              alignment: WrapAlignment.end,
              spacing: 8,
              children: [
                TextButton(onPressed: () => Navigator.of(context).pop(), child: Text(context.t('income.notNow'))),
                FilledButton(
                  onPressed: busy ? null : () => _allocate(paid),
                  child: Text(context.t('income.allocate')),
                ),
              ],
            ),
          ],
        ],
      ),
    );
  }
}
