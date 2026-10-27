import 'dart:async';

import 'package:baraka_daftari/app/router/app_router.dart';
import 'package:baraka_daftari/app/router/app_routes.dart';
import 'package:baraka_daftari/core/domain/enums.dart';
import 'package:baraka_daftari/core/money/money.dart';
import 'package:baraka_daftari/core/time/calendar.dart';
import 'package:baraka_daftari/features/prices/data/price_providers.dart';
import 'package:baraka_daftari/features/vault/data/vault_providers.dart';
import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:mocktail/mocktail.dart';

import '../../helpers/pump_app.dart';

const nbsp = ' ';
String n(String s) => s.replaceAll(' ', nbsp);
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

Future<void> scrollTo(WidgetTester tester, Finder f) async {
  await tester.scrollUntilVisible(
    f,
    300,
    scrollable: find.byType(Scrollable).first,
  );
  await tester.ensureVisible(f);
  await tester.pumpAndSettle();
}

void main() {
  testWidgets('qorovul pul: taxminiy summa → «1,4 / 6 oy»', (tester) async {
    final env = await pumpBarakaApp(tester);
    await (await env.container.read(
      vaultServiceProvider.future,
    )).setInitialBalance(som(3500000));
    await open(tester, env, AppRoutes.vault);
    await scrollTo(tester, find.byKey(const Key('reserve-estimate')));
    await tester.tap(find.byKey(const Key('reserve-estimate')));
    await tester.pumpAndSettle();
    await typeAmount(tester, ['2', '5', '0', '0', '000']);
    await tester.tap(find.byKey(const Key('amount-sheet-done')));
    await tester.pumpAndSettle();
    await scrollTo(tester, find.byKey(const Key('reserve-months')));
    expect(find.text('1,4 / 6 oy'), findsOneWidget);
    expect(find.textContaining(n('15 000 000 soʻm')), findsOneWidget);
    expect(find.text('Siz kiritgan taxminiy summa boʻyicha'), findsOneWidget);
  });

  testWidgets('darvoza yopiq: ongli chetlab oʻtish → oʻsadiganga kiritish', (
    tester,
  ) async {
    final env = await pumpBarakaApp(tester);
    await open(tester, env, AppRoutes.vault);
    await scrollTo(tester, find.byKey(const Key('growth-bypass')));
    expect(find.text('Avval tayyorgarlik, keyin sarmoya'), findsOneWidget);
    await tester.tap(find.byKey(const Key('growth-bypass')));
    await tester.pumpAndSettle();
    expect(find.text('Ongli qaror'), findsOneWidget);
    await tester.tap(find.byKey(const Key('gate-bypass-confirm')));
    await tester.pumpAndSettle();
    await typeAmount(tester, ['3', '0', '0', '000']);
    await tester.tap(find.byKey(const Key('amount-sheet-done')));
    await tester.pumpAndSettle();
    final o = await env.container.read(vaultOverviewProvider.future);
    expect(o.growthBalance, som(300000));
    expect(o.household.gateBypassedAt, isNotNull);
    await scrollTo(tester, find.byKey(const Key('growth-balance')));
    expect(
      find.text('Darvoza ongli ravishda chetlab oʻtilgan'),
      findsOneWidget,
    );
  });

  testWidgets('narx daftari: mahsulot → narx → shaxsiy inflyatsiya', (
    tester,
  ) async {
    final env = await pumpBarakaApp(tester);
    final book = await env.container.read(priceBookServiceProvider.future);
    final meat = await book.addItem(
      name: 'Goʻsht',
      unit: 'kg',
      monthlyQuantityMilli: 4000,
    );
    await book.addPrice(meat, som(100000), on: LocalDate(2025, 10, 1));
    await open(tester, env, AppRoutes.prices);
    // Bir yil oldin ham, bugun ham 100 000 (oxirgi maʼlum narx) — 0 %.
    expect(find.text('Shaxsiy inflyatsiya (1 yil): +0 %'), findsOneWidget);

    await tester.tap(find.byKey(Key('price-add-${meat.meta.id}')));
    await tester.pumpAndSettle();
    // Oldingi narx oldindan toʻldirilgan — oʻchirib yangisini kiritamiz.
    for (var i = 0; i < 8; i++) {
      await tester.tap(find.byKey(const Key('amount-key-back')).last);
      await tester.pump();
    }
    await typeAmount(tester, ['1', '3', '0', '000']);
    await tester.tap(find.byKey(const Key('amount-sheet-done')));
    await tester.pumpAndSettle();
    expect(
      find.text('Shaxsiy inflyatsiya (1 yil): +30 %'),
      findsOneWidget,
    );

    // Yangi mahsulot dialogi: kasr miqdor.
    await tester.tap(find.byKey(const Key('price-item-add')));
    await tester.pumpAndSettle();
    await tester.enterText(find.byKey(const Key('price-item-name')), 'Un');
    await tester.enterText(find.byKey(const Key('price-item-qty')), '1,5');
    await tester.pump();
    await tester.tap(find.byKey(const Key('price-item-save')));
    await tester.pumpAndSettle();
    final items = (await env.container.read(priceBookProvider.future)).items;
    expect(items.last.item.monthlyQuantityMilli, 1500);
    verify(() => env.reminders.syncTreats(any(), any())).called(greaterThan(0));
  });

  testWidgets('«Inflyatsiya taʼsiri»: kg va keyingi qadam', (tester) async {
    final env = await pumpBarakaApp(tester);
    await (await env.container.read(
      vaultServiceProvider.future,
    )).setInitialBalance(som(1950000));
    final book = await env.container.read(priceBookServiceProvider.future);
    final meat = await book.addItem(
      name: 'goʻsht',
      unit: 'kg',
      monthlyQuantityMilli: 4000,
    );
    await book.addPrice(meat, som(100000), on: LocalDate(2025, 10, 1));
    await book.addPrice(meat, som(130000));
    await open(tester, env, AppRoutes.mouse);
    expect(find.text('Bugungi narxda: 15 kg goʻsht'), findsOneWidget);
    expect(find.text('Bir yil oldingi narxda edi: 19,5 kg'), findsOneWidget);
    expect(find.byKey(const Key('mouse-future')), findsOneWidget);
    expect(find.byKey(const Key('mouse-next')), findsOneWidget);
  });

  testWidgets('ribo filtri: «Foiz (ribo)» belgisi auditda alohida', (
    tester,
  ) async {
    final env = await pumpBarakaApp(tester);
    final incomes = await env.container.read(incomeServiceProvider.future);
    await incomes.add(
      amount: som(500000),
      source: IncomeSource.other,
      channel: PaymentChannel.card,
      sourceType: IncomeSourceType.ribo,
      receivedAt: DateTime.utc(2026, 9, 15, 7),
    );
    await open(tester, env, AppRoutes.audit);
    expect(
      find.text('Foizli daromad (alohida): ${n('500 000 soʻm')}'),
      findsOneWidget,
    );

    // Daromad ekranidagi belgi va izoh.
    await open(tester, env, AppRoutes.incomeNew);
    await scrollTo(tester, find.byKey(const Key('income-type-ribo')));
    await tester.tap(find.byKey(const Key('income-type-ribo')));
    await tester.pumpAndSettle();
    expect(find.byKey(const Key('income-ribo-note')), findsOneWidget);
  });
}
