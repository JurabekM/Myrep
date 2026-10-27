import 'package:baraka_daftari/app/router/app_router.dart';
import 'package:baraka_daftari/app/router/app_routes.dart';
import 'package:baraka_daftari/core/domain/enums.dart';
import 'package:baraka_daftari/core/money/money.dart';
import 'package:baraka_daftari/core/money/money_format.dart';
import 'package:baraka_daftari/core/notifications/reminder_api.pigeon.dart';
import 'package:baraka_daftari/features/audit/data/audit_providers.dart';
import 'package:baraka_daftari/features/expenses/data/expense_providers.dart';
import 'package:baraka_daftari/features/household/data/household_providers.dart';
import 'package:baraka_daftari/features/obligations/data/obligation_providers.dart';
import 'package:baraka_daftari/features/vault/data/vault_providers.dart';
import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:mocktail/mocktail.dart';

import '../../helpers/pump_app.dart';

Money som(int major) => Money.major(major, CurrencyCode.uzs);
String m(String s) => s.replaceAll(' ', nbsp);

Future<void> go(WidgetTester tester, TestEnv env, String route) async {
  env.container.read(appRouterProvider).go(route);
  await tester.pumpAndSettle();
}

Future<void> typeAmount(WidgetTester tester, List<String> keys) async {
  for (final k in keys) {
    await tester.tap(find.byKey(Key('amount-key-$k')).last);
    await tester.pump();
  }
}

/// Maʼlumotni xizmatlar orqali (test zonasida, `runAsyncʼsiz) kiritadi.
Future<void> seedMonth(TestEnv env) async {
  final c = env.container;
  final income = await (await c.read(incomeServiceProvider.future)).add(
    amount: som(8000000),
    source: IncomeSource.salary,
    channel: PaymentChannel.card,
  );
  final vault = await c.read(vaultServiceProvider.future);
  await vault.allocateFromIncome(income, som(800000));
  await vault.setInitialBalance(som(2000000));
  final expenses = await c.read(expenseServiceProvider.future);
  final groceries = (await expenses.categories()).firstWhere(
    (x) => x.systemKey == CategoryKey.groceries,
  );
  await expenses.add(
    amount: som(1500000),
    categoryId: groceries.meta.id,
    channel: PaymentChannel.cash,
  );
  await (await c.read(obligationServiceProvider.future)).addObligation(
    title: 'Ijara',
    kind: ObligationKind.rent,
    amount: som(3000000),
    dayOfMonth: 25,
  );
}

void main() {
  testWidgets('bosh ekran KPIʼlari repository maʼlumotlariga mos', (
    tester,
  ) async {
    final env = await pumpBarakaApp(tester);
    await seedMonth(env);
    env.container.invalidate(homeKpisProvider);
    await tester.pumpAndSettle();

    // Repositoryʼdan toʻgʻridan-toʻgʻri hisob.
    final kpis = await (await env.container.read(
      ledgerServiceProvider.future,
    )).homeKpis();
    expect(kpis.paidToSelf, som(800000));
    expect(kpis.vaultBalance, som(2800000));
    expect(kpis.monthResult, som(2700000));

    // Ekranda aynan shu qiymatlar.
    String text(String key) =>
        tester.widget<Text>(find.byKey(Key(key))).data ?? '';
    expect(text('kpi-paid-to-self'), m('800 000 soʻm'));
    expect(find.text(m('2 800 000 soʻm')), findsOneWidget);
    expect(find.text(m('+2 700 000 soʻm')), findsOneWidget);
    expect(find.text('1 hafta ketma-ket'), findsOneWidget);
    // Oʻtgan oy auditi hali oʻtkazilmagan.
    expect(find.textContaining('oylik audit'), findsOneWidget);
  });

  testWidgets('xarajat kiritish: kategoriya + summa', (tester) async {
    final env = await pumpBarakaApp(tester);
    await tester.tap(find.byKey(const Key('home-add-expense')));
    await tester.pumpAndSettle();
    FilledButton save() =>
        tester.widget<FilledButton>(find.byKey(const Key('expense-save')));
    await typeAmount(tester, ['4', '5', '000']);
    expect(save().onPressed, isNull, reason: 'kategoriya tanlanmagan');
    await tester.tap(find.byKey(const Key('category-groceries')));
    await tester.pump();
    await tester.tap(find.byKey(const Key('expense-save')));
    await tester.pumpAndSettle();

    final list =
        await (await env.container.read(
          expenseServiceProvider.future,
        )).listIn(
          await (await env.container.read(
            ledgerServiceProvider.future,
          )).currentPeriod(),
        );
    expect(list.single.amount, som(45000));
    // Toifa kategoriyadan avtomatik (oziq-ovqat — zarur).
    expect(list.single.necessity, Necessity.zarur);
    expect(find.text(m('+−45 000 soʻm')), findsNothing);
    expect(find.text(m('−45 000 soʻm')), findsOneWidget); // oy yakuni
  });

  testWidgets('majburiyat qoʻshilganda eslatma summasiz sinxronlanadi', (
    tester,
  ) async {
    final env = await pumpBarakaApp(tester);
    await go(tester, env, AppRoutes.obligations);
    await tester.tap(find.byKey(const Key('obligation-add')));
    await tester.pumpAndSettle();
    await tester.enterText(find.byKey(const Key('obligation-title')), 'Ijara');
    await tester.pump();
    await tester.tap(find.byKey(const Key('obligation-amount')));
    await tester.pumpAndSettle();
    await typeAmount(tester, ['3', '000', '000']);
    await tester.tap(find.byKey(const Key('amount-sheet-done')));
    await tester.pumpAndSettle();
    await tester.tap(find.byKey(const Key('obligation-save')));
    await tester.pumpAndSettle();

    expect(find.text('Ijara'), findsOneWidget);
    expect(find.textContaining(m('3 000 000 soʻm')), findsWidgets);
    final captured = verify(
      () => env.reminders.sync(captureAny(), captureAny()),
    ).captured;
    final reminders = captured[captured.length - 2] as List<ObligationReminder>;
    expect(reminders.single.dayOfMonth, 1);
    expect(reminders.single.title, 'Ertaga toʻlov: Ijara');
    expect(reminders.single.body, isNot(contains('000')));
    expect(captured.last, 'Toʻlov eslatmalari');
  });

  testWidgets('bildirishnoma oʻchiq boʻlsa ogohlantirish chiqadi', (
    tester,
  ) async {
    final env = await pumpBarakaApp(
      tester,
      reminderApi: stubbedReminderApi(enabled: false),
    );
    await go(tester, env, AppRoutes.obligations);
    expect(find.byKey(const Key('notifications-off')), findsOneWidget);

    // Regressiya (qurilmada topilgan): tizim oynasida ruxsat berilib,
    // ilovaga qaytilganda ogohlantirish yoʻqolishi kerak.
    when(env.reminders.areNotificationsEnabled).thenAnswer((_) async => true);
    sendToBackground(tester);
    bringToForeground(tester);
    await tester.pumpAndSettle();
    expect(find.byKey(const Key('notifications-off')), findsNothing);
  });

  testWidgets('nasiya: qoʻshish va qisman toʻlash', (tester) async {
    final env = await pumpBarakaApp(tester);
    await go(tester, env, AppRoutes.nasiya);
    await tester.tap(find.byKey(const Key('nasiya-add')));
    await tester.pumpAndSettle();
    await tester.enterText(find.byKey(const Key('nasiya-name')), 'Akmal aka');
    await tester.pump();
    await tester.tap(find.byKey(const Key('nasiya-amount')));
    await tester.pumpAndSettle();
    await typeAmount(tester, ['4', '5', '0', '000']);
    await tester.tap(find.byKey(const Key('amount-sheet-done')));
    await tester.pumpAndSettle();
    await tester.tap(find.byKey(const Key('nasiya-save')));
    await tester.pumpAndSettle();
    expect(find.text('Jami nasiya: ${m("450 000 soʻm")}'), findsOneWidget);

    final debt = (await (await env.container.read(
      obligationServiceProvider.future,
    )).nasiya()).single;
    await tester.tap(find.byKey(Key('nasiya-pay-${debt.meta.id}')));
    await tester.pumpAndSettle();
    // Taklif qoldiqdan boshlanadi; 150 000 kiritamiz.
    for (var i = 0; i < 6; i++) {
      await tester.tap(find.byKey(const Key('amount-key-back')).last);
      await tester.pump();
    }
    await typeAmount(tester, ['1', '5', '0', '000']);
    await tester.tap(find.byKey(const Key('amount-sheet-done')));
    await tester.pumpAndSettle();
    expect(find.text('Jami nasiya: ${m("300 000 soʻm")}'), findsOneWidget);
  });

  testWidgets('oylik audit: izohsizni belgilash va yakunlash', (tester) async {
    final env = await pumpBarakaApp(tester);
    final ledger = await env.container.read(ledgerServiceProvider.future);
    final prev = await ledger.previousPeriod();
    await (await env.container.read(incomeServiceProvider.future)).add(
      amount: som(4000000),
      source: IncomeSource.dailyWork,
      channel: PaymentChannel.cash,
      receivedAt: ledger.instantInside(prev),
    );
    env.container.read(appRouterProvider).go(AppRoutes.home);
    await tester.pumpAndSettle();
    await tapNav(tester, AppRoutes.audit);
    await tester.pumpAndSettle();
    expect(find.text(m('4 000 000 soʻm')), findsOneWidget);

    // 3-qadam: oziq-ovqatga 1 000 000 qoʻshamiz.
    await tester.tap(find.byKey(const Key('audit-next')));
    await tester.pumpAndSettle();
    await tester.tap(find.byKey(const Key('audit-next')));
    await tester.pumpAndSettle();
    await tester.tap(
      find.descendant(
        of: find.byKey(const Key('audit-cat-groceries')),
        matching: find.byType(IconButton),
      ),
    );
    await tester.pumpAndSettle();
    await typeAmount(tester, ['1', '000', '000']);
    await tester.tap(find.byKey(const Key('amount-sheet-done')));
    await tester.pumpAndSettle();

    await tester.tap(find.byKey(const Key('audit-next')));
    await tester.pumpAndSettle();
    expect(
      tester.widget<Text>(find.byKey(const Key('audit-unexplained'))).data,
      m('3 000 000 soʻm'),
    );
    await tester.tap(find.byKey(const Key('audit-mark-small')));
    await tester.pumpAndSettle();
    expect(
      tester.widget<Text>(find.byKey(const Key('audit-unexplained'))).data,
      m('0 soʻm'),
    );
    await tester.tap(find.byKey(const Key('audit-finish')));
    await tester.pumpAndSettle();

    final report = await ledger.reportFor(prev);
    expect(report, isNotNull);
    expect(report!.expenses, som(4000000));
    await tester.scrollUntilVisible(
      find.textContaining('Oxirgi audit'),
      -200,
      scrollable: find.byType(Scrollable).first,
    );
    expect(find.textContaining('Oxirgi audit'), findsOneWidget);
  });

  testWidgets('«Kimning puli?» — egalar va foizlar', (tester) async {
    final env = await pumpBarakaApp(tester);
    await seedMonth(env);
    await go(tester, env, AppRoutes.whoseMoney);
    expect(find.byKey(const Key('whose-bar')), findsOneWidget);
    // Regressiya: boʻlaklar haqiqatan koʻrinadi (balandligi 0 emas).
    final segments = find.descendant(
      of: find.byKey(const Key('whose-bar')),
      matching: find.byType(ColoredBox),
    );
    expect(segments, findsWidgets);
    for (final e in segments.evaluate()) {
      expect(tester.getSize(find.byWidget(e.widget)).height, 28);
    }
    expect(find.byKey(const Key('whose-over')), findsNothing);
    expect(find.byKey(const Key('owner-landlord')), findsOneWidget);
    expect(find.byKey(const Key('owner-self')), findsOneWidget);
    expect(find.byKey(const Key('owner-shop')), findsOneWidget);
    expect(find.byKey(const Key('owner-unexplained')), findsOneWidget);
    // Ijara 3 000 000 / 8 000 000 = 37,5 %.
    expect(find.text('37,5 %'), findsOneWidget);
    expect(find.text('10 %'), findsOneWidget); // oʻzingiz: 800 000
    await tester.tap(find.byKey(const Key('whose-prev')));
    await tester.pumpAndSettle();
    expect(find.text('Bu oy uchun hali maʼlumot yoʻq.'), findsOneWidget);
  });

  testWidgets('oila aʼzolari: qoʻshilgach daromadda «Kim?» tanlovi', (
    tester,
  ) async {
    final env = await pumpBarakaApp(tester);
    await go(tester, env, AppRoutes.incomeNew);
    expect(find.text('Kim'), findsNothing, reason: 'bitta aʼzo — tanlov yoʻq');
    await go(tester, env, AppRoutes.members);
    expect(find.text('Men'), findsOneWidget);
    await tester.tap(find.byKey(const Key('member-add')));
    await tester.pumpAndSettle();
    await tester.enterText(find.byKey(const Key('member-name')), 'Gulnora');
    await tester.pump();
    await tester.tap(find.byKey(const Key('member-save')));
    await tester.pumpAndSettle();
    expect(find.text('Gulnora'), findsOneWidget);

    await go(tester, env, AppRoutes.incomeNew);
    expect(find.text('Kim'), findsOneWidget);
    final members = await (await env.container.read(
      householdServiceProvider.future,
    )).members(ownerName: '');
    await tester.tap(find.byKey(Key('member-${members.last.meta.id}')));
    await tester.pump();
    await typeAmount(tester, ['5', '000']);
    await tester.tap(find.byKey(const Key('income-save')));
    await tester.pumpAndSettle();
    final income = await (await env.container.read(
      incomeServiceProvider.future,
    )).defaults();
    expect(income.recentAmounts.single, som(5000));
  });

  testWidgets('sozlamalar: oylik kuni', (tester) async {
    final env = await pumpBarakaApp(tester);
    await go(tester, env, AppRoutes.settings);
    expect(
      find.text('Oylik davr shu kundan boshlanadi: 1-sana'),
      findsOneWidget,
    );
    await tester.tap(find.byType(DropdownButton<int>));
    await tester.pumpAndSettle();
    await tester.tap(find.text('10').last);
    await tester.pumpAndSettle();
    expect(
      find.text('Oylik davr shu kundan boshlanadi: 10-sana'),
      findsOneWidget,
    );
    final period = await (await env.container.read(
      ledgerServiceProvider.future,
    )).currentPeriod();
    expect(period.start.day, 10);
  });
}
