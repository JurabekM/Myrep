import 'dart:async';

import 'package:baraka_daftari/app/l10n/l10n.dart';
import 'package:baraka_daftari/app/refresh.dart';
import 'package:baraka_daftari/app/widgets/money_input.dart';
import 'package:baraka_daftari/app/widgets/settings_actions.dart';
import 'package:baraka_daftari/core/domain/enums.dart';
import 'package:baraka_daftari/core/logging/app_log.dart';
import 'package:baraka_daftari/features/household/presentation/member_views.dart';
import 'package:baraka_daftari/features/income/domain/income_service.dart';
import 'package:baraka_daftari/features/vault/data/vault_providers.dart';
import 'package:baraka_daftari/features/vault/presentation/share_offer_sheet.dart';
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

/// Tez daromad kiritish (SPEC 2.1): bitta ekran, raqamli klaviatura, oxirgi
/// manba va kanal oldindan tanlangan. Oxirgi summa chip'i bilan saqlash
/// bosh sahifadan hisoblaganda 3 ta bosish: «Daromad» → chip → «Saqlash».
class IncomeNewScreen extends ConsumerStatefulWidget {
  const IncomeNewScreen({super.key});

  @override
  ConsumerState<IncomeNewScreen> createState() => _IncomeNewScreenState();
}

class _IncomeNewScreenState extends ConsumerState<IncomeNewScreen> {
  final _amount = AmountController();
  IncomeDefaults? _defaults;
  IncomeSource? _source;
  IncomeSourceType? _sourceType;
  PaymentChannel? _channel;
  String? _memberId;
  bool _saving = false;
  bool _loadFailed = false;

  @override
  void initState() {
    super.initState();
    unawaited(_load());
  }

  @override
  void dispose() {
    _amount.dispose();
    super.dispose();
  }

  Future<void> _load() async {
    try {
      final service = await ref.read(incomeServiceProvider.future);
      final d = await service.defaults();
      if (!mounted) return;
      setState(() {
        _defaults = d;
        _source ??= d.source;
        _channel ??= d.channel;
      });
    } on Object {
      // Cheksiz yuklanish o'rniga xato ko'rsatiladi.
      AppLog.event('income_defaults_failed');
      if (mounted) setState(() => _loadFailed = true);
    }
  }

  Future<void> _save() async {
    final d = _defaults;
    if (d == null || _amount.value == 0 || _saving) return;
    setState(() => _saving = true);
    final l10n = context.l10n;
    final messenger = ScaffoldMessenger.of(context);
    final navigator = Navigator.of(context);
    try {
      final service = await ref.read(incomeServiceProvider.future);
      final income = await service.add(
        amount: _amount.moneyIn(d.currency),
        source: _source!,
        channel: _channel!,
        memberId: _memberId,
        sourceType: _sourceType,
      );
      refreshMoneyViews(ref);
      final vault = await ref.read(vaultServiceProvider.future);
      final suggestion = await vault.suggestShare(income);
      if (!mounted) return;
      if (suggestion != null) {
        // Taklif oynasining o'zi «saqlandi» tasdig'i; natijani u xabar qiladi.
        await showShareOfferSheet(
          context,
          income: income,
          suggestion: suggestion,
        );
      } else {
        messenger.showSnackBar(SnackBar(content: Text(l10n.incomeSaved)));
      }
      if (navigator.canPop()) navigator.pop();
    } on Object {
      AppLog.event('income_save_failed');
      messenger.showSnackBar(SnackBar(content: Text(l10n.genericError)));
      if (mounted) setState(() => _saving = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    final l10n = context.l10n;
    final theme = Theme.of(context);
    final d = _defaults;
    return Scaffold(
      appBar: AppBar(
        title: Text(l10n.incomeNewTitle),
        actions: const [SettingsActions()],
      ),
      body: d == null
          ? Center(
              child: _loadFailed
                  ? Text(l10n.genericError, key: const Key('income-load-error'))
                  : const CircularProgressIndicator(),
            )
          : SafeArea(
              child: Center(
                child: ConstrainedBox(
                  constraints: const BoxConstraints(maxWidth: 520),
                  // Summa, klaviatura va «Saqlash» doim ko'rinadi (tez
                  // kiritish — 3 bosish); tanlovlar tepada aylanadi.
                  child: Column(
                    children: [
                      Expanded(
                        child: ListView(
                          padding: const EdgeInsets.fromLTRB(16, 8, 16, 8),
                          children: [
                            if (d.recentAmounts.isNotEmpty) ...[
                              const SizedBox(height: 12),
                              Text(
                                l10n.incomeRecentAmounts,
                                style: theme.textTheme.labelLarge,
                              ),
                              const SizedBox(height: 4),
                              Wrap(
                                spacing: 8,
                                children: [
                                  for (final (i, m) in d.recentAmounts.indexed)
                                    ActionChip(
                                      key: Key('recent-amount-$i'),
                                      label: Text(context.money(m)),
                                      onPressed: () => _amount.value =
                                          m.minorUnits ~/
                                          m.currency.minorPerMajor,
                                    ),
                                ],
                              ),
                            ],
                            const SizedBox(height: 12),
                            _Choice<IncomeSource>(
                              label: l10n.incomeSourceLabel,
                              values: IncomeSource.values,
                              selected: _source!,
                              name: (s) => switch (s) {
                                IncomeSource.dailyWork =>
                                  l10n.incomeSourceDailyWork,
                                IncomeSource.order => l10n.incomeSourceOrder,
                                IncomeSource.salary => l10n.incomeSourceSalary,
                                IncomeSource.other => l10n.incomeSourceOther,
                              },
                              onSelected: (s) => setState(() => _source = s),
                            ),
                            const SizedBox(height: 8),
                            _Choice<PaymentChannel>(
                              label: l10n.channelLabel,
                              values: PaymentChannel.values,
                              selected: _channel!,
                              name: (c) => switch (c) {
                                PaymentChannel.cash => l10n.channelCash,
                                PaymentChannel.card => l10n.channelCard,
                              },
                              onSelected: (c) => setState(() => _channel = c),
                            ),
                            MemberPicker(
                              selectedId: _memberId,
                              onSelected: (id) =>
                                  setState(() => _memberId = id),
                            ),
                            const SizedBox(height: 8),
                            // Ribo filtri (SPEC 2C.5): ixtiyoriy, bitta tanlov.
                            Text(
                              l10n.incomeSourceTypeLabel,
                              style: Theme.of(context).textTheme.labelLarge,
                            ),
                            Wrap(
                              spacing: 6,
                              children: [
                                for (final t in IncomeSourceType.values)
                                  FilterChip(
                                    key: Key('income-type-${t.name}'),
                                    label: Text(switch (t) {
                                      IncomeSourceType.ter =>
                                        l10n.incomeTypeTer,
                                      IncomeSourceType.mol =>
                                        l10n.incomeTypeMol,
                                      IncomeSourceType.tavakkal =>
                                        l10n.incomeTypeTavakkal,
                                      IncomeSourceType.ribo =>
                                        l10n.incomeTypeRibo,
                                    }),
                                    selected: _sourceType == t,
                                    onSelected: (on) => setState(
                                      () => _sourceType = on ? t : null,
                                    ),
                                  ),
                              ],
                            ),
                            if (_sourceType == IncomeSourceType.ribo)
                              Text(
                                l10n.incomeRiboNote,
                                key: const Key('income-ribo-note'),
                                style: Theme.of(context).textTheme.bodySmall,
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
                              currency: d.currency,
                            ),
                            MoneyKeypad(controller: _amount),
                            const SizedBox(height: 8),
                            ValueListenableBuilder<int>(
                              valueListenable: _amount,
                              builder: (context, value, _) => FilledButton(
                                key: const Key('income-save'),
                                style: FilledButton.styleFrom(
                                  minimumSize: const Size.fromHeight(52),
                                ),
                                onPressed: value > 0 && !_saving ? _save : null,
                                child: Text(l10n.incomeSave),
                              ),
                            ),
                          ],
                        ),
                      ),
                    ],
                  ),
                ),
              ),
            ),
    );
  }
}

class _Choice<T extends Enum> extends StatelessWidget {
  const _Choice({
    required this.label,
    required this.values,
    required this.selected,
    required this.name,
    required this.onSelected,
  });

  final String label;
  final List<T> values;
  final T selected;
  final String Function(T) name;
  final ValueChanged<T> onSelected;

  @override
  Widget build(BuildContext context) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Text(label, style: Theme.of(context).textTheme.labelLarge),
        const SizedBox(height: 4),
        Wrap(
          spacing: 8,
          runSpacing: 4,
          children: [
            for (final v in values)
              ChoiceChip(
                key: Key('choice-${v.name}'),
                label: Text(name(v)),
                selected: v == selected,
                onSelected: (_) => onSelected(v),
              ),
          ],
        ),
      ],
    );
  }
}
