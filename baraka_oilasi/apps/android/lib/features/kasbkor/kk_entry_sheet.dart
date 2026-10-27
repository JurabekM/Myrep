import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../app/i18n.dart';
import '../../core/core.dart';
import '../../core/query.dart';
import '../../shared/widgets.dart';
import 'kk_common.dart';

/// Bosh sahifadagi amallar: tushum, chiqim, «egasi oldi», kapital kiritish, o'tkazma, boshlang'ich
/// qoldiq.
const kkEntryModes = ['SALE', 'EXPENSE', 'OWNER_DRAW', 'OWNER_CONTRIBUTION', 'TRANSFER', 'OPENING'];

void openKkEntry(BuildContext context, String spaceId, String kind) =>
    showSheet<void>(context, (_) => KkEntrySheet(spaceId: spaceId, mode: kind));

/// Kasb-kor yozuvi (kasbkor/SPEC 2): tushum, chiqim, «egasi oldi», kapital kiritish, hamyonlar
/// orasida o'tkazma yoki boshlang'ich qoldiq. Summa matn ko'rinishida yadroga beriladi.
class KkEntrySheet extends ConsumerStatefulWidget {
  const KkEntrySheet({required this.spaceId, required this.mode, super.key});

  final String spaceId;
  final String mode;

  @override
  ConsumerState<KkEntrySheet> createState() => _KkEntrySheetState();
}

class _KkEntrySheetState extends ConsumerState<KkEntrySheet> with ActionState {
  final _amount = TextEditingController();
  final _note = TextEditingController();
  late String _wallet = widget.mode == 'TRANSFER' ? 'CARD' : 'CASH';
  String _toWallet = 'CASH';
  String? _categoryId;
  String? _date;

  /// «Sarmoya (o'qish)» (K9, kasbkor/SPEC 8A.3): chiqim haqiqiy foydaga kiradi, «Hisob kuni»da alohida qator.
  bool _selfInvestment = false;

  @override
  void dispose() {
    _amount.dispose();
    _note.dispose();
    super.dispose();
  }

  Future<void> _save(List<CategoryDto> categories) async {
    final mode = widget.mode;
    final note = _note.text.trim().isEmpty ? null : _note.text.trim();
    final core = ref.read(coreProvider);
    final ok = await act(() async {
      switch (mode) {
        case 'SALE':
          await core.kkRecordSale(
            spaceId: widget.spaceId,
            input: KkSaleInput(amount: _amount.text, channel: _wallet, occurredOn: _date, note: note),
          );
        case 'EXPENSE':
          await core.recordExpense(
            spaceId: widget.spaceId,
            input: NewExpenseInput(
              amount: _amount.text,
              categoryId: _categoryId ?? categories.firstOrNull?.id ?? '',
              channel: _wallet,
              occurredOn: _date,
              isGift: false,
              isOstentation: false,
              fundedByDebt: false,
              selfInvestment: _selfInvestment,
              note: note,
            ),
          );
        default:
          await core.kkRecordMove(
            spaceId: widget.spaceId,
            input: KkMoveInput(
              kind: mode,
              wallet: _wallet,
              toWallet: mode == 'TRANSFER' ? _toWallet : null,
              amount: _amount.text,
              occurredOn: _date,
              note: note,
            ),
          );
      }
      return true;
    });
    if (ok != null && mounted) Navigator.of(context).pop();
  }

  @override
  Widget build(BuildContext context) {
    final mode = widget.mode;
    final sid = widget.spaceId;
    final categories = mode == 'EXPENSE'
        ? ref.watch(query(['categories', sid], (c) => c.categories(spaceId: sid))).valueOrNull ?? <CategoryDto>[]
        : <CategoryDto>[];
    return SingleChildScrollView(
      padding: const EdgeInsets.fromLTRB(20, 0, 20, 20),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: [
          KkSheetTitle(context.t('kk.action.$mode'), hint: context.t('kk.hint.$mode')),
          AmountField(label: context.t('common.amount'), controller: _amount, autofocus: true),
          if (mode == 'EXPENSE') ...[
            const SizedBox(height: 12),
            Select<String>(
              label: context.t('kk.category'),
              items: [for (final c in categories) (c.id, c.customName ?? context.t(c.nameKey))],
              value: _categoryId ?? categories.firstOrNull?.id,
              onChanged: (v) => setState(() => _categoryId = v),
            ),
            CheckboxListTile(
              key: const Key('kk-self-investment'),
              contentPadding: EdgeInsets.zero,
              value: _selfInvestment,
              title: Text(context.t('kk.selfInvestment')),
              subtitle: Text(context.t('kk.selfInvestmentHint')),
              onChanged: (v) => setState(() => _selfInvestment = v ?? false),
            ),
          ],
          const SizedBox(height: 12),
          KkWalletPicker(
            label: context.t(mode == 'TRANSFER' ? 'kk.fromWallet' : 'kk.walletLabel'),
            value: _wallet,
            onChanged: (w) => setState(() => _wallet = w),
          ),
          if (mode == 'TRANSFER') ...[
            const SizedBox(height: 12),
            KkWalletPicker(
              label: context.t('kk.toWallet'),
              value: _toWallet,
              onChanged: (w) => setState(() => _toWallet = w),
            ),
          ],
          const SizedBox(height: 12),
          // Bo'sh sana — yadro «bugun» deb oladi.
          DateField(label: context.t('kk.date'), value: _date, onChanged: (v) => setState(() => _date = v)),
          const SizedBox(height: 12),
          Field(label: context.t(mode == 'SALE' ? 'kk.saleNote' : 'kk.note'), controller: _note),
          ErrorText(error),
          const SizedBox(height: 16),
          Row(
            mainAxisAlignment: MainAxisAlignment.end,
            children: [
              TextButton(onPressed: () => Navigator.of(context).pop(), child: Text(context.t('common.cancel'))),
              const SizedBox(width: 8),
              FilledButton(
                onPressed: busy ? null : () => _save(categories),
                child: Text(context.t('common.save')),
              ),
            ],
          ),
        ],
      ),
    );
  }
}
