import 'dart:async';

import 'package:baraka_daftari/app/router/app_router.dart';
import 'package:baraka_daftari/app/router/app_routes.dart';
import 'package:baraka_daftari/core/domain/enums.dart';
import 'package:baraka_daftari/core/money/money.dart';
import 'package:baraka_daftari/core/time/calendar.dart';
import 'package:baraka_daftari/features/debts/data/debt_providers.dart';
import 'package:baraka_daftari/features/debts/domain/debt_math.dart';
import 'package:baraka_daftari/features/debts/domain/debt_service.dart';
import 'package:baraka_daftari/features/household/data/drift_household_repository.dart';
import 'package:baraka_daftari/features/vault/data/vault_providers.dart';
import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';

import '../../helpers/pump_app.dart';

const nbsp = ' ';
String n(String s) => s.replaceAll(' ', nbsp);
Money som(int major) => Money.major(major, CurrencyCode.uzs);

Future<void> open(WidgetTester tester, TestEnv env, String route) async {
  // Ma'lumot servislar orqali to'g'ridan-to'g'ri yozilgan — ekranlar
  // (bosh ekran ostida tirik) eski holatni ushlab turmasin.
  env.container
    ..invalidate(debtOverviewProvider)
    ..invalidate(recoveryStateProvider)
    ..invalidate(sellablesProvider);
  unawaited(env.container.read(appRouterProvider).push<void>(route));
  await tester.pumpAndSettle();
}

Future<void> reveal(WidgetTester tester, Finder f) async {
  await tester.scrollUntilVisible(
    f,
    200,
    scrollable: find.byType(Scrollable).first,
  );
  await tester.ensureVisible(f);
  await tester.pumpAndSettle();
}

Future<void> tapIn(WidgetTester tester, Finder f) async {
  await reveal(tester, f);
  await tester.tap(f);
  await tester.pumpAndSettle();
}

/// Akmal: avtokredit 39 mln, 14 oy, 24 %; daromad oyiga 10 mln.
Future<DebtView> seedAkmal(TestEnv env, {bool income = true}) async {
  if (income) {
    final incomes = await env.container.read(incomeServiceProvider.future);
    for (final m in [7, 8, 9]) {
      await incomes.add(
        amount: som(10000000),
        source: IncomeSource.salary,
        channel: PaymentChannel.card,
        receivedAt: DateTime.utc(2026, m, 5, 7),
      );
    }
  }
  final debts = await env.container.read(debtServiceProvider.future);
  return debts.add(
    creditorType: CreditorType.bank,
    creditorName: 'Avtokredit',
    principal: som(39000000),
    scheduleType: DebtScheduleType.annuity,
    termMonths: 14,
    annualRateBp: 2400,
  );
}

void main() {
  testWidgets('rejim: jamgʻarmani 0 qilib boʻlmaydi, 70/20/10 yoqiladi', (
    tester,
  ) async {
    final env = await pumpBarakaApp(tester);
    await seedAkmal(env);
    await open(tester, env, AppRoutes.debts);
    await tapIn(tester, find.byKey(const Key('recovery-open')));

    FilledButton save() =>
        tester.widget<FilledButton>(find.byKey(const Key('recovery-save')));
    await tester.enterText(find.byKey(const Key('recovery-savings')), '0');
    await tester.enterText(find.byKey(const Key('recovery-needs')), '80');
    await tester.pump();
    expect(
      find.byKey(const Key('recovery-savings-error')),
      findsOneWidget,
      reason: '«Kelajagim» 0 — toʻxtatiladi',
    );
    await reveal(tester, find.byKey(const Key('recovery-save')));
    expect(save().onPressed, isNull);

    await tapIn(tester, find.byKey(const Key('recovery-standard')));
    expect(find.byKey(const Key('recovery-savings-error')), findsNothing);
    await reveal(tester, find.byKey(const Key('recovery-budget')));
    expect(
      find.textContaining('Qoʻshimcha qarz toʻlovi: ${n('2 000 000')}'),
      findsOneWidget,
    );
    await tapIn(tester, find.byKey(const Key('recovery-save')));

    final s = await env.container.read(recoveryStateProvider.future);
    expect(s.isActive, isTrue);
    expect(
      (await env.container
              .read(vaultServiceProvider.future)
              .then(
                (v) => v.overview(),
              ))
          .rule
          .basisPoints,
      1000,
    );
    await reveal(tester, find.textContaining('Yoqilgan'));
    expect(find.textContaining('Yoqilgan'), findsOneWidget);
  });

  testWidgets('reja: 20 % ulush bilan Akmal 5 oy erta, tartib oʻzgaradi', (
    tester,
  ) async {
    final env = await pumpBarakaApp(tester);
    final akmal = await seedAkmal(env);
    final debts = await env.container.read(debtServiceProvider.future);
    final shop = await debts.add(
      creditorType: CreditorType.shop,
      creditorName: 'Doʻkon',
      principal: som(1000000),
      scheduleType: DebtScheduleType.manual,
      manual: [
        Installment(
          dueOn: LocalDate(2026, 12, 1),
          amount: som(1000000),
          interest: som(0),
        ),
      ],
    );
    await (await env.container.read(recoveryServiceProvider.future)).enable();
    await open(tester, env, AppRoutes.debtPlan);

    final id = akmal.debt.meta.id;
    expect(find.byKey(Key('payoff-debt-$id')), findsOneWidget);
    final gain = tester.widget<Text>(find.byKey(Key('payoff-gain-$id'))).data;
    expect(gain, startsWith('5 oy erta'));
    expect(gain, contains(n('2 432 340,42')));
    expect(gain, endsWith('tejaladi'));
    // Taxminiy hisob izohi doim ko'rinadi.
    expect(find.textContaining('Taxminiy hisob'), findsOneWidget);

    // Jadvallar yonma-yon.
    await tapIn(tester, find.byKey(Key('payoff-table-$id')));
    expect(
      find.text('—'),
      findsWidgets,
      reason: 'tezlashtirilgan erta tugaydi',
    );

    // Do'konni birinchi o'ringa.
    await tapIn(tester, find.byKey(Key('payoff-up-${shop.debt.meta.id}')));
    // Servis orqali (yozuv navbatidan keyin) — provider keshi emas.
    final o = await debts.overview();
    expect(o.debts.first.debt.meta.id, shop.debt.meta.id);
    await tester.pumpAndSettle();
    final reset = find.byKey(const Key('payoff-order-reset'));
    await tester.scrollUntilVisible(
      reset,
      -200,
      scrollable: find.byType(Scrollable).first,
    );
    await tester.ensureVisible(reset);
    await tester.pumpAndSettle();
    await tester.tap(reset);
    await tester.pumpAndSettle();
    final o2 = await debts.overview();
    expect(o2.debts.first.debt.meta.id, id);
  });

  testWidgets('qarz yopilganda nishonlash va rejim odatiyga qaytadi', (
    tester,
  ) async {
    final env = await pumpBarakaApp(tester);
    final debts = await env.container.read(debtServiceProvider.future);
    final incomes = await env.container.read(incomeServiceProvider.future);
    await incomes.add(
      amount: som(10000000),
      source: IncomeSource.salary,
      channel: PaymentChannel.card,
      receivedAt: DateTime.utc(2026, 9, 5, 7),
    );
    final v = await debts.add(
      creditorType: CreditorType.relative,
      creditorName: 'Togʻam',
      principal: som(500000),
      scheduleType: DebtScheduleType.manual,
      manual: [
        Installment(
          dueOn: LocalDate(2026, 11, 1),
          amount: som(500000),
          interest: som(0),
        ),
      ],
    );
    await (await env.container.read(recoveryServiceProvider.future)).enable();
    await open(tester, env, AppRoutes.debt(v.debt.meta.id));
    await tester.tap(find.byKey(const Key('debt-pay')));
    await tester.pumpAndSettle();
    await tester.tap(find.byKey(const Key('amount-sheet-done')));
    await tester.pumpAndSettle();

    expect(find.byKey(const Key('debt-closed-title')), findsOneWidget);
    expect(find.byKey(const Key('debt-mode-returned')), findsOneWidget);
    await tester.tap(find.byKey(const Key('debt-closed-redirect')));
    await tester.pumpAndSettle();
    expect(find.byKey(const Key('debt-closed-message')), findsOneWidget);
    final rule = (await (await env.container.read(
      vaultServiceProvider.future,
    )).overview()).rule;
    expect(rule.basisPoints, 3000, reason: '10 % + boʻshagan 20 %');
    final h = await (await env.container.read(
      householdRepositoryProvider.future,
    )).current();
    expect(h.budgetMode, BudgetMode.standard);
    expect(h.freedShareOfferPending, isFalse);
    await tester.tap(find.byKey(const Key('debt-closed-done')));
    await tester.pumpAndSettle();
    expect(find.byKey(const Key('debt-closed-title')), findsNothing);
  });

  testWidgets('sotilgan buyum puli bir bosishda qarzga', (tester) async {
    final env = await pumpBarakaApp(tester);
    final akmal = await seedAkmal(env, income: false);
    await open(tester, env, AppRoutes.sellables);
    await tester.tap(find.byKey(const Key('sellable-add')));
    await tester.pumpAndSettle();
    await tester.enterText(find.byKey(const Key('sellable-name')), 'Televizor');
    await tester.pump();
    await tester.tap(find.byKey(const Key('sellable-next')));
    await tester.pumpAndSettle();
    for (final k in ['1', '5', '0', '0', '000']) {
      await tester.tap(find.byKey(Key('amount-key-$k')).last);
      await tester.pump();
    }
    await tester.tap(find.byKey(const Key('amount-sheet-done')));
    await tester.pumpAndSettle();

    final item = (await env.container.read(sellablesProvider.future)).single;
    await tester.pumpAndSettle();
    expect(find.textContaining(n('1 500 000')), findsOneWidget);
    await tester.tap(find.byKey(Key('sellable-sold-${item.meta.id}')));
    await tester.pumpAndSettle();
    await tester.tap(find.byKey(const Key('amount-sheet-done')));
    await tester.pumpAndSettle();
    await tester.tap(find.byKey(Key('sellable-apply-${item.meta.id}')));
    await tester.pumpAndSettle();

    expect(find.textContaining('qoʻshimcha toʻlov qilindi'), findsOneWidget);
    final debts = await env.container.read(debtServiceProvider.future);
    final after = await debts.view(akmal.debt);
    expect(after.payments.single.isPrepayment, isTrue);
    expect(after.payments.single.amount, som(1500000));
    expect(after.cost.totalPaid < akmal.cost.totalPaid, isTrue);
  });

  testWidgets('bosh ekranda «Qarzsiz kun» va rejim taklifi', (tester) async {
    final env = await pumpBarakaApp(tester);
    await seedAkmal(env);
    env.container.invalidate(debtOverviewProvider);
    env.container.invalidate(recoveryStateProvider);
    await tester.pumpAndSettle();
    final card = find.byKey(const Key('home-debt-free'));
    await reveal(tester, card);
    expect(
      find.descendant(of: card, matching: find.text('Qarzsiz kun: 09.12.2027')),
      findsOneWidget,
    );
    expect(
      find.descendant(
        of: card,
        matching: find.textContaining('«Qarzdan chiqish» rejimini yoqing'),
      ),
      findsOneWidget,
    );
  });

  test('yangi marshrutlar FLAG_SECURE', () {
    for (final r in [
      AppRoutes.debtPlan,
      AppRoutes.debtRecovery,
      AppRoutes.sellables,
    ]) {
      expect(AppRoutes.secure, contains(r));
    }
  });
}
