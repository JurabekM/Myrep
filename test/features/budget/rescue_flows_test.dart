import 'dart:async';

import 'package:baraka_daftari/app/router/app_router.dart';
import 'package:baraka_daftari/app/router/app_routes.dart';
import 'package:baraka_daftari/core/domain/enums.dart';
import 'package:baraka_daftari/core/money/money.dart';
import 'package:baraka_daftari/features/budget/data/budget_providers.dart';
import 'package:baraka_daftari/features/envelopes/data/envelope_providers.dart';
import 'package:baraka_daftari/features/expenses/data/expense_providers.dart';
import 'package:baraka_daftari/features/subscriptions/data/subscription_providers.dart';
import 'package:baraka_daftari/features/vault/data/vault_providers.dart';
import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';

import '../../helpers/pump_app.dart';

Money som(int major) => Money.major(major, CurrencyCode.uzs);

Future<void> open(WidgetTester tester, TestEnv env, String route) async {
  unawaited(env.container.read(appRouterProvider).push<void>(route));
  await tester.pumpAndSettle();
}

Future<void> typeAmount(WidgetTester tester, List<String> keys) async {
  for (final k in keys) {
    await tester.tap(find.byKey(Key('amount-key-$k')).last);
    await tester.pump();
  }
}

DateTime tashkent(int y, int m, int d, [int h = 12]) =>
    DateTime.utc(y, m, d, h).subtract(const Duration(hours: 5));

void main() {
  testWidgets('obuna: qoʻshish → bekor qilish → yillik tejam', (tester) async {
    final env = await pumpBarakaApp(tester);
    await open(tester, env, AppRoutes.subscriptions);
    await tester.tap(find.byKey(const Key('subscription-add')));
    await tester.pumpAndSettle();
    await tester.enterText(find.byKey(const Key('subscription-title')), 'Kino');
    await tester.pump();
    await tester.tap(find.byKey(const Key('subscription-next')));
    await tester.pumpAndSettle();
    await typeAmount(tester, ['4', '9', '000']);
    await tester.tap(find.byKey(const Key('amount-sheet-done')));
    await tester.pumpAndSettle();
    expect(
      find.text('Faol obunalar yiliga: 588 000 soʻm'),
      findsOneWidget,
    );

    final s = (await env.container.read(subscriptionsProvider.future)).single;
    await tester.tap(find.byKey(Key('subscription-cancel-${s.meta.id}')));
    await tester.pumpAndSettle();
    expect(find.textContaining('Yiliga 588'), findsOneWidget);
    await tester.tap(find.byKey(const Key('subscription-cancel-ok')));
    await tester.pumpAndSettle();
    expect(
      find.byKey(Key('subscription-cancelled-${s.meta.id}')),
      findsOneWidget,
    );
    expect(find.text('Faol obunalar yiliga: 0 soʻm'), findsOneWidget);
  });

  testWidgets('naqd konvert: ochish, keyingi haftada qoldiqni kiritish', (
    tester,
  ) async {
    final env = await pumpBarakaApp(tester);
    await open(tester, env, AppRoutes.envelopes);
    await tester.tap(find.byKey(const Key('envelope-add')));
    await tester.pumpAndSettle();
    await tester.enterText(find.byKey(const Key('envelope-title')), 'Bozor');
    await tester.pump();
    await tester.tap(find.byKey(const Key('envelope-cat-groceries')));
    await tester.pump();
    await tester.tap(find.byKey(const Key('envelope-next')));
    await tester.pumpAndSettle();
    await typeAmount(tester, ['2', '0', '0', '000']);
    await tester.tap(find.byKey(const Key('amount-sheet-done')));
    await tester.pumpAndSettle();
    expect(find.textContaining('Bu hafta konvertga 200'), findsOneWidget);

    // Karta bilan xarajat ham konvertdan ayiriladi.
    final expenses = await env.container.read(expenseServiceProvider.future);
    final groceries = (await expenses.categories()).firstWhere(
      (c) => c.systemKey == CategoryKey.groceries,
    );
    await expenses.add(
      amount: som(50000),
      categoryId: groceries.meta.id,
      channel: PaymentChannel.card,
    );
    env.container.invalidate(envelopeStatusProvider);
    await tester.pumpAndSettle();
    expect(find.textContaining('qoldi 150'), findsOneWidget);

    // Keyingi hafta: oʻtgan hafta qoldigʻi soʻraladi.
    env.clock.setNow(tashkent(2026, 10, 17));
    env.container.invalidate(envelopeStatusProvider);
    await tester.pumpAndSettle();
    final pending = find.byWidgetPredicate(
      (w) =>
          w.key is ValueKey<String> &&
          (w.key! as ValueKey<String>).value.startsWith('envelope-close-'),
    );
    expect(pending, findsOneWidget);
    await tester.tap(pending);
    await tester.pumpAndSettle();
    await typeAmount(tester, ['1', '2', '0', '000']);
    await tester.tap(find.byKey(const Key('amount-sheet-done')));
    await tester.pumpAndSettle();
    expect(find.textContaining('Qoldiq 120'), findsOneWidget);
    expect(pending, findsNothing);
    final o = await env.container.read(rescueOverviewProvider.future);
    expect(o.week.envelopes, som(120000));
  });

  testWidgets('bosh ekran: «Bu hafta qutqarildi» → Kelajagimga oʻtkazish', (
    tester,
  ) async {
    final env = await pumpBarakaApp(tester);
    final subs = await env.container.read(subscriptionServiceProvider.future);
    final s = await subs.add(title: 'Musiqa', price: som(30000));
    await subs.cancel(s);
    env.clock.advance(const Duration(days: 2));
    env.container.invalidate(rescueOverviewProvider);
    await tester.pumpAndSettle();

    // 1 000 soʻm/kun × 3 kun.
    expect(find.textContaining('Bu hafta qutqarildi: 3'), findsOneWidget);
    await tester.scrollUntilVisible(
      find.byKey(const Key('home-rescue-transfer')),
      100,
      scrollable: find.byType(Scrollable).first,
    );
    await tester.ensureVisible(find.byKey(const Key('home-rescue-transfer')));
    await tester.pumpAndSettle();
    await tester.tap(find.byKey(const Key('home-rescue-transfer')));
    await tester.pumpAndSettle();
    expect(find.textContaining('Kelajagimga oʻtkazildi'), findsOneWidget);
    final vault = await env.container.read(vaultServiceProvider.future);
    expect((await vault.overview()).balance, som(3000));
    expect(find.byKey(const Key('home-rescue-transfer')), findsNothing);
  });
}
