import 'dart:async';

import 'package:baraka_daftari/app/router/app_router.dart';
import 'package:baraka_daftari/app/router/app_routes.dart';
import 'package:baraka_daftari/core/domain/enums.dart';
import 'package:baraka_daftari/core/money/money.dart';
import 'package:baraka_daftari/core/widget/widget_bridge.dart';
import 'package:baraka_daftari/features/audit/data/audit_providers.dart';
import 'package:baraka_daftari/features/budget/data/budget_providers.dart';
import 'package:baraka_daftari/features/expenses/data/expense_providers.dart';
import 'package:baraka_daftari/features/expenses/domain/expense.dart';
import 'package:baraka_daftari/features/expenses/presentation/expense_views.dart';
import 'package:baraka_daftari/features/household/data/household_providers.dart';
import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:mocktail/mocktail.dart';

import '../../helpers/pump_app.dart';

Money som(int major) => Money.major(major, CurrencyCode.uzs);

/// Ilovadagidek bosh sahifa ustiga ochiladi (saqlagach `pop` qaytaradi).
Future<void> go(WidgetTester tester, TestEnv env, String route) async {
  unawaited(env.container.read(appRouterProvider).push<void>(route));
  await tester.pumpAndSettle();
}

Future<void> typeAmount(WidgetTester tester, List<String> keys) async {
  for (final k in keys) {
    await tester.tap(find.byKey(Key('amount-key-$k')).last);
    await tester.pump();
  }
}

Future<ExpenseTemplate> seedTemplate(TestEnv env) async {
  final service = await env.container.read(expenseServiceProvider.future);
  final snacks = (await service.categories()).firstWhere(
    (c) => c.systemKey == CategoryKey.snacks,
  );
  final t = await service.addTemplate(
    title: 'Somsa',
    amount: som(8000),
    categoryId: snacks.meta.id,
  );
  env.container
    ..invalidate(expenseTemplatesProvider)
    ..invalidate(latestExpenseProvider);
  return t;
}

Future<List<Expense>> monthExpenses(TestEnv env) async =>
    (await env.container.read(expenseServiceProvider.future)).listIn(
      await (await env.container.read(
        ledgerServiceProvider.future,
      )).currentPeriod(),
    );

void main() {
  testWidgets('vidjet: qulfdan ochiq — summa koʻrinadi, qulfda — yashiriladi', (
    tester,
  ) async {
    final env = await pumpBarakaApp(tester);
    int inTwoMinutes() => env.clock
        .nowUtc()
        .add(const Duration(minutes: 2))
        .millisecondsSinceEpoch;
    // Qulf ochildi: hech qachon «cheksiz» emas — qulf vaqtigacha.
    verify(() => env.widget.setVisibleUntil(inTwoMinutes())).called(1);

    // Fonga: qulf vaqti (2 daqiqa) tugaguncha.
    env.clock.advance(const Duration(seconds: 30));
    sendToBackground(tester);
    verify(() => env.widget.setVisibleUntil(inTwoMinutes())).called(1);

    // Vaqt o'tdi — ilova qulflanadi va vidjet darhol yashiriladi.
    env.clock.advance(const Duration(minutes: 3));
    bringToForeground(tester);
    await tester.pumpAndSettle();
    verify(() => env.widget.setVisibleUntil(0)).called(1);
    expect(find.text('PIN kodni kiriting'), findsOneWidget);
  });

  testWidgets('vidjetda bosilgan shablon qulf ochilgach bazaga yoziladi', (
    tester,
  ) async {
    final env = await pumpBarakaApp(tester);
    final t = await seedTemplate(env);
    final at = DateTime.utc(2026, 10, 9, 7, 30);
    when(env.widget.takePending).thenAnswer(
      (_) async => [
        PendingWidgetExpense(
          templateId: t.meta.id,
          recordedAtMillis: at.millisecondsSinceEpoch,
        ),
        // O'chirilgan shablon — o'tkazib yuboriladi.
        PendingWidgetExpense(templateId: 'yoq', recordedAtMillis: 0),
      ],
    );
    sendToBackground(tester);
    bringToForeground(tester);
    await tester.pumpAndSettle();
    expect(find.text('Vidjetdan 1 ta xarajat yozildi'), findsOneWidget);
    final list = await monthExpenses(env);
    expect(list.single.amount, som(8000));
    expect(list.single.spentAt, at);
    expect(list.single.necessity, Necessity.havas);
    // Shablonlar vidjetga uzatilgan.
    verify(() => env.widget.setTemplates(any(), any())).called(greaterThan(0));
  });

  testWidgets('bosh ekran: shablon bir bosishda, «Bekor qilish» qaytaradi', (
    tester,
  ) async {
    final env = await pumpBarakaApp(tester);
    final t = await seedTemplate(env);
    await tester.pumpAndSettle();
    await tester.tap(find.byKey(Key('quick-${t.meta.id}')));
    await tester.pumpAndSettle();
    expect(find.textContaining('Somsa yozildi'), findsOneWidget);
    expect(await monthExpenses(env), hasLength(1));

    await tester.tap(find.byKey(const Key('quick-undo')));
    await tester.pumpAndSettle();
    expect(await monthExpenses(env), isEmpty);
  });

  testWidgets('xarajat: sadaqa — toifasiz izoh; qarzga havas — qizil bayroq', (
    tester,
  ) async {
    final env = await pumpBarakaApp(tester);
    await go(tester, env, AppRoutes.expenseNew);
    await tester.ensureVisible(find.byKey(const Key('category-sadaqa')));
    await tester.pumpAndSettle();
    await tester.tap(find.byKey(const Key('category-sadaqa')));
    await tester.pumpAndSettle();
    expect(find.byKey(const Key('necessity-sadaqa')), findsOneWidget);
    expect(find.byKey(const Key('necessity-selector')), findsNothing);

    await tester.ensureVisible(find.byKey(const Key('category-snacks')));
    await tester.pumpAndSettle();
    await tester.tap(find.byKey(const Key('category-snacks')));
    await tester.pumpAndSettle();
    final selector = tester.widget<SegmentedButton<Necessity>>(
      find.byKey(const Key('necessity-selector')),
    );
    expect(selector.selected, {Necessity.havas});
    expect(find.byKey(const Key('debt-havas-flag')), findsNothing);
    await tester.ensureVisible(find.byKey(const Key('flag-debt')));
    await tester.tap(find.byKey(const Key('flag-debt')));
    await tester.pumpAndSettle();
    expect(find.byKey(const Key('debt-havas-flag')), findsOneWidget);

    await typeAmount(tester, ['5', '0', '000']);
    await tester.tap(find.byKey(const Key('expense-save')));
    await tester.pumpAndSettle();
    final e = (await monthExpenses(env)).single;
    expect(e.fundedByDebt, isTrue);
    expect(e.necessity, Necessity.havas);
  });

  testWidgets('havas chegarasi: ikki katta rozi boʻlgach faol (PIN bilan)', (
    tester,
  ) async {
    final env = await pumpBarakaApp(tester);
    final households = await env.container.read(
      householdServiceProvider.future,
    );
    await households.members(ownerName: '');
    final wife = await households.addMember('Zuhra', MemberRole.adult);
    await (await env.container.read(
      memberPinServiceProvider.future,
    )).setPin(wife, '482915');

    await go(tester, env, AppRoutes.havas);
    expect(
      find.text('Havas uchun oylik chegara hali kelishilmagan.'),
      findsOneWidget,
    );
    await tester.tap(find.byKey(const Key('havas-propose')));
    await tester.pumpAndSettle();
    await typeAmount(tester, ['5', '0', '0', '000']);
    await tester.tap(find.byKey(const Key('amount-sheet-done')));
    await tester.pumpAndSettle();
    expect(find.byKey(const Key('havas-pending')), findsOneWidget);

    final overview = await env.container.read(havasOverviewProvider.future);
    final owner = overview.pending!.adults.firstWhere((m) => m.isOwner);
    await tester.tap(find.byKey(Key('consent-${owner.meta.id}')));
    await tester.pumpAndSettle();
    // Bitta katta yetmaydi.
    expect(find.byKey(const Key('havas-of-limit')), findsNothing);

    await tester.tap(find.byKey(Key('consent-${wife.meta.id}')));
    await tester.pumpAndSettle();
    await tester.enterText(find.byKey(const Key('member-pin-field')), '482915');
    await tester.pump();
    await tester.tap(find.byKey(const Key('member-pin-ok')));
    await tester.pumpAndSettle();
    expect(find.text('Chegara kelishildi — endi faol.'), findsOneWidget);
    expect(find.byKey(const Key('havas-of-limit')), findsOneWidget);
    expect(find.byKey(const Key('havas-level-ok')), findsOneWidget);
  });

  testWidgets('kategoriya toifasi oʻzgaradi va tarixda koʻrinadi', (
    tester,
  ) async {
    final env = await pumpBarakaApp(tester);
    await go(tester, env, AppRoutes.categories);
    final row = find.byKey(const Key('category-row-phone'));
    await tester.ensureVisible(row);
    await tester.tap(
      find.descendant(
        of: row,
        matching: find.byKey(const Key('necessity-zarur')),
      ),
    );
    await tester.pumpAndSettle();
    final phone = (await env.container.read(
      expenseCategoriesProvider.future,
    )).firstWhere((c) => c.systemKey == CategoryKey.phone);
    expect(phone.defaultNecessity, Necessity.zarur);

    await tester.tap(find.byKey(Key('history-${phone.meta.id}')));
    await tester.pumpAndSettle();
    expect(find.textContaining('Kerak → Zarur'), findsOneWidget);
  });

  testWidgets('ikki aʼzo boʻlsa toifani kim oʻzgartirgani soʻraladi', (
    tester,
  ) async {
    final env = await pumpBarakaApp(tester);
    final households = await env.container.read(
      householdServiceProvider.future,
    );
    await households.members(ownerName: '');
    final wife = await households.addMember('Zuhra', MemberRole.adult);
    await go(tester, env, AppRoutes.categories);
    final row = find.byKey(const Key('category-row-phone'));
    await tester.ensureVisible(row);
    await tester.tap(
      find.descendant(
        of: row,
        matching: find.byKey(const Key('necessity-havas')),
      ),
    );
    await tester.pumpAndSettle();
    expect(find.text('Kim oʻzgartiryapti?'), findsOneWidget);
    await tester.tap(find.byKey(Key('who-${wife.meta.id}')));
    await tester.pumpAndSettle();
    final phone = (await env.container.read(
      expenseCategoriesProvider.future,
    )).firstWhere((c) => c.systemKey == CategoryKey.phone);
    await tester.tap(find.byKey(Key('history-${phone.meta.id}')));
    await tester.pumpAndSettle();
    expect(find.textContaining('Kerak → Havas · Zuhra'), findsOneWidget);
  });
}
