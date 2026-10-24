import 'package:baraka_daftari/app/l10n/l10n.dart';
import 'package:baraka_daftari/app/router/app_routes.dart';
import 'package:baraka_daftari/app/widgets/money_input.dart';
import 'package:baraka_daftari/core/money/money.dart';
import 'package:baraka_daftari/features/prices/data/price_providers.dart';
import 'package:baraka_daftari/features/prices/domain/price_book_service.dart';
import 'package:baraka_daftari/features/prices/domain/price_math.dart';
import 'package:baraka_daftari/features/prices/presentation/prices_screen.dart';
import 'package:baraka_daftari/features/vault/data/vault_providers.dart';
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';

/// Mingdan birlarni «15» / «7,69» ko'rinishiga.
String milliLabel(int milli) {
  final whole = milli ~/ 1000;
  final hundredths = (milli % 1000) ~/ 10;
  if (hundredths == 0) return '$whole';
  final frac = hundredths
      .toString()
      .padLeft(2, '0')
      .replaceAll(
        RegExp(r'0$'),
        '',
      );
  return '$whole,$frac';
}

/// Taqqoslash uchun mahsulot: oylik og'irligi eng katta va narxi ma'lum.
ItemHistory? referenceItem(List<ItemHistory> items) {
  ItemHistory? best;
  for (final h in items) {
    if (h.last == null) continue;
    if (best == null ||
        h.item.monthlyQuantityMilli * h.last!.price.minorUnits >
            best.item.monthlyQuantityMilli * best.last!.price.minorUnits) {
      best = h;
    }
  }
  return best;
}

/// «Inflyatsiya taʼsiri» (SPEC 2C.2): yotgan pulning real qiymati. Har doim
/// keyingi qadam bilan tugaydi.
class MouseScreen extends ConsumerWidget {
  const MouseScreen({super.key});

  static const _years = 3;

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final l10n = context.l10n;
    final theme = Theme.of(context);
    final money = context.money;
    final vault = ref.watch(vaultOverviewProvider).valueOrNull;
    final book = ref.watch(priceBookProvider).valueOrNull;
    if (vault == null || book == null) {
      return Scaffold(
        appBar: AppBar(title: Text(l10n.mouseTitle)),
        body: const Center(child: CircularProgressIndicator()),
      );
    }
    final balance = vault.reserveBalance;
    final ref0 = referenceItem(book.items);
    final today = book.today;
    final yearAgo = today.plusDays(-365);
    Money? priceYearAgo;
    if (ref0 != null) priceYearAgo = priceAt(ref0.observations, yearAgo);
    final rate = book.yearInflationBp;
    return Scaffold(
      appBar: AppBar(title: Text(l10n.mouseTitle)),
      body: ListView(
        padding: const EdgeInsets.fromLTRB(16, 8, 16, 32),
        children: [
          Text(l10n.mouseHint),
          const SizedBox(height: 12),
          Card(
            child: Padding(
              padding: const EdgeInsets.all(16),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text(
                    l10n.mouseBalance(money(balance)),
                    style: theme.textTheme.titleMedium,
                  ),
                  const SizedBox(height: 8),
                  if (ref0 == null)
                    Text(l10n.mouseNoPrices, key: const Key('mouse-no-prices'))
                  else ...[
                    Text(
                      l10n.mouseToday(
                        milliLabel(purchasableMilli(balance, ref0.last!.price)),
                        ref0.item.unit,
                        ref0.item.name,
                      ),
                      key: const Key('mouse-today'),
                      style: theme.textTheme.titleSmall,
                    ),
                    if (priceYearAgo != null)
                      Text(
                        l10n.mouseYearAgo(
                          milliLabel(purchasableMilli(balance, priceYearAgo)),
                          ref0.item.unit,
                        ),
                        key: const Key('mouse-year-ago'),
                      ),
                    if (rate != null && rate > 0)
                      Text(
                        l10n.mouseFuture(
                          signedPercent(rate),
                          _years,
                          milliLabel(
                            purchasableMilli(
                              balance,
                              projectPrice(ref0.last!.price, rate, _years),
                            ),
                          ),
                          ref0.item.unit,
                        ),
                        key: const Key('mouse-future'),
                      ),
                  ],
                ],
              ),
            ),
          ),
          const SizedBox(height: 12),
          Card(
            color: theme.colorScheme.primaryContainer,
            child: Padding(
              padding: const EdgeInsets.all(16),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text(
                    vault.reserve.isFull
                        ? l10n.mouseNextGrowth
                        : l10n.mouseNextReserve,
                    key: const Key('mouse-next'),
                  ),
                  Align(
                    alignment: Alignment.centerRight,
                    child: TextButton(
                      onPressed: () => context.canPop()
                          ? context.pop()
                          : context.go(AppRoutes.vault),
                      child: Text(l10n.mouseOpenVault),
                    ),
                  ),
                ],
              ),
            ),
          ),
          if (ref0 == null)
            TextButton(
              onPressed: () => context.push(AppRoutes.prices),
              child: Text(l10n.pricesTitle),
            ),
        ],
      ),
    );
  }
}
