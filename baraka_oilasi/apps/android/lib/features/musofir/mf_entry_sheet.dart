import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../app/i18n.dart';
import '../../core/core.dart';
import '../../core/query.dart';
import '../../shared/widgets.dart';
import 'purpose_shares.dart';

/// Musofir makoni sharhi (bosh sahifa va yozuv oynasi uchun bitta kalit).
ProviderListenable<AsyncValue<MfOverviewDto>> mfOverviewQuery(String spaceId) =>
    query(['mf', spaceId], (c) => c.mfOverview(spaceId: spaceId));

ProviderListenable<AsyncValue<MfTermsDto>> mfTermsQuery(String spaceId) =>
    query(['mfTerms', spaceId], (c) => c.mfTerms(spaceId: spaceId));

ProviderListenable<AsyncValue<List<CategoryDto>>> categoriesQuery(String spaceId) =>
    query(['categories', spaceId], (c) => c.categories(spaceId: spaceId));

/// Maoshdan keyingi taklif (M4): oxirgi daromad yozuvi natijasi — bosh sahifa ko'rsatadi
/// (yozuv tez tugmadan ochilgan bo'lsa ham).
final mfOfferProvider = StateProvider<MfIncomeRecordedDto?>((ref) => null);

/// Kategoriya nomi (o'z nomi yoki tizim kaliti).
String categoryName(BuildContext context, List<CategoryDto> list, String? id) {
  final c = list.where((x) => x.id == id).firstOrNull;
  return c == null ? '' : (c.customName ?? context.t(c.nameKey));
}

/// Musofir yozuvi oynasi: `kind` — `SALARY`, `OTHER_INCOME`, `EXPENSE`, `SENT_HOME`, `FUND_IN`,
/// `FUND_OUT`, `OPENING`, `FUND_OPENING`, `RESERVE_IN`, `RESERVE_OUT`, `RESERVE_OPENING`.
Future<void> openMfEntry(BuildContext context, String spaceId, String kind, {String? initialAmount}) =>
    showSheet<void>(context, (_) => MfEntrySheet(spaceId: spaceId, kind: kind, initialAmount: initialAmount));

/// Musofir yozuvi (musofir/SPEC 2–3): maosh, boshqa daromad, xarajat, uyga yuborish, jamg'armaga /
/// jamg'armadan, zaxira pul, boshlang'ich qoldiqlar. Summalar ish valyutasida, matn ko'rinishida
/// yadroga beriladi.
class MfEntrySheet extends ConsumerStatefulWidget {
  const MfEntrySheet({required this.spaceId, required this.kind, this.initialAmount, super.key});

  final String spaceId;
  final String kind;
  final String? initialAmount;

  @override
  ConsumerState<MfEntrySheet> createState() => _MfEntrySheetState();
}

class _MfEntrySheetState extends ConsumerState<MfEntrySheet> with ActionState {
  late final _amount = TextEditingController(text: widget.initialAmount ?? '');
  final _fee = TextEditingController();
  final _received = TextEditingController();
  final _note = TextEditingController();
  String _channel = 'CARD';
  String? _categoryId;
  String? _date;
  SharesDraft? _shares;

  String get _kind => widget.kind;
  bool get _income => _kind == 'SALARY' || _kind == 'OTHER_INCOME';
  bool get _withdrawal => _kind == 'FUND_OUT' || _kind == 'RESERVE_OUT';

  @override
  void dispose() {
    for (final c in [_amount, _fee, _received, _note]) {
      c.dispose();
    }
    _shares?.dispose();
    super.dispose();
  }

  String? _opt(TextEditingController c) => c.text.trim().isEmpty ? null : c.text.trim();

  Future<void> _save(List<CategoryDto> categories) async {
    final core = ref.read(coreProvider);
    final sid = widget.spaceId;
    final note = _opt(_note);
    final ok = await act(() async {
      if (_income) {
        final r = await core.mfRecordIncome(
          spaceId: sid,
          input: MfIncomeInput(kind: _kind, amount: _amount.text, channel: _channel, occurredOn: _date, note: note),
        );
        ref.read(mfOfferProvider.notifier).state = r;
      } else if (_kind == 'EXPENSE') {
        await core.mfRecordExpense(
          spaceId: sid,
          input: MfExpenseInput(
            amount: _amount.text,
            categoryId: _categoryId ?? categories.firstOrNull?.id ?? '',
            channel: _channel,
            occurredOn: _date,
            note: note,
          ),
        );
      } else {
        final sent = _kind == 'SENT_HOME';
        await core.mfRecordMove(
          spaceId: sid,
          input: MfMoveInput(
            kind: _kind,
            amount: _amount.text,
            fee: sent ? _opt(_fee) : null,
            received: sent ? _opt(_received) : null,
            occurredOn: _date,
            note: note,
            purposes: sent ? _shares?.input() : null,
          ),
        );
      }
      return true;
    });
    if (ok == true && mounted) Navigator.of(context).pop();
  }

  @override
  Widget build(BuildContext context) {
    final sid = widget.spaceId;
    final s = ref.watch(mfOverviewQuery(sid)).valueOrNull?.settings;
    final work = s?.workCurrency ?? '';
    final home = s?.homeCurrency ?? '';
    final categories = _kind == 'EXPENSE'
        ? ref.watch(categoriesQuery(sid)).valueOrNull ?? const <CategoryDto>[]
        : const <CategoryDto>[];
    if (_kind == 'SENT_HOME' && _shares == null) {
      // Maqsadlar — kelishuv shartlaridan taklif, o'zgartirish mumkin (M2).
      final terms = ref.watch(mfTermsQuery(sid));
      if (terms.hasValue || terms.hasError) _shares = SharesDraft.from(terms.valueOrNull?.shares);
    }
    final shares = _shares;
    return SingleChildScrollView(
      padding: const EdgeInsets.fromLTRB(20, 0, 20, 20),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: [
          Semantics(
            header: true,
            child: Text(
              context.t('mf.action.$_kind'),
              style: const TextStyle(fontSize: 20, fontWeight: FontWeight.w700),
            ),
          ),
          const SizedBox(height: 4),
          Hint(context.t('mf.hint.$_kind')),
          const SizedBox(height: 16),
          AmountField(
            label: context.t('mf.amountIn', {'currency': work}),
            controller: _amount,
            autofocus: widget.initialAmount == null,
          ),
          if (_kind == 'EXPENSE') ...[
            const SizedBox(height: 12),
            Select<String>(
              label: context.t('kk.category'),
              items: [for (final c in categories) (c.id, c.customName ?? context.t(c.nameKey))],
              value: _categoryId ?? categories.firstOrNull?.id,
              onChanged: (v) => setState(() => _categoryId = v),
            ),
          ],
          if (_kind == 'SENT_HOME') ...[
            const SizedBox(height: 12),
            AmountField(label: context.t('mf.fee', {'currency': work}), controller: _fee),
            const SizedBox(height: 12),
            AmountField(label: context.t('mf.received', {'currency': home}), controller: _received),
            const SizedBox(height: 12),
            if (shares != null) PurposeShares(draft: shares, legend: context.t('mf.purposesLegend')),
          ],
          if (_income || _kind == 'EXPENSE') ...[
            const SizedBox(height: 12),
            SegmentedChoice<String>(
              label: context.t('mf.channel'),
              options: [
                for (final c in ['CARD', 'CASH']) (c, context.t('kk.channel.$c')),
              ],
              value: _channel,
              onChanged: (v) => setState(() => _channel = v),
            ),
          ],
          const SizedBox(height: 12),
          DateField(label: context.t('kk.date'), value: _date, onChanged: (v) => setState(() => _date = v)),
          const SizedBox(height: 12),
          Field(label: context.t(_withdrawal ? 'mf.reason' : 'kk.note'), controller: _note),
          ErrorText(error),
          const SizedBox(height: 12),
          Wrap(
            spacing: 8,
            alignment: WrapAlignment.end,
            children: [
              TextButton(onPressed: () => Navigator.of(context).pop(), child: Text(context.t('common.cancel'))),
              FilledButton(
                onPressed: busy || s == null ? null : () => _save(categories),
                child: Text(context.t('common.save')),
              ),
            ],
          ),
        ],
      ),
    );
  }
}
