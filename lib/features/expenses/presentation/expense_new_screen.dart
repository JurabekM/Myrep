import 'package:baraka_daftari/app/l10n/l10n.dart';
import 'package:baraka_daftari/app/refresh.dart';
import 'package:baraka_daftari/app/widgets/labels.dart';
import 'package:baraka_daftari/app/widgets/money_input.dart';
import 'package:baraka_daftari/core/domain/enums.dart';
import 'package:baraka_daftari/core/logging/app_log.dart';
import 'package:baraka_daftari/core/money/money.dart';
import 'package:baraka_daftari/features/budget/data/budget_providers.dart';
import 'package:baraka_daftari/features/content/data/content_providers.dart';
import 'package:baraka_daftari/features/content/domain/content.dart';
import 'package:baraka_daftari/features/expenses/data/expense_providers.dart';
import 'package:baraka_daftari/features/expenses/domain/expense.dart';
import 'package:baraka_daftari/features/expenses/presentation/expense_views.dart';
import 'package:baraka_daftari/features/household/presentation/member_views.dart';
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

/// Tez xarajat kiritish (SPEC 2B.1–2B.2): shablon, «oxirgisini takrorlash»,
/// summa, kategoriya (toifa undan avtomatik), belgilar.
class ExpenseNewScreen extends ConsumerStatefulWidget {
  const ExpenseNewScreen({super.key});

  @override
  ConsumerState<ExpenseNewScreen> createState() => _ExpenseNewScreenState();
}

class _ExpenseNewScreenState extends ConsumerState<ExpenseNewScreen> {
  final _amount = AmountController();
  final _templateTitle = TextEditingController();
  String? _categoryId;
  Necessity? _necessity;
  PaymentChannel _channel = PaymentChannel.cash;
  String? _memberId;
  String? _habitId;
  bool _gift = false;
  bool _ostentation = false;
  bool _debt = false;
  bool _asTemplate = false;
  bool _saving = false;

  @override
  void dispose() {
    _amount.dispose();
    _templateTitle.dispose();
    super.dispose();
  }

  void _selectCategory(Category c) => setState(() {
    _categoryId = c.meta.id;
    _necessity = c.defaultNecessity;
  });

  void _applyTemplate(ExpenseTemplate t, List<Category> categories) {
    final category = categories.where((c) => c.meta.id == t.categoryId);
    setState(() {
      _amount.value = t.amount.minorUnits ~/ t.amount.currency.minorPerMajor;
      _categoryId = t.categoryId;
      _necessity =
          t.necessity ??
          (category.isEmpty ? null : category.first.defaultNecessity);
      _channel = t.channel;
      _habitId = t.habitId;
    });
  }

  Future<void> _repeatLast() async {
    final l10n = context.l10n;
    final messenger = ScaffoldMessenger.of(context);
    final navigator = Navigator.of(context);
    final money = context.money;
    try {
      final service = await ref.read(expenseServiceProvider.future);
      final e = await service.repeatLast(memberId: _memberId);
      refreshMoneyViews(ref);
      await recordTaskEvent(ref, TaskTrigger.expenseRecorded);
      messenger.showSnackBar(
        SnackBar(content: Text(l10n.repeatLastDone(money(e.amount)))),
      );
      navigator.pop();
    } on Object {
      AppLog.event('expense_repeat_failed');
      messenger.showSnackBar(SnackBar(content: Text(l10n.genericError)));
    }
  }

  bool get _canSave =>
      _amount.value > 0 &&
      _categoryId != null &&
      !_saving &&
      (!_asTemplate || _templateTitle.text.trim().isNotEmpty);

  Future<void> _save() async {
    if (!_canSave) return;
    setState(() => _saving = true);
    final l10n = context.l10n;
    final messenger = ScaffoldMessenger.of(context);
    final navigator = Navigator.of(context);
    try {
      final service = await ref.read(expenseServiceProvider.future);
      final amount = Money.major(_amount.value, await service.currency());
      await service.add(
        amount: amount,
        categoryId: _categoryId!,
        channel: _channel,
        memberId: _memberId,
        necessity: _necessity,
        isGift: _gift,
        isOstentation: _ostentation,
        fundedByDebt: _debt,
        habitId: _habitId,
      );
      if (_asTemplate) {
        await service.addTemplate(
          title: _templateTitle.text,
          amount: amount,
          categoryId: _categoryId!,
          channel: _channel,
          necessity: _necessity,
          habitId: _habitId,
        );
      }
      refreshMoneyViews(ref);
      await recordTaskEvent(ref, TaskTrigger.expenseRecorded);
      messenger.showSnackBar(SnackBar(content: Text(l10n.expenseSaved)));
      navigator.pop();
    } on Object {
      AppLog.event('expense_save_failed');
      messenger.showSnackBar(SnackBar(content: Text(l10n.genericError)));
      if (mounted) setState(() => _saving = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    final l10n = context.l10n;
    final theme = Theme.of(context);
    final categories = ref.watch(expenseCategoriesProvider);
    final templates =
        ref.watch(expenseTemplatesProvider).valueOrNull ?? const [];
    final latest = ref.watch(latestExpenseProvider).valueOrNull;
    final habits = ref.watch(habitStatsProvider).valueOrNull ?? const [];
    return Scaffold(
      appBar: AppBar(title: Text(l10n.expenseNewTitle)),
      body: switch (categories) {
        AsyncError() => Center(child: Text(l10n.genericError)),
        AsyncData(:final value) => Center(
          child: ConstrainedBox(
            constraints: const BoxConstraints(maxWidth: 520),
            // Summa, klaviatura va «Saqlash» doim ko'rinadi (SPEC 2B.1:
            // kiritish 1 ekranda); tanlovlar tepada aylanadi.
            child: Column(
              children: [
                Expanded(
                  child: ListView(
                    padding: const EdgeInsets.fromLTRB(16, 8, 16, 8),
                    children: [
                      if (templates.isNotEmpty || latest != null)
                        Wrap(
                          spacing: 8,
                          runSpacing: 4,
                          children: [
                            for (final t in templates)
                              ActionChip(
                                key: Key('template-${t.meta.id}'),
                                avatar: const Icon(Icons.bolt, size: 18),
                                label: Text(t.title),
                                onPressed: () => _applyTemplate(t, value),
                              ),
                            if (latest != null)
                              ActionChip(
                                key: const Key('expense-repeat-last'),
                                avatar: const Icon(Icons.replay, size: 18),
                                label: Text(l10n.repeatLast),
                                onPressed: _repeatLast,
                              ),
                          ],
                        ),
                      const SizedBox(height: 4),
                      Text(
                        l10n.expenseCategory,
                        style: theme.textTheme.labelLarge,
                      ),
                      const SizedBox(height: 4),
                      Wrap(
                        spacing: 8,
                        runSpacing: 4,
                        children: [
                          for (final c in value)
                            ChoiceChip(
                              key: Key(
                                'category-${c.systemKey?.name ?? c.meta.id}',
                              ),
                              label: Text(l10n.category(c)),
                              selected: c.meta.id == _categoryId,
                              onSelected: (_) => _selectCategory(c),
                            ),
                        ],
                      ),
                      if (_categoryId != null) ...[
                        const SizedBox(height: 8),
                        _NecessityPicker(
                          isSadaqa: value.any(
                            (c) =>
                                c.meta.id == _categoryId &&
                                c.systemKey == CategoryKey.sadaqa,
                          ),
                          value: _necessity,
                          onChanged: (n) => setState(() => _necessity = n),
                        ),
                      ],
                      const SizedBox(height: 8),
                      Text(
                        l10n.channelLabel,
                        style: theme.textTheme.labelLarge,
                      ),
                      const SizedBox(height: 4),
                      Wrap(
                        spacing: 8,
                        children: [
                          for (final ch in PaymentChannel.values)
                            ChoiceChip(
                              key: Key('expense-channel-${ch.name}'),
                              label: Text(
                                ch == PaymentChannel.cash
                                    ? l10n.channelCash
                                    : l10n.channelCard,
                              ),
                              selected: ch == _channel,
                              onSelected: (_) => setState(() => _channel = ch),
                            ),
                        ],
                      ),
                      MemberPicker(
                        selectedId: _memberId,
                        onSelected: (id) => setState(() => _memberId = id),
                      ),
                      const SizedBox(height: 8),
                      Text(
                        l10n.expenseFlagsLabel,
                        style: theme.textTheme.labelLarge,
                      ),
                      const SizedBox(height: 4),
                      Wrap(
                        spacing: 8,
                        runSpacing: 4,
                        children: [
                          FilterChip(
                            key: const Key('flag-gift'),
                            avatar: const Icon(Icons.card_giftcard, size: 18),
                            label: Text(l10n.flagGift),
                            selected: _gift,
                            onSelected: (v) => setState(() => _gift = v),
                          ),
                          FilterChip(
                            key: const Key('flag-ostentation'),
                            avatar: const Icon(
                              Icons.visibility_outlined,
                              size: 18,
                            ),
                            label: Text(l10n.flagOstentation),
                            selected: _ostentation,
                            onSelected: (v) => setState(() => _ostentation = v),
                          ),
                          FilterChip(
                            key: const Key('flag-debt'),
                            avatar: const Icon(Icons.credit_card, size: 18),
                            label: Text(l10n.flagDebt),
                            selected: _debt,
                            onSelected: (v) => setState(() => _debt = v),
                          ),
                        ],
                      ),
                      if (_debt && _necessity == Necessity.havas)
                        const Padding(
                          padding: EdgeInsets.only(top: 4),
                          child: DebtHavasFlag(key: Key('debt-havas-flag')),
                        ),
                      if (habits.isNotEmpty) ...[
                        const SizedBox(height: 8),
                        Text(
                          l10n.habitLabel,
                          style: theme.textTheme.labelLarge,
                        ),
                        Wrap(
                          spacing: 8,
                          children: [
                            ChoiceChip(
                              label: Text(l10n.habitNone),
                              selected: _habitId == null,
                              onSelected: (_) =>
                                  setState(() => _habitId = null),
                            ),
                            for (final h in habits)
                              ChoiceChip(
                                key: Key('habit-${h.subject.meta.id}'),
                                label: Text(h.subject.title),
                                selected: _habitId == h.subject.meta.id,
                                onSelected: (_) => setState(
                                  () => _habitId = h.subject.meta.id,
                                ),
                              ),
                          ],
                        ),
                      ],
                      CheckboxListTile(
                        key: const Key('expense-as-template'),
                        contentPadding: EdgeInsets.zero,
                        controlAffinity: ListTileControlAffinity.leading,
                        title: Text(l10n.templateFromForm),
                        value: _asTemplate,
                        onChanged: (v) =>
                            setState(() => _asTemplate = v ?? false),
                      ),
                      if (_asTemplate)
                        TextField(
                          key: const Key('expense-template-title'),
                          controller: _templateTitle,
                          decoration: InputDecoration(
                            labelText: l10n.templateTitleLabel,
                          ),
                          onChanged: (_) => setState(() {}),
                        ),
                    ],
                  ),
                ),
                const Divider(height: 1),
                Padding(
                  padding: const EdgeInsets.fromLTRB(16, 4, 16, 12),
                  child: Column(
                    children: [
                      AmountDisplay(
                        controller: _amount,
                        currency: CurrencyCode.uzs,
                      ),
                      MoneyKeypad(controller: _amount),
                      const SizedBox(height: 8),
                      ValueListenableBuilder<int>(
                        valueListenable: _amount,
                        builder: (context, v, _) => FilledButton(
                          key: const Key('expense-save'),
                          style: FilledButton.styleFrom(
                            minimumSize: const Size.fromHeight(52),
                          ),
                          onPressed: _canSave ? _save : null,
                          child: Text(l10n.save),
                        ),
                      ),
                    ],
                  ),
                ),
              ],
            ),
          ),
        ),
        _ => const Center(child: CircularProgressIndicator()),
      },
    );
  }
}

/// Zarur / Kerak / Havas tanlovi; sadaqada — izoh.
class _NecessityPicker extends StatelessWidget {
  const _NecessityPicker({
    required this.isSadaqa,
    required this.value,
    required this.onChanged,
  });

  final bool isSadaqa;
  final Necessity? value;
  final ValueChanged<Necessity> onChanged;

  @override
  Widget build(BuildContext context) {
    final l10n = context.l10n;
    final theme = Theme.of(context);
    if (isSadaqa) {
      return Text(
        l10n.necessitySadaqaNote,
        key: const Key('necessity-sadaqa'),
        style: theme.textTheme.bodySmall,
      );
    }
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Text(l10n.necessityLabel, style: theme.textTheme.labelLarge),
        const SizedBox(height: 4),
        NecessitySelector(value: value, onChanged: onChanged),
      ],
    );
  }
}

/// Uch toifali tanlov (havas — neytral rangda, qizil emas).
class NecessitySelector extends StatelessWidget {
  const NecessitySelector({
    required this.value,
    required this.onChanged,
    super.key,
  });

  final Necessity? value;
  final ValueChanged<Necessity> onChanged;

  @override
  Widget build(BuildContext context) {
    final l10n = context.l10n;
    return SegmentedButton<Necessity>(
      key: const Key('necessity-selector'),
      emptySelectionAllowed: true,
      showSelectedIcon: false,
      segments: [
        for (final n in Necessity.values)
          ButtonSegment(
            value: n,
            label: Text(l10n.necessity(n), key: Key('necessity-${n.name}')),
          ),
      ],
      selected: {?value},
      onSelectionChanged: (s) {
        if (s.isNotEmpty) onChanged(s.single);
      },
    );
  }
}

/// Qarz bilan qilingan havas — qizil bayroq (SPEC 2B.8).
class DebtHavasFlag extends StatelessWidget {
  const DebtHavasFlag({super.key});

  @override
  Widget build(BuildContext context) {
    final color = Theme.of(context).colorScheme.error;
    return Row(
      children: [
        Icon(Icons.flag, size: 18, color: color),
        const SizedBox(width: 4),
        Flexible(
          child: Text(
            context.l10n.debtHavasFlag,
            style: TextStyle(color: color),
          ),
        ),
      ],
    );
  }
}
