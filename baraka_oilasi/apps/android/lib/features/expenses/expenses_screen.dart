import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../app/i18n.dart';
import '../../app/theme.dart';
import '../../core/core.dart';
import '../../core/query.dart';
import '../../shared/widgets.dart';
import '../learning/learning_screen.dart';

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
  // «O'zimga sarmoya» belgisi (uy/SPEC 2G.3). Bu ekran faqat Uy menyusida (Kasb-kor, Musofir va
  // sotuvchi menyularida yo'q; Kasb-kor va Musofir belgisi — o'z yozuv oynalarida). Rejalar faqat belgi qo'yilganda o'qiladi.
  bool _selfInvestment = false;
  String? _memberId;
  String? _planId;

  @override
  void dispose() {
    _amount.dispose();
    super.dispose();
  }

  Future<void> _save(List<LearningPlanDto> plans) async {
    final plan = plans.where((p) => p.id == _planId).firstOrNull;
    final invest = _selfInvestment;
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
              // Reja tanlansa — xarajat reja a'zosiniki (yadro mosligini tekshiradi).
              memberId: invest ? _memberId ?? plan?.memberId : null,
              isGift: false,
              isOstentation: false,
              fundedByDebt: false,
              selfInvestment: invest,
              learningPlanId: invest ? plan?.id : null,
            ),
          ),
    );
    if (r != null) {
      _amount.clear();
      setState(() {
        _necessity = null;
        _selfInvestment = false;
        _planId = null;
      });
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
    final learning = _selfInvestment ? ref.watch(learningQuery(id)).valueOrNull : null;
    final members = learning?.members ?? <LearningMemberDto>[];
    final names = {for (final m in members) m.memberId: m.displayName};
    // Faqat ochiq (`ACTIVE`/`PAUSED`) rejalar; a'zo tanlangan bo'lsa — uning rejalari.
    final plans = [
      for (final pl in learning?.plans ?? <LearningPlanDto>[])
        if ((pl.status == 'ACTIVE' || pl.status == 'PAUSED') && (_memberId == null || pl.memberId == _memberId)) pl,
    ];
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
            CheckboxListTile(
              contentPadding: EdgeInsets.zero,
              value: _selfInvestment,
              title: Text(context.t('expense.selfInvestment')),
              subtitle: Text(context.t('expense.selfInvestmentHint')),
              onChanged: (on) => setState(() => _selfInvestment = on ?? false),
            ),
            if (_selfInvestment) ...[
              if (members.length > 1) ...[
                Select<String?>(
                  label: context.t('expense.member'),
                  items: [(null, '—'), for (final m in members) (m.memberId, m.displayName)],
                  value: _memberId,
                  onChanged: (v) => setState(() {
                    _memberId = v;
                    _planId = null;
                  }),
                ),
                const SizedBox(height: 8),
              ],
              Select<String?>(
                label: context.t('expense.plan'),
                items: [
                  (null, '—'),
                  for (final pl in plans)
                    (pl.id, members.length > 1 ? '${pl.skill} · ${names[pl.memberId] ?? ''}' : pl.skill),
                ],
                value: _planId,
                onChanged: (v) => setState(() => _planId = v),
              ),
            ],
            ErrorText(error),
            const SizedBox(height: 12),
            FilledButton(onPressed: busy ? null : () => _save(plans), child: Text(context.t('common.save'))),
          ],
        ),
        if (by != null)
          SectionCard(
            children: [
              ValueRow(context.t('necessity.ZARUR'), by.zarur.formatted, valueColor: p.zarur),
              ValueRow(context.t('necessity.KERAK'), by.kerak.formatted, valueColor: p.kerak),
              ValueRow(context.t('necessity.HAVAS'), by.havas.formatted, valueColor: p.havas),
              ValueRow(context.t('audit.sadaqa'), by.sadaqa.formatted, valueColor: p.accentText),
              if (summary != null)
                ValueRow(
                  context.t('expense.selfInvestmentTotal'),
                  summary.selfInvestment.total.formatted,
                  valueColor: p.accentText,
                ),
            ],
          ),
      ],
    );
  }
}
