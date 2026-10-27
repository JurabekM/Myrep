import 'package:baraka_daftari/app/l10n/l10n.dart';
import 'package:baraka_daftari/app/refresh.dart';
import 'package:baraka_daftari/app/router/app_routes.dart';
import 'package:baraka_daftari/app/widgets/money_input.dart';
import 'package:baraka_daftari/core/logging/app_log.dart';
import 'package:baraka_daftari/core/money/fx_rate.dart';
import 'package:baraka_daftari/core/money/money.dart';
import 'package:baraka_daftari/core/time/clock.dart';
import 'package:baraka_daftari/features/vault/data/vault_providers.dart';
import 'package:baraka_daftari/features/vault/domain/lump_sum.dart';
import 'package:baraka_daftari/features/vault/domain/vault_service.dart';
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';

/// Katta summa (SPEC 2G.5): avval oilaning 6 oylik zaxira kamomadi,
/// qolgani hunarga. Summa chet el valyutasida bo'lsa,
/// foydalanuvchi kiritgan kurs bilan asosiy valyutaga aylantiriladi.
class LumpSumScreen extends ConsumerStatefulWidget {
  const LumpSumScreen({super.key});

  @override
  ConsumerState<LumpSumScreen> createState() => _LumpSumScreenState();
}

class _LumpSumScreenState extends ConsumerState<LumpSumScreen> {
  final _rate = TextEditingController();
  CurrencyCode? _currency;
  Money? _amount;
  bool _busy = false;

  @override
  void dispose() {
    _rate.dispose();
    super.dispose();
  }

  /// Kiritilgan summa asosiy valyutada; kurs noto'g'ri bo'lsa — `null`.
  Money? _inBase(CurrencyCode base) {
    final a = _amount;
    if (a == null) return null;
    if (a.currency == base) return a;
    try {
      final rate = FxRate.parse(
        a.currency,
        base,
        _rate.text,
        ref.read(clockProvider).nowUtc(),
      );
      return convert(a, rate);
    } on Object {
      return null;
    }
  }

  Future<void> _pickAmount(CurrencyCode currency) async {
    final l10n = context.l10n;
    final a = await showAmountSheet(
      context,
      currency: currency,
      title: l10n.lumpAmount,
      initial: _amount?.currency == currency ? _amount : null,
    );
    if (a != null && mounted) setState(() => _amount = a);
  }

  /// Devor (6 oylik zarur xarajat) hali noma'lum bo'lsa — oylik taxminni
  /// shu yerda so'raydi (qorovul kartasidagi taxmin amali bilan bir xil).
  Future<void> _estimate(CurrencyCode base) async {
    final amount = await showAmountSheet(
      context,
      currency: base,
      title: context.l10n.reserveEstimateTitle,
    );
    if (amount == null || !amount.isPositive) return;
    await (await ref.read(
      essentialSpendServiceProvider.future,
    )).setEstimate(amount);
    refreshMoneyViews(ref);
  }

  Future<void> _deposit(LumpSumPlan plan) async {
    final l10n = context.l10n;
    final messenger = ScaffoldMessenger.of(context);
    setState(() => _busy = true);
    try {
      await (await ref.read(
        vaultServiceProvider.future,
      )).depositManual(plan.toReserve);
      ref.invalidate(vaultOverviewProvider);
      messenger.showSnackBar(SnackBar(content: Text(l10n.lumpDeposited)));
    } on Object {
      AppLog.event('lump_sum_deposit_failed');
      messenger.showSnackBar(SnackBar(content: Text(l10n.genericError)));
    }
    if (mounted) setState(() => _busy = false);
  }

  @override
  Widget build(BuildContext context) {
    final l10n = context.l10n;
    final overview = ref.watch(vaultOverviewProvider);
    return Scaffold(
      appBar: AppBar(title: Text(l10n.lumpTitle)),
      body: switch (overview) {
        AsyncData(:final value) => _body(context, value),
        AsyncError() => Center(child: Text(l10n.genericError)),
        _ => const Center(child: CircularProgressIndicator()),
      },
    );
  }

  Widget _body(BuildContext context, VaultOverview o) {
    final l10n = context.l10n;
    final theme = Theme.of(context);
    final money = context.money;
    final base = o.household.baseCurrency;
    final currency = _currency ?? base;
    final foreign = currency != base;
    final inBase = _inBase(base);
    final missing = o.reserve.missing;
    final plan = inBase == null || missing == null
        ? null
        : splitLumpSum(inBase, missing);
    return ListView(
      padding: const EdgeInsets.fromLTRB(16, 8, 16, 32),
      children: [
        Text(l10n.lumpHint, style: theme.textTheme.bodyMedium),
        const SizedBox(height: 12),
        SegmentedButton<CurrencyCode>(
          showSelectedIcon: false,
          segments: [
            for (final c in {base, CurrencyCode.usd})
              ButtonSegment(
                value: c,
                label: Text(c.iso, key: Key('lump-cur-${c.name}')),
              ),
          ],
          selected: {currency},
          onSelectionChanged: (s) => setState(() {
            _currency = s.single;
            if (_amount?.currency != s.single) _amount = null;
          }),
        ),
        ListTile(
          key: const Key('lump-amount'),
          contentPadding: EdgeInsets.zero,
          title: Text(l10n.lumpAmount),
          subtitle: Text(_amount == null ? '—' : money(_amount!)),
          trailing: const Icon(Icons.edit_outlined),
          onTap: () => _pickAmount(currency),
        ),
        if (foreign)
          TextField(
            key: const Key('lump-rate'),
            controller: _rate,
            keyboardType: const TextInputType.numberWithOptions(decimal: true),
            decoration: InputDecoration(
              labelText: l10n.lumpRate(currency.iso),
            ),
            onChanged: (_) => setState(() {}),
          ),
        const SizedBox(height: 16),
        if (missing == null) ...[
          Text(l10n.lumpNoTarget, key: const Key('lump-no-target')),
          Align(
            alignment: Alignment.centerLeft,
            child: TextButton(
              key: const Key('lump-estimate'),
              onPressed: () => _estimate(base),
              child: Text(l10n.reserveEstimateAction),
            ),
          ),
        ] else if (plan != null)
          Card(
            key: const Key('lump-plan'),
            child: Padding(
              padding: const EdgeInsets.all(16),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Row(
                    children: [
                      const Icon(Icons.fort_outlined),
                      const SizedBox(width: 8),
                      Expanded(
                        child: Text(
                          plan.toReserve.isPositive
                              ? l10n.lumpReserve(money(plan.toReserve))
                              : l10n.lumpReserveFull,
                          key: const Key('lump-reserve'),
                          style: theme.textTheme.titleMedium,
                        ),
                      ),
                    ],
                  ),
                  if (plan.toReserve.isPositive) ...[
                    const SizedBox(height: 4),
                    Text(l10n.lumpWallNote),
                  ],
                  const SizedBox(height: 12),
                  Text(
                    l10n.lumpInvest(money(plan.toInvest)),
                    key: const Key('lump-invest'),
                  ),
                ],
              ),
            ),
          ),
        const SizedBox(height: 16),
        FilledButton.icon(
          key: const Key('lump-deposit'),
          icon: const Icon(Icons.fort_outlined),
          label: Text(l10n.lumpDeposit),
          onPressed: plan != null && plan.toReserve.isPositive && !_busy
              ? () => _deposit(plan)
              : null,
        ),
        const SizedBox(height: 8),
        OutlinedButton.icon(
          key: const Key('lump-ideas'),
          icon: const Icon(Icons.build_outlined),
          label: Text(l10n.lumpIdeas),
          onPressed: () => context.push(AppRoutes.ideaNew),
        ),
      ],
    );
  }
}
