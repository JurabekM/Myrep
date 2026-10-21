import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../app/i18n.dart';
import '../../app/theme.dart';
import '../../core/core.dart';
import '../../core/query.dart';
import '../../shared/widgets.dart';

const necessities = ['ZARUR', 'KERAK', 'HAVAS'];

/// Tez xarajat kiritish: toifa kategoriyadan olinadi va o'zgartirilishi mumkin (havas — neytral rangda).
class ExpensesScreen extends ConsumerStatefulWidget {
  const ExpensesScreen({required this.spaceId, super.key});

  final String spaceId;

  @override
  ConsumerState<ExpensesScreen> createState() => _ExpensesScreenState();
}

class _ExpensesScreenState extends ConsumerState<ExpensesScreen> with ActionState {
  final _amount = TextEditingController();
  String? _categoryId;
  String? _necessity;
  String _channel = 'CASH';

  @override
  void dispose() {
    _amount.dispose();
    super.dispose();
  }

  Future<void> _save() async {
    final r = await act(
      () => ref
          .read(coreProvider)
          .recordExpense(
            spaceId: widget.spaceId,
            input: NewExpenseInput(
              amount: _amount.text,
              categoryId: _categoryId ?? '',
              channel: _channel,
              necessity: _necessity,
              isGift: false,
              isOstentation: false,
              fundedByDebt: false,
            ),
          ),
    );
    if (r != null) {
      _amount.clear();
      setState(() => _necessity = null);
    }
  }

  @override
  Widget build(BuildContext context) {
    final id = widget.spaceId;
    final categories = ref.watch(query(['categories', id], (c) => c.categories(spaceId: id))).valueOrNull ?? [];
    final summary = ref.watch(query(['summary', id, null], (c) => c.monthlySummary(spaceId: id))).valueOrNull;
    final selected = categories.where((c) => c.id == _categoryId).firstOrNull;
    final active = _necessity ?? selected?.defaultNecessity;
    final by = summary?.byNecessity;
    final p = context.palette;
    return ScreenBody(
      mentorKey: 'mentor.expenses',
      children: [
        SectionCard(
          title: context.t('expense.title'),
          children: [
            AmountField(label: context.t('common.amount'), controller: _amount),
            const SizedBox(height: 12),
            Select<String>(
              label: context.t('expense.category'),
              items: [for (final c in categories) (c.id, c.customName ?? context.t(c.nameKey))],
              value: _categoryId,
              onChanged: (v) => setState(() => _categoryId = v),
            ),
            const SizedBox(height: 12),
            SegmentedChoice<String>(
              label: '',
              options: [for (final n in necessities) (n, context.t('necessity.$n'))],
              value: active,
              onChanged: (n) => setState(() => _necessity = n),
            ),
            const SizedBox(height: 8),
            SegmentedChoice<String>(
              label: '',
              options: [
                for (final c in ['CASH', 'CARD']) (c, context.t('income.channel.$c')),
              ],
              value: _channel,
              onChanged: (c) => setState(() => _channel = c),
            ),
            ErrorText(error),
            const SizedBox(height: 12),
            FilledButton(onPressed: busy ? null : _save, child: Text(context.t('common.save'))),
          ],
        ),
        if (by != null)
          SectionCard(
            children: [
              ValueRow(context.t('necessity.ZARUR'), by.zarur.formatted, valueColor: p.zarur),
              ValueRow(context.t('necessity.KERAK'), by.kerak.formatted, valueColor: p.kerak),
              ValueRow(context.t('necessity.HAVAS'), by.havas.formatted, valueColor: p.havas),
              ValueRow(context.t('audit.sadaqa'), by.sadaqa.formatted, valueColor: p.accentText),
            ],
          ),
      ],
    );
  }
}
