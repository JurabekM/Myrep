import 'package:baraka_daftari/app/l10n/l10n.dart';
import 'package:baraka_daftari/app/widgets/labels.dart';
import 'package:baraka_daftari/app/widgets/money_input.dart';
import 'package:baraka_daftari/core/money/money.dart';
import 'package:baraka_daftari/core/time/calendar.dart';
import 'package:baraka_daftari/features/audit/data/audit_providers.dart';
import 'package:baraka_daftari/features/audit/domain/month_ledger.dart';
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:riverpod_annotation/riverpod_annotation.dart';

part 'whose_money_screen.g.dart';

typedef WhoseData = ({
  DateRange period,
  Money income,
  Map<MoneyOwner, Money> parts,
});

/// [offset] — joriy oydan necha oy oldin (0 — shu oy).
@riverpod
Future<WhoseData> whoseMoneyData(Ref ref, int offset) async {
  final ledger = await ref.watch(ledgerServiceProvider.future);
  var period = await ledger.currentPeriod();
  for (var i = 0; i < offset; i++) {
    period = await ledger.previousPeriodOf(period);
  }
  final l = await ledger.ledgerFor(period);
  return (
    period: period,
    income: l.income,
    parts: whoseMoney(l, await ledger.categoryKeys()),
  );
}

/// Ranglar (SPEC 9: iliq, «daftar» palitrasi). «O'zingizniki» — asosiy yashil;
/// isrof uchun qizil ishlatilmaydi.
Color ownerColor(MoneyOwner o, ColorScheme s) => switch (o) {
  MoneyOwner.landlord => const Color(0xFF8D6E63),
  MoneyOwner.bank => const Color(0xFF5C6B8A),
  MoneyOwner.shop => const Color(0xFFC08A3E),
  MoneyOwner.utilities => const Color(0xFF6E8B74),
  MoneyOwner.fuel => const Color(0xFF9C7B54),
  MoneyOwner.self => s.primary,
  MoneyOwner.sadaqa => const Color(0xFF4F8A8B),
  MoneyOwner.other => const Color(0xFFA39E93),
  MoneyOwner.unexplained => const Color(0xFFD8CFBC),
};

/// «Kimning puli?» (SPEC 2.4): oylik daromad egalarga bo'lib ko'rsatiladi.
class WhoseMoneyScreen extends ConsumerStatefulWidget {
  const WhoseMoneyScreen({super.key});

  @override
  ConsumerState<WhoseMoneyScreen> createState() => _WhoseMoneyScreenState();
}

class _WhoseMoneyScreenState extends ConsumerState<WhoseMoneyScreen> {
  int _offset = 0;

  @override
  Widget build(BuildContext context) {
    final l10n = context.l10n;
    final data = ref.watch(whoseMoneyDataProvider(_offset));
    return Scaffold(
      appBar: AppBar(
        title: Text(l10n.sectionWhoseMoney),
        actions: [
          IconButton(
            key: const Key('whose-prev'),
            tooltip: l10n.back,
            icon: const Icon(Icons.chevron_left),
            onPressed: () => setState(() => _offset++),
          ),
          IconButton(
            key: const Key('whose-next'),
            tooltip: l10n.next,
            icon: const Icon(Icons.chevron_right),
            onPressed: _offset == 0 ? null : () => setState(() => _offset--),
          ),
        ],
      ),
      body: switch (data) {
        AsyncError() => Center(child: Text(l10n.genericError)),
        AsyncData(:final value) => _body(context, value),
        _ => const Center(child: CircularProgressIndicator()),
      },
    );
  }

  Widget _body(BuildContext context, WhoseData d) {
    final l10n = context.l10n;
    final theme = Theme.of(context);
    final total = d.parts.values.fold(0, (a, m) => a + m.minorUnits);
    return Center(
      child: ConstrainedBox(
        constraints: const BoxConstraints(maxWidth: 620),
        child: ListView(
          padding: const EdgeInsets.all(16),
          children: [
            Text(
              l10n.whoseIntro(periodLabel(context, d.period)),
              style: theme.textTheme.titleMedium,
            ),
            const SizedBox(height: 4),
            Text(
              '${l10n.auditIncome}: ${context.money(d.income)}',
              key: const Key('whose-income'),
            ),
            if (total > d.income.minorUnits && d.income.isPositive ||
                total > 0 && !d.income.isPositive) ...[
              const SizedBox(height: 4),
              Text(
                l10n.homeMonthResultMinus,
                key: const Key('whose-over'),
                style: TextStyle(color: theme.colorScheme.onSurfaceVariant),
              ),
            ],
            const SizedBox(height: 16),
            if (total == 0)
              Text(l10n.whoseEmpty)
            else ...[
              // Gorizontal bo'lak-diagramma.
              ClipRRect(
                borderRadius: BorderRadius.circular(8),
                child: SizedBox(
                  key: const Key('whose-bar'),
                  height: 28,
                  child: Row(
                    // Bo'laklar bolasiz — balandlik bo'yicha cho'zilmasa
                    // ko'rinmaydi (qurilmada topilgan xato).
                    crossAxisAlignment: CrossAxisAlignment.stretch,
                    children: [
                      for (final MapEntry(key: o, value: m) in d.parts.entries)
                        Expanded(
                          // Har bo'lak kamida ko'rinadigan bo'lsin.
                          flex: (m.minorUnits * 1000 ~/ total).clamp(8, 1000),
                          child: Tooltip(
                            message: l10n.owner(o),
                            child: ColoredBox(
                              color: ownerColor(o, theme.colorScheme),
                            ),
                          ),
                        ),
                    ],
                  ),
                ),
              ),
              const SizedBox(height: 16),
              for (final MapEntry(key: o, value: m) in d.parts.entries)
                ListTile(
                  key: Key('owner-${o.name}'),
                  contentPadding: EdgeInsets.zero,
                  leading: Container(
                    width: 14,
                    height: 14,
                    decoration: BoxDecoration(
                      color: ownerColor(o, theme.colorScheme),
                      borderRadius: BorderRadius.circular(3),
                    ),
                  ),
                  title: Text(
                    l10n.owner(o),
                    style: o == MoneyOwner.self
                        ? const TextStyle(fontWeight: FontWeight.w600)
                        : null,
                  ),
                  subtitle: Text(
                    l10n.whosePercent(ratioPercent(m.minorUnits, total)),
                  ),
                  trailing: Text(context.money(m)),
                ),
            ],
          ],
        ),
      ),
    );
  }
}
