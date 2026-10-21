import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../app/i18n.dart';
import '../../app/theme.dart';
import '../../core/core.dart';
import '../../shared/widgets.dart';

Future<void> openIncome(BuildContext context, String spaceId) =>
    showSheet<void>(context, (_) => IncomeSheet(spaceId: spaceId));

/// Tez daromad kiritish va ulush taklifi: [Ajratish] [Boshqa summa] [Bu safar emas].
/// Taklif qilingan summa yadrodan `plain` ko'rinishida olinadi va o'zgarishsiz qaytariladi.
class IncomeSheet extends ConsumerStatefulWidget {
  const IncomeSheet({required this.spaceId, super.key});

  final String spaceId;

  @override
  ConsumerState<IncomeSheet> createState() => _IncomeSheetState();
}

class _IncomeSheetState extends ConsumerState<IncomeSheet> with ActionState {
  final _amount = TextEditingController();
  final _source = TextEditingController();
  final _custom = TextEditingController();
  String _channel = 'CASH';
  IncomeRecordedDto? _recorded;
  bool _customMode = false;

  @override
  void dispose() {
    _amount.dispose();
    _source.dispose();
    _custom.dispose();
    super.dispose();
  }

  Future<void> _save() async {
    final r = await act(
      () => ref
          .read(coreProvider)
          .recordIncome(
            spaceId: widget.spaceId,
            input: NewIncomeInput(amount: _amount.text, source: _source.text, channel: _channel),
          ),
    );
    if (r != null) setState(() => _recorded = r);
  }

  Future<void> _allocate(String share) async {
    final r = await act(
      () => ref
          .read(coreProvider)
          .allocateToVault(spaceId: widget.spaceId, incomeId: _recorded!.income.id, amount: share),
    );
    if (r != null && mounted) Navigator.of(context).pop();
  }

  @override
  Widget build(BuildContext context) {
    final rec = _recorded;
    return SingleChildScrollView(
      padding: const EdgeInsets.fromLTRB(20, 0, 20, 20),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: [
          Semantics(
            header: true,
            child: Text(context.t('income.title'), style: const TextStyle(fontSize: 20, fontWeight: FontWeight.w700)),
          ),
          const SizedBox(height: 16),
          if (rec == null) ...[
            AmountField(label: context.t('common.amount'), controller: _amount, autofocus: true),
            const SizedBox(height: 12),
            Field(label: context.t('income.source'), controller: _source),
            const SizedBox(height: 12),
            SegmentedChoice<String>(
              label: '',
              options: [
                for (final c in ['CASH', 'CARD']) (c, context.t('income.channel.$c')),
              ],
              value: _channel,
              onChanged: (c) => setState(() => _channel = c),
            ),
            ErrorText(error),
            const SizedBox(height: 16),
            Row(
              mainAxisAlignment: MainAxisAlignment.end,
              children: [
                TextButton(onPressed: () => Navigator.of(context).pop(), child: Text(context.t('common.cancel'))),
                const SizedBox(width: 8),
                FilledButton(onPressed: busy ? null : _save, child: Text(context.t('common.save'))),
              ],
            ),
          ] else ...[
            Text(
              context.t('income.shareOffer', {'amount': rec.suggestedShare.formatted}),
              key: const Key('income-share-offer'),
              style: const TextStyle(fontSize: 18),
            ),
            if (rec.progressiveSuggestionPercent != null)
              Padding(
                padding: const EdgeInsets.only(top: 8),
                child: Text(
                  context.t('income.progressive', {'percent': rec.progressiveSuggestionPercent}),
                  style: TextStyle(color: context.palette.accentText),
                ),
              ),
            if (_customMode) ...[
              const SizedBox(height: 12),
              AmountField(label: context.t('income.otherAmount'), controller: _custom, autofocus: true),
            ],
            ErrorText(error),
            const SizedBox(height: 16),
            Wrap(
              alignment: WrapAlignment.end,
              spacing: 8,
              runSpacing: 8,
              children: [
                TextButton(onPressed: () => Navigator.of(context).pop(), child: Text(context.t('income.notNow'))),
                if (!_customMode)
                  OutlinedButton(
                    onPressed: () => setState(() {
                      _customMode = true;
                      _custom.text = rec.suggestedShare.plain;
                    }),
                    child: Text(context.t('income.otherAmount')),
                  ),
                FilledButton(
                  onPressed: busy ? null : () => _allocate(_customMode ? _custom.text : rec.suggestedShare.plain),
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
