import 'package:baraka_daftari/features/audit/data/audit_providers.dart';
import 'package:baraka_daftari/features/budget/data/budget_providers.dart';
import 'package:baraka_daftari/features/debts/data/debt_providers.dart';
import 'package:baraka_daftari/features/envelopes/data/envelope_providers.dart';
import 'package:baraka_daftari/features/expenses/presentation/expense_views.dart';
import 'package:baraka_daftari/features/household/presentation/member_views.dart';
import 'package:baraka_daftari/features/obligations/presentation/obligation_views.dart';
import 'package:baraka_daftari/features/prices/data/price_providers.dart';
import 'package:baraka_daftari/features/subscriptions/data/subscription_providers.dart';
import 'package:baraka_daftari/features/vault/data/vault_providers.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

/// Pul yozuvlari o'zgargach barcha ko'rinishlarni yangilash.
void refreshMoneyViews(WidgetRef ref) {
  ref
    ..invalidate(homeKpisProvider)
    ..invalidate(vaultOverviewProvider)
    ..invalidate(monthExpensesProvider)
    ..invalidate(latestExpenseProvider)
    ..invalidate(expenseTemplatesProvider)
    ..invalidate(havasOverviewProvider)
    ..invalidate(spendingInsightsProvider)
    ..invalidate(habitStatsProvider)
    ..invalidate(treatsProvider)
    ..invalidate(subscriptionsProvider)
    ..invalidate(envelopeStatusProvider)
    ..invalidate(rescueOverviewProvider)
    ..invalidate(priceBookProvider)
    ..invalidate(debtOverviewProvider)
    ..invalidate(recoveryStateProvider)
    ..invalidate(sellablesProvider)
    ..invalidate(obligationsListProvider)
    ..invalidate(nasiyaListProvider)
    ..invalidate(membersProvider);
}
